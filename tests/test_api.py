from fastapi.testclient import TestClient
from backend.server.game_context import GameContext
from backend.music_service.mock import DummyMusicService
from backend.server.server import Server  # Replace with your actual module name

game_context = GameContext(
    target_song_count=2,
    music_service=DummyMusicService(),
)
server = Server(game_context=game_context, port="8000")  # Mock or pass a GameContext if needed
client = TestClient(server.app)


def test_register_user_successful():
    user_name = "testuser"
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()


def test_register_twice_unsuccessful():
    user_name = "testuser"
    client.post(f"/register?user_name={user_name}")
    response = client.post(f"/register?user_name={user_name}")
    assert response.status_code == 409
    assert "detail" in response.json()


def test_register_two_users_successful():
    user_name_1 = "testuser1"
    user_name_2 = "testuser2"

    client.post(f"/register?user_name={user_name_1}")
    response = client.post(f"/register?user_name={user_name_2}")
    assert response.status_code == 201
    assert "message" in response.json()
    assert "user" in response.json()


def test_shutdown_server_endpoint():
    response = client.post("/shutdown")
    assert response.status_code == 200
    assert "message" in response.json()


def test_nobody_registered_cannot_start():
    response = client.post("/start")
    assert response.status_code == 400
    assert "detail" in response.json()


def test_invalid_start_game_method():
    response = client.get("/start")
    assert response.status_code == 405
