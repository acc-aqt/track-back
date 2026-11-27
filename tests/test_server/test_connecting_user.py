from collections.abc import Callable

from fastapi.testclient import TestClient

from server.game_sessions import GameSession

USER_1 = "testuser1"
USER_2 = "testuser2"


def _is_active(session: GameSession, user_name: str) -> bool:
    user = session.game_logic.get_user(user_name)
    assert user is not None
    return user.is_active


def test_connecting_users(
    client: TestClient,
    create_game: Callable[[str], None],
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "session-test-connecting-users"

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": []}

    create_game(game_id)

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [game_id]}

    response = client.post(
        "/join", json={"game_id": "non-existing-game-id", "user_name": USER_1}
    )
    assert response.status_code == 404

    response = client.post("/join", json={"game_id": game_id, "user_name": USER_1})
    assert response.status_code == 200

    response = client.post("/join", json={"game_id": game_id, "user_name": USER_2})
    assert response.status_code == 200

    game_session = get_session(game_id)
    with (
        client.websocket_connect(f"/ws/{game_id}/{USER_1}"),
        client.websocket_connect(f"/ws/{game_id}/{USER_2}"),
    ):
        response = client.post("/start", json={"game_id": "non-existing-game-id"})
        assert response.status_code == 404

        response = client.get("list-sessions")
        assert response.status_code == 200
        assert response.json() == {"sessions": [game_id]}

        response = client.post("/start", json={"game_id": game_id})
        assert response.status_code == 200

        # a running game is no longer joinable
        response = client.get("list-sessions")
        assert response.status_code == 200
        assert response.json() == {"sessions": []}

        assert set(game_session.connection_manager.user_connections) == {
            USER_1,
            USER_2,
        }
        assert len(game_session.game_logic.users) == 2
        assert _is_active(game_session, USER_1) is True
        assert _is_active(game_session, USER_2) is True


def test_disconnecting_users(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "session-test-disconnecting-users"
    create_and_join(game_id, USER_1, USER_2)

    game_session = get_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{USER_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{USER_2}"):
            assert ws1.receive_json()["type"] == "welcome"

            client.post("/start", json={"game_id": game_id})

            assert ws1.receive_json()["type"] == "your_turn"

            assert set(game_session.connection_manager.user_connections) == {
                USER_1,
                USER_2,
            }
            assert len(game_session.game_logic.users) == 2
            assert _is_active(game_session, USER_1) is True
            assert _is_active(game_session, USER_2) is True

        assert ws1.receive_json()["type"] == "user_disconnected"

        assert set(game_session.connection_manager.user_connections) == {USER_1}
        assert len(game_session.game_logic.users) == 2
        assert _is_active(game_session, USER_1) is True
        assert _is_active(game_session, USER_2) is False

    # the last user disconnecting keeps the running game for rejoin
    assert len(game_session.connection_manager.user_connections) == 0
    assert len(game_session.game_logic.users) == 2
    assert _is_active(game_session, USER_1) is False
    assert _is_active(game_session, USER_2) is False

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [game_id]}


def test_reconnect_after_disconnect(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "session-test-reconnect-after-disconnect"
    create_and_join(game_id, USER_1, USER_2)

    game_session = get_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{USER_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{USER_2}"):
            assert ws1.receive_json()["type"] == "welcome"

            client.post("/start", json={"game_id": game_id})
            assert client.get("list-sessions").json() == {"sessions": []}

            assert ws1.receive_json()["type"] == "your_turn"

        assert ws1.receive_json()["type"] == "user_disconnected"
        assert client.get("list-sessions").json() == {"sessions": [game_id]}

        for name, expected_status in [
            ("unknown_user", 409),
            (USER_1, 409),
            (USER_2, 200),
        ]:
            response = client.post(
                "/join", json={"game_id": game_id, "user_name": name}
            )
            assert response.status_code == expected_status

        # /join on a running game only checks; the WebSocket connect rejoins
        assert set(game_session.connection_manager.user_connections) == {USER_1}
        assert _is_active(game_session, USER_2) is False
        assert client.get("list-sessions").json() == {"sessions": [game_id]}

        with client.websocket_connect(f"/ws/{game_id}/{USER_2}") as ws2:
            assert ws2.receive_json()["type"] == "welcome"
            assert ws2.receive_json()["type"] == "your_turn"
            assert ws1.receive_json()["type"] == "player_rejoined"
            assert _is_active(game_session, USER_2) is True
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

        with client.websocket_connect(f"/ws/{game_id}/{USER_2}") as ws2:
            assert ws2.receive_json()["type"] == "welcome"
            assert ws2.receive_json()["type"] == "player_rejoined"

            # already guessed this round
            ws2.send_json({"type": "guess", "index": 0})
            assert ws2.receive_json()["type"] == "error"
