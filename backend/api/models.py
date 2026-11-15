from datetime import datetime

from django.db import models


class Reading(models.Model):
    """One sensor value as sent by the device; evaluated on the way out."""

    channel: models.CharField[str, str] = models.CharField(max_length=64)
    # number, boolean for flags, ACVPU text
    value: models.JSONField = models.JSONField()
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


class FindingRule(models.Model):
    """A custom rule's source, or a built-in rule's enabled state.

    Built-in rules come from ``core.rules`` and have a row only once toggled;
    their ``source`` stays empty.
    """

    rule_id: models.CharField[str, str] = models.CharField(max_length=64, unique=True)
    source: models.TextField[str, str] = models.TextField(blank=True)
    enabled: models.BooleanField[bool, bool] = models.BooleanField(default=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True
    )
