from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


def test_root_serves_the_web_ui(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<script src="script.js"' in response.text


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/script.js", "javascript"),
        ("/style.css", "text/css"),
        ("/dummy-cover/cover1.webp", "image/webp"),
    ],
)
def test_web_ui_assets_load_from_the_server(
    client: TestClient, path: str, content_type: str
) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


def test_api_routes_take_precedence_over_the_web_ui(client: TestClient) -> None:
    response = client.get("/list-sessions")
    assert response.json() == {"sessions": []}


def test_websocket_endpoint_takes_precedence_over_the_web_ui(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    create_and_join("g1", "alice")
    with client.websocket_connect("/ws/g1/alice") as ws:
        assert ws.receive_json()["type"] == "welcome"
