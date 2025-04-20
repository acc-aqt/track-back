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
    return TestClient(server.app), request.param


def test_single_player_game(test_env):
    client, game_mode = test_env
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


def test_two_player_game(test_env):
    client, game_mode = test_env
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

        if game_mode == GameMode.SEQUENTIAL:
            # Player2: Receive the turn result
            response = json.loads(ws2.receive_text())
            assert response["type"] == "turn_result"

        # Player1: Make another guess -> not my turn
        ws1.send_json({"type": "guess", "index": 0})
        response = json.loads(ws1.receive_text())
        assert response["type"] == "error"
        # # Player2: Also receive the "error" message
        # response = json.loads(ws2.receive_text())
        # assert response["type"] == "error"

        # Player2: Receive the "your_turn" message
        response = json.loads(ws2.receive_text())
        assert response["type"] == "your_turn"

        if game_mode == GameMode.SIMULTANEOUS:
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

        # Player1: Receive the turn result
        if game_mode == GameMode.SEQUENTIAL:
            response = json.loads(ws1.receive_text())
            assert response["type"] == "turn_result"

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

        # Player2: Receive the turn result
        if game_mode == GameMode.SEQUENTIAL:
            response = json.loads(ws2.receive_text())
            assert response["type"] == "turn_result"

        # Player2: Receive the "your_turn" message
        response = json.loads(ws2.receive_text())
        assert response["type"] == "your_turn"
        if game_mode == GameMode.SIMULTANEOUS:
            response = json.loads(ws2.receive_text())
            assert response["type"] == "your_turn"

        # Player2: Send the second guess --> correct --> wins
        ws2.send_json({"type": "guess", "index": 1})

        # Then receive the guess result
        response = json.loads(ws2.receive_text())

        assert response["type"] == "guess_result"
        assert response["result"] == "correct"
        assert len(response["song_list"]) == 2
        assert response["last_index"] == "1"
        assert len(response["other_players"]) == 1
        assert response["game_over"] is True
        assert response["winner"] == user_name_2
