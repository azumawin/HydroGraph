"""Shared-cabin fault trajectories, windows, transport and regression coverage."""

import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.delivery import Delivery, HttpTransport
from imitacija.main import load_settings
from imitacija.models import (
    AstronautProfile,
    Environment,
    HypercapniaScenario,
    SansScenario,
    Settings,
)
from imitacija.physiology import crew_values, rmssd
from imitacija.registry import dictionary, effective_channels
from imitacija.scenarios import (
    hypercapnia_cabin_mmhg,
    hypercapnia_eeg_values,
    hypercapnia_references,
)
from imitacija.scheduler import Scheduler
from imitacija.units import MMHG_TO_PA


class Sink:
    def __init__(self):
        self.items = []

    def submit(self, item):
        self.items.append(item)


def acquire(settings, end=600):
    sink = Sink()
    scheduler = Scheduler(settings, ManualClock(), sink)
    asyncio.run(scheduler.run(end))
    scheduler.initialize()
    return sink.items


def demo():
    return load_settings(Path("config/badscenario2.toml"), None, None)


def test_demo_windows_units_and_determinism():
    settings = demo()
    items = acquire(settings)
    assert items == acquire(settings)
    startup = [o for o in items if o.sample_kind == "startup_baseline"]
    assert len(startup) == 30
    assert {o.reading.channel for o in startup} == effective_channels(settings)
    assert len({(o.owner, o.reading.channel) for o in startup}) == len(startup)
    assert sum(o.scope == "crew" for o in startup) == 25
    assert sum(o.scope == "environment" for o in startup) == 5
    assert all(o.acquired_s == o.window_s == 0 for o in startup)
    baseline = {o.reading.channel: o.reading.value for o in startup}
    assert {
        key: baseline[key]
        for key in ("ambient_ppco2", "heart_rate", "respiratory_rate", "spo2", "eeg_cfe_ratio")
    } == pytest.approx(
        dict(
            ambient_ppco2=2.2 * MMHG_TO_PA,
            heart_rate=1.2,
            respiratory_rate=14 / 60,
            spo2=0.97,
            eeg_cfe_ratio=0.58,
        )
    )
    for channel, first, window in [
        ("ambient_ppco2", 1, 0),
        ("heart_rate", 60, 60),
        ("respiratory_rate", 77, 60),
        ("spo2", 0.2, 0),
        ("eeg_cfe_ratio", 60, 60),
    ]:
        values = [o for o in items if o.reading.channel == channel and o.sample_kind == "scheduled"]
        assert values[0].acquired_s == first
        assert all(o.window_s == window for o in values)
    co2 = [o for o in items if o.reading.channel == "ambient_ppco2"]
    assert next(o.acquired_s for o in co2 if o.reading.value / MMHG_TO_PA > 3) == 154
    assert co2[-1].reading.value == pytest.approx(4.8 * MMHG_TO_PA)
    last = {o.reading.channel: o.reading.value for o in items}
    assert last["heart_rate"] * 60 == pytest.approx(104, abs=4)
    assert last["respiratory_rate"] * 60 == pytest.approx(24, abs=0.35)
    assert last["spo2"] * 100 == pytest.approx(92, abs=0.25)
    assert last["eeg_cfe_ratio"] == pytest.approx(1.28)


def test_latent_order_and_partial_windows():
    s = HypercapniaScenario()
    p = AstronautProfile(resting_hr_bpm=72)
    assert hypercapnia_cabin_mmhg(120, s) == 2.2
    assert hypercapnia_cabin_mmhg(210, s) == 4.8
    assert hypercapnia_references(130, p, s)["heart_rate"] == 72
    assert hypercapnia_references(150, p, s)["spo2"] == 97
    assert hypercapnia_references(240, p, s) == pytest.approx(
        dict(heart_rate=104, respiratory_rate=24, spo2=92, eeg_cfe_ratio=1.28)
    )
    assert (
        0.58
        < hypercapnia_eeg_values(180, s)["eeg_cfe_ratio"]
        < hypercapnia_references(180, p, s)["eeg_cfe_ratio"]
    )
    with pytest.raises(ValueError):
        hypercapnia_eeg_values(30, s)
    for group in ["heart", "respiration"]:
        healthy = crew_values(group, 180, p, 42)
        affected = crew_values(group, 180, p, 42, hypercapnia=s)
        assert affected[next(iter(affected))] > healthy[next(iter(healthy))]
    assert rmssd(120, p, 42, hypercapnia=s) == rmssd(120, p, 42)
    assert rmssd(400, p, 42, hypercapnia=s) == pytest.approx(40, abs=3)
    for group in ["bp", "temperature", "il6", "mass"]:
        assert crew_values(group, 400, p, 42, hypercapnia=s) == crew_values(group, 400, p, 42)


