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
    Display,
    EnvironmentInfo,
    Evaluation,
    FindingResult,
    Severity,
    evaluate_reading,
)
from rest_framework import serializers

from api.models import Reading

# The one enum channel, consciousness_level; core rejects anything else.
ACVPU = ("ALERT", "CONFUSION", "VOICE", "PAIN", "UNRESPONSIVE")


class ReadingIn(TypedDict):
    """``validated_data`` of :class:`ReadingInSerializer`."""

    channel: str
    value: float | bool | str
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
        if info["value_type"] == "enum":
            valid = value in ACVPU
        elif info["value_type"] == "boolean":
            valid = isinstance(value, bool)
        else:
            valid = (
                isinstance(value, int | float)
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
        if not valid:
            expected = (
                f"one of {', '.join(ACVPU)}"
                if info["value_type"] == "enum"
                else f"a {info['value_type']}"
            )
            errors["value"] = [f"Expected {expected} for {channel}."]
        if context["scope"] != info["scope"]:
            errors["X-Simulation-Scope"] = [
                f'Expected "{info["scope"]}" for {channel}.'
            ]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class HistoryQuery(TypedDict):
    """``validated_data`` of :class:`HistoryQuerySerializer`."""

    channel: list[str]
    limit: int


class HistoryQuerySerializer(serializers.Serializer[None]):
    """The query of ``GET /api/readings/``: which channels, how many readings each."""

    channel: serializers.ListField = serializers.ListField(
        child=serializers.ChoiceField(choices=list(CHANNELS)), required=False
    )
    limit: serializers.IntegerField = serializers.IntegerField(
        min_value=1, max_value=1000, default=120
    )


class ReadingPayload(TypedDict):
    """A reading for the frontend (docs/json-shape.md, section 2).

    Only what changes per reading; unit and scope are per channel, in the
    dictionary.
    """

    channel: str
    value: float | bool | str
    measured_at: str
    evaluation: Evaluation


def reading_payload(reading: Reading, environment: EnvironmentInfo) -> ReadingPayload:
    """The frontend shape of one reading, as sent by POST and the stream.

    ``environment`` is the one in effect; the dose rate is graded against it.
    """
    value = cast("float | bool | str", reading.value)
    measured_at = reading.measured_at.astimezone(UTC).isoformat()
    return {
        "channel": reading.channel,
        "value": value,
        "measured_at": measured_at.replace("+00:00", "Z"),
        "evaluation": evaluate_reading(reading.channel, value, environment=environment),
    }


class ChannelEntry(TypedDict):
    name: str
    scope: Literal["crew", "environment"]
    unit: str
    display: Display
    body_regions: list[str]
    explanation: str


class FindingEntry(TypedDict):
    name: str
    channels: list[str]


class DictionaryPayload(TypedDict):
    """The static dictionary for the frontend (docs/json-shape.md, section 4).

    Every section is keyed by id, in core's order.
    """

    environments: dict[str, EnvironmentInfo]
    channels: dict[str, ChannelEntry]
    findings: dict[str, FindingEntry]


def environments_payload() -> dict[str, EnvironmentInfo]:
    """Every mission environment by id, in core's (dropdown) order.

    Served on its own by ``GET /api/environments/`` and as part of the stream
    dictionary, so the two always describe the same set.
    """
    return dict(ENVIRONMENTS)


def dictionary_payload() -> DictionaryPayload:
    """Environments, channel metadata and findings, all from core."""
    return {
        "environments": environments_payload(),
        "channels": {
            k: {
                "name": v["name"],
                "scope": v["scope"],
                "unit": v["unit"],
                "display": v["display"],
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


class FindingPayload(TypedDict):
    """A finding for the frontend (docs/json-shape.md, section 3)."""

    id: str
    status: Severity
    triggers: list[str]
    action: str
    values: dict[str, object]


def finding_payload(finding: str, result: FindingResult) -> FindingPayload:
    """Core's result in one shape for every finding.

    A single-severity finding's ``True`` / ``False`` becomes ``"warning"`` /
    ``"nominal"``; the finding's own evaluated quantities go under ``values``.
    """
    fields: dict[str, object] = dict(result)
    status = fields.pop("status")
    triggers = cast("list[str]", fields.pop("triggers"))
    action = cast("str", fields.pop("action"))
    if isinstance(status, bool):
        status = "warning" if status else "nominal"
    return {
        "id": finding,
        "status": cast("Severity", status),
        "triggers": triggers,
        "action": action,
        "values": fields,
    }


class EnvironmentSelectionSerializer(serializers.Serializer[None]):
    """The body of ``PUT /api/environment/``."""

    id: serializers.ChoiceField = serializers.ChoiceField(choices=list(ENVIRONMENTS))


class ChatMessageSerializer(serializers.Serializer[None]):
    role: serializers.ChoiceField = serializers.ChoiceField(
        choices=["user", "assistant"]
    )
    content: serializers.CharField = serializers.CharField(max_length=4000)


class ChatSerializer(serializers.Serializer[None]):
    """The body of ``POST /api/assistant/``: the conversation, oldest first."""

    messages: ChatMessageSerializer = ChatMessageSerializer(
        many=True, allow_empty=False
    )

    def validate_messages(self, value: list[object]) -> list[object]:
        if len(value) > 40:
            raise serializers.ValidationError("At most 40 messages.")
        return value
