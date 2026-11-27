"""Describes each Music Service: whether it can work here and how to build it."""

import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.apple_music import AppleMusicAdapter
from track_back.music_service.mock import MockMusicService


class MusicServiceType(StrEnum):
    """Music services a game can be created with."""

    SPOTIFY = "spotify"
    APPLE_MUSIC = "applemusic"
    MOCK = "mock"


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


@dataclass(frozen=True)
class MusicServiceDescription:
    """Everything the server needs to know about one Music Service.

    Attributes
    ----------
    can_work : Callable[[], bool]
        Whether the Music Service can work on this server (platform, credentials).
    unavailable_hint : str
        What the Server Operator can do when it can't work here.
    build : Callable[[], AbstractMusicServiceAdapter] | None
        Builds a ready adapter for a new Game Session, or None when Game Sessions
        with this Music Service are only created through its login.
    login_hint : str
        Where a Host creates Game Sessions with a Music Service that has no
        ``build``.
    """

    can_work: Callable[[], bool]
    unavailable_hint: str
    build: Callable[[], AbstractMusicServiceAdapter] | None
    login_hint: str = ""


def _spotify_credentials_are_set() -> bool:
    return all(os.environ.get(name) for name in SPOTIFY_CREDENTIAL_VARIABLES)


def _running_on_macos() -> bool:
    return sys.platform == "darwin"


MUSIC_SERVICES: dict[MusicServiceType, MusicServiceDescription] = {
    MusicServiceType.SPOTIFY: MusicServiceDescription(
        can_work=_spotify_credentials_are_set,
        unavailable_hint="Spotify needs credentials: "
        "run `track-back-server init` to add them.",
        build=None,
        login_hint="Spotify Game Sessions are created by logging in to Spotify "
        "at /spotify-login.",
    ),
    MusicServiceType.APPLE_MUSIC: MusicServiceDescription(
        can_work=_running_on_macos,
        unavailable_hint="Apple Music needs macOS and the Music app: "
        "try --music-service spotify.",
        build=AppleMusicAdapter,
    ),
    MusicServiceType.MOCK: MusicServiceDescription(
        can_work=lambda: True,
        unavailable_hint="",
        build=MockMusicService,
    ),
}


def available_music_services(
    chosen: MusicServiceType,
    music_services: Mapping[MusicServiceType, MusicServiceDescription] = MUSIC_SERVICES,
) -> list[MusicServiceType]:
    """Return the Music Services that can work on this server.

    Parameters
    ----------
    chosen : MusicServiceType
        The server's Music Service. The Mock Music Service is only available when
        it is the chosen one.
    music_services : Mapping[MusicServiceType, MusicServiceDescription]
        The description of each Music Service.

    Returns
    -------
    list[MusicServiceType]
        The Music Services whose description says they can work here, without
        Mock unless chosen, in ``MusicServiceType`` order.
    """
    return [
        service
        for service in MusicServiceType
        if music_services[service].can_work()
        and (service != MusicServiceType.MOCK or chosen == MusicServiceType.MOCK)
    ]
