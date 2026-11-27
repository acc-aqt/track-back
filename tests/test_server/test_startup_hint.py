from unittest import mock

import pytest

from track_back.music_service.selection import MusicServiceType
from track_back.server.server import Server


def run_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], port: int
) -> str:
    monkeypatch.setattr("uvicorn.Server.run", mock.MagicMock())
    Server(music_service=MusicServiceType.MOCK).run(port=port)
    return capsys.readouterr().out


@pytest.fixture(autouse=True)
def no_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSL_KEYFILE", raising=False)
    monkeypatch.delenv("SSL_CERTFILE", raising=False)


def set_lan_addresses(monkeypatch: pytest.MonkeyPatch, addresses: list[str]) -> None:
    monkeypatch.setattr(
        "track_back.server.network.lan_ipv4_addresses", lambda: addresses
    )


def test_prints_localhost_url_when_no_lan_addresses(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_lan_addresses(monkeypatch, [])

    out = run_server(monkeypatch, capsys, port=4321)

    assert out == "Open http://localhost:4321 on this machine.\n"


@pytest.mark.parametrize(
    ("addresses", "expected"),
    [
        (
            ["192.168.1.23"],
            (
                "Open http://localhost:4200 on this machine, "
                "or http://192.168.1.23:4200 on other devices.\n"
            ),
        ),
        (
            ["192.168.1.23", "10.0.0.5"],
            (
                "Open http://localhost:4200 on this machine, "
                "or http://192.168.1.23:4200 or http://10.0.0.5:4200 on other devices.\n"
            ),
        ),
    ],
)
def test_prints_one_url_per_lan_address(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    addresses: list[str],
    expected: str,
) -> None:
    set_lan_addresses(monkeypatch, addresses)

    out = run_server(monkeypatch, capsys, port=4200)

    assert out == expected


@pytest.mark.parametrize(
    ("ssl_env", "scheme"),
    [
        ({"SSL_KEYFILE": "key.pem", "SSL_CERTFILE": "cert.pem"}, "https"),
        ({"SSL_KEYFILE": "key.pem"}, "http"),
        ({"SSL_CERTFILE": "cert.pem"}, "http"),
    ],
)
def test_url_scheme_follows_ssl_config(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ssl_env: dict[str, str],
    scheme: str,
) -> None:
    for name, value in ssl_env.items():
        monkeypatch.setenv(name, value)
    set_lan_addresses(monkeypatch, ["192.168.1.23"])

    out = run_server(monkeypatch, capsys, port=4200)

    assert out == (
        f"Open {scheme}://localhost:4200 on this machine, "
        f"or {scheme}://192.168.1.23:4200 on other devices.\n"
    )


def test_lan_discovery_failure_still_prints_localhost_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail() -> list[str]:
        raise OSError("network unavailable")

    monkeypatch.setattr("track_back.server.network.lan_ipv4_addresses", fail)

    out = run_server(monkeypatch, capsys, port=4200)

    assert out == "Open http://localhost:4200 on this machine.\n"
