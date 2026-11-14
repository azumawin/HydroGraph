"""Time-based synthetic SANS fixtures, independent of publication and delivery."""

from __future__ import annotations

from .models import (
    AcuteInfectionScenario,
    AstronautProfile,
    EvaDehydrationScenario,
    HypercapniaScenario,
    SansScenario,
)

SANS_CHANNELS = frozenset(
    {
        "jugular_strain_pct",
        "delta_R_over_R0",
        "icp_risk_indicator_mmHg",
        "visual_acuity_logmar",
        "amsler_grid_distortion",
    }
)


def smoothstep(t: float, start: float, end: float) -> float:
    u = min(1.0, max(0.0, (t - start) / (end - start)))
    return u * u * (3 - 2 * u)


def sans_state(t: float, scenario: SansScenario) -> dict[str, float]:
    w = smoothstep(t, scenario.onset_s, scenario.warning_at_s)
    c = (
        smoothstep(t, scenario.critical_start_s, scenario.critical_at_s)
        if scenario.escalate_to_critical
        else 0.0
    )
    strain = (
        scenario.baseline_strain_pct
        + (scenario.warning_strain_pct - scenario.baseline_strain_pct) * w
        + (scenario.critical_strain_pct - scenario.warning_strain_pct) * c
    )
    indicator = (
        scenario.baseline_icp_indicator_mmhg
        + (scenario.warning_icp_indicator_mmhg - scenario.baseline_icp_indicator_mmhg) * w
        + (scenario.critical_icp_indicator_mmhg - scenario.warning_icp_indicator_mmhg) * c
    )
    return {
        "jugular_strain_pct": strain,
        "delta_R_over_R0": scenario.gauge_factor * strain / 100,
        "icp_risk_indicator_mmHg": indicator,
    }


def sans_rmssd_reference(
    t: float, profile: AstronautProfile, scenario: SansScenario | None
) -> float:
    if scenario is None or scenario.owner_id != profile.id:
        return profile.rmssd_ms
    w = smoothstep(t, scenario.onset_s, scenario.warning_at_s)
    return profile.rmssd_ms + (scenario.affected_rmssd_ms - profile.rmssd_ms) * w


def sans_eye_screen_values(t: float, scenario: SansScenario) -> dict[str, float | bool | str]:
    w = smoothstep(t, scenario.onset_s, scenario.warning_at_s)
    return {
        "visual_acuity_logmar": scenario.affected_logmar * w,
        "amsler_grid_distortion": t >= scenario.warning_at_s,
    }


def sans_values(
    group: str, t: float, scenario: SansScenario, *, startup: bool = False
) -> dict[str, float | bool | str]:
    if group == "eye_screen":
        return sans_eye_screen_values(t, scenario)
    if group != "cephalic":
        raise ValueError(f"unknown SANS group: {group}")
    if startup:
        return dict(sans_state(0, scenario))
    if t < 60:
        raise ValueError("cephalic measurements require a completed 60s window")
    # 50Hz latent trend, midpoint quadrature; no pulse-waveform claim.
    totals = {name: 0.0 for name in sans_state(t, scenario)}
    for i in range(3000):
        for name, value in sans_state(t - 60 + (i + 0.5) / 50, scenario).items():
            totals[name] += value / 3000
    return dict(totals)


HYPERCAPNIA_CHANNELS = frozenset({"eeg_cfe_ratio"})


def hypercapnia_progress(t: float, scenario: HypercapniaScenario, delay: float = 0) -> float:
    start = scenario.onset_s + delay
    return smoothstep(t, start, start + scenario.ramp_duration_s)


def hypercapnia_cabin_mmhg(t: float, scenario: HypercapniaScenario) -> float:
    return scenario.baseline_ppco2_mmhg + (
        scenario.affected_ppco2_mmhg - scenario.baseline_ppco2_mmhg
    ) * hypercapnia_progress(t, scenario)


def hypercapnia_references(
    t: float, profile: AstronautProfile, scenario: HypercapniaScenario
) -> dict[str, float]:
    v = hypercapnia_progress(t, scenario, scenario.compensation_delay_s)
    o = hypercapnia_progress(t, scenario, scenario.oxygenation_delay_s)
    return {
        "heart_rate": profile.resting_hr_bpm
        + (scenario.affected_heart_rate_bpm - profile.resting_hr_bpm) * v,
        "respiratory_rate": scenario.baseline_respiratory_rate_br_min
        + (scenario.affected_respiratory_rate_br_min - scenario.baseline_respiratory_rate_br_min)
        * v,
        "spo2": scenario.baseline_spo2_pct
        + (scenario.affected_spo2_pct - scenario.baseline_spo2_pct) * o,
        "eeg_cfe_ratio": scenario.baseline_cfe_ratio
        + (scenario.affected_cfe_ratio - scenario.baseline_cfe_ratio) * o,
    }


