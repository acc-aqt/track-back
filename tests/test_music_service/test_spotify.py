from typing import Any

import pytest
from spotipy.exceptions import SpotifyException

from track_back.music_service.error import MusicServiceError
from track_back.music_service.spotify import SpotifyAdapter


class FakeSpotify:
    def __init__(self, playback: dict[str, Any] | None) -> None:
        self._playback = playback

    def current_playback(self) -> dict[str, Any] | None:
        return self._playback


class UnreachableSpotify:
    """A Spotify client whose every request fails, like one with no active device."""

    def _fail(self) -> None:
        raise SpotifyException(404, -1, "Player command failed: No active device found")

    def current_playback(self) -> None:
        self._fail()

    def next_track(self) -> None:
        self._fail()


def _adapter_with(playback: dict[str, Any] | None) -> SpotifyAdapter:
    return SpotifyAdapter(FakeSpotify(playback))


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


def test_failed_skip_raises_music_service_error() -> None:
    with pytest.raises(MusicServiceError, match="No active device"):
        SpotifyAdapter(UnreachableSpotify()).next_track()


def test_failed_playback_read_raises_music_service_error() -> None:
    with pytest.raises(MusicServiceError, match="No active device"):
        SpotifyAdapter(UnreachableSpotify()).current_song()
