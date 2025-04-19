# import pytest
# from fastapi.testclient import TestClient
# from backend.server.game_context import GameContext
# from backend.music_service.mock import DummyMusicService
# from backend.server.server import Server


# @pytest.fixture
# def test_env():
#     ctx = GameContext(
#         target_song_count=2,
#         music_service=DummyMusicService(),
#     )
#     server = Server(game_context=ctx, port="")
#     return TestClient(server.app), ctx


# def test_shutdown_server_endpoint(test_env):
#     client, _ = test_env
#     response = client.post("/shutdown")
#     assert response.status_code == 200
#     assert "message" in response.json()