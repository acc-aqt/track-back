import json


import pytest
from fastapi.testclient import TestClient

from music_service.mock import DummyMusicService
from game.game_modes import GameMode
from server.game_context import GameContext
from server.server import Server


@pytest.fixture(params=[GameMode.SEQUENTIAL, GameMode.SIMULTANEOUS])
def test_env(request):
    ctx = GameContext(
        target_song_count=2,
        music_service=DummyMusicService(),
        game_mode=request.param,
    )
    server = Server(game_context=ctx, port="")
    return TestClient(server.app)


def test_single_player_game(test_env):
    client  = test_env
    user_name = "testuser"

    client.post(f"/register?user_name={user_name}")

    with client.websocket_connect(f"/ws/{user_name}") as websocket:
        response = client.post("/start")
        data = response.json()
        assert response.status_code == 200
        assert data["type"] == "game_start"

        # Receive the welcome message
        response = json.loads(websocket.receive_text())
        assert response["type"] == "welcome"

        # Receive the "your_turn" message
        response = json.loads(websocket.receive_text())
        assert response["type"] == "your_turn"

        # Then send the first guess
        websocket.send_json({"type": "guess", "index": 0})

        # Then receive the guess result
        response = json.loads(websocket.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "correct"
        assert len(response["song_list"]) == 1
        assert response["last_index"] == "0"
        assert response["other_players"] == []
        assert response["game_over"] is False
        assert response["winner"] == ""

        # Receive the "your_turn" message
        response = json.loads(websocket.receive_text())
        assert response["type"] == "your_turn"

        # Send the second guess
        # Songs from MockService are ordered by release year.
        websocket.send_json({"type": "guess", "index": 0})  # this is a wrong guess

        # Then receive the guess result
        response = json.loads(websocket.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "wrong"
        assert len(response["song_list"]) == 1
        assert response["last_index"] == "0"
        assert response["other_players"] == []
        assert response["game_over"] is False
        assert response["winner"] == ""

        # Receive the "your_turn" message
        response = json.loads(websocket.receive_text())
        assert response["type"] == "your_turn"

        # Send the third guess
        websocket.send_json({"type": "guess", "index": 1})  # this is a correct guess

        # Then receive the guess result
        response = json.loads(websocket.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "correct"
        assert len(response["song_list"]) == 2
        assert response["last_index"] == "1"
        assert response["other_players"] == []
        assert response["game_over"] is True
        assert response["winner"] == user_name
