import json
import re
from pathlib import Path

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from music_service.apple_music import AppleMusicAdapter
from music_service.error import MusicServiceError
from server.game_sessions import game_session_manager
from server.server import Server


@pytest.fixture
def client():
    return TestClient(Server().app)


@pytest.fixture(autouse=True)
def _clear_sessions():
    yield
    game_session_manager.sessions.clear()


def _create_and_join(client: TestClient, game_id: str, user: str) -> None:
    response = client.post(
        "/create",
        json={"game_id": game_id, "target_song_count": 2, "music_service_type": "mock"},
    )
    assert response.status_code == 201
    response = client.post("/join", json={"game_id": game_id, "user_name": user})
    assert response.status_code == 200


def test_ping_before_start_keeps_session_alive(client: TestClient):
    game_id = "ping-before-start"
    _create_and_join(client, game_id, "host")

    with client.websocket_connect(f"/ws/{game_id}/host") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"

        ws.send_json({"type": "ping"})
        ws.send_json({"type": "ping"})

        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"


def test_create_with_unknown_music_service_is_rejected(client: TestClient):
    response = client.post(
        "/create",
        json={
            "game_id": "bad-service",
            "target_song_count": 2,
            "music_service_type": "napster",
        },
    )
    assert response.status_code == 422
    assert game_session_manager.get_game_session("bad-service") is None


def _music_service_dropdown_values() -> list[str]:
    index_html = (Path(__file__).parents[2] / "web_ui" / "index.html").read_text()
    dropdown = re.search(
        r'<select id="musicServiceDropdown">(.*?)</select>', index_html, re.DOTALL
    )
    assert dropdown is not None
    return re.findall(r'<option value="([^"]+)"', dropdown.group(1))


@pytest.mark.parametrize("music_service_type", _music_service_dropdown_values())
def test_create_accepts_every_browser_music_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, music_service_type: str
) -> None:
    """Every value the browser's music-service dropdown sends creates a game."""
    always = staticmethod(lambda: True)
    monkeypatch.setattr(AppleMusicAdapter, "running_on_macos", always)
    monkeypatch.setattr(AppleMusicAdapter, "music_app_is_running", always)
    response = client.post(
        "/create",
        json={
            "game_id": "dropdown",
            "target_song_count": 2,
            "music_service_type": music_service_type,
        },
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "bad_message",
    [
        "not json",
        json.dumps({"type": "guess"}),
        json.dumps({"type": "guess", "index": "0"}),
        json.dumps({"type": "guess", "index": True}),
        json.dumps({"type": "guess", "index": -1}),
        json.dumps({"type": "guess", "index": 99}),
        json.dumps({"type": "dance"}),
        json.dumps([1, 2]),
    ],
)
def test_malformed_message_gets_error_and_socket_stays_usable(
    client: TestClient, bad_message: str
):
    game_id = "malformed-message"
    _create_and_join(client, game_id, "solo")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"

        ws.send_text(bad_message)
        assert json.loads(ws.receive_text())["type"] == "error"

        ws.send_json({"type": "guess", "index": 0})
        assert json.loads(ws.receive_text())["type"] == "guess_result"


def test_music_service_failure_during_guess_is_reported(client: TestClient):
    game_id = "music-service-failure"
    _create_and_join(client, game_id, "solo")
    music_service = game_session_manager.get_game_session(game_id).game_logic.music_service

    def broken_current_song() -> None:
        raise MusicServiceError("No active Spotify playback.")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"

        music_service.current_song = broken_current_song
        ws.send_json({"type": "guess", "index": 0})
        response = json.loads(ws.receive_text())
        assert response["type"] == "error"
        assert "No active Spotify playback" in response["message"]


@pytest.mark.parametrize(
    "user_name",
    ["<b>x</b>", "<img src=x onerror=alert(1)>", "", " padded", "a" * 21, "semi;colon"],
)
def test_join_rejects_invalid_user_names(client: TestClient, user_name: str):
    client.post(
        "/create",
        json={"game_id": "names", "target_song_count": 2, "music_service_type": "mock"},
    )
    response = client.post("/join", json={"game_id": "names", "user_name": user_name})
    assert response.status_code == 422


@pytest.mark.parametrize("user_name", ["Alex", "Jörg", "dj-max_2", "Anna Lena"])
def test_join_accepts_valid_user_names(client: TestClient, user_name: str):
    client.post(
        "/create",
        json={"game_id": "names", "target_song_count": 2, "music_service_type": "mock"},
    )
    response = client.post("/join", json={"game_id": "names", "user_name": user_name})
    assert response.status_code == 200


BROWSER_NAME_PATTERN = r"/^[\p{L}\p{N}_-]+( [\p{L}\p{N}_-]+)*$/u"

NAMES_THE_BROWSER_ACCEPTS = [
    "Дмитрий",
    "李雷",
    "Ελένη",
    "٣٤٥",
    "x\u00b2",
    "\u216b",
    "Anna-Lena_2",
    "Anna Lena",
]

