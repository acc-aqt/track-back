from playwright.sync_api import Page, expect


def test_tabbing_to_a_text_field_shows_a_focus_outline(
    page: Page, base_url: str
) -> None:
    page.goto(base_url)
    username = page.get_by_label("Username")

    page.keyboard.press("Tab")

    expect(username).to_be_focused()
    expect(username).not_to_have_css("outline-style", "none")
    expect(username).to_have_css("outline-width", "3px")


def test_start_screen_controls_are_at_least_44px_tall(
    page: Page, base_url: str
) -> None:
    page.goto(base_url)

    controls = [
        page.get_by_label("Username"),
        page.get_by_role("button", name="Host a"),
        page.get_by_role("button", name="Join a"),
    ]

    for control in controls:
        box = control.bounding_box()
        assert box is not None
        assert box["height"] >= 44


def test_buttons_do_not_move_when_reduced_motion_is_requested(
    page: Page, base_url: str
) -> None:
    page.emulate_media(reduced_motion="reduce")
    page.goto(base_url)
    host_button = page.get_by_role("button", name="Host a")

    host_button.hover()

    expect(host_button).to_have_css("transform", "none")
    expect(host_button).to_have_css("transition-duration", "0s")
