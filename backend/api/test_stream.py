import asyncio
from datetime import UTC, datetime

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from django.urls import reverse
from rest_framework.test import APIClient

from api import broadcast, stream
from api.models import Reading

AT = datetime(2026, 11, 8, 7, 12, tzinfo=UTC)


@pytest.mark.django_db(transaction=True)
def test_connect_sends_environment_then_latest_per_channel() -> None:
    _ = Reading.objects.create(channel="heart_rate", value=72, measured_at=AT)
    _ = Reading.objects.create(
        channel="heart_rate", value=104, measured_at=AT.replace(minute=13)
    )
    _ = Reading.objects.create(channel="spo2", value=89, measured_at=AT)
    messages = stream.events("lunar_surface")

    async def run() -> list[str]:
        try:
            return [await anext(messages) for _ in range(3)]
        finally:
            await messages.aclose()

    environment, heart_rate, spo2 = async_to_sync(run)()

    assert environment == (
        "event: environment\n"
        'data: {"id": "lunar_surface", "gravity_g": 0.166, "comm_delay_s": 2.6}\n\n'
    )
    assert heart_rate.startswith("event: reading\ndata: ")
    assert '"value": 104.0' in heart_rate and '"evaluation": "warning"' in heart_rate
    assert '"channel": "spo2"' in spo2 and '"evaluation": "critical"' in spo2


@pytest.mark.django_db(transaction=True)
def test_post_is_pushed_to_open_streams_immediately() -> None:
    body = [{"channel": "glucose", "value": 2.9, "measured_at": "2026-11-08T07:12:00Z"}]
    messages = stream.events("mars_surface")

    async def run() -> tuple[str, str]:
        try:
            environment = await anext(messages)
            pending = asyncio.ensure_future(anext(messages))  # now subscribed
            await asyncio.sleep(0)
            response = await sync_to_async(APIClient().post)(
                reverse("readings"), body, format="json"
            )
            assert response.status_code == 201
            return environment, await asyncio.wait_for(pending, timeout=0.5)
        finally:
            await messages.aclose()

    environment, pushed = async_to_sync(run)()

    assert '"id": "mars_surface"' in environment
    assert pushed.startswith("event: reading\ndata: ")
    assert '"evaluation": "critical"' in pushed and '"unit": "mmol/L"' in pushed
    assert not broadcast._queues  # pyright: ignore[reportPrivateUsage]


@pytest.mark.django_db
def test_stream_rejects_unknown_environment() -> None:
    response = APIClient().get(reverse("stream"), {"environment": "mars_orbit"})

    assert response.status_code == 400
    assert response.json() == {
        "environment": [
            'Unknown environment "mars_orbit". Choose: lunar_surface, mars_surface.'
        ]
    }
