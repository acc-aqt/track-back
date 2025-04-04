"""Contains the TrackBackGame class that implements the game logic."""

from music_providers.abstract_music_provider import AbstractMusicProvider

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
        music_provider: AbstractMusicProvider,
    ) -> None:
        self.music_provider = music_provider
        self.target_song_count = target_song_count
        self.users = users
        self.round_counter = 0

    def run(self) -> None:
        """Run the game."""
        while True:
            self.round_counter += 1
            print(f"Round {self.round_counter}")
            for user in self.users:
                self._process_user_turn(user)
                self.music_provider.next_track()

                if len(user.song_list) == self.target_song_count:
                    user.print_song_list()
                    print(f"{user.name} wins!")
                    return

    def _process_user_turn(self, user: User) -> None:
        print(f"\n\nIt's {user.name}'s turn. Current song list:")
        user.print_song_list()

        input_index = user.get_index_by_input()
        current_song = self.music_provider.current_song()

        if self.verify_choice(user.song_list, input_index, current_song):
            print(f"✅ Correct! Song was {current_song}")
            user.add_song(input_index, current_song)
        else:
            print(f"❌ Wrong! Song was {current_song}")

    def verify_choice(
        self, song_list: list[Song], index: int, selected_song: Song
    ) -> bool:
        """Return True if the selected song is valid for the index."""
        if not song_list:  # handle empty list case
            return True
        if index == 0:  # handle first song case
            return selected_song.release_year < song_list[0].release_year
        if index == -1 or index == len(song_list):  # handle last song case
            return selected_song.release_year > song_list[-1].release_year
        if 0 < index < len(song_list):
            return (
                song_list[index - 1].release_year
                <= selected_song.release_year
                <= song_list[index].release_year
            )
        raise TrackBackGameError(
            "Error in game logic! Invalid index provided!"
        )
