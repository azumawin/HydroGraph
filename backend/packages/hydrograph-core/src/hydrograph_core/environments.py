"""Mission environments the dashboard can switch between.

Four environments cover the two axes that matter without redundancy: gravity
at 0, 0.166 and 0.377 g, and round-trip comm delay from 1.2 s to 26 min.
``iss_leo`` is 0 g with the ground always available and the magnetosphere
overhead; ``mars_transit`` is the worst case, 0 g with full autonomy and
unshielded GCR; the two surfaces hold the partial-gravity points.

Mostly display and simulation metadata: switching one changes what the
dashboard shows and what telemetry a simulator generates. The one exception is
radiation: the dose rate is graded as a spike above the environment's
``baseline_dose_rate_usv_h`` (``evaluate_reading`` and Finding 10), because the
lunar and Mars-transit backgrounds already exceed the plan's absolute 50 uSv/h.

``comm_delay_rt_s`` is **round trip** - the delay that decides whether the
crew can ask the ground at all. It is really a range (Mars is 364-2684 s
round trip); each value here is one representative number for the demo.

``baseline_dose_rate_usv_h`` is the measured nominal GCR dose-equivalent rate
with the crew inside the habitat or vehicle, in the unit Finding 10 compares
against. Note that the lunar surface and Mars transit baselines are already
above the plan's absolute 50 uSv/h warning cutoff, which is why that cutoff is
applied above the baseline instead.

``storm_shelter_available`` is whether "move to the shielded storm shelter",
Finding 10's action card, is a thing the crew can actually do. True for all
four, which are habitat and vehicle interiors; an EVA or surface sortie
environment would be the first False.

``day_length_h`` is the natural light-dark cycle Finding 5's circadian
premise rests on, and what a simulator would use to drive circadian drift. In
transit there is no natural cycle, so it is the crew's 24 h schedule.

References:
    Shavers, M., Semones, E., Tomi, L. et al. (2023). Space agency-specific
        standards for crew dose and risk assessment of ionising radiation
        exposures for the International Space Station. Zeitschrift fuer
        Medizinische Physik. https://doi.org/10.1016/j.zemedi.2023.06.005
        (ISS effective dose 0.2-0.5 mSv/day; 0.35 mSv/day used here.)

    Zhang, S. et al. (2020). First measurements of the radiation dose on the
        lunar surface. Science Advances, 6(39), eaaz1334.
        (Chang'e-4 LND: 1.369 mSv/day, 57.1 +/- 10.6 uSv/h charged particles.)

    Hassler, D. M. et al. (2014). Mars' surface radiation environment measured
        with the Mars Science Laboratory's Curiosity rover. Science, 343(6169),
        1244797. (RAD: 0.64 +/- 0.12 mSv/day on the surface, 1.84 +/- 0.3
        mSv/day during cruise.)
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, TypedDict


class EnvironmentInfo(TypedDict):
    name: str
    gravity_g: float
    comm_delay_rt_s: float
    baseline_dose_rate_usv_h: float
    storm_shelter_available: bool
    day_length_h: float


ENVIRONMENTS: Final[Mapping[str, EnvironmentInfo]] = MappingProxyType(
    {
        "iss_leo": {
            "name": "ISS, low Earth orbit",
            "gravity_g": 0.0,
            # Crew to ground and back through a geostationary relay.
            "comm_delay_rt_s": 1.2,
            "baseline_dose_rate_usv_h": 14.6,  # 0.35 mSv/day
            "storm_shelter_available": True,
            "day_length_h": 1.52,  # ~91 min orbit, the plan's 16 sunrises a day
        },
        "lunar_surface": {
            "name": "Lunar surface",
            "gravity_g": 0.166,
            "comm_delay_rt_s": 2.6,  # 384 400 km each way
            "baseline_dose_rate_usv_h": 57.1,
            "storm_shelter_available": True,
            "day_length_h": 708.7,  # synodic day, 29.53 Earth days
        },
        "mars_transit": {
            "name": "Mars transit",
            "gravity_g": 0.0,
            "comm_delay_rt_s": 1560.0,  # 26 min, mid-range for the cruise
            "baseline_dose_rate_usv_h": 76.7,  # 1.84 mSv/day
            "storm_shelter_available": True,
            "day_length_h": 24.0,  # no natural cycle: the crew's own schedule
        },
        "mars_surface": {
            "name": "Mars surface",
            "gravity_g": 0.377,
            "comm_delay_rt_s": 1560.0,  # 26 min, mid-range Earth-Mars
            "baseline_dose_rate_usv_h": 26.7,  # 0.64 mSv/day
            "storm_shelter_available": True,
            "day_length_h": 24.66,  # one sol, 24 h 39 min
        },
    }
)

DEFAULT_ENVIRONMENT: Final = "iss_leo"
"""The environment in effect until one is selected."""
