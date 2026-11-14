from typing import cast

import pytest
from django.urls import reverse
from hydrograph_core import ENVIRONMENTS
from hydrograph_core.findings import DehydrationResult, InfectionResult
from rest_framework.test import APIClient

from api.environment import current_environment
from api.findings import crew_findings
from api.models import Reading
from api.serializers import dictionary_payload, finding_payload

TICK = "2026-11-14T08:00:00Z"
SHELTER = "Move to shielded storm shelter zone immediately and confirm hatch closure"
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
    environments = cast("list[dict[str, object]]", payload["environments"])
    assert [e["id"] for e in environments] == [
        "iss_leo",
        "lunar_surface",
        "mars_transit",
        "mars_surface",
    ]
    assert environments[1] == {
        "id": "lunar_surface",
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
        "unit": "1",
        "evaluation": "critical",
        "measured_at": TICK,
        "scope": "crew",
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
    assert payload["scope"] == "environment"


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
def test_health_conditions_returns_the_findings_the_readings_support(
    client: APIClient,
) -> None:
    for channel, value in (
        ("ambient_integrated_dose", 0.001),
        ("ambient_dose_rate", 5e-9),
        ("spe_flag", True),
    ):
        _ = Reading.objects.create(channel=channel, value=value, measured_at=TICK)
    response = client.get(reverse("health-conditions"))

    assert response.status_code == 200
    assert cast("dict[str, object]", response.json()) == {
        "findings": [
            {
                "id": "radiation_exposure_3_2",
                "cumulative_dose_msv": 1.0,
                "dose_rate_usv_h": 18.0,
                "triggers": ["solar particle event"],
                "status": "critical",
                "action": SHELTER,
            }
        ]
    }


@pytest.mark.django_db
def test_health_conditions_is_empty_without_readings(client: APIClient) -> None:
    response = client.get(reverse("health-conditions"))

    assert response.status_code == 200
    assert cast("dict[str, object]", response.json()) == {"findings": []}


@pytest.mark.django_db
def test_health_conditions_omits_findings_with_a_missing_input(
    client: APIClient,
) -> None:
    """Bone needs two channels; one reading is not enough to evaluate it."""
    _ = Reading.objects.create(
        channel="bone_ntx_pct_baseline", value=0.31, measured_at=TICK
    )
    assert cast(
        "dict[str, object]", client.get(reverse("health-conditions")).json()
    ) == {"findings": []}

    _ = Reading.objects.create(
        channel="urine_volume_24h", value=1.4e-3, measured_at=TICK
    )
    payload = cast("dict[str, object]", client.get(reverse("health-conditions")).json())
    findings = cast("list[dict[str, object]]", payload["findings"])
    assert [f["id"] for f in findings] == ["bone_demineralization_1_2"]
    assert findings[0]["status"] is True


@pytest.mark.django_db
def test_health_conditions_evaluates_several_findings_at_once(
    client: APIClient,
) -> None:
    for channel, value in (
        ("jugular_strain_pct", 0.021),
        ("spo2", 0.92),
        ("ambient_ppco2", 500.0),
    ):
        _ = Reading.objects.create(channel=channel, value=value, measured_at=TICK)
    payload = cast("dict[str, object]", client.get(reverse("health-conditions")).json())
    findings = cast("list[dict[str, object]]", payload["findings"])

    assert [f["id"] for f in findings] == ["sans_fluid_shift_1_3", "hypoxia_co2_2_2"]
    assert [f["status"] for f in findings] == ["critical", "warning"]


@pytest.mark.django_db
def test_health_conditions_matches_the_stream_finding_events(
    client: APIClient,
) -> None:
    for channel, value in (
        ("urine_specific_gravity", 1.025),
        ("body_mass", 80.0),
    ):
        _ = Reading.objects.create(channel=channel, value=value, measured_at=TICK)
    payload = cast("dict[str, object]", client.get(reverse("health-conditions")).json())

    assert payload["findings"] == [
        finding_payload(f, r) for f, r in crew_findings(current_environment()).items()
    ]


def test_health_conditions_is_get_only(client: APIClient) -> None:
    assert client.post(reverse("health-conditions")).status_code == 405


@pytest.mark.django_db
def test_eva_whole_body_channel_and_dehydration(
    client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = Reading.objects.all().delete()  # Isolated pytest database only.
    published: list[str] = []
    monkeypatch.setattr("api.views.publish", published.append)
    for channel, value, unit, time in [
        ("body_mass", 75.0, "kg", "2026-11-14T00:00:00Z"),
        ("urine_specific_gravity", 1.012, "1", "2026-11-14T00:00:00Z"),
        ("whole_body_sweat_rate", 0.820 / 3_600_000, "m^3/s", "2026-11-14T00:10:01Z"),
        ("body_mass", 73.2, "kg", "2026-11-14T02:40:00Z"),
        ("urine_specific_gravity", 1.026, "1", "2026-11-14T02:40:00Z"),
    ]:
        response = client.post(
            "/api/readings/",
            {"channel": channel, "value": value, "unit": unit, "measured_at": time},
            format="json",
            HTTP_X_SIMULATION_SCOPE="crew",
        )
        assert response.status_code == 201
    result = cast(
        "DehydrationResult",
        crew_findings(ENVIRONMENTS["iss_leo"])["dehydration_2_1"],
    )
    assert result["status"] is True
    assert result["fluid_deficit_ml"] == 1800
    assert any("dehydration_2_1" in event for event in published)


@pytest.mark.django_db
def test_infection_explicit_context_and_optional_assays(
    client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    published: list[str] = []
    monkeypatch.setattr("api.views.publish", published.append)
    rows = [
        ("heart_rate", 116 / 60, "s^-1"),
        ("respiratory_rate", 23 / 60, "s^-1"),
        ("spo2", 0.94, "1"),
        ("bp_systolic", 96 * 133.322, "Pa"),
        ("body_temperature", 311.85, "K"),
        ("consciousness_level", "ALERT", "ACVPU"),
        ("supplemental_o2", False, "boolean"),
        ("post_ared_exercise_window", False, "boolean"),
        ("il6_pg_mL", 8.4e-9, "kg/m^3"),
    ]
    for channel, value, unit in rows:
        response = client.post(
            "/api/readings/",
            {
                "channel": channel,
                "value": value,
                "unit": unit,
                "measured_at": "2026-11-14T00:32:00Z",
            },
            format="json",
            HTTP_X_SIMULATION_SCOPE="crew",
        )
        assert response.status_code == 201
    result = cast(
        "InfectionResult",
        crew_findings(ENVIRONMENTS["iss_leo"])["acute_infection_3_1"],
    )
    assert (
        result["status"] == "critical"
        and result["news2_score"] == 8
        and result.get("qsofa_score") == 2
    )
    assert result.get("il6_source_channel") == "il6_pg_mL"
    assert any("acute_infection_3_1" in x for x in published)
    response = client.post(
        "/api/readings/",
        {
            "channel": "consciousness_level",
            "value": "CONFUSION",
            "unit": "ACVPU",
            "measured_at": "2026-11-14T00:33:00Z",
        },
        format="json",
        HTTP_X_SIMULATION_SCOPE="crew",
    )
    assert response.status_code == 201
    confused = cast(
        "InfectionResult",
        crew_findings(ENVIRONMENTS["iss_leo"])["acute_infection_3_1"],
    )
    assert confused.get("qsofa_score") == 3
    response = client.post(
        "/api/readings/",
        {
            "channel": "consciousness_level",
            "value": "bad",
            "unit": "ACVPU",
            "measured_at": "2026-11-14T00:34:00Z",
        },
        format="json",
        HTTP_X_SIMULATION_SCOPE="crew",
    )
    assert response.status_code == 400
