"""Behavioral health & HPA-axis decline: not monitored, the simulator sends no PHQ-9, GAD-7 and EEG inputs."""

from __future__ import annotations

from core.rule import FindingResult, RuleInputs

ID = "behavioral_health_decline_4_2"
NAME = "Behavioral health & HPA-axis decline"
CHANNELS: tuple[str, ...] = ()


def evaluate(_inputs: RuleInputs) -> FindingResult | None:
    return None
