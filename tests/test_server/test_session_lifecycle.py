import json
import sys
from collections.abc import Callable
from importlib.resources import files

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from track_back.music_service.apple_music import AppleMusicAdapter
from track_back.music_service.error import MusicServiceError
from track_back.music_service.selection import MusicServiceType
from track_back.server.game_sessions import GameSession, game_session_manager
from track_back.server.names import SESSION_NAME_MAX_LENGTH
from track_back.server.server import Server

WEB_UI = files("track_back") / "web_ui"


def test_ping_before_start_keeps_session_alive(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "ping-before-start"
    create_and_join(session_name, "host")

    with client.websocket_connect(f"/ws/{session_name}/host") as ws:
        assert ws.receive_json()["type"] == "welcome"

        ws.send_json({"type": "ping"})
        ws.send_json({"type": "ping"})

        response = client.post("/start", json={"game_id": session_name})
        assert response.status_code == 200
        assert ws.receive_json()["type"] == "your_turn"


def test_create_with_unknown_music_service_is_rejected(client: TestClient) -> None:
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


def test_create_accepts_every_music_service_the_server_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every service /music-services offers the Web UI creates a game."""
    monkeypatch.setattr(sys, "platform", "darwin")
    for key in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        monkeypatch.setenv(key, "value")
    client = TestClient(Server(music_service=MusicServiceType.MOCK).app)
    always = staticmethod(lambda: True)
    monkeypatch.setattr(AppleMusicAdapter, "running_on_macos", always)
    monkeypatch.setattr(AppleMusicAdapter, "music_app_is_running", always)

    available = client.get("/music-services").json()["available"]

    assert available == ["spotify", "applemusic", "mock"]
    for music_service_type in available:
        response = client.post(
            "/create",
            json={
                "game_id": f"offered-{music_service_type}",
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
    client: TestClient, create_and_join: Callable[..., None], bad_message: str
) -> None:
    session_name = "malformed-message"
    create_and_join(session_name, "solo")

    with client.websocket_connect(f"/ws/{session_name}/solo") as ws:
        assert ws.receive_json()["type"] == "welcome"
        assert client.post("/start", json={"game_id": session_name}).status_code == 200
        assert ws.receive_json()["type"] == "your_turn"

        ws.send_text(bad_message)
        assert ws.receive_json()["type"] == "error"

        ws.send_json({"type": "guess", "index": 0})
        assert ws.receive_json()["type"] == "guess_result"


def test_music_service_failure_during_guess_is_reported(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_name = "music-service-failure"
    create_and_join(session_name, "solo")
    music_service = get_session(session_name).game_logic.music_service

    def broken_current_song() -> None:
        raise MusicServiceError("No active Spotify playback.")

    with client.websocket_connect(f"/ws/{session_name}/solo") as ws:
        assert ws.receive_json()["type"] == "welcome"
        assert client.post("/start", json={"game_id": session_name}).status_code == 200
        assert ws.receive_json()["type"] == "your_turn"

        monkeypatch.setattr(music_service, "current_song", broken_current_song)
        ws.send_json({"type": "guess", "index": 0})
        response = ws.receive_json()
        assert response["type"] == "error"
        assert "No active Spotify playback" in response["message"]


@pytest.mark.parametrize(
    "user_name",
    ["<b>x</b>", "<img src=x onerror=alert(1)>", "", " padded", "a" * 21, "semi;colon"],
)
def test_join_rejects_invalid_user_names(
    client: TestClient, create_game: Callable[[str], None], user_name: str
) -> None:
    create_game("names")
    response = client.post("/join", json={"game_id": "names", "user_name": user_name})
    assert response.status_code == 422


@pytest.mark.parametrize("user_name", ["Alex", "Jörg", "dj-max_2", "Anna Lena"])
def test_join_accepts_valid_user_names(
    client: TestClient, create_game: Callable[[str], None], user_name: str
) -> None:
    create_game("names")
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


BROWSER_SESSION_NAME_RULE = (
    "const isValidSessionName = id =>\n"
    "  id.length <= SESSION_NAME_MAX_LENGTH && NAME_PATTERN.test(id)"
)

SESSION_NAMES_THE_BROWSER_ACCEPTS = [
    *NAMES_THE_BROWSER_ACCEPTS,
    "g" * SESSION_NAME_MAX_LENGTH,
]
SESSION_NAMES_THE_BROWSER_REJECTS = [
    *NAMES_THE_BROWSER_REJECTS,
    "g" * (SESSION_NAME_MAX_LENGTH + 1),
    "<script>",
]


def _browser_script() -> str:
    return (WEB_UI / "script.js").read_text()


def test_browser_name_pattern_is_the_one_under_test() -> None:
    """The name cases below are checked against this exact browser pattern."""
    assert f"const NAME_PATTERN = {BROWSER_NAME_PATTERN}" in _browser_script()


def test_browser_session_name_rule_is_the_one_under_test() -> None:
    """The browser checks Game Session Names with the name pattern and the server's cap."""
    script = _browser_script()
    assert f"const SESSION_NAME_MAX_LENGTH = {SESSION_NAME_MAX_LENGTH}\n" in script
    assert BROWSER_SESSION_NAME_RULE in script
    assert "if (!isValidSessionName(sessionName)) {" in script


@pytest.mark.parametrize("user_name", NAMES_THE_BROWSER_ACCEPTS)
def test_server_accepts_user_names_the_browser_accepts(
    create_and_join: Callable[..., None], user_name: str
) -> None:
    """Any user name the browser lets through can join."""
    create_and_join("names", user_name)


@pytest.mark.parametrize("user_name", NAMES_THE_BROWSER_REJECTS)
def test_server_rejects_user_names_the_browser_rejects(
    client: TestClient, create_game: Callable[[str], None], user_name: str
) -> None:
    """Any user name the browser blocks is a 422 on /join."""
    create_game("names")
    response = client.post("/join", json={"game_id": "names", "user_name": user_name})
    assert response.status_code == 422


@pytest.mark.parametrize("session_name", SESSION_NAMES_THE_BROWSER_ACCEPTS)
def test_server_accepts_session_names_the_browser_accepts(
    create_game: Callable[[str], None], session_name: str
) -> None:
    """Any Game Session Name the browser lets through can be created."""
    create_game(session_name)


@pytest.mark.parametrize("session_name", SESSION_NAMES_THE_BROWSER_REJECTS)
def test_server_rejects_session_names_the_browser_rejects(
    client: TestClient, session_name: str
) -> None:
    """Any Game Session Name the browser blocks is a 422 on /create."""
    response = client.post(
        "/create",
        json={
            "game_id": session_name,
            "target_song_count": 2,
            "music_service_type": "mock",
        },
    )
    assert response.status_code == 422


def test_websocket_rejects_invalid_user_name(
    client: TestClient,
    create_game: Callable[[str], None],
    get_session: Callable[[str], GameSession],
) -> None:
    session_name = "ws-names"
    create_game(session_name)
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/ws/{session_name}/%3Cimg%20src%3Dx%3E") as ws,
    ):
        ws.receive_text()
    assert get_session(session_name).connection_manager.player_connections == {}


