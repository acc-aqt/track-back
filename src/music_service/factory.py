"""Defines the MusicServiceFactory class."""

from music_service.abstract_adapter import AbstractMusicServiceAdapter
from music_service.apple_music import AppleMusicAdapter
from music_service.mock import DummyMusicService
from music_service.spotify import SpotifyAdapter


class MusicServiceError(Exception):
    """Base class for exceptions in this module."""


class MusicServiceFactory:
    """Creates music service adapters based on the provided name."""

    @staticmethod
    def create_music_service(
        provider_name: str,
    ) -> AbstractMusicServiceAdapter:
        """Create a music service adapter based on the provided name."""
        if provider_name == "spotify":
            return SpotifyAdapter()

        if provider_name == "applemusic":
            return AppleMusicAdapter()

        if provider_name == "mock":
            return DummyMusicService()

        raise MusicServiceError(f"Invalid music service: '{provider_name}'")
