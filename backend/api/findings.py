"""Feed core's findings from stored readings.

The backend monitors one astronaut: findings use the latest reading of every
channel, crew and cabin alike.
"""

from collections.abc import Iterable
from datetime import timedelta
from typing import cast

from hydrograph_core import FINDINGS, EnvironmentInfo, FindingResult, evaluate_findings

from api.models import Reading

WEEK = timedelta(days=7)


def crew_findings(
    environment: EnvironmentInfo, findings: Iterable[str] = FINDINGS
) -> dict[str, FindingResult]:
    """The given monitored findings (default: all), from the latest readings.

    Only those findings' input channels are read.
    """
    wanted = set(findings)
    channels = {c for f in wanted for c in FINDINGS[f]["channels"]}
    latest: dict[str, float | bool | str] = {}
    for channel in channels:
        reading = (
            Reading.objects.filter(channel=channel)
            .order_by("-measured_at", "-id")
            .first()
        )
        if reading is not None:
            latest[channel] = cast("float | bool | str", reading.value)

    first = week_before = None
    if "body_mass" in channels:
        body_mass = Reading.objects.filter(channel="body_mass")
        first = body_mass.order_by("measured_at", "id").first()
        last = body_mass.order_by("-measured_at", "-id").first()
        if last is not None:
            week_before = (
                body_mass.filter(measured_at__lte=last.measured_at - WEEK)
                .order_by("-measured_at", "-id")
                .first()
            )
    results = evaluate_findings(
        latest,
        None if first is None else cast("float", first.value),
        None if week_before is None else cast("float", week_before.value),
        environment,
    )
    return {f: r for f, r in results.items() if f in wanted}


def affected_findings(
    channel: str, environment: EnvironmentInfo
) -> dict[str, FindingResult]:
    """Every finding that uses a new reading's channel."""
    return crew_findings(
        environment, (f for f, info in FINDINGS.items() if channel in info["channels"])
    )
