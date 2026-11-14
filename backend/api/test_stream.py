import asyncio
import json
from datetime import UTC, datetime
from typing import cast

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from hydrograph_core import CHANNELS
from rest_framework.test import APIClient

from api import broadcast, stream, views
from api.models import Reading
from api.serializers import DictionaryPayload, dictionary_payload, reading_payload

AT = datetime(2026, 11, 14, 8, 0, tzinfo=UTC)
CREW = {"X-Simulation-Scope": "crew"}


@pytest.mark.django_db(transaction=True)
def test_connect_sends_dictionary_then_latest_per_channel() -> None:
    def create(channel: str, value: float, minute: int) -> None:
        measured_at = AT.replace(minute=minute)
        _ = Reading.objects.create(
            channel=channel, value=value, measured_at=measured_at
        )

    create("heart_rate", 1.2, minute=13)
    create("heart_rate", 1.7, minute=12)  # older, arrived later
    create("spo2", 0.97, minute=12)
    messages = stream.events()

    async def run() -> list[str]:
        try:
            return [await anext(messages) for _ in range(3)]
        finally:
            await messages.aclose()

    dictionary, *latest = async_to_sync(run)()

    assert dictionary.startswith("event: dictionary\ndata: ")
    payload = cast("DictionaryPayload", json.loads(dictionary.split("data: ", 1)[1]))
    assert payload == dictionary_payload()
    assert payload["environments"][0] == {
        "id": "lunar_surface",
        "gravity_g": 0.166,
        "comm_delay_s": 2.6,
    }
    assert payload["channels"]["bp_systolic"] == {
        "name": "Blood pressure (systolic)",
        "body_regions": ["heart", "chest"],
        "explanation": CHANNELS["bp_systolic"]["explanation"],
    }
    assert sorted(latest) == sorted(
        [
            stream.sse_event("reading", reading_payload(reading))
            for reading in Reading.objects.filter(value__in=[1.2, 0.97])
        ]
    )


@pytest.mark.django_db(transaction=True)
def test_published_message_reaches_open_stream_and_close_unsubscribes() -> None:
    messages = stream.events()

    async def run() -> str:
        try:
            _ = await anext(messages)  # dictionary
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
    body = {
        "channel": "glucose",
        "value": 2.9,
        "unit": "mol/m^3",
        "measured_at": "2026-11-14T08:00:00Z",
    }

    response = APIClient().post(reverse("readings"), body, format="json", headers=CREW)

    assert response.status_code == 201
    payload = cast("dict[str, object]", response.json())
    assert published == [stream.sse_event("reading", payload)]


def test_stream_is_get_only() -> None:
    assert APIClient().post(reverse("stream")).status_code == 405
