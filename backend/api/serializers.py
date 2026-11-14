"""DRF serializers for the api app.

Keep these thin: validation and shaping only. Domain logic belongs in
`hydrograph_core` (or another package under `packages/`).
"""

import math
from datetime import UTC, datetime
from typing import Literal, TypedDict, cast, override

from hydrograph_core import (
    CHANNELS,
    ENVIRONMENTS,
    FINDINGS,
    Evaluation,
    FindingResult,
    evaluate_reading,
)
from rest_framework import serializers

from api.models import Reading


class ReadingIn(TypedDict):
    """``validated_data`` of :class:`ReadingInSerializer`."""

    channel: str
    value: float | bool
    unit: str
    measured_at: datetime


class ReadingInSerializer(serializers.Serializer[None]):
    """The device body (docs/json-shape.md, section 1).

    The ``X-Simulation-Scope`` header arrives as ``context["scope"]``.
    """

    channel: serializers.CharField = serializers.CharField()
    value: serializers.JSONField = serializers.JSONField()
    unit: serializers.CharField = serializers.CharField()
    measured_at: serializers.DateTimeField = serializers.DateTimeField()

    def validate_channel(self, value: str) -> str:
        if value not in CHANNELS:
            raise serializers.ValidationError(f'Unknown channel "{value}".')
        return value

    @override
    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        channel = cast("str", attrs["channel"])
        info = CHANNELS[channel]
        context = cast("dict[str, str]", self.context)
        errors: dict[str, list[str]] = {}
        if attrs["unit"] != info["unit"]:
            errors["unit"] = [f'Expected "{info["unit"]}" for {channel}.']
        value = attrs["value"]
        if info["value_type"] == "boolean":
            valid = isinstance(value, bool)
        else:
            valid = (
                isinstance(value, int | float)
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
        if not valid:
            errors["value"] = [f"Expected a {info['value_type']} for {channel}."]
        if context["scope"] != info["scope"]:
            errors["X-Simulation-Scope"] = [
                f'Expected "{info["scope"]}" for {channel}.'
            ]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ReadingPayload(TypedDict):
    """A reading for the frontend (docs/json-shape.md, section 2)."""

    channel: str
    value: float | bool
    unit: str
    evaluation: Evaluation
    measured_at: str
    scope: Literal["crew", "environment"]


def reading_payload(reading: Reading) -> ReadingPayload:
    """The frontend shape of one reading, as sent by POST and the stream."""
    info = CHANNELS[reading.channel]
    value = cast("float | bool", reading.value)
    measured_at = reading.measured_at.astimezone(UTC).isoformat()
    return {
        "channel": reading.channel,
        "value": value,
        "unit": info["unit"],
        "evaluation": evaluate_reading(reading.channel, value),
        "measured_at": measured_at.replace("+00:00", "Z"),
        "scope": info["scope"],
    }


class ChannelEntry(TypedDict):
    name: str
    body_regions: list[str]
    explanation: str


class EnvironmentEntry(TypedDict):
    id: str
    gravity_g: float
    comm_delay_s: float


class FindingEntry(TypedDict):
    name: str
    channels: list[str]


class DictionaryPayload(TypedDict):
    """The static dictionary for the frontend (docs/json-shape.md, section 4)."""

    environments: list[EnvironmentEntry]
    channels: dict[str, ChannelEntry]
    findings: dict[str, FindingEntry]


def environments_payload() -> list[EnvironmentEntry]:
    """Every mission environment, in core's order, with its key as ``id``.

    Served on its own by ``GET /api/environments/`` and as part of the stream
    dictionary, so the two always describe the same set.
    """
    return [{"id": k, **v} for k, v in ENVIRONMENTS.items()]


def dictionary_payload() -> DictionaryPayload:
    """Environments and per-channel display text, all from core."""
    return {
        "environments": environments_payload(),
        "channels": {
            k: {
                "name": v["name"],
                "body_regions": list(v["body_regions"]),
                "explanation": v["explanation"],
            }
            for k, v in CHANNELS.items()
        },
        "findings": {
            k: {"name": v["name"], "channels": list(v["channels"])}
            for k, v in FINDINGS.items()
        },
    }


def finding_payload(finding: str, result: FindingResult) -> dict[str, object]:
    """A finding for the frontend (docs/json-shape.md, section 3): core's result
    plus which finding it is."""
    return {"id": finding, **result}
