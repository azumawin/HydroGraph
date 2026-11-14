"""Readings posted to the backend show up on the dashboard, exactly and live.

Each test posts readings in SI wire units, as the simulator does, and checks
what a crew member sees: converted values, evaluations, history charts, the
body scan and the findings.
"""

import re

import dashboard as ui
import httpx
from conftest import Backend
from playwright.sync_api import Page, expect

MMHG = 133.322  # Pa
VITALS = ["Heart rate", "Blood pressure", "Blood sugar", "Body temperature", "Blood oxygen"]


def test_empty_dashboard_before_any_reading(dashboard: Page) -> None:
    for label in VITALS:
        row = ui.vital(dashboard, label)
        expect(ui.status(row)).to_have_text("Not measured")
        expect(ui.value(row)).to_have_text(re.compile("^—(/—)?$"))
        expect(row.locator(".vitals-dashboard-chart-message")).to_have_text("No readings yet.")
    expect(dashboard.locator(".vitals-dashboard-findings-empty")).to_have_text("No findings yet.")
    expect(ui.region_status(ui.region(dashboard, "Upper body"))).to_have_text("No reading")


def test_readings_appear_in_display_units(dashboard: Page, backend: Backend) -> None:
    backend.post("heart_rate", 72 / 60, "s^-1")
    backend.post("bp_systolic", 120 * MMHG, "Pa")
    backend.post("bp_diastolic", 80 * MMHG, "Pa")
    backend.post("glucose", 5.4, "mol/m^3")
    backend.post("body_temperature", 273.15 + 36.8, "K")
    backend.post("spo2", 0.97, "1")

    expected = {
        "Heart rate": ("72", "bpm"),
        "Blood pressure": ("120/80", "mmHg"),
        "Blood sugar": ("5.4", "mmol/L"),
        "Body temperature": ("36.8", "°C"),
        "Blood oxygen": ("97", "%"),
    }
    for label, (shown, shown_unit) in expected.items():
        row = ui.vital(dashboard, label)
        expect(ui.value(row)).to_have_text(shown)
        expect(ui.unit(row)).to_have_text(shown_unit)


def test_evaluations_match_the_backend(dashboard: Page, backend: Backend) -> None:
    backend.post("heart_rate", 96 / 60, "s^-1")
    backend.post("spo2", 0.89, "1")
    backend.post("glucose", 5.0, "mol/m^3")
    backend.post("bp_systolic", 120 * MMHG, "Pa")
    backend.post("bp_diastolic", 80 * MMHG, "Pa")

    cases = {
        "Heart rate": ("Warning", "is-warning"),
        "Blood oxygen": ("Critical", "is-critical"),
        "Blood sugar": ("Nominal", "is-nominal"),
        "Blood pressure": ("No threshold", "is-unspecified"),
    }
    for label, (text, css) in cases.items():
        row_status = ui.status(ui.vital(dashboard, label))
        expect(row_status).to_have_text(text)
        expect(row_status).to_have_class(re.compile(css))


def test_each_reading_adds_a_chart_point(dashboard: Page, backend: Backend) -> None:
    row = ui.vital(dashboard, "Heart rate")
    for minute, bpm in enumerate([60, 64, 68, 72, 76]):
        backend.post("heart_rate", bpm / 60, "s^-1", minutes=minute)
        expect(ui.chart(row)).to_have_attribute(
            "aria-label", f"Heart rate history. {minute + 1} recorded timestamps."
        )
    expect(ui.value(row)).to_have_text("76")


def test_blood_pressure_chart_draws_both_series(dashboard: Page, backend: Backend) -> None:
    row = ui.vital(dashboard, "Blood pressure")
    for minute in range(3):
        backend.post("bp_systolic", (118 + minute) * MMHG, "Pa", minutes=minute)
        backend.post("bp_diastolic", (78 + minute) * MMHG, "Pa", minutes=minute)
    expect(ui.chart(row)).to_have_attribute(
        "aria-label", "Blood pressure history. 3 recorded timestamps."
    )
    expect(ui.chart(row).locator(".recharts-area")).to_have_count(2)
    expect(ui.value(row)).to_have_text("120/80")


def test_late_reading_joins_history_but_keeps_the_newest_value(
    dashboard: Page, backend: Backend
) -> None:
    row = ui.vital(dashboard, "Heart rate")
    backend.post("heart_rate", 60 / 60, "s^-1", minutes=10)
    expect(ui.value(row)).to_have_text("60")

    backend.post("heart_rate", 90 / 60, "s^-1", minutes=5)  # measured earlier, arrives later

    expect(ui.chart(row)).to_have_attribute(
        "aria-label", "Heart rate history. 2 recorded timestamps."
    )
    expect(ui.value(row)).to_have_text("60")


