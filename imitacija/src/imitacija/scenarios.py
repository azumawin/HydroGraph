"""Time-based synthetic SANS fixtures, independent of publication and delivery."""

from __future__ import annotations

from .models import AstronautProfile, SansScenario

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


def sans_eye_screen_values(t: float, scenario: SansScenario) -> dict[str, float | bool]:
    w = smoothstep(t, scenario.onset_s, scenario.warning_at_s)
    return {
        "visual_acuity_logmar": scenario.affected_logmar * w,
        "amsler_grid_distortion": t >= scenario.warning_at_s,
    }


def sans_values(
    group: str, t: float, scenario: SansScenario, *, startup: bool = False
) -> dict[str, float | bool]:
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
