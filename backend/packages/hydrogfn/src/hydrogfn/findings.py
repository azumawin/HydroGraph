"""Tier 1: the 10 personal health findings (master plan, section 2).

Each function evaluates one finding for the main window and returns its
immediate action card. Criteria the master plan quantifies are computed here.
Criteria it names without a cutoff are either keyword-only arguments the
caller must supply (numeric) or booleans evaluated upstream (qualitative).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from .shared import Status


class OrthostaticResult(TypedDict):
    finding: str
    delta_sbp_mmhg: float
    hr_rise_bpm: float
    shock_index: float
    triggers: list[str]
    status: Status
    action: str


class DehydrationResult(TypedDict):
    finding: str
    body_mass_loss_pct: float
    urine_specific_gravity: float
    triggers: list[str]
    status: Status
    action: str


class InfectionResult(TypedDict):
    finding: str
    news2_score: int
    qsofa_score: int
    triggers: list[str]
    status: Status
    action: str


class HypoxiaResult(TypedDict):
    finding: str
    spo2_pct: float
    respiratory_rate_bpm: float
    ppco2_mmhg: float
    triggers: list[str]
    status: Status
    action: str


class SleepResult(TypedDict):
    finding: str
    sleep_hours: float
    sleep_efficiency_pct: float
    light_exposure_lux: float
    pvt_lapses: int
    triggers: list[str]
    status: Status
    action: str


class BehavioralResult(TypedDict):
    finding: str
    phq9_score: int
    gad7_score: int
    pvt_lapses: int
    sleep_debt_hours: float
    triggers: list[str]
    status: Status
    action: str


class EnergyBalanceResult(TypedDict):
    finding: str
    body_mass_slope_kg_week: float
    glucose_mg_dl: float
    triggers: list[str]
    status: Status
    action: str


class BoneResult(TypedDict):
    finding: str
    ntx_change_pct: float
    urine_volume_l_day: float
    triggers: list[str]
    status: Status
    action: str


class SansResult(TypedDict):
    finding: str
    fluid_shift_index: float
    triggers: list[str]
    status: Status
    action: str


class RadiationResult(TypedDict):
    finding: str
    cumulative_dose_msv: float
    dose_rate_usv_h: float
    triggers: list[str]
    status: Status
    action: str


def orthostatic_intolerance_1(
    sbp_supine_mmhg: float,
    sbp_standing_mmhg: float,
    hr_supine_bpm: float,
    hr_standing_bpm: float,
) -> OrthostaticResult:
    r"""
    Finding 1: Orthostatic intolerance & CV deconditioning (gravity / cardiovascular).

    Postural response and shock index:
        \Delta\text{SBP} = \text{SBP}_{\text{supine}} - \text{SBP}_{\text{standing}}
        \Delta\text{HR} = \text{HR}_{\text{standing}} - \text{HR}_{\text{supine}}
        \text{SI} = \text{HR}_{\text{standing}} / \text{SBP}_{\text{standing}}

    Args:
        sbp_supine_mmhg: Systolic pressure lying down [mmHg].
        sbp_standing_mmhg: Systolic pressure standing [mmHg].
        hr_supine_bpm: Heart rate lying down [BPM].
        hr_standing_bpm: Heart rate standing [BPM].

    Returns:
        ``finding``, ``delta_sbp_mmhg``, ``hr_rise_bpm``, ``shock_index``,
        ``triggers``, ``status``, ``action``.
        WARNING when ΔSBP >= 20 mmHg, ΔHR >= 30 BPM or SI > 0.9.
    """
    delta_sbp = sbp_supine_mmhg - sbp_standing_mmhg
    hr_rise = hr_standing_bpm - hr_supine_bpm
    shock_index = hr_standing_bpm / sbp_standing_mmhg

    triggers: list[str] = []
    if delta_sbp >= 20.0:
        triggers.append("postural SBP drop >= 20 mmHg")
    if hr_rise >= 30.0:
        triggers.append("HR rise >= 30 BPM")
    if shock_index > 0.9:
        triggers.append("shock index > 0.9")

    if triggers:
        status, action = (
            Status.WARNING,
            "Execute 3-min stand test; ingest 600 mL fluid + 1 salt tablet",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "1",
        "delta_sbp_mmhg": round(delta_sbp, 1),
        "hr_rise_bpm": round(hr_rise, 1),
        "shock_index": round(shock_index, 2),
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def dehydration_2(
    body_mass_kg: float,
    baseline_body_mass_kg: float,
    urine_specific_gravity: float,
) -> DehydrationResult:
    r"""
    Finding 2: Dehydration & electrolyte loss (closed environment).

    Body-mass loss:
        \text{loss} = \frac{m_{\text{baseline}} - m}{m_{\text{baseline}}} \times 100

    Args:
        body_mass_kg: Current body mass :math:`m` [kg].
        baseline_body_mass_kg: Baseline body mass :math:`m_{\text{baseline}}` [kg].
        urine_specific_gravity: Urine specific gravity [unitless].

    Returns:
        ``finding``, ``body_mass_loss_pct``, ``urine_specific_gravity``,
        ``triggers``, ``status``, ``action``.
        WARNING when mass loss > 2 % or USG > 1.020. The plan also lists
        sweat rate and Na+ flux but gives no criteria, so they are not used.
    """
    loss_pct = (baseline_body_mass_kg - body_mass_kg) / baseline_body_mass_kg * 100

    triggers: list[str] = []
    if loss_pct > 2.0:
        triggers.append("body-mass loss > 2%")
    if urine_specific_gravity > 1.020:
        triggers.append("urine specific gravity > 1.020")

    if triggers:
        status, action = (
            Status.WARNING,
            "Drink 600 mL electrolyte solution within 30 minutes",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "2",
        "body_mass_loss_pct": round(loss_pct, 2),
        "urine_specific_gravity": urine_specific_gravity,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def acute_infection_3(
    news2_score: int,
    qsofa_score: int,
    viral_shedding: bool,
) -> InfectionResult:
    r"""
    Finding 3: Acute infection & immune dysregulation (radiation / immune).

    Args:
        news2_score: Aggregate NEWS2 early-warning score [0-20].
        qsofa_score: qSOFA sepsis score [0-3].
        viral_shedding: Latent viral shedding detected (e.g. EBV, VZV).

    Returns:
        ``finding``, ``news2_score``, ``qsofa_score``, ``triggers``,
        ``status``, ``action``.
        CRITICAL when NEWS2 >= 7 (the plan's "urgent"); otherwise WARNING when
        NEWS2 >= 5 ("review"), qSOFA >= 2 or viral shedding is detected.
    """
    triggers: list[str] = []
    if news2_score >= 7:
        triggers.append("NEWS2 >= 7 (urgent)")
    elif news2_score >= 5:
        triggers.append("NEWS2 >= 5 (review)")
    if qsofa_score >= 2:
        triggers.append("qSOFA >= 2")
    if viral_shedding:
        triggers.append("latent viral shedding")

    action = "Initiate medical-kit protocol; reduce physical workload"
    if news2_score >= 7:
        status = Status.CRITICAL
    elif triggers:
        status = Status.WARNING
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "3",
        "news2_score": news2_score,
        "qsofa_score": qsofa_score,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def hypoxia_co2_4(
    spo2_pct: float,
    respiratory_rate_bpm: float,
    ppco2_mmhg: float,
    headache: bool,
    *,
    max_respiratory_rate_bpm: float,
    max_ppco2_mmhg: float,
) -> HypoxiaResult:
    r"""
    Finding 4: Hypoxia & CO2 exposure (closed environment).

    Args:
        spo2_pct: Peripheral oxygen saturation :math:`\text{SpO}_2` [%].
        respiratory_rate_bpm: Respiratory rate [breaths/min].
        ppco2_mmhg: Ambient CO2 partial pressure :math:`pp\text{CO}_2` [mmHg].
        headache: Headache reported.
        max_respiratory_rate_bpm: Elevated-rate cutoff; the plan gives no value.
        max_ppco2_mmhg: ppCO2 cutoff; the plan gives no value.

    Returns:
        ``finding``, ``spo2_pct``, ``respiratory_rate_bpm``, ``ppco2_mmhg``,
        ``triggers``, ``status``, ``action``.
        WARNING when SpO2 < 94 %, either cutoff is exceeded, or headache is
        reported.
    """
    triggers: list[str] = []
    if spo2_pct < 94.0:
        triggers.append("SpO2 < 94%")
    if respiratory_rate_bpm > max_respiratory_rate_bpm:
        triggers.append("elevated respiratory rate")
    if ppco2_mmhg > max_ppco2_mmhg:
        triggers.append("elevated ambient ppCO2")
    if headache:
        triggers.append("headache")

    if triggers:
        status, action = (
            Status.WARNING,
            "Check CO2 scrubber, increase ventilation, or relocate",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "4",
        "spo2_pct": spo2_pct,
        "respiratory_rate_bpm": respiratory_rate_bpm,
        "ppco2_mmhg": ppco2_mmhg,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def sleep_deficiency_5(
    sleep_hours: float,
    sleep_efficiency_pct: float,
    light_exposure_lux: float,
    pvt_reaction_times_ms: Sequence[float],
    *,
    min_sleep_efficiency_pct: float,
    min_light_exposure_lux: float,
    max_pvt_lapses: int,
) -> SleepResult:
    r"""
    Finding 5: Sleep deficiency & circadian misalignment (isolation / sleep).

    A PVT lapse is a reaction time over 500 ms.

    Args:
        sleep_hours: Actigraphy sleep duration [h].
        sleep_efficiency_pct: Actigraphy sleep efficiency [%].
        light_exposure_lux: Daily light exposure [lux].
        pvt_reaction_times_ms: Reaction times from the daily 5-min PVT [ms].
        min_sleep_efficiency_pct: Efficiency cutoff; the plan gives no value.
        min_light_exposure_lux: Light cutoff; the plan gives no value.
        max_pvt_lapses: Lapse-count cutoff; the plan gives no value.

    Returns:
        ``finding``, ``sleep_hours``, ``sleep_efficiency_pct``,
        ``light_exposure_lux``, ``pvt_lapses``, ``triggers``, ``status``, ``action``.
        WARNING when sleep <= 7.5 h (parameter spec 4.3: nominal needs > 7.5 h),
        efficiency or light is below its cutoff, or lapses exceed the cutoff.
    """
    lapses = sum(1 for rt in pvt_reaction_times_ms if rt > 500.0)

    triggers: list[str] = []
    if sleep_hours <= 7.5:
        triggers.append("sleep <= 7.5 h")
    if sleep_efficiency_pct < min_sleep_efficiency_pct:
        triggers.append("low sleep efficiency")
    if light_exposure_lux < min_light_exposure_lux:
        triggers.append("low light exposure")
    if lapses > max_pvt_lapses:
        triggers.append("PVT lapses")

    if triggers:
        status, action = (
            Status.WARNING,
            "Begin 45-min 480 nm blue-light therapy; schedule 30-min nap",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "5",
        "sleep_hours": sleep_hours,
        "sleep_efficiency_pct": sleep_efficiency_pct,
        "light_exposure_lux": light_exposure_lux,
        "pvt_lapses": lapses,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def behavioral_health_decline_6(
    phq9_score: int,
    gad7_score: int,
    pvt_reaction_times_ms: Sequence[float],
    sleep_debt_hours: float,
    cortisol_slope_flattened: bool,
    *,
    min_phq9_score: int,
    min_gad7_score: int,
    max_pvt_lapses: int,
    max_sleep_debt_hours: float,
) -> BehavioralResult:
    r"""
    Finding 6: Behavioral health decline (isolation / behavioral).

    A PVT lapse is a reaction time over 500 ms.

    Args:
        phq9_score: PHQ-9 depression check-in score [0-27].
        gad7_score: GAD-7 anxiety check-in score [0-21].
        pvt_reaction_times_ms: Reaction times from the daily 5-min PVT [ms].
        sleep_debt_hours: Accumulated sleep debt [h].
        cortisol_slope_flattened: Diurnal cortisol slope has flattened
            (from the Tier 2 cortisol series, :func:`hydrogfn.domain_4.cortisol_4_1`).
        min_phq9_score: PHQ-9 flag score; the plan gives no value.
        min_gad7_score: GAD-7 flag score; the plan gives no value.
        max_pvt_lapses: Lapse-count cutoff; the plan gives no value.
        max_sleep_debt_hours: Sleep-debt cutoff; the plan gives no value.

    Returns:
        ``finding``, ``phq9_score``, ``gad7_score``, ``pvt_lapses``,
        ``sleep_debt_hours``, ``triggers``, ``status``, ``action``.
        WARNING when any criterion is met.
    """
    lapses = sum(1 for rt in pvt_reaction_times_ms if rt > 500.0)

    triggers: list[str] = []
    if phq9_score >= min_phq9_score:
        triggers.append("PHQ-9 elevated")
    if gad7_score >= min_gad7_score:
        triggers.append("GAD-7 elevated")
    if lapses > max_pvt_lapses:
        triggers.append("PVT lapses")
    if sleep_debt_hours > max_sleep_debt_hours:
        triggers.append("sleep debt")
    if cortisol_slope_flattened:
        triggers.append("flattened diurnal cortisol slope")

    if triggers:
        status, action = (
            Status.WARNING,
            "Defer non-essential tasks; initiate guided breathing/comms break",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "6",
        "phq9_score": phq9_score,
        "gad7_score": gad7_score,
        "pvt_lapses": lapses,
        "sleep_debt_hours": sleep_debt_hours,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def negative_energy_balance_7(
    body_mass_slope_kg_week: float,
    glucose_mmol_l: float,
    vitamin_d_declining: bool,
    *,
    min_body_mass_slope_kg_week: float,
) -> EnergyBalanceResult:
    r"""
    Finding 7: Negative energy balance & nutrition (closed environment).

    Unit conversion (spec 2.1):
        \text{glucose [mg/dL]} \approx 18 \cdot \text{glucose [mM]}

    Args:
        body_mass_slope_kg_week: Weekly body-mass trend [kg/week], negative = loss.
        glucose_mmol_l: Blood glucose [mM], e.g. from
            :func:`hydrogfn.domain_2.glucose_2_1`.
        vitamin_d_declining: 25-OH vitamin D trend is falling.
        min_body_mass_slope_kg_week: Slope cutoff (negative); the plan gives no value.

    Returns:
        ``finding``, ``body_mass_slope_kg_week``, ``glucose_mg_dl``,
        ``triggers``, ``status``, ``action``.
        WARNING when glucose < 70 mg/dL, the mass slope is below its cutoff,
        or vitamin D is declining.
    """
    glucose_mg_dl = glucose_mmol_l * 18.0

    triggers: list[str] = []
    if body_mass_slope_kg_week < min_body_mass_slope_kg_week:
        triggers.append("body-mass loss trend")
    if glucose_mg_dl < 70.0:
        triggers.append("glucose < 70 mg/dL")
    if vitamin_d_declining:
        triggers.append("declining 25-OH vitamin D")

    if triggers:
        status, action = (
            Status.WARNING,
            "Consume 400 kcal nutritional gel/ration + Vitamin D3 supplement",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "7",
        "body_mass_slope_kg_week": body_mass_slope_kg_week,
        "glucose_mg_dl": round(glucose_mg_dl, 1),
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def bone_demineralization_8(
    ntx_change_pct: float,
    urine_volume_l_day: float,
    exercise_compliant: bool,
    *,
    max_ntx_change_pct: float,
) -> BoneResult:
    r"""
    Finding 8: Bone demineralization & renal stone risk (gravity / musculoskeletal).

    Args:
        ntx_change_pct: Urinary NTx change from baseline [%].
        urine_volume_l_day: 24-hour urine volume [L/day].
        exercise_compliant: Resistive exercise prescription was completed.
        max_ntx_change_pct: NTx change cutoff; the plan gives no value.

    Returns:
        ``finding``, ``ntx_change_pct``, ``urine_volume_l_day``, ``triggers``,
        ``status``, ``action``.
        WARNING when NTx rises above its cutoff, urine volume < 2.0 L/day, or
        exercise is not compliant.
    """
    triggers: list[str] = []
    if ntx_change_pct > max_ntx_change_pct:
        triggers.append("NTx above baseline")
    if urine_volume_l_day < 2.0:
        triggers.append("urine volume < 2.0 L/day")
    if not exercise_compliant:
        triggers.append("exercise non-compliance")

    if triggers:
        status, action = (
            Status.WARNING,
            "Increase resistive exercise load +10%; raise daily water target to 2.5 L",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "8",
        "ntx_change_pct": ntx_change_pct,
        "urine_volume_l_day": urine_volume_l_day,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def sans_fluid_shift_9(
    fluid_shift_index: float,
    *,
    max_fluid_shift_index: float,
) -> SansResult:
    r"""
    Finding 9: SANS & cephalic fluid shift (gravity / neuro-ocular).

    Args:
        fluid_shift_index: Segmental bioimpedance fluid shift index [unitless].
        max_fluid_shift_index: Index that triggers the eye tests; the plan
            gives no value.

    Returns:
        ``finding``, ``fluid_shift_index``, ``triggers``, ``status``, ``action``.
        WARNING when the index exceeds its cutoff.
    """
    triggers: list[str] = []
    if fluid_shift_index > max_fluid_shift_index:
        triggers.append("cephalic fluid shift")

    if triggers:
        status, action = (
            Status.WARNING,
            "Run on-screen LogMAR/Amsler eye test; engage LBNP at -35 mmHg",
        )
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "9",
        "fluid_shift_index": fluid_shift_index,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def radiation_exposure_10(
    cumulative_dose_msv: float,
    dose_rate_usv_h: float,
    spe_flag: bool,
    *,
    max_dose_rate_usv_h: float,
) -> RadiationResult:
    r"""
    Finding 10: Radiation dose & solar particle events (radiation hazard).

    Args:
        cumulative_dose_msv: Cumulative effective dose [mSv].
        dose_rate_usv_h: Live dose rate [µSv/h].
        spe_flag: Solar particle event in progress.
        max_dose_rate_usv_h: Dose-rate cutoff; the plan gives no value.

    Returns:
        ``finding``, ``cumulative_dose_msv``, ``dose_rate_usv_h``, ``triggers``,
        ``status``, ``action``.
        CRITICAL (the plan's red shelter alert) when the cumulative dose
        exceeds the NASA-STD-3001 600 mSv limit, the dose rate exceeds its
        cutoff, or an SPE is flagged. There is no WARNING level.
    """
    triggers: list[str] = []
    if cumulative_dose_msv > 600.0:
        triggers.append("cumulative dose > 600 mSv")
    if dose_rate_usv_h > max_dose_rate_usv_h:
        triggers.append("dose rate above limit")
    if spe_flag:
        triggers.append("solar particle event")

    if triggers:
        status, action = Status.CRITICAL, "Move to shielded shelter zone immediately"
    else:
        status, action = Status.NOMINAL, "No finding"

    return {
        "finding": "10",
        "cumulative_dose_msv": cumulative_dose_msv,
        "dose_rate_usv_h": dose_rate_usv_h,
        "triggers": triggers,
        "status": status,
        "action": action,
    }
