"""Contains the TrackBackGame class that implements the game logic."""

from itertools import pairwise

from music_service.abstract_adapter import AbstractMusicServiceAdapter

from .song import Song
from .user import User


class TrackBackGameError(Exception):
    """Base class for exceptions in this module."""


class TrackBackGame:
    """Implements the game logic."""

    def __init__(
        self,
        users: list[User],
        target_song_count: int,
        music_service: AbstractMusicServiceAdapter,
    ) -> None:
        self.music_service = music_service
        self.target_song_count = target_song_count
        self.users = users
        self.round_counter = 0
        self.winner: User | None = None

    def run(self) -> None:
        """Run the game."""
        while True:
            self.round_counter += 1
            print(f"Round {self.round_counter}")
            for user in self.users:
                self._process_user_turn(user)
                self.music_service.next_track()

                if len(user.song_list) == self.target_song_count:
                    self.winner = user
                    return

    def _process_user_turn(self, user: User) -> None:
        print(f"\nIt's {user.name}'s turn. Current song list:")
        user.print_song_list()

        input_index = user.get_index_by_input()
        current_song = self.music_service.current_song()

        if self.verify_choice(user.song_list, input_index, current_song):
            print(f"✅ Correct! Song was {current_song}\n")
            user.add_song(input_index, current_song)
        else:
            print(f"❌ Wrong! Song was {current_song}\n")

    @staticmethod
    def verify_choice(
        song_list: list[Song], index: int, selected_song: Song
    ) -> bool:
        """Return True if the new song list would be sorted by release year."""
        potential_list = song_list.copy()
        potential_list.insert(index, selected_song)

        return TrackBackGame._is_sorted_by_release_year(potential_list)

    @staticmethod
    def _is_sorted_by_release_year(song_list: list[Song]) -> bool:
        return all(
            earlier.release_year <= later.release_year
            for earlier, later in pairwise(song_list)
        )
