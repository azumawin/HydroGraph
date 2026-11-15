"""A synthetic CGM trend reaches the wire without changing protocol defaults.

The CGM's own 5-minute sensor window puts its first completed result 343 s into
a run, so a short dashboard demo showed one startup point and nothing else. The
demo override samples a correspondingly shorter window instead; everything about
the unconfigured protocol path has to stay exactly as it was.
"""

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.main import load_settings
from imitacija.models import CGM_WINDOW_S, Observation, Settings
from imitacija.physiology import crew_values, glucose_demo_scale
from imitacija.registry import dictionary
from imitacija.scheduler import Scheduler

INTERVAL = 5.0


class Samples:
    def __init__(self) -> None:
        self.items: list[Observation] = []

    def submit(self, item: Observation) -> None:
        self.items.append(item)


def acquire(settings: Settings, until: float) -> list[Observation]:
    sink = Samples()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(until))
    return sink.items


def demo(config: str) -> Settings:
    settings = load_settings(
        Path("config") / config, None, None, glucose_demo_interval=INTERVAL
    )
    return settings.model_copy(update={"enabled_channels": ("glucose",)})


@pytest.mark.parametrize("config", ["healthy.toml", *(f"badscenario{i}.toml" for i in range(1, 5))])
def test_each_scenario_fills_the_chart_from_the_first_interval(config: str) -> None:
    settings = demo(config)
    items = acquire(settings, 120)
    assert items == acquire(settings, 120)

    startup = [o for o in items if o.sample_kind == "startup_baseline"]
    scheduled = [o for o in items if o.sample_kind == "scheduled"]
    assert [o.acquired_s for o in startup] == [0]
    # Every interval from the first one, instead of a single point until 343 s.
    assert [o.acquired_s for o in scheduled] == [float(t) for t in range(5, 121, 5)]
    assert [o.sequence for o in scheduled] == list(range(2, 26))

    shown = [round(float(o.reading.value), 2) for o in scheduled]
    assert max(shown) - min(shown) > 0.1
    assert len(set(shown)) > 5


@pytest.mark.parametrize("config", ["badscenario1.toml", "healthy.toml"])
def test_demo_result_is_its_own_window_mean_and_says_so(config: str) -> None:
    """The reading must not claim the 5 minutes the registry records."""
    settings = demo(config)
    profile = settings.crew[0]
    last = acquire(settings, 120)[-1]

    assert last.acquired_s == 120
    assert last.window_s == INTERVAL
    source = crew_values(
        "glucose", 120, profile, settings.seed, glucose_window_s=INTERVAL
    )["glucose"]
    assert float(last.reading.value) == pytest.approx(
        float(source) * glucose_demo_scale(120, settings.seed, profile.id)
    )
    # A bounded trend around the healthy trajectory, not a new excursion.
    assert float(last.reading.value) == pytest.approx(float(source), rel=0.03)


def test_protocol_schedule_is_untouched_without_the_override() -> None:
    settings = Settings(enabled_channels=("glucose",))
    items = acquire(settings, 342)

    # Only the startup fixture before the first completed sensor window.
    assert [o.sample_kind for o in items] == ["startup_baseline"]
    first = [o for o in acquire(settings, 400) if o.sample_kind == "scheduled"][0]
    assert first.acquired_s == 343
    assert first.window_s == CGM_WINDOW_S
    assert float(first.reading.value) == pytest.approx(
        float(crew_values("glucose", 343, settings.crew[0], settings.seed)["glucose"])
    )


def test_demo_metadata_and_validation() -> None:
    settings = Settings(
        enabled_channels=("glucose",), glucose_demo_interval_s=INTERVAL
    )
    entry = next(
        c
        for c in dictionary(settings.environment, settings.lab_delay_s, settings).channels
        if c.channel == "glucose"
    )

    assert "every 5.0s" in entry.collection_schedule
    assert "synthetic dashboard trend" in entry.method
    assert entry.frequency_basis == "explicit dashboard demo override"
    assert entry.window_s == INTERVAL

    plain = next(
        c
        for c in dictionary(Settings().environment, 0, Settings()).channels
        if c.channel == "glucose"
    )
    assert plain.window_s == CGM_WINDOW_S
    assert plain.frequency_basis == "docs/frequency_table.md"
    assert "synthetic dashboard trend" not in plain.method

    for invalid in (0, -1, 0.01, 61, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            Settings(glucose_demo_interval_s=invalid)
