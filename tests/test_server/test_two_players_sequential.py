import json


import pytest
from fastapi.testclient import TestClient
from game.track_back_game import TrackBackGame
from music_service.mock import DummyMusicService
from game.strategies.factory import GameStrategyEnum
from server.connection_manager import ConnectionManager
from server.server import Server


@pytest.fixture()
def test_env():
    ctx = ConnectionManager()

    game = TrackBackGame(
        target_song_count=2,
        music_service=DummyMusicService(),
        game_strategy_enum=GameStrategyEnum.SEQUENTIAL,
    )

    server = Server(connection_manager=ctx, game=game)
    return TestClient(server.app)


def test_two_player_game(test_env):
    client = test_env
    user_name_1 = "testuser1"
    user_name_2 = "testuser2"

    client.post(f"/register?user_name={user_name_1}")
    client.post(f"/register?user_name={user_name_2}")

    with (
        client.websocket_connect(f"/ws/{user_name_1}") as ws1,
        client.websocket_connect(f"/ws/{user_name_2}") as ws2,
    ):
        response = client.post("/start")
        data = response.json()
        assert response.status_code == 200
        assert data["type"] == "game_start"

        # Player 1 & 2: Receive the welcome message
        response = json.loads(ws1.receive_text())
        assert response["type"] == "welcome"

        response = json.loads(ws2.receive_text())
        assert response["type"] == "welcome"

        # Player1: Receive the "your_turn" message
        response = json.loads(ws1.receive_text())
        assert response["type"] == "your_turn"

        # Player1: Send the first guess
        ws1.send_json({"type": "guess", "index": 0})
        response = json.loads(ws1.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "correct"
        assert len(response["song_list"]) == 1
        assert response["last_index"] == "0"
        assert len(response["other_players"]) == 1
        assert response["game_over"] is False
        assert response["winner"] == ""

        # Player1: Make another guess -> not my turn
        ws1.send_json({"type": "guess", "index": 0})
        response = json.loads(ws1.receive_text())
        assert response["type"] == "error"

        # Player2: Receive the "other_player_guess" message --> came in after refactoring
        response = json.loads(ws2.receive_text())
        assert response["type"] == "other_player_guess"

        # Player2: Receive the "your_turn" message
        response = json.loads(ws2.receive_text())
        assert response["type"] == "your_turn"

        # Player2: Send the first guess
        ws2.send_json({"type": "guess", "index": 0})
        response = json.loads(ws2.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "correct"
        assert len(response["song_list"]) == 1
        assert response["last_index"] == "0"
        assert len(response["other_players"]) == 1
        assert response["game_over"] is False
        assert response["winner"] == ""

        # Player1: Receive the "other_player_guess" message --> came in after refactoring
        response = json.loads(ws1.receive_text())
        assert response["type"] == "other_player_guess"

        # Player1: Receive the "your_turn" message
        response = json.loads(ws1.receive_text())
        assert response["type"] == "your_turn"

        # Player1: Send the second guess -> wrong
        ws1.send_json({"type": "guess", "index": 0})
        response = json.loads(ws1.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "wrong"
        assert len(response["song_list"]) == 1
        assert response["last_index"] == "0"
        assert len(response["other_players"]) == 1
        assert response["game_over"] is False
        assert response["winner"] == ""

        # Player2: Receive the "other_player_guess" message --> came in after refactoring
        response = json.loads(ws2.receive_text())
        assert response["type"] == "other_player_guess"

        # Player2: Receive the "your_turn" message
        response = json.loads(ws2.receive_text())
        assert response["type"] == "your_turn"

        # Player2: Send the second guess --> correct --> wins
        ws2.send_json({"type": "guess", "index": 1})
        response = json.loads(ws2.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "correct"
        assert len(response["song_list"]) == 2
        assert response["last_index"] == "1"
        assert len(response["other_players"]) == 1
        assert response["game_over"] is True
        assert response["winner"] == user_name_2
