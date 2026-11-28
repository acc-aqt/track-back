import re

from playwright.sync_api import Page, WebSocketRoute, expect

# The first reconnect waits 2 s; wait a little longer.
FIRST_RECONNECT_MS = 2500


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
