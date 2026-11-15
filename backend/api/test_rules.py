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

from api.findings import crew_findings
from api.models import Reading
from core import ENVIRONMENTS, FINDINGS

TACHYCARDIA = """
ID = "resting_tachycardia"
NAME = "Resting tachycardia"
CHANNELS = ("heart_rate",)


def evaluate(inputs):
    bpm = inputs["latest"]["heart_rate"] * 60
    status = "critical" if bpm > 120 else "nominal"
    return {"status": status, "triggers": [], "action": "Rest", "bpm": bpm}
"""


pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> Client:
    return Client()


def send(
    client: Client, method: str, url: str, body: Mapping[str, object]
) -> _MonkeyPatchedWSGIResponse:
    return client.generic(
        method, url, json.dumps(body), content_type="application/json"
    )


def rules(client: Client) -> dict[str, dict[str, object]]:
    payload = cast(
        "dict[str, list[dict[str, object]]]", client.get(reverse("rules")).json()
    )
    return {cast("str", rule["id"]): rule for rule in payload["rules"]}


def findings() -> set[str]:
    return set(async_to_sync(crew_findings)(ENVIRONMENTS["iss_leo"]))


def test_built_in_rules_are_listed_enabled_with_their_source(client: Client) -> None:
    listed = rules(client)
    assert list(listed) == list(FINDINGS)
    assert all(rule["default"] and rule["enabled"] for rule in listed.values())
    assert 'ID = "sans_fluid_shift_1_3"' in cast(
        "str", listed["sans_fluid_shift_1_3"]["source"]
    )


def test_a_custom_rule_is_added_and_evaluated(client: Client) -> None:
    response = send(client, "POST", reverse("rules"), {"source": TACHYCARDIA})
    assert response.status_code == 201
    assert response.json()["id"] == "resting_tachycardia"

    _ = Reading.objects.create(
        channel="heart_rate", value=2.5, measured_at="2026-11-14T08:00:00Z"
    )
    result = async_to_sync(crew_findings)(ENVIRONMENTS["iss_leo"])
    assert result["resting_tachycardia"]["status"] == "critical"
    assert rules(client)["resting_tachycardia"]["default"] is False


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("ID = 'x'\nNAME = 'x'\nCHANNELS = ()", "evaluate"),
        (TACHYCARDIA.replace("resting_tachycardia", "sans_fluid_shift_1_3"), "exists"),
    ],
)
def test_an_invalid_rule_is_rejected(client: Client, source: str, message: str) -> None:
    response = send(client, "POST", reverse("rules"), {"source": source})
    assert response.status_code == 400
    assert message in response.json()["source"][0]


def test_a_built_in_rule_can_be_disabled_but_not_edited_or_deleted(
    client: Client,
) -> None:
    _ = Reading.objects.create(
        channel="jugular_strain_pct", value=0.02, measured_at="2026-11-14T08:00:00Z"
    )
    url = reverse("rule", args=["sans_fluid_shift_1_3"])
    assert "sans_fluid_shift_1_3" in findings()

    assert send(client, "PUT", url, {"enabled": False}).status_code == 200
    assert "sans_fluid_shift_1_3" not in findings()
    assert rules(client)["sans_fluid_shift_1_3"]["enabled"] is False

    assert send(client, "PUT", url, {"source": TACHYCARDIA}).status_code == 400
    assert client.delete(url).status_code == 409

    assert send(client, "PUT", url, {"enabled": True}).status_code == 200
    assert "sans_fluid_shift_1_3" in findings()


def test_a_custom_rule_can_be_edited_and_deleted(client: Client) -> None:
    _ = send(client, "POST", reverse("rules"), {"source": TACHYCARDIA})
    url = reverse("rule", args=["resting_tachycardia"])

    renamed = TACHYCARDIA.replace('"Resting tachycardia"', '"Fast resting pulse"')
    response = send(client, "PUT", url, {"source": renamed})
    assert response.status_code == 200
    assert response.json()["name"] == "Fast resting pulse"

    moved = TACHYCARDIA.replace('ID = "resting_tachycardia"', 'ID = "other"')
    assert send(client, "PUT", url, {"source": moved}).status_code == 400

    assert client.delete(url).status_code == 204
    assert "resting_tachycardia" not in rules(client)
    assert client.delete(url).status_code == 404
