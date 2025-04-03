"""Defines the MusicProviderFactory class."""

from .abstract_music_provider import AbstractMusicProvider
from .apple_music import AppleMusicClient
from .spotify import SpotifyClient


class MusicProvicerError(Exception):
    """Base class for exceptions in this module."""


class MusicProviderFactory:
    """Creates music providers based on the provider name."""

    @staticmethod
    def create_music_provider(provider_name: str) -> AbstractMusicProvider:
        """Create a music provider based on the provider name."""
        if provider_name == "spotify":
            return SpotifyClient()

        if provider_name == "applemusic":
            return AppleMusicClient()

        raise MusicProvicerError(f"Invalid music provider: '{provider_name}'")
