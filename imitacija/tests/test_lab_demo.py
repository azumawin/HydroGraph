"""Assay, specimen and spot-collection trends reach the wire for a dashboard run.

These channels acquire on a calendar: the next cortisol is hours away, the next
24h urine a day, the next vitamin D a month. A dashboard run therefore showed
their startup baseline and nothing else. The demo override publishes them at a
fixed interval and walks each one along its own calendar, so the points are this
simulator's own trajectory; nothing about the unconfigured protocol path, and
nothing a scenario owns, may change with it.
"""

import asyncio
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.frequency import LAB_DEMO_CALENDAR
from imitacija.main import load_settings
from imitacija.models import Observation, Settings
from imitacija.physiology import crew_values
from imitacija.registry import CHANNELS, dictionary
from imitacija.scheduler import Scheduler
from imitacija.units import convert

INTERVAL = 5.0

# Every channel that used to show one startup point and nothing else, by the
# acquisition group whose calendar the demo compresses.
SPARSE: dict[str, tuple[str, ...]] = {
    "cortisol": ("cortisol_saliva",),
    "troponin": ("troponin_i",),
    "lactate": ("lactate",),
    "vitamin": ("vitamin_d_25oh",),
    "il6": ("il6_serum",),
    "mass": ("body_mass",),
    "usg": ("urine_specific_gravity",),
    "urine": ("urine_volume_24h",),
    "ntx": ("urinary_ntx", "bone_ntx_pct_baseline"),
    "sweat": ("sweat_rate", "sweat_sodium_concentration"),
    "sweat_summary": ("sweat_sodium_flux",),
}
CHANNEL_NAMES = tuple(name for names in SPARSE.values() for name in names)


class Samples:
    def __init__(self) -> None:
        self.items: list[Observation] = []

    def submit(self, item: Observation) -> None:
        self.items.append(item)


def acquire(settings: Settings, until: float) -> list[Observation]:
    sink = Samples()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(until))
    return sink.items


def scheduled(items: list[Observation], channel: str) -> list[Observation]:
    return [o for o in items if o.reading.channel == channel and o.sample_kind == "scheduled"]


def test_every_group_the_demo_covers_is_a_real_acquisition_group() -> None:
    for group, names in SPARSE.items():
        assert group in LAB_DEMO_CALENDAR
        assert {c.id for c in CHANNELS.values() if c.group == group} == set(names)
    assert set(LAB_DEMO_CALENDAR) == set(SPARSE)


# badscenario3 and 4 give their target crew member explicit schedules for some of
# these groups, which the demo must leave alone; they are checked on their own below.
@pytest.mark.parametrize("config", ["healthy.toml", "badscenario1.toml", "badscenario2.toml"])
def test_each_sparse_channel_fills_its_chart_from_the_first_interval(config: str) -> None:
    settings = load_settings(Path("config") / config, None, None, lab_demo_interval=INTERVAL)
    settings = settings.model_copy(update={"enabled_channels": CHANNEL_NAMES})
    items = acquire(settings, 120)
    assert items == acquire(settings, 120)

    for name in CHANNEL_NAMES:
        startup = [o for o in items if o.reading.channel == name and o.sample_kind != "scheduled"]
        samples = scheduled(items, name)
        assert [o.acquired_s for o in startup] == [0], name
        assert [o.acquired_s for o in samples] == [float(t) for t in range(5, 121, 5)], name
        assert [o.sequence for o in samples] == list(range(2, 26)), name
        # A trend, not the same stored value published again.
        assert len({float(o.reading.value) for o in samples}) > 5, name


def test_each_sample_is_the_model_value_at_its_own_calendar_instant() -> None:
    """The points are the simulator's trajectory, sampled coarsely."""
    settings = Settings(enabled_channels=CHANNEL_NAMES, lab_demo_interval_s=INTERVAL)
    profile = settings.crew[0]
    items = acquire(settings, 120)

    for group, names in SPARSE.items():
        calendar = LAB_DEMO_CALENDAR[group]
        for index, item in enumerate(scheduled(items, names[0])):
            instant = calendar.instant(index)
            assert instant == calendar.first + index * calendar.step
            source = crew_values(group, instant, profile, settings.seed)[names[0]]
            channel = CHANNELS[names[0]]
            assert float(item.reading.value) == pytest.approx(
                convert(float(source), channel.factor, channel.offset)
            ), (group, index)
            # The acquisition instant itself still stamps the reading.
            assert item.acquired_s == (index + 1) * INTERVAL


def test_demo_results_are_not_held_for_the_synthetic_laboratory() -> None:
    settings = Settings(enabled_channels=("cortisol_saliva",), lab_demo_interval_s=INTERVAL)
    assert CHANNELS["cortisol_saliva"].lab
    for item in scheduled(acquire(settings, 120), "cortisol_saliva"):
        assert item.available_s == item.acquired_s

    # Without the override the same assay waits its configured laboratory hour.
    plain = Settings(enabled_channels=("cortisol_saliva",))
    first = scheduled(acquire(plain, 7 * 3600), "cortisol_saliva")[0]
    assert first.acquired_s == 7 * 3600
    assert first.available_s == 7 * 3600 + plain.lab_delay_s


