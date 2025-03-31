"""Entry point to start the track-back server."""

import os
import time
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ToDo: Allow extension for other music services


@dataclass
class Song:
    """Represents a song with title, artist and release year."""
    title: str
    artist: str
    release_year: int

    def __str__(self):
        return f"'{self.title}' by {self.artist} ({self.release_year})"


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
                "\nEnter the index in front of which the song shall be added. " \
                "(0 for the first song, -1 for the last song): "
            )
            try:
                input_index = int(input_index)
                if -1 <= input_index <= len(self.song_list):
                    return input_index
                print("Please enter a valid index.")
            except ValueError:
                print("Please enter a valid index.")


class TrackBackGame:
    """Handles the game session"""
    def __init__(self, users, target_history_length, session):
        self.session = session
        self.users = users
        self.target_history_length = target_history_length
        self.round_counter = 0
        self.finished = False

    def run(self):
        """Runs the game session."""
        while True:
            self.round_counter += 1
            print(f"Round {self.round_counter}")
            for user in self.users:
                self._process_user_turn(user)
                if self.finished:
                    return

    def _process_user_turn(self, user):
        print(f"\n\nIt's {user.name}'s turn. Current Songlist:")
        user.print_song_list()
        input_index = user.get_valid_index_by_input()

        current_song = get_current_song(self.session)

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

        self.session.next_track()

        if len(user.song_list) == self.target_history_length:
            print(f"{user.name} wins!")
            self.finished = True


def initialize_spotify_session():
    """Initializes a spotify session."""

    o_authenticator = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-library-read,user-read-playback-state,user-modify-playback-state",
    )

    return spotipy.Spotify(auth_manager=o_authenticator)


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


def extract_year(date_str: str) -> int:
    """Extracts the year from a date string and handles different date formats."""
    formats = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).year
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")


def get_current_song(session) -> Song:
    """Gets the current song from the streaming session."""
    playback = session.current_playback()
    song_name = playback["item"]["name"]
    artist_names = ", ".join([artist["name"] for artist in playback["item"]["artists"]])
    release_date = playback["item"]["album"]["release_date"]
    release_year = extract_year(release_date)

    current_song = Song(song_name, artist_names, release_year)
    return current_song


def start_playback(session):
    """Starts the playback of the session."""
    try:
        session.start_playback()
    except spotipy.exceptions.SpotifyException:
        print("Probably song is already plaing, skip to next...")
        try:
            session.next_track()
        except spotipy.exceptions.SpotifyException:
            print("Could not start playback. Please start a song manually.")
            exit(1)


def main():
    load_dotenv()

    target_history_length = 2

    session = initialize_spotify_session()
    start_playback(session)

    users = get_users()

    game = TrackBackGame(users=users, target_history_length=target_history_length, session=session)
    game.run()


if __name__ == "__main__":
    main()