"""Dehydration & electrolyte loss."""

from __future__ import annotations

from core.findings import dehydration_2_1
from core.rule import FindingResult, RuleInputs

ID = "dehydration_2_1"
NAME = "Dehydration & electrolyte loss"
CHANNELS = ("body_mass", "urine_specific_gravity")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    baseline = inputs["body_mass_first_kg"]
    if baseline is None:
        return None
    latest = inputs["latest"]
    return dehydration_2_1(
        float(latest["body_mass"]), baseline, float(latest["urine_specific_gravity"])
    )
