"""Spotify login routes that create a game session with an authenticated adapter."""

import html
import json
import os

import spotipy
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import TypeAdapter, ValidationError
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from game.game_logic import GameLogic
from music_service.spotify import SpotifyAdapter
from server.game_sessions import game_session_manager
from server.names import GAME_ID_MAX_LENGTH, TargetSongCount, is_valid_name

router = APIRouter()


def get_spotify_oauth() -> SpotifyOAuth:
    """Get Spotify OAuth object."""
    scope = "user-read-playback-state,user-modify-playback-state"

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

    if not game_id or not is_valid_name(str(game_id), GAME_ID_MAX_LENGTH):
        return HTMLResponse("❌ Missing or invalid game_id (state)", status_code=400)
    try:
        target_song_count = TypeAdapter(TargetSongCount).validate_python(
            target_song_count
        )
    except ValidationError:
        return HTMLResponse(
            "❌ Missing or invalid target_song_count (state)", status_code=400
        )

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
        content=f"✅ Logged in as <b>{html.escape(username)}</b>. "
        "You can now close this tab and return to the game."
    )
