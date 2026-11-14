import pytest
from django.urls import reverse
from hydrograph_core import Status
from rest_framework.test import APIClient

from api.channels import CHANNELS
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


@pytest.mark.parametrize(
    ("channel", "value", "expected"),
    [
        ("heart_rate", 45, Status.UNSPECIFIED),
        ("heart_rate", 90, Status.NOMINAL),
        ("heart_rate", 95, Status.WARNING),
        ("bp_systolic", 118, Status.UNSPECIFIED),
        ("spo2", 94, Status.NOMINAL),
        ("spo2", 93.9, Status.WARNING),
        ("spo2", 89.9, Status.CRITICAL),
        ("core_temp", 38.0, Status.NOMINAL),
        ("core_temp", 35.9, Status.WARNING),
        ("glucose", 3.9, Status.NOMINAL),
        ("glucose", 3.8, Status.WARNING),
        ("glucose", 2.9, Status.CRITICAL),
        ("glucose", 7.1, Status.UNSPECIFIED),
        ("ppco2", 3.1, Status.WARNING),
        ("dose_rate", 50, Status.NOMINAL),
        ("jugular_distension", 1.1, Status.WARNING),
        ("jugular_distension", 1.9, Status.CRITICAL),
    ],
)
def test_channel_thresholds(channel: str, value: float, expected: Status) -> None:
    assert CHANNELS[channel].evaluate(value) is expected
