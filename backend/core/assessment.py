"""Tier 1 findings from the latest channel readings.

:mod:`core.findings` takes spec-unit arguments; the device sends SI
channel readings (:mod:`core.channels`). Each finding is a rule
(:mod:`core.rule`); the built-in rules in :mod:`core.rules` convert the latest
readings and call their finding. :func:`evaluate_findings` runs a set of rules
for one crew member.

Seven of the ten findings are monitored. :data:`FINDINGS` lists all ten; an
empty ``channels`` tuple marks one whose inputs the simulator does not send
(postural BP, sleep, PHQ-9/GAD-7, EEG/PVT).

Context a single reading cannot carry, assumed here:

- NEWS2 uses explicit oxygen and ACVPU context when present, otherwise
  assumes room air and alertness with per-field provenance.
- Finding 3 uses explicit post-ARED context when supplied, otherwise False.
- Finding 4's "rising respiratory rate" has no definition and headache is not
  reported, so both are passed as False.
- Finding 7's resting lactate is the latest lactate reading.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from types import MappingProxyType
from typing import Final, TypedDict

from .environments import EnvironmentInfo
from .rule import FindingResult, Rule, RuleInputs
from .rules import DEFAULT_RULES
from .scores import News2Result, news2, qsofa

__all__ = [
    "FINDINGS",
    "FindingInfo",
    "FindingResult",
    "News2Result",
    "evaluate_findings",
    "news2",
    "qsofa",
]


class FindingInfo(TypedDict):
    name: str
    channels: tuple[str, ...]


FINDINGS: Final[Mapping[str, FindingInfo]] = MappingProxyType(
    {rule.id: {"name": rule.name, "channels": rule.channels} for rule in DEFAULT_RULES}
)
"""The built-in findings by id; an empty ``channels`` marks an unmonitored one."""


def evaluate_findings(
    latest: Mapping[str, float | bool | str],
    body_mass_first_kg: float | None,
    body_mass_week_before_kg: float | None,
    environment: EnvironmentInfo,
    rules: Iterable[Rule] = DEFAULT_RULES,
    on_error: Callable[[Rule, Exception], None] | None = None,
) -> dict[str, FindingResult]:
    """Every rule whose required channels all have a reading.

    Args:
        latest: Latest reading per channel for one crew member, in SI wire
            units, plus the latest cabin (environment) readings.
        body_mass_first_kg: The crew member's earliest body mass, the mission
            baseline for Finding 2.
        body_mass_week_before_kg: Their latest body mass taken at least 7 days
            before the latest one, for Finding 7's weekly loss; ``None`` in the
            first week, when the loss since the baseline is used instead (not
            extrapolated to a weekly rate).
        environment: The mission environment in effect; Finding 10 grades the
            dose rate above its baseline.
        rules: The rules to run; default: the built-in ones.
        on_error: Called with a rule that raised and its exception, which is
            then skipped; without it, the exception propagates.

    Returns:
        Rule id to its result. Rules with a missing input, or that return
        ``None``, are left out.
    """
    results: dict[str, FindingResult] = {}
    for rule in rules:
        if not all(channel in latest for channel in rule.required):
            continue
        inputs: RuleInputs = {
            "latest": {c: latest[c] for c in rule.channels if c in latest},
            "environment": environment,
            "body_mass_first_kg": body_mass_first_kg,
            "body_mass_week_before_kg": body_mass_week_before_kg,
        }
        try:
            result = rule.run(inputs)
        except Exception as error:
            if on_error is None:
                raise
            on_error(rule, error)
            continue
        if result is not None:
            results[rule.id] = result
    return results
