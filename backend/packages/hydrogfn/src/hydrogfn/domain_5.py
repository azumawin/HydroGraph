"""Domain 5: Immune System & Host Defense (parameter 5.1)."""

from __future__ import annotations

from typing import TypedDict

from .shared import Status


class InflammationResult(TypedDict):
    param: str
    inflammatory_index: float
    status: Status
    action: str


def inflammatory_cytokines_5_1(
    il6_pg_ml: float,
    tnf_alpha_pg_ml: float,
    post_ared_window: bool,
    *,
    w1: float,
    w2: float,
) -> InflammationResult:
    r"""
    Parameter 5.1: Immune cytokines (IL-6 & TNF-α), inflammatory cascades (dual-aptamer GFET).

    Inflammatory index:
        I_{\text{inf}} = w_1 \cdot [\text{IL-6}] + w_2 \cdot [\text{TNF-}\alpha]

    References:
        Chen, Y. et al. (2025). Aptamer-based graphene field-effect transistor
        biosensor for cytokine detection in undiluted physiological media. ACS
        Sensors.

    Args:
        il6_pg_ml: IL-6 concentration :math:`[\text{IL-6}]` [pg/mL].
        tnf_alpha_pg_ml: TNF-α concentration :math:`[\text{TNF-}\alpha]` [pg/mL].
        post_ared_window: The reading is within 2 h after an ARED workout.
        w1: IL-6 weight :math:`w_1` [unitless]; the spec gives no value.
        w2: TNF-α weight :math:`w_2` [unitless]; the spec gives no value.

    Returns:
        ``param``, ``inflammatory_index``, ``status``, ``action``.
        The spec gives no unit for :math:`I_{\text{inf}}`; with unitless
        weights it is in pg/mL. Nominal needs both :math:`I_{\text{inf}} < 5.0`
        and IL-6 <= 3.0 pg/mL. A reading with :math:`I_{\text{inf}} < 5.0` but
        IL-6 > 3.0 pg/mL falls in the gap below the warning band: WARNING.
        The master plan's IL-6 warning is "> 3.0 pg/mL" (the parameter spec's
        nominal is "< 3.0"), and it ignores IL-6 within 2 h after ARED
        exercise; the index bands still apply in that window.
    """
    inflammatory_index = w1 * il6_pg_ml + w2 * tnf_alpha_pg_ml

    if inflammatory_index > 12.0:
        status, action = Status.CRITICAL, "Immediate clinical isolation protocol"
    elif inflammatory_index >= 5.0 or (il6_pg_ml > 3.0 and not post_ared_window):
        status, action = (
            Status.WARNING,
            "Recommend antioxidant/anti-inflammatory regimen, restrict EVA exposure",
        )
    else:
        status, action = Status.NOMINAL, "Normal immune status"

    return {
        "param": "5.1",
        "inflammatory_index": round(inflammatory_index, 2),
        "status": status,
        "action": action,
    }
