"""The all-measurements tab lists every channel the backend describes, in full.

Not run in the session that wrote it (no browser was available); the dictionary
it relies on is pinned by backend/api/test_contracts.py.
"""

import re

import dashboard as ui
from conftest import Backend
from playwright.sync_api import Locator, Page, expect

# hydrograph_core.CHANNELS; test_contracts.py pins the dictionary to exactly these.
CHANNELS = 40


def test_tab_lists_every_channel_with_its_detail(dashboard: Page, backend: Backend) -> None:
    ui.tab(dashboard, "All measurements").click()

    expect(dashboard.locator(".vitals-dashboard-measurement")).to_have_count(CHANNELS)
    # The vitals rows are not mounted behind the list, so nothing is counted twice.
    expect(dashboard.locator(".vitals-dashboard-reading")).to_have_count(0)

    strain = ui.measurement(dashboard, "Jugular strain")
    expect(ui.measurement_status(strain)).to_have_text("Not measured")
    expect(ui.measurement_value(strain)).to_have_text("—")

    backend.post("jugular_strain_pct", 0.0152, "1")
    expect(ui.measurement_status(strain)).to_have_text("Warning")
    expect(ui.measurement_value(strain)).to_have_text("1.5")
    assert ui.chart_points(strain) >= 1

    # A flag renders as text, graded, with no chart.
    backend.post("viral_ebv_detected", True, "boolean")
    reactivation = ui.measurement(dashboard, "EBV reactivation")
    expect(ui.measurement_value(reactivation)).to_have_text("true")
    expect(ui.measurement_status(reactivation)).to_have_text("Warning")
    expect(reactivation.locator(".vitals-dashboard-chart")).to_have_count(0)

    ui.tab(dashboard, "Vitals").click()
    expect(ui.vital(dashboard, "Heart rate")).to_be_visible()
    expect(dashboard.locator(".vitals-dashboard-measurement")).to_have_count(0)


def expect_chart_points(row: Locator, count: int) -> None:
    """Wait for the row's chart to be drawn from exactly `count` timestamps."""
    expect(ui.chart(row)).to_have_attribute(
        "aria-label", re.compile(rf"(?<!\d){count} recorded timestamps\.")
    )


def test_a_timeframe_narrows_every_chart_to_its_own_window(
    dashboard: Page, backend: Backend
) -> None:
    """The charts hold minutes of history -- 120 points at each channel's own
    cadence -- so the timeframes offered are minute-scale, and each one is
    measured back from the channel's newest reading.
    """
    for minutes, strain in ((0, 0.0100), (10, 0.0120), (20, 0.0152)):
        backend.post("jugular_strain_pct", strain, "1", minutes=minutes)
    ui.tab(dashboard, "All measurements").click()
    row = ui.measurement(dashboard, "Jugular strain")
    expect(ui.measurement_value(row)).to_have_text("1.5")
    expect_chart_points(row, 3)

    # Readings 10 minutes apart: only the newest is inside a five-minute window.
    ui.measurement_range(dashboard, "5 min").click()
    expect_chart_points(row, 1)
    ui.measurement_range(dashboard, "30 min").click()
    expect_chart_points(row, 3)
    ui.measurement_range(dashboard, "1 min").click()
    expect_chart_points(row, 1)
    ui.measurement_range(dashboard, "All").click()
    expect_chart_points(row, 3)
