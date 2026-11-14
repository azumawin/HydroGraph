"""Server-sent events for the frontend: the dictionary, then readings as they arrive.

Message data follows docs/json-shape.md.
"""

import json
from collections.abc import AsyncGenerator, Mapping
from typing import cast

from django.db.models import QuerySet

from api import broadcast
from api.models import Reading
from api.serializers import dictionary_payload, reading_payload


def sse_event(event: str, data: Mapping[str, object]) -> str:
    """One SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def events() -> AsyncGenerator[str]:
    """Yield the dictionary, the latest reading per owner and channel, then live ones.

    Subscribes before reading the snapshot, so a reading posted in between is
    sent twice at worst, never lost. A reconnect gets a fresh snapshot.
    """
    yield sse_event("dictionary", dictionary_payload())
    with broadcast.subscribe() as queue:
        pairs = cast(
            "QuerySet[Reading, tuple[str, str]]",
            Reading.objects.order_by().values_list("owner_id", "channel").distinct(),
        )
        for owner_id, channel in [pair async for pair in pairs]:
            latest = await (
                Reading.objects.filter(owner_id=owner_id, channel=channel)
                .order_by("-measured_at", "-id")
                .afirst()
            )
            if latest is not None:
                yield sse_event("reading", reading_payload(latest))
        while True:
            yield await queue.get()
