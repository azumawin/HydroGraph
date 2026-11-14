"""The real simulator drives the dashboard: it fills, updates live and escalates.

Each test runs one of the simulator's configs against a fresh backend at an
accelerated speed the backend keeps up with, and watches the dashboard.
"""

import json
import re

import dashboard as ui
from conftest import Backend
from playwright.sync_api import Page, expect

VITALS = ["Heart rate", "Blood pressure", "Blood sugar", "Body temperature", "Blood oxygen"]
MEASURED = re.compile("Nominal|Warning|Critical|No threshold")


def wait_for_more_points(page: Page, label: str, than: int, timeout_ms: int = 20000) -> int:
    row = ui.vital(page, label)
    waited = 0
    while waited < timeout_ms:
        points = ui.chart_points(row)
        if points > than:
            return points
        page.wait_for_timeout(250)
        waited += 250
    raise AssertionError(f"{label} chart stayed at {than} points for {timeout_ms} ms")


def assert_delivered_cleanly(counters_line: str, backend: Backend) -> None:
    counters = json.loads(counters_line)
    assert counters["failed"] == 0, counters
    assert counters["delivered"] > 0, counters
    assert backend.server_errors() == []


def test_healthy_run_fills_every_vital_and_flags_nothing(
    dashboard: Page, backend: Backend, simulate
) -> None:
    run = simulate("healthy.toml", speed=60, duration=900)

    for label in VITALS:
        expect(ui.status(ui.vital(dashboard, label))).to_have_text(MEASURED, timeout=15000)

    run.wait()
    assert_delivered_cleanly(run.counters(), backend)
    for label in ["Heart rate", "Blood oxygen", "Body temperature"]:
        assert ui.chart_points(ui.vital(dashboard, label)) >= 3, label
    expect(dashboard.locator(".vitals-dashboard-chat-message")).to_have_count(0)
    expect(dashboard.locator(".vitals-dashboard-reading-status.is-critical")).to_have_count(0)


def test_charts_and_values_update_live_during_a_run(
    dashboard: Page, backend: Backend, simulate
) -> None:
    simulate("healthy.toml", speed=60, duration=1200)

    first = wait_for_more_points(dashboard, "Heart rate", than=0)
    later = wait_for_more_points(dashboard, "Heart rate", than=first)
    assert later > first

    oxygen = ui.vital(dashboard, "Blood oxygen")
    expect(ui.value(oxygen)).to_have_text(re.compile(r"^9\d(\.\d)?$"))
    expect(ui.unit(oxygen)).to_have_text("%")
    heart_rate = ui.vital(dashboard, "Heart rate")
    expect(ui.value(heart_rate)).to_have_text(re.compile(r"^\d{2,3}(\.\d)?$"))
    expect(ui.unit(heart_rate)).to_have_text("bpm")


def test_reload_mid_run_resumes_live_updates(dashboard: Page, backend: Backend, simulate) -> None:
    simulate("healthy.toml", speed=60, duration=1200)
    wait_for_more_points(dashboard, "Heart rate", than=1)

    dashboard.reload()

    for label in VITALS:
        expect(ui.status(ui.vital(dashboard, label))).to_have_text(MEASURED, timeout=5000)
    after_reload = ui.chart_points(ui.vital(dashboard, "Heart rate"))
    wait_for_more_points(dashboard, "Heart rate", than=after_reload)


def test_hypercapnia_scenario_escalates_on_screen(
    dashboard: Page, backend: Backend, simulate
) -> None:
    run = simulate("badscenario2.toml", speed=30, duration=420)

    hypoxia = ui.finding_message(dashboard, "Hypoxia & CO2 exposure")
    expect(hypoxia).to_contain_text("Warning", timeout=30000)
    expect(hypoxia).to_contain_text("ppCO2 > 3.0 mmHg")

    oxygen = ui.vital(dashboard, "Blood oxygen")
    expect(ui.status(oxygen)).to_have_text("Warning", timeout=30000)
    expect(ui.status(ui.vital(dashboard, "Heart rate"))).to_have_text("Warning", timeout=30000)
    expect(ui.region_status(ui.region(dashboard, "Head & neck"))).to_have_text(
        "Critical", timeout=30000
    )

    run.wait()
    assert_delivered_cleanly(run.counters(), backend)


def test_sans_scenario_reaches_critical(dashboard: Page, backend: Backend, simulate) -> None:
    run = simulate("badscenario1.toml", speed=120, duration=4200)

    sans_warning = ui.finding_messages_with_status(
        dashboard, "SANS & cephalic fluid shift", "Warning"
    )
    expect(sans_warning.first).to_be_visible(timeout=40000)
    sans_critical = ui.finding_messages_with_status(
        dashboard, "SANS & cephalic fluid shift", "Critical"
    )
    expect(sans_critical.first).to_be_visible(timeout=40000)
    expect(sans_critical.first).to_contain_text("jugular distension > 1.8%")
    expect(ui.region_status(ui.region(dashboard, "Head & neck"))).to_have_text("Critical")

    run.wait()
    assert backend.server_errors() == []
