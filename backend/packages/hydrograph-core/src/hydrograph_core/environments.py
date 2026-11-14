"""Mission environments the dashboard can switch between."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, TypedDict


class EnvironmentInfo(TypedDict):
    gravity_g: float
    comm_delay_s: float


# Values from docs/json-shape.md; the Earth communication delay is really a
# range, simplified to a single number for the demo.
ENVIRONMENTS: Final[Mapping[str, EnvironmentInfo]] = MappingProxyType(
    {
        "lunar_surface": {"gravity_g": 0.166, "comm_delay_s": 2.6},
        "mars_surface": {"gravity_g": 0.377, "comm_delay_s": 600.0},
    }
)
