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
    expect(dashboard.locator(".vitals-dashboard-reading-status.is-critical")).to_have_count(0)

    # The detections are their own tab; the store collected them while the
    # vitals tab was the one mounted.
    ui.tab(dashboard, "Health conditions").click()
    # Six original findings plus the combined blood pressure assessment.
    expect(dashboard.locator(".vitals-dashboard-finding")).to_have_count(7, timeout=15000)
    expect(dashboard.locator(".vitals-dashboard-finding-status.is-warning")).to_have_count(0)
    expect(dashboard.locator(".vitals-dashboard-finding-status.is-critical")).to_have_count(0)


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


def test_scenario_one_streams_six_hr_measurements_per_minute_at_speed_one(
    dashboard: Page,
    backend: Backend,
    simulate,
) -> None:
    run = simulate("badscenario1.toml", speed=1, duration=65)
    heart = ui.vital(dashboard, "Heart rate")
    expect(ui.chart(heart)).to_have_attribute(
        "aria-label", "Heart rate history. 1 recorded timestamps.", timeout=15000
    )
    for count in range(2, 8):
        expect(ui.chart(heart)).to_have_attribute(
            "aria-label", f"Heart rate history. {count} recorded timestamps.", timeout=20000
        )
    run.wait()
    assert_delivered_cleanly(run.counters(), backend)


def test_reload_mid_run_resumes_live_updates(dashboard: Page, backend: Backend, simulate) -> None:
    simulate("healthy.toml", speed=60, duration=1200)
    wait_for_more_points(dashboard, "Heart rate", than=1)

    dashboard.reload()
    ui.enter(dashboard)

    for label in VITALS:
        expect(ui.status(ui.vital(dashboard, label))).to_have_text(MEASURED, timeout=5000)
    after_reload = ui.chart_points(ui.vital(dashboard, "Heart rate"))
    wait_for_more_points(dashboard, "Heart rate", than=after_reload)


def test_hypercapnia_scenario_escalates_on_screen(
    dashboard: Page, backend: Backend, simulate
) -> None:
    run = simulate("badscenario2.toml", speed=30, duration=420)

    # Watch the detection escalate on its own tab, then come back for the
    # vitals and the body scan it is built from.
    ui.tab(dashboard, "Health conditions").click()
    hypoxia = ui.finding(dashboard, "Hypoxia & CO2 exposure")
    expect(ui.finding_status(hypoxia)).to_have_text("Nominal", timeout=15000)
    expect(ui.finding_status(hypoxia)).to_have_text("Warning", timeout=30000)
    expect(hypoxia.locator(".vitals-dashboard-finding-triggers")).to_contain_text(
        "ppCO2 > 3.0 mmHg"
    )

    ui.tab(dashboard, "Vitals").click()
    oxygen = ui.vital(dashboard, "Blood oxygen")
    expect(ui.status(oxygen)).to_have_text("Warning", timeout=30000)
    expect(ui.status(ui.vital(dashboard, "Heart rate"))).to_have_text("Warning", timeout=30000)
    expect(ui.region_status(ui.region(dashboard, "Head & neck"))).to_have_text(
        "Critical", timeout=30000
    )

    run.wait()
    assert_delivered_cleanly(run.counters(), backend)


def test_sans_scenario_reaches_critical(dashboard: Page, backend: Backend, simulate) -> None:
    # The scenario itself progresses early; telemetry runs at real-time speed.
    run = simulate("badscenario1.toml", speed=1, duration=135)

    ui.tab(dashboard, "Health conditions").click()
    sans = ui.finding(dashboard, "SANS & cephalic fluid shift")
    expect(ui.finding_status(sans)).to_have_text("Nominal", timeout=15000)
    expect(ui.finding_status(sans)).to_have_text("Warning", timeout=75000)
    expect(ui.finding_status(sans)).to_have_text("Critical", timeout=75000)
    expect(sans.locator(".vitals-dashboard-finding-triggers")).to_have_text(
        "jugular distension > 1.8%"
    )

    ui.tab(dashboard, "Vitals").click()
    expect(ui.region_status(ui.region(dashboard, "Head & neck"))).to_have_text("Critical")

    run.wait()
    assert_delivered_cleanly(run.counters(), backend)