def hypercapnia_eeg_values(
    t: float, scenario: HypercapniaScenario, *, startup: bool = False
) -> dict[str, float]:
    if startup:
        return {"eeg_cfe_ratio": scenario.baseline_cfe_ratio}
    if t < 60:
        raise ValueError("CFE requires a completed 60s window")
    mean_progress = (
        sum(
            hypercapnia_progress(t - 60 + i + 0.5, scenario, scenario.oxygenation_delay_s)
            for i in range(60)
        )
        / 60
    )
    return {
        "eeg_cfe_ratio": scenario.baseline_cfe_ratio
        + (scenario.affected_cfe_ratio - scenario.baseline_cfe_ratio) * mean_progress
    }


EVA_CHANNELS = frozenset({"whole_body_sweat_rate"})


def eva_balance(
    t: float, profile: AstronautProfile, scenario: EvaDehydrationScenario
) -> dict[str, float]:
    hours = min(max(t - scenario.onset_s, 0), scenario.eva_duration_s) / 3600
    sweat = scenario.active_whole_body_sweat_l_h * hours
    intake = scenario.drink_rate_l_h * hours
    deficit = sweat - intake
    return dict(
        sweat_loss_l=sweat,
        intake_l=intake,
        deficit_l=deficit,
        mass_kg=profile.mass_kg - deficit,
        loss_pct=100 * deficit / profile.mass_kg,
        sodium_loss_mmol=sweat * scenario.active_sweat_sodium_mmol_l,
    )


def eva_weight(t: float, profile: AstronautProfile, scenario: EvaDehydrationScenario) -> float:
    p = min(1.0, eva_balance(t, profile, scenario)["loss_pct"] / scenario.response_loss_pct)
    return p * p * (3 - 2 * p)


def eva_usg(t: float, profile: AstronautProfile, scenario: EvaDehydrationScenario) -> float:
    return scenario.baseline_usg + (scenario.affected_usg - scenario.baseline_usg) * eva_weight(
        t, profile, scenario
    )


def eva_sweat_values(
    t: float, scenario: EvaDehydrationScenario, *, startup: bool = False
) -> dict[str, float]:
    if not startup and not scenario.onset_s + 1 <= t <= scenario.onset_s + scenario.eva_duration_s:
        return {}
    flow = (
        scenario.baseline_whole_body_sweat_l_h if startup else scenario.active_whole_body_sweat_l_h
    )
    sodium = (
        scenario.baseline_sweat_sodium_mmol_l if startup else scenario.active_sweat_sodium_mmol_l
    )
    local = flow / scenario.whole_body_to_patch_multiplier
    return dict(
        whole_body_sweat_rate=flow,
        sweat_rate=local,
        sweat_sodium_concentration=sodium,
        sweat_sodium_flux=local * sodium,
    )


INFECTION_CHANNELS = frozenset(
    {"il6_pg_mL", "consciousness_level", "supplemental_o2", "post_ared_exercise_window"}
)


def infection_references(
    t: float, profile: AstronautProfile, scenario: AcuteInfectionScenario
) -> dict[str, float]:
    w = smoothstep(t, scenario.onset_s, scenario.affected_at_s)
    pairs = {
        "body_temperature": (scenario.baseline_temp_c, scenario.affected_temp_c),
        "heart_rate": (profile.resting_hr_bpm, scenario.affected_heart_rate_bpm),
        "respiratory_rate": (
            scenario.baseline_respiratory_rate_br_min,
            scenario.affected_respiratory_rate_br_min,
        ),
        "bp_systolic": (profile.sbp_mmhg, scenario.affected_sbp_mmhg),
        "spo2": (scenario.baseline_spo2_pct, scenario.affected_spo2_pct),
        "il6_pg_mL": (scenario.baseline_il6_pg_ml, scenario.affected_il6_pg_ml),
    }
    return {k: a + (z - a) * w for k, (a, z) in pairs.items()}


def infection_context_values(
    t: float, scenario: AcuteInfectionScenario
) -> dict[str, float | bool | str]:
    affected = t >= scenario.affected_at_s
    return dict(
        consciousness_level=scenario.affected_consciousness_level if affected else "ALERT",
        supplemental_o2=scenario.affected_supplemental_o2 if affected else False,
        post_ared_exercise_window=scenario.affected_post_ared_exercise_window
        if affected
        else False,
    )
