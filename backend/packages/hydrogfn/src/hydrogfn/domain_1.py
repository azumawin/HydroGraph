"""Domain 1: Cardiovascular Health & Fluid Dynamics (parameters 1.1-1.3)."""

from __future__ import annotations

import math
from typing import TypedDict

from .shared import Status


class IcpResult(TypedDict):
    param: str
    strain_pct: float
    icp_mmhg: float
    status: Status
    action: str


class TroponinResult(TypedDict):
    param: str
    delta_vt_mv: float
    ctni_ng_ml: float
    status: Status
    action: str


class BpHrResult(TypedDict):
    param: str
    map_mmhg: float
    hr_bpm: float
    status: Status
    action: str


def cephalic_fluid_shift_1_1(
    r: float,
    r0: float = 0.45089,
    gf: float = 2.1,
    k1: float = 185.4,
    icp_baseline: float = 9.5,
) -> IcpResult:
    r"""
    Parameter 1.1: Cephalic fluid shift & SANS (carrageenan strain sensor).

    Strain from fractional resistance change:
        \epsilon = \frac{1}{GF} \cdot \left( \frac{\Delta R}{R_0} \right)

    Intracranial pressure estimate:
        \text{ICP}_{\text{est}} = k_1 \cdot \epsilon + \text{ICP}_{\text{baseline}}

    References:
        Bučinskas, V.; Žaimis, U.; Udris, D.; Petronienė, J.J.; Dzedzickis, A.
        Piezoelectric Effect of k-Carrageenan as a Tool for Force Sensor.
        Sensors 2025, 25, 4594. https://doi.org/10.3390/s25154594

        Liu, X., Du, L., Ma, Y., Li, T., Chen, S., Yang, J., Ran, Z., Zhou, L., Dong, Q.,
        Zheng, W., Jiang, Z. Highly conductive and stable double network carrageenan
        organohydrogels for advanced strain sensing and signal recognition arrays.

    Args:
        r: Live sensor resistance :math:`R` [Ω].
        r0: Un-stretched baseline resistance :math:`R_0` [Ω], at t = 0.
        gf: Gauge factor :math:`GF` [unitless].
        k1: Pressure-strain scaling :math:`k_1` [mmHg/strain].
        icp_baseline: :math:`\text{ICP}_{\text{baseline}}` [mmHg].

    Returns:
        ``param``, ``strain_pct``, ``icp_mmhg``, ``status``, ``action``.
        Status is the worst of the ICP and strain thresholds.
    """
    strain = ((r - r0) / r0) / gf  # fraction, 0.0143 = 1.43%
    icp = k1 * strain + icp_baseline  # mmHg
    pct = strain * 100

    if icp > 18.0 or pct > 1.8:
        status, action = (
            Status.CRITICAL,
            "Mandatory 45-min LBNP, restrict high-sodium rations, alert flight surgeon",
        )
    elif icp >= 12.0 or pct >= 1.1:
        status, action = Status.WARNING, "Engage LBNP at -35 mmHg for 20 min"
    else:
        status, action = Status.NOMINAL, "Baseline microgravity adaptation"

    return {
        "param": "1.1",
        "strain_pct": round(pct, 3),
        "icp_mmhg": round(icp, 2),
        "status": status,
        "action": action,
    }


