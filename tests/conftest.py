from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from track_back.server.game_sessions import GameSession, game_session_manager
from track_back.server.server import Server

CreateGame = Callable[[str], None]
CreateAndJoin = Callable[..., None]


@pytest.fixture
def client() -> TestClient:
    return TestClient(Server().app)


@pytest.fixture(autouse=True)
def _clear_sessions() -> Iterator[None]:
    yield
    game_session_manager.sessions.clear()


@pytest.fixture
def create_game(client: TestClient) -> CreateGame:
    def create(game_id: str) -> None:
        response = client.post(
            "/create",
            json={
                "game_id": game_id,
                "target_song_count": 2,
                "music_service_type": "mock",
            },
        )
        assert response.status_code == 201

    return create


@pytest.fixture
def create_and_join(client: TestClient, create_game: CreateGame) -> CreateAndJoin:
    def create_and_join(game_id: str, *user_names: str) -> None:
        create_game(game_id)
        for user_name in user_names:
            response = client.post(
                "/join", json={"game_id": game_id, "user_name": user_name}
            )
            assert response.status_code == 200

    return create_and_join


@pytest.fixture
def get_session() -> Callable[[str], GameSession]:
    def get(game_id: str) -> GameSession:
        session = game_session_manager.get_game_session(game_id)
        assert session is not None
        return session

    return get
