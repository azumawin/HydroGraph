"""Read the dashboard the way a person does: by labels, not internals."""

import re

from playwright.sync_api import Locator, Page, expect

POINTS = re.compile(r"(\d+) recorded timestamps")
DEFAULT_ENVIRONMENT = "ISS, low Earth orbit"


def environment_card(page: Page, name: str) -> Locator:
    """One mission environment's card on the picker that opens the app."""
    heading = page.locator(
        ".vitals-dashboard-environment-card-name", has_text=re.compile(f"^{re.escape(name)}$")
    )
    return page.locator(".vitals-dashboard-environment-card").filter(has=heading)


def enter(page: Page, name: str = DEFAULT_ENVIRONMENT) -> None:
    """Choose a mission environment, leaving the dashboard open behind it.

    Every page load starts on the picker: the choice is per load, so a reload
    asks again. Choosing the environment already in effect changes nothing.
    """
    card = environment_card(page, name)
    expect(card).to_be_visible(timeout=15000)
    card.click()
    expect(page.locator(".vitals-dashboard-environment-picker")).to_have_count(0)


def vital(page: Page, label: str) -> Locator:
    """One row of the Vitals panel, e.g. "Heart rate"."""
    heading = page.locator(".vitals-dashboard-reading-label", has_text=re.compile(f"^{label}$"))
    return page.locator(".vitals-dashboard-reading").filter(has=heading)


def value(row: Locator) -> Locator:
    return row.locator(".vitals-dashboard-reading-value")


def unit(row: Locator) -> Locator:
    return row.locator(".vitals-dashboard-reading-unit")


def status(row: Locator) -> Locator:
    return row.locator(".vitals-dashboard-reading-status")


def chart(row: Locator) -> Locator:
    return row.locator(".vitals-dashboard-chart")


def chart_points(row: Locator) -> int:
    """How many timestamps the row's history chart draws (0 when it shows a message)."""
    if chart(row).count() == 0:
        return 0
    match = POINTS.search(chart(row).get_attribute("aria-label") or "")
    assert match is not None
    return int(match.group(1))


def finding_messages(page: Page, name: str) -> Locator:
    return page.locator(".vitals-dashboard-chat-message.is-assistant", has_text=name)


def finding_message(page: Page, name: str) -> Locator:
    return finding_messages(page, name).last


def finding_messages_with_status(page: Page, name: str, status: str) -> Locator:
    return finding_messages(page, name).filter(has_text=status)


def region(page: Page, name: str) -> Locator:
    label = page.locator(".vitals-dashboard-body-region-name", has_text=name)
    return page.locator(".vitals-dashboard-body-region").filter(has=label)


def region_status(item: Locator) -> Locator:
    return item.locator(".vitals-dashboard-body-region-status")


def environment_select(page: Page) -> Locator:
    return page.locator(".vitals-dashboard-environment-select")


def environment_facts(page: Page) -> Locator:
    return page.locator(".vitals-dashboard-environment-facts")


def root(page: Page) -> Locator:
    return page.locator(".vitals-dashboard")
