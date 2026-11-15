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


def chat_starter(page: Page) -> Locator:
    """The assistant's suggested question, shown until the chat has messages."""
    return page.get_by_role("button", name="Summarize findings and advise")


def chat_input(page: Page) -> Locator:
    return page.get_by_label("Ask about the findings…")


def chat_send(page: Page) -> Locator:
    return page.get_by_role("button", name="Send")


def chat_messages(page: Page, role: str = "") -> Locator:
    """The transcript, or just its user/assistant/error/pending messages."""
    return page.locator(f".vitals-dashboard-chat-message{f'.is-{role}' if role else ''}")


def finding(page: Page, name: str) -> Locator:
    heading = page.locator(".vitals-dashboard-finding-name", has_text=name)
    return page.locator(".vitals-dashboard-finding").filter(has=heading)


def finding_status(item: Locator) -> Locator:
    return item.locator(".vitals-dashboard-finding-status")


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


def tab(page: Page, label: str) -> Locator:
    """One of the header tabs, e.g. "All measurements"."""
    return page.get_by_role("tab", name=label)


def measurement(page: Page, name: str) -> Locator:
    """One row of the all-measurements tab, by the channel's display name."""
    heading = page.locator(
        ".vitals-dashboard-measurement-name", has_text=re.compile(f"^{re.escape(name)}$")
    )
    return page.locator(".vitals-dashboard-measurement").filter(has=heading)


def measurement_value(row: Locator) -> Locator:
    return row.locator(".vitals-dashboard-measurement-value")


def measurement_status(row: Locator) -> Locator:
    return row.locator(".vitals-dashboard-reading-status")


def measurement_range(page: Page, label: str) -> Locator:
    """One timeframe button of the all-measurements tab, e.g. "5 min"."""
    return page.get_by_role("group", name="Chart timeframe").get_by_role(
        "button", name=label, exact=True
    )
