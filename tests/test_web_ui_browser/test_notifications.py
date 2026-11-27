from playwright.sync_api import Page, expect


def test_notifications_say_nothing_yet_until_the_first_message(
    page: Page, base_url: str
) -> None:
    page.goto(base_url)
    expect(page.get_by_text("No notifications yet")).to_be_visible()

    page.get_by_label("Username").fill("alice")
    page.get_by_role("button", name="Host a").click()

    expect(page.get_by_text("Joined game: Game-by-alice")).to_be_visible()
    expect(page.get_by_text("No notifications yet")).to_have_count(0)
