"""Feed core's findings from stored readings.

The backend monitors one astronaut: findings use the latest reading of every
channel, crew and cabin alike.
"""

from collections.abc import Iterable
from datetime import timedelta
from typing import cast

from api.models import Reading
from api.rules import enabled_rules, log_rule_error
from core import EnvironmentInfo, FindingResult, evaluate_findings

WEEK = timedelta(days=7)


async def crew_findings(
    environment: EnvironmentInfo, findings: Iterable[str] | None = None
) -> dict[str, FindingResult]:
    """The given findings (default: every enabled rule), from the latest readings."""
    rules = await enabled_rules()
    if findings is not None:
        wanted = set(findings)
        rules = [rule for rule in rules if rule.id in wanted]
    channels = {channel for rule in rules for channel in rule.channels}
    latest: dict[str, float | bool | str] = {}
    for channel in channels:
        reading = await (
            Reading.objects.filter(channel=channel)
            .order_by("-measured_at", "-id")
            .afirst()
        )
        if reading is not None:
            latest[channel] = cast("float | bool | str", reading.value)

    first: Reading | None = None
    week_before: Reading | None = None
    if "body_mass" in channels:
        body_mass = Reading.objects.filter(channel="body_mass")
        first = await body_mass.order_by("measured_at", "id").afirst()
        last = await body_mass.order_by("-measured_at", "-id").afirst()
        if last is not None:
            week_before = await (
                body_mass.filter(measured_at__lte=last.measured_at - WEEK)
                .order_by("-measured_at", "-id")
                .afirst()
            )
    return evaluate_findings(
        latest,
        None if first is None else cast("float", first.value),
        None if week_before is None else cast("float", week_before.value),
        environment,
        rules,
        log_rule_error,
    )


async def affected_findings(
    channel: str, environment: EnvironmentInfo
) -> dict[str, FindingResult]:
    """Every finding that uses a new reading's channel."""
    return await crew_findings(
        environment,
        [rule.id for rule in await enabled_rules() if channel in rule.channels],
    )
