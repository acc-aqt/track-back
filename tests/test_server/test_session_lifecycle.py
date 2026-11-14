import json

import pytest
from fastapi.testclient import TestClient

from music_service.error import MusicServiceError
from server.game_sessions import game_session_manager
from server.server import Server


@pytest.fixture
def client():
    return TestClient(Server().app)


@pytest.fixture(autouse=True)
def _clear_sessions():
    yield
    game_session_manager.sessions.clear()


def _create_and_join(client: TestClient, game_id: str, user: str) -> None:
    response = client.post(
        "/create",
        json={"game_id": game_id, "target_song_count": 2, "music_service_type": "mock"},
    )
    assert response.status_code == 201
    response = client.post("/join", json={"game_id": game_id, "user_name": user})
    assert response.status_code == 200


def test_ping_before_start_keeps_session_alive(client: TestClient):
    game_id = "ping-before-start"
    _create_and_join(client, game_id, "host")

    with client.websocket_connect(f"/ws/{game_id}/host") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"

        ws.send_json({"type": "ping"})
        ws.send_json({"type": "ping"})

        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"


def test_create_with_unknown_music_service_is_rejected(client: TestClient):
    response = client.post(
        "/create",
        json={
            "game_id": "bad-service",
            "target_song_count": 2,
            "music_service_type": "napster",
        },
    )
    assert response.status_code == 400
    assert "napster" in response.json()["detail"]
    assert game_session_manager.get_game_session("bad-service") is None


@pytest.mark.parametrize(
    "bad_message",
    [
        "not json",
        json.dumps({"type": "guess"}),
        json.dumps({"type": "guess", "index": "0"}),
        json.dumps({"type": "guess", "index": True}),
        json.dumps({"type": "guess", "index": -1}),
        json.dumps({"type": "guess", "index": 99}),
        json.dumps({"type": "dance"}),
        json.dumps([1, 2]),
    ],
)
def test_malformed_message_gets_error_and_socket_stays_usable(
    client: TestClient, bad_message: str
):
    game_id = "malformed-message"
    _create_and_join(client, game_id, "solo")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"

        ws.send_text(bad_message)
        assert json.loads(ws.receive_text())["type"] == "error"

        ws.send_json({"type": "guess", "index": 0})
        assert json.loads(ws.receive_text())["type"] == "guess_result"


def test_music_service_failure_during_guess_is_reported(client: TestClient):
    game_id = "music-service-failure"
    _create_and_join(client, game_id, "solo")
    music_service = game_session_manager.get_game_session(game_id).game_logic.music_service

    def broken_current_song() -> None:
        raise MusicServiceError("No active Spotify playback.")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"

        music_service.current_song = broken_current_song
        ws.send_json({"type": "guess", "index": 0})
        response = json.loads(ws.receive_text())
        assert response["type"] == "error"
        assert "No active Spotify playback" in response["message"]
