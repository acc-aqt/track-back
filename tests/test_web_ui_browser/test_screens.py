import json

from playwright.sync_api import Locator, Page, Route, expect


def screen_sections(page: Page) -> dict[str, list[Locator]]:
    return {
        "setup": [
            page.get_by_role("button", name="Host a Game"),
            page.get_by_role("button", name="Join a Game"),
        ],
        "Lobby": [
            page.get_by_text("Waiting for all players"),
            page.get_by_role("button", name="Start!"),
            page.get_by_alt_text("QR code to join this Game Session"),
        ],
        "playing": [
            page.get_by_text("Your TrackBack Timeline"),
            page.get_by_text("Song count:"),
        ],
        "game over": [page.get_by_text("You win!")],
    }


def expect_only_visible(page: Page, *screens: str) -> None:
    for screen, sections in screen_sections(page).items():
        for section in sections:
            if screen in screens:
                expect(section).to_be_visible()
            else:
                expect(section).to_be_hidden()


def host_a_game_to_one_song(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    page.get_by_role("button", name="Edit").click()
    page.get_by_label("Target Song Count").fill("1")
    page.get_by_role("button", name="Host a Game").click()


def answer_start_with_a_conflict(route: Route) -> None:
    route.fulfill(
        status=409,
        body=json.dumps({"detail": "Not every Player is connected."}),
        content_type="application/json",
    )


def test_a_failed_start_keeps_the_host_in_the_lobby(page: Page, base_url: str) -> None:
    page.route("**/start", answer_start_with_a_conflict)
    host_a_game_to_one_song(page, base_url)
    expect(page.get_by_text("Connected to game session.")).to_be_visible()

    page.get_by_role("button", name="Start!").click()

    expect(
        page.get_by_text("Failed to start game: Not every Player is connected.")
    ).to_be_visible()
    expect_only_visible(page, "Lobby")


def test_one_screen_is_visible_at_a_time(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect_only_visible(page, "setup")

    host_a_game_to_one_song(page, base_url)
    expect_only_visible(page, "Lobby")

    page.get_by_role("button", name="Start!").click()
    new_song = page.get_by_text("Drag the song to the right place in the timeline.")
    expect(new_song).to_be_visible()
    expect_only_visible(page, "playing")

    new_song.drag_to(page.locator("#songTimeline"))
    expect_only_visible(page, "playing", "game over")
    expect(new_song).to_be_hidden()
