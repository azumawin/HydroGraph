"""Paired pressure demo trends reach the wire without changing protocol defaults."""

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.main import load_settings
from imitacija.models import Observation, Settings
from imitacija.physiology import blood_pressure_demo_scale, crew_values
from imitacija.registry import dictionary
from imitacija.scheduler import Scheduler
from imitacija.units import MMHG_TO_PA

PRESSURES = ("bp_systolic", "bp_diastolic")


class Samples:
    def __init__(self) -> None:
        self.items: list[Observation] = []

    def submit(self, item: Observation) -> None:
        self.items.append(item)


def acquire(settings: Settings, until: float) -> list[Observation]:
    sink = Samples()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(until))
    return sink.items


@pytest.mark.parametrize("config", ["healthy.toml", *(f"badscenario{i}.toml" for i in range(1, 5))])
def test_each_scenario_has_changing_synchronized_pressure_samples(config: str) -> None:
    settings = load_settings(Path("config") / config, None, None, bp_demo_interval=5)
    settings = settings.model_copy(update={"enabled_channels": PRESSURES})
    items = acquire(settings, 120)
    assert items == acquire(settings, 120)
    by_channel = {name: [o for o in items if o.reading.channel == name] for name in PRESSURES}
    for name, samples in by_channel.items():
        assert [o.acquired_s for o in samples] == list(range(0, 121, 5))
        assert [o.sequence for o in samples] == list(range(1, 26))
        shown = [round(float(o.reading.value) / MMHG_TO_PA, 1) for o in samples]
        assert max(shown) - min(shown) > (2 if name == "bp_systolic" else 1)
        assert len(set(shown)) > 5
    for systolic, diastolic in zip(*by_channel.values(), strict=True):
        assert systolic.reading.measured_at == diastolic.reading.measured_at
        assert systolic.reading.value > diastolic.reading.value
        assert systolic.reading.unit == diastolic.reading.unit == "Pa"


@pytest.mark.parametrize("config", ["badscenario3.toml", "badscenario4.toml"])
def test_demo_preserves_underlying_disease_pressure_trajectory(config: str) -> None:
    settings = load_settings(Path("config") / config, None, None, bp_demo_interval=5)
    settings = settings.model_copy(update={"enabled_channels": PRESSURES})
    items = acquire(settings, 2400)
    profile = settings.crew[0]
    original = crew_values(
        "bp",
        2400,
        profile,
        settings.seed,
        dehydration=settings.eva_dehydration_scenario,
        infection=settings.acute_infection_scenario,
    )
    for item in items[-2:]:
        source = float(item.reading.value) / MMHG_TO_PA
        expected = original[item.reading.channel]
        assert source == pytest.approx(
            expected * blood_pressure_demo_scale(2400, settings.seed, profile.id)
        )
        assert source == pytest.approx(expected, rel=0.03)


def test_protocol_defaults_and_demo_metadata() -> None:
    normal = Settings(enabled_channels=PRESSURES)
    assert len(acquire(normal, 3600)) == 2  # Only the startup pair before hour 8.
    demo = normal.model_copy(update={"bp_demo_interval_s": 5})
    metadata = dictionary(demo.environment, demo.lab_delay_s, demo)
    for channel in metadata.channels:
        if channel.channel in PRESSURES:
            assert "every 5s" in channel.collection_schedule
            assert "synthetic dashboard trend" in channel.method
            assert channel.frequency_basis == "explicit dashboard demo override"
    for invalid in (0, -1, 0.01, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            Settings(bp_demo_interval_s=invalid)
