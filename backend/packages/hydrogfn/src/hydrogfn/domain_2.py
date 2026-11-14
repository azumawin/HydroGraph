"""Domain 2: Metabolic & Nutritional Health (parameters 2.1-2.2)."""

from __future__ import annotations

import math
from typing import TypedDict

from .shared import Status


class GlucoseResult(TypedDict):
    param: str
    glucose_mmol_l: float
    glucose_mg_dl: float
    status: Status
    action: str


class TemperatureResult(TypedDict):
    param: str
    temperature_k: float
    temperature_c: float
    status: Status
    action: str


def glucose_2_1(
    delta_ids: float,
    gm: float = 120.0,
    vgs: float = 0.4,
    k_enz: float = 0.185,
) -> GlucoseResult:
    r"""
    Parameter 2.1: Blood glucose & inadequate nutrition (enzymatic GFET).

    GFET enzyme-response equation:
        \Delta I_{ds} = g_m \cdot V_{gs} \cdot \left(1 - e^{-k_{\text{enz}} \cdot [\text{Glucose}]}\right)

    Solved for glucose (what the sensor reading gives us):
        [\text{Glucose}] = -\frac{\ln\left(1 - \frac{\Delta I_{ds}}{g_m V_{gs}}\right)}{k_{\text{enz}}}

    References:
        None given in the spec for this sensor.

    Args:
        delta_ids: Drain-source current shift from baseline :math:`\Delta I_{ds}` [µA].
        gm: Transconductance :math:`g_m` [µS].
        vgs: Gate-source voltage :math:`V_{gs}` [V].
        k_enz: Enzyme saturation constant :math:`k_{\text{enz}}` [mM^-1].

    Returns:
        ``param``, ``glucose_mmol_l``, ``glucose_mg_dl``, ``status``, ``action``.
        mg/dL uses the spec's approximate 1 mM = 18 mg/dL. CRITICAL < 3.0 mM,
        WARNING 3.0-3.9 mM, nominal 3.9-7.0 mM: the master plan's IHSG/ADA
        Level 2 (< 3.0 mM) and Level 1 (< 3.9 mM) hypoglycemia cutoffs
        (Finding 7) override the parameter spec's 3.5 and 4.0 mM. Above 7.0 mM
        (hyperglycemia) has no protocol: UNSPECIFIED.

    Raises:
        ValueError: ``delta_ids`` is outside ``0 <= delta_ids < gm * vgs``; the
            response saturates at ``gm * vgs``, so no concentration matches.
    """
    saturation = gm * vgs  # µA
    if not 0 <= delta_ids < saturation:
        raise ValueError(f"delta_ids={delta_ids} µA outside [0, {saturation}) µA")

    glucose_mmol_l = -math.log1p(-delta_ids / saturation) / k_enz
    glucose_mg_dl = glucose_mmol_l * 18.0

    if glucose_mmol_l < 3.0:
        status, action = (
            Status.CRITICAL,
            "Mandatory rest alert, lock mission-critical EVA controls until nutrition intake confirmed",
        )
    elif glucose_mmol_l < 3.9:
        status, action = Status.WARNING, "Consume nutritional gel packet"
    elif glucose_mmol_l <= 7.0:
        status, action = Status.NOMINAL, "Optimal energy balance"
    else:
        status, action = Status.UNSPECIFIED, "No protocol defined in spec"

    return {
        "param": "2.1",
        "glucose_mmol_l": round(glucose_mmol_l, 2),
        "glucose_mg_dl": round(glucose_mg_dl, 1),
        "status": status,
        "action": action,
    }


def core_temperature_2_2(
    r_t: float,
    a: float = 1.1292e-3,
    b: float = 2.3412e-4,
    c: float = 8.7654e-8,
) -> TemperatureResult:
    r"""
    Parameter 2.2: Core body temperature & thermoregulation failure (hydrogel thermistor).

    Steinhart-Hart equation:
        \frac{1}{T} = A + B \cdot \ln(R_T) + C \cdot \left( \ln(R_T) \right)^3

    Celsius conversion:
        T(^\circ\text{C}) = T(\text{K}) - 273.15

    References:
        Li, X., Zhou, Y., Wei, Z., Yin, H., Wang, P., Li, G., Meng, C. High-Performance
        Hydrogel-Based Temperature Sensor by Integrating Ion Channels and Stabilized
        Ion Gradients.

    Args:
        r_t: Thermistor resistance :math:`R_T` [Ω].
        a: Steinhart-Hart coefficient :math:`A` [K^-1].
        b: Steinhart-Hart coefficient :math:`B` [K^-1].
        c: Steinhart-Hart coefficient :math:`C` [K^-1]; the spec labels it
            K^-3, but every term must be K^-1 for the equation to balance.

    Returns:
        ``param``, ``temperature_k``, ``temperature_c``, ``status``, ``action``.
        Nominal 36.5-37.5 °C. The spec only defines a WARNING above 38.0 °C,
        so the 37.5-38.0 gap is WARNING too. Below 36.5 °C (hypothermia) has
        no protocol: UNSPECIFIED.
    """
    log_r = math.log(r_t)
    temperature_k = 1.0 / (a + b * log_r + c * log_r**3)
    temperature_c = temperature_k - 273.15

    if temperature_c > 37.5:
        status, action = (
            Status.WARNING,
            "Auto-increase liquid cooling garment pump rate, flash thermal warning",
        )
    elif temperature_c >= 36.5:
        status, action = Status.NOMINAL, "Normal baseline"
    else:
        status, action = Status.UNSPECIFIED, "No protocol defined in spec"

    return {
        "param": "2.2",
        "temperature_k": round(temperature_k, 2),
        "temperature_c": round(temperature_c, 2),
        "status": status,
        "action": action,
    }
