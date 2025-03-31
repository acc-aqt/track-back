"""Contains the TrackBackGame class that implements the game logic."""

from game.user import User
from music_providers.abstract_music_provider import AbstractMusicProvider


class TrackBackGame:
    """Implements the game logic."""

    def __init__(self, users, target_song_count: int, music_provider: AbstractMusicProvider):
        self.music_provider = music_provider
        self.users = users
        self.target_song_count = target_song_count
        self.round_counter = 0
        self.finished = False

    def run(self):
        """Runs the game."""
        while True:
            self.round_counter += 1
            print(f"Round {self.round_counter}")
            for user in self.users:
                self._process_user_turn(user)
                if self.finished:
                    return

    def _process_user_turn(self, user: User):
        print(f"\n\nIt's {user.name}'s turn. Current Songlist:")
        user.print_song_list()
        input_index = user.get_valid_index_by_input()

        current_song = self.music_provider.current_song()

        if not user.song_list:
            user.song_list.append(current_song)
        elif input_index == 0 and current_song.release_year < user.song_list[0].release_year:
            print(f"Correct! Song was {current_song}")
            user.song_list.insert(0, current_song)
        elif (
            input_index == -1 or input_index == len(user.song_list)
        ) and current_song.release_year > user.song_list[-1].release_year:
            print(f"Correct! Song was {current_song}")
            user.song_list.append(current_song)
        elif (
            0 < input_index < len(user.song_list)
            and user.song_list[input_index - 1].release_year
            > current_song.release_year
            > user.song_list[input_index].release_year
        ):
            print(f"Correct! Song was {current_song}")
            user.song_list.insert(input_index, current_song)
        else:
            print(f"Wrong! Song was {current_song}")

        self.music_provider.next_track()

        if len(user.song_list) == self.target_song_count:
            print(f"{user.name} wins!")
            self.finished = True
