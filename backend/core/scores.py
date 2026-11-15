"""Clinical early-warning scores the findings build on."""

from __future__ import annotations

from typing import TypedDict


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