def troponin_1_2(
    ctni_ng_ml: float,
    n_b: float = 2.5e14,
    eps_r: float = 78.4,
    delta: float = 3.5e-9,
    lambda_d: float = 1.0e-9,
) -> TroponinResult:
    r"""
    Parameter 1.2: Cardiac Troponin I (cTnI), myocardial strain & ischemia (GFET array).

    GFET threshold voltage shift (surface charge model):
        \Delta V_t = \frac{q \cdot N_b}{\epsilon_r \cdot \epsilon_0} \cdot \delta \cdot \left(1 - \frac{\delta}{2 \lambda_D}\right)

    References:
        Lakshmanakumar, M., Nesakumar, N., Sethuraman, S. et al. Functionalized Graphene
        Quantum Dot Interfaced Electrochemical Detection of Cardiac Troponin I: An Antibody
        Free Approach. Sci Rep 9, 17348 (2019). https://doi.org/10.1038/s41598-019-53979-5

    Args:
        ctni_ng_ml: Troponin concentration :math:`[\text{cTnI}]` [ng/mL]; the spec
            gives no N_b -> concentration conversion, so it is passed in directly.
        n_b: Bound biomarker surface density :math:`N_b` [molecules/m^2].
        eps_r: Relative permittivity of the bio-fluid interface :math:`\epsilon_r` [unitless].
        delta: Molecular binding layer height :math:`\delta` [m].
        lambda_d: Debye screening length :math:`\lambda_D` [m], 0.8-1.2 nm.

    Returns:
        ``param``, ``delta_vt_mv``, ``ctni_ng_ml``, ``status``, ``action``.
        Status comes from cTnI; a shift of 1.2 mV or more is at least WARNING.
    """
    q = 1.602e-19  # elementary charge [C]
    eps_0 = 8.854e-12  # vacuum permittivity [F/m]

    delta_vt = (q * n_b) / (eps_r * eps_0) * delta * (1 - delta / (2 * lambda_d))  # V
    # with delta > 2*lambda_d the bracket goes negative, so compare the magnitude
    vt_mv = abs(delta_vt) * 1000

    if ctni_ng_ml > 0.04:
        status, action = (
            Status.CRITICAL,
            "Immediate EVA termination protocol, initiate tele-medical ECG evaluation",
        )
    elif ctni_ng_ml >= 0.01 or vt_mv >= 1.2:
        status, action = (
            Status.WARNING,
            "Flag workload elevation, increase EVA cooling flow rate",
        )
    else:
        status, action = Status.NOMINAL, "Healthy cardiac function"

    return {
        "param": "1.2",
        "delta_vt_mv": round(vt_mv, 3),
        "ctni_ng_ml": ctni_ng_ml,
        "status": status,
        "action": action,
    }


def blood_pressure_heart_rate_1_3(
    ptt_ms: float,
    dt_peak_peak_s: float,
    a: float = -45.2,
    b: float = 280.5,
) -> BpHrResult:
    r"""
    Parameter 1.3: Continuous blood pressure (BP) & heart rate (HR) (hydrogel pulse patches + dry ECG).

    Mean arterial pressure from pulse transit time:
        \text{MAP} = a \cdot \ln(\text{PTT}) + b

    Heart rate from peak-to-peak interval:
        \text{HR (BPM)} = \frac{60}{\Delta t_{\text{peak-peak}}}

    References:
        Liu, T., Hu, X., Wang, D., Shi, W., Xing, D., You, C., Xu, T., Tian, M., Qu, L.,
        Zhang, X. Flexible dry electrodes for electrocardiographic monitoring: Working
        principles, design strategies, and recent advances. iScience.

    Args:
        ptt_ms: Pulse transit time neck -> wrist :math:`\text{PTT}` [ms].
        dt_peak_peak_s: Time between consecutive systolic peaks
            :math:`\Delta t_{\text{peak-peak}}` [s].
        a: Arterial stiffness scaling factor :math:`a` [mmHg/ms].
        b: Baseline pressure offset :math:`b` [mmHg].

    Returns:
        ``param``, ``map_mmhg``, ``hr_bpm``, ``status``, ``action``.
        Nominal needs MAP 70-100 mmHg and HR 50-90 BPM. The spec defines no
        CRITICAL level and only high-side warnings, so anything above either
        nominal range is WARNING (this fills the MAP 100-110 and HR 90-100 gaps
        and covers HR > 120). Low MAP or low HR has no protocol: UNSPECIFIED,
        unless the other metric is WARNING.
    """
    map_mmhg = a * math.log(ptt_ms) + b
    hr_bpm = 60 / dt_peak_peak_s

    if map_mmhg > 100 or hr_bpm > 90:
        status, action = (
            Status.WARNING,
            "Adjust cabin temperature, re-balance hydration schedule",
        )
    elif map_mmhg < 70 or hr_bpm < 50:
        status, action = Status.UNSPECIFIED, "No protocol defined in spec"
    else:
        status, action = Status.NOMINAL, "Normal baseline"

    return {
        "param": "1.3",
        "map_mmhg": round(map_mmhg, 2),
        "hr_bpm": round(hr_bpm, 1),
        "status": status,
        "action": action,
    }
