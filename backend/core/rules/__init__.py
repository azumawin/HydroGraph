"""The built-in findings, one rule module each, in master-plan display order.

The ten master-plan findings plus the supplementary blood pressure evaluator.

Built-in rules can be disabled but not deleted; see :mod:`core.rule` for the
contract every rule, built-in or custom, follows.
"""

from __future__ import annotations

import inspect
from typing import Final

from core.rule import Rule, rule_from_module

from . import (
    acute_infection_3_1,
    behavioral_health_decline_4_2,
    blood_pressure_1_4,
    bone_demineralization_1_2,
    dehydration_2_1,
    hypoxia_co2_2_2,
    negative_energy_balance_2_3,
    orthostatic_intolerance_1_1,
    radiation_exposure_3_2,
    sans_fluid_shift_1_3,
    sleep_deficiency_4_1,
)

DEFAULT_RULES: Final[tuple[Rule, ...]] = tuple(
    rule_from_module(module, inspect.getsource(module))
    for module in (
        orthostatic_intolerance_1_1,
        blood_pressure_1_4,
        bone_demineralization_1_2,
        sans_fluid_shift_1_3,
        dehydration_2_1,
        hypoxia_co2_2_2,
        negative_energy_balance_2_3,
        acute_infection_3_1,
        radiation_exposure_3_2,
        sleep_deficiency_4_1,
        behavioral_health_decline_4_2,
    )
)
