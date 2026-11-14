from datetime import datetime
from typing import override

from django.db import models


class Reading(models.Model):
    """One sensor value as sent by the device; evaluated on the way out."""

    channel: models.CharField[str, str] = models.CharField(max_length=64)
    value: models.FloatField[float, float] = models.FloatField()
    measured_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()
    received_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes: tuple[models.Index, ...] = (
            models.Index(fields=["channel", "-measured_at"]),
        )

    @override
    def __str__(self) -> str:
        return f"{self.channel}={self.value} @ {self.measured_at:%Y-%m-%dT%H:%M:%SZ}"
