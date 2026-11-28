"""Implementation of the SpotifyAdapter class."""

from datetime import datetime

import spotipy

from track_back.game.song import Song
from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.error import MusicServiceError


class SpotifyAdapter(AbstractMusicServiceAdapter):
    """Interface to the Spotify API."""

    service_name = "Spotify"

    def __init__(self, session: spotipy.Spotify) -> None:
        """Use an authenticated Spotify client, such as ``spotipy.Spotify(auth=token)``."""
        self.session = session

    def current_song(self) -> Song:
        """Get the currently playing song."""
        try:
            playback = self.session.current_playback()
        except spotipy.exceptions.SpotifyException as e:
            raise MusicServiceError(f"Cannot read the Spotify playback: {e.msg}") from e
        if not playback or not playback.get("item"):
            raise MusicServiceError(
                "No active Spotify playback. Start playing on a Spotify device."
            )
        if playback["is_playing"] is False:
            raise MusicServiceError("Spotify is not playing.")
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
            try:
                self.session.next_track()
            except spotipy.exceptions.SpotifyException as e:
                raise MusicServiceError(
                    "Cannot start playback. Spotify is probably not running."
                ) from e

    def next_track(self) -> None:
        """Skip to the next track."""
        try:
            self.session.next_track()
        except spotipy.exceptions.SpotifyException as e:
            raise MusicServiceError(f"Cannot skip to the next track: {e.msg}") from e


def extract_year(date_str: str) -> int:
    """Extract the year from a date and handle different date formats."""
    formats = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).year
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")
