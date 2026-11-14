"""Server-sent events for the frontend: the dictionary, then readings and findings.

Message data follows docs/json-shape.md.
"""

import json
from collections.abc import AsyncGenerator, Mapping

from asgiref.sync import sync_to_async
from hydrograph_core import CHANNELS

from api import broadcast
from api.findings import crew_findings
from api.models import Reading
from api.serializers import dictionary_payload, finding_payload, reading_payload


def sse_event(event: str, data: Mapping[str, object]) -> str:
    """One SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def events() -> AsyncGenerator[str]:
    """Yield the dictionary, the latest reading per channel, the current findings,
    then live readings and findings.

    Subscribes before reading the snapshot, so a message posted in between is
    sent twice at worst, never lost. A reconnect gets a fresh snapshot.
    """
    yield sse_event("dictionary", dictionary_payload())
    with broadcast.subscribe() as queue:
        for channel in CHANNELS:
            latest = await (
                Reading.objects.filter(channel=channel)
                .order_by("-measured_at", "-id")
                .afirst()
            )
            if latest is not None:
                yield sse_event("reading", reading_payload(latest))
        for finding, result in (await sync_to_async(crew_findings)()).items():
            yield sse_event("finding", finding_payload(finding, result))
        while True:
            yield await queue.get()
