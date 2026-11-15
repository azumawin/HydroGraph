"""Scenario 1 (`badscenario1.toml`) is the scenario we demo, so the values that
scenario actually puts on the wire are pinned here.

The simulator reports `jugular_strain_pct` as a completed-minute mean, not the
instantaneous ramp endpoint its config names: the first minute averages to
1.1375 % even though `warning_strain_pct` is 1.55. Those means sit close to
Finding 9's band edges, so a change to either side -- the scenario's ramp or
core's thresholds -- can flatten the demo without any other test noticing.
`imitacija/tests/test_sans.py` pins the same numbers from the producing side.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import cast

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from rest_framework.test import APIClient

from api import stream
from api.models import Reading
from api.serializers import dictionary_payload

AT = datetime(2026, 11, 14, tzinfo=UTC)
CREW = {"X-Owner-ID": "crew-1", "X-Simulation-Scope": "crew"}

# The completed-minute means badscenario1.toml produces at 0 s, 60 s and 120 s,
# as asserted in imitacija/tests/test_sans.py, with the band each must land in.
DEMO_MINUTES = [
    (0, 0.0065, "nominal"),
    (60, 0.011375477093821085, "warning"),
    (120, 0.019250126525278383, "critical"),
]
CRITICAL_TRIGGER = "jugular distension > 1.8%"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_scenario_1_minute_means_escalate_through_the_api(client: APIClient) -> None:
    """Each completed minute grades one band higher, reading and finding alike."""
    for second, value, expected in DEMO_MINUTES:
        response = client.post(
            reverse("readings"),
            {
                "channel": "jugular_strain_pct",
                "value": value,
                "unit": "1",
                "measured_at": AT.replace(second=second % 60, minute=second // 60),
            },
            format="json",
            headers=CREW,
        )
        assert response.status_code == 201, response.content
        assert cast("dict[str, object]", response.json())["evaluation"] == expected

        payload = cast(
            "dict[str, object]", client.get(reverse("health-conditions")).json()
        )
        findings = cast("list[dict[str, object]]", payload["findings"])
        sans = [f for f in findings if f["id"] == "sans_fluid_shift_1_3"]
        assert [f["status"] for f in sans] == [expected]

    # The trigger text the dashboard shows once the demo reaches its endpoint.
    assert sans[0]["triggers"] == [CRITICAL_TRIGGER]


def test_scenario_1_warning_minute_keeps_a_margin_above_the_band_edge() -> None:
    """The first minute must not sit within rounding distance of 1.1 %.

    It clears the edge by 0.0375 points. A shorter onset or a later warning
    endpoint would push it under, and the demo would show two nominal minutes
    before jumping straight to critical.
    """
    _, warning_value, _ = DEMO_MINUTES[1]
    assert warning_value * 100.0 - 1.1 > 0.02


@pytest.mark.django_db(transaction=True)
def test_stream_snapshot_carries_the_sans_finding_after_a_reload() -> None:
    """Reloading mid-demo must not blank Finding 9 until the next minute.

    Strain arrives once a minute, so a reload that only replayed readings would
    leave the findings panel empty for up to 60 s.
    """
    _ = Reading.objects.create(
        channel="jugular_strain_pct", value=DEMO_MINUTES[2][1], measured_at=AT
    )
    messages = stream.events()

    async def collect() -> list[str]:
        # The snapshot is the dictionary, the environment, one reading per
        # channel with data, then every finding whose inputs are all present.
        # After it the generator waits on live messages, so drain until it does.
        sent: list[str] = []
        try:
            while True:
                sent.append(await asyncio.wait_for(anext(messages), timeout=5))
        except TimeoutError:
            return sent
        finally:
            await messages.aclose()

    findings = [m for m in async_to_sync(collect)() if m.startswith("event: finding")]
    sans = [
        payload
        for m in findings
        if (payload := json.loads(m.split("data: ", 1)[1]))["id"]
        == "sans_fluid_shift_1_3"
    ]

    assert len(sans) == 1
    assert sans[0]["status"] == "critical"
    assert sans[0]["triggers"] == [CRITICAL_TRIGGER]


def test_sans_channels_carry_the_body_regions_the_body_scan_needs() -> None:
    """The demo's "Head & neck" region lights up from these regions alone."""
    channels = dictionary_payload()["channels"]
    regions = {
        channel: channels[channel]["body_regions"]
        for channel in (
            "jugular_strain_pct",
            "delta_R_over_R0",
            "icp_risk_indicator_mmHg",
            "visual_acuity_logmar",
            "amsler_grid_distortion",
        )
    }

    assert regions == {
        "jugular_strain_pct": ["neck"],
        "delta_R_over_R0": ["neck"],
        "icp_risk_indicator_mmHg": ["head"],
        "visual_acuity_logmar": ["head"],
        "amsler_grid_distortion": ["head"],
    }
