"""Following the backend's mission environment mid-run."""

import asyncio

import httpx
import pytest

from imitacija.clock import ManualClock
from imitacija.main import follow_environment
from imitacija.models import Settings
from imitacija.physiology import environment_values, monitor_dose_msv
from imitacija.scheduler import Scheduler

CATALOG = {
    "environments": [
        {
            "id": "iss_leo",
            "gravity_g": 0.0,
            "comm_delay_rt_s": 1.2,
            "baseline_dose_rate_usv_h": 14.6,
        },
        {
            "id": "mars_transit",
            "gravity_g": 0.0,
            "comm_delay_rt_s": 1560.0,
            "baseline_dose_rate_usv_h": 76.7,
        },
    ]
}


class Sink:
    def submit(self, item: object) -> None:
        pass


def scheduler_at(instant: float) -> Scheduler:
    clock = ManualClock()
    clock.instant = instant
    return Scheduler(Settings(), clock, Sink())


def test_switch_keeps_integrated_dose_continuous_and_changes_its_rate() -> None:
    scheduler = scheduler_at(3600)
    before = monitor_dose_msv(scheduler.settings.environment, 3600)

    scheduler.set_environment(gravity_g=0.377, comm_delay_s=780, dose_rate_usv_h=76.7)

    environment = scheduler.settings.environment
    assert monitor_dose_msv(environment, 3600) == pytest.approx(before)
    later = environment_values("radiation", 7200, environment, 42)
    assert later["ambient_integrated_dose"] == pytest.approx(monitor_dose_msv(environment, 7200))
    # one hour later at ~76.7 uSv/h: about 0.077 mSv more, not 18 uSv/h worth
    assert monitor_dose_msv(environment, 7200) - before == pytest.approx(0.0767, rel=0.15)
    assert later["ambient_dose_rate"] == pytest.approx(76.7, rel=0.13)
    assert (environment.gravity_g, environment.comm_delay_s) == (0.377, 780)


def backend(selected: list[str], *, fail: bool = False) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if fail:
            return httpx.Response(503)
        if request.url.path == "/api/environments/":
            return httpx.Response(200, json=CATALOG)
        return httpx.Response(200, json={"id": selected[0]})

    return httpx.MockTransport(handle)


async def follow_for(seconds: float, scheduler: Scheduler, transport: httpx.MockTransport) -> None:
    settings = Settings(environment_poll_wall_s=0.01)
    async with httpx.AsyncClient(base_url="http://backend", transport=transport) as client:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(follow_environment(client, scheduler, settings), seconds)


def test_follower_applies_the_selected_environment() -> None:
    scheduler = scheduler_at(0)
    selected = ["iss_leo"]

    async def run() -> None:
        await follow_for(0.05, scheduler, backend(selected))
        assert scheduler.settings.environment.dose_rate_usv_h == 14.6
        selected[0] = "mars_transit"
        await follow_for(0.05, scheduler, backend(selected))

    asyncio.run(run())

    environment = scheduler.settings.environment
    assert environment.dose_rate_usv_h == 76.7
    assert environment.comm_delay_s == 780  # one way: half the 1560 s round trip


def test_follower_survives_a_failing_backend(capsys: pytest.CaptureFixture[str]) -> None:
    scheduler = scheduler_at(0)
    original = scheduler.settings.environment

    asyncio.run(follow_for(0.05, scheduler, backend(["iss_leo"], fail=True)))

    assert scheduler.settings.environment == original
    assert capsys.readouterr().err.count("environment poll failed") == 1
