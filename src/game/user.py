"""Contains the user class."""

from game.song import Song


class User:
    """Represents a user with a name and a list of songs."""

    def __init__(self, name: str):
        self.name = name
        self.song_list = []

    def print_song_list(self) -> None:
        """Prints the song list of the user."""
        for index, song in enumerate(self.song_list):
            print(f"{index} : {song.release_year} | '{song.title}' by {song.artist}")

    def add_song(self, index: int, song: Song) -> None:
        """Adds a song to the song_list of the user."""
        self.song_list.insert(index if index != -1 else len(self.song_list), song)

    def get_index_by_input(self) -> int:
        """Gets a valid index from the user by input."""
        while True:
            input_index = input(
                "\nEnter the index in front of which the song shall be added. "
                "(0 for the first song, -1 for the last song): "
            )
            try:
                input_index = int(input_index)
                if -1 <= input_index <= len(self.song_list):
                    return input_index
                print("Please enter a valid index.")
            except ValueError:
                print("Please enter a valid index.")


def get_users() -> list[User]:
    """Asks for input of user names and return a list of User objects."""
    users = []
    while True:
        user_name = input("Enter the name of the user (if empty, continue to play): ")
        if user_name.strip() == "":
            break
        users.append(User(user_name))

    if not users:
        users = [User("Noname")]

    return users
