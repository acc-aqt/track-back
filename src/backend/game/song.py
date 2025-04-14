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

    def serialize(self) -> dict[str, str]:
        """Serialize the song to a dictionary."""
        return {
            "title": self.title,
            "artist": self.artist,
            "release_year": str(self.release_year),
        }
def deserialize_song(data: dict[str, str]) -> Song:
    """Deserialize the song from a dictionary."""
    return Song(
        title=data["title"],
        artist=data["artist"],
        release_year=int(data["release_year"]),
        )
