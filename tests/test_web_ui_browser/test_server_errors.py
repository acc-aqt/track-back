from collections.abc import Callable

import httpx
import pytest
from playwright.sync_api import Dialog, Page, Route, expect

PROXY_ERROR_PAGE = "<html><body><h1>502 Bad Gateway</h1></body></html>"


def answer_with_a_proxy_error_page(route: Route) -> None:
    route.fulfill(status=502, body=PROXY_ERROR_PAGE, content_type="text/html")


def answer_with_a_captive_portal(route: Route) -> None:
    route.fulfill(status=200, body=PROXY_ERROR_PAGE, content_type="text/html")


def create_a_game_session(base_url: str, name: str) -> None:
    created = httpx.post(
        f"{base_url}/create",
        json={"game_id": name, "target_song_count": 10, "music_service_type": "mock"},
    )
    assert created.is_success


@pytest.fixture
def dialogs(page: Page) -> list[str]:
    messages: list[str] = []

    def record(dialog: Dialog) -> None:
        messages.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", record)
    return messages


def test_joining_shows_an_unexpected_response(
    page: Page, base_url: str, dialogs: list[str]
) -> None:
    create_a_game_session(base_url, "Friday Party")
    page.route("**/join", answer_with_a_proxy_error_page)
    page.goto(base_url)
    page.get_by_label("Username").fill("bob")

    page.get_by_role("button", name="Join a Game").click()

    expect(page.get_by_text("Failed to join game")).to_contain_text(
        "unexpected response (HTTP 502)"
    )
    expect(page.get_by_role("button", name="Join a Game")).to_be_visible()
    assert dialogs == []


def test_joining_shows_that_the_server_could_not_be_reached(
    page: Page, base_url: str
) -> None:
    create_a_game_session(base_url, "Friday Party")
    page.route("**/join", lambda route: route.abort())
    page.goto(base_url)
    page.get_by_label("Username").fill("bob")

    page.get_by_role("button", name="Join a Game").click()

    expect(page.get_by_text("Failed to join game")).to_contain_text(
        "the server could not be reached"
    )


def test_hosting_shows_an_unexpected_response(
    page: Page, base_url: str, dialogs: list[str]
) -> None:
    page.route("**/create", answer_with_a_proxy_error_page)
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")

    page.get_by_role("button", name="Host a Game").click()

    expect(page.get_by_text("Failed to create Game Session")).to_contain_text(
        "unexpected response (HTTP 502)"
    )
    expect(page.get_by_role("button", name="Start!")).to_be_hidden()
    assert dialogs == []


@pytest.mark.parametrize(
    "answer", [answer_with_a_proxy_error_page, answer_with_a_captive_portal]
)
def test_listing_game_sessions_shows_an_unexpected_response(
    page: Page, base_url: str, dialogs: list[str], answer: Callable[[Route], None]
) -> None:
    page.route("**/list-sessions", answer)
    page.goto(base_url)
    page.get_by_label("Username").fill("bob")

    page.get_by_role("button", name="Join a Game").click()

    expect(page.get_by_text("Failed to fetch game sessions")).to_contain_text(
        "unexpected response"
    )
    assert dialogs == []
