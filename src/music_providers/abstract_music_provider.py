"""Defines the interface for AbstractMusicProvider."""

from abc import ABC, abstractmethod

from game.song import Song


class AbstractMusicProvider(ABC):
    """Abstract base class that defines the interface for a music provider."""

    @abstractmethod
    def current_song(self) -> Song:
        """Returns the currently playing song."""

    @abstractmethod
    def start_playback(self) -> None:
        """Starts playing the music."""

    @abstractmethod
    def next_track(self) -> None:
        """Skips to the next track."""
