"""Catalog of sensor channels the backend accepts, and of demo environments.

Each channel's thresholds come from the master plan's Tier 1 cutoffs where it
gives one for that vital, otherwise from ``NSA_hydrograph.md`` (both in
``packages/hydrograph-core/``). A value on a side neither document addresses
is ``Status.UNSPECIFIED``, as in ``hydrograph_core``.
"""

from collections.abc import Callable
from dataclasses import dataclass

from hydrograph_core import Status


@dataclass(frozen=True)
class Channel:
    name: str
    unit: str
    body_regions: tuple[str, ...]
    explanation: str
    evaluate: Callable[[float], Status]


def _heart_rate(bpm: float) -> Status:
    # NSA 1.3: nominal 50-90, warning 100-120; 90-100 and > 120 take the
    # nearest defined band (warning). Below 50 is not addressed.
    if bpm < 50.0:
        return Status.UNSPECIFIED
    if bpm <= 90.0:
        return Status.NOMINAL
    return Status.WARNING


def _blood_pressure(_mmhg: float) -> Status:
    # Neither document grades a single systolic or diastolic reading; they
    # only feed Finding 1 (postural drop) and NSA 1.3 (MAP).
    return Status.UNSPECIFIED


def _spo2(pct: float) -> Status:
    # Master plan Finding 4: < 94 % warning, < 90 % critical hypoxemia.
    if pct < 90.0:
        return Status.CRITICAL
    if pct < 94.0:
        return Status.WARNING
    return Status.NOMINAL


def _core_temp(celsius: float) -> Status:
    # Master plan Finding 3 (SIRS): > 38.0 or < 36.0 degC.
    if celsius > 38.0 or celsius < 36.0:
        return Status.WARNING
    return Status.NOMINAL


def _glucose(mmol_l: float) -> Status:
    # Master plan Finding 7: Level 1 < 3.9 mM (70 mg/dL), Level 2 < 3.0 mM
    # (54 mg/dL), graded critical as NSA 2.1 does for its lowest band.
    # NSA 2.1 nominal tops out at 7.0 mM; hyperglycemia is not addressed.
    if mmol_l < 3.0:
        return Status.CRITICAL
    if mmol_l < 3.9:
        return Status.WARNING
    if mmol_l <= 7.0:
        return Status.NOMINAL
    return Status.UNSPECIFIED


def _ppco2(mmhg: float) -> Status:
    # Master plan Finding 4: ppCO2 > 3.0 mmHg.
    return Status.WARNING if mmhg > 3.0 else Status.NOMINAL


def _dose_rate(usv_h: float) -> Status:
    # Master plan Finding 10: dose-rate spike > 50 uSv/h warning.
    return Status.WARNING if usv_h > 50.0 else Status.NOMINAL


def _jugular_distension(pct: float) -> Status:
    # Master plan Finding 9: 1.1-1.8 % warning, > 1.8 % critical.
    if pct > 1.8:
        return Status.CRITICAL
    if pct >= 1.1:
        return Status.WARNING
    return Status.NOMINAL


CHANNELS: dict[str, Channel] = {
    "heart_rate": Channel(
        name="Heart rate",
        unit="bpm",
        body_regions=("heart",),
        explanation=(
            "Resting heart rate above 90 bpm signals vascular stress, "
            "dehydration or infection."
        ),
        evaluate=_heart_rate,
    ),
    "bp_systolic": Channel(
        name="Blood pressure (systolic)",
        unit="mmHg",
        body_regions=("heart", "chest"),
        explanation=(
            "A systolic drop of 20 mmHg or more on standing marks orthostatic "
            "intolerance after time in reduced gravity."
        ),
        evaluate=_blood_pressure,
    ),
    "bp_diastolic": Channel(
        name="Blood pressure (diastolic)",
        unit="mmHg",
        body_regions=("heart", "chest"),
        explanation=(
            "A diastolic drop of 10 mmHg or more on standing marks orthostatic "
            "intolerance after time in reduced gravity."
        ),
        evaluate=_blood_pressure,
    ),
    "spo2": Channel(
        name="Blood oxygen saturation",
        unit="%",
        body_regions=("lungs",),
        explanation=(
            "Below 94 % is low and below 90 % is critical hypoxemia; check the "
            "CO2 scrubber and module ventilation."
        ),
        evaluate=_spo2,
    ),
    "core_temp": Channel(
        name="Core body temperature",
        unit="°C",
        body_regions=("head", "torso"),
        explanation=(
            "Above 38.0 °C or below 36.0 °C meets the SIRS fever or "
            "hypothermia criterion for acute infection."
        ),
        evaluate=_core_temp,
    ),
    "glucose": Channel(
        name="Blood glucose",
        unit="mmol/L",
        body_regions=("blood",),
        explanation=(
            "Below 3.9 mmol/L is level 1 hypoglycemia and below 3.0 mmol/L "
            "level 2; a sign of negative energy balance."
        ),
        evaluate=_glucose,
    ),
    "ppco2": Channel(
        name="Cabin CO2 partial pressure",
        unit="mmHg",
        body_regions=("lungs",),
        explanation=(
            "Above 3.0 mmHg (about 4,000 ppm) causes headaches and impairs "
            "performance in closed habitats."
        ),
        evaluate=_ppco2,
    ),
    "dose_rate": Channel(
        name="Radiation dose rate",
        unit="µSv/h",
        body_regions=("whole_body",),
        explanation=(
            "A spike above 50 µSv/h can mean a solar particle event; move to "
            "the shielded storm shelter."
        ),
        evaluate=_dose_rate,
    ),
    "jugular_distension": Channel(
        name="Jugular distension",
        unit="%",
        body_regions=("neck", "head", "eyes"),
        explanation=(
            "Neck-vein distension above 1.1 % of baseline signals the cephalic "
            "fluid shift behind spaceflight-associated neuro-ocular syndrome."
        ),
        evaluate=_jugular_distension,
    ),
}


@dataclass(frozen=True)
class Environment:
    gravity_g: float
    comm_delay_s: float


# Values from docs/json-shape.md; the Earth communication delay is really a
# range, simplified to a single number for the demo.
ENVIRONMENTS: dict[str, Environment] = {
    "lunar_surface": Environment(gravity_g=0.166, comm_delay_s=2.6),
    "mars_surface": Environment(gravity_g=0.377, comm_delay_s=600.0),
}
