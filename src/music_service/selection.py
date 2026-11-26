"""Maps the music services a client can choose to their adapters."""

from collections.abc import Callable
from enum import StrEnum

from music_service.abstract_adapter import AbstractMusicServiceAdapter
from music_service.apple_music import AppleMusicAdapter
from music_service.mock import DummyMusicService
from music_service.spotify import SpotifyAdapter


class MusicServiceType(StrEnum):
    """Music services a game can be created with."""

    SPOTIFY = "spotify"
    APPLE_MUSIC = "applemusic"
    MOCK = "mock"


MUSIC_SERVICES: dict[MusicServiceType, Callable[[], AbstractMusicServiceAdapter]] = {
    MusicServiceType.SPOTIFY: SpotifyAdapter,
    MusicServiceType.APPLE_MUSIC: AppleMusicAdapter,
    MusicServiceType.MOCK: DummyMusicService,
}
