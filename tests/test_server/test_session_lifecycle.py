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


def test_starting_a_running_game_is_a_conflict_and_keeps_timelines(
    client: TestClient,
) -> None:
    """A second Start is a 409 and does not wipe the timelines."""
    game_id = "restart"
    _create_and_join(client, game_id, "solo")

    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert json.loads(ws.receive_text())["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert json.loads(ws.receive_text())["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 0})
        assert len(json.loads(ws.receive_text())["song_list"]) == 1
        assert len(json.loads(ws.receive_text())["song_list"]) == 1

        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 409
        assert response.json() == {"detail": f"Game {game_id} is already running."}

        ws.send_json({"type": "guess", "index": 1})
        result = json.loads(ws.receive_text())
        assert result["type"] == "guess_result"
        assert len(result["song_list"]) == 2


def test_starting_with_unconnected_players_is_a_conflict_and_retryable(
    client: TestClient,
) -> None:
    """Start names the unconnected players, leaves the game not running."""
    game_id = "half-start"
    _create_and_join(client, game_id, "alex")
    for user in ("bo", "cy"):
        client.post("/join", json={"game_id": game_id, "user_name": user})

    with client.websocket_connect(f"/ws/{game_id}/alex") as ws_alex:
        assert json.loads(ws_alex.receive_text())["type"] == "welcome"

        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 409
        assert response.json() == {"detail": "Players not connected: bo, cy."}
        assert client.get("/list-sessions").json() == {"sessions": [game_id]}

        with (
            client.websocket_connect(f"/ws/{game_id}/bo") as ws_bo,
            client.websocket_connect(f"/ws/{game_id}/cy") as ws_cy,
        ):
            response = client.post("/start", json={"game_id": game_id})
            assert response.status_code == 200
            assert response.json() == {"message": f"Game {game_id} started."}
            for ws in (ws_bo, ws_cy):
                assert json.loads(ws.receive_text())["type"] == "welcome"
                assert json.loads(ws.receive_text())["type"] == "your_turn"