NAMES_THE_BROWSER_REJECTS = [
    "",
    " Anna",
    "Anna ",
    "Anna  Lena",
    "a\u0301",
    "a\u203fb",
    "tab\there",
    "semi;colon",
]


def test_browser_name_pattern_is_the_one_under_test() -> None:
    """The name cases below are checked against this exact browser pattern."""
    script = (Path(__file__).parents[2] / "web_ui" / "script.js").read_text()
    assert f"const NAME_PATTERN = {BROWSER_NAME_PATTERN}" in script


@pytest.mark.parametrize("user_name", NAMES_THE_BROWSER_ACCEPTS)
def test_server_accepts_user_names_the_browser_accepts(
    client: TestClient, user_name: str
) -> None:
    """Any user name the browser lets through can join."""
    _create_and_join(client, "names", user_name)


@pytest.mark.parametrize("user_name", NAMES_THE_BROWSER_REJECTS)
def test_server_rejects_user_names_the_browser_rejects(
    client: TestClient, user_name: str
) -> None:
    """Any user name the browser blocks is a 422 on /join."""
    _create_and_join(client, "names", "host")
    response = client.post("/join", json={"game_id": "names", "user_name": user_name})
    assert response.status_code == 422


@pytest.mark.parametrize("game_id", NAMES_THE_BROWSER_ACCEPTS)
def test_server_accepts_game_ids_the_browser_accepts(
    client: TestClient, game_id: str
) -> None:
    """Game ids follow the same rule as user names."""
    _create_and_join(client, game_id, "host")


@pytest.mark.parametrize("game_id", NAMES_THE_BROWSER_REJECTS)
def test_server_rejects_game_ids_the_browser_rejects(
    client: TestClient, game_id: str
) -> None:
    """A game id the name rule blocks is a 422 on /create."""
    response = client.post(
        "/create",
        json={"game_id": game_id, "target_song_count": 2, "music_service_type": "mock"},
    )
    assert response.status_code == 422


def test_server_rejects_game_ids_over_40_characters(client: TestClient) -> None:
    """Game ids are capped at 40 characters."""
    response = client.post(
        "/create",
        json={
            "game_id": "g" * 41,
            "target_song_count": 2,
            "music_service_type": "mock",
        },
    )
    assert response.status_code == 422


def test_create_rejects_markup_in_game_id(client: TestClient):
    response = client.post(
        "/create",
        json={
            "game_id": "<script>",
            "target_song_count": 2,
            "music_service_type": "mock",
        },
    )
    assert response.status_code == 422


def test_websocket_rejects_invalid_user_name(client: TestClient):
    game_id = "ws-names"
    client.post(
        "/create",
        json={"game_id": game_id, "target_song_count": 2, "music_service_type": "mock"},
    )
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/ws/{game_id}/%3Cimg%20src%3Dx%3E") as ws,
    ):
        ws.receive_text()
    assert game_session_manager.get_game_session(game_id).connection_manager.user_connections == {}


def test_playback_failure_on_start_is_reported_as_server_error(
    client: TestClient,
) -> None:
    """A failed playback start is a 500 and leaves the game startable."""
    game_id = "playback-failure"
    _create_and_join(client, game_id, "solo")
    session = game_session_manager.get_game_session(game_id)
    music_service = session.game_logic.music_service
    working_start_playback = music_service.start_playback

    def broken_start_playback() -> None:
        raise MusicServiceError("No active device.")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"

        music_service.start_playback = broken_start_playback
        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 500
        assert response.json() == {
            "detail": "Failed to play music. Please check if music service "
            "Dummy Music Service is running!"
        }

        music_service.start_playback = working_start_playback
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"


def test_joining_twice_before_start_is_a_conflict(client: TestClient) -> None:
    """Joining under a registered name before start is a 409."""
    game_id = "double-join"
    _create_and_join(client, game_id, "alex")

    response = client.post("/join", json={"game_id": game_id, "user_name": "alex"})

    assert response.status_code == 409
    assert response.json() == {"detail": "User 'alex' already registered"}


def test_creating_an_existing_session_is_a_conflict(client: TestClient) -> None:
    """Creating a session with a taken ID is a 409."""
    _create_and_join(client, "taken", "alex")

    response = client.post(
        "/create",
        json={"game_id": "taken", "target_song_count": 2, "music_service_type": "mock"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Session 'taken' already exists. Choose different ID."
    }


@pytest.mark.parametrize("target_song_count", [0, -1])
def test_create_rejects_target_song_count_below_one(
    client: TestClient, target_song_count: int
) -> None:
    """A Target Song Count below 1 is a 422 and creates no session."""
    response = client.post(
        "/create",
        json={
            "game_id": "too-few-songs",
            "target_song_count": target_song_count,
            "music_service_type": "mock",
        },
    )
    assert response.status_code == 422
    assert game_session_manager.get_game_session("too-few-songs") is None
