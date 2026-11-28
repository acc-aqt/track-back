import json
import re
from urllib.parse import urlsplit

from playwright.sync_api import Locator, Page, Route, WebSocket, expect

GUESS_RESULT = re.compile(r"Guess was (correct|wrong)")


def notifications(page: Page) -> Locator:
    return page.locator("#log")


def guess_results(count: int) -> re.Pattern[str]:
    return re.compile(
        rf"^(?:(?:(?!Guess was).)*Guess was (?:correct|wrong)){{{count}}}(?:(?!Guess was).)*$",
        re.DOTALL,
    )


def new_song(page: Page) -> Locator:
    return page.get_by_text("Drag the song to the right place in the timeline.")


def start_a_game_alone(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    page.get_by_role("button", name="Host a Game").click()
    page.get_by_role("button", name="Start!").click()


def place_the_new_song(page: Page) -> None:
    new_song(page).drag_to(page.locator("#songTimeline"))


def test_a_song_can_be_placed_without_internet_access(
    page: Page, base_url: str
) -> None:
    server_host = urlsplit(base_url).netloc

    def block_outside_hosts(route: Route) -> None:
        if urlsplit(route.request.url).netloc == server_host:
            route.continue_()
        else:
            route.abort()

    page.route("**/*", block_outside_hosts)
    start_a_game_alone(page, base_url)

    place_the_new_song(page)

    expect(page.get_by_text(GUESS_RESULT)).to_be_visible()


def test_each_round_sends_exactly_one_guess(page: Page, base_url: str) -> None:
    guesses: list[dict[str, object]] = []

    def record_guesses(ws: WebSocket) -> None:
        def on_frame(payload: str | bytes) -> None:
            message = json.loads(payload)
            if message["type"] == "guess":
                guesses.append(message)

        ws.on("framesent", on_frame)

    page.on("websocket", record_guesses)
    start_a_game_alone(page, base_url)

    rounds = 3
    for played in range(1, rounds + 1):
        expect(new_song(page)).to_be_visible(timeout=10_000)
        place_the_new_song(page)
        expect(notifications(page)).to_have_text(guess_results(played))
        assert len(guesses) == played

    expect(page.get_by_text("already guessed")).to_have_count(0)
