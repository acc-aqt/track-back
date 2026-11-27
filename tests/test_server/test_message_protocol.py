"""Tests pinning the WebSocket messages the server sends."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

YESTERDAY = {
    "title": "Yesterday",
    "artist": "The Beatles",
    "release_year": 1965,
    "album_cover_url": "",
}


def _receive(ws: WebSocketTestSession) -> dict[str, Any]:
    message: dict[str, Any] = ws.receive_json()
    return message


def _receive_until(ws: WebSocketTestSession, msg_type: str) -> dict[str, Any]:
    while (message := _receive(ws))["type"] != msg_type:
        pass
    return message


def _join(client: TestClient, game_id: str, user: str) -> None:
    response = client.post("/join", json={"game_id": game_id, "user_name": user})
    assert response.status_code == 200


def test_join_is_broadcast_to_connected_players(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """A join is announced to players already connected."""
    game_id = "join-broadcast"
    create_and_join(game_id, "alice")

    with client.websocket_connect(f"/ws/{game_id}/alice") as ws:
        assert _receive(ws) == {
            "type": "welcome",
            "message": "Welcome alice, you're connected.",
        }
        _join(client, game_id, "bob")
        assert _receive(ws) == {
            "type": "player_joined",
            "message": "bob joined the game! There are now 2 players: alice, bob.",
            "user_name": "bob",
        }


def test_lobby_connect_without_join_registers_silently(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """Connecting in the lobby without /join registers the player unannounced."""
    game_id = "silent-lobby-connect"
    create_and_join(game_id, "alice")

    with client.websocket_connect(f"/ws/{game_id}/alice") as alice:
        assert _receive(alice)["type"] == "welcome"
        with client.websocket_connect(f"/ws/{game_id}/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            assert client.post("/start", json={"game_id": game_id}).status_code == 200
            assert _receive(alice)["type"] == "your_turn"
            assert _receive(bob)["type"] == "your_turn"


def test_start_and_next_round_send_your_turn(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """Start and round completion send your_turn with the timeline."""
    game_id = "your-turn"
    create_and_join(game_id, "alice", "bob")

    with (
        client.websocket_connect(f"/ws/{game_id}/alice") as ws1,
        client.websocket_connect(f"/ws/{game_id}/bob") as ws2,
    ):
        _receive(ws1)
        _receive(ws2)
        assert client.post("/start", json={"game_id": game_id}).status_code == 200

        assert _receive(ws1) == {
            "type": "your_turn",
            "message": "It's your turn!",
            "next_player": "alice",
            "song_list": [],
        }
        assert _receive(ws2)["next_player"] == "bob"

        ws1.send_json({"type": "guess", "index": 0})
        assert _receive(ws1)["type"] == "guess_result"
        assert _receive(ws2) == {
            "type": "other_player_guess",
            "player": "alice",
            "result": "correct",
            "message": "alice made a guess. Guess was correct.",
            "next_player": None,
        }

        ws2.send_json({"type": "guess", "index": 0})
        assert _receive(ws2)["type"] == "guess_result"
        assert _receive(ws1)["type"] == "other_player_guess"

        assert _receive(ws1) == {
            "type": "your_turn",
            "message": "New round! Make your guess!",
            "next_player": "alice",
            "song_list": [YESTERDAY],
        }
        assert _receive(ws2)["type"] == "your_turn"


def test_game_over_is_broadcast_to_every_player(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """The winning guess ends the game for every player."""
    game_id = "game-over"
    create_and_join(game_id, "alice", "bob")

    with (
        client.websocket_connect(f"/ws/{game_id}/alice") as ws1,
        client.websocket_connect(f"/ws/{game_id}/bob") as ws2,
    ):
        _receive(ws1)
        _receive(ws2)
        client.post("/start", json={"game_id": game_id})
        _receive(ws1)
        _receive(ws2)

        ws1.send_json({"type": "guess", "index": 0})
        _receive(ws1)
        _receive(ws2)
        ws2.send_json({"type": "guess", "index": 0})
        _receive(ws2)
        _receive(ws1)
        assert _receive(ws1)["type"] == "your_turn"
        assert _receive(ws2)["type"] == "your_turn"

        ws1.send_json({"type": "guess", "index": 1})
        assert _receive(ws1)["game_over"] is True
        assert _receive(ws2)["type"] == "other_player_guess"

        game_over = {
            "type": "game_over",
            "winner": "alice",
            "message": "alice has won the game!",
        }
        assert _receive_until(ws1, "game_over") == game_over
        assert _receive_until(ws2, "game_over") == game_over


def test_disconnect_and_rejoin_are_broadcast(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """Disconnect and rejoin are announced; the rejoiner gets a card."""
    game_id = "rejoin"
    create_and_join(game_id, "alice", "bob")

    with client.websocket_connect(f"/ws/{game_id}/alice") as ws1:
        _receive(ws1)
        with client.websocket_connect(f"/ws/{game_id}/bob") as ws2:
            _receive(ws2)
            client.post("/start", json={"game_id": game_id})
            _receive(ws1)
            _receive(ws2)

        assert _receive(ws1) == {
            "type": "user_disconnected",
            "message": "bob disconnected. bob can try to re-join the game.",
        }

        _join(client, game_id, "bob")
        with client.websocket_connect(f"/ws/{game_id}/bob") as ws2:
            assert _receive(ws2)["type"] == "welcome"
            assert _receive(ws2) == {
                "type": "your_turn",
                "message": "It's your turn!",
                "next_player": "bob",
                "song_list": [],
            }
            assert _receive(ws1) == {
                "type": "player_rejoined",
                "message": "bob re-joined the game! "
                "There are now 2 players: alice, bob.",
                "song_list": [],
                "user_name": "bob",
            }


@pytest.mark.parametrize("message_type", [["guess"], {"a": 1}, None, 3])
def test_non_string_message_type_is_unknown(
    client: TestClient,
    create_and_join: Callable[..., None],
    message_type: object,
) -> None:
    """A non-string message type is rejected as unknown."""
    game_id = "odd-type"
    create_and_join(game_id, "solo")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        _receive(ws)
        ws.send_json({"type": message_type})
        assert _receive(ws) == {"type": "error", "message": "Unknown message type."}
