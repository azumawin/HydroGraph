"""Bone demineralization & renal stone risk."""

from __future__ import annotations

from core.findings import bone_demineralization_1_2
from core.rule import FindingResult, RuleInputs

ID = "bone_demineralization_1_2"
NAME = "Bone demineralization & renal stone risk"
CHANNELS = ("bone_ntx_pct_baseline", "urine_volume_24h")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    latest = inputs["latest"]
    # Fractional NTx change -> %; m^3 -> L.
    return bone_demineralization_1_2(
        float(latest["bone_ntx_pct_baseline"]) * 100.0,
        float(latest["urine_volume_24h"]) * 1000.0,
    )
