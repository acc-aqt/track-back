import json

import pytest
from fastapi.testclient import TestClient

from server.game_sessions import game_session_manager
from server.server import Server


@pytest.fixture
def client():
    return TestClient(Server().app)


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

    game_session_manager.remove_game_session(game_id)
