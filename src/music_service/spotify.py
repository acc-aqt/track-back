"""Implementation of the SpotifyClient class."""

import json
import os
import sys

import spotipy
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from game.game_logic import GameLogic
from game.song import Song
from music_service.abstract_adapter import AbstractMusicServiceAdapter
from music_service.error import MusicServiceError
from music_service.utils import extract_year
from server.game_sessions import game_session_manager


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
        if not self.session:
            raise MusicServiceError("Spotify session is not yet authenticated.")
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
        if not self.session:
            raise MusicServiceError("Spotify session is not yet authenticated.")
        self.session.next_track()


# ----------------------
# FastAPI Router for Spotify Login
# ----------------------
router = APIRouter()


def get_spotify_oauth() -> SpotifyOAuth:
    """Get Spotify OAuth object."""
    read_library = "user-library-read"
    read_playback = "user-read-playback-state"
    modify_playback = "user-modify-playback-state"
    scope = f"{read_library},{read_playback},{modify_playback}"

    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=scope,
        cache_handler=MemoryCacheHandler(),
    )


@router.get("/spotify-login")
def spotify_login(state: str = "") -> RedirectResponse:
    """Initiate the Spotify OAuth authorization flow.

    This endpoint generates an authorization URL and redirects the user to Spotify's
    login and consent page. An optional 'state' parameter can be passed to track the
    session or pass metadata, which will be included in the callback.

    Args:
        state (str, optional): A JSON-encoded string to maintain state between the
        request and callback. Defaults to an empty string.

    Returns
    -------
        RedirectResponse: A redirect to Spotify's authorization URL where the user can
        log in and authorize access.

    """
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url(state=state)

    return RedirectResponse(auth_url)


@router.get("/spotify-callback")
def spotify_callback(request: Request) -> HTMLResponse:
    """Handle the Spotify OAuth callback after user authorization.

    This endpoint is triggered by Spotify after a user logs in and approves access. It
    extracts the authorization code and the game configuration state (game ID, target
    song count) from the request, exchanges the code for an access token, retrieves the
    user profile, sets up the game logic with a Spotify adapter, and registers the new
    game session.

    Args:
        request (Request): The incoming request containing query parameters 'code' and
        'state'.

    Returns
    -------
        HTMLResponse: A success message if login and setup succeeded, or an error
        message if any part of the process failed.

    """
    code = request.query_params.get("code")
    state_raw = request.query_params.get("state")

    if not code or not state_raw:
        return HTMLResponse(
            "❌ Missing code or state in callback request", status_code=400
        )

    try:
        state = json.loads(state_raw)
        game_id = state.get("game_id")
        target_song_count = state.get("target_song_count")
    except json.JSONDecodeError:
        return HTMLResponse("❌ Failed to parse state", status_code=400)

    if not game_id:
        return HTMLResponse("❌ Missing game_id (state)", status_code=400)
    if not target_song_count:
        return HTMLResponse("❌ Missing target_song_count", status_code=400)

    sp_oauth = get_spotify_oauth()
    token_info = sp_oauth.get_access_token(code)

    if not token_info:
        return HTMLResponse("❌ Could not get token from Spotify", status_code=400)

    access_token = token_info["access_token"]
    sp = spotipy.Spotify(auth=access_token)

    user_profile = sp.current_user()
    username = user_profile["id"]

    adapter = SpotifyAdapter()
    adapter.authenticate(access_token)
    game = GameLogic(target_song_count=target_song_count, music_service=adapter)

    game_session_manager.add_game(game_id, game)

    return HTMLResponse(
        content=f"✅ Logged in as <b>{username}</b>. "
        "You can now close this tab and return to the game."
    )
