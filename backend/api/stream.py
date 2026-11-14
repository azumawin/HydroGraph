"""Server-sent events for the frontend: environments, then readings as they arrive.

Message data follows docs/json-shape.md.
"""

import json
from collections.abc import AsyncGenerator, Mapping

from hydrograph_core import CHANNELS, ENVIRONMENTS

from api import broadcast
from api.models import Reading
from api.serializers import reading_payload


def sse_event(event: str, data: Mapping[str, object]) -> str:
    """One SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def events() -> AsyncGenerator[str]:
    """Yield the environments, the latest reading per channel, then live readings.

    Subscribes before reading the snapshot, so a reading posted in between is
    sent twice at worst, never lost. A reconnect gets a fresh snapshot.
    """
    yield sse_event(
        "environments",
        {"environments": [{"id": k, **v} for k, v in ENVIRONMENTS.items()]},
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
