"""Tests for keeping a fully disconnected running game for a grace period."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from server.game_sessions import (
    EMPTY_SESSION_GRACE_PERIOD_SECONDS,
    game_session_manager,
)


def _receive(ws: WebSocketTestSession) -> dict[str, Any]:
    message: dict[str, Any] = ws.receive_json()
    return message


def _join(client: TestClient, game_id: str, user: str) -> int:
    response = client.post("/join", json={"game_id": game_id, "user_name": user})
    return response.status_code


def _start_solo_game_and_guess_once(
    client: TestClient, create_and_join: Callable[..., None], game_id: str
) -> None:
    create_and_join(game_id, "solo")
    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert _receive(ws)["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert _receive(ws)["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 0})
        assert _receive(ws)["type"] == "guess_result"
        assert _receive(ws)["type"] == "your_turn"


def test_solo_player_reconnects_and_finishes_the_game(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    game_id = "solo-comeback"
    _start_solo_game_and_guess_once(client, create_and_join, game_id)

    assert client.get("/list-sessions").json() == {"sessions": [game_id]}
    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert _receive(ws)["type"] == "welcome"
        assert _receive(ws)["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 1})
        result = _receive(ws)
        assert result["type"] == "guess_result"
        assert result["game_over"] is True
        while _receive(ws)["type"] != "game_over":
            pass


def test_whole_room_disconnects_rejoins_and_continues(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    game_id = "room-comeback"
    create_and_join(game_id, "alice", "bob")
    with client.websocket_connect(f"/ws/{game_id}/alice") as alice:
        assert _receive(alice)["type"] == "welcome"
        with client.websocket_connect(f"/ws/{game_id}/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            assert client.post("/start", json={"game_id": game_id}).status_code == 200
            assert _receive(alice)["type"] == "your_turn"
            assert _receive(bob)["type"] == "your_turn"
        assert _receive(alice)["type"] == "user_disconnected"

    assert client.get("/list-sessions").json() == {"sessions": [game_id]}
    with client.websocket_connect(f"/ws/{game_id}/alice") as alice:
        assert _receive(alice)["type"] == "welcome"
        assert _receive(alice)["type"] == "your_turn"
        with client.websocket_connect(f"/ws/{game_id}/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            assert _receive(bob)["type"] == "your_turn"
            assert _receive(alice)["type"] == "player_rejoined"

            alice.send_json({"type": "guess", "index": 0})
            assert _receive(alice)["type"] == "guess_result"
            assert _receive(bob)["type"] == "other_player_guess"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fake_clock = FakeClock()
    monkeypatch.setattr(game_session_manager, "clock", fake_clock)
    return fake_clock


def test_empty_session_is_kept_within_the_grace_period(
    client: TestClient, create_and_join: Callable[..., None], clock: FakeClock
) -> None:
    game_id = "still-waiting"
    _start_solo_game_and_guess_once(client, create_and_join, game_id)

    clock.now += EMPTY_SESSION_GRACE_PERIOD_SECONDS
    assert client.get("/list-sessions").json() == {"sessions": [game_id]}
    assert _join(client, game_id, "solo") == 200


def test_empty_session_past_the_grace_period_is_removed(
    client: TestClient,
    create_and_join: Callable[..., None],
    create_game: Callable[[str], None],
    clock: FakeClock,
) -> None:
    _start_solo_game_and_guess_once(client, create_and_join, "listed")
    clock.now += EMPTY_SESSION_GRACE_PERIOD_SECONDS + 1
    assert client.get("/list-sessions").json() == {"sessions": []}

    _start_solo_game_and_guess_once(client, create_and_join, "joined")
    clock.now += EMPTY_SESSION_GRACE_PERIOD_SECONDS + 1
    assert _join(client, "joined", "solo") == 404

    _start_solo_game_and_guess_once(client, create_and_join, "recreated")
    clock.now += EMPTY_SESSION_GRACE_PERIOD_SECONDS + 1
    create_game("recreated")


def test_finished_game_is_removed_when_its_last_player_leaves(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    game_id = "finished-and-gone"
    create_and_join(game_id, "solo")
    with client.websocket_connect(f"/ws/{game_id}/solo") as ws:
        assert _receive(ws)["type"] == "welcome"
        assert client.post("/start", json={"game_id": game_id}).status_code == 200
        assert _receive(ws)["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 0})
        assert _receive(ws)["type"] == "guess_result"
        assert _receive(ws)["type"] == "your_turn"
        ws.send_json({"type": "guess", "index": 1})
        while _receive(ws)["type"] != "game_over":
            pass
        assert _join(client, game_id, "solo") == 409

        ws.close()
        assert _join(client, game_id, "solo") == 404
