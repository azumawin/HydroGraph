import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.main import load_settings
from imitacija.models import AcuteInfectionScenario, AstronautProfile, Reading
from imitacija.physiology import crew_values
from imitacija.registry import effective_channels
from imitacija.scheduler import Scheduler


class Sink:
    def __init__(self):
        self.items = []

    def submit(self, item):
        self.items.append(item)


def simulate(cfg, end):
    sink = Sink()
    scheduler = Scheduler(cfg, ManualClock(), sink)
    asyncio.run(scheduler.run(end))
    scheduler.initialize()
    return sink.items


def demo():
    return load_settings(Path("config/badscenario4.toml"), None, None)


def test_full_demo(monkeypatch):
    cfg = demo()
    items = simulate(cfg, 2400)
    assert items == simulate(cfg, 2400)
    startup = [o for o in items if o.sample_kind == "startup_baseline"]
    assert len(startup) == 33 and {o.reading.channel for o in startup} == effective_channels(cfg)
    assert len({(o.owner, o.reading.channel) for o in startup}) == 33
    assert all(o.window_s == o.acquired_s == 0 for o in startup)
    assert (
        next(o.reading.value for o in startup if o.reading.channel == "consciousness_level")
        == "ALERT"
    )
    labs = [
        o
        for o in items
        if o.sample_kind == "scheduled" and o.reading.channel in {"il6_serum", "viral_ebv_detected"}
    ]
    assert len(labs) == 2 and all(o.acquired_s == 1860 and o.available_s == 1980 for o in labs)
    latest = {o.reading.channel: o.reading.value for o in items}
    assert latest["il6_pg_mL"] == pytest.approx(8.4e-9)
    assert latest["body_temperature"] == pytest.approx(311.85, abs=0.025)
    core = Path(__file__).resolve().parents[2] / "backend/packages/hydrograph-core/src"
    monkeypatch.syspath_prepend(str(core))
    from hydrograph_core.assessment import evaluate_findings, news2, qsofa

    r = evaluate_findings(latest, None, None)["acute_infection_3_1"]
    assert r["news2_score"] == 8 and r["qsofa_score"] == 2 and r["status"] == "critical"
    assert r["il6_source_channel"] == "il6_pg_mL"
    before = {o.reading.channel: o.reading.value for o in items if o.available_s <= 1920}
    assert evaluate_findings(before, None, None)["acute_infection_3_1"]["status"] == "critical"
    assert (
        news2(23, 94, 96, 116, 38.7, consciousness_level="CONFUSION", supplemental_o2=True)["score"]
        == 13
    )
    assert qsofa(23, 96, "CONFUSION") == 3


def test_owner_and_optional_events():
    cfg = demo()
    other = AstronautProfile(id="other")
    cfg = cfg.model_copy(
        update={
            "crew": (*cfg.crew, other),
            "acute_infection_scenario": AcuteInfectionScenario(
                serum_il6_event_times_s=(), saliva_pcr_event_times_s=()
            ),
        }
    )
    rows = simulate(cfg, 2000)
    assert not [
        o
        for o in rows
        if o.owner == "crew-1"
        and o.sample_kind == "scheduled"
        and o.reading.channel in {"il6_serum", "viral_ebv_detected"}
    ]
    assert all(o.owner == "crew-1" for o in rows if o.reading.channel == "consciousness_level")
    for group in ["heart", "bp", "temperature", "respiration", "il6"]:
        assert crew_values(
            group, 2000, other, 42, infection=cfg.acute_infection_scenario
        ) == crew_values(group, 2000, other, 42)
    assert not simulate(cfg.model_copy(update={"enabled_channels": ()}), 100)


@pytest.mark.parametrize(
    "channel,value,unit",
    [
        ("consciousness_level", "alert", "ACVPU"),
        ("heart_rate", "2", "s^-1"),
        ("supplemental_o2", 1, "boolean"),
        ("heart_rate", "ALERT", "s^-1"),
    ],
)
def test_invalid_values(channel, value, unit):
    with pytest.raises(ValidationError):
        Reading(channel=channel, value=value, unit=unit, measured_at="2026-11-14T00:00:00Z")


@pytest.mark.parametrize(
    "change",
    [
        dict(affected_at_s=600),
        dict(affected_temp_c=float("nan")),
        dict(saliva_pcr_event_times_s=(3, 2)),
        dict(affected_consciousness_level="bad"),
    ],
)
def test_invalid_config(change):
    with pytest.raises(ValidationError):
        AcuteInfectionScenario(**change)


def test_enum_transport():
    import json

    import httpx

    from imitacija.delivery import Delivery, HttpTransport
    from imitacija.preview import PreviewState

    cfg = demo()
    selected = [
        o
        for o in simulate(cfg, 0)
        if o.reading.channel in {"consciousness_level", "supplemental_o2", "il6_pg_mL"}
    ]
    state = PreviewState(cfg)
    for item in selected:
        state.record(item)
    assert "ALERT" in state.snapshot().decode()

    async def run():
        requests = []

        async def receive(request):
            requests.append(request)
            return httpx.Response(201)

        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(receive)
        ) as client:
            delivery = Delivery(cfg, ManualClock(), HttpTransport(client))
            for item in selected:
                delivery.submit(item)
            task = asyncio.create_task(delivery.run())
            await delivery.finish(task)
        assert len(requests) == 3
        for request, item in zip(requests, selected, strict=True):
            assert json.loads(request.content) == item.reading.model_dump(mode="json")
            assert request.headers["X-Sample-Kind"] == "startup_baseline"

    asyncio.run(run())
