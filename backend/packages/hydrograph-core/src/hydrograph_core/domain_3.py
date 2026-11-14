"""Domain 3: Musculoskeletal & Kinematic Performance (parameters 3.1-3.2)."""

from __future__ import annotations

import math
from typing import TypedDict

from .shared import Status


class NtxResult(TypedDict):
    param: str
    ntx_nm: float
    status: Status
    action: str


class JointResult(TypedDict):
    param: str
    left_flexion_deg: float
    right_flexion_deg: float
    asymmetry_ratio: float
    status: Status
    action: str


def bone_resorption_3_1(
    di_ds_ratio: float,
    t_met_days: float,
) -> NtxResult:
    r"""
    Parameter 3.1: Bone mineral resorption, microgravity osteopenia (anti-NTx GFET biosensor).

    GFET transconductance response to NTx:
        \frac{\Delta I_{ds}}{I_0} = \alpha_{\text{bone}} \cdot [\text{NTx}] \cdot e^{-\beta_{\text{flight}} \cdot t_{\text{MET}}}

    Solved for NTx concentration (what the sensor reading gives us):
        [\text{NTx}] = \frac{\Delta I_{ds} / I_0}{\alpha_{\text{bone}} \cdot e^{-\beta_{\text{flight}} \cdot t_{\text{MET}}}}

    References:
        None given in the spec for this sensor.

    Args:
        di_ds_ratio: Transconductance current reduction :math:`\Delta I_{ds} / I_0`
            as a fraction [unitless].
        t_met_days: Mission elapsed time :math:`t_{\text{MET}}` [days].

    Returns:
        ``param``, ``ntx_nm``, ``status``, ``action``.
        Nominal < 10.0 nM, WARNING 10.0-15.0 nM, CRITICAL > 15.0 nM.
    """
    alpha_bone = 0.042  # resorption calibration constant [nM^-1]
    beta_flight = 0.0012  # microgravity resorption rate [day^-1]

    # rounded before thresholds so 0.42 / 0.042 = 9.9999... still counts as 10.0
    ntx_nm = round(di_ds_ratio / (alpha_bone * math.exp(-beta_flight * t_met_days)), 2)

    if ntx_nm > 15.0:
        status, action = (
            Status.CRITICAL,
            "Notify flight surgeon for bisphosphonate therapy review",
        )
    elif ntx_nm >= 10.0:
        status, action = (
            Status.WARNING,
            "Increase ARED resistance loads +10%, adjust Calcium/Vitamin D3 intake",
        )
    else:
        status, action = Status.NOMINAL, "Healthy bone turnover"

    return {
        "param": "3.1",
        "ntx_nm": ntx_nm,
        "status": status,
        "action": action,
    }


def joint_kinematics_3_2(
    dr_r0_left: float,
    dr_r0_right: float,
) -> JointResult:
    r"""
    Parameter 3.2: Joint kinematics & exercise form degradation (carrageenan flexure strips, left/right pair).

    Joint flexural strain and its resistance response:
        \epsilon_{\text{joint}} = \frac{t_{\text{film}} \cdot \theta}{2 \cdot L_0}
        \quad \text{and} \quad
        \frac{\Delta R}{R_0} = GF \cdot \epsilon_{\text{joint}}

    Solved for joint angle (what the sensor reading gives us):
        \theta = \frac{2 \cdot L_0}{t_{\text{film}}} \cdot \frac{\Delta R / R_0}{GF}

    Left/right asymmetry ratio:
        \text{Asymmetry} = \frac{\max(\theta_L, \theta_R)}{\min(\theta_L, \theta_R)}

    References:
        Liu, X., Du, L., Ma, Y., Li, T., Chen, S., Yang, J., Ran, Z., Zhou, L., Dong, Q.,
        Zheng, W., Jiang, Z. Highly conductive and stable double network carrageenan
        organohydrogels for advanced strain sensing and signal recognition arrays.

    Args:
        dr_r0_left: Fractional resistance change :math:`\Delta R / R_0` of the left strip [unitless].
        dr_r0_right: Fractional resistance change :math:`\Delta R / R_0` of the right strip [unitless].

    Returns:
        ``param``, ``left_flexion_deg``, ``right_flexion_deg``, ``asymmetry_ratio``,
        ``status``, ``action``. Nominal needs asymmetry < 1.15 and flexion
        <= 115°. The spec defines no CRITICAL level and leaves asymmetry
        1.15-1.25 undefined, so anything outside nominal is WARNING.
    """
    t_film_mm = 1.2  # hydrogel thickness [mm]
    l0_mm = 50.0  # un-stretched gauge length [mm]
    gf = 2.1  # gauge factor [unitless]

    left_deg = math.degrees(abs(2 * l0_mm / t_film_mm * dr_r0_left / gf))
    right_deg = math.degrees(abs(2 * l0_mm / t_film_mm * dr_r0_right / gf))

    hi, lo = max(left_deg, right_deg), min(left_deg, right_deg)
    # both joints straight counts as symmetric; one straight, one bent is maximally asymmetric
    asymmetry = hi / lo if lo > 0 else (1.0 if hi == 0 else math.inf)

    if asymmetry < 1.15 and hi <= 115.0:
        status, action = Status.NOMINAL, "Balanced biomechanics"
    else:
        status, action = (
            Status.WARNING,
            "Highlight joint in red on 3D mannequin, trigger form correction prompt",
        )

    return {
        "param": "3.2",
        "left_flexion_deg": round(left_deg, 1),
        "right_flexion_deg": round(right_deg, 1),
        "asymmetry_ratio": round(asymmetry, 3),
        "status": status,
        "action": action,
    }
