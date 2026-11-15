"""Hypoxia & CO2 exposure.

Finding 4's "rising respiratory rate" has no definition and headache is not
reported, so both are passed as False.
"""

from __future__ import annotations

from core.findings import hypoxia_co2_2_2
from core.rule import FindingResult, RuleInputs

ID = "hypoxia_co2_2_2"
NAME = "Hypoxia & CO2 exposure"
CHANNELS = ("spo2", "ambient_ppco2")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    latest = inputs["latest"]
    # Fraction -> %; Pa -> mmHg.
    return hypoxia_co2_2_2(
        float(latest["spo2"]) * 100.0,
        False,
        float(latest["ambient_ppco2"]) / 133.322,
        False,
    )
