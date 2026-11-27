"""Tests for (re)entering a running game by opening the WebSocket."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

YESTERDAY = {
    "title": "Yesterday",
    "artist": "The Beatles",
    "release_year": 1965,
    "album_cover_url": "",
}


def _receive(ws: WebSocketTestSession) -> dict[str, Any]:
    message: dict[str, Any] = ws.receive_json()
    return message


def _join(client: TestClient, session_name: str, username: str) -> int:
    response = client.post(
        "/join", json={"game_id": session_name, "user_name": username}
    )
    status: int = response.status_code
    return status


@contextmanager
def _started_game(
    client: TestClient, create_and_join: Callable[..., None], session_name: str
) -> Iterator[WebSocketTestSession]:
    """Start a game for alice and bob; yield alice's socket after bob dropped."""
    create_and_join(session_name, "alice", "bob")
    with client.websocket_connect(f"/ws/{session_name}/alice") as alice:
        _receive(alice)
        with client.websocket_connect(f"/ws/{session_name}/bob") as bob:
            _receive(bob)
            assert (
                client.post("/start", json={"game_id": session_name}).status_code == 200
            )
            assert _receive(alice)["type"] == "your_turn"
            assert _receive(bob)["type"] == "your_turn"
        assert _receive(alice)["type"] == "user_disconnected"
        yield alice


def test_websocket_reconnect_without_join_restores_player(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "auto-reconnect"
    with (
        _started_game(client, create_and_join, session_name) as alice,
        client.websocket_connect(f"/ws/{session_name}/bob") as bob,
    ):
        assert _receive(bob)["type"] == "welcome"
        assert _receive(bob) == {
            "type": "your_turn",
            "message": "Place the new Song in your Timeline!",
            "next_player": "bob",
            "song_list": [],
        }
        assert _receive(alice)["type"] == "player_rejoined"
        assert client.get("/list-sessions").json() == {"sessions": []}
        assert _join(client, session_name, "bob") == 409


def test_manual_join_after_disconnect_then_connect(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "manual-rejoin"
    with _started_game(client, create_and_join, session_name) as alice:
        assert _join(client, session_name, "bob") == 200
        with client.websocket_connect(f"/ws/{session_name}/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            assert _receive(bob)["type"] == "your_turn"
            assert _receive(alice) == {
                "type": "player_rejoined",
                "message": "bob re-joined the game! "
                "There are now 2 players: alice, bob.",
                "song_list": [],
                "user_name": "bob",
            }


def test_rejoin_after_guessing_sends_timeline_only(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "rejoin-after-guess"
    create_and_join(session_name, "alice", "bob")
    with client.websocket_connect(f"/ws/{session_name}/alice") as alice:
        _receive(alice)
        with client.websocket_connect(f"/ws/{session_name}/bob") as bob:
            _receive(bob)
            client.post("/start", json={"game_id": session_name})
            _receive(alice)
            _receive(bob)
            bob.send_json({"type": "guess", "index": 0})
            assert _receive(bob)["type"] == "guess_result"
            assert _receive(alice)["type"] == "other_player_guess"
        assert _receive(alice)["type"] == "user_disconnected"

        with client.websocket_connect(f"/ws/{session_name}/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            rejoined = _receive(bob)
            assert rejoined["type"] == "player_rejoined"
            assert rejoined["user_name"] == "bob"
            assert rejoined["song_list"] == [YESTERDAY]
            assert _receive(alice)["type"] == "player_rejoined"

            alice.send_json({"type": "guess", "index": 0})
            assert _receive(alice)["type"] == "guess_result"
            assert _receive(bob)["type"] == "other_player_guess"
            assert _receive(bob)["song_list"] == [YESTERDAY]


@pytest.mark.parametrize(
    ("username", "detail"),
    [
        ("carol", "Player 'carol' is not a player in game session"),
        ("alice", "Player 'alice' is already connected to game session"),
    ],
)
def test_join_running_game_rejects_non_players_and_connected_players(
    client: TestClient, create_and_join: Callable[..., None], username: str, detail: str
) -> None:
    session_name = "join-rejected"
    with _started_game(client, create_and_join, session_name):
        response = client.post(
            "/join", json={"game_id": session_name, "user_name": username}
        )
        assert response.status_code == 409
        assert response.json()["detail"].startswith(detail)
        assert response.json()["detail"].endswith(
            "Only one of the following players can rejoin: bob."
        )


@pytest.mark.parametrize(
    ("username", "reason"),
    [
        (
            "carol",
            (
                "Player 'carol' is not a player in game session connect-rejected. "
                "Only one of the following players can rejoin: bob."
            ),
        ),
        (
            "alice",
            (
                "Player 'alice' is already connected to game session "
                "connect-rejected. "
                "Only one of the following players can rejoin: bob."
            ),
        ),
    ],
)
def test_connect_to_running_game_rejects_non_players_and_connected_players(
    client: TestClient, create_and_join: Callable[..., None], username: str, reason: str
) -> None:
    session_name = "connect-rejected"
    with (
        _started_game(client, create_and_join, session_name) as alice,
        client.websocket_connect(f"/ws/{session_name}/{username}") as intruder,
    ):
        assert _receive(intruder) == {"type": "error", "message": reason}
        with pytest.raises(WebSocketDisconnect):
            intruder.receive_json()

        with client.websocket_connect(f"/ws/{session_name}/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            assert _receive(alice)["type"] == "player_rejoined"


def test_connect_to_finished_game_gets_game_over(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "finished"
    with _started_game(client, create_and_join, session_name) as alice:
        alice.send_json({"type": "guess", "index": 0})
        assert _receive(alice)["type"] == "guess_result"
        assert _receive(alice)["type"] == "your_turn"
        alice.send_json({"type": "guess", "index": 1})
        assert _receive(alice)["game_over"] is True
        while _receive(alice)["type"] != "game_over":
            pass

        assert client.get("/list-sessions").json() == {"sessions": []}
        assert _join(client, session_name, "bob") == 409
        with client.websocket_connect(f"/ws/{session_name}/bob") as bob:
            assert _receive(bob) == {
                "type": "game_over",
                "winner": "alice",
                "message": "alice has won the game!",
            }
            with pytest.raises(WebSocketDisconnect):
                bob.receive_json()
