import json
from typing import Any

import pytest
import spotipy
from fastapi.testclient import TestClient

from music_service import spotify
from music_service.error import MusicServiceError
from music_service.spotify import SpotifyAdapter
from server.game_sessions import game_session_manager


class FakeSpotify:
    def __init__(self, playback: dict[str, Any] | None) -> None:
        self._playback = playback

    def current_playback(self) -> dict[str, Any] | None:
        return self._playback


def _adapter_with(playback: dict[str, Any] | None) -> SpotifyAdapter:
    adapter = SpotifyAdapter()
    adapter.session = FakeSpotify(playback)
    return adapter


def test_current_song_without_active_device_raises_music_service_error() -> None:
    with pytest.raises(MusicServiceError):
        _adapter_with(None).current_song()


def test_current_song_without_item_raises_music_service_error() -> None:
    with pytest.raises(MusicServiceError):
        _adapter_with({"is_playing": True, "item": None}).current_song()


def test_current_song_reads_track_metadata() -> None:
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
def callback_client(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> TestClient:
    monkeypatch.setattr(spotify, "get_spotify_oauth", FakeOAuth)
    monkeypatch.setattr(spotipy, "Spotify", FakeSpotifyProfile)
    return client


def test_callback_escapes_spotify_user_id(callback_client: TestClient) -> None:
    state = json.dumps({"game_id": "spotify-game", "target_song_count": 3})
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert game_session_manager.get_game_session("spotify-game") is not None


def test_callback_rejects_invalid_game_id(callback_client: TestClient) -> None:
    state = json.dumps({"game_id": "<b>x</b>", "target_song_count": 3})
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 400
    assert game_session_manager.sessions == {}
