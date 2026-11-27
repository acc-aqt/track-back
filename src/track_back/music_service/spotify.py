"""Implementation of the SpotifyAdapter class."""

from datetime import datetime

import spotipy

from track_back.game.song import Song
from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.error import MusicServiceError


class SpotifyAdapter(AbstractMusicServiceAdapter):
    """Interface to the Spotify API."""

    service_name = "Spotify"

    def __init__(self) -> None:
        self.session: spotipy.Spotify | None = None

    def authenticate(self, access_token: str) -> None:
        """Authenticate the Spotify session with the provided access token."""
        self.session = spotipy.Spotify(auth=access_token)

    def current_song(self) -> Song:
        """Get the currently playing song."""
        if not self.session:
            raise MusicServiceError("Spotify session is not yet authenticated.")
        playback = self.session.current_playback()
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
        if not self.session:
            raise MusicServiceError("Spotify session is not yet authenticated.")
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
        if not self.session:
            raise MusicServiceError("Spotify session is not yet authenticated.")
        self.session.next_track()


def extract_year(date_str: str) -> int:
    """Extract the year from a date and handle different date formats."""
    formats = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).year
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")
