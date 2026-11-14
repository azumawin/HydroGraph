from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from rest_framework.test import APIClient

from api import stream
from api.models import Reading

AT = datetime(2026, 11, 8, 7, 12, tzinfo=UTC)


def take(messages: AsyncGenerator[str], n: int) -> list[str]:
    """The next ``n`` messages of an SSE generator, then close it."""

    async def run() -> list[str]:
        try:
            return [await anext(messages) for _ in range(n)]
        finally:
            await messages.aclose()

    return async_to_sync(run)()


@pytest.fixture(autouse=True)
def fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stream, "POLL_INTERVAL_S", 0.01)


@pytest.mark.django_db(transaction=True)
def test_fresh_connect_sends_environment_then_latest_per_channel() -> None:
    old = Reading.objects.create(channel="heart_rate", value=72, measured_at=AT)
    new = Reading.objects.create(
        channel="heart_rate", value=104, measured_at=AT.replace(minute=13)
    )
    spo2 = Reading.objects.create(channel="spo2", value=89, measured_at=AT)

    environment, first, second, marker = take(stream.events("lunar_surface", None), 4)

    assert environment == (
        "event: environment\n"
        'data: {"id": "lunar_surface", "gravity_g": 0.166, "comm_delay_s": 2.6}\n\n'
    )
    assert first.startswith(f"id: {new.pk}\nevent: reading\ndata: ")
    assert '"value": 104.0' in first and '"evaluation": "warning"' in first
    assert second.startswith(f"id: {spo2.pk}\nevent: reading\n")
    assert marker == f"id: {spo2.pk}\n\n"
    assert f"id: {old.pk}\n" not in first + second


@pytest.mark.django_db(transaction=True)
def test_new_readings_are_pushed_after_the_snapshot() -> None:
    messages = stream.events("mars_surface", None)

    async def run() -> list[str]:
        try:
            head = [await anext(messages) for _ in range(2)]  # environment, marker
            created = await Reading.objects.acreate(
                channel="glucose", value=2.9, measured_at=AT
            )
            pushed = await anext(messages)
            assert pushed.startswith(f"id: {created.pk}\nevent: reading\n")
            return [*head, pushed]
        finally:
            await messages.aclose()

    environment, marker, pushed = async_to_sync(run)()

    assert '"id": "mars_surface"' in environment
    assert marker == "id: 0\n\n"
    assert '"evaluation": "critical"' in pushed and '"unit": "mmol/L"' in pushed


@pytest.mark.django_db(transaction=True)
def test_reconnect_replays_readings_after_last_event_id() -> None:
    seen = Reading.objects.create(channel="spo2", value=97, measured_at=AT)
    missed = Reading.objects.create(channel="spo2", value=93, measured_at=AT)

    _, replayed = take(stream.events("lunar_surface", seen.pk), 2)

    assert replayed.startswith(f"id: {missed.pk}\nevent: reading\n")


@pytest.mark.django_db
def test_stream_rejects_unknown_environment() -> None:
    response = APIClient().get(reverse("stream"), {"environment": "mars_orbit"})

    assert response.status_code == 400
    assert response.json() == {
        "environment": [
            'Unknown environment "mars_orbit". Choose: lunar_surface, mars_surface.'
        ]
    }
