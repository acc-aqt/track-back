"""Contains a mock music service for testing purposes."""

from backend.game.song import Song

from .abstract_adapter import AbstractMusicServiceAdapter


class DummyMusicService(AbstractMusicServiceAdapter):
    """Mock music service for testing purposes."""
    def __init__(self) -> None:
        self.playlist: list[Song] = [
            Song(title="Yesterday", artist="The Beatles", release_year=1965),
            Song(title="Bohemian Rhapsody", artist="Queen", release_year=1975),
            Song(
                title="Smells Like Teen Spirit",
                artist="Nirvana",
                release_year=1991,
            ),
            Song(
                title="Rolling in the Deep", artist="Adele", release_year=2010
            ),
            Song(title="Bad Guy", artist="Billie Eilish", release_year=2019),
            Song(
                title="Drivers License",
                artist="Olivia Rodrigo",
                release_year=2021,
            ),
        ]
        self.playlist_index = 0

    def current_song(self) -> Song:
        """Return the currently playing song."""
        return self.playlist[self.playlist_index]

    def start_playback(self) -> None:
        """Reset the playlist index to start playback."""
        self.playlist_index = 0

    def next_track(self) -> None:
        """Increment the playlist index to skip to the next track."""
        self.playlist_index += 1
        if self.playlist_index >= len(self.playlist):
            self.playlist_index = 0  # Loop back around
