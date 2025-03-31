"""Contains a class that represents a song with title, artist and release year."""

from dataclasses import dataclass


@dataclass
class Song:
    """Represents a song with title, artist and release year."""

    title: str
    artist: str
    release_year: int

    def __str__(self):
        return f"'{self.title}' by {self.artist} ({self.release_year})"
