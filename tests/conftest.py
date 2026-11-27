from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from track_back.music_service.selection import MusicServiceType
from track_back.server.game_sessions import GameSession, GameSessionManager
from track_back.server.server import Server

CreateGame = Callable[[str], None]
CreateAndJoin = Callable[..., None]


@pytest.fixture
def game_sessions() -> GameSessionManager:
    return GameSessionManager()


@pytest.fixture
def client(game_sessions: GameSessionManager) -> TestClient:
    server = Server(music_service=MusicServiceType.MOCK, game_sessions=game_sessions)
    return TestClient(server.app)


@pytest.fixture
def create_game(client: TestClient) -> CreateGame:
    def create(session_name: str) -> None:
        response = client.post(
            "/create",
            json={
                "game_id": session_name,
                "target_song_count": 2,
                "music_service_type": "mock",
            },
        )
        assert response.status_code == 201

    return create


@pytest.fixture
def create_and_join(client: TestClient, create_game: CreateGame) -> CreateAndJoin:
    def create_and_join(session_name: str, *player_names: str) -> None:
        create_game(session_name)
        for user_name in player_names:
            response = client.post(
                "/join", json={"game_id": session_name, "user_name": user_name}
            )
            assert response.status_code == 200

    return create_and_join


@pytest.fixture
def get_session(game_sessions: GameSessionManager) -> Callable[[str], GameSession]:
    def get(session_name: str) -> GameSession:
        session = game_sessions.get_game_session(session_name)
        assert session is not None
        return session

    return get
