"""HydroGFN health monitor: the 10 Tier 1 findings, sensor channels, environments.

Each ``<finding>_D_S`` function implements one finding: D is its hazard
domain, S its place within that domain. The numbering is ours, not the plan's;
the mapping to plan finding numbers is in :mod:`core.findings`.
:mod:`core.channels` grades single readings;
:mod:`core.rule` defines findings as rules and :mod:`core.rules` holds the
built-in ones; :mod:`core.assessment` runs rules on the latest readings;
:mod:`core.environments` lists the mission environments.
"""

from .assessment import (
    FINDINGS,
    FindingInfo,
    FindingResult,
    News2Result,
    evaluate_findings,
    news2,
    qsofa,
)
from .channels import (
    ACVPU,
    CHANNELS,
    SCHEDULES,
    ChannelInfo,
    Display,
    Evaluation,
    evaluate_reading,
)
from .environments import DEFAULT_ENVIRONMENT, ENVIRONMENTS, EnvironmentInfo
from .findings import (
    Severity,
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
from .rule import Rule, RuleError, RuleInputs, compile_rule
from .rules import DEFAULT_RULES

__all__ = [
    "ACVPU",
    "CHANNELS",
    "DEFAULT_ENVIRONMENT",
    "DEFAULT_RULES",
    "ENVIRONMENTS",
    "FINDINGS",
    "SCHEDULES",
    "ChannelInfo",
    "Display",
    "EnvironmentInfo",
    "Evaluation",
    "FindingInfo",
    "FindingResult",
    "News2Result",
    "Rule",
    "RuleError",
    "RuleInputs",
    "Severity",
    "__version__",
    "acute_infection_3_1",
    "behavioral_health_decline_4_2",
    "blood_pressure_1_4",
    "bone_demineralization_1_2",
    "compile_rule",
    "dehydration_2_1",
    "evaluate_findings",
    "evaluate_reading",
    "hypoxia_co2_2_2",
    "negative_energy_balance_2_3",
    "news2",
    "orthostatic_intolerance_1_1",
    "qsofa",
    "radiation_exposure_3_2",
    "sans_fluid_shift_1_3",
    "sleep_deficiency_4_1",
]

__version__ = "0.1.0"
