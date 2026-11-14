from typing import cast

import pytest
from django.urls import reverse
from hydrograph_core import CHANNELS
from rest_framework.test import APIClient

from api.models import Reading


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_health_is_public(client: APIClient) -> None:
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_schema_is_served(client: APIClient) -> None:
    response = client.get(reverse("schema"))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")


def test_docs_page_renders(client: APIClient) -> None:
    assert client.get(reverse("docs")).status_code == 200


TICK = "2026-11-08T07:12:00Z"


@pytest.mark.django_db
def test_post_reading_returns_doc_shape(client: APIClient) -> None:
    body = {"channel": "heart_rate", "value": 104, "measured_at": TICK}
    response = client.post(reverse("readings"), body, format="json")

    assert response.status_code == 201
    assert cast("dict[str, object]", response.json()) == {
        "channel": "heart_rate",
        "value": 104.0,
        "unit": "bpm",
        "evaluation": "warning",
        "measured_at": TICK,
        "name": "Heart rate",
        "body_regions": ["heart"],
        "explanation": CHANNELS["heart_rate"]["explanation"],
    }
    assert Reading.objects.count() == 1


@pytest.mark.django_db
def test_post_reading_rejects_unknown_channel(client: APIClient) -> None:
    body = {"channel": "heartrate", "value": 72}
    response = client.post(reverse("readings"), body, format="json")

    assert response.status_code == 400
    assert response.json() == {
        "channel": ['Unknown channel "heartrate".'],
        "measured_at": ["This field is required."],
    }
    assert Reading.objects.count() == 0
