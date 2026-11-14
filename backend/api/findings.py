"""Feed core's findings from stored readings.

The backend monitors one astronaut: findings use the latest reading of every
channel, crew and cabin alike.
"""

from datetime import timedelta
from typing import cast

from hydrograph_core import FINDINGS, FindingResult, evaluate_findings

from api.models import Reading

INPUTS = sorted({c for info in FINDINGS.values() for c in info["channels"]})
WEEK = timedelta(days=7)


def crew_findings() -> dict[str, FindingResult]:
    """Every monitored finding, from the latest readings."""
    latest: dict[str, float | bool] = {}
    for channel in INPUTS:
        reading = (
            Reading.objects.filter(channel=channel)
            .order_by("-measured_at", "-id")
            .first()
        )
        if reading is not None:
            latest[channel] = cast("float | bool", reading.value)

    body_mass = Reading.objects.filter(channel="body_mass")
    first = body_mass.order_by("measured_at", "id").first()
    last = body_mass.order_by("-measured_at", "-id").first()
    week_before = (
        None
        if last is None
        else body_mass.filter(measured_at__lte=last.measured_at - WEEK)
        .order_by("-measured_at", "-id")
        .first()
    )
    return evaluate_findings(
        latest,
        None if first is None else cast("float", first.value),
        None if week_before is None else cast("float", week_before.value),
    )


def affected_findings(channel: str) -> dict[str, FindingResult]:
    """Every finding that uses a new reading's channel."""
    if channel not in INPUTS:
        return {}
    return {
        finding: result
        for finding, result in crew_findings().items()
        if channel in FINDINGS[finding]["channels"]
    }
