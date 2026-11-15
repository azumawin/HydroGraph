"""Read the dashboard the way a person does: by labels, not internals."""

import re

from playwright.sync_api import Locator, Page

POINTS = re.compile(r"(\d+) recorded timestamps")


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
