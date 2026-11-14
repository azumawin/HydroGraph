import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.main import load_settings
from imitacija.models import AstronautProfile, EvaDehydrationScenario, SansScenario, Settings
from imitacija.physiology import crew_values, heart_rate, rmssd
from imitacija.registry import dictionary, effective_channels
from imitacija.scenarios import eva_balance, eva_sweat_values
from imitacija.scheduler import Scheduler
from imitacija.units import MMHG_TO_PA


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
    return load_settings(Path("config/badscenario3.toml"), None, None)


def test_full_run_balance_startup_windows():
    cfg = demo()
    items = simulate(cfg, 10200)
    startup = [o for o in items if o.sample_kind == "startup_baseline"]
    assert len(startup) == 30
    assert {o.reading.channel for o in startup} == effective_channels(cfg)
    assert len({(o.owner, o.reading.channel) for o in startup}) == 30
    assert all(o.window_s == o.acquired_s == 0 for o in startup)
    assert sum(o.scope == "crew" for o in startup) == 25
    for channel, first, last, count, window in [
        ("whole_body_sweat_rate", 601, 9600, 9000, 1),
        ("sweat_rate", 601, 9600, 9000, 1),
        ("sweat_sodium_flux", 660, 9600, 150, 60),
    ]:
        rows = [o for o in items if o.reading.channel == channel and o.sample_kind == "scheduled"]
        assert (rows[0].acquired_s, rows[-1].acquired_s, len(rows)) == (first, last, count)
        assert all(o.window_s == window for o in rows)
    scheduled = [o for o in items if o.sample_kind == "scheduled"]
    mass = {o.acquired_s: o.reading.value for o in scheduled if o.reading.channel == "body_mass"}
    assert mass[5100] == pytest.approx(74.1)
    assert mass[9600] == mass[10200] == pytest.approx(73.2)
    assert next(t for t, v in mass.items() if round(100 * (75 - v) / 75, 9) > 2) == 8160
    assert [
        o.acquired_s for o in scheduled if o.reading.channel == "urine_specific_gravity"
    ] == list(cfg.eva_dehydration_scenario.usg_event_times_s)
    last = {o.reading.channel: o.reading.value for o in items}
    assert last["heart_rate"] * 60 == pytest.approx(122, abs=0.8)
    assert last["bp_systolic"] / MMHG_TO_PA == pytest.approx(98, abs=1.2)
    assert last["bp_diastolic"] / MMHG_TO_PA == pytest.approx(74, abs=0.8)
    assert last["urine_specific_gravity"] == pytest.approx(1.026)
    assert last["whole_body_sweat_rate"] * 3_600_000 == pytest.approx(0.820)
    assert last["sweat_rate"] * 1800 == pytest.approx(last["whole_body_sweat_rate"])
    assert last["sweat_sodium_flux"] == pytest.approx(last["sweat_rate"] * 74)
    assert sum(
        o.reading.value * 1000 for o in scheduled if o.reading.channel == "whole_body_sweat_rate"
    ) == pytest.approx(2.05)
    assert sum(
        o.reading.value * 60 * 1000 * 1800
        for o in scheduled
        if o.reading.channel == "sweat_sodium_flux"
    ) == pytest.approx(151.7)


def test_balance_and_owner_isolation():
    s = EvaDehydrationScenario()
    p = AstronautProfile(resting_hr_bpm=72, dbp_mmhg=78)
    assert eva_balance(5100, p, s)["deficit_l"] == pytest.approx(0.9)
    b = eva_balance(9600, p, s)
    assert b == eva_balance(10200, p, s)
    assert b["sweat_loss_l"] == pytest.approx(2.05)
    assert b["intake_l"] == pytest.approx(0.25)
    assert b["loss_pct"] == pytest.approx(2.4)
    assert eva_balance(9600, p, s.model_copy(update={"drink_rate_l_h": 0}))["loss_pct"] > 2.4
    other = AstronautProfile(id="other")
    for group in ["heart", "bp", "mass", "usg", "sweat", "temperature", "il6"]:
        assert crew_values(group, 9600, other, 42, dehydration=s) == crew_values(
            group, 9600, other, 42
        )
    assert rmssd(10200, p, 42, dehydration=s) == pytest.approx(p.rmssd_ms, abs=3)
    assert heart_rate(17.5 * 3600, p, 42, dehydration=s) == pytest.approx(122, abs=0.8)
    cfg = Settings(
        crew=(p, other),
        eva_dehydration_scenario=s,
        enabled_channels=("whole_body_sweat_rate", "body_mass", "bp_systolic"),
    )
    rows = simulate(cfg, 660)
    assert all(o.owner == p.id for o in rows if o.reading.channel == "whole_body_sweat_rate")
    assert (
        len(
            [
                o
                for o in rows
                if o.reading.channel == "body_mass"
                and o.owner == p.id
                and o.sample_kind == "scheduled"
            ]
        )
        == 11
    )
    assert len(effective_channels(Settings())) == 29
    assert not simulate(cfg.model_copy(update={"enabled_channels": ()}), 660)
    assert eva_sweat_values(9601, s) == {}
    info = dictionary(cfg.environment, 0, cfg)
    assert info.eva_dehydration_scenario["owner_id"] == p.id


