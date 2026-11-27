from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

PLAYER_1 = "testplayer1"
PLAYER_2 = "testplayer2"


def _assert_guess_result(
    response: dict[str, Any],
    result: str,
    song_count: int,
    last_index: str,
    winner: str = "",
) -> None:
    assert response["type"] == "guess_result"
    assert response["result"] == result
    assert len(response["song_list"]) == song_count
    assert response["last_index"] == last_index
    assert len(response["other_players"]) == 1
    assert response["game_over"] is bool(winner)
    assert response["winner"] == winner


def test_full_game_client_connection(
    client: TestClient,
    create_game: Callable[[str], None],
) -> None:
    session_name = "test-session-123"
    create_game(session_name)

    response = client.post(
        "/create",
        json={
            "game_id": session_name,
            "target_song_count": 2,
            "music_service_type": "mock",
        },
    )
    assert response.status_code == 409

    response = client.post("/start", json={"game_id": session_name})
    assert response.status_code == 400

    response = client.post(
        "/join", json={"game_id": session_name, "user_name": PLAYER_1}
    )
    assert response.status_code == 200

    response = client.post(
        "/join", json={"game_id": session_name, "user_name": PLAYER_1}
    )
    assert response.status_code == 409

    response = client.post(
        "/join", json={"game_id": session_name, "user_name": PLAYER_2}
    )
    assert response.status_code == 200

    with (
        client.websocket_connect(f"/ws/{session_name}/{PLAYER_1}") as ws1,
        client.websocket_connect(f"/ws/{session_name}/{PLAYER_2}") as ws2,
    ):
        assert ws1.receive_json()["type"] == "welcome"
        assert ws2.receive_json()["type"] == "welcome"

        response = client.post("/start", json={"game_id": session_name})
        assert response.status_code == 200
        assert "type" not in response.json()
        assert ws1.receive_json()["type"] == "your_turn"
        assert ws2.receive_json()["type"] == "your_turn"

        ws1.send_json({"type": "guess", "index": 0})
        first_guess = ws1.receive_json()
        _assert_guess_result(first_guess, "correct", 1, "0")
        assert first_guess["last_song"]["release_year"] == 1965
        assert ws2.receive_json()["type"] == "other_player_guess"

        # player 1 already guessed this round
        ws1.send_json({"type": "guess", "index": 0})
        assert ws1.receive_json()["type"] == "error"

        ws2.send_json({"type": "guess", "index": 0})
        _assert_guess_result(ws2.receive_json(), "correct", 1, "0")
        assert ws1.receive_json()["type"] == "other_player_guess"

        assert ws1.receive_json()["type"] == "your_turn"
        assert ws2.receive_json()["type"] == "your_turn"

        # the mock service delivers songs with increasing release years
        ws1.send_json({"type": "guess", "index": 0})
        _assert_guess_result(ws1.receive_json(), "wrong", 1, "0")
        assert ws2.receive_json()["type"] == "other_player_guess"

        ws2.send_json({"type": "guess", "index": 1})
        _assert_guess_result(ws2.receive_json(), "correct", 2, "1", winner=PLAYER_2)