def test_ownership_selection_and_metadata():
    s = demo().model_copy(update={"crew": (AstronautProfile(id="a"), AstronautProfile(id="b"))})
    items = acquire(s, 300)
    assert {o.owner for o in items if o.reading.channel == "ambient_ppco2"} == {"iss_cabin"}
    assert {o.owner for o in items if o.reading.channel == "eeg_cfe_ratio"} == {"a", "b"}
    assert not acquire(s.model_copy(update={"enabled_channels": ()}))
    assert len(effective_channels(Settings())) == 29
    assert len(effective_channels(Settings(sans_scenario=SansScenario()))) == 34
    cfg = Settings(hypercapnia_scenario=HypercapniaScenario())
    assert len(effective_channels(cfg)) == 30
    info = dictionary(cfg.environment, 0, cfg)
    assert len(info.channels) == 36 and info.hypercapnia_scenario["onset_s"] == 120
    eeg = next(c for c in info.channels if c.channel == "eeg_cfe_ratio")
    assert eeg.raw_acquisition_hz is None and eeg.window_s == 60
    only = acquire(s.model_copy(update={"enabled_channels": ("spo2",)}), 300)
    assert only[-1].reading.value < 0.94
    with pytest.raises(ValueError):
        effective_channels(Settings(enabled_channels=("eeg_cfe_ratio",)))


@pytest.mark.parametrize(
    "change",
    [
        {"onset_s": float("nan")},
        {"ramp_duration_s": 0},
        {"compensation_delay_s": 30},
        {"affected_spo2_pct": 89},
        {"affected_ppco2_mmhg": 7},
        {"baseline_cfe_ratio": 2},
        {"baseline_respiratory_rate_br_min": 25},
    ],
)
def test_invalid_fault(change):
    with pytest.raises(ValidationError):
        HypercapniaScenario(**change)


def test_invalid_settings():
    for change in [
        dict(crew=()),
        dict(environment=Environment(id="other")),
        dict(environment=Environment(pressure_pa=600)),
        dict(sans_scenario=SansScenario()),
    ]:
        with pytest.raises(ValidationError):
            Settings(hypercapnia_scenario=HypercapniaScenario(), **change)


def test_mock_delivery():
    settings = demo().model_copy(update={"environment": Environment(comm_delay_s=5)})
    selected = [o for o in acquire(settings, 300) if o.acquired_s in (0, 300)]
    assert all(o.available_s == o.acquired_s + 5 for o in selected)

    async def run():
        requests = []

        async def receive(request):
            requests.append(request)
            return httpx.Response(204)

        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(receive)
        ) as client:
            clock = ManualClock()
            await clock.sleep_until(305)
            delivery = Delivery(settings, clock, HttpTransport(client))
            for o in selected:
                delivery.submit(o)
            task = asyncio.create_task(delivery.run())
            await delivery.finish(task)
        import json

        assert len(requests) == len(selected)
        for request, o in zip(requests, selected, strict=True):
            assert json.loads(request.content) == o.reading.model_dump(mode="json")
            assert request.headers["X-Owner-ID"] == o.owner
            assert request.headers["X-Sample-Kind"] == o.sample_kind

    asyncio.run(run())


def test_core_mapping_and_thresholds(monkeypatch):
    core = Path(__file__).resolve().parents[2] / "backend/packages/hydrograph-core/src"
    if not core.exists():
        pytest.skip("backend core checkout is not present")
    monkeypatch.syspath_prepend(str(core))
    from hydrograph_core.findings import hypoxia_co2_2_2

    items = acquire(demo())
    last = {o.reading.channel: o.reading.value for o in items}
    result = hypoxia_co2_2_2(last["spo2"] * 100, False, last["ambient_ppco2"] / MMHG_TO_PA, False)
    assert result["status"] == "warning"
    assert "scrubber" in result["action"]
    for spo2, co2, expected in [
        (97, 2.2, "nominal"),
        (94, 3, "nominal"),
        (93.99, 3, "warning"),
        (94, 3.01, "warning"),
        (90, 2.2, "warning"),
        (89.99, 2.2, "critical"),
    ]:
        assert hypoxia_co2_2_2(spo2, False, co2, False)["status"] == expected


def test_preview_references():
    from imitacija.preview import PreviewState

    settings = demo()
    state = PreviewState(settings)
    for item in acquire(settings, 0):
        if item.reading.channel not in {
            "ambient_ppco2",
            "heart_rate",
            "respiratory_rate",
            "spo2",
            "eeg_cfe_ratio",
        }:
            continue
        assert state.baseline(item) == pytest.approx(
            item.reading.value
            / (
                1 / 60
                if item.reading.channel in {"heart_rate", "respiratory_rate"}
                else 0.01
                if item.reading.channel == "spo2"
                else 1
            )
        )
