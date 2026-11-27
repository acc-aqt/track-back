from collections.abc import Callable

from fastapi.testclient import TestClient

from track_back.server.game_sessions import GameSession

PLAYER_1 = "testplayer1"
PLAYER_2 = "testplayer2"


def _is_connected(session: GameSession, user_name: str) -> bool:
    player = session.game_logic.get_player(user_name)
    assert player is not None
    return player.is_connected


def test_connecting_players(
    client: TestClient,
    create_game: Callable[[str], None],
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "session-test-connecting-players"

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": []}

    create_game(game_id)

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [game_id]}

    response = client.post(
        "/join", json={"game_id": "non-existing-game-id", "user_name": PLAYER_1}
    )
    assert response.status_code == 404

    response = client.post("/join", json={"game_id": game_id, "user_name": PLAYER_1})
    assert response.status_code == 200

    response = client.post("/join", json={"game_id": game_id, "user_name": PLAYER_2})
    assert response.status_code == 200

    game_session = get_session(game_id)
    with (
        client.websocket_connect(f"/ws/{game_id}/{PLAYER_1}"),
        client.websocket_connect(f"/ws/{game_id}/{PLAYER_2}"),
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

        assert set(game_session.connection_manager.player_connections) == {
            PLAYER_1,
            PLAYER_2,
        }
        assert len(game_session.game_logic.players) == 2
        assert _is_connected(game_session, PLAYER_1) is True
        assert _is_connected(game_session, PLAYER_2) is True


def test_disconnecting_players(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "session-test-disconnecting-players"
    create_and_join(game_id, PLAYER_1, PLAYER_2)

    game_session = get_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{PLAYER_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{PLAYER_2}"):
            assert ws1.receive_json()["type"] == "welcome"

            client.post("/start", json={"game_id": game_id})

            assert ws1.receive_json()["type"] == "your_turn"

            assert set(game_session.connection_manager.player_connections) == {
                PLAYER_1,
                PLAYER_2,
            }
            assert len(game_session.game_logic.players) == 2
            assert _is_connected(game_session, PLAYER_1) is True
            assert _is_connected(game_session, PLAYER_2) is True

        assert ws1.receive_json()["type"] == "user_disconnected"

        assert set(game_session.connection_manager.player_connections) == {PLAYER_1}
        assert len(game_session.game_logic.players) == 2
        assert _is_connected(game_session, PLAYER_1) is True
        assert _is_connected(game_session, PLAYER_2) is False

    # the last player disconnecting keeps the running game for rejoin
    assert len(game_session.connection_manager.player_connections) == 0
    assert len(game_session.game_logic.players) == 2
    assert _is_connected(game_session, PLAYER_1) is False
    assert _is_connected(game_session, PLAYER_2) is False

    response = client.get("list-sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [game_id]}


def test_reconnect_after_disconnect(
    client: TestClient,
    create_and_join: Callable[..., None],
    get_session: Callable[[str], GameSession],
) -> None:
    game_id = "session-test-reconnect-after-disconnect"
    create_and_join(game_id, PLAYER_1, PLAYER_2)

    game_session = get_session(game_id)
    with client.websocket_connect(f"/ws/{game_id}/{PLAYER_1}") as ws1:
        with client.websocket_connect(f"/ws/{game_id}/{PLAYER_2}"):
            assert ws1.receive_json()["type"] == "welcome"

            client.post("/start", json={"game_id": game_id})
            assert client.get("list-sessions").json() == {"sessions": []}

            assert ws1.receive_json()["type"] == "your_turn"

        assert ws1.receive_json()["type"] == "user_disconnected"
        assert client.get("list-sessions").json() == {"sessions": [game_id]}

        for name, expected_status in [
            ("unknown_user", 409),
            (PLAYER_1, 409),
            (PLAYER_2, 200),
        ]:
            response = client.post(
                "/join", json={"game_id": game_id, "user_name": name}
            )
            assert response.status_code == expected_status

        # /join on a running game only checks; the WebSocket connect rejoins
        assert set(game_session.connection_manager.player_connections) == {PLAYER_1}
        assert _is_connected(game_session, PLAYER_2) is False
        assert client.get("list-sessions").json() == {"sessions": [game_id]}

        with client.websocket_connect(f"/ws/{game_id}/{PLAYER_2}") as ws2:
            assert ws2.receive_json()["type"] == "welcome"
            assert ws2.receive_json()["type"] == "your_turn"
            assert ws1.receive_json()["type"] == "player_rejoined"
            assert _is_connected(game_session, PLAYER_2) is True
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

        with client.websocket_connect(f"/ws/{game_id}/{PLAYER_2}") as ws2:
            assert ws2.receive_json()["type"] == "welcome"
            assert ws2.receive_json()["type"] == "player_rejoined"

            # already guessed this round
            ws2.send_json({"type": "guess", "index": 0})
            assert ws2.receive_json()["type"] == "error"
