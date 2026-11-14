"""Server-sent events for the frontend: the dictionary, then readings and findings.

Message data follows docs/json-shape.md.
"""

import json
from collections.abc import AsyncGenerator, Mapping
from typing import cast

from asgiref.sync import sync_to_async
from django.db.models import QuerySet

from api import broadcast
from api.findings import crew_findings, crew_owners
from api.models import Reading
from api.serializers import dictionary_payload, finding_payload, reading_payload


def sse_event(event: str, data: Mapping[str, object]) -> str:
    """One SSE message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def events() -> AsyncGenerator[str]:
    """Yield the dictionary, the latest reading per owner and channel, every crew
    member's findings, then live readings and findings.

    Subscribes before reading the snapshot, so a message posted in between is
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
        for owner_id in await sync_to_async(crew_owners)():
            results = await sync_to_async(crew_findings)(owner_id)
            for finding, result in results.items():
                yield sse_event("finding", finding_payload(owner_id, finding, result))
        while True:
            yield await queue.get()
