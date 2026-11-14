"""Tier 1 findings from the latest channel readings.

:mod:`core.findings` takes spec-unit arguments; the device sends SI
channel readings (:mod:`core.channels`). This module bridges the
two for one crew member: :func:`evaluate_findings` converts the latest
readings and calls every finding whose inputs the simulator provides.

Seven of the ten findings are monitored. :data:`FINDINGS` lists all ten; an
empty ``channels`` tuple marks one whose inputs the simulator does not send
(postural BP, sleep, PHQ-9/GAD-7, EEG/PVT).

Context a single reading cannot carry, assumed here:

- NEWS2 uses explicit oxygen and ACVPU context when present, otherwise
  assumes room air and alertness with per-field provenance.
- Finding 3 uses explicit post-ARED context when supplied, otherwise False.
- Finding 4's "rising respiratory rate" has no definition and headache is not
  reported, so both are passed as False.
- Finding 7's resting lactate is the latest lactate reading.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, TypedDict

from .environments import EnvironmentInfo
from .findings import (
    BoneResult,
    DehydrationResult,
    EnergyBalanceResult,
    HypoxiaResult,
    InfectionResult,
    RadiationResult,
    SansResult,
    acute_infection_3_1,
    bone_demineralization_1_2,
    dehydration_2_1,
    hypoxia_co2_2_2,
    negative_energy_balance_2_3,
    radiation_exposure_3_2,
    sans_fluid_shift_1_3,
)


class FindingInfo(TypedDict):
    name: str
    channels: tuple[str, ...]


FINDINGS: Final[Mapping[str, FindingInfo]] = MappingProxyType(
    {
        "orthostatic_intolerance_1_1": {
            "name": "Orthostatic intolerance & CV deconditioning",
            "channels": (),
        },
        "bone_demineralization_1_2": {
            "name": "Bone demineralization & renal stone risk",
            "channels": ("bone_ntx_pct_baseline", "urine_volume_24h"),
        },
        "sans_fluid_shift_1_3": {
            "name": "SANS & cephalic fluid shift",
            "channels": ("jugular_strain_pct",),
        },
        "dehydration_2_1": {
            "name": "Dehydration & electrolyte loss",
            "channels": ("body_mass", "urine_specific_gravity"),
        },
        "hypoxia_co2_2_2": {
            "name": "Hypoxia & CO2 exposure",
            "channels": ("spo2", "ambient_ppco2"),
        },
        "negative_energy_balance_2_3": {
            "name": "Negative energy balance & nutrition",
            "channels": ("body_mass", "glucose", "lactate"),
        },
        "acute_infection_3_1": {
            "name": "Acute infection & immune dysregulation",
            "channels": (
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
            ),
        },
        "radiation_exposure_3_2": {
            "name": "Radiation dose & solar particle events",
            "channels": ("ambient_integrated_dose", "ambient_dose_rate", "spe_flag"),
        },
        "sleep_deficiency_4_1": {
            "name": "Sleep deficiency & circadian fatigue",
            "channels": (),
        },
        "behavioral_health_decline_4_2": {
            "name": "Behavioral health & HPA-axis decline",
            "channels": (),
        },
    }
)

type FindingResult = (
    BoneResult
    | DehydrationResult
    | HypoxiaResult
    | EnergyBalanceResult
    | InfectionResult
    | RadiationResult
    | SansResult
)


class News2Result(TypedDict):
    components: dict[str, int]
    score: int
    max_parameter_score: int


def news2(
    respiratory_rate_min: float,
    spo2_pct: float,
    sbp_mmhg: float,
    heart_rate_bpm: float,
    temp_c: float,
    *,
    consciousness_level: str = "ALERT",
    supplemental_o2: bool = False,
) -> News2Result:
    """
    National Early Warning Score 2, SpO2 scale 1, room air, alert patient.

    References:
        Royal College of Physicians. (2017). National Early Warning Score
        (NEWS) 2: Standardising the assessment of acute-illness severity in
        the NHS. London: RCP.

    Args:
        respiratory_rate_min: Respiratory rate [breaths/min].
        spo2_pct: Peripheral oxygen saturation [%].
        sbp_mmhg: Systolic blood pressure [mmHg].
        heart_rate_bpm: Pulse [BPM].
        temp_c: Temperature [°C].

    Returns:
        ``score`` (0-20) and ``max_parameter_score`` (0-3). Air/oxygen and
        consciousness score 0 by assumption. The chart bands whole numbers
        (0.1 °C for temperature), so values are rounded before banding.
    """
    rr = round(respiratory_rate_min)
    spo2 = round(spo2_pct)
    sbp = round(sbp_mmhg)
    hr = round(heart_rate_bpm)
    temp = round(temp_c, 1)

    if rr <= 8:
        rr_score = 3
    elif rr <= 11:
        rr_score = 1
    elif rr <= 20:
        rr_score = 0
    elif rr <= 24:
        rr_score = 2
    else:
        rr_score = 3

    if spo2 <= 91:
        spo2_score = 3
    elif spo2 <= 93:
        spo2_score = 2
    elif spo2 <= 95:
        spo2_score = 1
    else:
        spo2_score = 0

    if sbp <= 90 or sbp >= 220:
        sbp_score = 3
    elif sbp <= 100:
        sbp_score = 2
    elif sbp <= 110:
        sbp_score = 1
    else:
        sbp_score = 0

    if hr <= 40 or hr >= 131:
        hr_score = 3
    elif hr <= 50:
        hr_score = 1
    elif hr <= 90:
        hr_score = 0
    elif hr <= 110:
        hr_score = 1
    else:
        hr_score = 2

    if temp <= 35.0:
        temp_score = 3
    elif temp <= 36.0:
        temp_score = 1
    elif temp <= 38.0:
        temp_score = 0
    elif temp <= 39.0:
        temp_score = 1
    else:
        temp_score = 2

    if consciousness_level not in (
        "ALERT",
        "CONFUSION",
        "VOICE",
        "PAIN",
        "UNRESPONSIVE",
    ):
        raise ValueError("invalid ACVPU state")
    scores = (
        rr_score,
        spo2_score,
        sbp_score,
        hr_score,
        temp_score,
        2 if supplemental_o2 else 0,
        0 if consciousness_level == "ALERT" else 3,
    )
    return {
        "score": sum(scores),
        "max_parameter_score": max(scores),
        "components": dict(
            zip(
                (
                    "respiration",
                    "spo2",
                    "systolic",
                    "heart_rate",
                    "temperature",
                    "oxygen",
                    "consciousness",
                ),
                scores,
            )
        ),
    }


def evaluate_findings(
    latest: Mapping[str, float | bool | str],
    body_mass_first_kg: float | None,
    body_mass_week_before_kg: float | None,
    environment: EnvironmentInfo,
) -> dict[str, FindingResult]:
    """Every monitored finding whose input channels all have a reading.

    Args:
        latest: Latest reading per channel for one crew member, in SI wire
            units, plus the latest cabin (environment) readings.
        body_mass_first_kg: The crew member's earliest body mass, the mission
            baseline for Finding 2.
        body_mass_week_before_kg: Their latest body mass taken at least 7 days
            before the latest one, for Finding 7's weekly loss; ``None`` in the
            first week, when the loss since the baseline is used instead (not
            extrapolated to a weekly rate).
        environment: The mission environment in effect; Finding 10 grades the
            dose rate above its baseline.

    Returns:
        Finding id (a key of :data:`FINDINGS`) to its result. Findings with a
        missing input are left out.
    """

    def has(finding: str) -> bool:
        required = (
            (
                "respiratory_rate",
                "spo2",
                "bp_systolic",
                "heart_rate",
                "body_temperature",
            )
            if finding == "acute_infection_3_1"
            else FINDINGS[finding]["channels"]
        )
        return all(c in latest for c in required)

    def num(channel: str) -> float:
        return float(latest[channel])

    results: dict[str, FindingResult] = {}

    if has("bone_demineralization_1_2"):
        # Fractional NTx change -> %; m^3 -> L.
        results["bone_demineralization_1_2"] = bone_demineralization_1_2(
            num("bone_ntx_pct_baseline") * 100.0,
            num("urine_volume_24h") * 1000.0,
        )

    if has("sans_fluid_shift_1_3"):
        # Fractional strain -> %, rounded so float noise cannot move a band
        # boundary (0.011 * 100 = 1.0999...).
        results["sans_fluid_shift_1_3"] = sans_fluid_shift_1_3(
            round(num("jugular_strain_pct") * 100.0, 9)
        )

    if has("dehydration_2_1") and body_mass_first_kg is not None:
        results["dehydration_2_1"] = dehydration_2_1(
            num("body_mass"), body_mass_first_kg, num("urine_specific_gravity")
        )

    if has("hypoxia_co2_2_2"):
        # Fraction -> %; Pa -> mmHg. Rising RR and headache: see module doc.
        results["hypoxia_co2_2_2"] = hypoxia_co2_2_2(
            num("spo2") * 100.0, False, num("ambient_ppco2") / 133.322, False
        )

    if has("negative_energy_balance_2_3") and body_mass_first_kg is not None:
        reference = (
            body_mass_week_before_kg
            if body_mass_week_before_kg is not None
            else body_mass_first_kg
        )
        loss_pct = (reference - num("body_mass")) / reference * 100.0
        # mol/m^3 equals mmol/L.
        results["negative_energy_balance_2_3"] = negative_energy_balance_2_3(
            loss_pct, num("glucose"), num("lactate")
        )

    if has("acute_infection_3_1"):
        temp_c = num("body_temperature") - 273.15
        score = news2(
            num("respiratory_rate") * 60.0,
            num("spo2") * 100.0,
            num("bp_systolic") / 133.322,
            num("heart_rate") * 60.0,
            temp_c,
            consciousness_level=str(latest.get("consciousness_level", "ALERT")),
            supplemental_o2=latest.get("supplemental_o2", False) is True,
        )
        viral = ("viral_ebv_detected", "viral_vzv_detected", "viral_cmv_detected")
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
            any(latest.get(c) is True for c in viral),
        )
        result["qsofa_score"] = qsofa(
            num("respiratory_rate") * 60,
            num("bp_systolic") / 133.322,
            str(latest.get("consciousness_level", "ALERT")),
        )
        result["news2_components"] = score["components"]
        result["il6_source_channel"] = source
        result["context_values"] = {
            c: latest.get(c, "ALERT" if c == "consciousness_level" else False)
            for c in (
                "consciousness_level",
                "supplemental_o2",
                "post_ared_exercise_window",
            )
        }
        result["context_provenance"] = {
            c: "explicit" if c in latest else "assumed"
            for c in (
                "consciousness_level",
                "supplemental_o2",
                "post_ared_exercise_window",
            )
        }
        result["unavailable_assays"] = [
            c for c in (*viral, "il6_serum", "il6_pg_mL") if c not in latest
        ]
        results["acute_infection_3_1"] = result

    if has("radiation_exposure_3_2"):
        # Sv -> mSv; Sv/s -> uSv/h.
        results["radiation_exposure_3_2"] = radiation_exposure_3_2(
            num("ambient_integrated_dose") * 1000.0,
            num("ambient_dose_rate") * 3.6e9,
            latest["spe_flag"] is True,
            environment["baseline_dose_rate_usv_h"],
        )

    return results


def qsofa(
    respiratory_rate_min: float, sbp_mmhg: float, consciousness_level: str = "ALERT"
) -> int:
    """ACVPU adaptation: any non-ALERT state is altered consciousness."""
    if consciousness_level not in (
        "ALERT",
        "CONFUSION",
        "VOICE",
        "PAIN",
        "UNRESPONSIVE",
    ):
        raise ValueError("invalid ACVPU state")
    return (
        int(respiratory_rate_min >= 22)
        + int(sbp_mmhg <= 100)
        + int(consciousness_level != "ALERT")
    )
