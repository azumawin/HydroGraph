"""The health assistant: an LLM on Ollama Cloud, briefed with the live state.

Every request carries the environment, the current findings and the latest
reading of every channel, so the model's advice follows the dashboard.
"""

import json
import urllib.error
import urllib.request
from typing import Literal, TypedDict, cast

from django.conf import settings
from hydrograph_core import CHANNELS

from api.environment import current_environment
from api.findings import crew_findings
from api.models import Reading
from api.serializers import finding_payload, reading_payload

# Model families from Chinese labs; the project does not use them.
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
Keep answers short: a few sentences or a short list. No markdown tables.
"""


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class AssistantError(Exception):
    """The LLM could not answer; the message is safe to show the user."""


def is_blocked_model(model: str) -> bool:
    name = model.lower().rsplit("/", 1)[-1]
    return name.startswith(BLOCKED_MODEL_PREFIXES)


def briefing() -> str:
    """The live state, as JSON for the model."""
    environment = current_environment()
    findings = [finding_payload(f, r) for f, r in crew_findings(environment).items()]
    readings: dict[str, object] = {}
    for channel, info in CHANNELS.items():
        latest = (
            Reading.objects.filter(channel=channel)
            .order_by("-measured_at", "-id")
            .first()
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


def reply(messages: list[ChatMessage]) -> str:
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
        "messages": [{"role": "system", "content": briefing()}, *messages],
    }
    request = urllib.request.Request(
        cast("str", settings.OLLAMA_URL),
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=cast("float", settings.OLLAMA_TIMEOUT_S)
        ) as response:
            data = cast("dict[str, object]", json.load(response))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise AssistantError("The assistant could not reach the model.") from error
    message = data.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise AssistantError("The model returned an empty answer.")
    return content.strip()
