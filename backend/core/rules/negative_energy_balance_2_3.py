"""Negative energy balance & nutrition.

The weekly loss uses the latest body mass at least 7 days before the latest
one; in the first week, the loss since the mission baseline instead (not
extrapolated to a weekly rate). Resting lactate is the latest lactate reading.
"""

from __future__ import annotations

from core.findings import negative_energy_balance_2_3
from core.rule import FindingResult, RuleInputs

ID = "negative_energy_balance_2_3"
NAME = "Negative energy balance & nutrition"
CHANNELS = ("body_mass", "glucose", "lactate")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    baseline = inputs["body_mass_first_kg"]
    if baseline is None:
        return None
    week_before = inputs["body_mass_week_before_kg"]
    reference = week_before if week_before is not None else baseline
    latest = inputs["latest"]
    loss_pct = (reference - float(latest["body_mass"])) / reference * 100.0
    # mol/m^3 equals mmol/L.
    return negative_energy_balance_2_3(
        loss_pct, float(latest["glucose"]), float(latest["lactate"])
    )
