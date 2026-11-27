from fastapi.testclient import TestClient

from track_back.music_service.covers import cover_store


def test_stored_cover_is_served_as_jpeg(client: TestClient) -> None:
    cover_id = cover_store.add(b"\xff\xd8 fake jpeg bytes")

    response = client.get(f"/covers/{cover_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"\xff\xd8 fake jpeg bytes"


def test_unknown_cover_is_not_found(client: TestClient) -> None:
    response = client.get("/covers/does-not-exist")

    assert response.status_code == 404
