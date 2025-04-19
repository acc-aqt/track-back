import pytest
from fastapi.testclient import TestClient
from backend.server.game_context import GameContext
from backend.music_service.mock import DummyMusicService
from backend.server.server import Server
import json


@pytest.fixture
def test_env():
    ctx = GameContext(
        target_song_count=2,
        music_service=DummyMusicService(),
    )
    server = Server(game_context=ctx, port="")
    return TestClient(server.app), ctx


def test_register_user_succeeds(test_env):
    print("Test1 running")
    client, ctx = test_env
    user_name = "testuser"
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()
    assert len(ctx.registered_users) == 1


def test_register_user_twice_fails(test_env):
    print("Test2 running")

    client, ctx = test_env
    user_name = "testuser"
    client.post(f"/register?user_name={user_name}")
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 409
    assert "detail" in response.json()
    assert len(ctx.registered_users) == 1


def test_register_two_users_succeeds(test_env):
    print("Test3 running")

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


def test_one_player_one_correct_guess(test_env):
    client, _ = test_env
    user_name = "testuser"

    client.post(f"/register?user_name={user_name}")

    with client.websocket_connect(f"/ws/{user_name}") as websocket:
        response = client.post("/start")
        data = response.json()
        assert response.status_code == 200
        assert "message" in data
        assert "first_player" in data
        assert data["first_player"] == user_name

        # Receive the welcome message
        welcome = websocket.receive_text()
        welcome_data = json.loads(welcome)
        assert welcome_data["type"] == "welcome"

        # Receive the "your_turn" message
        welcome = websocket.receive_text()
        turn_data = json.loads(welcome)
        assert turn_data["type"] == "your_turn"

        # Then send the guess
        websocket.send_json({"type": "guess", "index": 0})

        # Then receive the guess result
        result = websocket.receive_text()
        result_data = json.loads(result)

        assert "error" not in result_data
        assert result_data["type"] == "guess_result"
        assert len(result_data["song_list"]) == 1
        assert result_data["last_index"] == "0"
        assert result_data["other_players"] == []


def test_websocket_disconnect_cleans_user(test_env):
    client, ctx = test_env
    username = "disconnect_test"

    with client.websocket_connect(f"/ws/{username}") as websocket:
        assert username in ctx.connected_users

    # After exiting context manager, disconnect happens
    assert username not in ctx.connected_users
