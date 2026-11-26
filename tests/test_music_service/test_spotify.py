import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from music_service import spotify
from music_service.error import MusicServiceError
from music_service.spotify import SpotifyAdapter
from server.game_sessions import game_session_manager
from server.server import Server


class FakeSpotify:
    def __init__(self, playback: dict[str, Any] | None) -> None:
        self._playback = playback

    def current_playback(self) -> dict[str, Any] | None:
        return self._playback


def _adapter_with(playback: dict[str, Any] | None) -> SpotifyAdapter:
    adapter = SpotifyAdapter()
    adapter.session = FakeSpotify(playback)  # type: ignore[assignment]
    return adapter


def test_current_song_without_active_device_raises_music_service_error():
    with pytest.raises(MusicServiceError):
        _adapter_with(None).current_song()


def test_current_song_without_item_raises_music_service_error():
    with pytest.raises(MusicServiceError):
        _adapter_with({"is_playing": True, "item": None}).current_song()


def test_current_song_reads_track_metadata():
    playback = {
        "is_playing": True,
        "item": {
            "name": "Yesterday",
            "artists": [{"name": "The Beatles"}],
            "album": {
                "release_date": "1965-08-06",
                "images": [{"url": "big.jpg"}, {"url": "small.jpg"}],
            },
        },
    }
    song = _adapter_with(playback).current_song()
    assert (song.title, song.artist, song.release_year, song.album_cover_url) == (
        "Yesterday",
        "The Beatles",
        1965,
        "small.jpg",
    )


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
    monkeypatch.setattr(spotify, "get_spotify_oauth", FakeOAuth)
    monkeypatch.setattr(spotify.spotipy, "Spotify", FakeSpotifyProfile)
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
