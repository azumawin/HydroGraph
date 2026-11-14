from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

import pytest
from asgiref.sync import async_to_sync
from django.test import Client
from django.urls import reverse

if TYPE_CHECKING:
    from django.test.client import (
        _MonkeyPatchedWSGIResponse,  # pyright: ignore[reportPrivateUsage]
    )

from api.contracts import dictionary_payload, finding_payload
from api.environment import current_environment
from api.findings import crew_findings
from api.models import Reading
from core import ACVPU, ENVIRONMENTS
from core.findings import DehydrationResult, InfectionResult

TICK = "2026-11-14T08:00:00Z"
SHELTER = "Move to shielded storm shelter zone immediately and confirm hatch closure"
CREW = {"X-Owner-ID": "crew-1", "X-Simulation-Scope": "crew"}
CABIN = {"X-Owner-ID": "node-1", "X-Simulation-Scope": "environment"}


@pytest.fixture
def client() -> Client:
    return Client()


def post(
    client: Client,
    name: str,
    body: Mapping[str, object],
    headers: dict[str, str] | None = None,
) -> _MonkeyPatchedWSGIResponse:
    return client.post(
        reverse(name),
        json.dumps(body),
        content_type="application/json",
        headers=headers or {},
    )


def test_health_is_public(client: Client) -> None:
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_environments_lists_the_predefined_set(client: Client) -> None:
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


def test_environments_matches_the_stream_dictionary(client: Client) -> None:
    payload = cast("dict[str, object]", client.get(reverse("environments")).json())

    assert payload["environments"] == dictionary_payload()["environments"]


def test_environments_is_get_only(client: Client) -> None:
    assert client.post(reverse("environments")).status_code == 405


@pytest.mark.django_db
def test_post_reading_returns_doc_shape(client: Client) -> None:
    body = {"channel": "spo2", "value": 0.89, "unit": "1", "measured_at": TICK}
    response = post(client, "readings", body, CREW)

    assert response.status_code == 201
    assert cast("dict[str, object]", response.json()) == {
        "channel": "spo2",
        "value": 0.89,
        "measured_at": TICK,
        "evaluation": "critical",
    }
    assert Reading.objects.count() == 1


@pytest.mark.django_db
def test_post_accepts_boolean_environment_channel(client: Client) -> None:
    body = {
        "channel": "spe_flag",
        "value": True,
        "unit": "boolean",
        "measured_at": TICK,
    }
    response = post(client, "readings", body, CABIN)

    assert response.status_code == 201
    payload = cast("dict[str, object]", response.json())
    assert payload["value"] is True
    assert payload["evaluation"] == "critical"


@pytest.mark.django_db
def test_post_rejects_unknown_channel(client: Client) -> None:
    body = {"channel": "heartrate", "value": 1.1, "unit": "s^-1"}
    response = post(client, "readings", body, CREW)

    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "channel": ['Unknown channel "heartrate".'],
        "measured_at": ["This field is required."],
    }
    assert Reading.objects.count() == 0


@pytest.mark.django_db
def test_post_rejects_wrong_unit_type_and_scope(client: Client) -> None:
    body = {"channel": "heart_rate", "value": True, "unit": "bpm", "measured_at": TICK}
    headers = {"X-Simulation-Scope": "environment"}
    response = post(client, "readings", body, headers)

    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "unit": ['Expected "s^-1" for heart_rate.'],
        "value": ["Expected a number for heart_rate."],
        "X-Simulation-Scope": ['Expected "crew" for heart_rate.'],
    }
    assert Reading.objects.count() == 0


@pytest.mark.django_db
def test_post_rejects_number_for_boolean_channel(client: Client) -> None:
    body = {
        "channel": "viral_ebv_detected",
        "value": 1,
        "unit": "boolean",
        "measured_at": TICK,
    }
    response = post(client, "readings", body, CREW)

    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "value": ["Expected a boolean for viral_ebv_detected."]
    }


@pytest.mark.django_db
def test_post_accepts_acvpu_and_rejects_other_text(client: Client) -> None:
    body = {
        "channel": "consciousness_level",
        "value": "CONFUSION",
        "unit": "ACVPU",
        "measured_at": TICK,
    }
    response = post(client, "readings", body, CREW)
    assert response.status_code == 201
    assert cast("dict[str, object]", response.json())["value"] == "CONFUSION"

    body["value"] = "SLEEPY"
    response = post(client, "readings", body, CREW)
    assert response.status_code == 400
    assert cast("dict[str, object]", response.json()) == {
        "value": [f"Expected one of {', '.join(ACVPU)} for consciousness_level."]
    }


@pytest.mark.django_db
def test_post_accepts_the_scenario_channels(client: Client) -> None:
    for channel, value, unit in (
        ("whole_body_sweat_rate", 3e-7, "m^3/s"),
        ("il6_pg_mL", 1e-8, "kg/m^3"),
        ("supplemental_o2", False, "boolean"),
        ("post_ared_exercise_window", True, "boolean"),
    ):
        body = {"channel": channel, "value": value, "unit": unit, "measured_at": TICK}
        response = post(client, "readings", body, CREW)
        assert response.status_code == 201, channel


