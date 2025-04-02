"""Implementation of the SpotifyClient class."""

import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from game.song import Song

from .abstract_music_provider import AbstractMusicProvider
from .utils import extract_year


class SpotifyClient(AbstractMusicProvider):
    """Interface to the Spotify API."""

    def __init__(self):
        self.session = self._initialize_spotify_session()

    def current_song(self) -> Song:
        playback = self.session.current_playback()

        song_name = playback["item"]["name"]
        artist_names = ", ".join(
            [artist["name"] for artist in playback["item"]["artists"]]
        )
        release_year = extract_year(playback["item"]["album"]["release_date"])

        return Song(title=song_name, artist=artist_names, release_year=release_year)

    def start_playback(self) -> None:
        try:
            self.session.start_playback()
        except spotipy.exceptions.SpotifyException:
            print("Probably song is already plaing, skip to next...")
            try:
                self.session.next_track()
            except spotipy.exceptions.SpotifyException:
                print("Could not start playback. Please start a song manually.")
                exit(1)

    def next_track(self) -> None:
        return self.session.next_track()

    def _initialize_spotify_session(self):
        """Initializes a spotify session."""

        o_authenticator = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope="user-library-read,user-read-playback-state,user-modify-playback-state",
        )

        return spotipy.Spotify(auth_manager=o_authenticator)
