"""Contains the user class."""


class User:
    """Represents a user with a name and a list of songs."""

    def __init__(self, name):
        self.name = name
        self.song_list = []

    def print_song_list(self):
        """Prints the song list of the user."""
        for index, song in enumerate(self.song_list):
            print(f"{index} : {song.release_year} | '{song.title}' by {song.artist}")

    def get_valid_index_by_input(self):
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
