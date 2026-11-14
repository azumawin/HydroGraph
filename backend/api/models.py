from datetime import datetime

from django.db import models


class Reading(models.Model):
    """One sensor value as sent by the device; evaluated on the way out."""

    channel: models.CharField[str, str] = models.CharField(max_length=64)
    value: models.JSONField = models.JSONField()  # number, boolean for flags, ACVPU text
    measured_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()

    class Meta:
        indexes: tuple[models.Index, ...] = (
            models.Index(fields=["channel", "-measured_at"]),
        )


class EnvironmentSelection(models.Model):
    """One switch of the mission environment; the latest row is in effect."""

    environment_id: models.CharField[str, str] = models.CharField(max_length=64)
    selected_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True
    )
