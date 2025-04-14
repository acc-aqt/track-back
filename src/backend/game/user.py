"""Contains the user class."""


from .song import Song
from .utils import get_user_input


class User:
    """Represents a user with a name and a list of songs."""

    def __init__(self, name: str) -> None:
        """User has name and song list (release year ascending)."""
        self.name = name
        self.song_list = []  # type: list[Song]

    def print_song_list(self) -> None:
        """Print the song list of the user."""
        for index, song in enumerate(self.song_list):
            print(f"{index} : {song.release_year} | '{song.title}' by {song.artist}")

    def add_song(self, index: int, song: Song) -> None:
        """Add a song to the song_list of the user."""
        self.song_list.insert(index, song)

    def get_index_by_input(self) -> int:
        """Get a valid index from the user by input."""
        while True:
            raw_input_index = get_user_input(
                f"\nEnter the index in front of which the song shall be added."
                f"\n0 -> sort in as first song; "
                f"{len(self.song_list)} -> sort in as last song: "
            )
            try:
                input_index = int(raw_input_index)
                if 0 <= input_index <= len(self.song_list):
                    return input_index
                print("Please enter a valid index.")
            except ValueError:
                print("Please enter a valid index.")


def get_users() -> list[User]:
    """Ask for input of user names and return a list of User objects."""
    users: list[User] = []
    while True:
        user_name = get_user_input(
            f"Enter the name of user #{len(users) + 1} (if empty, continue to play): "
        )
        if user_name.strip() == "":
            break
        users.append(User(user_name))

    return users or [User("Anonymous")]
