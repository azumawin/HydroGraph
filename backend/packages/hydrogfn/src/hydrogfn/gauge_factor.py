"""Master plan section 3A: carrageenan hydrogel segmented dynamic gauge factor."""

from __future__ import annotations

import math
from typing import TypedDict


class GaugeFactorResult(TypedDict):
    section: str
    displacement_mm: float
    strain_pct: float
    zone: str
    gauge_factor: float
    delta_r_over_r0: float


class StrainResult(TypedDict):
    section: str
    delta_r_over_r0: float
    displacement_mm: float
    strain_pct: float
    zone: str
    gauge_factor: float


def dynamic_gauge_factor(
    displacement_mm: float,
    l0_mm: float = 50.0,
) -> GaugeFactorResult:
    r"""
    Section 3A: Segmented dynamic gauge factor (carrageenan ionic hydrogel strip).

    Mechanical strain and fractional resistance shift:
        \epsilon = \frac{\Delta L}{L_0}
        \frac{\Delta R}{R_0} = GF(\epsilon) \cdot \epsilon

    Gauge factor inside a zone, a power law through the zone's end points:
        GF(\Delta L) = GF_{\text{lo}} \cdot
            \left(\frac{\Delta L}{\Delta L_{\text{lo}}}\right)^{p},\quad
        p = \frac{\ln(GF_{\text{hi}} / GF_{\text{lo}})}
            {\ln(\Delta L_{\text{hi}} / \Delta L_{\text{lo}})}

    References:
        Saputra, A. N. et al. (2025). Piezoelectric effect of κ-carrageenan as a
        tool for force sensor. Sensors, 25(15), 4594.

        Zhang, Y. et al. (2025). Ionic hydrogel sensors toward next-gen
        personalized healthcare. Advanced Materials, 37, 2509122.

        Roy, S. et al. (2024). Jugular venous pulse waveform acquisition using
        contact piezo sensor. IEEE Transactions on Biomedical Engineering,
        71(8), 2410–2419.

        Ding, X.-R. et al. (2019). Pulse transit time technique for cuffless
        unobtrusive blood pressure measurement: From theory to algorithm.
        BioMedical Engineering OnLine, 18(1), 33.

    Args:
        displacement_mm: Linear displacement :math:`\Delta L` [mm].
        l0_mm: Unstretched gauge length :math:`L_0` [mm].

    Returns:
        ``section``, ``displacement_mm``, ``strain_pct``, ``zone``,
        ``gauge_factor``, ``delta_r_over_r0``. Zone 1 is 0.01-0.10 mm (GF
        1180.75 down to 114.86), zone 2 is 0.20-1.00 mm (54.24 down to 9.53),
        zone 3 is 4.00-5.05 mm (0.94 down to 0.56). The plan gives each GF as
        a span; its "ultra-high initial contact sensitivity" and the p.8
        example (GF 153.2 at 0.08 mm, near the top of zone 1) put the high
        value at the low end. The power law is the closest simple curve to
        that example (144.0 at 0.08 mm; linear gives 351.7).

    Raises:
        ValueError: If ``displacement_mm`` is in none of the three zones (below
            0.01 mm, in the gaps 0.10-0.20 mm and 1.00-4.00 mm, or above
            5.05 mm), where the plan defines no gauge factor.
    """
    # (zone, dL lo [mm], dL hi [mm], GF at lo, GF at hi), master plan p.5
    zones = (
        ("1", 0.01, 0.10, 1180.75, 114.86),
        ("2", 0.20, 1.00, 54.24, 9.53),
        ("3", 4.00, 5.05, 0.94, 0.56),
    )

    for name, d_lo, d_hi, gf_lo, gf_hi in zones:
        if d_lo <= displacement_mm <= d_hi:
            p = math.log(gf_hi / gf_lo) / math.log(d_hi / d_lo)
            gf = gf_lo * math.pow(displacement_mm / d_lo, p)
            strain = displacement_mm / l0_mm  # fraction
            return {
                "section": "3A",
                "displacement_mm": displacement_mm,
                "strain_pct": round(strain * 100, 3),
                "zone": name,
                "gauge_factor": round(gf, 2),
                "delta_r_over_r0": round(gf * strain, 6),
            }

    raise ValueError(
        f"displacement {displacement_mm} mm is in none of the plan's GF zones"
    )


def strain_from_resistance(
    delta_r_over_r0: float,
    l0_mm: float = 50.0,
) -> StrainResult:
    r"""
    Section 3A: Displacement and strain from a hydrogel resistance reading.

    Fractional resistance shift, with the zone power law of
    :func:`dynamic_gauge_factor`:
        \frac{\Delta R}{R_0} = \frac{GF_{\text{lo}}}{L_0 \, \Delta L_{\text{lo}}^{p}}
            \cdot \Delta L^{1 + p}

    Solved for displacement (what the sensor reading gives us):
        \Delta L = \left(\frac{\Delta R}{R_0} \cdot
            \frac{L_0 \, \Delta L_{\text{lo}}^{p}}{GF_{\text{lo}}}\right)^{1 / (1 + p)}

    References:
        Saputra, A. N. et al. (2025). Piezoelectric effect of κ-carrageenan as a
        tool for force sensor. Sensors, 25(15), 4594.

        Zhang, Y. et al. (2025). Ionic hydrogel sensors toward next-gen
        personalized healthcare. Advanced Materials, 37, 2509122.

    Args:
        delta_r_over_r0: Fractional resistance shift :math:`\Delta R / R_0` [unitless].
        l0_mm: Unstretched gauge length :math:`L_0` [mm].

    Returns:
        ``section``, ``delta_r_over_r0``, ``displacement_mm``, ``strain_pct``,
        ``zone``, ``gauge_factor``. In every zone GF falls faster than strain
        rises, so ΔR/R0 falls slightly as displacement grows, and the three
        zones cover separate ΔR/R0 bands (at L0 = 50 mm: zone 1
        0.2297-0.2362, zone 2 0.1906-0.2170, zone 3 0.0566-0.0752). A reading
        therefore matches at most one displacement.

    Raises:
        ValueError: If ``delta_r_over_r0`` is in none of the zones' bands, so
            no displacement the plan defines produces it.
    """
    # (zone, dL lo [mm], dL hi [mm], GF at lo, GF at hi), master plan p.5
    zones = (
        ("1", 0.01, 0.10, 1180.75, 114.86),
        ("2", 0.20, 1.00, 54.24, 9.53),
        ("3", 4.00, 5.05, 0.94, 0.56),
    )

    for name, d_lo, d_hi, gf_lo, gf_hi in zones:
        # band edges at the precision dynamic_gauge_factor returns
        y_at_lo = round(gf_lo * d_lo / l0_mm, 6)
        y_at_hi = round(gf_hi * d_hi / l0_mm, 6)
        if y_at_hi <= delta_r_over_r0 <= y_at_lo:
            p = math.log(gf_hi / gf_lo) / math.log(d_hi / d_lo)
            d = math.pow(
                delta_r_over_r0 * l0_mm * math.pow(d_lo, p) / gf_lo, 1 / (1 + p)
            )
            gf = gf_lo * math.pow(d / d_lo, p)
            return {
                "section": "3A",
                "delta_r_over_r0": delta_r_over_r0,
                "displacement_mm": round(d, 4),
                "strain_pct": round(d / l0_mm * 100, 3),
                "zone": name,
                "gauge_factor": round(gf, 2),
            }

    raise ValueError(
        f"delta_r_over_r0 {delta_r_over_r0} matches no displacement in the plan's GF zones"
    )
