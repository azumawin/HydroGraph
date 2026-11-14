"""Server-sent events for the frontend: environment, then readings as they arrive.

The stream polls the database for readings newer than the last one sent, so
it needs no broker and resumes from the browser's ``Last-Event-ID``.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Mapping

from django.db.models import Max
from hydrograph_core import CHANNELS, ENVIRONMENTS

from api.models import Reading
from api.serializers import reading_payload

POLL_INTERVAL_S = 1.0
KEEPALIVE_INTERVAL_S = 15.0


def sse_event(
    event: str, data: Mapping[str, object], event_id: int | None = None
) -> str:
    """One SSE message; ``id:`` comes first so the browser records it."""
    lines = [] if event_id is None else [f"id: {event_id}"]
    lines += [f"event: {event}", f"data: {json.dumps(data, ensure_ascii=False)}"]
    return "\n".join(lines) + "\n\n"


async def events(environment_id: str, after_id: int | None) -> AsyncGenerator[str]:
    """Yield SSE messages forever.

    Args:
        environment_id: A key of ``ENVIRONMENTS``.
        after_id: The client's ``Last-Event-ID``. ``None`` on a fresh connect,
            which sends the latest reading per channel; otherwise every reading
            after this id is replayed.
    """
    environment = ENVIRONMENTS[environment_id]
    yield sse_event(
        "environment",
        {
            "id": environment_id,
            **environment,
        },
    )

    if after_id is None:
        aggregate = await Reading.objects.aaggregate(newest=Max("id"))
        newest: int = aggregate["newest"] or 0
        snapshot: list[Reading] = []
        for channel in CHANNELS:
            latest = await (
                Reading.objects.filter(channel=channel, id__lte=newest)
                .order_by("-measured_at", "-id")
                .afirst()
            )
            if latest is not None:
                snapshot.append(latest)
        for reading in sorted(snapshot, key=lambda r: r.pk):
            yield sse_event("reading", reading_payload(reading), reading.pk)
        # An id-only message moves the browser's Last-Event-ID to `newest`
        # without dispatching an event, so a reconnect skips stale readings.
        yield f"id: {newest}\n\n"
        after_id = newest

    idle_s = 0.0
    while True:
        new = [r async for r in Reading.objects.filter(id__gt=after_id).order_by("id")]
        for reading in new:
            yield sse_event("reading", reading_payload(reading), reading.pk)
            after_id = reading.pk
        if new:
            idle_s = 0.0
        elif idle_s >= KEEPALIVE_INTERVAL_S:
            yield ": keepalive\n\n"
            idle_s = 0.0
        await asyncio.sleep(POLL_INTERVAL_S)
        idle_s += POLL_INTERVAL_S
