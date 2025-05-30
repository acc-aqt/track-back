"""Contains a mock music service for testing purposes."""

from game.song import Song
from music_service.abstract_adapter import AbstractMusicServiceAdapter


class DummyMusicService(AbstractMusicServiceAdapter):
    """Mock music service for testing purposes."""

    service_name = "Dummy Music Service"

    def __init__(self) -> None:
        self.playlist: list[Song] = [
            Song(title="Yesterday", artist="The Beatles", release_year=1965),
            Song(title="Bohemian Rhapsody", artist="Queen", release_year=1975),
            Song(
                title="Smells Like Teen Spirit",
                artist="Nirvana",
                release_year=1991,
            ),
            Song(title="Rolling in the Deep", artist="Adele", release_year=2010),
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
        """Skip to next track. Songs are orderer by release year."""
        self.playlist_index += 1
        if self.playlist_index >= len(self.playlist):
            self.playlist_index = 0  # Loop back around
