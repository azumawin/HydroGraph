"""Sensor channels: what a single reading is, and how it is graded on its own.

A channel is one value the device sends (``"spo2"``, ``"heart_rate"``, ...).
:data:`CHANNELS` describes each one for display; :func:`evaluate_reading`
grades one value. Thresholds come from the master plan's Tier 1 cutoffs where
it gives one for that vital, otherwise from ``NSA_hydrograph.md``. A value on a
side neither document addresses is ``Status.UNSPECIFIED``.

The 10 findings in :mod:`hydrograph_core.findings` combine several channels;
this module grades each channel alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, TypedDict

from .shared import Status


class ChannelInfo(TypedDict):
    name: str
    unit: str
    body_regions: tuple[str, ...]
    explanation: str


CHANNELS: Final[Mapping[str, ChannelInfo]] = MappingProxyType(
    {
        "heart_rate": {
            "name": "Heart rate",
            "unit": "bpm",
            "body_regions": ("heart",),
            "explanation": (
                "Resting heart rate above 90 bpm signals vascular stress, "
                "dehydration or infection."
            ),
        },
        "bp_systolic": {
            "name": "Blood pressure (systolic)",
            "unit": "mmHg",
            "body_regions": ("heart", "chest"),
            "explanation": (
                "A systolic drop of 20 mmHg or more on standing marks orthostatic "
                "intolerance after time in reduced gravity."
            ),
        },
        "bp_diastolic": {
            "name": "Blood pressure (diastolic)",
            "unit": "mmHg",
            "body_regions": ("heart", "chest"),
            "explanation": (
                "A diastolic drop of 10 mmHg or more on standing marks orthostatic "
                "intolerance after time in reduced gravity."
            ),
        },
        "spo2": {
            "name": "Blood oxygen saturation",
            "unit": "%",
            "body_regions": ("lungs",),
            "explanation": (
                "Below 94 % is low and below 90 % is critical hypoxemia; check the "
                "CO2 scrubber and module ventilation."
            ),
        },
        "core_temp": {
            "name": "Core body temperature",
            "unit": "°C",
            "body_regions": ("head", "torso"),
            "explanation": (
                "Above 38.0 °C or below 36.0 °C meets the SIRS fever or "
                "hypothermia criterion for acute infection."
            ),
        },
        "glucose": {
            "name": "Blood glucose",
            "unit": "mmol/L",
            "body_regions": ("blood",),
            "explanation": (
                "Below 3.9 mmol/L is level 1 hypoglycemia and below 3.0 mmol/L "
                "level 2; a sign of negative energy balance."
            ),
        },
        "ppco2": {
            "name": "Cabin CO2 partial pressure",
            "unit": "mmHg",
            "body_regions": ("lungs",),
            "explanation": (
                "Above 3.0 mmHg (about 4,000 ppm) causes headaches and impairs "
                "performance in closed habitats."
            ),
        },
        "dose_rate": {
            "name": "Radiation dose rate",
            "unit": "µSv/h",
            "body_regions": ("whole_body",),
            "explanation": (
                "A spike above 50 µSv/h can mean a solar particle event; move to "
                "the shielded storm shelter."
            ),
        },
        "jugular_distension": {
            "name": "Jugular distension",
            "unit": "%",
            "body_regions": ("neck", "head", "eyes"),
            "explanation": (
                "Neck-vein distension above 1.1 % of baseline signals the cephalic "
                "fluid shift behind spaceflight-associated neuro-ocular syndrome."
            ),
        },
    }
)


def evaluate_reading(channel: str, value: float) -> Status:
    """Grade one reading of one channel on its own.

    Args:
        channel: A key of :data:`CHANNELS`.
        value: The reading, in the channel's ``unit``.

    Returns:
        The reading's status. Sources and boundary choices are commented per
        channel.

    Raises:
        ValueError: ``channel`` is not in :data:`CHANNELS`.
    """
    match channel:
        case "heart_rate":
            # NSA 1.3: nominal 50-90 bpm, warning 100-120; 90-100 and > 120
            # take the nearest defined band (warning). Below 50 not addressed.
            if value < 50.0:
                return Status.UNSPECIFIED
            if value <= 90.0:
                return Status.NOMINAL
            return Status.WARNING
        case "bp_systolic" | "bp_diastolic":
            # Neither document grades a single systolic or diastolic reading;
            # they only feed Finding 1 (postural drop) and NSA 1.3 (MAP).
            return Status.UNSPECIFIED
        case "spo2":
            # Master plan Finding 4: < 94 % warning, < 90 % critical hypoxemia.
            if value < 90.0:
                return Status.CRITICAL
            if value < 94.0:
                return Status.WARNING
            return Status.NOMINAL
        case "core_temp":
            # Master plan Finding 3 (SIRS): > 38.0 or < 36.0 degC.
            if value > 38.0 or value < 36.0:
                return Status.WARNING
            return Status.NOMINAL
        case "glucose":
            # Master plan Finding 7: Level 1 < 3.9 mM (70 mg/dL), Level 2
            # < 3.0 mM (54 mg/dL), critical as NSA 2.1 grades its lowest band.
            # NSA 2.1 nominal tops out at 7.0 mM; hyperglycemia not addressed.
            if value < 3.0:
                return Status.CRITICAL
            if value < 3.9:
                return Status.WARNING
            if value <= 7.0:
                return Status.NOMINAL
            return Status.UNSPECIFIED
        case "ppco2":
            # Master plan Finding 4: ppCO2 > 3.0 mmHg.
            return Status.WARNING if value > 3.0 else Status.NOMINAL
        case "dose_rate":
            # Master plan Finding 10: dose-rate spike > 50 uSv/h warning.
            return Status.WARNING if value > 50.0 else Status.NOMINAL
        case "jugular_distension":
            # Master plan Finding 9: 1.1-1.8 % warning, > 1.8 % critical.
            if value > 1.8:
                return Status.CRITICAL
            if value >= 1.1:
                return Status.WARNING
            return Status.NOMINAL
        case _:
            raise ValueError(f'Unknown channel "{channel}".')
