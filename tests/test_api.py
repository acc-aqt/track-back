import pytest
from fastapi.testclient import TestClient
from backend.server.game_context import GameContext
from backend.music_service.mock import DummyMusicService
from backend.server.server import Server

game_context = GameContext(
    target_song_count=2,
    music_service=DummyMusicService(),
)
server = Server(game_context=game_context, port="")
client = TestClient(server.app)


@pytest.fixture(autouse=True)
def reset_game_context():
    game_context.reset()


def test_register_user_succeeds():
    user_name = "testuser"
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()
    assert len(server.game_context.registered_users) == 1


def test_register_user_twice_fails():
    user_name = "testuser"
    client.post(f"/register?user_name={user_name}")
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 409
    assert "detail" in response.json()
    assert len(server.game_context.registered_users) == 1


def test_register_two_users_succeeds():
    user_name_1 = "testuser1"
    user_name_2 = "testuser2"

    client.post(f"/register?user_name={user_name_1}")
    response = client.post(f"/register?user_name={user_name_2}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()
    assert len(server.game_context.registered_users) == 2


def test_shutdown_server_endpoint():
    response = client.post("/shutdown")
    assert response.status_code == 200
    assert "message" in response.json()


def test_nobody_registered_start_fails():
    response = client.post("/start")
    assert response.status_code == 400
    assert "detail" in response.json()


def test_one_user_registered_start_succeeds():
    user_name = "testuser"
    client.post(f"/register?user_name={user_name}")
    response = client.post("/start")
    assert response.status_code == 200
    assert "message" in response.json()


def test_invalid_start_game_method():
    response = client.get("/start")
    assert response.status_code == 405