@pytest.mark.django_db
def test_history_returns_latest_per_channel_oldest_first(client: Client) -> None:
    for minute, value in [(3, 0.95), (1, 0.97), (2, 0.89)]:  # out of order
        body = {
            "channel": "spo2",
            "value": value,
            "unit": "1",
            "measured_at": f"2026-11-14T08:0{minute}:00Z",
        }
        _ = post(client, "readings", body, CREW)

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
def test_history_filters_by_channel_and_rejects_bad_query(client: Client) -> None:
    body = {"channel": "spo2", "value": 0.97, "unit": "1", "measured_at": TICK}
    _ = post(client, "readings", body, CREW)

    filtered = client.get(reverse("readings"), {"channel": ["heart_rate", "glucose"]})
    assert filtered.json() == {"readings": {}}

    bad = client.get(reverse("readings"), {"channel": "heartrate", "limit": 0})
    assert bad.status_code == 400
    assert set(cast("dict[str, object]", bad.json())) == {"channel", "limit"}


@pytest.mark.django_db
def test_health_conditions_returns_the_findings_the_readings_support(
    client: Client,
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
                "values": {
                    "cumulative_dose_msv": 1.0,
                    "dose_rate_usv_h": 18.0,
                },
                "triggers": ["solar particle event"],
                "status": "critical",
                "action": SHELTER,
            }
        ]
    }


@pytest.mark.django_db
def test_health_conditions_is_empty_without_readings(client: Client) -> None:
    response = client.get(reverse("health-conditions"))

    assert response.status_code == 200
    assert cast("dict[str, object]", response.json()) == {"findings": []}


@pytest.mark.django_db
def test_health_conditions_omits_findings_with_a_missing_input(
    client: Client,
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
    assert findings[0]["status"] == "warning"


@pytest.mark.django_db
def test_health_conditions_evaluates_several_findings_at_once(
    client: Client,
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
    client: Client,
) -> None:
    for channel, value in (
        ("urine_specific_gravity", 1.025),
        ("body_mass", 80.0),
    ):
        _ = Reading.objects.create(channel=channel, value=value, measured_at=TICK)
    payload = cast("dict[str, object]", client.get(reverse("health-conditions")).json())

    assert payload["findings"] == [
        finding_payload(finding, result)
        for finding, result in async_to_sync(crew_findings)(
            async_to_sync(current_environment)()
        ).items()
    ]


def test_health_conditions_is_get_only(client: Client) -> None:
    assert client.post(reverse("health-conditions")).status_code == 405


@pytest.mark.django_db
def test_eva_whole_body_channel_and_dehydration(
    client: Client, monkeypatch: pytest.MonkeyPatch
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
        response = post(
            client,
            "readings",
            {"channel": channel, "value": value, "unit": unit, "measured_at": time},
            {"X-Simulation-Scope": "crew"},
        )
        assert response.status_code == 201
    result = cast(
        "DehydrationResult",
        async_to_sync(crew_findings)(ENVIRONMENTS["iss_leo"])["dehydration_2_1"],
    )
    assert result["status"] is True
    assert result["fluid_deficit_ml"] == 1800
    assert any("dehydration_2_1" in event for event in published)


@pytest.mark.django_db
def test_infection_explicit_context_and_optional_assays(
    client: Client, monkeypatch: pytest.MonkeyPatch
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
        response = post(
            client,
            "readings",
            {
                "channel": channel,
                "value": value,
                "unit": unit,
                "measured_at": "2026-11-14T00:32:00Z",
            },
            {"X-Simulation-Scope": "crew"},
        )
        assert response.status_code == 201
    result = cast(
        "InfectionResult",
        async_to_sync(crew_findings)(ENVIRONMENTS["iss_leo"])["acute_infection_3_1"],
    )
    assert (
        result["status"] == "critical"
        and result["news2_score"] == 8
        and result.get("qsofa_score") == 2
    )
    assert result.get("il6_source_channel") == "il6_pg_mL"
    assert any("acute_infection_3_1" in x for x in published)
    response = post(
        client,
        "readings",
        {
            "channel": "consciousness_level",
            "value": "CONFUSION",
            "unit": "ACVPU",
            "measured_at": "2026-11-14T00:33:00Z",
        },
        {"X-Simulation-Scope": "crew"},
    )
    assert response.status_code == 201
    confused = cast(
        "InfectionResult",
        async_to_sync(crew_findings)(ENVIRONMENTS["iss_leo"])["acute_infection_3_1"],
    )
    assert confused.get("qsofa_score") == 3
    response = post(
        client,
        "readings",
        {
            "channel": "consciousness_level",
            "value": "bad",
            "unit": "ACVPU",
            "measured_at": "2026-11-14T00:34:00Z",
        },
        {"X-Simulation-Scope": "crew"},
    )
    assert response.status_code == 400
