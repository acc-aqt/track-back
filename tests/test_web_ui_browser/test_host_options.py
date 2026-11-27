import re

import httpx
from playwright.sync_api import Dialog, Locator, Page, expect


def host_options_strip(page: Page) -> Locator:
    return page.get_by_role("button", name=re.compile(r"· Edit$", re.IGNORECASE))


def test_strip_shows_the_default_host_options(page: Page, base_url: str) -> None:
    page.goto(base_url)

    strip = page.get_by_role(
        "button", name=re.compile(r"10 songs · Mock · Edit", re.IGNORECASE)
    )
    expect(strip).to_be_visible()
    expect(strip).to_have_attribute("aria-expanded", "false")


def test_strip_opens_and_closes_host_options(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    strip = host_options_strip(page)

    strip.click()
    expect(strip).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_label("Target Song Count")).to_be_visible()
    expect(page.get_by_label("Game Session Name")).to_have_value("Game-by-alice")

    strip.click()
    expect(strip).to_have_attribute("aria-expanded", "false")
    expect(page.get_by_label("Target Song Count")).to_be_hidden()


def test_strip_opens_with_the_keyboard(page: Page, base_url: str) -> None:
    page.goto(base_url)
    strip = host_options_strip(page)

    strip.focus()
    page.keyboard.press("Enter")
    expect(strip).to_have_attribute("aria-expanded", "true")
    page.keyboard.press("Space")
    expect(strip).to_have_attribute("aria-expanded", "false")


def test_summary_follows_edits(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    host_options_strip(page).click()

    page.get_by_label("Target Song Count").fill("7")
    expect(host_options_strip(page)).to_have_accessible_name(
        re.compile(r"^7 songs · Mock · Edit$", re.IGNORECASE)
    )

    page.get_by_label("Game Session Name").fill("Friday Party")
    expect(host_options_strip(page)).to_have_accessible_name(
        re.compile(r"^7 songs · Mock · Friday Party · Edit$", re.IGNORECASE)
    )


def test_hosting_uses_values_edited_before_closing(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    host_options_strip(page).click()
    page.get_by_label("Game Session Name").fill("Friday Party")
    page.get_by_label("Target Song Count").fill("3")
    host_options_strip(page).click()

    page.get_by_role("button", name="Host a game").click()

    expect(page.get_by_role("button", name="Start!")).to_be_visible()
    expect(page.get_by_text("Joined game: Friday Party")).to_be_visible()
    sessions = httpx.get(f"{base_url}/list-sessions").json()["sessions"]
    assert sessions == ["Friday Party"]


def test_invalid_count_shows_an_inline_error_and_no_dialog(
    page: Page, base_url: str
) -> None:
    dialogs: list[str] = []

    def record(dialog: Dialog) -> None:
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", record)
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    host_options_strip(page).click()
    page.get_by_label("Target Song Count").fill("0")
    host_options_strip(page).click()

    page.get_by_role("button", name="Host a game").click()

    expect(page.get_by_role("alert")).to_contain_text("valid number greater than 0")
    expect(host_options_strip(page)).to_have_attribute("aria-expanded", "true")
    assert dialogs == []
    assert httpx.get(f"{base_url}/list-sessions").json()["sessions"] == []


def test_taken_name_opens_host_options_with_the_error(
    page: Page, base_url: str
) -> None:
    created = httpx.post(
        f"{base_url}/create",
        json={
            "game_id": "Game-by-alice",
            "target_song_count": 10,
            "music_service_type": "mock",
        },
    )
    assert created.is_success
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")

    page.get_by_role("button", name="Host a game").click()

    expect(page.get_by_role("alert")).to_contain_text("already exists")
    expect(host_options_strip(page)).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_label("Game Session Name")).to_be_visible()


def test_target_song_count_is_remembered_after_a_reload(
    page: Page, base_url: str
) -> None:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    host_options_strip(page).click()
    page.get_by_label("Target Song Count").fill("4")
    page.get_by_role("button", name="Host a game").click()
    expect(page.get_by_role("button", name="Start!")).to_be_visible()

    page.reload()

    expect(host_options_strip(page)).to_have_accessible_name(
        re.compile(r"^4 songs · Mock · Edit$", re.IGNORECASE)
    )
