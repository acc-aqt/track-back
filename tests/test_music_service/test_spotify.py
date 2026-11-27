from typing import Any

import pytest

from track_back.music_service.error import MusicServiceError
from track_back.music_service.spotify import SpotifyAdapter


class FakeSpotify:
    def __init__(self, playback: dict[str, Any] | None) -> None:
        self._playback = playback

    def current_playback(self) -> dict[str, Any] | None:
        return self._playback


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
