"""Tests that the list of joinable Game Sessions follows the join rules."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession


def _receive(ws: WebSocketTestSession) -> dict[str, Any]:
    message: dict[str, Any] = ws.receive_json()
    return message


def _receive_until(ws: WebSocketTestSession, message_type: str) -> dict[str, Any]:
    while (message := _receive(ws))["type"] != message_type:
        pass
    return message


def _listed(client: TestClient, session_name: str) -> bool:
    sessions: list[str] = client.get("/list-sessions").json()["sessions"]
    return session_name in sessions


def _join(client: TestClient, session_name: str, username: str) -> int:
    response = client.post(
        "/join", json={"game_id": session_name, "user_name": username}
    )
    status: int = response.status_code
    return status


def test_lobby_is_listed_and_joinable(
    client: TestClient, create_game: Callable[[str], None]
) -> None:
    create_game("lobby")

    assert _listed(client, "lobby")
    assert _join(client, "lobby", "newcomer") == 200


def test_running_game_is_listed_exactly_while_a_player_can_rejoin(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    create_and_join("running", "alice", "bob")
    with client.websocket_connect("/ws/running/alice") as alice:
        assert _receive(alice)["type"] == "welcome"
        with client.websocket_connect("/ws/running/bob"):
            assert client.post("/start", json={"game_id": "running"}).status_code == 200

            assert not _listed(client, "running")
            assert _join(client, "running", "alice") == 409
            assert _join(client, "running", "bob") == 409
            assert _join(client, "running", "newcomer") == 409

        assert _listed(client, "running")
        assert _join(client, "running", "bob") == 200
        assert _join(client, "running", "newcomer") == 409


def test_game_with_a_winner_is_neither_listed_nor_joinable_nor_startable(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    create_and_join("finished", "alice", "bob")
    with client.websocket_connect("/ws/finished/alice") as alice:
        assert _receive(alice)["type"] == "welcome"
        with client.websocket_connect("/ws/finished/bob") as bob:
            assert _receive(bob)["type"] == "welcome"
            assert (
                client.post("/start", json={"game_id": "finished"}).status_code == 200
            )
            alice.send_json({"type": "guess", "index": 0})
            bob.send_json({"type": "guess", "index": 0})
            _receive_until(bob, "guess_result")
            _receive_until(bob, "your_turn")
            bob.send_json({"type": "guess", "index": 1})
            assert _receive_until(bob, "guess_result")["game_over"] is True
            assert (
                client.post("/start", json={"game_id": "finished"}).status_code == 409
            )

        assert not _listed(client, "finished")
        assert _join(client, "finished", "bob") == 409
        assert _join(client, "finished", "newcomer") == 409
