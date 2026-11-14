"""Master plan section 5: standard JSON telemetry payload."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypedDict

from .domain_1 import IcpResult, TroponinResult
from .domain_2 import GlucoseResult, TemperatureResult
from .domain_3 import JointResult
from .domain_4 import CfeResult, CortisolResult
from .gauge_factor import GaugeFactorResult
from .shared import Status


class StandardVitals(TypedDict):
    heart_rate_bpm: float
    blood_pressure_sys_mmHg: float
    blood_pressure_dia_mmHg: float
    respiratory_rate_br_min: float
    spo2_pct: float
    blood_glucose_mg_dL: float
    zhf_core_temp_celsius: float
    news2_aggregate_score: int
    cabin_ppco2_mmHg: float


class CarrageenanHydrogel(TypedDict):
    displacement_mm: float
    strain_percentage: float
    dynamic_gauge_factor: float
    delta_R_over_R0: float
    jugular_fluid_shift_pct: float
    estimated_icp_mmHg: float


class GrapheneGfet(TypedDict):
    isf_cortisol_nM: float
    cortisol_diurnal_slope_status: str
    bone_ntx_pct_baseline: float
    il6_pg_mL: float
    post_ared_exercise_window: bool
    latent_virus_shedding: str
    hs_troponin_ng_mL: float
    delta_Ids_over_I0: float
    eeg_theta_alpha_ratio: float


class AdvancedBiotransduction(TypedDict):
    carrageenan_hydrogel: CarrageenanHydrogel
    graphene_gfet: GrapheneGfet


class CopilotDecision(TypedDict):
    overall_status: str
    primary_hazard: str
    recommended_actions: list[str]


class TelemetryPayload(TypedDict):
    timestamp: str
    user_state: str
    standard_vitals: StandardVitals
    advanced_biotransduction: AdvancedBiotransduction
    kinematics_3d_dummy: dict[str, float | str]
    copilot_decision_engine: CopilotDecision


def telemetry_payload(
    *,
    timestamp: str,
    user_state: str,
    heart_rate_bpm: float,
    bp_systolic_mmhg: float,
    bp_diastolic_mmhg: float,
    respiratory_rate_br_min: float,
    spo2_pct: float,
    glucose: GlucoseResult,
    temperature: TemperatureResult,
    news2_score: int,
    cabin_ppco2_mmhg: float,
    gauge: GaugeFactorResult,
    icp: IcpResult,
    cortisol: CortisolResult,
    cortisol_di_ds_ratio: float,
    cortisol_slope_status: Status,
    ntx_change_pct: float,
    il6_pg_ml: float,
    post_ared_window: bool,
    latent_virus_shedding: str,
    troponin: TroponinResult,
    cfe: CfeResult,
    joint_angles_deg: Mapping[str, float],
    form: JointResult,
    form_joint: str,
    others: Sequence[Mapping[str, object]] = (),
) -> TelemetryPayload:
    r"""
    Section 5: Verified JSON telemetry payload.

    References:
        None given in the plan for the payload.

    Args:
        timestamp: ISO-8601 UTC time of the readings, e.g.
            ``"2026-11-01T12:00:00Z"``; the backend supplies it.
        user_state: ``"ACTIVE"``, ``"RESTING"`` or ``"SLEEPING"`` (the
            backend's stored ``hydrogfn.polling.UserState`` value).
        heart_rate_bpm: Heart rate [bpm].
        bp_systolic_mmhg: Systolic blood pressure [mmHg].
        bp_diastolic_mmhg: Diastolic blood pressure [mmHg].
        respiratory_rate_br_min: Respiratory rate [breaths/min].
        spo2_pct: Peripheral oxygen saturation [%].
        glucose: Result of :func:`hydrogfn.glucose_2_1`.
        temperature: Result of :func:`hydrogfn.core_temperature_2_2`.
        news2_score: Aggregate NEWS2 score [0-20].
        cabin_ppco2_mmhg: Ambient CO2 partial pressure [mmHg].
        gauge: Result of :func:`hydrogfn.gauge_factor.dynamic_gauge_factor`.
        icp: Result of :func:`hydrogfn.cephalic_fluid_shift_1_1`; its
            ``strain_pct`` is the jugular fluid shift.
        cortisol: Result of :func:`hydrogfn.cortisol_4_1`.
        cortisol_di_ds_ratio: The :math:`\Delta I_{ds} / I_0` reading passed
            to ``cortisol_4_1`` [unitless].
        cortisol_slope_status: Status of the diurnal cortisol degradation
            slope, evaluated upstream from the cortisol series.
        ntx_change_pct: Bone NTx change from the preflight baseline [%].
        il6_pg_ml: GFET IL-6 concentration [pg/mL].
        post_ared_window: Within 2 h after an ARED workout.
        latent_virus_shedding: Latent virus shedding result, passed through
            (the plan's example: ``"NO_DETECT"``).
        troponin: Result of :func:`hydrogfn.troponin_1_2`.
        cfe: Result of :func:`hydrogfn.cognitive_fatigue_4_2`.
        joint_angles_deg: Joint angles for the 3D dummy, keyed without the
            unit, e.g. ``{"left_knee_flexion": 112.4}`` [deg].
        form: Result of :func:`hydrogfn.joint_kinematics_3_2` for the joint
            pair that sets the form status.
        form_joint: Name of that joint pair, e.g. ``"lumbar"``.
        others: Any further parameter or finding results evaluated this tick
            (``blood_pressure_heart_rate_1_3``, ``hydrogfn.findings``, ...).

    Returns:
        The p.8 payload. Statuses are upper case as in the plan's example
        (``"WARNING"``). ``copilot_decision_engine`` is derived from every
        result passed (``glucose`` ... ``form`` and ``others``):

        - ``overall_status`` is the worst status, in the order CRITICAL >
          WARNING > UNSPECIFIED > NOMINAL.
        - ``primary_hazard`` joins the names of the results at that status
          with " + ", in argument order; ``"None"`` when all are nominal.
        - ``recommended_actions`` numbers the actions of every non-nominal,
          non-unspecified result, worst first, without duplicates.

        Apply ``hydrogfn.polling.alert_allowed`` before passing results in: a result
        left out is neither a hazard nor an action. ``delta_Ids_over_I0`` is
        the cortisol channel; the plan's example does not say which GFET it
        is. ``blood_glucose_mg_dL`` uses 1 mM = 18 mg/dL, as in
        ``glucose_2_1``.
    """
    # parameter / finding id -> hazard name for primary_hazard
    names = {
        "1.1": "SANS Jugular Fluid Shift",
        "1.2": "Myocardial Strain",
        "1.3": "Blood Pressure / Heart Rate",
        "2.1": "Glucose",
        "2.2": "Core Temperature",
        "3.1": "Bone Resorption",
        "3.2": "Exercise Form Asymmetry",
        "4.1": "Cortisol Stress",
        "4.2": "Cognitive Fatigue",
        "4.3": "Sleep & Mood",
        "5.1": "Inflammation",
        "F1": "Orthostatic Intolerance",
        "F2": "Dehydration",
        "F3": "Acute Infection",
        "F4": "Hypoxia & CO2",
        "F5": "Sleep Deficiency",
        "F6": "Behavioral Health Decline",
        "F7": "Negative Energy Balance",
        "F8": "Bone Demineralization & Renal Stone Risk",
        "F9": "SANS & Cephalic Fluid Shift",
        "F10": "Radiation Exposure",
    }
    rank = {
        Status.CRITICAL: 3,
        Status.WARNING: 2,
        Status.UNSPECIFIED: 1,
        Status.NOMINAL: 0,
    }

    results: list[Mapping[str, object]] = [
        glucose,
        temperature,
        icp,
        cortisol,
        troponin,
        cfe,
        form,
        *others,
    ]
    rated: list[tuple[int, str, str]] = []
    for result in results:
        status = Status(result["status"])
        key = f"F{result['finding']}" if "finding" in result else str(result["param"])
        rated.append((rank[status], names[key], str(result["action"])))

    worst = max(r[0] for r in rated)
    overall = next(s for s, n in rank.items() if n == worst)
    hazards = [name for r, name, _ in rated if r == worst]
    actions: list[str] = []
    for r, _, action in sorted(rated, key=lambda x: -x[0]):
        if r >= rank[Status.WARNING] and action not in actions:
            actions.append(action)

    kinematics: dict[str, float | str] = {
        f"{joint}_deg": angle for joint, angle in joint_angles_deg.items()
    }
    kinematics[f"{form_joint}_asymmetry_ratio"] = form["asymmetry_ratio"]
    kinematics["form_status"] = Status(form["status"]).name

    return {
        "timestamp": timestamp,
        "user_state": user_state,
        "standard_vitals": {
            "heart_rate_bpm": heart_rate_bpm,
            "blood_pressure_sys_mmHg": bp_systolic_mmhg,
            "blood_pressure_dia_mmHg": bp_diastolic_mmhg,
            "respiratory_rate_br_min": respiratory_rate_br_min,
            "spo2_pct": spo2_pct,
            "blood_glucose_mg_dL": glucose["glucose_mg_dl"],
            "zhf_core_temp_celsius": temperature["temperature_c"],
            "news2_aggregate_score": news2_score,
            "cabin_ppco2_mmHg": cabin_ppco2_mmhg,
        },
        "advanced_biotransduction": {
            "carrageenan_hydrogel": {
                "displacement_mm": gauge["displacement_mm"],
                "strain_percentage": gauge["strain_pct"],
                "dynamic_gauge_factor": gauge["gauge_factor"],
                "delta_R_over_R0": gauge["delta_r_over_r0"],
                "jugular_fluid_shift_pct": icp["strain_pct"],
                "estimated_icp_mmHg": icp["icp_mmhg"],
            },
            "graphene_gfet": {
                "isf_cortisol_nM": cortisol["cortisol_nm"],
                "cortisol_diurnal_slope_status": Status(cortisol_slope_status).name,
                "bone_ntx_pct_baseline": ntx_change_pct,
                "il6_pg_mL": il6_pg_ml,
                "post_ared_exercise_window": post_ared_window,
                "latent_virus_shedding": latent_virus_shedding,
                "hs_troponin_ng_mL": troponin["ctni_ng_ml"],
                "delta_Ids_over_I0": cortisol_di_ds_ratio,
                "eeg_theta_alpha_ratio": cfe["cfe_ratio"],
            },
        },
        "kinematics_3d_dummy": kinematics,
        "copilot_decision_engine": {
            "overall_status": overall.name,
            "primary_hazard": " + ".join(hazards) if worst > 0 else "None",
            "recommended_actions": [f"{i}. {a}" for i, a in enumerate(actions, 1)],
        },
    }
