import json

import pytest
from fastapi.testclient import TestClient

from server.server import Server
from server.game_sessions import game_session_manager


@pytest.fixture
def client():
    """Fixture to create a fresh TestClient instance."""
    server = Server()
    return TestClient(server.app)


def test_connecting_users(client: TestClient):

    # create a new game session
    game_id = "session-test-connecting-users"
    payload = {
        "game_id": game_id,
        "target_song_count": 2,
        "music_service_type": "mock",
    }

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": []}

    response = client.post("/create", json=payload)
    assert response.status_code == 201

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [game_id]}

    test_user_1 = "testuser1"

    response = client.post(
        "/join", json={"game_id": "non-existing-game-id", "user_name": test_user_1}
    )
    assert response.status_code == 404

    response = client.post("/join", json={"game_id": game_id, "user_name": test_user_1})
    assert response.status_code == 200

    test_user_2 = "testuser2"
    client.post("/join", json={"game_id": game_id, "user_name": test_user_2})
    assert response.status_code == 200

    game_session = game_session_manager.get_game_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{test_user_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{test_user_2}") as ws2:
            response = client.post("/start", json={"game_id": "non-existing-game-id"})
            assert response.status_code == 404
            
            response = client.get("list-sessions")
            assert response.status_code == 200
            assert response.json() == {"sessions": [game_id]}

            client.post("/start", json={"game_id": game_id})
            assert response.status_code == 200

            # after start not joinable anymore
            response = client.get("list-sessions")
            assert response.status_code == 200
            assert response.json() == {"sessions": []}

            assert len(game_session.connection_manager.user_connections) == 2
            assert test_user_1 in game_session.connection_manager.user_connections
            assert test_user_2 in game_session.connection_manager.user_connections
            assert len(game_session.game_logic.users) == 2

            assert game_session.game_logic.get_user(test_user_1).is_active is True
            assert game_session.game_logic.get_user(test_user_2).is_active is True


def test_disconnecting_users(client: TestClient):

    # create a new game session
    game_id = "session-test-disconnecting-users"
    payload = {
        "game_id": game_id,
        "target_song_count": 2,
        "music_service_type": "mock",
    }

    client.post("/create", json=payload)

    test_user_1 = "testuser1"
    payload = {"game_id": game_id, "user_name": test_user_1}
    client.post("/join", json=payload)

    test_user_2 = "testuser2"
    payload = {"game_id": game_id, "user_name": test_user_2}
    client.post("/join", json=payload)

    game_session = game_session_manager.get_game_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{test_user_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{test_user_2}") as ws2:
            response = json.loads(ws1.receive_text())
            assert response["type"] == "welcome"

            client.post("/start", json={"game_id": game_id})

            response = json.loads(ws1.receive_text())
            assert response["type"] == "your_turn"

            assert len(game_session.connection_manager.user_connections) == 2
            assert test_user_1 in game_session.connection_manager.user_connections
            assert test_user_2 in game_session.connection_manager.user_connections
            assert len(game_session.game_logic.users) == 2

            assert game_session.game_logic.get_user(test_user_1).is_active is True
            assert game_session.game_logic.get_user(test_user_2).is_active is True

        # user2 disconnects
        response = json.loads(ws1.receive_text())
        assert response["type"] == "user_disconnected"

        assert len(game_session.connection_manager.user_connections) == 1
        assert test_user_1 in game_session.connection_manager.user_connections
        assert test_user_2 not in game_session.connection_manager.user_connections
        assert len(game_session.game_logic.users) == 2
        assert game_session.game_logic.get_user(test_user_1).is_active is True
        assert game_session.game_logic.get_user(test_user_2).is_active is False

    # user1 disconnects --> session is removed
    assert len(game_session.connection_manager.user_connections) == 0
    assert len(game_session.game_logic.users) == 2
    assert game_session.game_logic.get_user(test_user_1).is_active is False
    assert game_session.game_logic.get_user(test_user_2).is_active is False

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": []}


def test_reconnect_after_disconnect(client: TestClient):

    # create a new game session
    game_id = "session-test-reconnect-after-disconnect"
    payload = {
        "game_id": game_id,
        "target_song_count": 2,
        "music_service_type": "mock",
    }

    client.post("/create", json=payload)

    test_user_1 = "testuser1"
    client.post("/join", json={"game_id": game_id, "user_name": test_user_1})

    test_user_2 = "testuser2"
    client.post("/join", json={"game_id": game_id, "user_name": test_user_2})

    game_session = game_session_manager.get_game_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{test_user_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{test_user_2}") as ws2:
            response = json.loads(ws1.receive_text())
            assert response["type"] == "welcome"

            client.post("/start", json={"game_id": game_id})
            response = client.get("list-sessions")
            assert response.json() == {"sessions": []}

            response = json.loads(ws1.receive_text())
            assert response["type"] == "your_turn"

        # user2 disconnects -> now there is a joinable session for this user
        response = json.loads(ws1.receive_text())
        assert response["type"] == "user_disconnected"

        response = client.get("list-sessions")
        assert response.json() == {"sessions": [game_id]}

        response = client.post("/join", json={"game_id": game_id, "user_name": "unknown_user"})
        assert response.status_code == 409
        assert len(game_session.connection_manager.user_connections) == 1
        assert game_session.game_logic.get_user(test_user_1).is_active is True
        assert game_session.game_logic.get_user(test_user_2).is_active is False

        response = client.post("/join", json={"game_id": game_id, "user_name": test_user_1})
        assert response.status_code == 409
        assert len(game_session.connection_manager.user_connections) == 1
        assert game_session.game_logic.get_user(test_user_1).is_active is True
        assert game_session.game_logic.get_user(test_user_2).is_active is False

        response = client.post("/join", json={"game_id": game_id, "user_name": test_user_2})
        assert response.status_code == 200
        assert len(game_session.connection_manager.user_connections) == 2
        assert game_session.game_logic.get_user(test_user_1).is_active is True
        assert game_session.game_logic.get_user(test_user_2).is_active is True

        response = client.get("list-sessions")
        assert response.json() == {"sessions": []}

        with client.websocket_connect(f"/ws/{game_id}/{test_user_2}") as ws2:
            response = json.loads(ws1.receive_text())
            assert response["type"] == "player_rejoined"
            # player 2: receive welcome and your turn message after reconnect
            response = json.loads(ws2.receive_text())
            assert response["type"] == "welcome"
            response = json.loads(ws2.receive_text())
            assert response["type"] == "your_turn"
            # player 2: send guess after reconnect
            ws2.send_json({"type": "guess", "index": 0})
            response = json.loads(ws2.receive_text())
            assert response["type"] == "guess_result"
            assert response["result"] == "correct"
            assert len(response["song_list"]) == 1
            assert response["last_index"] == "0"
            assert len(response["other_players"]) == 1
            assert response["game_over"] is False
            assert response["winner"] == ""

        # Player 1: Receive messages, including the guess from Player 2
        response = json.loads(ws1.receive_text())
        assert response["type"] == "other_player_guess"

        with client.websocket_connect(f"/ws/{game_id}/{test_user_2}") as ws2:
            # player 2: receive welcome and your turn message after reconnect
            response = json.loads(ws2.receive_text())
            assert response["type"] == "welcome"
            # player 2: send guess after reconnect --> already guessed
            ws2.send_json({"type": "guess", "index": 0})
            response = json.loads(ws2.receive_text())
            assert response["type"] == "error"

        # Player 1: Receive rejoin message
        # response = json.loads(ws1.receive_text())
        # assert response["type"] == "player_rejoined"
