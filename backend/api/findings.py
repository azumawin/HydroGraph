"""Feed core's findings from stored readings.

Findings are per crew member. Their crew channels come from that member's own
readings; cabin (environment) channels from the latest reading of any
compartment, since every crew member shares the one simulated cabin.
"""

from datetime import timedelta
from typing import cast

from hydrograph_core import CHANNELS, FINDINGS, FindingResult, evaluate_findings

from api.models import Reading

INPUTS = sorted({c for info in FINDINGS.values() for c in info["channels"]})
CREW_CHANNELS = [c for c, info in CHANNELS.items() if info["scope"] == "crew"]
WEEK = timedelta(days=7)


def crew_owners() -> list[str]:
    """Every owner that has sent a crew reading."""
    owners = Reading.objects.filter(channel__in=CREW_CHANNELS).order_by()
    return sorted(
        cast("list[str]", list(owners.values_list("owner_id", flat=True).distinct()))
    )


def crew_findings(owner_id: str) -> dict[str, FindingResult]:
    """Every monitored finding for one crew member, from their latest readings."""
    latest: dict[str, float | bool] = {}
    for channel in INPUTS:
        readings = Reading.objects.filter(channel=channel)
        if CHANNELS[channel]["scope"] == "crew":
            readings = readings.filter(owner_id=owner_id)
        reading = readings.order_by("-measured_at", "-id").first()
        if reading is not None:
            latest[channel] = cast("float | bool", reading.value)

    body_mass = Reading.objects.filter(owner_id=owner_id, channel="body_mass")
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


def affected_findings(
    owner_id: str, channel: str
) -> list[tuple[str, str, FindingResult]]:
    """(owner, finding, result) for every finding that uses a new reading's channel.

    A crew reading affects its own owner; a cabin reading affects every crew
    member.
    """
    if channel not in INPUTS:
        return []
    owners = [owner_id] if CHANNELS[channel]["scope"] == "crew" else crew_owners()
    return [
        (owner, finding, result)
        for owner in owners
        for finding, result in crew_findings(owner).items()
        if channel in FINDINGS[finding]["channels"]
    ]
