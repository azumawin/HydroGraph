"""Acute infection & immune dysregulation.

NEWS2 uses explicit oxygen and ACVPU context when present, otherwise assumes
room air and alertness with per-field provenance. Post-ARED context defaults
to False.
"""

from __future__ import annotations

from core.findings import acute_infection_3_1
from core.rule import FindingResult, RuleInputs
from core.scores import news2, qsofa

ID = "acute_infection_3_1"
NAME = "Acute infection & immune dysregulation"
CHANNELS = (
    "respiratory_rate",
    "spo2",
    "bp_systolic",
    "heart_rate",
    "body_temperature",
    "consciousness_level",
    "supplemental_o2",
    "post_ared_exercise_window",
    "il6_pg_mL",
    "il6_serum",
    "viral_ebv_detected",
    "viral_vzv_detected",
    "viral_cmv_detected",
)
REQUIRED = (
    "respiratory_rate",
    "spo2",
    "bp_systolic",
    "heart_rate",
    "body_temperature",
)
CONTEXT = ("consciousness_level", "supplemental_o2", "post_ared_exercise_window")
VIRAL = ("viral_ebv_detected", "viral_vzv_detected", "viral_cmv_detected")


def evaluate(inputs: RuleInputs) -> FindingResult | None:
    latest = inputs["latest"]

    def num(channel: str) -> float:
        return float(latest[channel])

    temp_c = num("body_temperature") - 273.15
    consciousness = str(latest.get("consciousness_level", "ALERT"))
    score = news2(
        num("respiratory_rate") * 60.0,
        num("spo2") * 100.0,
        num("bp_systolic") / 133.322,
        num("heart_rate") * 60.0,
        temp_c,
        consciousness_level=consciousness,
        supplemental_o2=latest.get("supplemental_o2", False) is True,
    )
    source = (
        "il6_pg_mL"
        if "il6_pg_mL" in latest
        else "il6_serum" if "il6_serum" in latest else None
    )
    il6 = num(source) * 1e9 if source else None
    result = acute_infection_3_1(
        score["score"],
        score["max_parameter_score"],
        temp_c,
        il6,
        latest.get("post_ared_exercise_window", False) is True,
        any(latest.get(channel) is True for channel in VIRAL),
    )
    result["qsofa_score"] = qsofa(
        num("respiratory_rate") * 60, num("bp_systolic") / 133.322, consciousness
    )
    result["news2_components"] = score["components"]
    result["il6_source_channel"] = source
    result["context_values"] = {
        channel: latest.get(
            channel, "ALERT" if channel == "consciousness_level" else False
        )
        for channel in CONTEXT
    }
    result["context_provenance"] = {
        channel: "explicit" if channel in latest else "assumed" for channel in CONTEXT
    }
    result["unavailable_assays"] = [
        channel
        for channel in (*VIRAL, "il6_serum", "il6_pg_mL")
        if channel not in latest
    ]
    return result
