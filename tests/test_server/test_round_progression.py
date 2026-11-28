"""Tests that a disconnect never leaves a round waiting forever."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from track_back.music_service.error import MusicServiceError
from track_back.server.game_sessions import GameSession

YESTERDAY = {
    "title": "Yesterday",
    "artist": "The Beatles",
    "release_year": 1965,
    "album_cover_url": "",
}


def _receive(ws: WebSocketTestSession) -> dict[str, Any]:
    message: dict[str, Any] = ws.receive_json()
    return message


def _start(
    client: TestClient, session_name: str, *sockets: WebSocketTestSession
) -> None:
    response = client.post("/start", json={"game_id": session_name})
    assert response.status_code == 200
    for ws in sockets:
        assert _receive(ws)["type"] == "your_turn"


def test_last_owed_guesser_disconnecting_starts_next_round(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "advance-on-disconnect"
    create_and_join(session_name, "alice", "bob")

    with (
        client.websocket_connect(f"/ws/{session_name}/alice") as ws1,
        client.websocket_connect(f"/ws/{session_name}/bob") as ws2,
    ):
        _receive(ws1)
        _receive(ws2)
        _start(client, session_name, ws1, ws2)
        ws1.send_json({"type": "guess", "index": 0})
        assert _receive(ws1)["type"] == "guess_result"

        ws2.close()

        assert _receive(ws1)["type"] == "user_disconnected"
        assert _receive(ws1) == {
            "type": "your_turn",
            "message": "New round! Make your guess!",
            "next_player": "alice",
            "song_list": [YESTERDAY],
        }


def test_disconnect_of_player_who_guessed_does_not_advance_round(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "no-early-advance"
    create_and_join(session_name, "alice", "bob")

    with (
        client.websocket_connect(f"/ws/{session_name}/alice") as ws1,
        client.websocket_connect(f"/ws/{session_name}/bob") as ws2,
    ):
        _receive(ws1)
        _receive(ws2)
        _start(client, session_name, ws1, ws2)
        ws1.send_json({"type": "guess", "index": 0})
        assert _receive(ws1)["type"] == "guess_result"
        assert _receive(ws2)["type"] == "other_player_guess"

        ws1.close()
        assert _receive(ws2)["type"] == "user_disconnected"

        ws2.send_json({"type": "guess", "index": 0})
        guess_result = _receive(ws2)
        assert guess_result["type"] == "guess_result"
        assert guess_result["last_song"] == YESTERDAY
        assert _receive(ws2)["type"] == "your_turn"


def test_winning_guess_sends_no_your_turn(client: TestClient) -> None:
    session_name = "first-guess-wins"
    response = client.post(
        "/create",
        json={
            "game_id": session_name,
            "target_song_count": 1,
            "music_service_type": "mock",
        },
    )
    assert response.status_code == 201
    for username in ("alice", "bob"):
        response = client.post(
            "/join", json={"game_id": session_name, "user_name": username}
        )
        assert response.status_code == 200

    with (
        client.websocket_connect(f"/ws/{session_name}/alice") as ws1,
        client.websocket_connect(f"/ws/{session_name}/bob") as ws2,
    ):
        _receive(ws1)
        _receive(ws2)
        _start(client, session_name, ws1, ws2)
        ws1.send_json({"type": "guess", "index": 0})

        assert _receive(ws1)["type"] == "guess_result"
        assert _receive(ws1)["type"] == "game_over"
        assert _receive(ws2)["type"] == "other_player_guess"
        assert _receive(ws2)["type"] == "game_over"


def test_failed_skip_after_a_disconnect_still_starts_the_next_round(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_name = "skip-failure-on-disconnect"
    create_and_join(session_name, "alice", "bob")
    music_service = get_session(session_name).game_logic.music_service

    def broken_next_track() -> None:
        raise MusicServiceError("Cannot skip to the next track.")

    with (
        client.websocket_connect(f"/ws/{session_name}/alice") as ws1,
        client.websocket_connect(f"/ws/{session_name}/bob") as ws2,
    ):
        _receive(ws1)
        _receive(ws2)
        _start(client, session_name, ws1, ws2)
        ws1.send_json({"type": "guess", "index": 0})
        assert _receive(ws1)["type"] == "guess_result"

        monkeypatch.setattr(music_service, "next_track", broken_next_track)
        ws2.close()

        assert _receive(ws1)["type"] == "user_disconnected"
        assert _receive(ws1)["type"] == "your_turn"
