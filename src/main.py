"""Entry point to start the track-back server."""

import os

from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth


def run_track_back_server():
    """Entry point to start the track-back server."""

    sp = initialize_spotify_client()
    results = sp.current_user_saved_tracks()
    for idx, item in enumerate(results["items"]):
        track = item["track"]
        print(idx, track["artists"][0]["name"], " – ", track["name"])


def initialize_spotify_client():
    """Initializes a Spotify client."""

    o_authenticator = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-library-read",
    )

    return spotipy.Spotify(auth_manager=o_authenticator)


if __name__ == "__main__":
    load_dotenv()
    run_track_back_server()
