"""Defines the MusicServiceFactory class."""

from .abstract_adapter import AbstractMusicServiceAdapter
from .apple_music import AppleMusicAdapter
from .spotify import SpotifyAdapter


class MusicServiceError(Exception):
    """Base class for exceptions in this module."""


class MusicServiceFactory:
    """Creates music service adapters based on the provided name."""

    @staticmethod
    def create_music_provider(
        provider_name: str,
    ) -> AbstractMusicServiceAdapter:
        """Create a music service adapter based on the provided name."""
        if provider_name == "spotify":
            return SpotifyAdapter()

        if provider_name == "applemusic":
            return AppleMusicAdapter()

        raise MusicServiceError(f"Invalid music service: '{provider_name}'")
