"""Domain 4: Behavioral Health & Neuro-Cognitive Performance (parameters 4.1-4.3)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from .shared import Status


class CortisolResult(TypedDict):
    param: str
    cortisol_nm: float
    status: Status
    action: str


class CfeResult(TypedDict):
    param: str
    theta_power_uv2: float
    alpha_power_uv2: float
    cfe_ratio: float
    status: Status
    action: str


class SleepMoodResult(TypedDict):
    param: str
    sqi_pct: float
    sleep_hours: float
    mood_index: float
    status: Status
    action: str


def cortisol_4_1(
    di_ds_ratio: float,
) -> CortisolResult:
    r"""
    Parameter 4.1: Cortisol, stress & HPA-axis activation (aptamer / graphene-SERS biosensor).

    Langmuir binding response:
        \frac{\Delta I_{ds}}{I_0} = \frac{I_{\max} \cdot [\text{Cortisol}]}{K_d + [\text{Cortisol}]}

    Solved for cortisol (what the sensor reading gives us):
        [\text{Cortisol}] = \frac{K_d \cdot \Delta I_{ds} / I_0}{I_{\max} - \Delta I_{ds} / I_0}

    References:
        Tong, K., Liang, H., Yu, L., Song, L., Gong, E., Liu, X., Lou, Z., Mi, Y., Ruan, L.,
        Huang, Y. Sandwich SERS Chip with Raman-Silent Reporters for Ultrasensitive Serum
        Cortisol Detection and Depression Differentiation. ACS Sens. 2026.

        Bellando-Randone, M. et al. (2023). Aptamer-field-effect transistor for
        cortisol detection. Biosensors and Bioelectronics.

    Args:
        di_ds_ratio: Transconductance drop :math:`\Delta I_{ds} / I_0` as a fraction [unitless].

    Returns:
        ``param``, ``cortisol_nm``, ``status``, ``action``.
        Nominal < 15.0 nM, WARNING 15.0-30.0 nM, CRITICAL > 30.0 nM, as in
        both specs. The master plan evaluates cortisol primarily by its
        diurnal slope and applies these cutoffs to a time-of-day normalized
        reading; normalizing is the caller's job.

    Raises:
        ValueError: ``di_ds_ratio`` is outside ``0 <= di_ds_ratio < i_max``; the
            response saturates at :math:`I_{\max}` = 0.65, so no concentration
            matches.
    """
    i_max = 0.65  # drop at full saturation I_max [unitless]
    k_d = 14.8  # aptamer dissociation constant K_d [nM]

    if not 0 <= di_ds_ratio < i_max:
        raise ValueError(f"di_ds_ratio={di_ds_ratio} outside [0, {i_max})")

    cortisol_nm = k_d * di_ds_ratio / (i_max - di_ds_ratio)

    if cortisol_nm > 30.0:
        status, action = (
            Status.CRITICAL,
            "Mandatory rest period, defer non-critical ground communications",
        )
    elif cortisol_nm >= 15.0:
        status, action = (
            Status.WARNING,
            "Trigger guided neuro-feedback, shift cabin lighting to warm spectrum (2700 K)",
        )
    else:
        status, action = Status.NOMINAL, "Baseline stress state"

    return {
        "param": "4.1",
        "cortisol_nm": round(cortisol_nm, 2),
        "status": status,
        "action": action,
    }


def cognitive_fatigue_4_2(
    freqs_hz: Sequence[float],
    psd_uv2_hz: Sequence[float],
) -> CfeResult:
    r"""
    Parameter 4.2: Frontal theta/alpha EEG ratio, cognitive fatigue (dry prefrontal GFET electrodes).

    Cognitive fatigue estimation from band power:
        \text{CFE} = \frac{P_{\Theta}}{P_{\alpha}} = \frac{\int_{4}^{8} S(f) \, df}{\int_{8}^{13} S(f) \, df}

    Each integral is the trapezoid rule over the PSD samples, with :math:`S(f)`
    linearly interpolated at the band edges, so bins need not land on 4, 8 or 13 Hz.

    References:
        Cernat, A., Ştefan, G., Tertis, M., Cristea, C., Simon, I. An overview of the
        detection of serotonin and dopamine with graphene-based sensors. Bioelectrochemistry.

        Liu, T., Hu, X., Wang, D., Shi, W., Xing, D., You, C., Xu, T., Tian, M., Qu, L.,
        Zhang, X. Flexible dry electrodes for electrocardiographic monitoring: Working
        principles, design strategies, and recent advances. iScience.

    Args:
        freqs_hz: Strictly increasing frequency bins :math:`f` [Hz], covering 4-13 Hz.
        psd_uv2_hz: Power spectral density :math:`S(f)` at each bin [µV²/Hz].

    Returns:
        ``param``, ``theta_power_uv2``, ``alpha_power_uv2``, ``cfe_ratio``,
        ``status``, ``action``.
        Nominal < 0.70, WARNING 0.70-1.20, CRITICAL > 1.20. The spec's
        serotonin/dopamine readings have no formula or thresholds, so they are
        not used.

    Raises:
        ValueError: The bins do not cover 4-13 Hz, or alpha power is zero.
    """
    if len(freqs_hz) != len(psd_uv2_hz) or freqs_hz[0] > 4.0 or freqs_hz[-1] < 13.0:
        raise ValueError(
            "freqs_hz and psd_uv2_hz must be the same length and cover 4-13 Hz"
        )

    bands = ((4.0, 8.0), (8.0, 13.0))  # theta, alpha [Hz]
    power = [0.0, 0.0]  # µV²
    for i in range(len(freqs_hz) - 1):
        f0, f1 = freqs_hz[i], freqs_hz[i + 1]
        s0, s1 = psd_uv2_hz[i], psd_uv2_hz[i + 1]
        for j, (lo, hi) in enumerate(bands):
            a, b = max(f0, lo), min(f1, hi)
            if a < b:
                sa = s0 + (s1 - s0) * (a - f0) / (f1 - f0)
                sb = s0 + (s1 - s0) * (b - f0) / (f1 - f0)
                power[j] += (sa + sb) / 2 * (b - a)
    theta, alpha = power

    if alpha <= 0:
        raise ValueError("alpha band power is zero, CFE undefined")
    cfe = theta / alpha

    if cfe > 1.20:
        status, action = (
            Status.CRITICAL,
            "Mandatory task handoff, order 30-minute nap protocol",
        )
    elif cfe >= 0.70:
        status, action = (
            Status.WARNING,
            "Display fatigue warning, re-assign supervisory tasks",
        )
    else:
        status, action = Status.NOMINAL, "High cognitive alertness"

    return {
        "param": "4.2",
        "theta_power_uv2": round(theta, 3),
        "alpha_power_uv2": round(alpha, 3),
        "cfe_ratio": round(cfe, 3),
        "status": status,
        "action": action,
    }


def sleep_mood_4_3(
    t_deep_hours: float,
    t_rem_hours: float,
    t_light_hours: float,
    t_target_hours: float,
    s_self: float,
    s_voice: float,
    gsr_stress: float,
) -> SleepMoodResult:
    r"""
    Parameter 4.3: Daily sleep hours & mood index (headgear EEG + EMA self-report + voice sentiment).

    Sleep quality index:
        \text{SQI} = \left( \frac{1.5 \cdot t_{\text{deep}} + 1.0 \cdot t_{\text{REM}} + 0.5 \cdot t_{\text{light}}}{t_{\text{target}}} \right) \times 100

    Mood index:
        \text{Mood} = 0.4 \cdot S_{\text{self}} + 0.3 \cdot S_{\text{voice}} + 0.3 \cdot (10 - \text{GSR}_{\text{stress}})

    Total sleep is :math:`t_{\text{deep}} + t_{\text{REM}} + t_{\text{light}}`.

    References:
        None given in the spec for this sensor.

    Args:
        t_deep_hours: Deep sleep :math:`t_{\text{deep}}` [h].
        t_rem_hours: REM sleep :math:`t_{\text{REM}}` [h].
        t_light_hours: Light sleep :math:`t_{\text{light}}` [h].
        t_target_hours: Target sleep :math:`t_{\text{target}}` [h]; the spec gives no value.
        s_self: EMA self-report :math:`S_{\text{self}}` [1-10].
        s_voice: Voice sentiment score :math:`S_{\text{voice}}` [0-10].
        gsr_stress: Galvanic skin response stress :math:`\text{GSR}_{\text{stress}}` [0-10].

    Returns:
        ``param``, ``sqi_pct``, ``sleep_hours``, ``mood_index``, ``status``, ``action``.
        Nominal needs SQI > 80 %, sleep > 7.5 h and mood > 7.0. The spec
        defines no CRITICAL level; SQI <= 80 % or sleep <= 7.5 h is WARNING
        (this fills the SQI 55-80 % and sleep 5.5-7.5 h gaps). Mood has no
        protocol, so mood <= 7.0 with otherwise nominal sleep is UNSPECIFIED.
    """
    sqi = (
        (1.5 * t_deep_hours + 1.0 * t_rem_hours + 0.5 * t_light_hours)
        / t_target_hours
        * 100
    )
    sleep_hours = t_deep_hours + t_rem_hours + t_light_hours
    mood = 0.4 * s_self + 0.3 * s_voice + 0.3 * (10 - gsr_stress)

    if sqi <= 80.0 or sleep_hours <= 7.5:
        status, action = (
            Status.WARNING,
            "Schedule 45-minute blue-light therapy (480 nm)",
        )
    elif mood <= 7.0:
        status, action = Status.UNSPECIFIED, "No protocol defined in spec"
    else:
        status, action = Status.NOMINAL, "Healthy status"

    return {
        "param": "4.3",
        "sqi_pct": round(sqi, 1),
        "sleep_hours": round(sleep_hours, 2),
        "mood_index": round(mood, 2),
        "status": status,
        "action": action,
    }
