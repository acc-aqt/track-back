"""Implementation of the SpotifyClient class."""

import os
import sys
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from game.song import Song
from music_service.abstract_adapter import AbstractMusicServiceAdapter
from music_service.error import MusicServiceError
from music_service.utils import extract_year


class SpotifyAdapter(AbstractMusicServiceAdapter):
    """Interface to the Spotify API."""

    def __init__(self) -> None:
        self.session = None

    def authenticate(self, access_token: str) -> None:
        self.session = spotipy.Spotify(auth=access_token)

    def current_song(self) -> Song:
        """Get the currently playing song."""
        playback = self.session.current_playback()
        if playback["is_playing"] is False:
            print("Spotify is not playing.")
            sys.exit(1)
        song_name = playback["item"]["name"]
        artist_names = ", ".join([artist["name"] for artist in playback["item"]["artists"]])
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


# ----------------------
# FastAPI Router for Spotify Login
# ----------------------
router = APIRouter()
user_tokens: dict[str, dict] = {}  # In-memory user token storage (user_id → token_info)


def get_spotify_oauth(username=None):
    read_library = "user-library-read"
    read_playback = "user-read-playback-state"
    modify_playback = "user-modify-playback-state"
    scope = f"{read_library},{read_playback},{modify_playback}"

    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8000/spotify-callback"),
        scope=scope,
        cache_path=f".cache-{username}" if username else None,
    )


@router.get("/spotify-login")
def spotify_login():
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@router.get("/spotify-callback")
def spotify_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse("❌ Missing code from Spotify", status_code=400)

    sp_oauth = get_spotify_oauth()
    token_info = sp_oauth.get_access_token(code)

    if not token_info:
        return HTMLResponse("❌ Could not get token from Spotify", status_code=400)

    sp = spotipy.Spotify(auth=token_info["access_token"])
    user_profile = sp.current_user()
    username = user_profile["id"]

    user_tokens[username] = token_info

    return HTMLResponse(
        f"✅ Logged in as <b>{username}</b>. You can now close this tab and return to the game."
    )
