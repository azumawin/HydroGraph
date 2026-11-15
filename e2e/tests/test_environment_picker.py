"""The picker that opens the app: the demo starts by choosing where it runs.

The mission environment decides the gravity, how late a result arrives, the
light-dark cycle the circadian findings rest on and the dose rate a radiation
spike is graded against, so the demo asks before showing any telemetry. The
choice is per page load: a reload asks again rather than resuming somewhere
nobody picked.
"""

import re

import dashboard as ui
import httpx
from conftest import Backend
from playwright.sync_api import Page, expect

ENVIRONMENTS = {
    "ISS, low Earth orbit": ("iss_leo", ["0 g", "1.2 s", "1.52 h", "14.6 µSv/h"]),
    "Lunar surface": ("lunar_surface", ["0.17 g", "2.6 s", "29.53 days", "57.1 µSv/h"]),
    "Mars transit": ("mars_transit", ["0 g", "26 min", "24 h", "76.7 µSv/h"]),
    "Mars surface": ("mars_surface", ["0.38 g", "26 min", "24.66 h", "26.7 µSv/h"]),
}


def current_environment(backend: Backend) -> str:
    return httpx.get(f"{backend.url}/api/environment/").json()["id"]


def test_the_app_opens_on_the_picker_and_shows_nothing_until_a_choice(
    page: Page, frontend: str, backend: Backend
) -> None:
    page.goto(frontend)

    expect(page.locator(".vitals-dashboard-environment-picker")).to_be_visible()
    # No telemetry, and nothing to navigate or switch, before a choice is made.
    expect(page.locator(".vitals-dashboard-reading")).to_have_count(0)
    expect(page.locator(".vitals-dashboard-measurement")).to_have_count(0)
    expect(page.locator(".vitals-dashboard-finding")).to_have_count(0)
    expect(page.get_by_role("tablist")).to_have_count(0)
    expect(ui.environment_select(page)).to_have_count(0)

    ui.enter(page)

    expect(page.get_by_role("tab", name="Vitals")).to_be_visible()
    expect(ui.environment_select(page)).to_have_value("iss_leo")
    expect(ui.vital(page, "Heart rate")).to_be_visible()


def test_every_environment_has_a_card_with_its_picture_and_what_it_sets(
    page: Page, frontend: str, backend: Backend
) -> None:
    page.goto(frontend)
    cards = page.locator(".vitals-dashboard-environment-card")
    expect(cards).to_have_count(len(ENVIRONMENTS))

    for name, (environment, facts) in ENVIRONMENTS.items():
        card = ui.environment_card(page, name)
        expect(card).to_have_attribute("data-environment", environment)
        # An illustration of the setting, hidden from the accessible name.
        expect(card.locator("img")).to_have_attribute("alt", "")
        for fact in facts:
            expect(card).to_contain_text(fact)
        # What the choice does to the demo, from the environment's own numbers.
        expect(card).to_contain_text("A dose-rate spike is graded above")
        expect(card).to_contain_text("after they are taken")

    # The one the backend already holds is marked; the others are not.
    expect(ui.environment_card(page, "ISS, low Earth orbit")).to_contain_text("In effect")
    expect(ui.environment_card(page, "Mars transit")).not_to_contain_text("In effect")


def test_choosing_applies_the_environment_everywhere(
    page: Page, frontend: str, backend: Backend
) -> None:
    page.goto(frontend)
    ui.enter(page, "Mars transit")

    assert current_environment(backend) == "mars_transit"
    expect(ui.environment_select(page)).to_have_value("mars_transit")
    expect(ui.root(page)).to_have_class(re.compile(r"\bis-environment-mars_transit\b"))
    expect(ui.environment_facts(page)).to_contain_text("76.7 µSv/h")


def test_a_reload_asks_again_and_keeps_the_last_choice_marked(
    page: Page, frontend: str, backend: Backend
) -> None:
    page.goto(frontend)
    ui.enter(page, "Lunar surface")
    expect(ui.environment_select(page)).to_have_value("lunar_surface")

    page.reload()

    expect(page.locator(".vitals-dashboard-environment-picker")).to_be_visible()
    expect(ui.environment_select(page)).to_have_count(0)
    expect(ui.environment_card(page, "Lunar surface")).to_contain_text("In effect")
    assert current_environment(backend) == "lunar_surface", "the reload changed nothing"

    # A different choice from the picker replaces it.
    ui.enter(page, "Mars surface")
    assert current_environment(backend) == "mars_surface"
