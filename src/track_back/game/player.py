"""Contains the Player class."""

from track_back.game.song import Song


class Player:
    """Represents a player with a name and a timeline of songs."""

    def __init__(self, name: str, *, is_connected: bool = True) -> None:
        """Player has a name and a timeline (release year ascending)."""
        self.name = name
        self.timeline: list[Song] = []
        self.is_connected = is_connected

    def add_to_timeline(self, index: int, song: Song) -> None:
        """Add a song to the player's timeline."""
        self.timeline.insert(index, song)
