"""Spotify login and callback routes, with Spotify OAuth patched out."""

import json
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from server import spotify_login
from server.game_sessions import game_session_manager
from server.server import Server


class FakeOAuth:
    def get_access_token(self, _code: str) -> dict[str, str]:
        return {"access_token": "token"}


class FakeSpotifyProfile:
    def __init__(self, auth: str) -> None:
        self.auth = auth

    def current_user(self) -> dict[str, str]:
        return {"id": "<script>alert(1)</script>"}


@pytest.fixture
def callback_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(spotify_login, "get_spotify_oauth", FakeOAuth)
    monkeypatch.setattr(spotify_login.spotipy, "Spotify", FakeSpotifyProfile)
    yield TestClient(Server().app)
    game_session_manager.sessions.clear()


def test_callback_escapes_spotify_user_id(callback_client: TestClient):
    state = json.dumps({"game_id": "spotify-game", "target_song_count": 3})
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert game_session_manager.get_game_session("spotify-game") is not None


def test_callback_rejects_invalid_game_id(callback_client: TestClient):
    state = json.dumps({"game_id": "<b>x</b>", "target_song_count": 3})
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 400
    assert game_session_manager.sessions == {}


@pytest.mark.parametrize("target_song_count", [0, -1, "zero"])
def test_callback_rejects_target_song_count_below_one(
    callback_client: TestClient, target_song_count: object
):
    state = json.dumps(
        {"game_id": "spotify-game", "target_song_count": target_song_count}
    )
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 400
    assert game_session_manager.sessions == {}


def test_login_asks_only_for_playback_permissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Spotify login requests playback scopes and no library access."""
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://localhost/spotify-callback")
    client = TestClient(Server().app)

    response = client.get("/spotify-login", follow_redirects=False)

    scopes = parse_qs(urlparse(response.headers["location"]).query)["scope"][0]
    assert set(scopes.split()) == {
        "user-read-playback-state",
        "user-modify-playback-state",
    }
