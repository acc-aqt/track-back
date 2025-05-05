import json

import pytest
from fastapi.testclient import TestClient

from server.server import Server
from server.websocket_handler import WebSocketGameHandler
from server.game_sessions import game_session_manager

@pytest.fixture
def client():
    """Fixture to create a fresh TestClient instance."""
    server = Server()
    return TestClient(server.app)


def test_full_game_client_connection(client: TestClient):

    # create a new game session
    game_id = "test-session-123"
    payload = {
        "game_id": game_id,
        "target_song_count": 2,
        "music_service_type": "mock",
    }

    response = client.post("/create", json=payload)

    game_session = game_session_manager.get_game_session(game_id)

    assert response.status_code == 201

    assert game_session is not None
    assert game_session.game_logic.target_song_count == 2
    assert game_session.game_logic.music_service.service_name == "Dummy Music Service"

    assert game_session.connection_manager is not None
    assert len(game_session.connection_manager.user_connections) == 0

    # try to create the same game session again fails
    response = client.post("/create", json=payload)
    assert response.status_code == 409

    payload = {"game_id": game_id}

    # nobody_registered_start_fails
    response = client.post("/start", json=payload)
    assert response.status_code == 400

    # user joining the game session

    test_user_1 = "testuser1"

    payload = {"game_id": game_id, "user_name": test_user_1}

    response = client.post("/join", json=payload)
    assert response.status_code == 200
    assert len(game_session.connection_manager.user_connections) == 1
    # same user joining again fails

    response = client.post("/join", json=payload)
    assert response.status_code == 409

    # second user joining the game session

    test_user_2 = "testuser2"

    payload = {"game_id": game_id, "user_name": test_user_2}

    response = client.post("/join", json=payload)
    assert response.status_code == 200
    assert len(game_session.connection_manager.user_connections) == 2

    with (
        client.websocket_connect(f"/ws/{game_id}/{test_user_1}") as ws1,
        client.websocket_connect(f"/ws/{game_id}/{test_user_2}") as ws2,
    ):

        # Player 1 & 2: Receive the welcome message
        response = json.loads(ws1.receive_text())
        assert response["type"] == "welcome"

        response = json.loads(ws2.receive_text())
        assert response["type"] == "welcome"

        # start game
        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 200
        assert response.json()["type"] == "game_start"
        # Player1 & 2: Receive the "your_turn" message
        response = json.loads(ws1.receive_text())
        assert response["type"] == "your_turn"

        response = json.loads(ws2.receive_text())
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

        # Player 2: Receive guess from Player 1
        response = json.loads(ws2.receive_text())
        assert response["type"] == "other_player_guess"

        # Player1: Make another guess -> not my turn
        ws1.send_json({"type": "guess", "index": 0})
        response = json.loads(ws1.receive_text())
        assert response["type"] == "error"

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

        # Player 1: Receive guess from Player 2
        response = json.loads(ws1.receive_text())
        assert response["type"] == "other_player_guess"

        # Player1 & 2: Receive the "your_turn" message
        response = json.loads(ws1.receive_text())
        assert response["type"] == "your_turn"

        response = json.loads(ws2.receive_text())
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

        #        # Player2: Receive guess from Player 1
        response = json.loads(ws2.receive_text())
        assert response["type"] == "other_player_guess"

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
        assert response["winner"] == test_user_2


