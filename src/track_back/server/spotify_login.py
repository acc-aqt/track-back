"""Spotify login routes that create a game session with an authenticated adapter."""

import html
import os
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ValidationError
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from track_back.game.game_logic import GameLogic
from track_back.music_service.spotify import SpotifyAdapter
from track_back.server.errors import SessionAlreadyExistsError
from track_back.server.game_sessions import game_session_manager
from track_back.server.names import SessionName, TargetSongCount, Username

router = APIRouter()


class LoginState(BaseModel):
    """The Game Setup and the Host's username, carried through the Spotify login."""

    game_id: SessionName
    target_song_count: TargetSongCount
    username: Username


def _state_error_message(error: ValidationError) -> str:
    """Name the first state field that failed validation."""
    first_error = error.errors()[0]
    field_path = first_error["loc"]
    if not field_path:
        return "Failed to parse state"
    field_name = field_path[0]
    return f"Missing or invalid {field_name} (state)"


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

    Parameters
    ----------
    state : str, optional
        A JSON-encoded string to maintain state between the request and callback.
        Defaults to an empty string.

    Returns
    -------
    RedirectResponse
        A redirect to Spotify's authorization URL where the user can log in and
        authorize access.

    """
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url(state=state)

    return RedirectResponse(auth_url)


@router.get("/spotify-callback")
def spotify_callback(request: Request) -> Response:
    """Handle the Spotify OAuth callback after user authorization.

    This endpoint is triggered by Spotify after a user logs in and approves access. It
    extracts the authorization code and the game configuration state (game ID, target
    song count, the Host's username) from the request, exchanges the code for an
    access token, sets up the game logic with a Spotify adapter, registers the new game
    session and sends the Host back to the Web UI to join it.

    Parameters
    ----------
    request : Request
        The incoming request containing query parameters 'code' and 'state'.

    Returns
    -------
    Response
        A 303 redirect to ``/?join=<session>&username=<username>&host=1`` if login and setup
        succeeded, or an error page if any part of the process failed or the Game
        Session Name is taken.

    """
    code = request.query_params.get("code")
    state_raw = request.query_params.get("state")

    if not code or not state_raw:
        return HTMLResponse(
            "❌ Missing code or state in callback request", status_code=400
        )

    try:
        state = LoginState.model_validate_json(state_raw)
    except ValidationError as error:
        return HTMLResponse(f"❌ {_state_error_message(error)}", status_code=400)

    sp_oauth = get_spotify_oauth()
    token_info = sp_oauth.get_access_token(code)

    if not token_info:
        return HTMLResponse("❌ Could not get token from Spotify", status_code=400)

    access_token = token_info["access_token"]

    adapter = SpotifyAdapter()
    adapter.authenticate(access_token)
    game = GameLogic(target_song_count=state.target_song_count, music_service=adapter)

    try:
        game_session_manager.add_session(state.game_id, game)
    except SessionAlreadyExistsError as error:
        return HTMLResponse(f"❌ {html.escape(str(error))}", status_code=409)

    join_query = (
        f"join={quote(state.game_id, safe='')}"
        f"&username={quote(state.username, safe='')}"
        "&host=1"
    )
    return RedirectResponse(f"/?{join_query}", status_code=303)
