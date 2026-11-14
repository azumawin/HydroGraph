import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from rest_framework.test import APIClient

from api import broadcast, stream, views
from api.models import Reading

AT = datetime(2026, 11, 8, 7, 12, tzinfo=UTC)


@pytest.mark.django_db(transaction=True)
def test_connect_sends_environments_then_latest_per_channel() -> None:
    _ = Reading.objects.create(channel="heart_rate", value=72, measured_at=AT)
    _ = Reading.objects.create(
        channel="heart_rate", value=104, measured_at=AT.replace(minute=13)
    )
    _ = Reading.objects.create(channel="spo2", value=89, measured_at=AT)
    messages = stream.events()

    async def run() -> list[str]:
        try:
            return [await anext(messages) for _ in range(3)]
        finally:
            await messages.aclose()

    environments, heart_rate, spo2 = async_to_sync(run)()

    assert environments == (
        "event: environments\n"
        'data: {"environments": ['
        '{"id": "lunar_surface", "gravity_g": 0.166, "comm_delay_s": 2.6}, '
        '{"id": "mars_surface", "gravity_g": 0.377, "comm_delay_s": 600.0}]}\n\n'
    )
    assert heart_rate.startswith("event: reading\ndata: ")
    assert '"value": 104.0' in heart_rate and '"evaluation": "warning"' in heart_rate
    assert '"channel": "spo2"' in spo2 and '"evaluation": "critical"' in spo2


@pytest.mark.django_db(transaction=True)
def test_published_message_reaches_open_stream_and_close_unsubscribes() -> None:
    messages = stream.events()

    async def run() -> str:
        try:
            _ = await anext(messages)  # environments
            pending = asyncio.ensure_future(anext(messages))
            while not broadcast._queues:  # pyright: ignore[reportPrivateUsage]
                await asyncio.sleep(0)
            broadcast.publish("event: test\ndata: {}\n\n")  # not in the DB
            return await asyncio.wait_for(pending, timeout=1)
        finally:
            await messages.aclose()

    assert async_to_sync(run)() == "event: test\ndata: {}\n\n"
    assert not broadcast._queues  # pyright: ignore[reportPrivateUsage]


@pytest.mark.django_db
def test_post_publishes_the_reading_it_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[str] = []
    monkeypatch.setattr(views, "publish", published.append)
    body = {"channel": "glucose", "value": 2.9, "measured_at": "2026-11-08T07:12:00Z"}

    response = APIClient().post(reverse("readings"), body, format="json")

    assert response.status_code == 201
    payload = cast("dict[str, object]", response.json())
    assert published == [stream.sse_event("reading", payload)]


def test_stream_is_get_only() -> None:
    assert APIClient().post(reverse("stream")).status_code == 405