def test_protocol_calendars_are_untouched_without_the_override() -> None:
    settings = Settings(enabled_channels=CHANNEL_NAMES)
    items = acquire(settings, 1200)

    assert [o.sample_kind for o in items] == ["startup_baseline"] * len(CHANNEL_NAMES)
    assert {o.reading.channel for o in items} == set(CHANNEL_NAMES)


@pytest.mark.parametrize(
    ("config", "channel", "expected"),
    [
        # The EVA target's own 60s mass points and its configured spot urine times.
        ("badscenario3.toml", "body_mass", [60.0, 120.0, 180.0, 240.0, 300.0]),
        ("badscenario3.toml", "urine_specific_gravity", [600.0, 3600.0]),
        # The infection target's configured serum specimen.
        ("badscenario4.toml", "il6_serum", [1860.0]),
    ],
)
def test_a_scenario_target_keeps_the_schedule_its_fault_gave_it(
    config: str, channel: str, expected: list[float]
) -> None:
    settings = load_settings(Path("config") / config, None, None, lab_demo_interval=INTERVAL)
    settings = settings.model_copy(update={"enabled_channels": (channel,)})
    times = [o.acquired_s for o in scheduled(acquire(settings, max(expected)), channel)]
    assert times[: len(expected)] == expected


def test_the_daily_sweat_bout_is_replayed_rather_than_running_dry() -> None:
    """Local sweat has no resting acquisition, so its demo wraps its active window."""
    calendar = LAB_DEMO_CALENDAR["sweat"]
    assert calendar.samples is not None
    settings = Settings(enabled_channels=("sweat_rate",), lab_demo_interval_s=INTERVAL)
    samples = scheduled(acquire(settings, (calendar.samples + 2) * INTERVAL), "sweat_rate")

    assert len(samples) == calendar.samples + 2
    # The bout starts over instead of the patch going dry mid-run.
    assert samples[calendar.samples].reading.value == samples[0].reading.value
    assert samples[calendar.samples + 1].reading.value == samples[1].reading.value


def test_the_compressed_calendar_raises_no_alert_of_its_own() -> None:
    """Core grades these channels one reading at a time, so a demo sample sweeping
    a whole day of the trajectory must still land in the nominal band. Cutoffs are
    hydrograph_core.channels.evaluate_reading's, in the wire units it grades.
    """
    settings = load_settings(
        Path("config/badscenario1.toml"), None, None, lab_demo_interval=INTERVAL
    )
    settings = settings.model_copy(update={"enabled_channels": CHANNEL_NAMES})
    items = acquire(settings, 1500)
    worst = {
        name: (
            min(float(o.reading.value) for o in scheduled(items, name)),
            max(float(o.reading.value) for o in scheduled(items, name)),
        )
        for name in CHANNEL_NAMES
    }

    assert worst["lactate"][1] < 4.0  # Finding 7: resting lactate > 4.0 mmol/L
    assert worst["troponin_i"][1] * 1e6 < 0.04  # Finding 1: hs-cTnI > 0.04 ng/mL
    assert worst["il6_serum"][1] * 1e9 < 3.0  # Finding 3: IL-6 > 3.0 pg/mL
    assert worst["urine_specific_gravity"][1] < 1.020  # Finding 2: USG > 1.020
    assert worst["urine_volume_24h"][0] * 1000 > 2.0  # Finding 8: < 2.0 L/day
    assert worst["bone_ntx_pct_baseline"][1] < 0.25  # Finding 8: NTx > +25 %
    # Finding 2 and 2.3 compare body mass against the run's first reading.
    first = float(scheduled(items, "body_mass")[0].reading.value)
    assert (first - worst["body_mass"][0]) / first * 100 < 1.0


def test_demo_metadata_and_validation() -> None:
    settings = Settings(lab_demo_interval_s=INTERVAL)
    entries = {
        c.channel: c
        for c in dictionary(settings.environment, settings.lab_delay_s, settings).channels
    }
    plain = {
        c.channel: c for c in dictionary(Settings().environment, 3600, Settings()).channels
    }

    for name in CHANNEL_NAMES:
        assert "dashboard demo: every 5.0s" in entries[name].collection_schedule
        assert entries[name].frequency_basis == "explicit dashboard demo override"
        assert entries[name].availability_delay_s == 0
        assert plain[name].frequency_basis == "docs/frequency_table.md"
    assert plain["cortisol_saliva"].availability_delay_s == 3600

    # A lab channel the demo does not cover keeps its processing delay.
    assert "viral_ebv_detected" not in CHANNEL_NAMES
    assert entries["viral_ebv_detected"].availability_delay_s == settings.lab_delay_s

    for invalid in (0, -1, 0.01, 61, math.inf, math.nan):
        with pytest.raises(ValidationError):
            Settings(lab_demo_interval_s=invalid)
