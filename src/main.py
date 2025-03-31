"""Entry point to start the track-back server."""

from dotenv import load_dotenv
import tomllib
from music_providers.factory import MusicProviderFactory
from music_providers.abstract_music_provider import AbstractMusicProvider
from user import User
from song import Song


class TrackBackException(Exception):
    """Base class for exceptions in this module."""


class TrackBackGame:
    """Handles the game session."""

    def __init__(self, users, target_history_length: int, music_provider: AbstractMusicProvider):
        self.music_provider = music_provider
        self.users = users
        self.target_history_length = target_history_length
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

        if len(user.song_list) == self.target_history_length:
            print(f"{user.name} wins!")
            self.finished = True


def get_users():
    """Gets the user names by input."""
    users = []
    while True:
        user_name = input("Enter the name of the user (if empty, continue to play): ")
        if user_name.strip() == "":
            break
        users.append(User(user_name))

    if not users:
        users = [User("Noname")]

    return users


def load_config(path="config.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


def main():
    """Main entry point to start the game."""
    load_dotenv()

    target_history_length = 2

    config = load_config()
    provider = config.get("music_provider")
    music_provider = MusicProviderFactory.create_music_provider(provider)
    music_provider.start_playback()

    users = get_users()

    game = TrackBackGame(
        users=users, target_history_length=target_history_length, music_provider=music_provider
    )
    game.run()


if __name__ == "__main__":
    main()
