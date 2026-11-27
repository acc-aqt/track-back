"""Spotify login and callback routes, with Spotify OAuth patched out."""

import json
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from track_back.server import spotify_login


class FakeOAuth:
    def get_access_token(self, _code: str) -> dict[str, str]:
        return {"access_token": "token"}


@pytest.fixture
def callback_client(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> TestClient:
    monkeypatch.setattr(spotify_login, "get_spotify_oauth", FakeOAuth)
    return client


@pytest.mark.parametrize("username", ["<script>alert(1)</script>", "", None])
def test_callback_rejects_invalid_username(
    callback_client: TestClient, username: object
) -> None:
    """The callback applies the same Username rule as joining a Game Session."""
    state = json.dumps(
        {"game_id": "spotify-game", "target_song_count": 3, "username": username}
    )
    response = callback_client.get(
        "/spotify-callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "<script>" not in response.text
    assert callback_client.get("/list-sessions").json() == {"sessions": []}


def test_callback_redirects_host_into_the_new_game_session(
    callback_client: TestClient,
) -> None:
    state = json.dumps(
        {"game_id": "Spiel für alle", "target_song_count": 3, "username": "Anna Lü"}
    )
    response = callback_client.get(
        "/spotify-callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/?join=Spiel%20f%C3%BCr%20alle&username=Anna%20L%C3%BC&host=1"
    )
    assert callback_client.get("/list-sessions").json() == {
        "sessions": ["Spiel für alle"]
    }


def test_callback_rejects_invalid_game_id(callback_client: TestClient) -> None:
    state = json.dumps(
        {"game_id": "<b>x</b>", "target_song_count": 3, "username": "Anna"}
    )
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 400
    assert callback_client.get("/list-sessions").json() == {"sessions": []}


def test_callback_shows_an_error_page_when_the_name_is_taken(
    callback_client: TestClient,
) -> None:
    """A Host who logs in with a taken Game Session Name sees an error page."""
    callback_client.post("/create", json={"game_id": "taken", "target_song_count": 3})
    state = json.dumps({"game_id": "taken", "target_song_count": 3, "username": "Anna"})
    response = callback_client.get(
        "/spotify-callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("text/html")
    assert "Game session &#x27;taken&#x27; already exists" in response.text


@pytest.mark.parametrize("target_song_count", [0, -1, "zero"])
def test_callback_rejects_target_song_count_below_one(
    callback_client: TestClient, target_song_count: object
) -> None:
    """The callback applies the same Target Song Count rule as /create."""
    state = json.dumps(
        {
            "game_id": "spotify-game",
            "target_song_count": target_song_count,
            "username": "Anna",
        }
    )
    response = callback_client.get(
        "/spotify-callback", params={"code": "abc", "state": state}
    )
    assert response.status_code == 400
    assert callback_client.get("/list-sessions").json() == {"sessions": []}


def test_login_asks_only_for_playback_permissions(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """The Spotify login requests playback scopes and no library access."""
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://localhost/spotify-callback")

    response = client.get("/spotify-login", follow_redirects=False)

    scopes = parse_qs(urlparse(response.headers["location"]).query)["scope"][0]
    assert set(scopes.split()) == {
        "user-read-playback-state",
        "user-modify-playback-state",
    }
