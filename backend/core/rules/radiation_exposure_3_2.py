"""Radiation dose & solar particle events, graded against the environment."""

from __future__ import annotations

from core.findings import radiation_exposure_3_2
from core.rule import FindingResult, RuleInputs

ID = "radiation_exposure_3_2"
NAME = "Radiation dose & solar particle events"
CHANNELS = ("ambient_integrated_dose", "ambient_dose_rate", "spe_flag")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    latest = inputs["latest"]
    # Sv -> mSv; Sv/s -> uSv/h.
    return radiation_exposure_3_2(
        float(latest["ambient_integrated_dose"]) * 1000.0,
        float(latest["ambient_dose_rate"]) * 3.6e9,
        latest["spe_flag"] is True,
        inputs["environment"]["baseline_dose_rate_usv_h"],
    )
