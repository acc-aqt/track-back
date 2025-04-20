import pytest
from fastapi.testclient import TestClient

from music_service.mock import DummyMusicService
from game.game_modes import GameMode
from server.game_context import GameContext
from server.server import Server
from server.websocket_handler import WebSocketGameHandler

WebSocketGameHandler._terminate_process = lambda self: print(
    "Terminating (stubbed)"
)  # not actually killing the process within Tet

@pytest.fixture()
def test_env():
    ctx = GameContext(
        target_song_count=2,
        music_service=DummyMusicService(),
    )
    server = Server(game_context=ctx, port="")
    return TestClient(server.app), ctx


def test_register_user_succeeds(test_env):
    client, ctx = test_env
    user_name = "testuser"
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()
    assert len(ctx.registered_users) == 1


def test_register_user_twice_fails(test_env):
    client, ctx = test_env
    user_name = "testuser"
    client.post(f"/register?user_name={user_name}")
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 409
    assert "detail" in response.json()
    assert len(ctx.registered_users) == 1


def test_register_two_users_succeeds(test_env):
    client, ctx = test_env
    user_name_1 = "testuser1"
    user_name_2 = "testuser2"

    client.post(f"/register?user_name={user_name_1}")
    response = client.post(f"/register?user_name={user_name_2}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()
    assert len(ctx.registered_users) == 2


def test_nobody_registered_start_fails(test_env):
    client, _ = test_env
    response = client.post("/start")
    assert response.status_code == 400
    assert "detail" in response.json()


def test_one_user_registered_start_succeeds(test_env):
    client, _ = test_env
    user_name = "testuser"
    client.post(f"/register?user_name={user_name}")
    with client.websocket_connect(f"/ws/{user_name}") as websocket:
        response = client.post("/start")
        assert response.status_code == 200
        assert "message" in response.json()


def test_websocket_disconnect_cleans_user(test_env):
    client, ctx = test_env
    username = "disconnect_test"

    with client.websocket_connect(f"/ws/{username}") as websocket:
        assert username in ctx.connected_users

    # After exiting context manager, disconnect happens
    assert username not in ctx.connected_users
