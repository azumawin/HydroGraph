from typing import cast

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import Reading
from api.serializers import ACVPU, dictionary_payload

TICK = "2026-11-14T08:00:00Z"
CREW = {"X-Owner-ID": "crew-1", "X-Simulation-Scope": "crew"}
CABIN = {"X-Owner-ID": "node-1", "X-Simulation-Scope": "environment"}


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_health_is_public(client: APIClient) -> None:
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_environments_lists_the_predefined_set(client: APIClient) -> None:
    response = client.get(reverse("environments"))

    assert response.status_code == 200
    payload = cast("dict[str, object]", response.json())
    environments = cast("dict[str, dict[str, object]]", payload["environments"])
    assert list(environments) == [
        "iss_leo",
        "lunar_surface",
        "mars_transit",
        "mars_surface",
    ]
    assert environments["lunar_surface"] == {
        "name": "Lunar surface",
        "gravity_g": 0.166,
        "comm_delay_rt_s": 2.6,
        "baseline_dose_rate_usv_h": 57.1,
        "storm_shelter_available": True,
        "day_length_h": 708.7,
    }


def test_environments_matches_the_stream_dictionary(client: APIClient) -> None:
    payload = cast("dict[str, object]", client.get(reverse("environments")).json())

    assert payload["environments"] == dictionary_payload()["environments"]


def test_environments_is_get_only(client: APIClient) -> None:
    assert client.post(reverse("environments")).status_code == 405


def test_schema_is_served(client: APIClient) -> None:
    response = client.get(reverse("schema"))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")


def test_docs_page_renders(client: APIClient) -> None:
    assert client.get(reverse("docs")).status_code == 200


@pytest.mark.django_db
def test_post_reading_returns_doc_shape(client: APIClient) -> None:
    body = {"channel": "spo2", "value": 0.89, "unit": "1", "measured_at": TICK}
    response = client.post(reverse("readings"), body, format="json", headers=CREW)

    assert response.status_code == 201
    assert cast("dict[str, object]", response.json()) == {
        "channel": "spo2",
        "value": 0.89,
        "measured_at": TICK,
        "evaluation": "critical",
    }
    assert Reading.objects.count() == 1


@pytest.mark.django_db
def test_post_accepts_boolean_environment_channel(client: APIClient) -> None:
    body = {
        "channel": "spe_flag",
        "value": True,
        "unit": "boolean",
        "measured_at": TICK,
    }
    response = client.post(reverse("readings"), body, format="json", headers=CABIN)

    assert response.status_code == 201
    payload = cast("dict[str, object]", response.json())
    assert payload["value"] is True
    assert payload["evaluation"] == "critical"


@pytest.mark.django_db
def test_post_rejects_unknown_channel(client: APIClient) -> None:
    body = {"channel": "heartrate", "value": 1.1, "unit": "s^-1"}
    response = client.post(reverse("readings"), body, format="json", headers=CREW)

    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "channel": ['Unknown channel "heartrate".'],
        "measured_at": ["This field is required."],
    }
    assert Reading.objects.count() == 0


@pytest.mark.django_db
def test_post_rejects_wrong_unit_type_and_scope(client: APIClient) -> None:
    body = {"channel": "heart_rate", "value": True, "unit": "bpm", "measured_at": TICK}
    headers = {"X-Simulation-Scope": "environment"}
    response = client.post(reverse("readings"), body, format="json", headers=headers)

    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "unit": ['Expected "s^-1" for heart_rate.'],
        "value": ["Expected a number for heart_rate."],
        "X-Simulation-Scope": ['Expected "crew" for heart_rate.'],
    }
    assert Reading.objects.count() == 0


@pytest.mark.django_db
def test_post_rejects_number_for_boolean_channel(client: APIClient) -> None:
    body = {
        "channel": "viral_ebv_detected",
        "value": 1,
        "unit": "boolean",
        "measured_at": TICK,
    }
    response = client.post(reverse("readings"), body, format="json", headers=CREW)

    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "value": ["Expected a boolean for viral_ebv_detected."]
    }


@pytest.mark.django_db
def test_post_accepts_acvpu_and_rejects_other_text(client: APIClient) -> None:
    body = {
        "channel": "consciousness_level",
        "value": "CONFUSION",
        "unit": "ACVPU",
        "measured_at": TICK,
    }
    response = client.post(reverse("readings"), body, format="json", headers=CREW)
    assert response.status_code == 201
    assert cast("dict[str, object]", response.json())["value"] == "CONFUSION"

    body["value"] = "SLEEPY"
    response = client.post(reverse("readings"), body, format="json", headers=CREW)
    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "value": [f"Expected one of {', '.join(ACVPU)} for consciousness_level."]
    }


@pytest.mark.django_db
def test_post_accepts_the_scenario_channels(client: APIClient) -> None:
    for channel, value, unit in (
        ("whole_body_sweat_rate", 3e-7, "m^3/s"),
        ("il6_pg_mL", 1e-8, "kg/m^3"),
        ("supplemental_o2", False, "boolean"),
        ("post_ared_exercise_window", True, "boolean"),
    ):
        body = {"channel": channel, "value": value, "unit": unit, "measured_at": TICK}
        response = client.post(reverse("readings"), body, format="json", headers=CREW)
        assert response.status_code == 201, channel


@pytest.mark.django_db
def test_history_returns_latest_per_channel_oldest_first(client: APIClient) -> None:
    for minute, value in [(3, 0.95), (1, 0.97), (2, 0.89)]:  # out of order
        body = {
            "channel": "spo2",
            "value": value,
            "unit": "1",
            "measured_at": f"2026-11-14T08:0{minute}:00Z",
        }
        _ = client.post(reverse("readings"), body, format="json", headers=CREW)

    response = client.get(reverse("readings"), {"limit": 2})

    assert response.status_code == 200
    assert cast("dict[str, object]", response.json()) == {
        "readings": {
            "spo2": [
                {
                    "channel": "spo2",
                    "value": 0.89,
                    "measured_at": "2026-11-14T08:02:00Z",
                    "evaluation": "critical",
                },
                {
                    "channel": "spo2",
                    "value": 0.95,
                    "measured_at": "2026-11-14T08:03:00Z",
                    "evaluation": "nominal",
                },
            ]
        }
    }


@pytest.mark.django_db
def test_history_filters_by_channel_and_rejects_bad_query(client: APIClient) -> None:
    body = {"channel": "spo2", "value": 0.97, "unit": "1", "measured_at": TICK}
    _ = client.post(reverse("readings"), body, format="json", headers=CREW)

    filtered = client.get(reverse("readings"), {"channel": ["heart_rate", "glucose"]})
    assert filtered.json() == {"readings": {}}

    bad = client.get(reverse("readings"), {"channel": "heartrate", "limit": 0})
    assert bad.status_code == 400
    assert set(cast("dict[str, object]", bad.json())) == {"channel", "limit"}
