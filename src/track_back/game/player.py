"""Contains the Player class."""

from track_back.game.song import Song


class Player:
    """Represents a player with a name and a timeline of songs."""

    def __init__(self, name: str) -> None:
        """Player has name and song list (release year ascending)."""
        self.name = name
        self.song_list: list[Song] = []
        self.is_connected = True

    def add_song(self, index: int, song: Song) -> None:
        """Add a song to the song_list of the player."""
        self.song_list.insert(index, song)

    def serialize(self) -> dict[str, str | list[dict[str, str | int]]]:
        """Serialize the player to a dictionary."""
        return {
            "name": self.name,
            "song_list": [song.serialize() for song in self.song_list],
        }