def test_playback_failure_on_start_is_reported_as_server_error(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed playback start is a 500 and leaves the game startable."""
    session_name = "playback-failure"
    create_and_join(session_name, "solo")
    music_service = get_session(session_name).game_logic.music_service

    def broken_start_playback() -> None:
        raise MusicServiceError("No active device.")

    with client.websocket_connect(f"/ws/{session_name}/solo") as ws:
        assert ws.receive_json()["type"] == "welcome"

        monkeypatch.setattr(music_service, "start_playback", broken_start_playback)
        response = client.post("/start", json={"game_id": session_name})
        assert response.status_code == 500
        assert response.json() == {
            "detail": "Failed to play music. Please check if music service "
            "Mock Music Service is running!"
        }

        monkeypatch.undo()
        assert client.post("/start", json={"game_id": session_name}).status_code == 200
        assert ws.receive_json()["type"] == "your_turn"


def test_joining_twice_before_start_is_a_conflict(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """Joining under a registered name before start is a 409."""
    session_name = "double-join"
    create_and_join(session_name, "alex")

    response = client.post("/join", json={"game_id": session_name, "user_name": "alex"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Player 'alex' already registered"}


def test_creating_an_existing_session_is_a_conflict(
    client: TestClient, create_game: Callable[[str], None]
) -> None:
    """Creating a session with a taken ID is a 409."""
    create_game("taken")

    response = client.post(
        "/create",
        json={"game_id": "taken", "target_song_count": 2, "music_service_type": "mock"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Game session 'taken' already exists. Choose a different name."
    }


def test_starting_a_running_game_is_a_conflict_and_keeps_timelines(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """A second Start is a 409 and does not wipe the timelines."""
    session_name = "restart"
    create_and_join(session_name, "solo")

    with client.websocket_connect(f"/ws/{session_name}/solo") as ws:
        assert ws.receive_json()["type"] == "welcome"
        assert client.post("/start", json={"game_id": session_name}).status_code == 200
        assert ws.receive_json()["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 0})
        assert len(ws.receive_json()["song_list"]) == 1
        assert len(ws.receive_json()["song_list"]) == 1

        response = client.post("/start", json={"game_id": session_name})
        assert response.status_code == 409
        assert response.json() == {
            "detail": f"Game session {session_name} is already running."
        }

        ws.send_json({"type": "guess", "index": 1})
        result = ws.receive_json()
        assert result["type"] == "guess_result"
        assert len(result["song_list"]) == 2


def test_starting_with_unconnected_players_is_a_conflict_and_retryable(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    """Start names the unconnected players and leaves the game not running."""
    session_name = "half-start"
    create_and_join(session_name, "alex", "bo", "cy")

    with client.websocket_connect(f"/ws/{session_name}/alex") as ws_alex:
        assert ws_alex.receive_json()["type"] == "welcome"

        response = client.post("/start", json={"game_id": session_name})
        assert response.status_code == 409
        assert response.json() == {"detail": "Players not connected: bo, cy."}
        assert client.get("/list-sessions").json() == {"sessions": [session_name]}

        with (
            client.websocket_connect(f"/ws/{session_name}/bo") as ws_bo,
            client.websocket_connect(f"/ws/{session_name}/cy") as ws_cy,
        ):
            response = client.post("/start", json={"game_id": session_name})
            assert response.status_code == 200
            assert response.json() == {
                "message": f"Game session {session_name} started."
            }
            for ws in (ws_bo, ws_cy):
                assert ws.receive_json()["type"] == "welcome"
                assert ws.receive_json()["type"] == "your_turn"


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
