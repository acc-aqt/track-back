"""Contains the user class."""

from game.song import Song


class User:
    """Represents a user with a name and a list of songs."""

    def __init__(self, name: str) -> None:
        """User has name and song list (release year ascending)."""
        self.name = name
        self.song_list = []  # type: list[Song]

    def add_song(self, index: int, song: Song) -> None:
        """Add a song to the song_list of the user."""
        self.song_list.insert(index, song)

    def serialize(self) -> dict[str, str | list[dict[str, str]]]:
        """Serialize the user object to a dictionary."""
        return {
            "name": self.name,
            "song_list": [song.serialize() for song in self.song_list],
        }
