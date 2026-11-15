"""Blood pressure & hemodynamic stability (supplementary telemetry evaluator).

Heart rate updates the shock index, but pressure is assessed as soon as both
pressures have a reading.
"""

from __future__ import annotations

from core.findings import blood_pressure_1_4
from core.rule import FindingResult, RuleInputs

ID = "blood_pressure_1_4"
NAME = "Blood pressure & hemodynamic stability"
CHANNELS = ("bp_systolic", "bp_diastolic", "heart_rate")
REQUIRED = ("bp_systolic", "bp_diastolic")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    latest = inputs["latest"]
    # Pa -> mmHg; s^-1 -> bpm. Avoid SI round-trip noise at exact cutoffs.
    sbp = round(float(latest["bp_systolic"]) / 133.322, 9)
    dbp = round(float(latest["bp_diastolic"]) / 133.322, 9)
    hr = float(latest["heart_rate"]) * 60 if "heart_rate" in latest else None
    try:
        return blood_pressure_1_4(sbp, dbp, hr)
    except ValueError as error:
        # Paired channels arrive in separate requests; an invalid or
        # temporarily inconsistent pair must not break ingestion or SSE.
        return {
            "sbp_mmhg": sbp,
            "dbp_mmhg": dbp,
            "sensor_error": str(error),
            "triggers": [str(error)],
            "status": "warning",
            "action": "Check the blood pressure sensor and repeat the paired measurement",
        }
