"""SANS & cephalic fluid shift."""

from __future__ import annotations

from core.findings import sans_fluid_shift_1_3
from core.rule import FindingResult, RuleInputs

ID = "sans_fluid_shift_1_3"
NAME = "SANS & cephalic fluid shift"
CHANNELS = ("jugular_strain_pct",)


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    # Fractional strain -> %, rounded so float noise cannot move a band
    # boundary (0.011 * 100 = 1.0999...).
    return sans_fluid_shift_1_3(
        round(float(inputs["latest"]["jugular_strain_pct"]) * 100.0, 9)
    )
