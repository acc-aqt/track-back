import json
import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from track_back.music_service.selection import MusicServiceType
from track_back.server.server import Server


def test_root_serves_the_web_ui(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<script src="script.js"' in response.text


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/script.js", "javascript"),
        ("/server-client.js", "javascript"),
        ("/screen.js", "javascript"),
        ("/round-flow.js", "javascript"),
        ("/host-options.js", "javascript"),
        ("/names.js", "javascript"),
        ("/storage.js", "javascript"),
        ("/style.css", "text/css"),
        ("/dummy-cover/cover1.webp", "image/webp"),
        ("/assets/logo.svg", "image/svg+xml"),
        ("/assets/favicon.png", "image/png"),
        ("/vendor/sortablejs/Sortable.min.js", "javascript"),
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


@pytest.mark.parametrize(
    ("base_url", "expected_server_url"),
    [
        ("http://localhost:4200", "http://localhost:4200"),
        ("http://192.168.1.5:8000", "http://192.168.1.5:8000"),
        ("https://trackback.example.org", "https://trackback.example.org"),
    ],
)
def test_server_config_points_the_web_ui_at_the_requesting_origin(
    base_url: str, expected_server_url: str
) -> None:
    client = TestClient(
        Server(music_service=MusicServiceType.MOCK).app, base_url=base_url
    )
    response = client.get("/server_config.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    match = re.fullmatch(
        r"window\.TRACK_BACK_CONFIG = (\{.*\});\s*", response.text, re.DOTALL
    )
    assert match is not None
    assert json.loads(match.group(1)) == {
        "TRACK_BACK_SERVER_URL": expected_server_url,
        "NAME_PATTERN": r"^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$",
        "USERNAME_MAX_LENGTH": 20,
        "SESSION_NAME_MAX_LENGTH": 40,
    }
