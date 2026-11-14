"""The mission environment: chosen on the dashboard, applied everywhere.

The dropdown switches the backend's environment; every open dashboard and the
running simulator follow it, the background palette changes, and radiation is
graded against the selected environment's own background.
"""

import json
import re
import time

import dashboard as ui
import httpx
from conftest import Backend
from playwright.sync_api import Page, expect

ENVIRONMENT_NAMES = ["ISS, low Earth orbit", "Lunar surface", "Mars transit", "Mars surface"]
RADIATION_FINDING = "radiation_exposure_3_2"
USV_H = 1e-6 / 3600  # Sv/s


def current_environment(backend: Backend) -> str:
    return httpx.get(f"{backend.url}/api/environment/").json()["id"]


def finding_status(backend: Backend, finding_id: str) -> str:
    findings = httpx.get(f"{backend.url}/api/health-conditions/").json()["findings"]
    return next(item["status"] for item in findings if item["id"] == finding_id)


def latest_dose_rate_usv_h(backend: Backend) -> float | None:
    """The cabin dose rate in the stream's snapshot, or None before one arrives."""
    event = ""
    with httpx.stream("GET", f"{backend.url}/api/stream/", timeout=5) as stream:
        for line in stream.iter_lines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
                if event == "finding":
                    return None  # readings in the snapshot are over
            elif event == "reading" and line.startswith("data: "):
                reading = json.loads(line.removeprefix("data: "))
                if reading["channel"] == "ambient_dose_rate":
                    return reading["value"] / USV_H
    return None


def wait_for_dose_rate(backend: Backend, usv_h: float, timeout_s: float = 20) -> float:
    """Wait until the cabin dose rate oscillates around ``usv_h`` (it varies +-12%)."""
    deadline = time.monotonic() + timeout_s
    seen = None
    while time.monotonic() < deadline:
        seen = latest_dose_rate_usv_h(backend)
        if seen is not None and abs(seen - usv_h) <= 0.13 * usv_h:
            return seen
        time.sleep(0.5)
    raise AssertionError(f"dose rate stayed at {seen} uSv/h, expected about {usv_h}")


def test_dropdown_offers_the_four_environments_and_defaults_to_iss(dashboard: Page) -> None:
    select = ui.environment_select(dashboard)
    expect(select).to_have_value("iss_leo")
    expect(select.locator("option")).to_have_text(ENVIRONMENT_NAMES)
    facts = ui.environment_facts(dashboard)
    expect(facts).to_contain_text("0 g")
    expect(facts).to_contain_text("1.2 s")
    expect(facts).to_contain_text("14.6 µSv/h")
    expect(ui.root(dashboard)).to_have_class(re.compile(r"\bis-environment-iss_leo\b"))


def test_each_environment_shows_its_facts_and_background(dashboard: Page) -> None:
    cases = {
        "lunar_surface": ["0.17 g", "2.6 s", "29.53 days", "57.1 µSv/h"],
        "mars_transit": ["0 g", "26 min", "24 h", "76.7 µSv/h"],
        "mars_surface": ["0.38 g", "26 min", "24.66 h", "26.7 µSv/h"],
    }
    for environment, facts in cases.items():
        ui.environment_select(dashboard).select_option(environment)
        expect(ui.root(dashboard)).to_have_class(re.compile(rf"\bis-environment-{environment}\b"))
        for fact in facts:
            expect(ui.environment_facts(dashboard)).to_contain_text(fact)


def test_switch_reaches_every_dashboard_and_survives_restart(
    dashboard: Page, frontend: str, backend: Backend
) -> None:
    other = dashboard.context.new_page()
    other.goto(frontend)
    expect(ui.environment_select(other)).to_have_value("iss_leo")

    ui.environment_select(dashboard).select_option("mars_surface")

    expect(ui.environment_select(other)).to_have_value("mars_surface")
    expect(ui.root(other)).to_have_class(re.compile(r"\bis-environment-mars_surface\b"))
    assert current_environment(backend) == "mars_surface"

    backend.stop()
    backend.start()
    dashboard.reload()
    expect(ui.environment_select(dashboard)).to_have_value("mars_surface")


def test_unknown_environment_is_rejected(dashboard: Page, backend: Backend) -> None:
    response = httpx.put(f"{backend.url}/api/environment/", json={"id": "venus"})

    assert response.status_code == 400
    assert current_environment(backend) == "iss_leo"
    expect(ui.environment_select(dashboard)).to_have_value("iss_leo")


def test_radiation_is_graded_against_the_selected_environment(
    dashboard: Page, backend: Backend
) -> None:
    backend.post("ambient_integrated_dose", 0.001, "Sv", scope="environment")
    backend.post("ambient_dose_rate", 70 * USV_H, "Sv/s", scope="environment")
    backend.post("spe_flag", False, "boolean", scope="environment")
    radiation = ui.finding_message(dashboard, "Radiation dose & solar particle events")

    # 70 uSv/h is 55.4 above the ISS background but only 12.9 above the Moon's
    expect(radiation).to_contain_text("Warning:")
    expect(radiation).to_contain_text("dose rate > 50 µSv/h above baseline")
    assert finding_status(backend, RADIATION_FINDING) == "warning"

    ui.environment_select(dashboard).select_option("lunar_surface")
    assert finding_status(backend, RADIATION_FINDING) == "nominal"

    ui.environment_select(dashboard).select_option("iss_leo")
    assert finding_status(backend, RADIATION_FINDING) == "warning"


def test_running_simulator_follows_the_dashboard(
    dashboard: Page, backend: Backend, simulate
) -> None:
    run = simulate("healthy.toml", speed=30, duration=900)
    wait_for_dose_rate(backend, 14.6)  # ISS, the default, replaces the config's 18

    # the lunar surface: its 1.3 s one way delay keeps the test fast, where Mars
    # transit's 13 min would hold every new reading back for 26 s at this speed
    ui.environment_select(dashboard).select_option("lunar_surface")

    wait_for_dose_rate(backend, 57.1)
    assert finding_status(backend, RADIATION_FINDING) == "nominal"  # background, not a spike

    run.wait()
    assert "environment: lunar_surface" in run.output.read_text()
    assert backend.server_errors() == []
