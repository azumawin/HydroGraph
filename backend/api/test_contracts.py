"""The API contracts the dashboard's next tabs build on.

An all-measurements view iterates the dictionary and renders every channel; a
long-range trends view reads months of history; a demo preload writes that
history before, or while, the simulator runs. These pin what each relies on
today, so extending the API for them cannot quietly change it.
"""

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from hydrograph_core import CHANNELS, ENVIRONMENTS, FINDINGS
from rest_framework.test import APIClient

from api import stream
from api.serializers import dictionary_payload

AT = datetime(2026, 11, 14, 8, 0, tzinfo=UTC)
CREW = {"X-Owner-ID": "crew-1", "X-Simulation-Scope": "crew"}
CABIN = {"X-Owner-ID": "node-1", "X-Simulation-Scope": "environment"}
SEVERITIES = {"nominal", "warning", "critical", "unspecified"}
DASHBOARD_CONSTANTS = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "Constants.ts"
)


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def post(
    client: APIClient, channel: str, value: object, at: datetime, **more: object
) -> None:
    unit = CHANNELS[channel]["unit"]
    headers = CABIN if CHANNELS[channel]["scope"] == "environment" else CREW
    body = {"channel": channel, "value": value, "unit": unit, "measured_at": at, **more}
    response = client.post(reverse("readings"), body, format="json", headers=headers)
    assert response.status_code == 201, response.content


def history(client: APIClient, **query: object) -> dict[str, list[dict[str, object]]]:
    response = client.get(reverse("readings"), query)
    assert response.status_code == 200, response.content
    payload = cast("dict[str, object]", response.json())
    return cast("dict[str, list[dict[str, object]]]", payload["readings"])


def snapshot() -> list[dict[str, object]]:
    """Every message a freshly connected dashboard receives before live ones."""
    messages = stream.events()

    async def collect() -> list[str]:
        sent: list[str] = []
        try:
            while True:
                sent.append(await asyncio.wait_for(anext(messages), timeout=5))
        except TimeoutError:
            return sent
        finally:
            await messages.aclose()

    return [json.loads(m.split("data: ", 1)[1]) for m in async_to_sync(collect)()]


# --------------------------------------------------------------- the dictionary


def test_dictionary_describes_every_channel_and_finding() -> None:
    """An all-measurements view renders each entry with no fallback for gaps."""
    payload = dictionary_payload()

    assert set(payload["channels"]) == set(CHANNELS)
    assert set(payload["findings"]) == set(FINDINGS)
    assert set(payload["environments"]) == set(ENVIRONMENTS)
    for channel, entry in payload["channels"].items():
        assert entry["name"], channel
        assert entry["scope"] in {"crew", "environment"}, channel
        assert entry["unit"], channel
        assert entry["value_type"] == CHANNELS[channel]["value_type"], channel
        assert entry["value_type"] in {"number", "boolean", "enum"}, channel
        assert entry["explanation"], channel
        display = entry["display"]
        assert display["scale"] != 0 and display["scale"] == display["scale"], channel
        assert display["offset"] == display["offset"], channel
    for finding, entry in payload["findings"].items():
        assert entry["name"], finding
        assert set(entry["channels"]) <= set(CHANNELS), finding
    # Catalogued without live inputs: no reading can ever change their status,
    # so a findings view must not wait on them. Wiring one up is a deliberate
    # change that should show here.
    unwired = {k for k, v in payload["findings"].items() if not v["channels"]}
    assert unwired == {
        "behavioral_health_decline_4_2",
        "orthostatic_intolerance_1_1",
        "sleep_deficiency_4_1",
    }


def test_every_body_region_in_the_dictionary_is_drawn_by_the_dashboard() -> None:
    """The body scan ignores a reading placed on a region it has no group for.

    Core names the regions; BODY_SCAN_REGION_GROUPS in the dashboard decides
    which are drawn. A channel on an unlisted region would silently never
    light anything up.
    """
    source = DASHBOARD_CONSTANTS.read_text()
    groups = source[source.index("BODY_SCAN_REGION_GROUPS") :]
    groups = groups[: groups.index("];")]
    drawn = set(re.findall(r'"([a-z_]+)"', groups)) - {"LABEL", "REGIONS"}

    used = {region for entry in CHANNELS.values() for region in entry["body_regions"]}

    assert used <= drawn, sorted(used - drawn)


# ------------------------------------------------------------------ the history


