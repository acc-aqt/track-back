from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from server.game_sessions import GameSession

USER_1 = "testuser1"
USER_2 = "testuser2"


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
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "test-session-123"
    create_game(game_id)
    game_session = get_session(game_id)

    assert game_session.game_logic.target_song_count == 2
    assert game_session.game_logic.music_service.service_name == "Mock Music Service"
    assert len(game_session.connection_manager.user_connections) == 0

    response = client.post(
        "/create",
        json={"game_id": game_id, "target_song_count": 2, "music_service_type": "mock"},
    )
    assert response.status_code == 409

    response = client.post("/start", json={"game_id": game_id})
    assert response.status_code == 400

    response = client.post("/join", json={"game_id": game_id, "user_name": USER_1})
    assert response.status_code == 200
    assert len(game_session.connection_manager.user_connections) == 1

    response = client.post("/join", json={"game_id": game_id, "user_name": USER_1})
    assert response.status_code == 409

    response = client.post("/join", json={"game_id": game_id, "user_name": USER_2})
    assert response.status_code == 200
    assert len(game_session.connection_manager.user_connections) == 2

    with (
        client.websocket_connect(f"/ws/{game_id}/{USER_1}") as ws1,
        client.websocket_connect(f"/ws/{game_id}/{USER_2}") as ws2,
    ):
        assert ws1.receive_json()["type"] == "welcome"
        assert ws2.receive_json()["type"] == "welcome"

        response = client.post("/start", json={"game_id": game_id})
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
        _assert_guess_result(ws2.receive_json(), "correct", 2, "1", winner=USER_2)
