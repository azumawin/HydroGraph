"""DRF serializers for the api app.

Keep these thin: validation and shaping only. Domain logic belongs in
`hydrograph_core` (or another package under `packages/`).
"""

import math
from datetime import UTC, datetime
from typing import Literal, TypedDict, cast, override

from hydrograph_core import CHANNELS, ENVIRONMENTS, evaluate_reading
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

    Owner and scope arrive as headers; pass them as ``context``.
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
        if not context["owner_id"]:
            errors["X-Owner-ID"] = ["This header is required."]
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
    evaluation: str
    measured_at: str
    owner_id: str
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
        "evaluation": evaluate_reading(reading.channel, value).value,
        "measured_at": measured_at.replace("+00:00", "Z"),
        "owner_id": reading.owner_id,
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


class DictionaryPayload(TypedDict):
    """The static dictionary for the frontend (docs/json-shape.md, section 3)."""

    environments: list[EnvironmentEntry]
    channels: dict[str, ChannelEntry]


def dictionary_payload() -> DictionaryPayload:
    """Environments and per-channel display text, all from core."""
    return {
        "environments": [{"id": k, **v} for k, v in ENVIRONMENTS.items()],
        "channels": {
            k: {
                "name": v["name"],
                "body_regions": list(v["body_regions"]),
                "explanation": v["explanation"],
            }
            for k, v in CHANNELS.items()
        },
    }
