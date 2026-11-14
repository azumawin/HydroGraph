"""In-process fan-out from POST /api/readings/ to every open SSE stream.

Each stream owns a queue; ``publish`` puts a message on all of them right away.
Works only while the server runs as a single process (``runserver``, the demo).
"""

import asyncio
from collections.abc import Generator
from contextlib import contextmanager

_queues: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[str]]] = set()


@contextmanager
def subscribe() -> Generator[asyncio.Queue[str]]:
    """A queue that receives every message published while the block is open."""
    entry = (asyncio.get_running_loop(), asyncio.Queue[str]())
    _queues.add(entry)
    try:
        yield entry[1]
    finally:
        _queues.discard(entry)


def publish(message: str) -> None:
    """Send ``message`` to every subscriber; safe to call from a sync view's thread."""
    for loop, queue in list(_queues):
        _ = loop.call_soon_threadsafe(queue.put_nowait, message)
