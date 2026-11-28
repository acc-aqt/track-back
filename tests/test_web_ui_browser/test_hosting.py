import httpx
from playwright.sync_api import Page, expect


def test_hosting_with_defaults_lands_in_the_lobby(page: Page, base_url: str) -> None:
    page.goto(base_url)

    page.get_by_label("Username").fill("alice")
    page.get_by_role("button", name="Host a game").click()

    expect(page.get_by_role("button", name="Start!")).to_be_visible()
    expect(page.get_by_text("Joined game: Game-by-alice")).to_be_visible()
    sessions = httpx.get(f"{base_url}/list-sessions").json()["sessions"]
    assert sessions == ["Game-by-alice"]


def test_hosting_works_with_a_typed_in_relative_server_url(
    page: Page, base_url: str
) -> None:
    page.route("**/server_config.js", lambda route: route.abort())
    page.route("http://localhost:4200/**", lambda route: route.abort())
    page.goto(base_url)
    page.get_by_label("Server").fill("")
    page.get_by_label("Username").fill("alice")

    page.get_by_role("button", name="Host a Game").click()

    expect(page.get_by_role("button", name="Start!")).to_be_visible()
    expect(page.get_by_text("Connected to game session.")).to_be_visible()
