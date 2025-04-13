
from backend.game.song import Song

from .abstract_adapter import AbstractMusicServiceAdapter


class DummyMusicService(AbstractMusicServiceAdapter):
    def __init__(self):
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
        self.current_index = 0

    def current_song(self) -> Song:
        return self.playlist[self.current_index]

    def start_playback(self) -> None:
        self.current_index = 0

    def next_track(self) -> None:
        self.current_index += 1
        if self.current_index >= len(self.playlist):
            self.current_index = 0  # Loop back around
