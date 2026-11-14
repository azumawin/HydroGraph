"""Request validation and wire shapes for the async API.

Domain logic belongs in ``core``; this module only validates incoming JSON and
shapes outgoing payloads for ``docs/json-shape.md``.
"""

import math
from datetime import UTC, datetime
from typing import Literal, TypedDict, cast

from django.http import QueryDict
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from api.models import Reading
from core import (
    ACVPU,
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

ERRORS = dict[str, list[str]]
ReadingValue = float | bool | str


class ReadingIn(TypedDict):
    channel: str
    value: ReadingValue
    unit: str
    measured_at: datetime


class HistoryQuery(TypedDict):
    channel: list[str]
    limit: int


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ReadingPayload(TypedDict):
    channel: str
    value: ReadingValue
    measured_at: str
    evaluation: Evaluation


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
    environments: dict[str, EnvironmentInfo]
    channels: dict[str, ChannelEntry]
    findings: dict[str, FindingEntry]


class FindingPayload(TypedDict):
    id: str
    status: Severity
    triggers: list[str]
    action: str
    values: dict[str, object]


def reading_payload(reading: Reading, environment: EnvironmentInfo) -> ReadingPayload:
    """The frontend shape of one reading, as sent by POST and the stream."""
    value = cast("ReadingValue", reading.value)
    measured_at = reading.measured_at.astimezone(UTC).isoformat()
    return {
        "channel": reading.channel,
        "value": value,
        "measured_at": measured_at.replace("+00:00", "Z"),
        "evaluation": evaluate_reading(reading.channel, value, environment=environment),
    }


def environments_payload() -> dict[str, EnvironmentInfo]:
    """Every mission environment by id, in core's (dropdown) order."""
    return dict(ENVIRONMENTS)


def dictionary_payload() -> DictionaryPayload:
    """Environments, channel metadata and findings, all from core."""
    return {
        "environments": environments_payload(),
        "channels": {
            key: {
                "name": info["name"],
                "scope": info["scope"],
                "unit": info["unit"],
                "display": info["display"],
                "body_regions": list(info["body_regions"]),
                "explanation": info["explanation"],
            }
            for key, info in CHANNELS.items()
        },
        "findings": {
            key: {"name": info["name"], "channels": list(info["channels"])}
            for key, info in FINDINGS.items()
        },
    }


def finding_payload(finding: str, result: FindingResult) -> FindingPayload:
    """Core's result in one shape for every finding."""
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


def parse_reading(payload: object, scope: str) -> tuple[ReadingIn | None, ERRORS]:
    """Validate one POSTed reading; preserve the old DRF field errors."""
    if not isinstance(payload, dict):
        return None, {"detail": ["Expected a JSON object."]}

    data = cast("dict[str, object]", payload)
    errors: ERRORS = {}
    channel = data.get("channel")
    info = CHANNELS.get(channel) if isinstance(channel, str) else None
    if info is None:
        errors["channel"] = [
            (
                f'Unknown channel "{channel}".'
                if isinstance(channel, str)
                else "This field is required."
            )
        ]

    unit = data.get("unit")
    if not isinstance(unit, str):
        errors["unit"] = ["This field is required."]
    elif info is not None and unit != info["unit"]:
        errors["unit"] = [f'Expected "{info["unit"]}" for {channel}.']

    value = data.get("value")
    if value is None:
        errors["value"] = ["This field is required."]
    elif info is not None:
        expected = _value_error(info["value_type"], value, cast("str", channel))
        if expected is not None:
            errors["value"] = [expected]

    measured_at = data.get("measured_at")
    parsed_at = parse_datetime(measured_at) if isinstance(measured_at, str) else None
    if parsed_at is not None and timezone.is_naive(parsed_at):
        parsed_at = timezone.make_aware(parsed_at)
    if not isinstance(measured_at, str):
        errors["measured_at"] = ["This field is required."]
    elif parsed_at is None:
        errors["measured_at"] = ["A valid date-time is required."]

    if info is not None and scope != info["scope"]:
        errors["X-Simulation-Scope"] = [f'Expected "{info["scope"]}" for {channel}.']

    if errors:
        return None, errors
    return {
        "channel": cast("str", channel),
        "value": cast("ReadingValue", value),
        "unit": cast("str", unit),
        "measured_at": cast("datetime", parsed_at),
    }, {}


def _value_error(
    value_type: Literal["number", "boolean", "enum"], value: object, channel: str
) -> str | None:
    if value_type == "enum":
        if isinstance(value, str) and value in ACVPU:
            return None
        return f"Expected one of {', '.join(ACVPU)} for {channel}."
    if value_type == "boolean":
        if isinstance(value, bool):
            return None
        return f"Expected a boolean for {channel}."
    if (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    ):
        return None
    return f"Expected a number for {channel}."


def parse_history_query(query: QueryDict) -> tuple[HistoryQuery | None, ERRORS]:
    errors: ERRORS = {}
    channels = query.getlist("channel")
    invalid = [channel for channel in channels if channel not in CHANNELS]
    if invalid:
        errors["channel"] = [
            f'"{channel}" is not a valid choice.' for channel in invalid
        ]

    raw_limit = query.get("limit", "120")
    try:
        limit = int(raw_limit)
    except ValueError:
        errors["limit"] = ["A valid integer is required."]
        limit = 120
    else:
        if limit < 1:
            errors["limit"] = ["Ensure this value is greater than or equal to 1."]
        elif limit > 1000:
            errors["limit"] = ["Ensure this value is less than or equal to 1000."]

    if errors:
        return None, errors
    return {"channel": channels, "limit": limit}, {}


def parse_chat(payload: object) -> tuple[list[ChatMessage] | None, ERRORS]:
    if not isinstance(payload, dict):
        return None, {"detail": ["Expected a JSON object."]}

    messages = cast("dict[str, object]", payload).get("messages")
    if not isinstance(messages, list) or not messages:
        return None, {"messages": ["This field is required."]}
    items = cast("list[object]", messages)
    if len(items) > 40:
        return None, {"messages": ["At most 40 messages."]}

    parsed: list[ChatMessage] = []
    errors: list[str] = []
    for index, message in enumerate(items):
        if not isinstance(message, dict):
            errors.append(f"Message {index}: expected an object.")
            continue
        item = cast("dict[str, object]", message)
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant"):
            errors.append(f'Message {index}: "{role}" is not a valid role.')
        if not isinstance(content, str):
            errors.append(f"Message {index}: content is required.")
        elif len(content) > 4000:
            errors.append(f"Message {index}: content exceeds 4000 characters.")
        if (
            role in ("user", "assistant")
            and isinstance(content, str)
            and len(content) <= 4000
        ):
            parsed.append({"role": role, "content": content})
    if errors:
        return None, {"messages": errors}
    return parsed, {}


def parse_environment(payload: object) -> tuple[str | None, ERRORS]:
    if not isinstance(payload, dict):
        return None, {"detail": ["Expected a JSON object."]}
    environment_id = cast("dict[str, object]", payload).get("id")
    if not isinstance(environment_id, str):
        return None, {"id": ["This field is required."]}
    if environment_id not in ENVIRONMENTS:
        return None, {"id": [f'"{environment_id}" is not a valid choice.']}
    return environment_id, {}
