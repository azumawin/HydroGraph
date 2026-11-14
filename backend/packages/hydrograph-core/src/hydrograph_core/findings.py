"""Tier 1: the 10 personal health findings (master plan, section 2).

Each function evaluates one finding for the main window and returns its
immediate action card. Criteria the master plan quantifies are computed here.
Criteria it names without a cutoff are either keyword-only arguments the
caller must supply (numeric) or booleans evaluated upstream (qualitative).

Naming: ``<finding>_D_S``. The master plan numbers the findings 1-10 and gives
each a "Primary Domain" (hazard), but does not number the domains. Our
numbering: domains in order of first appearance in the plan's table, findings
in plan order within each domain. The ``finding`` key of each result keeps the
plan's own number.

====  ==================  =======================================  ============
D     Domain              Function                                 Plan finding
====  ==================  =======================================  ============
1     Gravity             ``orthostatic_intolerance_1_1``          1
1     Gravity             ``bone_demineralization_1_2``            8
1     Gravity             ``sans_fluid_shift_1_3``                 9
2     Closed environment  ``dehydration_2_1``                      2
2     Closed environment  ``hypoxia_co2_2_2``                      4
2     Closed environment  ``negative_energy_balance_2_3``          7
3     Radiation           ``acute_infection_3_1``                  3
3     Radiation           ``radiation_exposure_3_2``               10
4     Isolation           ``sleep_deficiency_4_1``                 5
4     Isolation           ``behavioral_health_decline_4_2``        6
====  ==================  =======================================  ============
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

Severity = Literal["nominal", "warning", "critical"]
"""``status`` of a finding with several severities."""


class OrthostaticResult(TypedDict):
    finding: str
    delta_sbp_mmhg: float
    delta_dbp_mmhg: float
    hr_rise_bpm: float
    shock_index: float
    ctni_ng_ml: float | None
    triggers: list[str]
    status: Severity
    action: str


class DehydrationResult(TypedDict):
    finding: str
    body_mass_loss_pct: float
    fluid_deficit_ml: float
    urine_specific_gravity: float
    triggers: list[str]
    status: bool
    action: str


class InfectionResult(TypedDict):
    finding: str
    news2_score: int
    core_temp_c: float
    il6_pg_ml: float
    triggers: list[str]
    status: Severity
    action: str


class HypoxiaResult(TypedDict):
    finding: str
    spo2_pct: float
    ppco2_mmhg: float
    triggers: list[str]
    status: Severity
    action: str


class SleepResult(TypedDict):
    finding: str
    sleep_hours: float
    pvt_lapses: int
    cfe_ratio: float
    triggers: list[str]
    status: Severity
    action: str


class BehavioralResult(TypedDict):
    finding: str
    phq9_score: int
    gad7_score: int
    pvt_lapses: int
    sleep_debt_hours: float
    cortisol_nm: float
    triggers: list[str]
    status: Severity
    action: str


class EnergyBalanceResult(TypedDict):
    finding: str
    body_mass_loss_pct_week: float
    glucose_mg_dl: float
    resting_lactate_mm: float
    triggers: list[str]
    status: bool
    action: str


class BoneResult(TypedDict):
    finding: str
    ntx_change_pct: float
    urine_volume_l_day: float
    triggers: list[str]
    status: bool
    action: str


class SansResult(TypedDict):
    finding: str
    jugular_distension_pct: float
    triggers: list[str]
    status: Severity
    action: str


class RadiationResult(TypedDict):
    finding: str
    cumulative_dose_msv: float
    dose_rate_usv_h: float
    triggers: list[str]
    status: Severity
    action: str


def orthostatic_intolerance_1_1(
    sbp_supine_mmhg: float,
    sbp_standing_mmhg: float,
    dbp_supine_mmhg: float,
    dbp_standing_mmhg: float,
    hr_supine_bpm: float,
    hr_standing_bpm: float,
    ctni_ng_ml: float | None,
) -> OrthostaticResult:
    r"""
    Finding 1: Orthostatic intolerance & CV deconditioning (gravity / cardiovascular).

    Postural response and shock index:
        \Delta\text{SBP} = \text{SBP}_{\text{supine}} - \text{SBP}_{\text{standing}}
        \Delta\text{DBP} = \text{DBP}_{\text{supine}} - \text{DBP}_{\text{standing}}
        \Delta\text{HR} = \text{HR}_{\text{standing}} - \text{HR}_{\text{supine}}
        \text{SI} = \text{HR}_{\text{standing}} / \text{SBP}_{\text{standing}}

    References:
        Freeman, R. et al. (2011). Consensus statement on the definition of
        orthostatic hypotension, neurally mediated syncope and the postural
        tachycardia syndrome. Clinical Autonomic Research, 21(2), 69–72.

        Sheldon, R. S. et al. (2015). 2015 Heart Rhythm Society expert consensus
        statement on the diagnosis and treatment of postural tachycardia
        syndrome, inappropriate sinus tachycardia, and vasovagal syncope. Heart
        Rhythm, 12(6), e41–e63.

        Al-Mulla, M. et al. (2024). Correlation between shock index and
        mortality in the prehospital and emergency setting. International
        Journal of Paramedicine, (6), 42–51.

    Args:
        sbp_supine_mmhg: Systolic pressure lying down [mmHg].
        sbp_standing_mmhg: Systolic pressure within 3 min of standing [mmHg].
        dbp_supine_mmhg: Diastolic pressure lying down [mmHg].
        dbp_standing_mmhg: Diastolic pressure within 3 min of standing [mmHg].
        hr_supine_bpm: Heart rate lying down [BPM].
        hr_standing_bpm: Heart rate within 10 min of standing [BPM].
        ctni_ng_ml: Event-triggered hs-cTnI [ng/mL], e.g. from
            Parameter 1.2; ``None`` when no assay was run.

    Returns:
        ``finding``, ``delta_sbp_mmhg``, ``delta_dbp_mmhg``, ``hr_rise_bpm``,
        ``shock_index``, ``ctni_ng_ml``, ``triggers``, ``status``, ``action``.
        CRITICAL when hs-cTnI > 0.04 ng/mL; otherwise WARNING when ΔSBP >= 20
        mmHg, ΔDBP >= 10 mmHg, ΔHR >= 30 BPM or SI > 0.9. The plan's
        "without hypotension" only separates POTS from orthostatic
        hypotension; both are WARNING, so the HR rise fires either way.
    """
    delta_sbp = sbp_supine_mmhg - sbp_standing_mmhg
    delta_dbp = dbp_supine_mmhg - dbp_standing_mmhg
    hr_rise = hr_standing_bpm - hr_supine_bpm
    shock_index = hr_standing_bpm / sbp_standing_mmhg
    troponin_high = ctni_ng_ml is not None and ctni_ng_ml > 0.04

    triggers: list[str] = []
    if delta_sbp >= 20.0:
        triggers.append("postural SBP drop >= 20 mmHg")
    if delta_dbp >= 10.0:
        triggers.append("postural DBP drop >= 10 mmHg")
    if hr_rise >= 30.0:
        triggers.append("HR rise >= 30 BPM")
    if shock_index > 0.9:
        triggers.append("shock index > 0.9")
    if troponin_high:
        triggers.append("hs-cTnI > 0.04 ng/mL")

    action = "Execute 3-min stand test; ingest 600 mL fluid + 1 salt tablet; restrict EVA if hs-cTnI elevated"
    if troponin_high:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "1",
        "delta_sbp_mmhg": round(delta_sbp, 1),
        "delta_dbp_mmhg": round(delta_dbp, 1),
        "hr_rise_bpm": round(hr_rise, 1),
        "shock_index": round(shock_index, 2),
        "ctni_ng_ml": ctni_ng_ml,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def dehydration_2_1(
    body_mass_kg: float,
    baseline_body_mass_kg: float,
    urine_specific_gravity: float,
) -> DehydrationResult:
    r"""
    Finding 2: Dehydration & electrolyte loss (closed environment).

    Body-mass loss and fluid deficit (1 kg of acute mass loss = 1 L of water):
        \text{loss} = \frac{m_{\text{baseline}} - m}{m_{\text{baseline}}} \times 100
        V_{\text{deficit}} = (m_{\text{baseline}} - m) \times 1000

    References:
        Sawka, M. N. et al. (2007). American College of Sports Medicine position
        stand: Exercise and fluid replacement. Medicine & Science in Sports &
        Exercise, 39(2), 377–390.

        Armstrong, L. E. et al. (1998). Urinary indices during dehydration,
        exercise, and rehydration. International Journal of Sport Nutrition,
        8(4), 345–355.

        Lu, L. et al. (2025). Sweat-sensing patches with integrated hydrogel
        interface for resting sweat collection and multi-information detection.
        Biosensors, 15(6), 342.

    Args:
        body_mass_kg: Current body mass :math:`m` [kg].
        baseline_body_mass_kg: Baseline body mass :math:`m_{\text{baseline}}` [kg].
        urine_specific_gravity: Urine specific gravity [unitless].

    Returns:
        ``finding``, ``body_mass_loss_pct``, ``fluid_deficit_ml``,
        ``urine_specific_gravity``, ``triggers``, ``status``, ``action``.
        ``status`` is True when mass loss > 2 % or USG > 1.020. ``fluid_deficit_ml`` is
        the action card's "calculated fluid deficit", 0 when mass has not
        dropped. The plan tracks sweat rate and Na+ flux only as
        baseline-relative trends with no cutoff, so they are not used.
    """
    loss_kg = baseline_body_mass_kg - body_mass_kg
    loss_pct = loss_kg / baseline_body_mass_kg * 100

    triggers: list[str] = []
    if loss_pct > 2.0:
        triggers.append("body-mass loss > 2%")
    if urine_specific_gravity > 1.020:
        triggers.append("urine specific gravity > 1.020")

    status = bool(triggers)
    action = (
        "Drink calculated fluid deficit (e.g., 600 mL electrolyte solution) within 30 minutes"
        if status
        else "No finding"
    )

    return {
        "finding": "2",
        "body_mass_loss_pct": round(loss_pct, 2),
        "fluid_deficit_ml": round(max(loss_kg, 0.0) * 1000),
        "urine_specific_gravity": urine_specific_gravity,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def acute_infection_3_1(
    news2_score: int,
    news2_max_parameter_score: int,
    core_temp_c: float,
    il6_pg_ml: float,
    post_ared_window: bool,
    herpesvirus_reactivation: bool,
) -> InfectionResult:
    r"""
    Finding 3: Acute infection & immune dysregulation (radiation / immune).

    References:
        Royal College of Physicians. (2017). National Early Warning Score (NEWS)
        2: Standardising the assessment of acute-illness severity in the NHS.
        London, U.K.: RCP.

        Mehta, S. K. et al. (2017). Latent virus reactivation in astronauts on
        the International Space Station. npj Microgravity, 3(1), 11.

        Chen, Y. et al. (2025). Aptamer-based graphene field-effect transistor
        biosensor for cytokine detection in undiluted physiological media. ACS
        Sensors.

    Args:
        news2_score: Aggregate NEWS2 early-warning score [0-20].
        news2_max_parameter_score: Highest single-vital NEWS2 score [0-3].
        core_temp_c: ZHF core-equivalent temperature [°C], e.g. from
            Parameter 2.2.
        il6_pg_ml: GFET IL-6 concentration [pg/mL].
        post_ared_window: The reading is within 2 h after an ARED workout.
        herpesvirus_reactivation: Latent EBV, VZV or CMV reactivation detected.

    Returns:
        ``finding``, ``news2_score``, ``core_temp_c``, ``il6_pg_ml``,
        ``triggers``, ``status``, ``action``.
        CRITICAL when NEWS2 >= 7 (the plan's "emergency"); otherwise WARNING
        when NEWS2 >= 5 or any single vital scores 3 ("urgent review"), core
        temperature is > 38.0 °C or < 36.0 °C (SIRS), herpesvirus
        reactivation is detected, or IL-6 > 3.0 pg/mL outside the
        post-ARED window.
    """
    triggers: list[str] = []
    if news2_score >= 7:
        triggers.append("NEWS2 >= 7 (emergency)")
    elif news2_score >= 5:
        triggers.append("NEWS2 >= 5 (urgent review)")
    if news2_max_parameter_score >= 3:
        triggers.append("NEWS2 single vital scoring 3")
    if core_temp_c > 38.0:
        triggers.append("core temp > 38.0 °C")
    elif core_temp_c < 36.0:
        triggers.append("core temp < 36.0 °C")
    if herpesvirus_reactivation:
        triggers.append("latent herpesvirus reactivation")
    if il6_pg_ml > 3.0 and not post_ared_window:
        triggers.append("IL-6 > 3.0 pg/mL")

    action = (
        "Initiate medical-kit protocol; reduce physical workload; isolate if febrile"
    )
    if news2_score >= 7:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "3",
        "news2_score": news2_score,
        "core_temp_c": core_temp_c,
        "il6_pg_ml": il6_pg_ml,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def hypoxia_co2_2_2(
    spo2_pct: float,
    respiratory_rate_rising: bool,
    ppco2_mmhg: float,
    headache: bool,
) -> HypoxiaResult:
    r"""
    Finding 4: Hypoxia & CO2 exposure (closed environment).

    References:
        NASA Office of the Chief Health and Medical Officer (OCHMO). (2023a).
        Carbon Dioxide (CO2). NASA Technical Brief OCHMO-TB-004 Rev. B.

    Args:
        spo2_pct: Peripheral oxygen saturation :math:`\text{SpO}_2` [%].
        respiratory_rate_rising: Respiratory rate is rising (trend evaluated
            upstream; the plan gives no cutoff).
        ppco2_mmhg: NDIR ambient CO2 partial pressure :math:`pp\text{CO}_2` [mmHg].
        headache: Headache reported.

    Returns:
        ``finding``, ``spo2_pct``, ``ppco2_mmhg``, ``triggers``, ``status``,
        ``action``.
        CRITICAL when SpO2 < 90 % (hypoxemia); otherwise WARNING when SpO2 <
        94 %, ppCO2 > 3.0 mmHg, respiratory rate is rising, or headache is
        reported.
    """
    triggers: list[str] = []
    if spo2_pct < 90.0:
        triggers.append("SpO2 < 90%")
    elif spo2_pct < 94.0:
        triggers.append("SpO2 < 94%")
    if respiratory_rate_rising:
        triggers.append("rising respiratory rate")
    if ppco2_mmhg > 3.0:
        triggers.append("ppCO2 > 3.0 mmHg")
    if headache:
        triggers.append("headache")

    action = (
        "Inspect CO2 scrubber, increase module ventilation, or relocate immediately"
    )
    if spo2_pct < 90.0:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "4",
        "spo2_pct": spo2_pct,
        "ppco2_mmhg": ppco2_mmhg,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def sleep_deficiency_4_1(
    sleep_hours: float,
    pvt_reaction_times_ms: Sequence[float],
    cfe_ratio: float,
    *,
    max_pvt_lapses: int,
) -> SleepResult:
    r"""
    Finding 5: Sleep deficiency & circadian fatigue (isolation / sleep).

    A PVT lapse is a reaction time over 500 ms.

    References:
        Barger, L. K. et al. (2014). Prevalence of sleep deficiency and use of
        hypnotic drugs in astronauts before, during, and after spaceflight: An
        observational study. The Lancet Neurology, 13(9), 904–912.

        Rajaratnam, S. M. et al. (2023). Effectiveness of caffeine and
        blue-enriched light countermeasures on sleepiness and EEG power during
        circadian misalignment. Journal of Pineal Research.

    Args:
        sleep_hours: Wrist actigraphy sleep duration [h].
        pvt_reaction_times_ms: Reaction times from the daily 5-min PVT [ms].
        cfe_ratio: Prefrontal EEG CFE, e.g. from
            Parameter 4.2 [unitless].
        max_pvt_lapses: Lapse-count cutoff; the plan gives no value.

    Returns:
        ``finding``, ``sleep_hours``, ``pvt_lapses``, ``cfe_ratio``,
        ``triggers``, ``status``, ``action``.
        CRITICAL when CFE > 1.20; otherwise WARNING when CFE >= 0.70, sleep
        <= 7.5 h, or lapses exceed the cutoff. The plan anchors actigraphy to
        the flight baseline (ISS mean 6.09 h vs. 8.5 h scheduled) without a
        cutoff, so the sleep cutoff is the parameter spec's (4.3: nominal
        needs > 7.5 h).
    """
    lapses = sum(1 for rt in pvt_reaction_times_ms if rt > 500.0)

    triggers: list[str] = []
    if sleep_hours <= 7.5:
        triggers.append("sleep <= 7.5 h")
    if lapses > max_pvt_lapses:
        triggers.append("PVT lapses")
    if cfe_ratio > 1.20:
        triggers.append("CFE > 1.20")
    elif cfe_ratio >= 0.70:
        triggers.append("CFE >= 0.70")

    action = (
        "Begin 45-min 480 nm blue-enriched light protocol; schedule 30-min recovery nap"
    )
    if cfe_ratio > 1.20:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "5",
        "sleep_hours": sleep_hours,
        "pvt_lapses": lapses,
        "cfe_ratio": cfe_ratio,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def behavioral_health_decline_4_2(
    phq9_score: int,
    gad7_score: int,
    pvt_reaction_times_ms: Sequence[float],
    sleep_debt_hours: float,
    cortisol_slope_flattened: bool,
    cortisol_nm: float,
    *,
    max_pvt_lapses: int,
    max_sleep_debt_hours: float,
) -> BehavioralResult:
    r"""
    Finding 6: Behavioral health & HPA-axis decline (isolation / behavioral).

    A PVT lapse is a reaction time over 500 ms.

    References:
        Kroenke, K., Spitzer, R. L., & Williams, J. B. W. (2001). The PHQ-9:
        Validity of a brief depression severity measure. Journal of General
        Internal Medicine, 16(9), 606–613.

        Bellando-Randone, M. et al. (2023). Aptamer-field-effect transistor for
        cortisol detection. Biosensors and Bioelectronics.

    Args:
        phq9_score: PHQ-9 depression check-in score [0-27].
        gad7_score: GAD-7 anxiety check-in score [0-21].
        pvt_reaction_times_ms: Reaction times from the daily 5-min PVT [ms].
        sleep_debt_hours: Accumulated sleep debt [h].
        cortisol_slope_flattened: Diurnal cortisol degradation slope has
            flattened (from the Tier 2 cortisol series).
        cortisol_nm: Time-of-day normalized ISF cortisol [nM], e.g. from
            Parameter 4.1.
        max_pvt_lapses: Lapse-count cutoff; the plan gives no value.
        max_sleep_debt_hours: Sleep-debt cutoff; the plan gives no value.

    Returns:
        ``finding``, ``phq9_score``, ``gad7_score``, ``pvt_lapses``,
        ``sleep_debt_hours``, ``cortisol_nm``, ``triggers``, ``status``,
        ``action``.
        CRITICAL when cortisol > 30 nM; otherwise WARNING when PHQ-9 or GAD-7
        >= 10, cortisol >= 15 nM, the slope has flattened, or lapses or sleep
        debt exceed their cutoffs.
    """
    lapses = sum(1 for rt in pvt_reaction_times_ms if rt > 500.0)

    triggers: list[str] = []
    if phq9_score >= 10:
        triggers.append("PHQ-9 >= 10")
    if gad7_score >= 10:
        triggers.append("GAD-7 >= 10")
    if lapses > max_pvt_lapses:
        triggers.append("PVT lapses")
    if sleep_debt_hours > max_sleep_debt_hours:
        triggers.append("sleep debt")
    if cortisol_slope_flattened:
        triggers.append("flattened diurnal cortisol slope")
    if cortisol_nm > 30.0:
        triggers.append("ISF cortisol > 30 nM")
    elif cortisol_nm >= 15.0:
        triggers.append("ISF cortisol >= 15 nM")

    action = "Defer non-essential tasks; initiate guided breathing/biofeedback and crew comms break"
    if cortisol_nm > 30.0:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "6",
        "phq9_score": phq9_score,
        "gad7_score": gad7_score,
        "pvt_lapses": lapses,
        "sleep_debt_hours": sleep_debt_hours,
        "cortisol_nm": cortisol_nm,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def negative_energy_balance_2_3(
    body_mass_loss_pct_week: float,
    glucose_mmol_l: float,
    resting_lactate_mm: float,
) -> EnergyBalanceResult:
    r"""
    Finding 7: Negative energy balance & nutrition (closed environment).

    Unit conversion (spec 2.1):
        \text{glucose [mg/dL]} \approx 18 \cdot \text{glucose [mM]}

    References:
        Heer, M. et al. (2022). Physiological alterations in relation to space
        flight: Nutritional concerns and negative energy balance. Nutrients,
        14(22).

        International Hypoglycaemia Study Group (IHSG) & American Diabetes
        Association (ADA). (2017). Glucose concentrations of less than 3.0
        mmol/L (54 mg/dL) should be reported in clinical trials: A joint
        position statement. Diabetes Care, 40(1), 155–157.

    Args:
        body_mass_loss_pct_week: Weekly body-mass loss as % of baseline
            [%/week], positive = loss.
        glucose_mmol_l: Blood glucose [mM], e.g. from
            Parameter 2.1.
        resting_lactate_mm: Resting blood lactate [mM].

    Returns:
        ``finding``, ``body_mass_loss_pct_week``, ``glucose_mg_dl``,
        ``resting_lactate_mm``, ``triggers``, ``status``, ``action``.
        ``status`` is True when mass loss > 1.0 %/week, glucose < 70 mg/dL
        (Level 1; the trigger names Level 2 below 54 mg/dL) or resting lactate
        > 4.0 mM. The plan gives one action card and marks neither level
        urgent, so the finding has no severity.
    """
    glucose_mg_dl = glucose_mmol_l * 18.0

    triggers: list[str] = []
    if body_mass_loss_pct_week > 1.0:
        triggers.append("weekly body-mass loss > 1.0%")
    if glucose_mg_dl < 54.0:
        triggers.append("Level 2 hypoglycemia < 54 mg/dL")
    elif glucose_mg_dl < 70.0:
        triggers.append("Level 1 hypoglycemia < 70 mg/dL")
    if resting_lactate_mm > 4.0:
        triggers.append("resting lactate > 4.0 mM")

    status = bool(triggers)
    action = (
        "Consume 400 kcal nutritional ration + Vitamin D3 supplement; re-check glucose in 15 min"
        if status
        else "No finding"
    )

    return {
        "finding": "7",
        "body_mass_loss_pct_week": body_mass_loss_pct_week,
        "glucose_mg_dl": round(glucose_mg_dl, 1),
        "resting_lactate_mm": resting_lactate_mm,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def bone_demineralization_1_2(
    ntx_change_pct: float,
    urine_volume_l_day: float,
) -> BoneResult:
    r"""
    Finding 8: Bone demineralization & renal stone risk (gravity / musculoskeletal).

    References:
        NASA Human Research Program. (2025). Risk of Spaceflight-Induced Bone
        Changes. NASA Human System Risk Board Evidence Report.

        Kasprzak, A., & Kaczmarek, M. (2024). Renal stone formation in
        spaceflight. Aerospace Medicine and Human Performance / Sciendo, 30(1),
        35–42.

    Args:
        ntx_change_pct: GFET urinary/serum NTx change from the personal
            preflight baseline [%].
        urine_volume_l_day: 24-hour urine volume [L/day].

    Returns:
        ``finding``, ``ntx_change_pct``, ``urine_volume_l_day``, ``triggers``,
        ``status``, ``action``.
        ``status`` is True when NTx is > +25 % or urine volume < 2.0 L/day. The plan's
        BMD loss of 1.0-1.5 %/month is context, not a criterion.
    """
    triggers: list[str] = []
    if ntx_change_pct > 25.0:
        triggers.append("NTx > +25% from baseline")
    if urine_volume_l_day < 2.0:
        triggers.append("urine volume < 2.0 L/day")

    status = bool(triggers)
    action = (
        "Increase ARED resistive exercise load +10%; raise daily water target to >= 2.5 L/day"
        if status
        else "No finding"
    )

    return {
        "finding": "8",
        "ntx_change_pct": ntx_change_pct,
        "urine_volume_l_day": urine_volume_l_day,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def sans_fluid_shift_1_3(jugular_distension_pct: float) -> SansResult:
    r"""
    Finding 9: SANS & cephalic fluid shift (gravity / neuro-ocular).

    References:
        Roy, S. et al. (2024). Jugular venous pulse waveform acquisition using
        contact piezo sensor. IEEE Transactions on Biomedical Engineering,
        71(8), 2410–2419.

        Lee, A. G. et al. (2020). Spaceflight associated neuro-ocular syndrome
        (SANS) and the neuro-ophthalmologic effects of microgravity: A review
        and an update. npj Microgravity, 6(1), 7.

        Petersen, L. G. et al. (2019). Lower body negative pressure to safely
        reduce intracranial pressure. The Journal of Physiology, 597(1),
        237–248.

    Args:
        jugular_distension_pct: Baseline-relative jugular distension from the
            carrageenan neck patch [%], e.g. ``strain_pct`` of
            Parameter 1.1.

    Returns:
        ``finding``, ``jugular_distension_pct``, ``triggers``, ``status``,
        ``action``.
        Nominal < 1.1 %, WARNING 1.1-1.8 %, CRITICAL > 1.8 %. Both bands
        share the one action card.
    """
    triggers: list[str] = []
    if jugular_distension_pct > 1.8:
        triggers.append("jugular distension > 1.8%")
    elif jugular_distension_pct >= 1.1:
        triggers.append("jugular distension >= 1.1%")

    action = "Run on-screen LogMAR/Amsler eye test; engage 20-min LBNP at -35 mmHg"
    if jugular_distension_pct > 1.8:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "9",
        "jugular_distension_pct": jugular_distension_pct,
        "triggers": triggers,
        "status": status,
        "action": action,
    }


def radiation_exposure_3_2(
    cumulative_dose_msv: float,
    dose_rate_usv_h: float,
    spe_flag: bool,
) -> RadiationResult:
    r"""
    Finding 10: Radiation dose & solar particle events (radiation hazard).

    References:
        NASA. (2022). NASA Space Flight Human-System Standard Volume 1: Crew
        Health (NASA-STD-3001 Vol. 1 Rev. B, Sec. 4.8.2–4.8.3).

    Args:
        cumulative_dose_msv: Cumulative effective dose [mSv].
        dose_rate_usv_h: Live dose rate [µSv/h].
        spe_flag: Telemetry SPE flag (solar particle event in progress).

    Returns:
        ``finding``, ``cumulative_dose_msv``, ``dose_rate_usv_h``, ``triggers``,
        ``status``, ``action``.
        CRITICAL (the storm shelter alert) when an SPE is flagged; otherwise
        WARNING when the dose rate is > 50 µSv/h (the plan's "warning") or the
        cumulative dose exceeds the 600 mSv career limit. The plan gives the
        finding one action card, the shelter, for every criterion.
    """
    triggers: list[str] = []
    if cumulative_dose_msv > 600.0:
        triggers.append("cumulative dose > 600 mSv")
    if dose_rate_usv_h > 50.0:
        triggers.append("dose rate > 50 µSv/h")
    if spe_flag:
        triggers.append("solar particle event")

    action = "Move to shielded storm shelter zone immediately and confirm hatch closure"
    if spe_flag:
        status = "critical"
    elif triggers:
        status = "warning"
    else:
        status, action = "nominal", "No finding"

    return {
        "finding": "10",
        "cumulative_dose_msv": cumulative_dose_msv,
        "dose_rate_usv_h": dose_rate_usv_h,
        "triggers": triggers,
        "status": status,
        "action": action,
    }
