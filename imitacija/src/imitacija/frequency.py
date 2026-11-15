"""Executable interpretation of docs/frequency_table.md for implemented channels.

Raw acquisition, publication and backend clinical evaluation are different clocks.
The simulator evaluates latent raw samples on demand for completed windows; it
never publishes 100 scalar heart rates per second as a substitute for a PPG waveform.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frequency:
    """Project timing policy; missing interval means a calendar/event acquisition."""

    description: str
    raw_hz: float | None = None
    interval_s: float | None = None
    window_s: float = 0
    rows: tuple[int, ...] = ()


FREQUENCIES: dict[str, Frequency] = {
    "infection_context": Frequency(
        "configured state heartbeat; no examination", interval_s=60, rows=(3,)
    ),
    "infection_gfet": Frequency(
        "synthetic concentration mean; no electrical waveform",
        interval_s=60,
        window_s=60,
        rows=(3,),
    ),
    "eva_sweat": Frequency("1s whole-body fixture during explicit EVA", 1, 1, 1, (2,)),
    "eeg_cfe": Frequency(
        "60s mean synthetic ratio fixture; no raw EEG", interval_s=60, window_s=60, rows=(5,)
    ),
    "cephalic": Frequency("60s mean synthetic strain trend; 50Hz latent grid", 50, 60, 60, (9,)),
    "eye_screen": Frequency("configured synthetic completed eye-screen events", rows=(9,)),
    "heart": Frequency("10s HR estimate every 10s (6/min); first at 10s", 100, 10, 10, (1,)),
    "hrv": Frequency("60s RMSSD window every 60s; first at 61s", 100, 60, 60, (1,)),
    "bp": Frequency(
        "hourly in configured session; optional 10Hz / 180s stand-test burst", rows=(1,)
    ),
    "spo2": Frequency(
        "1Hz scalar pulse-oximetry; backend acute checks every 5s", 1, 1, rows=(3, 4)
    ),
    "temperature": Frequency("1Hz core-equivalent temperature", 1, 1, rows=(3,)),
    "respiration": Frequency(
        "60s respiratory estimate every 60s; first at 77s", interval_s=60, window_s=60, rows=(3, 4)
    ),
    "glucose": Frequency(
        "5-minute CGM result from 5s raw samples; first at 343s", 0.2, 300, 300, (7,)
    ),
    "sweat": Frequency(
        "1Hz local flow/concentration while active and wet; no resting acquisition", 1, 1, 1, (2,)
    ),
    "sweat_summary": Frequency(
        "60s integrated local sodium loss rate while active and wet", 1, 60, 60, (2,)
    ),
    "cortisol": Frequency("every 4 waking hours: 07:00/11:00/15:00/19:00/23:00 daily", rows=(6,)),
    "troponin": Frequency("configured assay events only; default synthetic baseline", rows=(1,)),
    "lactate": Frequency("baseline and configured exercise-test sessions; not specified by matrix"),
    "vitamin": Frequency("baseline then every 30 days (monthly simulator convention)", rows=(7,)),
    "il6": Frequency("explicitly configured gated assay events; default baseline only", rows=(3,)),
    "ntx": Frequency(
        "weekly completed 24h urine specimen; first result at FD7", window_s=86400, rows=(8,)
    ),
    "urine": Frequency(
        "completed 24h urine volume daily; first result at FD1", window_s=86400, rows=(8,)
    ),
    "usg": Frequency("spot urine twice daily pre/post activity: 07:00 and 18:30", rows=(2,)),
    "mass": Frequency("daily pre/post activity mass: 07:00 and 18:30", rows=(2, 7)),
    "saliva_pcr": Frequency("saliva PCR every 48h at 09:00 (daily/48h matrix choice)", rows=(3,)),
    "urine_pcr": Frequency(
        "CMV urine PCR every 48h at 10:00; adaptation of viral session cadence", rows=(3,)
    ),
    "co2": Frequency("1Hz cabin CO2; backend acute checks every 5s", 1, 1, rows=(4,)),
    "light": Frequency("1Hz ambient photopic light; no sleep inference", 1, 1, rows=(5,)),
    "radiation": Frequency("1Hz monitor dose-equivalent rate", 1, 1, rows=(10,)),
    "radiation_dose": Frequency("60s integrated monitor dose publication", 1, 60, rows=(10,)),
    "spe": Frequency("1Hz SPE heartbeat, independent of crew state", 1, 1, rows=(10,)),
}


@dataclass(frozen=True)
class Calendar:
    """Where a dashboard-demo sample sits on a sparse channel's own calendar.

    ``samples`` bounds a group that only acquires inside a daily window: the
    demo replays that window instead of polling a patch that is dry or a
    specimen that does not exist.
    """

    first: float
    step: float
    samples: int | None = None

    def instant(self, index: int) -> float:
        """Protocol time of this group's index-th demo sample."""
        return self.first + (index % self.samples if self.samples else index) * self.step


# A dashboard chart needs a point a second at most, and the demo below publishes
# thirteen channels at once. At accelerated speed a five-simulation-second
# interval is far past that: the transport cannot absorb the volume, the bounded
# queue thins the busiest channels to keep up, and the dashboard ends up with
# fewer points than it would have had -- including on the vitals it was already
# drawing. So a demo sample is never asked for more often than this many
# simulation seconds per wall second.
LAB_DEMO_MIN_WALL_S = 1.0


def lab_demo_interval(configured: float, speed: float) -> float:
    """The demo interval in effect: the configured one, or the rate floor above.

    At the demo's own speed of 1 these are the same. Only an accelerated run
    moves the floor, where a chart gains nothing from a faster stream than the
    backend can store.
    """
    return max(configured, speed * LAB_DEMO_MIN_WALL_S)


# Assay, 24h-specimen and spot-collection protocols put their next result hours,
# days or a month out, so a dashboard run shows their startup baseline and
# nothing else. The demo publishes these groups at a fixed interval and evaluates
# each sample one step further along their own calendar: the trend is this
# simulator's trajectory sampled coarsely, never a value invented for the chart.
# Each step is the group's own cadence, except where its trajectory moves more
# slowly than that cadence and finer steps are what show a trend at all.
LAB_DEMO_CALENDAR: dict[str, Calendar] = {
    "cortisol": Calendar(7 * 3600, 4 * 3600),
    "troponin": Calendar(3600, 3600),
    "lactate": Calendar(17 * 3600, 1800),
    # Monthly assay, but its seasonal curve runs over 90 days: a month per
    # sample would step a third of that curve at a time.
    "vitamin": Calendar(30 * 86400, 5 * 86400),
    "il6": Calendar(3600, 3600),
    "mass": Calendar(7 * 3600, 11.5 * 3600),
    "usg": Calendar(7 * 3600, 11.5 * 3600),
    "urine": Calendar(86400, 86400),
    "ntx": Calendar(7 * 86400, 7 * 86400),
    # Local sweat has no resting acquisition, so these replay the daily active
    # and wet bout (roughly 16.8h to 18.6h). The summary's windows overlap at
    # this step; a demo trend is not a sequence of disjoint 60s integrations.
    "sweat": Calendar(17 * 3600, 40, samples=145),
    "sweat_summary": Calendar(17 * 3600, 40, samples=145),
}
