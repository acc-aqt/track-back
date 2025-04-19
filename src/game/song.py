"""Contains a class representing a song."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Song:
    """Represents a song with title, artist and release year."""

    title: str
    artist: str
    release_year: int
    album_cover_url: str = ""

    def __str__(self) -> str:
        """Return a string representation of the song's metadata."""
        return f"'{self.title}' by {self.artist} ({self.release_year})"

    def serialize(self) -> dict[str, str]:
        """Serialize the song to a dictionary."""
        return asdict(self)


def deserialize_song(data: dict[str, Any]) -> Song:
    """Deserialize the song from a dictionary."""
    return Song(**data)
