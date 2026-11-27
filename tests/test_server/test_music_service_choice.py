import sys
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from track_back.music_service.mock import MockMusicService
from track_back.music_service.selection import MusicServiceType
from track_back.server.game_sessions import GameSession
from track_back.server.server import Server

SPOTIFY_KEYS = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]


def client_for(
    monkeypatch: pytest.MonkeyPatch,
    music_service: MusicServiceType,
    *,
    platform: str,
    spotify_credentials: bool,
) -> TestClient:
    monkeypatch.setattr(sys, "platform", platform)
    for key in SPOTIFY_KEYS:
        if spotify_credentials:
            monkeypatch.setenv(key, "value")
        else:
            monkeypatch.delenv(key, raising=False)
    return TestClient(Server(music_service=music_service).app)


def test_create_without_music_service_uses_the_servers_music_service(
    client: TestClient, get_session: Callable[[str], GameSession]
) -> None:
    response = client.post("/create", json={"game_id": "party", "target_song_count": 2})

    assert response.status_code == 201
    assert isinstance(get_session("party").game_logic.music_service, MockMusicService)


ServerSetup = tuple[str, str, bool]
"""The chosen Music Service, the platform and whether Spotify credentials are set."""


@pytest.mark.parametrize(
    ("setup", "requested", "available"),
    [
        (("mock", "linux", False), "spotify", "mock"),
        (("mock", "linux", False), "applemusic", "mock"),
        (("applemusic", "darwin", False), "spotify", "applemusic"),
        (("spotify", "darwin", True), "mock", "spotify, applemusic"),
    ],
)
def test_create_with_unavailable_music_service_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    setup: ServerSetup,
    requested: str,
    available: str,
) -> None:
    chosen, platform, spotify_credentials = setup
    client = client_for(
        monkeypatch,
        MusicServiceType(chosen),
        platform=platform,
        spotify_credentials=spotify_credentials,
    )

    response = client.post(
        "/create",
        json={
            "game_id": "party",
            "target_song_count": 2,
            "music_service_type": requested,
        },
    )

    assert response.status_code == 400
    assert available in response.json()["detail"]
    assert client.get("/list-sessions").json() == {"sessions": []}
