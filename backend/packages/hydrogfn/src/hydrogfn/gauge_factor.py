"""Master plan section 3A: carrageenan hydrogel segmented dynamic gauge factor."""

from __future__ import annotations

import math
from typing import TypedDict


class GaugeFactorResult(TypedDict):
    section: str
    strain_pct: float
    range: str
    gauge_factor: float
    delta_r_over_r0: float


class StrainResult(TypedDict):
    section: str
    delta_r_over_r0: float
    strain_pct: float
    range: str
    gauge_factor: float
    candidates_pct: list[float]


def dynamic_gauge_factor(strain_pct: float) -> GaugeFactorResult:
    r"""
    Section 3A: Segmented dynamic gauge factor (carrageenan ionic hydrogel strip).

    Fractional resistance change:
        \frac{\Delta R}{R_0} = GF(\epsilon) \cdot \epsilon

    Segmented gauge factor, linear inside each range:
        GF(\epsilon) = GF_{\text{lo}} + (GF_{\text{hi}} - GF_{\text{lo}})
            \cdot \frac{\epsilon - \epsilon_{\text{lo}}}{\epsilon_{\text{hi}} - \epsilon_{\text{lo}}}

    References:
        Liu, X. et al. Highly conductive and stable double network carrageenan
        organohydrogels for advanced strain sensing and signal recognition arrays.

        Bučinskas, V., Žaimis, U., Udris, D., Petronienė, J.J., & Dzedzickis, A.
        (2025). Piezoelectric Effect of k-Carrageenan as a Tool for Force Sensor.
        Sensors, 25, 4594. https://doi.org/10.3390/s25154594

    Args:
        strain_pct: Elongation :math:`\epsilon` [%].

    Returns:
        ``section``, ``strain_pct``, ``range``, ``gauge_factor``,
        ``delta_r_over_r0``. Range A is 0-5 % (GF 1180.75), B is 5-15 %
        (GF 233.48-389.58), C is 15-30 % (GF 74.34-114.86). The plan gives B
        and C only as spans; GF is interpolated linearly from the first value
        at the low end to the second at the high end. The shared boundaries
        5 % and 15 % belong to the lower range.

    Raises:
        ValueError: If ``strain_pct`` is outside 0-30 %, where the plan
            defines no gauge factor.
    """
    # (range, strain lo [%], strain hi [%], GF at lo, GF at hi), master plan p.3
    ranges = (
        ("A", 0.0, 5.0, 1180.75, 1180.75),
        ("B", 5.0, 15.0, 233.48, 389.58),
        ("C", 15.0, 30.0, 74.34, 114.86),
    )

    for name, e_lo, e_hi, gf_lo, gf_hi in ranges:
        if e_lo <= strain_pct <= e_hi:
            gf = gf_lo + (gf_hi - gf_lo) * (strain_pct - e_lo) / (e_hi - e_lo)
            return {
                "section": "3A",
                "strain_pct": strain_pct,
                "range": name,
                "gauge_factor": round(gf, 2),
                "delta_r_over_r0": round(gf * strain_pct / 100, 4),
            }

    raise ValueError(f"strain {strain_pct} % is outside the 0-30 % defined by the plan")


def strain_from_resistance(delta_r_over_r0: float) -> StrainResult:
    r"""
    Section 3A: Strain from a hydrogel resistance reading (inverse of the segmented GF).

    Fractional resistance change:
        \frac{\Delta R}{R_0} = GF(\epsilon) \cdot \epsilon

    Solved for strain inside one range (what the sensor reading gives us), with
    :math:`s = (GF_{\text{hi}} - GF_{\text{lo}}) / (\epsilon_{\text{hi}} - \epsilon_{\text{lo}})`:
        s \epsilon^2 + (GF_{\text{lo}} - s \epsilon_{\text{lo}}) \epsilon - \frac{\Delta R}{R_0} = 0

    References:
        Liu, X. et al. Highly conductive and stable double network carrageenan
        organohydrogels for advanced strain sensing and signal recognition arrays.

        Bučinskas, V., Žaimis, U., Udris, D., Petronienė, J.J., & Dzedzickis, A.
        (2025). Piezoelectric Effect of k-Carrageenan as a Tool for Force Sensor.
        Sensors, 25, 4594. https://doi.org/10.3390/s25154594

    Args:
        delta_r_over_r0: Fractional resistance change :math:`\Delta R / R_0` [unitless].

    Returns:
        ``section``, ``delta_r_over_r0``, ``strain_pct``, ``range``,
        ``gauge_factor``, ``candidates_pct``. The plan's GF jumps down at 5 %
        and 15 %, so one reading can match a strain in more than one range.
        ``candidates_pct`` lists every match, lowest first; ``strain_pct``,
        ``range`` and ``gauge_factor`` describe the lowest. Ranges and
        interpolation as in :func:`dynamic_gauge_factor`.

    Raises:
        ValueError: If ``delta_r_over_r0`` is negative or above every range's
            maximum (59.0375, the top of range A), so no strain in 0-30 %
            produces it.
    """
    # (range, strain lo [%], strain hi [%], GF at lo, GF at hi), master plan p.3
    ranges = (
        ("A", 0.0, 5.0, 1180.75, 1180.75),
        ("B", 5.0, 15.0, 233.48, 389.58),
        ("C", 15.0, 30.0, 74.34, 114.86),
    )

    matches: list[tuple[float, str, float]] = []
    for name, e_lo_pct, e_hi_pct, gf_lo, gf_hi in ranges:
        e_lo, e_hi = e_lo_pct / 100, e_hi_pct / 100  # fractions
        s = (gf_hi - gf_lo) / (e_hi - e_lo)
        b = gf_lo - s * e_lo
        if s == 0:
            roots = [delta_r_over_r0 / b]
        else:
            disc = b * b + 4 * s * delta_r_over_r0
            roots = [] if disc < 0 else [(-b + math.sqrt(disc)) / (2 * s)]
        for e in roots:
            # boundary strain belongs to the lower range, so B and C exclude e_lo
            above_lo = e >= e_lo if name == "A" else e > e_lo
            if above_lo and e <= e_hi:
                gf = gf_lo + s * (e - e_lo)
                matches.append((e * 100, name, gf))

    if delta_r_over_r0 < 0 or not matches:
        raise ValueError(
            f"delta_r_over_r0 {delta_r_over_r0} matches no strain in the plan's 0-30 %"
        )

    strain_pct, name, gf = min(matches)
    return {
        "section": "3A",
        "delta_r_over_r0": delta_r_over_r0,
        "strain_pct": round(strain_pct, 3),
        "range": name,
        "gauge_factor": round(gf, 2),
        "candidates_pct": sorted(round(m[0], 3) for m in matches),
    }
