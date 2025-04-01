"""Defines the MusicProviderFactory class."""

from music_providers.spotify import SpotifyClient
from music_providers.apple_music import AppleMusicClient
from music_providers.abstract_music_provider import AbstractMusicProvider


class MusicProvicerException(Exception):
    """Base class for exceptions in this module."""


class MusicProviderFactory:
    """Creates music providers based on the provider name."""

    @staticmethod
    def create_music_provider(provider: str) -> AbstractMusicProvider:
        """Creates a music provider based on the provider name."""
        if provider == "spotify":
            return SpotifyClient()
        
        if provider == "applemusic":
            return AppleMusicClient()

        raise MusicProvicerException(f"Invalid music provider: '{music_provider}'")
