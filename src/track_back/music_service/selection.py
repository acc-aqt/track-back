"""Decides which Music Services the server can use and maps them to adapters."""

import os
import sys
from collections.abc import Callable
from enum import StrEnum

from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.apple_music import AppleMusicAdapter
from track_back.music_service.mock import MockMusicService
from track_back.music_service.spotify import SpotifyAdapter


class MusicServiceType(StrEnum):
    """Music services a game can be created with."""

    SPOTIFY = "spotify"
    APPLE_MUSIC = "applemusic"
    MOCK = "mock"


MUSIC_SERVICES: dict[MusicServiceType, Callable[[], AbstractMusicServiceAdapter]] = {
    MusicServiceType.SPOTIFY: SpotifyAdapter,
    MusicServiceType.APPLE_MUSIC: AppleMusicAdapter,
    MusicServiceType.MOCK: MockMusicService,
}


def default_music_service() -> MusicServiceType:
    """Return the Music Service used when the Server Operator chooses none."""
    if sys.platform == "darwin":
        return MusicServiceType.APPLE_MUSIC
    return MusicServiceType.SPOTIFY


SPOTIFY_CREDENTIAL_VARIABLES = (
    "SPOTIPY_CLIENT_ID",
    "SPOTIPY_CLIENT_SECRET",
    "SPOTIPY_REDIRECT_URI",
)


def available_music_services(chosen: MusicServiceType) -> list[MusicServiceType]:
    """Return the Music Services that can work on this server.

    Parameters
    ----------
    chosen : MusicServiceType
        The server's Music Service. The Mock Music Service is only available when
        it is the chosen one.

    Returns
    -------
    list[MusicServiceType]
        Apple Music on macOS, Spotify when all its credentials are set, and Mock
        when chosen, in ``MusicServiceType`` order.
    """
    usable = {
        MusicServiceType.SPOTIFY: all(
            os.environ.get(name) for name in SPOTIFY_CREDENTIAL_VARIABLES
        ),
        MusicServiceType.APPLE_MUSIC: sys.platform == "darwin",
        MusicServiceType.MOCK: chosen == MusicServiceType.MOCK,
    }
    return [service for service in MusicServiceType if usable[service]]
