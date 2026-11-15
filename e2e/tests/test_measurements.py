"""The all-measurements tab lists every channel the backend describes, in full.

Not run in the session that wrote it (no browser was available); the dictionary
it relies on is pinned by backend/api/test_contracts.py.
"""

import dashboard as ui
from conftest import Backend
from playwright.sync_api import Page, expect

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
