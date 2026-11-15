"""Orthostatic intolerance & CV deconditioning: not monitored, the simulator sends no postural blood pressure inputs."""

from __future__ import annotations

from core.rule import FindingResult, RuleInputs

ID = "orthostatic_intolerance_1_1"
NAME = "Orthostatic intolerance & CV deconditioning"
CHANNELS: tuple[str, ...] = ()


def evaluate(_inputs: RuleInputs) -> FindingResult | None:
    return None
