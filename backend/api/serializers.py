"""DRF serializers for the api app.

Keep these thin: validation and shaping only. Domain logic belongs in
`hydrograph_core` (or another package under `packages/`).
"""

from typing import Any

from hydrograph_core import CHANNELS, evaluate_reading
from rest_framework import serializers

from api.models import Reading


class ReadingInSerializer(serializers.ModelSerializer[Reading]):
    """What the device sends (docs/json-shape.md, "backend receives this")."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]  # DRF stubs
        model = Reading
        fields = ("channel", "value", "measured_at")

    def validate_channel(self, value: str) -> str:
        if value not in CHANNELS:
            raise serializers.ValidationError(f'Unknown channel "{value}".')
        return value


class ReadingOutSerializer(serializers.ModelSerializer[Reading]):
    """What the frontend gets (docs/json-shape.md, reading shape)."""

    unit = serializers.SerializerMethodField()
    evaluation = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    body_regions = serializers.SerializerMethodField()
    explanation = serializers.SerializerMethodField()

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]  # DRF stubs
        model = Reading
        fields = (
            "channel",
            "value",
            "unit",
            "evaluation",
            "measured_at",
            "name",
            "body_regions",
            "explanation",
        )

    def get_unit(self, obj: Reading) -> str:
        return CHANNELS[obj.channel]["unit"]

    def get_evaluation(self, obj: Reading) -> str:
        return evaluate_reading(obj.channel, obj.value).value

    def get_name(self, obj: Reading) -> str:
        return CHANNELS[obj.channel]["name"]

    def get_body_regions(self, obj: Reading) -> list[str]:
        return list(CHANNELS[obj.channel]["body_regions"])

    def get_explanation(self, obj: Reading) -> str:
        return CHANNELS[obj.channel]["explanation"]


def reading_payload(reading: Reading) -> dict[str, Any]:
    """The frontend shape of one reading, as sent by POST and the stream."""
    return dict(ReadingOutSerializer(reading).data)
