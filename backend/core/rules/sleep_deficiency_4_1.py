"""Sleep deficiency & circadian fatigue: not monitored, the simulator sends no sleep and PVT inputs."""

from __future__ import annotations

from core.rule import FindingResult, RuleInputs

ID = "sleep_deficiency_4_1"
NAME = "Sleep deficiency & circadian fatigue"
CHANNELS: tuple[str, ...] = ()


def evaluate(_inputs: RuleInputs) -> FindingResult | None:
    return None
