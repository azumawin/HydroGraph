"""Shared telemetry status definitions."""

from enum import Enum


class Status(str, Enum):
    """Classification of a calculated telemetry parameter."""

    CRITICAL = "critical"
    WARNING = "warning"
    NOMINAL = "nominal"
    UNSPECIFIED = "unspecified"