def test_body_scan_regions_show_the_worst_evaluation(dashboard: Page, backend: Backend) -> None:
    backend.post("heart_rate", 72 / 60, "s^-1")
    backend.post("spo2", 0.89, "1")
    backend.post("body_temperature", 273.15 + 36.8, "K")

    upper = ui.region_status(ui.region(dashboard, "Upper body"))
    expect(upper).to_have_text("Critical")
    expect(upper).to_have_class(re.compile("is-critical"))
    expect(ui.region_status(ui.region(dashboard, "Head & neck"))).to_have_text("Nominal")
    expect(ui.region_status(ui.region(dashboard, "Arms"))).to_have_text("No reading")


def test_present_or_absent_finding_shows_triggers_and_action(
    dashboard: Page, backend: Backend
) -> None:
    backend.post("bone_ntx_pct_baseline", 0.30, "1")
    backend.post("urine_volume_24h", 1.5e-3, "m^3")

    bone = ui.finding(dashboard, "Bone demineralization & renal stone risk")
    expect(ui.finding_status(bone)).to_have_text("Present")
    expect(bone.locator(".vitals-dashboard-finding-triggers")).to_have_text(
        "NTx > +25% from baseline · urine volume < 2.0 L/day"
    )
    expect(bone.locator(".vitals-dashboard-finding-action")).to_contain_text(
        "Increase ARED resistive exercise load"
    )


def test_severity_finding_escalates_and_recovers(dashboard: Page, backend: Backend) -> None:
    backend.post("ambient_integrated_dose", 0.001, "Sv", scope="environment")
    backend.post("ambient_dose_rate", 5e-9, "Sv/s", scope="environment")
    backend.post("spe_flag", True, "boolean", minutes=1, scope="environment")

    radiation = ui.finding(dashboard, "Radiation dose & solar particle events")
    expect(ui.finding_status(radiation)).to_have_text("Critical")
    expect(radiation.locator(".vitals-dashboard-finding-action")).to_contain_text("storm shelter")

    backend.post("spe_flag", False, "boolean", minutes=2, scope="environment")

    expect(ui.finding_status(radiation)).to_have_text("Nominal")
    expect(radiation.locator(".vitals-dashboard-finding-action")).to_have_count(0)


def test_finding_combines_crew_and_cabin_readings(dashboard: Page, backend: Backend) -> None:
    backend.post("spo2", 0.97, "1")
    backend.post("ambient_ppco2", 3.5 * MMHG, "Pa", scope="environment")

    hypoxia = ui.finding(dashboard, "Hypoxia & CO2 exposure")
    expect(ui.finding_status(hypoxia)).to_have_text("Warning")
    expect(hypoxia.locator(".vitals-dashboard-finding-triggers")).to_have_text("ppCO2 > 3.0 mmHg")


def test_rejected_reading_changes_nothing(dashboard: Page, backend: Backend) -> None:
    response = httpx.post(
        f"{backend.url}/api/readings/",
        json={
            "channel": "heart_rate",
            "value": 72,
            "unit": "bpm",
            "measured_at": "2026-11-14T08:00:00Z",
        },
        headers={"X-Simulation-Scope": "crew"},
    )
    assert response.status_code == 400

    backend.post("spo2", 0.97, "1")  # a valid reading after it, to know the stream is live
    expect(ui.value(ui.vital(dashboard, "Blood oxygen"))).to_have_text("97")
    expect(ui.status(ui.vital(dashboard, "Heart rate"))).to_have_text("Not measured")


def test_reload_restores_the_latest_state(dashboard: Page, backend: Backend) -> None:
    backend.post("heart_rate", 66 / 60, "s^-1", minutes=0)
    backend.post("heart_rate", 70 / 60, "s^-1", minutes=1)
    backend.post("spo2", 0.95, "1")
    expect(ui.value(ui.vital(dashboard, "Heart rate"))).to_have_text("70")

    dashboard.reload()

    heart_rate = ui.vital(dashboard, "Heart rate")
    expect(ui.value(heart_rate)).to_have_text("70")
    expect(ui.status(heart_rate)).to_have_text("Nominal")
    expect(ui.value(ui.vital(dashboard, "Blood oxygen"))).to_have_text("95")
    # The stream's snapshot carries the latest reading per channel, not history.
    expect(ui.chart(heart_rate)).to_have_attribute(
        "aria-label", "Heart rate history. 1 recorded timestamps."
    )


def test_dashboard_reconnects_after_the_backend_restarts(dashboard: Page, backend: Backend) -> None:
    backend.post("heart_rate", 72 / 60, "s^-1")
    expect(ui.value(ui.vital(dashboard, "Heart rate"))).to_have_text("72")

    backend.stop()
    expect(dashboard.locator(".vitals-dashboard-error-toast")).to_contain_text(
        "Could not load live telemetry"
    )
    expect(ui.value(ui.vital(dashboard, "Heart rate"))).to_have_text("72")  # last data stays

    backend.start()
    backend.post("heart_rate", 90 / 60, "s^-1", minutes=1)

    expect(ui.value(ui.vital(dashboard, "Heart rate"))).to_have_text("90", timeout=15000)
