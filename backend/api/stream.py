"""Server-sent events for the frontend: the dictionary, then readings and findings.

Message data follows docs/json-shape.md.
"""

import json
from collections.abc import AsyncGenerator, Mapping

from api import broadcast
from api.contracts import dictionary_payload, finding_payload, reading_payload
from api.environment import current_environment_id
from api.findings import crew_findings
from api.models import Reading
from api.rules import enabled_rules
from core import CHANNELS, ENVIRONMENTS


def sse_event(event: str, data: Mapping[str, object]) -> str:
    """One SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def events() -> AsyncGenerator[str]:
    """Yield the snapshot, then live messages.

    Subscribes before reading the snapshot, so a message posted in between is
    sent twice at worst, never lost. A reconnect gets a fresh snapshot.
    """
    yield sse_event("dictionary", dictionary_payload(await enabled_rules()))
    with broadcast.subscribe() as queue:
        environment_id = await current_environment_id()
        environment = ENVIRONMENTS[environment_id]
        yield sse_event("environment", {"id": environment_id})
        for channel in CHANNELS:
            latest = await (
                Reading.objects.filter(channel=channel)
                .order_by("-measured_at", "-id")
                .afirst()
            )
            if latest is not None:
                yield sse_event("reading", reading_payload(latest, environment))
        for finding, result in (await crew_findings(environment)).items():
            yield sse_event("finding", finding_payload(finding, result))
        while True:
            yield await queue.get()
