"""The health assistant: an LLM on Ollama Cloud, briefed with the live state.

Every request carries the environment, the current findings and the latest
reading of every channel, so the model's advice follows the dashboard.
"""

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import IO, cast

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest

from api.contracts import ChatMessage, finding_payload, reading_payload
from api.environment import current_environment
from api.findings import crew_findings
from api.models import Reading
from core import CHANNELS

BLOCKED_MODEL_PREFIXES = (
    "deepseek",
    "qwen",
    "qwq",
    "kimi",
    "glm",
    "minimax",
    "yi",
    "baichuan",
    "internlm",
    "ernie",
    "hunyuan",
    "doubao",
    "step",
)

INSTRUCTIONS = """\
You are the health assistant on a crewed space mission's medical dashboard.
You monitor one astronaut. Below is the live state: the mission environment,
the findings the monitoring system computed, and the latest reading of each
channel with its grade.

Report findings plainly, warning and critical first, and give practical,
specific advice the crew can act on. Base everything on the data below; say so
when data is missing. You support the crew and flight surgeon, you do not
replace them: for anything critical, tell them to contact the flight surgeon.
Keep answers short: a few sentences or a short list. Plain text only, no
markdown: no tables, bold or headings; use "- " for list items.
"""

RATE_PERIODS = {
    "s": 1,
    "sec": 1,
    "m": 60,
    "min": 60,
    "h": 3600,
    "hour": 3600,
    "d": 86400,
    "day": 86400,
}


class AssistantError(Exception):
    """The LLM could not answer; the message is safe to show the user."""


def is_blocked_model(model: str) -> bool:
    name = model.lower().rsplit("/", 1)[-1]
    return name.startswith(BLOCKED_MODEL_PREFIXES)


async def is_rate_limited(request: HttpRequest) -> bool:
    """Count assistant calls per client IP in the cache."""
    client_ip = cast("str", request.META.get("REMOTE_ADDR", "unknown"))
    for setting, period in (
        ("ASSISTANT_RATE", "minute"),
        ("ASSISTANT_DAILY_RATE", "day"),
    ):
        limit, window = _parse_rate(cast("str", getattr(settings, setting)))
        key = f"assistant:{period}:{client_ip}"
        current = cast("int", await cache.aget(key, 0))
        if current >= limit:
            return True
        _ = await cache.aadd(key, 0, window)
        _ = await cache.aincr(key)
    return False


def _parse_rate(rate: str) -> tuple[int, int]:
    count, period = rate.strip().split("/", 1)
    return int(count), RATE_PERIODS[period]


async def briefing() -> str:
    """The live state, as JSON for the model."""
    environment = await current_environment()
    findings = [
        finding_payload(finding, result)
        for finding, result in (await crew_findings(environment)).items()
    ]
    readings: dict[str, object] = {}
    for channel, info in CHANNELS.items():
        latest = await (
            Reading.objects.filter(channel=channel)
            .order_by("-measured_at", "-id")
            .afirst()
        )
        if latest is not None:
            payload = reading_payload(latest, environment)
            readings[channel] = {
                "name": info["name"],
                "value": payload["value"],
                "unit": info["unit"],
                "evaluation": payload["evaluation"],
                "measured_at": payload["measured_at"],
            }
    state = {"environment": environment, "findings": findings, "readings": readings}
    return INSTRUCTIONS + "\n" + json.dumps(state, default=str)


async def reply(messages: list[ChatMessage]) -> str:
    """The model's answer to the conversation so far."""
    model = cast("str", settings.OLLAMA_MODEL)
    if is_blocked_model(model):
        raise AssistantError(f'Model "{model}" is not allowed; set OLLAMA_MODEL.')
    key = cast("str", settings.OLLAMA_API_KEY)
    if not key:
        raise AssistantError("The assistant is not configured: set OLLAMA_API_KEY.")
    body = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": await briefing()},
            *messages,
        ],
    }
    return await asyncio.to_thread(_post, body, key)


def _post(body: Mapping[str, object], key: str) -> str:
    request = urllib.request.Request(
        cast("str", settings.OLLAMA_URL),
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with cast(
            "IO[bytes]",
            urllib.request.urlopen(
                request, timeout=cast("float", settings.OLLAMA_TIMEOUT_S)
            ),
        ) as response:
            data = cast("dict[str, object]", json.load(response))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise AssistantError("The assistant could not reach the model.") from error
    message = data.get("message")
    content = (
        cast("dict[str, object]", message).get("content")
        if isinstance(message, dict)
        else None
    )
    if not isinstance(content, str) or not content.strip():
        raise AssistantError("The model returned an empty answer.")
    return content.strip()
