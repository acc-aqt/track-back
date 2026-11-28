"""Every Guess in a Round is judged against the Song read on the Round's first Guess."""

from contextlib import ExitStack
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from track_back.game.song import Song
from track_back.music_service.abstract_adapter import AbstractMusicServiceAdapter
from track_back.music_service.selection import MUSIC_SERVICES, MusicServiceType
from track_back.server.server import Server

SONGS = [
    Song(title="Yesterday", artist="The Beatles", release_year=1965),
    Song(title="Bohemian Rhapsody", artist="Queen", release_year=1975),
    Song(title="Bad Guy", artist="Billie Eilish", release_year=2019),
]


class SkippingMusicService(AbstractMusicServiceAdapter):
    """A Music Service whose current Song changes on every read."""

    service_name = "Skipping Music Service"

    def __init__(self) -> None:
        self.reads = 0

    def current_song(self) -> Song:
        song = SONGS[self.reads % len(SONGS)]
        self.reads += 1
        return song

    def start_playback(self) -> None:
        pass

    def next_track(self) -> None:
        pass


class SlowSkippingMusicService(AbstractMusicServiceAdapter):
    """A Music Service whose skips land some time after they are requested."""

    service_name = "Slow Skipping Music Service"

    def __init__(self) -> None:
        self.playing = 0
        self.requested = 0

    def current_song(self) -> Song:
        return SONGS[self.playing % len(SONGS)]

    def start_playback(self) -> None:
        pass

    def next_track(self) -> None:
        self.requested += 1

    def land_skips(self) -> None:
        self.playing = self.requested


@pytest.fixture
def music_service() -> SkippingMusicService:
    return SkippingMusicService()


def _client_for(music_service: AbstractMusicServiceAdapter) -> TestClient:
    music_services = {
        **MUSIC_SERVICES,
        MusicServiceType.MOCK: replace(
            MUSIC_SERVICES[MusicServiceType.MOCK], build=lambda _covers: music_service
        ),
    }
    server = Server(music_service=MusicServiceType.MOCK, music_services=music_services)
    return TestClient(server.app)


@pytest.fixture
def client(music_service: SkippingMusicService) -> TestClient:
    return _client_for(music_service)


def _receive(ws: WebSocketTestSession) -> dict[str, Any]:
    message: dict[str, Any] = ws.receive_json()
    return message


def _receive_guess_result(ws: WebSocketTestSession) -> dict[str, Any]:
    while (message := _receive(ws))["type"] != "guess_result":
        assert message["type"] == "other_player_guess"
    return message


def _play_first_round(client: TestClient, *user_names: str) -> list[dict[str, Any]]:
    """Let every Player guess once in the first Round; return their guess results."""
    client.post("/create", json={"game_id": "party", "target_song_count": 3})
    for user_name in user_names:
        client.post("/join", json={"game_id": "party", "user_name": user_name})

    with ExitStack() as stack:
        sockets = [
            stack.enter_context(client.websocket_connect(f"/ws/party/{user_name}"))
            for user_name in user_names
        ]
        for ws in sockets:
            assert _receive(ws)["type"] == "welcome"
        assert client.post("/start", json={"game_id": "party"}).status_code == 200
        for ws in sockets:
            assert _receive(ws)["type"] == "your_turn"

        results = []
        for ws in sockets:
            ws.send_json({"type": "guess", "index": 0})
            results.append(_receive_guess_result(ws))
        return results


def test_every_guess_in_a_round_is_judged_against_the_same_song(
    client: TestClient,
) -> None:
    alice_result, bob_result = _play_first_round(client, "alice", "bob")

    assert alice_result["last_song"]["title"] == "Yesterday"
    assert bob_result["last_song"]["title"] == "Yesterday"


def test_current_song_is_read_once_per_round(
    client: TestClient, music_service: SkippingMusicService
) -> None:
    _play_first_round(client, "alice", "bob", "carol")

    assert music_service.reads == 1, "the next Round's Song is read on its first Guess"


def test_round_song_is_the_one_playing_at_the_first_guess() -> None:
    music_service = SlowSkippingMusicService()
    client = _client_for(music_service)
    client.post("/create", json={"game_id": "party", "target_song_count": 3})
    client.post("/join", json={"game_id": "party", "user_name": "solo"})

    with client.websocket_connect("/ws/party/solo") as ws:
        assert _receive(ws)["type"] == "welcome"
        client.post("/start", json={"game_id": "party"})
        assert _receive(ws)["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 0})
        assert _receive(ws)["last_song"]["title"] == "Yesterday"
        assert _receive(ws)["type"] == "your_turn"

        music_service.land_skips()
        ws.send_json({"type": "guess", "index": 1})
        assert _receive(ws)["last_song"]["title"] == "Bohemian Rhapsody"
