import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from hydrograph_core import ENVIRONMENTS
from hydrograph_core.findings import DehydrationResult, EnergyBalanceResult
from rest_framework.test import APIClient

from api import stream, views
from api.findings import crew_findings
from api.models import Reading

AT = datetime(2026, 11, 14, 8, 0, tzinfo=UTC)
CABIN = {"X-Simulation-Scope": "environment"}
CREW = {"X-Simulation-Scope": "crew"}


def create(channel: str, value: float | bool, day: int = 0) -> None:
    measured_at = AT.replace(day=AT.day + day)
    _ = Reading.objects.create(channel=channel, value=value, measured_at=measured_at)


def post(
    body: Mapping[str, object], headers: dict[str, str]
) -> list[dict[str, object]]:
    """POST a reading; return the data of every event it published."""
    published: list[str] = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(views, "publish", published.append)
        response = APIClient().post(
            reverse("readings"), body, format="json", headers=headers
        )
    assert response.status_code == 201
    return [
        cast("dict[str, object]", json.loads(m.split("data: ", 1)[1]))
        for m in published
    ]


@pytest.mark.django_db
def test_cabin_reading_publishes_the_finding_it_feeds() -> None:
    create("ambient_integrated_dose", 0.001)
    create("ambient_dose_rate", 5e-9)
    body = {
        "channel": "spe_flag",
        "value": True,
        "unit": "boolean",
        "measured_at": "2026-11-14T09:00:00Z",
    }

    reading, finding = post(body, CABIN)

    assert reading["channel"] == "spe_flag"
    assert (finding["id"], finding["status"]) == ("radiation_exposure_3_2", "critical")
    assert finding["triggers"] == ["solar particle event"]


@pytest.mark.django_db
def test_reading_publishes_only_findings_that_use_it() -> None:
    create("bone_ntx_pct_baseline", 0.03)
    body = {
        "channel": "urine_volume_24h",
        "value": 1.5e-3,
        "unit": "m^3",
        "measured_at": "2026-11-14T09:00:00Z",
    }
    _, finding = post(body, CREW)
    assert (finding["id"], finding["status"]) == ("bone_demineralization_1_2", True)

    body = {
        "channel": "hrv_rmssd",
        "value": 0.04,
        "unit": "s",
        "measured_at": "2026-11-14T09:00:00Z",
    }
    assert [m["channel"] for m in post(body, CREW)] == ["hrv_rmssd"]


@pytest.mark.django_db
def test_body_mass_baseline_and_week_before_come_from_history() -> None:
    create("urine_specific_gravity", 1.010)
    create("glucose", 5.0)
    create("lactate", 1.0)
    create("body_mass", 80.0, day=0)
    create("body_mass", 76.0, day=1)
    create("body_mass", 75.0, day=8)

    results = crew_findings(ENVIRONMENTS["iss_leo"])

    dehydration = cast("DehydrationResult", results["dehydration_2_1"])
    energy = cast("EnergyBalanceResult", results["negative_energy_balance_2_3"])
    assert dehydration["body_mass_loss_pct"] == 6.25  # vs the first, 80 kg
    assert energy["body_mass_loss_pct_week"] == pytest.approx(1.3158, abs=1e-3)


@pytest.mark.django_db(transaction=True)
def test_stream_snapshot_includes_findings() -> None:
    create("ambient_integrated_dose", 0.001)
    create("ambient_dose_rate", 5e-9)
    create("spe_flag", False)
    messages = stream.events()

    async def run() -> list[str]:
        try:
            return [await anext(messages) for _ in range(6)]
        finally:
            await messages.aclose()

    *_, finding = async_to_sync(run)()

    assert finding.startswith("event: finding\ndata: ")
    payload = cast("dict[str, object]", json.loads(finding.split("data: ", 1)[1]))
    assert (payload["id"], payload["status"]) == ("radiation_exposure_3_2", "nominal")


def put_environment(environment_id: str) -> tuple[int, list[dict[str, object]]]:
    """PUT the environment; return the status and every event it published."""
    published: list[str] = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(views, "publish", published.append)
        response = APIClient().put(
            reverse("environment"), {"id": environment_id}, format="json"
        )
    events = [
        cast("dict[str, object]", json.loads(m.split("data: ", 1)[1]))
        for m in published
    ]
    return response.status_code, events


@pytest.mark.django_db
def test_environment_defaults_to_iss_and_switches() -> None:
    client = APIClient()
    assert client.get(reverse("environment")).json() == {"id": "iss_leo"}

    status, events = put_environment("mars_transit")

    assert status == 200
    assert events[0] == {"id": "mars_transit"}
    assert client.get(reverse("environment")).json() == {"id": "mars_transit"}


@pytest.mark.django_db
def test_unknown_environment_is_rejected_and_changes_nothing() -> None:
    status, events = put_environment("venus")

    assert status == 400
    assert events == []
    assert APIClient().get(reverse("environment")).json() == {"id": "iss_leo"}


@pytest.mark.django_db
def test_switch_regrades_dose_rate_against_the_new_baseline() -> None:
    lunar_background = 57.1e-6 / 3600  # Sv/s
    create("ambient_integrated_dose", 0.001)
    create("ambient_dose_rate", lunar_background)
    create("spe_flag", False)

    _, iss = put_environment("iss_leo")
    _, lunar = put_environment("lunar_surface")

    def graded(events: list[dict[str, object]]) -> tuple[object, object]:
        reading = next(e for e in events if e.get("channel") == "ambient_dose_rate")
        finding = next(e for e in events if e.get("id") == "radiation_exposure_3_2")
        return reading["evaluation"], finding["status"]

    # 57.1 uSv/h is a 42.5 spike above ISS (nominal) and the lunar background.
    assert graded(iss) == ("nominal", "nominal")
    assert graded(lunar) == ("nominal", "nominal")
    spike = 57.1 + 50.1
    create("ambient_dose_rate", spike * 1e-6 / 3600, day=1)
    _, lunar_spike = put_environment("lunar_surface")
    assert graded(lunar_spike) == ("warning", "warning")


def test_stream_and_environment_allow_any_origin() -> None:
    client = APIClient()
    preflight = client.options(
        reverse("environment"),
        HTTP_ORIGIN="http://127.0.0.1:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="PUT",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )
    assert preflight["Access-Control-Allow-Origin"] == "*"
    assert "PUT" in preflight["Access-Control-Allow-Methods"]
