"""The Lobby QR code that opens the Web UI with a Game Session preselected."""

from collections.abc import Callable
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from track_back.music_service.selection import MusicServiceType
from track_back.server.server import Server

PORT = 4300


@pytest.fixture
def client() -> TestClient:
    return TestClient(Server(music_service=MusicServiceType.MOCK, port=PORT).app)


@pytest.fixture(autouse=True)
def no_ssl_and_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSL_KEYFILE", raising=False)
    monkeypatch.delenv("SSL_CERTFILE", raising=False)
    monkeypatch.setattr("track_back.server.network.lan_ipv4_addresses", list)


def test_join_qr_is_svg_for_existing_session(
    client: TestClient, create_game: Callable[[str], None]
) -> None:
    create_game("qr-game")

    response = client.get("/join-qr.svg", params={"session": "qr-game"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert response.text.startswith("<svg")


def test_join_qr_for_unknown_session_is_not_found(client: TestClient) -> None:
    response = client.get("/join-qr.svg", params={"session": "no-such-game"})

    assert response.status_code == 404


@pytest.mark.parametrize("session", ["<b>x</b>", "", "x" * 41])
def test_join_qr_rejects_invalid_session_name(client: TestClient, session: str) -> None:
    response = client.get("/join-qr.svg", params={"session": session})

    assert response.status_code == 422


@pytest.fixture
def encoded_urls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    urls: list[str] = []

    def fake_render_svg(url: str) -> str:
        urls.append(url)
        return "<svg/>"

    monkeypatch.setattr("track_back.server.join_qr.render_svg", fake_render_svg)
    return urls


def set_lan_addresses(monkeypatch: pytest.MonkeyPatch, addresses: list[str]) -> None:
    monkeypatch.setattr(
        "track_back.server.network.lan_ipv4_addresses", lambda: addresses
    )


@pytest.fixture
def get_join_qr(
    client: TestClient, create_game: Callable[[str], None]
) -> Callable[[str], None]:
    def get(session_name: str) -> None:
        create_game(session_name)
        response = client.get("/join-qr.svg", params={"session": session_name})
        assert response.status_code == 200

    return get


def test_join_qr_encodes_lan_join_url(
    monkeypatch: pytest.MonkeyPatch,
    encoded_urls: list[str],
    get_join_qr: Callable[[str], None],
) -> None:
    set_lan_addresses(monkeypatch, ["192.168.1.23", "10.0.0.5"])

    get_join_qr("Game-by-Ann ä")

    assert encoded_urls == [f"http://192.168.1.23:{PORT}/?join=Game-by-Ann%20%C3%A4"]


def test_join_qr_uses_https_when_ssl_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    encoded_urls: list[str],
    get_join_qr: Callable[[str], None],
) -> None:
    monkeypatch.setenv("SSL_KEYFILE", "key.pem")
    monkeypatch.setenv("SSL_CERTFILE", "cert.pem")
    set_lan_addresses(monkeypatch, ["192.168.1.23"])

    get_join_qr("secure-game")

    assert encoded_urls == [f"https://192.168.1.23:{PORT}/?join=secure-game"]


def test_join_qr_falls_back_to_localhost_without_lan_addresses(
    monkeypatch: pytest.MonkeyPatch,
    encoded_urls: list[str],
    get_join_qr: Callable[[str], None],
) -> None:
    set_lan_addresses(monkeypatch, [])

    get_join_qr("offline-game")

    assert encoded_urls == [f"http://localhost:{PORT}/?join=offline-game"]


def test_join_qr_falls_back_to_localhost_when_lan_discovery_fails(
    monkeypatch: pytest.MonkeyPatch,
    encoded_urls: list[str],
    get_join_qr: Callable[[str], None],
) -> None:
    def fail() -> list[str]:
        raise OSError("network unavailable")

    monkeypatch.setattr("track_back.server.network.lan_ipv4_addresses", fail)

    get_join_qr("offline-game")

    assert encoded_urls == [f"http://localhost:{PORT}/?join=offline-game"]


def test_join_qr_uses_the_port_the_server_runs_on(
    monkeypatch: pytest.MonkeyPatch, encoded_urls: list[str]
) -> None:
    monkeypatch.setattr("uvicorn.Server.run", mock.MagicMock())
    set_lan_addresses(monkeypatch, ["192.168.1.23"])
    server = Server(music_service=MusicServiceType.MOCK)
    server.run(port=5100)
    client = TestClient(server.app)
    client.post("/create", json={"game_id": "run-game", "target_song_count": 2})

    client.get("/join-qr.svg", params={"session": "run-game"})

    assert encoded_urls == ["http://192.168.1.23:5100/?join=run-game"]


def test_join_qr_uses_the_web_ui_colours(
    client: TestClient, create_game: Callable[[str], None]
) -> None:
    create_game("qr-game")

    svg = client.get("/join-qr.svg", params={"session": "qr-game"}).text.lower()

    assert "#1a1a2e" in svg
    assert "#8aabdb" in svg
    assert "#fff" not in svg