@pytest.mark.parametrize(
    "change",
    [
        dict(drink_rate_l_h=0.9),
        dict(eva_duration_s=61),
        dict(onset_s=-1),
        dict(whole_body_to_patch_multiplier=0),
        dict(usg_event_times_s=(2, 1)),
        dict(active_whole_body_sweat_l_h=float("nan")),
    ],
)
def test_invalid(change):
    with pytest.raises(ValidationError):
        EvaDehydrationScenario(**change)


def test_invalid_settings_and_selection():
    for change in [dict(crew=()), dict(sans_scenario=SansScenario()), dict(stand_test_start_s=100)]:
        with pytest.raises(ValidationError):
            Settings(eva_dehydration_scenario=EvaDehydrationScenario(), **change)
    with pytest.raises(ValueError):
        effective_channels(Settings(enabled_channels=("whole_body_sweat_rate",)))
    cfg = demo().model_copy(
        update={"eva_dehydration_scenario": EvaDehydrationScenario(usg_event_times_s=())}
    )
    assert not [
        o
        for o in simulate(cfg, 660)
        if o.reading.channel == "urine_specific_gravity" and o.sample_kind == "scheduled"
    ]


def test_backend_mapping(monkeypatch):
    core = Path(__file__).resolve().parents[2] / "backend/packages/hydrograph-core/src"
    if not core.exists():
        pytest.skip("backend checkout unavailable")
    monkeypatch.syspath_prepend(str(core))
    from hydrograph_core.channels import CHANNELS, evaluate_reading
    from hydrograph_core.findings import dehydration_2_1

    assert "whole_body_sweat_rate" in CHANNELS
    from hydrograph_core.environments import ENVIRONMENTS

    assert (
        evaluate_reading(
            "whole_body_sweat_rate", 0.820 / 3_600_000, environment=ENVIRONMENTS["iss_leo"]
        )
        == "unspecified"
    )
    r = dehydration_2_1(73.2, 75, 1.026)
    assert r["status"] is True and r["fluid_deficit_ml"] == 1800
    assert r["body_mass_loss_pct"] == 2.4
    assert dehydration_2_1(100, 100, 1.012)["status"] is False
    assert dehydration_2_1(98, 100, 1.020)["status"] is False
    assert dehydration_2_1(97.9, 100, 1.012)["status"] is True
    assert dehydration_2_1(100, 100, 1.026)["status"] is True


def test_deterministic_transport_and_late_guard():
    import json

    import httpx

    from imitacija.delivery import Delivery, HttpTransport
    from imitacija.models import Environment
    from imitacija.preview import PreviewState

    cfg = demo().model_copy(update={"environment": Environment(comm_delay_s=5)})
    items = simulate(cfg, 660)
    assert items == simulate(cfg, 660)
    selected = [
        o
        for o in items
        if o.sample_kind == "startup_baseline"
        or o.reading.channel == "whole_body_sweat_rate"
        and o.acquired_s == 601
    ]
    assert len(selected) == 31
    assert all(o.available_s == o.acquired_s + 5 for o in selected)
    state = PreviewState(cfg)
    whole = next(o for o in selected if o.reading.channel == "whole_body_sweat_rate")
    assert state.baseline(whole) == 0.045
    sink = Sink()
    clock = ManualClock()
    scheduler = Scheduler(cfg, clock, sink)
    event = next(e for e in scheduler.events if e.rule.group == "eva_sweat")
    scheduler.acquire(event, 9601)
    assert not sink.items

    async def run():
        requests = []

        async def receive(request):
            requests.append(request)
            return httpx.Response(204)

        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(receive)
        ) as client:
            await clock.sleep_until(666)
            delivery = Delivery(cfg, clock, HttpTransport(client))
            for item in selected:
                delivery.submit(item)
            task = asyncio.create_task(delivery.run())
            await delivery.finish(task)
        assert len(requests) == 31
        for request, item in zip(requests, selected, strict=True):
            assert json.loads(request.content) == item.reading.model_dump(mode="json")
            assert request.headers["X-Sample-Kind"] == item.sample_kind
            assert request.headers["X-Owner-ID"] == item.owner

    asyncio.run(run())
