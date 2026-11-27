import json
import re

import httpx
from playwright.sync_api import Dialog, Page, Route, expect

from track_back.server.names import SESSION_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH

# The browser trims what is typed, so names with spaces at either end are left out.
NAMES = [
    "Дмитрий",
    "李雷",
    "Ελένη",
    "٣٤٥",
    "x²",
    "Ⅻ",
    "Anna-Lena_2",
    "Anna Lena",
    "Anna  Lena",
    "á",
    "a‿b",
    "tab\there",
    "semi;colon",
    "<script>",
]
USERNAMES = [*NAMES, "u" * USERNAME_MAX_LENGTH, "u" * (USERNAME_MAX_LENGTH + 1)]
SESSION_NAMES = [
    *NAMES,
    "g" * SESSION_NAME_MAX_LENGTH,
    "g" * (SESSION_NAME_MAX_LENGTH + 1),
]

USERNAME_RULE = re.compile(r"Usernames can have up to (\d+)")
SESSION_NAME_RULE = "Game Session Names can have up to"
DIALOG_WAIT_STEPS = 50
DIALOG_WAIT_STEP_MS = 100


def browser_accepts_username(page: Page, name: str) -> bool:
    messages: list[str] = []

    def record(dialog: Dialog) -> None:
        messages.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", record)
    try:
        page.get_by_label("Username").fill(name)
        page.get_by_role("button", name="Join a Game").click()
        for _ in range(DIALOG_WAIT_STEPS):
            if messages:
                break
            page.wait_for_timeout(DIALOG_WAIT_STEP_MS)
    finally:
        page.remove_listener("dialog", record)
    assert messages, f"No dialog after joining as {name!r}"
    return not USERNAME_RULE.search(messages[0])


def browser_accepts_session_name(page: Page, base_url: str, name: str) -> bool:
    page.goto(base_url)
    page.get_by_label("Username").fill("alice")
    page.get_by_role("button", name="Edit").click()
    page.get_by_label("Game Session Name").fill(name)
    page.get_by_role("button", name="Host a Game").click()
    outcome = page.get_by_text(
        re.compile(f"{SESSION_NAME_RULE}|Failed to create Game Session")
    ).first
    expect(outcome).to_be_visible()
    return SESSION_NAME_RULE not in outcome.inner_text()


def server_accepts_session_name(base_url: str, name: str) -> bool:
    response = httpx.post(
        f"{base_url}/create",
        json={"game_id": name, "target_song_count": 10, "music_service_type": "mock"},
    )
    return response.status_code != 422


def server_accepts_username(base_url: str, name: str) -> bool:
    response = httpx.post(
        f"{base_url}/join", json={"game_id": "names", "user_name": name}
    )
    return response.status_code != 422


def refuse_to_create(route: Route) -> None:
    route.fulfill(
        status=503,
        body=json.dumps({"detail": "Not now."}),
        content_type="application/json",
    )


def test_browser_and_server_agree_on_usernames(page: Page, base_url: str) -> None:
    page.goto(base_url)
    browser = {name: browser_accepts_username(page, name) for name in USERNAMES}

    assert server_accepts_session_name(base_url, "names")
    server = {name: server_accepts_username(base_url, name) for name in USERNAMES}

    assert browser == server


def test_browser_and_server_agree_on_session_names(page: Page, base_url: str) -> None:
    page.route("**/create", refuse_to_create)
    browser = {
        name: browser_accepts_session_name(page, base_url, name)
        for name in SESSION_NAMES
    }

    server = {
        name: server_accepts_session_name(base_url, name) for name in SESSION_NAMES
    }

    assert browser == server


def test_browser_follows_the_name_rules_the_server_serves(
    page: Page, base_url: str
) -> None:
    def serve_shorter_usernames(route: Route) -> None:
        config = json.loads(
            re.sub(r"^window\.TRACK_BACK_CONFIG = |;\s*$", "", route.fetch().text())
        )
        config["USERNAME_MAX_LENGTH"] = 5
        route.fulfill(
            body=f"window.TRACK_BACK_CONFIG = {json.dumps(config)};",
            content_type="text/javascript",
        )

    page.route("**/server_config.js", serve_shorter_usernames)
    page.goto(base_url)

    assert not browser_accepts_username(page, "alexa1")
    assert browser_accepts_username(page, "alexa")


def test_browser_falls_back_to_the_usual_name_rules(page: Page, base_url: str) -> None:
    page.route("**/server_config.js", lambda route: route.abort())
    page.goto(base_url)
    page.get_by_label("Server").fill(base_url)

    assert browser_accepts_username(page, "u" * USERNAME_MAX_LENGTH)
    assert not browser_accepts_username(page, "u" * (USERNAME_MAX_LENGTH + 1))
