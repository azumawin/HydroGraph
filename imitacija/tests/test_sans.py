"""Scenario ownership, physical coupling, windows and configuration regressions."""

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.main import load_settings
from imitacija.models import AstronautProfile, Environment, SansScenario, Settings
from imitacija.physiology import crew_values, rmssd
from imitacija.registry import dictionary, effective_channels
from imitacija.scenarios import SANS_CHANNELS, sans_state, sans_values
from imitacija.scheduler import Scheduler
from imitacija.units import MMHG_TO_PA


class Sink:
    def __init__(self):
        self.items = []

    def submit(self, item):
        self.items.append(item)


def acquire(settings, end):
    sink = Sink()
    scheduler = Scheduler(settings, ManualClock(), sink)
    asyncio.run(scheduler.run(end))
    asyncio.run(scheduler.run(end))
    return sink.items


def test_demo_windows_units_screens_and_thresholds():
    config = load_settings(Path("config/badscenario1.toml"), None, None)
    items = acquire(config, 4200)
    startup = [o for o in items if o.sample_kind == "startup_baseline"]
    # Every enabled channel (all of them, SANS included) reports at boot.
    assert len(startup) == len(effective_channels(config))
    assert {o.reading.channel for o in startup} == effective_channels(config)
    assert SANS_CHANNELS <= effective_channels(config)
    assert all(o.window_s == 0 and o.acquired_s == 0 for o in startup)
    strain = [
        o
        for o in items
        if o.reading.channel == "jugular_strain_pct" and o.sample_kind == "scheduled"
    ]
    assert strain[0].acquired_s == 60
    assert next(o.acquired_s for o in strain if o.reading.value * 100 >= 1.1) == 1260
    assert next(o.acquired_s for o in strain if o.reading.value * 100 > 1.8) == 3060
    for o in strain:
        ratio = next(
            r
            for r in items
            if r.acquired_s == o.acquired_s and r.reading.channel == "delta_R_over_R0"
        )
        assert ratio.reading.value == pytest.approx(15.5 * o.reading.value)
        assert o.window_s == 60
    for t, expected in [(600, 0.0065), (2400, 0.0155), (4200, 0.0205)]:
        assert next(o.reading.value for o in strain if o.acquired_s == t) == pytest.approx(expected)
    indicator = next(
        o for o in items if o.acquired_s == 2400 and o.reading.channel == "icp_risk_indicator_mmHg"
    )
    assert indicator.reading.value == pytest.approx(16.2 * MMHG_TO_PA)
    assert indicator.reading.unit == "Pa"
    for channel, value in [("visual_acuity_logmar", 0.2), ("amsler_grid_distortion", True)]:
        results = [
            o for o in items if o.reading.channel == channel and o.sample_kind == "scheduled"
        ]
        assert [o.acquired_s for o in results] == [1860, 3660]
        assert all(o.reading.value == value and o.window_s == 0 for o in results)
    assert [o.model_dump() for o in items] == [o.model_dump() for o in acquire(config, 4200)]


def test_hrv_signal_and_owner_isolation():
    a = AstronautProfile(id="a", rmssd_ms=48)
    b = AstronautProfile(id="b", rmssd_ms=48)
    scenario = SansScenario(owner_id="a", eye_screen_times_s=())
    assert rmssd(500, a, 42, scenario=scenario) == rmssd(500, a, 42)
    assert rmssd(2400, a, 42, scenario=scenario) == pytest.approx(36, abs=3)
    assert rmssd(2400, a, 42) == pytest.approx(48, abs=3)
    assert rmssd(2400, b, 42, scenario=scenario) == rmssd(2400, b, 42)
    for group in ["heart", "bp", "spo2", "temperature"]:
        assert crew_values(group, 2400, a, 42, scenario) == crew_values(group, 2400, a, 42)
    config = Settings(
        crew=(a, b),
        sans_scenario=scenario,
        enabled_channels=tuple(SANS_CHANNELS | {"hrv_rmssd"}),
        environment=Environment(comm_delay_s=5),
    )
    items = acquire(config, 120)
    assert all(o.owner == "a" for o in items if o.reading.channel in SANS_CHANNELS)
    assert all(o.available_s == o.acquired_s + 5 for o in items)
    assert not [
        o
        for o in items
        if o.sample_kind == "scheduled"
        and o.reading.channel in {"visual_acuity_logmar", "amsler_grid_distortion"}
    ]
    assert not acquire(config.model_copy(update={"enabled_channels": ()}), 120)


def test_warning_only_windows_and_metadata():
    scenario = SansScenario(escalate_to_critical=False)
    assert sans_state(10000, scenario)["jugular_strain_pct"] == pytest.approx(1.55)
    average = sans_values("cephalic", 630, scenario)["jugular_strain_pct"]
    assert 0.65 < average < sans_state(630, scenario)["jugular_strain_pct"]
    with pytest.raises(ValueError):
        sans_values("cephalic", 30, scenario)
    healthy = Settings()
    assert not effective_channels(healthy) & SANS_CHANNELS
    info = dictionary(healthy.environment, 0, healthy)
    assert all(not c.enabled for c in info.channels if c.channel in SANS_CHANNELS)
    configured = Settings(sans_scenario=scenario)
    assert dictionary(configured.environment, 0, configured).sans_scenario["warning_at_s"] == 1800
    with pytest.raises(ValueError):
        effective_channels(Settings(enabled_channels=("jugular_strain_pct",)))


@pytest.mark.parametrize(
    "change",
    [
        {"warning_at_s": 600},
        {"critical_start_s": 1700},
        {"eye_screen_times_s": (2, 1)},
        {"eye_screen_times_s": (1, 1)},
        {"eye_screen_times_s": (float("nan"),)},
        {"gauge_factor": 0},
        {"warning_strain_pct": 2},
        {"onset_s": float("inf")},
    ],
)
def test_invalid_scenario(change):
    with pytest.raises(ValidationError):
        SansScenario(**change)


def test_invalid_owner_gravity_and_hrv():
    for scenario, env in [
        (SansScenario(owner_id="missing"), Environment()),
        (SansScenario(), Environment(gravity_g=1)),
        (SansScenario(affected_rmssd_ms=50), Environment()),
    ]:
        with pytest.raises(ValidationError):
            Settings(sans_scenario=scenario, environment=env)


def test_sans_mock_http_contract():
    import json

    import httpx

    from imitacija.delivery import Delivery, HttpTransport

    settings = Settings(sans_scenario=SansScenario(), enabled_channels=("jugular_strain_pct",))
    items = acquire(settings, 2400)
    selected = [o for o in items if o.acquired_s in (0, 2400)]

    async def run():
        requests = []

        async def receive(request):
            requests.append(request)
            return httpx.Response(204)

        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(receive)
        ) as client:
            clock = ManualClock()
            await clock.sleep_until(2400)
            delivery = Delivery(settings, clock, HttpTransport(client))
            for item in selected:
                delivery.submit(item)
            task = asyncio.create_task(delivery.run())
            await delivery.finish(task)
        assert len(requests) == 2
        for request, item in zip(requests, selected, strict=True):
            payload = json.loads(request.content)
            assert set(payload) == {"channel", "value", "unit", "measured_at"}
            assert payload == item.reading.model_dump(mode="json")
            assert request.headers["X-Sample-Kind"] == item.sample_kind
            assert request.headers["X-Owner-ID"] == "crew-1"
        assert json.loads(requests[-1].content)["value"] == pytest.approx(0.0155)

    asyncio.run(run())
