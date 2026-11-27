from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from track_back.music_service.selection import MusicServiceType
from track_back.server.game_sessions import GameSession, game_session_manager
from track_back.server.server import Server

CreateGame = Callable[[str], None]
CreateAndJoin = Callable[..., None]


@pytest.fixture
def client() -> TestClient:
    return TestClient(Server(music_service=MusicServiceType.MOCK).app)


@pytest.fixture(autouse=True)
def _clear_sessions() -> Iterator[None]:
    yield
    game_session_manager.sessions.clear()


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
def get_session() -> Callable[[str], GameSession]:
    def get(session_name: str) -> GameSession:
        session = game_session_manager.get_game_session(session_name)
        assert session is not None
        return session

    return get
