"""DRF serializers for the api app.

Keep these thin: validation and shaping only. Domain logic belongs in
`hydrograph_core` (or another package under `packages/`).
"""

from datetime import UTC
from typing import TypedDict

from hydrograph_core import CHANNELS, evaluate_reading
from rest_framework import serializers

from api.models import Reading


class ReadingInSerializer(serializers.ModelSerializer[Reading]):
    """What the device sends (docs/json-shape.md, "backend receives this")."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]  # DRF stubs
        model: type[Reading] = Reading
        fields: tuple[str, ...] = ("channel", "value", "measured_at")

    def validate_channel(self, value: str) -> str:
        if value not in CHANNELS:
            raise serializers.ValidationError(f'Unknown channel "{value}".')
        return value


class ReadingPayload(TypedDict):
    """What the frontend gets (docs/json-shape.md, reading shape)."""

    channel: str
    value: float
    unit: str
    evaluation: str
    measured_at: str
    name: str
    body_regions: list[str]
    explanation: str


def reading_payload(reading: Reading) -> ReadingPayload:
    """The frontend shape of one reading, as sent by POST and the stream."""
    info = CHANNELS[reading.channel]
    measured_at = reading.measured_at.astimezone(UTC).isoformat()
    return {
        "channel": reading.channel,
        "value": reading.value,
        "unit": info["unit"],
        "evaluation": evaluate_reading(reading.channel, reading.value).value,
        "measured_at": measured_at.replace("+00:00", "Z"),
        "name": info["name"],
        "body_regions": list(info["body_regions"]),
        "explanation": info["explanation"],
    }
