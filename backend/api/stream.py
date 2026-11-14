"""Server-sent events for the frontend: environment, then readings as they arrive."""

import json
from collections.abc import AsyncGenerator, Mapping

from hydrograph_core import CHANNELS, ENVIRONMENTS

from api import broadcast
from api.models import Reading
from api.serializers import reading_payload


def sse_event(event: str, data: Mapping[str, object]) -> str:
    """One SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def events(environment_id: str) -> AsyncGenerator[str]:
    """Yield the environment, the latest reading per channel, then live readings.

    Subscribes before reading the snapshot, so a reading posted in between is
    sent twice at worst, never lost. A reconnect gets a fresh snapshot.
    """
    yield sse_event(
        "environment", {"id": environment_id, **ENVIRONMENTS[environment_id]}
    )
    with broadcast.subscribe() as queue:
        for channel in CHANNELS:
            latest = await (
                Reading.objects.filter(channel=channel)
                .order_by("-measured_at", "-id")
                .afirst()
            )
            if latest is not None:
                yield sse_event("reading", reading_payload(latest))
        while True:
            yield await queue.get()