@pytest.mark.django_db
def test_history_limit_applies_per_channel_and_is_capped(client: APIClient) -> None:
    """A trends view asks for many readings of several channels at once."""
    for minute in range(3):
        at = AT.replace(minute=minute)
        post(client, "spo2", 0.97, at)
        post(client, "heart_rate", 1.2, at)

    two_each = history(client, limit=2)
    assert {k: len(v) for k, v in two_each.items()} == {"spo2": 2, "heart_rate": 2}
    assert [r["measured_at"] for r in two_each["spo2"]] == [
        "2026-11-14T08:01:00Z",
        "2026-11-14T08:02:00Z",
    ]

    assert client.get(reverse("readings"), {"limit": 1000}).status_code == 200
    assert client.get(reverse("readings"), {"limit": 1001}).status_code == 400


@pytest.mark.django_db
def test_history_keeps_years_of_readings_oldest_first(client: APIClient) -> None:
    """Preloaded months of data must come back whole; nothing expires by age."""
    for year in (2026, 2024, 2025):  # out of order, as a preload may write them
        post(client, "body_mass", 70 + year - 2024, AT.replace(year=year))

    masses = history(client, channel="body_mass")["body_mass"]

    assert [r["measured_at"][:4] for r in masses] == ["2024", "2025", "2026"]
    assert [r["value"] for r in masses] == [70, 71, 72]


@pytest.mark.django_db
def test_history_grades_against_the_environment_in_effect(client: APIClient) -> None:
    """Old readings are re-graded, not stored with a grade, so a switch moves them."""
    seventy_usv_h = 70e-6 / 3600  # Sv/s: a 55 spike above ISS, 13 above the Moon
    post(client, "ambient_dose_rate", seventy_usv_h, AT)

    def graded() -> object:
        return history(client, channel="ambient_dose_rate")["ambient_dose_rate"][0][
            "evaluation"
        ]

    assert graded() == "warning"
    switched = client.put(
        reverse("environment"), {"id": "lunar_surface"}, format="json"
    )
    assert switched.status_code == 200
    assert graded() == "nominal"


@pytest.mark.django_db(transaction=True)
def test_equal_timestamps_keep_insertion_order_and_the_last_wins(
    client: APIClient,
) -> None:
    """A preload and the live simulator can both write the same instant.

    The history returns both, in the order they arrived; whichever arrived last
    is the current reading everywhere the dashboard asks for one.
    """
    post(client, "spo2", 0.95, AT)
    post(client, "spo2", 0.97, AT)

    assert [r["value"] for r in history(client, channel="spo2")["spo2"]] == [0.95, 0.97]
    assert history(client, channel="spo2", limit=1)["spo2"][0]["value"] == 0.97
    latest = next(m for m in snapshot() if m.get("channel") == "spo2")
    assert latest["value"] == 0.97


# ------------------------------------------------- live data beside a preload


@pytest.mark.django_db(transaction=True)
def test_backdated_reading_never_displaces_the_latest(client: APIClient) -> None:
    """A preload that lands after the simulator starts must not look current.

    "Current" means measured last, not stored last: the big number, the
    findings and the reload snapshot all have to agree on that.
    """
    post(client, "jugular_strain_pct", 0.021, AT)  # live, critical
    post(
        client, "jugular_strain_pct", 0.0065, AT.replace(year=2025)
    )  # backdated, nominal

    assert (
        history(client, channel="jugular_strain_pct", limit=1)["jugular_strain_pct"][0][
            "value"
        ]
        == 0.021
    )

    findings = cast(
        "list[dict[str, object]]",
        cast("dict[str, object]", client.get(reverse("health-conditions")).json())[
            "findings"
        ],
    )
    sans = next(f for f in findings if f["id"] == "sans_fluid_shift_1_3")
    assert sans["status"] == "critical"

    messages = snapshot()
    reading = next(m for m in messages if m.get("channel") == "jugular_strain_pct")
    finding = next(m for m in messages if m.get("id") == "sans_fluid_shift_1_3")
    assert (reading["value"], reading["evaluation"]) == (0.021, "critical")
    assert finding["status"] == "critical"


# ------------------------------------------------------------------ the values


@pytest.mark.django_db
def test_each_value_type_round_trips_with_a_grade(client: APIClient) -> None:
    """Numbers, flags and ACVPU text each reach the history graded.

    The all-measurements view renders all three, so none may come back shaped
    differently from the others.
    """
    post(client, "spo2", 0.97, AT)
    post(client, "spe_flag", True, AT)
    post(client, "consciousness_level", "VOICE", AT)

    readings = history(client, channel=["spo2", "spe_flag", "consciousness_level"])

    assert {k: v[0]["value"] for k, v in readings.items()} == {
        "spo2": 0.97,
        "spe_flag": True,
        "consciousness_level": "VOICE",
    }
    for channel, [reading] in readings.items():
        assert set(reading) == {
            "channel",
            "value",
            "measured_at",
            "evaluation",
        }, channel
        assert reading["evaluation"] in SEVERITIES, channel
    assert readings["spe_flag"][0]["evaluation"] == "critical"
