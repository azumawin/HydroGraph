"""Findings as rules: built-in rule modules and custom rule source.

A rule is a Python module, or Python source for a custom rule, that defines:

- ``ID``: the finding id, lowercase letters, digits and underscores.
- ``NAME``: the finding's display name.
- ``CHANNELS``: every channel it reads; a new reading on one re-evaluates it.
- ``REQUIRED`` (optional): the channels that must all have a reading before it
  is evaluated; defaults to ``CHANNELS``.
- ``evaluate(inputs)``: returns the finding result, or ``None`` when the rule
  cannot be evaluated yet. ``inputs`` is a :class:`RuleInputs`.

A result is a dict with ``status`` (``"nominal"``, ``"warning"`` or
``"critical"``, or a boolean for a single-severity finding), ``triggers`` (a
list of strings), ``action`` (a string) and any further evaluated values.

Custom source runs as ordinary Python, with no sandbox or time limit.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import TypedDict, cast

from .channels import CHANNELS
from .environments import EnvironmentInfo
from .findings import (
    BloodPressureResult,
    BoneResult,
    DehydrationResult,
    EnergyBalanceResult,
    HypoxiaResult,
    InfectionResult,
    RadiationResult,
    SansResult,
    Severity,
)


class BloodPressureSensorErrorResult(TypedDict):
    sbp_mmhg: float
    dbp_mmhg: float
    sensor_error: str
    triggers: list[str]
    status: Severity
    action: str


type FindingResult = (
    BloodPressureResult
    | BloodPressureSensorErrorResult
    | BoneResult
    | DehydrationResult
    | HypoxiaResult
    | EnergyBalanceResult
    | InfectionResult
    | RadiationResult
    | SansResult
)

RULE_ID = re.compile(r"[a-z][a-z0-9_]{0,63}")
SEVERITIES = ("nominal", "warning", "critical")


class RuleInputs(TypedDict):
    """What a rule's ``evaluate`` receives.

    ``latest`` holds the latest reading of every channel the rule reads, in SI
    wire units. ``body_mass_first_kg`` is the earliest body mass (the mission
    baseline) and ``body_mass_week_before_kg`` the latest one taken at least
    seven days before the latest; both are ``None`` when unknown.
    """

    latest: Mapping[str, float | bool | str]
    environment: EnvironmentInfo
    body_mass_first_kg: float | None
    body_mass_week_before_kg: float | None


class RuleError(ValueError):
    """A rule that does not follow the contract in this module's docstring."""


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    channels: tuple[str, ...]
    required: tuple[str, ...]
    evaluate: Callable[[RuleInputs], object]
    source: str

    def run(self, inputs: RuleInputs) -> FindingResult | None:
        """The checked result, ``None`` when the rule cannot be evaluated yet.

        Raises:
            RuleError: The result does not follow the result contract.
        """
        result = self.evaluate(inputs)
        if result is None:
            return None
        return check_result(result)


def check_result(result: object) -> FindingResult:
    """``result`` if it follows the result contract.

    Raises:
        RuleError: It does not.
    """
    if not isinstance(result, dict):
        raise RuleError("evaluate must return a dict or None")
    fields = cast("dict[str, object]", result)
    status = fields.get("status")
    if not isinstance(status, bool) and status not in SEVERITIES:
        raise RuleError("status must be nominal, warning, critical or a boolean")
    triggers = fields.get("triggers")
    if not isinstance(triggers, list) or not all(
        isinstance(trigger, str) for trigger in cast("list[object]", triggers)
    ):
        raise RuleError("triggers must be a list of strings")
    if not isinstance(fields.get("action"), str):
        raise RuleError("action must be a string")
    return cast("FindingResult", cast("object", fields))


def rule_from_namespace(namespace: Mapping[str, object], source: str) -> Rule:
    """The rule a module or executed source defines.

    Raises:
        RuleError: The definitions do not follow the rule contract.
    """
    rule_id = namespace.get("ID")
    if not isinstance(rule_id, str) or RULE_ID.fullmatch(rule_id) is None:
        raise RuleError(
            "ID must start with a lowercase letter and use only lowercase letters, "
            + "digits and underscores (at most 64)"
        )
    name = namespace.get("NAME")
    if not isinstance(name, str) or not name.strip():
        raise RuleError("NAME must be a non-empty string")
    channels = _channels(namespace.get("CHANNELS"), "CHANNELS")
    required = (
        channels
        if "REQUIRED" not in namespace
        else _channels(namespace["REQUIRED"], "REQUIRED")
    )
    if not set(required) <= set(channels):
        raise RuleError("REQUIRED must be a subset of CHANNELS")
    evaluate = namespace.get("evaluate")
    if not callable(evaluate):
        raise RuleError("evaluate(inputs) must be defined")
    return Rule(
        id=rule_id,
        name=name.strip(),
        channels=channels,
        required=required,
        evaluate=cast("Callable[[RuleInputs], object]", evaluate),
        source=source,
    )


def _channels(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise RuleError(f"{field} must be a list or tuple of channel ids")
    channels = tuple(cast("list[object] | tuple[object, ...]", value))
    unknown = [
        str(channel)
        for channel in channels
        if not isinstance(channel, str) or channel not in CHANNELS
    ]
    if unknown:
        raise RuleError(f"{field} has unknown channels: {', '.join(unknown)}")
    return cast("tuple[str, ...]", channels)


def rule_from_module(module: ModuleType, source: str) -> Rule:
    """The rule a built-in rule module defines."""
    return rule_from_namespace(vars(module), source)


def compile_rule(source: str) -> Rule:
    """The rule custom ``source`` defines.

    Raises:
        RuleError: The source does not run or does not follow the rule
            contract.
    """
    namespace: dict[str, object] = {"__name__": "custom_rule"}
    try:
        exec(compile(source, "<custom rule>", "exec"), namespace)  # noqa: S102
    except Exception as error:
        raise RuleError(f"{type(error).__name__}: {error}") from error
    return rule_from_namespace(namespace, source)
