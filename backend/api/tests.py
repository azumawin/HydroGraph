import pytest
from django.urls import reverse
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
def test_post_readings_returns_enriched_array(client: APIClient) -> None:
    body = [
        {"channel": "heart_rate", "value": 104, "measured_at": TICK},
        {"channel": "spo2", "value": 89, "measured_at": TICK},
    ]
    response = client.post(reverse("readings"), body, format="json")

    assert response.status_code == 201
    heart_rate, spo2 = response.json()
    assert heart_rate == {
        "id": heart_rate["id"],
        "channel": "heart_rate",
        "value": 104.0,
        "unit": "bpm",
        "evaluation": "warning",
        "measured_at": TICK,
        "name": "Heart rate",
        "body_regions": ["heart"],
        "explanation": heart_rate["explanation"],
    }
    assert isinstance(heart_rate["id"], int)
    assert spo2["evaluation"] == "critical"
    assert Reading.objects.count() == 2


@pytest.mark.django_db
def test_post_readings_rejects_whole_batch_with_per_item_errors(
    client: APIClient,
) -> None:
    body = [
        {"channel": "heart_rate", "value": 72, "measured_at": TICK},
        {"channel": "heartrate", "value": 72, "measured_at": TICK},
        {"channel": "spo2", "value": 97},
    ]
    response = client.post(reverse("readings"), body, format="json")

    assert response.status_code == 400
    assert response.json() == {
        "1": {"channel": ['Unknown channel "heartrate".']},
        "2": {"measured_at": ["This field is required."]},
    }
    assert Reading.objects.count() == 0
