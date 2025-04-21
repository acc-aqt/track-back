"""Implementation of the SpotifyClient class."""

import os
import sys

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from game.song import Song
from music_service.abstract_adapter import AbstractMusicServiceAdapter
from music_service.error import MusicServiceError
from music_service.utils import extract_year


class SpotifyAdapter(AbstractMusicServiceAdapter):
    """Interface to the Spotify API."""

    def __init__(self) -> None:
        self.session = self._initialize_spotify_session()

    def current_song(self) -> Song:
        """Get the currently playing song."""
        playback = self.session.current_playback()
        if playback["is_playing"] is False:
            print("Spotify is not playing.")
            sys.exit(1)
        song_name = playback["item"]["name"]
        artist_names = ", ".join(
            [artist["name"] for artist in playback["item"]["artists"]]
        )
        release_year = extract_year(playback["item"]["album"]["release_date"])
        album_cover_url = playback["item"]["album"]["images"][-1]["url"]

        return Song(
            title=song_name,
            artist=artist_names,
            release_year=release_year,
            album_cover_url=album_cover_url,
        )

    def start_playback(self) -> None:
        """Start playing music."""
        try:
            self.session.start_playback()
        except spotipy.exceptions.SpotifyException:
            print("Probably song is already plaing, skip to next...")
            try:
                self.session.next_track()
            except spotipy.exceptions.SpotifyException as e:
                raise MusicServiceError(
                    "Cannot start playback. Spotify is probably not running."
                ) from e

    def next_track(self) -> None:
        """Skip to the next track."""
        self.session.next_track()

    def _initialize_spotify_session(self) -> spotipy.Spotify:
        """Initialize a spotify session, including authentication."""
        read_library = "user-library-read"
        read_playback = "user-read-playback-state"
        modify_playback = "user-modify-playback-state"
        scope_string = f"{read_library},{read_playback},{modify_playback}"

        cache_path = ".cache-spotify" if os.getenv("RENDER") == "true" else None

        o_authenticator = SpotifyOAuth(
            scope=scope_string,
            cache_path=cache_path,
        )

        return spotipy.Spotify(auth_manager=o_authenticator)
