"""Contains a class representing a song."""

from dataclasses import dataclass


@dataclass
class Song:
    """Represents a song with title, artist and release year."""

    title: str
    artist: str
    release_year: int

    def __str__(self) -> str:
        """Return a string representation of the song's metadata."""
        return f"'{self.title}' by {self.artist} ({self.release_year})"
