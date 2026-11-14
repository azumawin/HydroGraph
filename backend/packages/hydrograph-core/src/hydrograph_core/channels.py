"""Sensor channels: what a single reading is, and how it is graded on its own.

A channel is one value the device sends (``"spo2"``, ``"heart_rate"``, ...),
matching the simulator's channel registry (``docs/backend-integration.md``).
Values arrive in the SI wire ``unit`` of :data:`CHANNELS`; boolean channels
send ``True`` / ``False``.

:func:`evaluate_reading` grades one value. Thresholds come from the master
plan's Tier 1 cutoffs where it gives one for that channel, otherwise from
``NSA_hydrograph.md``, converted from the spec's unit in each ``case``. A
channel or side neither document addresses is ``Status.UNSPECIFIED``.

The 10 findings in :mod:`hydrograph_core.findings` combine several channels;
this module grades each channel alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal, TypedDict

from .shared import Status


class ChannelInfo(TypedDict):
    name: str
    unit: str
    value_type: Literal["number", "boolean"]
    scope: Literal["crew", "environment"]
    body_regions: tuple[str, ...]
    explanation: str


def _crew(
    name: str, unit: str, body_regions: tuple[str, ...], explanation: str
) -> ChannelInfo:
    return {
        "name": name,
        "unit": unit,
        "value_type": "boolean" if unit == "boolean" else "number",
        "scope": "crew",
        "body_regions": body_regions,
        "explanation": explanation,
    }


def _environment(name: str, unit: str, explanation: str) -> ChannelInfo:
    return {
        "name": name,
        "unit": unit,
        "value_type": "boolean" if unit == "boolean" else "number",
        "scope": "environment",
        "body_regions": (),
        "explanation": explanation,
    }


CHANNELS: Final[Mapping[str, ChannelInfo]] = MappingProxyType(
    {
        "heart_rate": _crew(
            "Heart rate",
            "s^-1",
            ("heart",),
            (
                "Resting heart rate above 90 bpm signals vascular stress, dehydration "
                "or infection."
            ),
        ),
        "hrv_rmssd": _crew(
            "Heart rate variability (RMSSD)",
            "s",
            ("heart",),
            (
                "Beat-to-beat variation; falls with stress and fatigue. The specs give "
                "no cutoff."
            ),
        ),
        "bp_systolic": _crew(
            "Blood pressure (systolic)",
            "Pa",
            ("heart", "chest"),
            (
                "A systolic drop of 20 mmHg or more on standing marks orthostatic "
                "intolerance after time in reduced gravity."
            ),
        ),
        "bp_diastolic": _crew(
            "Blood pressure (diastolic)",
            "Pa",
            ("heart", "chest"),
            (
                "A diastolic drop of 10 mmHg or more on standing marks orthostatic "
                "intolerance after time in reduced gravity."
            ),
        ),
        "spo2": _crew(
            "Blood oxygen saturation",
            "1",
            ("lungs",),
            (
                "Below 94 % is low and below 90 % is critical hypoxemia; check the CO2 "
                "scrubber and module ventilation."
            ),
        ),
        "body_temperature": _crew(
            "Core body temperature",
            "K",
            ("head", "torso"),
            (
                "Above 38.0 °C or below 36.0 °C meets the SIRS fever or hypothermia "
                "criterion for acute infection."
            ),
        ),
        "respiratory_rate": _crew(
            "Respiratory rate",
            "s^-1",
            ("lungs",),
            (
                "A rising rate is an early sign of hypoxia or CO2 exposure. The specs "
                "give no cutoff."
            ),
        ),
        "glucose": _crew(
            "Blood glucose",
            "mol/m^3",
            ("blood",),
            (
                "Below 3.9 mmol/L is level 1 hypoglycemia and below 3.0 mmol/L level 2; "
                "a sign of negative energy balance."
            ),
        ),
        "cortisol_saliva": _crew(
            "Salivary cortisol",
            "mol/m^3",
            ("head",),
            (
                "Stress hormone; the diurnal slope tracks behavioral health. The specs' "
                "cutoffs are for time-normalized interstitial fluid, not saliva."
            ),
        ),
        "troponin_i": _crew(
            "Cardiac troponin I",
            "kg/m^3",
            ("heart",),
            "Above 0.04 ng/mL indicates heart muscle injury; restrict EVA.",
        ),
        "lactate": _crew(
            "Blood lactate",
            "mol/m^3",
            ("blood", "muscles"),
            "Resting lactate above 4.0 mmol/L signals negative energy balance.",
        ),
        "urinary_ntx": _crew(
            "Urinary NTx",
            "mol BCE/mol creatinine",
            ("bones", "kidneys"),
            (
                "Bone breakdown marker; graded through its change from baseline "
                "(NTx change from baseline)."
            ),
        ),
        "bone_ntx_pct_baseline": _crew(
            "NTx change from baseline",
            "1",
            ("bones",),
            (
                "A rise of more than 25 % over the preflight baseline signals bone "
                "demineralization."
            ),
        ),
        "vitamin_d_25oh": _crew(
            "Vitamin D (25-OH)",
            "mol/m^3",
            ("bones", "blood"),
            "Supports bone health; the specs track its trend, with no cutoff.",
        ),
        "il6_serum": _crew(
            "Interleukin-6",
            "kg/m^3",
            ("blood",),
            (
                "Inflammation marker; above 3.0 pg/mL outside the 2 h after exercise "
                "suggests infection."
            ),
        ),
        "sweat_sodium_concentration": _crew(
            "Sweat sodium",
            "mol/m^3",
            ("skin",),
            (
                "Local electrolyte loss, tracked against the crew member's own "
                "baseline. The specs give no cutoff."
            ),
        ),
        "sweat_sodium_flux": _crew(
            "Sweat sodium loss rate",
            "mol/s",
            ("skin",),
            (
                "Local electrolyte loss rate, tracked against the crew member's own "
                "baseline. The specs give no cutoff."
            ),
        ),
        "sweat_rate": _crew(
            "Sweat rate",
            "m^3/s",
            ("skin",),
            (
                "Local sweat flow, tracked against the crew member's own baseline. The "
                "specs give no cutoff."
            ),
        ),
        "viral_ebv_detected": _crew(
            "EBV reactivation",
            "boolean",
            ("blood",),
            "Latent Epstein-Barr virus shedding signals immune dysregulation.",
        ),
        "viral_vzv_detected": _crew(
            "VZV reactivation",
            "boolean",
            ("blood",),
            "Latent varicella-zoster virus shedding signals immune dysregulation.",
        ),
        "viral_cmv_detected": _crew(
            "CMV reactivation",
            "boolean",
            ("blood",),
            "Latent cytomegalovirus shedding signals immune dysregulation.",
        ),
        "body_mass": _crew(
            "Body mass",
            "kg",
            ("body",),
            (
                "Acute loss over 2 % of baseline signals dehydration; graded against "
                "baseline, so not on its own."
            ),
        ),
        "urine_specific_gravity": _crew(
            "Urine specific gravity",
            "1",
            ("kidneys",),
            (
                "Above 1.020 signals dehydration; drink the fluid deficit within 30 "
                "minutes."
            ),
        ),
        "urine_volume_24h": _crew(
            "Urine volume (24 h)",
            "m^3",
            ("kidneys",),
            "Below 2.0 L/day raises kidney stone risk alongside bone loss.",
        ),
        "ambient_ppco2": _environment(
            "Cabin CO2 partial pressure",
            "Pa",
            (
                "Above 3.0 mmHg (about 4,000 ppm) causes headaches and impairs "
                "performance in closed habitats."
            ),
        ),
        "ambient_light_lux": _environment(
            "Cabin light level",
            "lx",
            "Light exposure drives the circadian rhythm. The specs give no cutoff.",
        ),
        "ambient_dose_rate": _environment(
            "Radiation dose rate",
            "Sv/s",
            (
                "A spike above 50 µSv/h can mean a solar particle event; move to the "
                "shielded storm shelter."
            ),
        ),
        "ambient_integrated_dose": _environment(
            "Cumulative radiation dose",
            "Sv",
            (
                "Mission dose so far; above the 600 mSv career limit, review radiation "
                "exposure."
            ),
        ),
        "spe_flag": _environment(
            "Solar particle event",
            "boolean",
            (
                "An active solar particle event; move to the shielded storm shelter "
                "immediately."
            ),
        ),
    }
)


def evaluate_reading(channel: str, value: float | bool) -> Status:
    """Grade one reading of one channel on its own.

    Args:
        channel: A key of :data:`CHANNELS`.
        value: The reading in the channel's SI wire ``unit``; ``True`` /
            ``False`` for boolean channels.

    Returns:
        The reading's status. Sources, unit conversions and boundary choices
        are commented per channel.

    Raises:
        ValueError: ``channel`` is not in :data:`CHANNELS`.
    """
    match channel:
        case "heart_rate":
            # NSA 1.3: nominal 50-90 bpm, warning 100-120; 90-100 and > 120
            # take the nearest defined band (warning). Below 50 not addressed.
            bpm = value * 60.0
            if bpm < 50.0:
                return Status.UNSPECIFIED
            if bpm <= 90.0:
                return Status.NOMINAL
            return Status.WARNING
        case "spo2":
            # Master plan Finding 4: < 94 % warning, < 90 % critical hypoxemia.
            pct = value * 100.0
            if pct < 90.0:
                return Status.CRITICAL
            if pct < 94.0:
                return Status.WARNING
            return Status.NOMINAL
        case "body_temperature":
            # Master plan Finding 3 (SIRS): > 38.0 or < 36.0 degC. It wins over
            # NSA 2.2's narrower 36.5-37.5 nominal band, so 36.0-38.0 is nominal.
            celsius = value - 273.15
            if celsius > 38.0 or celsius < 36.0:
                return Status.WARNING
            return Status.NOMINAL
        case "glucose":
            # Master plan Finding 7: Level 1 < 3.9 mM (70 mg/dL), Level 2
            # < 3.0 mM (54 mg/dL), critical as NSA 2.1 grades its lowest band.
            # NSA 2.1 nominal tops out at 7.0 mM; hyperglycemia not addressed.
            # mol/m^3 equals mmol/L.
            if value < 3.0:
                return Status.CRITICAL
            if value < 3.9:
                return Status.WARNING
            if value <= 7.0:
                return Status.NOMINAL
            return Status.UNSPECIFIED
        case "troponin_i":
            # Master plan Finding 1: event-triggered hs-cTnI > 0.04 ng/mL
            # critical. 1 kg/m^3 = 1e6 ng/mL.
            ng_ml = value * 1e6
            return Status.CRITICAL if ng_ml > 0.04 else Status.NOMINAL
        case "lactate":
            # Master plan Finding 7: resting lactate > 4.0 mM. mol/m^3 = mmol/L.
            return Status.WARNING if value > 4.0 else Status.NOMINAL
        case "bone_ntx_pct_baseline":
            # Master plan Finding 8: NTx > +25 % over preflight baseline. The
            # wire value is the fractional change (0.25 = +25 %).
            return Status.WARNING if value > 0.25 else Status.NOMINAL
        case "il6_serum":
            # Master plan Finding 3: IL-6 > 3.0 pg/mL. The 2 h post-ARED gate
            # needs exercise context a single reading lacks; the finding applies
            # it. 1 kg/m^3 = 1e9 pg/mL.
            pg_ml = value * 1e9
            return Status.WARNING if pg_ml > 3.0 else Status.NOMINAL
        case "viral_ebv_detected" | "viral_vzv_detected" | "viral_cmv_detected":
            # Master plan Finding 3: latent herpesvirus reactivation.
            return Status.WARNING if value else Status.NOMINAL
        case "urine_specific_gravity":
            # Master plan Finding 2: USG > 1.020.
            return Status.WARNING if value > 1.020 else Status.NOMINAL
        case "urine_volume_24h":
            # Master plan Finding 8: urine volume < 2.0 L/day. 1 m^3 = 1000 L.
            litres = value * 1000.0
            return Status.WARNING if litres < 2.0 else Status.NOMINAL
        case "ambient_ppco2":
            # Master plan Finding 4: ppCO2 > 3.0 mmHg. 1 mmHg = 133.322 Pa.
            mmhg = value / 133.322
            return Status.WARNING if mmhg > 3.0 else Status.NOMINAL
        case "ambient_dose_rate":
            # Master plan Finding 10: dose-rate spike > 50 uSv/h warning.
            # 1 Sv/s = 3.6e9 uSv/h.
            usv_h = value * 3.6e9
            return Status.WARNING if usv_h > 50.0 else Status.NOMINAL
        case "ambient_integrated_dose":
            # Master plan Finding 10: cumulative dose > 600 mSv career limit.
            msv = value * 1000.0
            return Status.WARNING if msv > 600.0 else Status.NOMINAL
        case "spe_flag":
            # Master plan Finding 10: an SPE is an immediate shelter alert.
            return Status.CRITICAL if value else Status.NOMINAL
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
            | "body_mass"
            | "ambient_light_lux"
        ):
            # No single-reading cutoff in either document: graded against a
            # baseline or trend (body mass, sweat, NTx, vitamin D), only inside
            # a finding (BP, respiratory rate), for another specimen (cortisol
            # cutoffs are for normalized ISF), or not at all (HRV, light).
            return Status.UNSPECIFIED
        case _:
            raise ValueError(f'Unknown channel "{channel}".')
