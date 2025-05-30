"""Defines the interface for music services."""

from abc import ABC, abstractmethod

from game.song import Song


class AbstractMusicServiceAdapter(ABC):
    """Abstract base class that defines the interface for a music service."""

    service_name: str

    @abstractmethod
    def current_song(self) -> Song:
        """Return the currently playing song."""

    @abstractmethod
    def start_playback(self) -> None:
        """Start playing the music."""

    @abstractmethod
    def next_track(self) -> None:
        """Skip to the next track."""
