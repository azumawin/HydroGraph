from datetime import datetime

from django.db import models


class Reading(models.Model):
    """One sensor value as sent by the device; evaluated on the way out."""

    owner_id: models.CharField[str, str] = models.CharField(max_length=64)
    channel: models.CharField[str, str] = models.CharField(max_length=64)
    value: models.JSONField = models.JSONField()  # number, or boolean for flags
    measured_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()

    class Meta:
        indexes: tuple[models.Index, ...] = (
            models.Index(fields=["owner_id", "channel", "-measured_at"]),
        )
