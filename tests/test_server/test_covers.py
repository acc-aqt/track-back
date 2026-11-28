import pytest
from fastapi.testclient import TestClient

from track_back.music_service.covers import CoverStore
from track_back.music_service.selection import MusicServiceType
from track_back.server.server import Server


@pytest.fixture
def covers() -> CoverStore:
    return CoverStore()


@pytest.fixture
def client(covers: CoverStore) -> TestClient:
    server = Server(music_service=MusicServiceType.MOCK, cover_store=covers)
    return TestClient(server.app)


def test_stored_cover_is_served_as_jpeg(client: TestClient, covers: CoverStore) -> None:
    cover_id = covers.add(b"\xff\xd8 fake jpeg bytes")

    response = client.get(f"/covers/{cover_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"\xff\xd8 fake jpeg bytes"


def test_unknown_cover_is_not_found(client: TestClient) -> None:
    response = client.get("/covers/does-not-exist")

    assert response.status_code == 404
