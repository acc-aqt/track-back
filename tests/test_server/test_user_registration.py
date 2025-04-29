import pytest
from fastapi.testclient import TestClient

from game.game_logic import GameLogic
from game.strategies.factory import GameStrategyEnum
from music_service.mock import DummyMusicService
from server.connection_manager import ConnectionManager
from server.server import Server
from server.websocket_handler import WebSocketGameHandler
from server.game_sessions import game_session_manager

WebSocketGameHandler._terminate_process = lambda self: print(
    "Terminating (stubbed)"
)  # not actually killing the process within Tet


@pytest.fixture
def client():
    """Fixture to create a fresh TestClient instance."""
    server = Server()
    return TestClient(server.app)


def test_create_game(client: TestClient):

    # create a new game session

    game_id = "test-session-123"
    payload = {
        "game_id": game_id,
        "target_song_count": 10,
        "music_service_type": "mock",  # or "spotify" depending on your app config
    }

    response = client.post("/create", json=payload)

    game_session = game_session_manager.get_game_session(game_id)

    assert response.status_code == 201

    assert game_session is not None
    assert game_session.game_logic.target_song_count == 10
    assert game_session.game_logic.music_service.service_name == "Dummy Music Service"

    assert game_session.connection_manager is not None
    assert len(game_session.connection_manager.user_connections) == 0

    # try to create the same game session again fails
    response = client.post("/create", json=payload)
    assert response.status_code == 409

    # user joining the game session

    test_user_1 = "testuser1"

    payload = {"game_id": game_id, "user_name": test_user_1}

    response = client.post("/join", json=payload)
    assert response.status_code == 200
    assert len(game_session.connection_manager.user_connections) == 1
    # same user joining again fails

    response = client.post("/join", json=payload)
    assert response.status_code == 409

    # assert response.status_code == 200
    # assert "message" in response.json()


# def test_register_user_succeeds():
#     server = Server()
#     client = TestClient(server.app)

#     user_name = "testuser"
#     response = client.post(f"/register?user_name={user_name}")
#     assert response.status_code == 201
#     assert "message" in response.json()
#     assert "user" in response.json()


# def test_register_user_twice_fails():
#     client, ctx = test_env
#     user_name = "testuser"
#     client.post(f"/register?user_name={user_name}")
#     response = client.post(f"/register?user_name={user_name}")
#     assert response.status_code == 409
#     assert "detail" in response.json()
#     assert len(ctx.user_connections) == 1


# def test_register_two_users_succeeds():
#     client, ctx = test_env
#     user_name_1 = "testuser1"
#     user_name_2 = "testuser2"

#     client.post(f"/register?user_name={user_name_1}")
#     response = client.post(f"/register?user_name={user_name_2}")
#     assert response.status_code == 201
#     assert "message" in response.json()
#     assert "user" in response.json()
#     assert len(ctx.user_connections) == 2


# def test_nobody_registered_start_fails():
#     client, _ = test_env
#     response = client.post("/start")
#     assert response.status_code == 400
#     assert "detail" in response.json()


# def test_one_user_registered_start_succeeds():
#     client, _ = test_env
#     user_name = "testuser"
#     client.post(f"/register?user_name={user_name}")
#     with client.websocket_connect(f"/ws/{user_name}") as websocket:
#         response = client.post("/start")
#         assert response.status_code == 200
#         assert "message" in response.json()


# def test_websocket_disconnect_cleans_user():
#     client, ctx = test_env
#     username = "disconnect_test"

#     with client.websocket_connect(f"/ws/{username}") as websocket:
#         assert username in ctx.user_connections

#     # After exiting context manager, disconnect happens
#     assert username not in ctx.user_connections
