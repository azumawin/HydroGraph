"""Sensor channels: what a single reading is, and how it is graded on its own.

A channel is one value the device sends (``"spo2"``, ``"heart_rate"``, ...),
matching the simulator's channel registry (``docs/backend-integration.md``).
Values arrive in the SI wire ``unit`` of :data:`CHANNELS`; boolean channels
send ``True`` / ``False``.

:func:`evaluate_reading` grades one value. Thresholds come from the master
plan's Tier 1 cutoffs where it gives one for that channel, otherwise from
``NSA_hydrograph.md``, converted from the spec's unit in each ``case``. A
channel or side neither document addresses is ``"unspecified"``.

The 10 findings in :mod:`hydrograph_core.findings` combine several channels;
this module grades each channel alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal, TypedDict

from .environments import EnvironmentInfo

Evaluation = Literal["nominal", "warning", "critical", "unspecified"]
"""Grade of one reading. ``unspecified``: the specs give no cutoff for it."""


class Display(TypedDict):
    """How to show a reading: ``value * scale + offset``, in ``unit``.

    The spec's clinical unit (mmHg, bpm, °C, ...); ``""`` for booleans and
    dimensionless ratios.
    """

    unit: str
    scale: float
    offset: float


def _display(unit: str, scale: float = 1.0, offset: float = 0.0) -> Display:
    return {"unit": unit, "scale": scale, "offset": offset}


class ChannelInfo(TypedDict):
    name: str
    unit: str
    display: Display
    value_type: Literal["number", "boolean", "enum"]
    scope: Literal["crew", "environment"]
    body_regions: tuple[str, ...]
    explanation: str


def _crew(
    name: str,
    unit: str,
    display: Display,
    body_regions: tuple[str, ...],
    explanation: str,
) -> ChannelInfo:
    return {
        "name": name,
        "unit": unit,
        "display": display,
        "value_type": (
            "enum" if unit == "ACVPU" else "boolean" if unit == "boolean" else "number"
        ),
        "scope": "crew",
        "body_regions": body_regions,
        "explanation": explanation,
    }


def _environment(
    name: str, unit: str, display: Display, explanation: str
) -> ChannelInfo:
    return {
        "name": name,
        "unit": unit,
        "display": display,
        "value_type": (
            "enum" if unit == "ACVPU" else "boolean" if unit == "boolean" else "number"
        ),
        "scope": "environment",
        "body_regions": (),
        "explanation": explanation,
    }


CHANNELS: Final[Mapping[str, ChannelInfo]] = MappingProxyType(
    {
        "consciousness_level": _crew(
            "Consciousness", "ACVPU", _display(""), ("head",), "Configured ACVPU state"
        ),
        "supplemental_o2": _crew(
            "Supplemental oxygen",
            "boolean",
            _display(""),
            ("chest",),
            "Explicit oxygen context",
        ),
        "post_ared_exercise_window": _crew(
            "Post-ARED window", "boolean", _display(""), (), "Explicit exercise context"
        ),
        "il6_pg_mL": _crew(
            "Synthetic GFET IL-6",
            "kg/m^3",
            _display("pg/mL", 1e9),
            (),
            "Synthetic interstitial concentration; provisional threshold",
        ),
        "heart_rate": _crew(
            "Heart rate",
            "s^-1",
            _display("bpm", 60.0),
            ("heart", "chest"),
            (
                "Resting heart rate above 90 bpm signals vascular stress, dehydration "
                "or infection."
            ),
        ),
        "hrv_rmssd": _crew(
            "Heart rate variability (RMSSD)",
            "s",
            _display("ms", 1e3),
            ("heart", "chest"),
            (
                "Beat-to-beat variation; falls with stress and fatigue. The specs give "
                "no cutoff."
            ),
        ),
        "bp_systolic": _crew(
            "Blood pressure (systolic)",
            "Pa",
            _display("mmHg", 1 / 133.322),
            ("heart", "chest"),
            (
                "A systolic drop of 20 mmHg or more on standing marks orthostatic "
                "intolerance after time in reduced gravity."
            ),
        ),
        "bp_diastolic": _crew(
            "Blood pressure (diastolic)",
            "Pa",
            _display("mmHg", 1 / 133.322),
            ("heart", "chest"),
            (
                "A diastolic drop of 10 mmHg or more on standing marks orthostatic "
                "intolerance after time in reduced gravity."
            ),
        ),
        "spo2": _crew(
            "Blood oxygen saturation",
            "1",
            _display("%", 100.0),
            ("chest",),
            (
                "Below 94 % is low and below 90 % is critical hypoxemia; check the CO2 "
                "scrubber and module ventilation."
            ),
        ),
        "body_temperature": _crew(
            "Core body temperature",
            "K",
            _display("°C", 1.0, -273.15),
            ("head", "neck"),
            (
                "Above 38.0 °C or below 36.0 °C meets the SIRS fever or hypothermia "
                "criterion for acute infection."
            ),
        ),
        "respiratory_rate": _crew(
            "Respiratory rate",
            "s^-1",
            _display("/min", 60.0),
            ("chest",),
            (
                "A rising rate is an early sign of hypoxia or CO2 exposure. The specs "
                "give no cutoff."
            ),
        ),
        "glucose": _crew(
            "Blood glucose",
            "mol/m^3",
            _display("mmol/L"),
            (),
            (
                "Below 3.9 mmol/L is level 1 hypoglycemia and below 3.0 mmol/L level 2; "
                "a sign of negative energy balance."
            ),
        ),
        "cortisol_saliva": _crew(
            "Salivary cortisol",
            "mol/m^3",
            _display("nmol/L", 1e6),
            (),
            (
                "Stress hormone; the diurnal slope tracks behavioral health. The specs' "
                "cutoffs are for time-normalized interstitial fluid, not saliva."
            ),
        ),
        "troponin_i": _crew(
            "Cardiac troponin I",
            "kg/m^3",
            _display("ng/mL", 1e6),
            ("heart", "chest"),
            "Above 0.04 ng/mL indicates heart muscle injury; restrict EVA.",
        ),
        "lactate": _crew(
            "Blood lactate",
            "mol/m^3",
            _display("mmol/L"),
            (),
            "Resting lactate above 4.0 mmol/L signals negative energy balance.",
        ),
        "urinary_ntx": _crew(
            "Urinary NTx",
            "mol BCE/mol creatinine",
            _display("nmol BCE/mmol creatinine", 1e6),
            (
                "pelvis",
                "left_thigh",
                "right_thigh",
                "left_lower_leg",
                "right_lower_leg",
            ),
            (
                "Bone breakdown marker; graded through its change from baseline "
                "(NTx change from baseline)."
            ),
        ),
        "bone_ntx_pct_baseline": _crew(
            "NTx change from baseline",
            "1",
            _display("%", 100.0),
            (
                "pelvis",
                "left_thigh",
                "right_thigh",
                "left_lower_leg",
                "right_lower_leg",
            ),
            (
                "A rise of more than 25 % over the preflight baseline signals bone "
                "demineralization."
            ),
        ),
        "vitamin_d_25oh": _crew(
            "Vitamin D (25-OH)",
            "mol/m^3",
            _display("nmol/L", 1e6),
            (),
            "Supports bone health; the specs track its trend, with no cutoff.",
        ),
        "il6_serum": _crew(
            "Interleukin-6",
            "kg/m^3",
            _display("pg/mL", 1e9),
            (),
            (
                "Inflammation marker; above 3.0 pg/mL outside the 2 h after exercise "
                "suggests infection."
            ),
        ),
        "sweat_sodium_concentration": _crew(
            "Sweat sodium",
            "mol/m^3",
            _display("mmol/L"),
            (),
            (
                "Local electrolyte loss, tracked against the crew member's own "
                "baseline. The specs give no cutoff."
            ),
        ),
        "sweat_sodium_flux": _crew(
            "Sweat sodium loss rate",
            "mol/s",
            _display("mmol/h", 3.6e6),
            (),
            (
                "Local electrolyte loss rate, tracked against the crew member's own "
                "baseline. The specs give no cutoff."
            ),
        ),
        "whole_body_sweat_rate": _crew(
            "Whole-body sweat fixture",
            "m^3/s",
            _display("L/h", 3.6e6),
            (),
            "Synthetic whole-body flow; not a local patch measurement or graded threshold.",
        ),
        "sweat_rate": _crew(
            "Sweat rate",
            "m^3/s",
            _display("L/h", 3.6e6),
            (),
            (
                "Local sweat flow, tracked against the crew member's own baseline. The "
                "specs give no cutoff."
            ),
        ),
        "viral_ebv_detected": _crew(
            "EBV reactivation",
            "boolean",
            _display(""),
            (),
            "Latent Epstein-Barr virus shedding signals immune dysregulation.",
        ),
        "viral_vzv_detected": _crew(
            "VZV reactivation",
            "boolean",
            _display(""),
            (),
            "Latent varicella-zoster virus shedding signals immune dysregulation.",
        ),
        "viral_cmv_detected": _crew(
            "CMV reactivation",
            "boolean",
            _display(""),
            (),
            "Latent cytomegalovirus shedding signals immune dysregulation.",
        ),
        "body_mass": _crew(
            "Body mass",
            "kg",
            _display("kg"),
            (),
            (
                "Acute loss over 2 % of baseline signals dehydration; graded against "
                "baseline, so not on its own."
            ),
        ),
        "urine_specific_gravity": _crew(
            "Urine specific gravity",
            "1",
            _display(""),
            ("abdomen",),
            (
                "Above 1.020 signals dehydration; drink the fluid deficit within 30 "
                "minutes."
            ),
        ),
        "urine_volume_24h": _crew(
            "Urine volume (24 h)",
            "m^3",
            _display("L", 1e3),
            ("abdomen",),
            "Below 2.0 L/day raises kidney stone risk alongside bone loss.",
        ),
        "eeg_cfe_ratio": _crew(
            "Cognitive fatigue (EEG theta/alpha)",
            "1",
            _display(""),
            ("head",),
            (
                "Prefrontal EEG theta/alpha power ratio; 0.70-1.20 is fatigued and "
                "above 1.20 severely fatigued."
            ),
        ),
        "jugular_strain_pct": _crew(
            "Jugular strain",
            "1",
            _display("%", 100.0),
            ("neck",),
            (
                "Neck-patch strain from cephalic fluid shift; above 1.1 % signals "
                "the SANS fluid shift, above 1.8 % optic nerve compression risk."
            ),
        ),
        "delta_R_over_R0": _crew(
            "Neck-patch resistance change",
            "1",
            _display(""),
            ("neck",),
            (
                "Raw hydrogel signal behind jugular strain (gauge factor times "
                "strain). The specs give no cutoff."
            ),
        ),
        "icp_risk_indicator_mmHg": _crew(
            "Intracranial pressure indicator",
            "Pa",
            _display("mmHg", 1 / 133.322),
            ("head",),
            (
                "Estimated from neck strain; 12-18 mmHg is moderate and above "
                "18 mmHg high SANS optic nerve compression risk."
            ),
        ),
        "visual_acuity_logmar": _crew(
            "Visual acuity (LogMAR)",
            "1",
            _display("logMAR"),
            ("head",),
            (
                "On-screen eye test result; higher is worse. The specs give no "
                "cutoff."
            ),
        ),
        "amsler_grid_distortion": _crew(
            "Amsler grid distortion",
            "boolean",
            _display(""),
            ("head",),
            (
                "Distorted lines on the on-screen Amsler grid can signal retinal "
                "changes from SANS. The specs give no grading."
            ),
        ),
        "ambient_ppco2": _environment(
            "Cabin CO2 partial pressure",
            "Pa",
            _display("mmHg", 1 / 133.322),
            (
                "Above 3.0 mmHg (about 4,000 ppm) causes headaches and impairs "
                "performance in closed habitats."
            ),
        ),
        "ambient_light_lux": _environment(
            "Cabin light level",
            "lx",
            _display("lx"),
            "Light exposure drives the circadian rhythm. The specs give no cutoff.",
        ),
        "ambient_dose_rate": _environment(
            "Radiation dose rate",
            "Sv/s",
            _display("µSv/h", 3.6e9),
            (
                "A spike above 50 µSv/h can mean a solar particle event; move to the "
                "shielded storm shelter."
            ),
        ),
        "ambient_integrated_dose": _environment(
            "Cumulative radiation dose",
            "Sv",
            _display("mSv", 1e3),
            (
                "Mission dose so far; above the 600 mSv career limit, review radiation "
                "exposure."
            ),
        ),
        "spe_flag": _environment(
            "Solar particle event",
            "boolean",
            _display(""),
            (
                "An active solar particle event; move to the shielded storm shelter "
                "immediately."
            ),
        ),
    }
)


def evaluate_reading(
    channel: str, value: float | bool | str, *, environment: EnvironmentInfo
) -> Evaluation:
    """Grade one reading of one channel on its own.

    Args:
        channel: A key of :data:`CHANNELS`.
        value: The reading in the channel's SI wire ``unit``; ``True`` /
            ``False`` for boolean channels.
        environment: The mission environment in effect; only the dose rate
            depends on it (graded above its ``baseline_dose_rate_usv_h``).

    Returns:
        The reading's grade. Sources, unit conversions and boundary choices
        are commented per channel.

    Raises:
        ValueError: ``channel`` is not in :data:`CHANNELS`.
    """
    if channel == "consciousness_level":
        if value not in ("ALERT", "CONFUSION", "VOICE", "PAIN", "UNRESPONSIVE"):
            raise ValueError("invalid ACVPU state")
        return "unspecified"
    if isinstance(value, str):
        raise TypeError("numeric/boolean channel cannot contain text")
    if channel in {"supplemental_o2", "post_ared_exercise_window", "il6_pg_mL"}:
        return "unspecified"
    match channel:
        case "heart_rate":
            # NSA 1.3: nominal 50-90 bpm, warning 100-120; 90-100 and > 120
            # take the nearest defined band (warning). Below 50 not addressed.
            bpm = value * 60.0
            if bpm < 50.0:
                return "unspecified"
            if bpm <= 90.0:
                return "nominal"
            return "warning"
        case "spo2":
            # Master plan Finding 4: < 94 % warning, < 90 % critical hypoxemia.
            pct = value * 100.0
            if pct < 90.0:
                return "critical"
            if pct < 94.0:
                return "warning"
            return "nominal"
        case "body_temperature":
            # Master plan Finding 3 (SIRS): > 38.0 or < 36.0 degC. It wins over
            # NSA 2.2's narrower 36.5-37.5 nominal band, so 36.0-38.0 is nominal.
            celsius = value - 273.15
            if celsius > 38.0 or celsius < 36.0:
                return "warning"
            return "nominal"
        case "glucose":
            # Master plan Finding 7: Level 1 < 3.9 mM (70 mg/dL), Level 2
            # < 3.0 mM (54 mg/dL), critical as NSA 2.1 grades its lowest band.
            # NSA 2.1 nominal tops out at 7.0 mM; hyperglycemia not addressed.
            # mol/m^3 equals mmol/L.
            if value < 3.0:
                return "critical"
            if value < 3.9:
                return "warning"
            if value <= 7.0:
                return "nominal"
            return "unspecified"
        case "troponin_i":
            # Master plan Finding 1: event-triggered hs-cTnI > 0.04 ng/mL
            # critical. 1 kg/m^3 = 1e6 ng/mL.
            ng_ml = value * 1e6
            return "critical" if ng_ml > 0.04 else "nominal"
        case "lactate":
            # Master plan Finding 7: resting lactate > 4.0 mM. mol/m^3 = mmol/L.
            return "warning" if value > 4.0 else "nominal"
        case "bone_ntx_pct_baseline":
            # Master plan Finding 8: NTx > +25 % over preflight baseline. The
            # wire value is the fractional change (0.25 = +25 %).
            return "warning" if value > 0.25 else "nominal"
        case "il6_serum":
            # Master plan Finding 3: IL-6 > 3.0 pg/mL. The 2 h post-ARED gate
            # needs exercise context a single reading lacks; the finding applies
            # it. 1 kg/m^3 = 1e9 pg/mL.
            pg_ml = value * 1e9
            return "warning" if pg_ml > 3.0 else "nominal"
        case "viral_ebv_detected" | "viral_vzv_detected" | "viral_cmv_detected":
            # Master plan Finding 3: latent herpesvirus reactivation.
            return "warning" if value else "nominal"
        case "urine_specific_gravity":
            # Master plan Finding 2: USG > 1.020.
            return "warning" if value > 1.020 else "nominal"
        case "urine_volume_24h":
            # Master plan Finding 8: urine volume < 2.0 L/day. 1 m^3 = 1000 L.
            litres = value * 1000.0
            return "warning" if litres < 2.0 else "nominal"
        case "eeg_cfe_ratio":
            # Master plan Finding 5 (and NSA 4.2): CFE 0.70-1.20 warning,
            # > 1.20 critical.
            if value > 1.20:
                return "critical"
            if value >= 0.70:
                return "warning"
            return "nominal"
        case "jugular_strain_pct":
            # Master plan Finding 9: 1.1-1.8 % warning, > 1.8 % critical. The
            # wire value is a fraction (0.0155 = 1.55 %). Rounded so float noise
            # cannot move an exact boundary (0.011 * 100 = 1.0999...).
            pct = round(value * 100.0, 9)
            if pct > 1.8:
                return "critical"
            if pct >= 1.1:
                return "warning"
            return "nominal"
        case "icp_risk_indicator_mmHg":
            # NSA 1.1: nominal < 12.0 mmHg, warning 12.0-18.0, critical > 18.0.
            mmhg = value / 133.322
            if mmhg > 18.0:
                return "critical"
            if mmhg >= 12.0:
                return "warning"
            return "nominal"
        case "ambient_ppco2":
            # Master plan Finding 4: ppCO2 > 3.0 mmHg. 1 mmHg = 133.322 Pa.
            mmhg = value / 133.322
            return "warning" if mmhg > 3.0 else "nominal"
        case "ambient_dose_rate":
            # Master plan Finding 10: dose-rate spike > 50 uSv/h warning, applied
            # above the environment's own background: the lunar and Mars-transit
            # baselines alone exceed 50 uSv/h. 1 Sv/s = 3.6e9 uSv/h.
            usv_h = value * 3.6e9
            spike = usv_h - environment["baseline_dose_rate_usv_h"]
            return "warning" if spike > 50.0 else "nominal"
        case "ambient_integrated_dose":
            # Master plan Finding 10: cumulative dose > 600 mSv career limit.
            msv = value * 1000.0
            return "warning" if msv > 600.0 else "nominal"
        case "spe_flag":
            # Master plan Finding 10: an SPE is an immediate shelter alert.
            return "critical" if value else "nominal"
        case (
            "hrv_rmssd"
            | "bp_systolic"
            | "bp_diastolic"
            | "respiratory_rate"
            | "cortisol_saliva"
            | "urinary_ntx"
            | "vitamin_d_25oh"
            | "sweat_sodium_concentration"
            | "sweat_sodium_flux"
            | "sweat_rate"
            | "whole_body_sweat_rate"
            | "body_mass"
            | "ambient_light_lux"
            | "delta_R_over_R0"
            | "visual_acuity_logmar"
            | "amsler_grid_distortion"
        ):
            # No single-reading cutoff in either document: graded against a
            # baseline or trend (body mass, sweat, NTx, vitamin D), only inside
            # a finding (BP, respiratory rate), for another specimen (cortisol
            # cutoffs are for normalized ISF), or not at all (HRV, light,
            # resistance change, visual acuity, Amsler grid).
            return "unspecified"
        case _:
            raise ValueError(f'Unknown channel "{channel}".')
