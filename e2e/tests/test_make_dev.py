"""Exercise the Make launcher, rather than independently started services."""

import importlib.util
import os
import re
import signal
import socket
import subprocess
import sys
from pathlib import Path

import dashboard as ui
import httpx
import pytest
from conftest import ROOT, wait_for
from playwright.sync_api import Page, expect

spec = importlib.util.spec_from_file_location("dev", ROOT / "scripts/dev.py")
assert spec is not None and spec.loader is not None
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


@pytest.mark.parametrize("target", ["dev", "sim"])
def test_make_accepts_lowercase_speed(target: str) -> None:
    result = subprocess.run(
        ["make", "-n", target, "speed=30"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert '--speed "30"' in result.stdout or "--speed 30" in result.stdout
    assert "--bp-demo-interval 5" in result.stdout
    assert "--lab-demo-interval 5" in result.stdout


def test_make_can_disable_pressure_demo() -> None:
    result = subprocess.run(
        ["make", "-n", "dev", "BP_DEMO_INTERVAL=0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--bp-demo-interval" not in result.stdout
    # One demo override is independent of the others.
    assert "--lab-demo-interval 5" in result.stdout


def test_make_can_disable_the_assay_and_specimen_demo() -> None:
    result = subprocess.run(
        ["make", "-n", "dev", "LAB_DEMO_INTERVAL=0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--lab-demo-interval" not in result.stdout
    assert "--bp-demo-interval 5" in result.stdout


def test_dev_refuses_an_occupied_port_before_starting_services() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen()
        with pytest.raises(RuntimeError, match="already in use"):
            dev.require_free_port(port)


def test_readiness_stops_when_a_server_exits() -> None:
    process = subprocess.Popen([sys.executable, "-c", "raise SystemExit(17)"])
    process.wait()
    with pytest.raises(RuntimeError, match="backend exited unexpectedly"):
        dev.wait_for("http://127.0.0.1:1/", {"backend": process})


def test_make_dev_streams_sparse_vitals_and_cleans_up(page: Page, tmp_path: Path) -> None:
    # The public make command uses fixed ports. Do not disturb a user's servers.
    for port in (8000, 5173):
        try:
            dev.require_free_port(port)
        except RuntimeError:
            pytest.skip(f"Port {port} is occupied by another dev session")

    source = (ROOT / "imitacija/config/healthy.toml").read_text()
    # Make enables the paired demo stream; CGM retains its 300-second schedule.
    config = tmp_path / "healthy.toml"
    config.write_text("duration_s = 2400\n" + source)
    previous_db = tmp_path / "previous.sqlite3"
    previous_db.write_bytes(b"previous demo recordings must remain untouched")
    log = tmp_path / "make-dev.log"
    with log.open("wb") as output:
        process = subprocess.Popen(
            ["make", "dev", f"CONFIG={config}", "speed=30", "OPEN_BROWSER=0"],
            cwd=ROOT,
            env={**os.environ, "DJANGO_DB_PATH": str(previous_db)},
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    try:
        wait_for("http://127.0.0.1:8000/api/health/")
        wait_for("http://127.0.0.1:5173/")
        page.goto("http://127.0.0.1:5173/")
        pressure = ui.vital(page, "Blood pressure")
        glucose = ui.vital(page, "Blood sugar")
        expect(ui.chart(pressure)).to_have_attribute(
            "aria-label",
            re.compile(r"Blood pressure history\. (?:[2-9]|\d{2,}) recorded timestamps\."),
            timeout=20000,
        )
        expect(ui.chart(glucose)).to_have_attribute(
            "aria-label",
            re.compile(r"Blood sugar history\. (?:[2-9]|\d{2,}) recorded timestamps\."),
            timeout=20000,
        )
        expect(ui.chart(pressure).locator(".recharts-area-curve")).to_have_count(2)
        expect(ui.chart(glucose).locator(".recharts-area-curve")).to_have_count(1)

        # Both rendered curves and the actual delivered measurements change.
        for curve in ui.chart(pressure).locator(".recharts-area-curve").all():
            before = curve.get_attribute("d")
            assert before is not None
            expect(curve).not_to_have_attribute("d", before, timeout=15000)
        for channel in ("bp_systolic", "bp_diastolic"):
            response = httpx.get("http://127.0.0.1:8000/api/readings/", params={"channel": channel})
            shown = {round(r["value"] / 133.322, 1) for r in response.json()["readings"][channel]}
            assert len(shown) > 2

        # Calendar-driven assays and specimens, whose next real result is hours,
        # days or a month out, follow the same demo path onto the chart.
        for channel in ("cortisol_saliva", "urine_volume_24h", "sweat_rate"):
            response = httpx.get("http://127.0.0.1:8000/api/readings/", params={"channel": channel})
            readings = response.json()["readings"][channel]
            assert len(readings) > 2, channel
            assert len({r["value"] for r in readings}) > 2, channel
            assert {r["evaluation"] for r in readings} <= {"nominal", "unspecified"}, channel

        page.reload()
        expect(ui.chart(glucose)).to_have_attribute(
            "aria-label",
            re.compile(r"Blood sugar history\. (?:[2-9]|\d{2,}) recorded timestamps\."),
            timeout=20000,
        )
        response = httpx.get("http://127.0.0.1:8000/api/readings/", params={"channel": "glucose"})
        assert len(response.json()["readings"]["glucose"]) >= 2
    finally:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        print(log.read_text())

    assert previous_db.read_bytes() == b"previous demo recordings must remain untouched"
    for port in (8000, 5173):
        dev.require_free_port(port)
