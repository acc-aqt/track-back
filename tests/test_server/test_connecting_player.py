from collections.abc import Callable

from fastapi.testclient import TestClient

PLAYER_1 = "testplayer1"
PLAYER_2 = "testplayer2"


def _join_status(client: TestClient, session_name: str, user_name: str) -> int:
    response = client.post(
        "/join", json={"game_id": session_name, "user_name": user_name}
    )
    status: int = response.status_code
    return status


def test_connecting_players(
    client: TestClient,
    create_game: Callable[[str], None],
) -> None:
    session_name = "session-test-connecting-players"

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": []}

    create_game(session_name)

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [session_name]}

    response = client.post(
        "/join", json={"game_id": "non-existing-game-id", "user_name": PLAYER_1}
    )
    assert response.status_code == 404

    response = client.post(
        "/join", json={"game_id": session_name, "user_name": PLAYER_1}
    )
    assert response.status_code == 200

    response = client.post(
        "/join", json={"game_id": session_name, "user_name": PLAYER_2}
    )
    assert response.status_code == 200

    with (
        client.websocket_connect(f"/ws/{session_name}/{PLAYER_1}"),
        client.websocket_connect(f"/ws/{session_name}/{PLAYER_2}"),
    ):
        response = client.post("/start", json={"game_id": "non-existing-game-id"})
        assert response.status_code == 404

        response = client.get("list-sessions")
        assert response.status_code == 200
        assert response.json() == {"sessions": [session_name]}

        response = client.post("/start", json={"game_id": session_name})
        assert response.status_code == 200

        # a running game is no longer joinable
        response = client.get("list-sessions")
        assert response.status_code == 200
        assert response.json() == {"sessions": []}

        assert _join_status(client, session_name, PLAYER_1) == 409
        assert _join_status(client, session_name, PLAYER_2) == 409


def test_disconnecting_players(
    client: TestClient,
    create_and_join: Callable[..., None],
) -> None:
    session_name = "session-test-disconnecting-players"
    create_and_join(session_name, PLAYER_1, PLAYER_2)

    with client.websocket_connect(f"/ws/{session_name}/{PLAYER_1}") as ws1:
        with client.websocket_connect(f"/ws/{session_name}/{PLAYER_2}"):
            assert ws1.receive_json()["type"] == "welcome"

            client.post("/start", json={"game_id": session_name})

            assert ws1.receive_json()["type"] == "your_turn"

            assert _join_status(client, session_name, PLAYER_1) == 409
            assert _join_status(client, session_name, PLAYER_2) == 409

        assert ws1.receive_json()["type"] == "user_disconnected"

        assert _join_status(client, session_name, PLAYER_1) == 409
        assert _join_status(client, session_name, PLAYER_2) == 200

    # the last player disconnecting keeps the running game for rejoin
    assert _join_status(client, session_name, PLAYER_1) == 200
    assert _join_status(client, session_name, PLAYER_2) == 200
    assert _join_status(client, session_name, "newcomer") == 409

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [session_name]}


def test_reconnect_after_disconnect(
    client: TestClient,
    create_and_join: Callable[..., None],
) -> None:
    session_name = "session-test-reconnect-after-disconnect"
    create_and_join(session_name, PLAYER_1, PLAYER_2)

    with client.websocket_connect(f"/ws/{session_name}/{PLAYER_1}") as ws1:
        with client.websocket_connect(f"/ws/{session_name}/{PLAYER_2}"):
            assert ws1.receive_json()["type"] == "welcome"

            client.post("/start", json={"game_id": session_name})
            assert client.get("list-sessions").json() == {"sessions": []}

            assert ws1.receive_json()["type"] == "your_turn"

        assert ws1.receive_json()["type"] == "user_disconnected"
        assert client.get("list-sessions").json() == {"sessions": [session_name]}

        for name, expected_status in [
            ("unknown_user", 409),
            (PLAYER_1, 409),
            (PLAYER_2, 200),
        ]:
            response = client.post(
                "/join", json={"game_id": session_name, "user_name": name}
            )
            assert response.status_code == expected_status

        # /join on a running game only checks; the WebSocket connect rejoins
        assert client.get("list-sessions").json() == {"sessions": [session_name]}

        with client.websocket_connect(f"/ws/{session_name}/{PLAYER_2}") as ws2:
            assert ws2.receive_json()["type"] == "welcome"
            assert ws2.receive_json()["type"] == "your_turn"
            assert ws1.receive_json()["type"] == "player_rejoined"
            assert _join_status(client, session_name, PLAYER_2) == 409
            assert client.get("list-sessions").json() == {"sessions": []}

            ws2.send_json({"type": "guess", "index": 0})
            guess_result = ws2.receive_json()
            assert guess_result["type"] == "guess_result"
            assert guess_result["result"] == "correct"
            assert len(guess_result["song_list"]) == 1
            assert guess_result["last_index"] == "0"
            assert len(guess_result["other_players"]) == 1
            assert guess_result["game_over"] is False
            assert guess_result["winner"] == ""

        assert ws1.receive_json()["type"] == "other_player_guess"

        with client.websocket_connect(f"/ws/{session_name}/{PLAYER_2}") as ws2:
            assert ws2.receive_json()["type"] == "welcome"
            assert ws2.receive_json()["type"] == "player_rejoined"

            # already guessed this round
            ws2.send_json({"type": "guess", "index": 0})
            assert ws2.receive_json()["type"] == "error"


def test_closing_a_lobby_tab_keeps_the_other_tab_with_the_same_name(
    client: TestClient, create_and_join: Callable[..., None]
) -> None:
    session_name = "two-tabs"
    create_and_join(session_name, "alice")
    with (
        client.websocket_connect(f"/ws/{session_name}/alice") as first_tab,
        client.websocket_connect(f"/ws/{session_name}/alice") as second_tab,
    ):
        assert first_tab.receive_json()["type"] == "welcome"
        assert second_tab.receive_json()["type"] == "welcome"

        first_tab.close()

        assert client.post("/start", json={"game_id": session_name}).status_code == 200
        assert second_tab.receive_json()["type"] == "your_turn"
