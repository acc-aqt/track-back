import json
import re

from playwright.sync_api import Page, WebSocketRoute, expect

# The first reconnect waits 2 s; wait a little longer.
FIRST_RECONNECT_MS = 2500
MESSAGE_ARRIVAL_MS = 200
SONG = {"title": "Song", "artist": "Artist", "release_year": 1999}


def host_a_game_with_a_fake_socket(page: Page, base_url: str) -> list[WebSocketRoute]:
    sockets: list[WebSocketRoute] = []

    def record(ws: WebSocketRoute) -> None:
        sockets.append(ws)

    page.route_web_socket(re.compile(r"/ws/"), record)
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    page.get_by_role("button", name="Host a Game").click()
    expect(page.get_by_text("Connected to game session.")).to_be_visible()
    return sockets


def test_coming_back_online_while_a_reconnect_waits_opens_one_socket(
    page: Page, base_url: str
) -> None:
    sockets = host_a_game_with_a_fake_socket(page, base_url)
    sockets[0].close()
    expect(page.get_by_text("Attempting to reconnect")).to_be_visible()

    page.evaluate("window.dispatchEvent(new Event('online'))")
    page.wait_for_timeout(FIRST_RECONNECT_MS)

    assert len(sockets) == 2


def test_a_guess_made_while_disconnected_can_be_made_again(
    page: Page, base_url: str
) -> None:
    sockets = host_a_game_with_a_fake_socket(page, base_url)
    sockets[0].send(json.dumps({"type": "your_turn", "song_list": [SONG]}))
    new_song = page.get_by_text("Drag the song to the right place in the timeline.")
    expect(new_song).to_be_visible()
    sockets[0].close()
    expect(page.get_by_text("Attempting to reconnect")).to_be_visible()

    new_song.drag_to(page.locator("#songTimeline"))

    expect(page.get_by_text("Not connected to the server")).to_be_visible()
    expect(new_song).to_be_visible()

    page.wait_for_timeout(FIRST_RECONNECT_MS)
    assert len(sockets) == 2
    messages: list[dict[str, object]] = []
    sockets[1].on_message(lambda message: messages.append(json.loads(message)))
    new_song.drag_to(page.locator("#songTimeline"))

    expect(new_song).to_be_hidden()
    page.wait_for_timeout(MESSAGE_ARRIVAL_MS)
    assert [m["type"] for m in messages if m["type"] == "guess"] == ["guess"]
