"""HydroGFN health monitor: the 10 Tier 1 findings of the master plan.

Each ``<finding>_D_S`` function implements one finding: D is its hazard
domain, S its place within that domain. The numbering is ours, not the plan's;
the mapping to plan finding numbers is in :mod:`hydrograph_core.findings`.
"""

from .findings import (
    acute_infection_3_1,
    behavioral_health_decline_4_2,
    bone_demineralization_1_2,
    dehydration_2_1,
    hypoxia_co2_2_2,
    negative_energy_balance_2_3,
    orthostatic_intolerance_1_1,
    radiation_exposure_3_2,
    sans_fluid_shift_1_3,
    sleep_deficiency_4_1,
)
from .shared import Status

__all__ = [
    "Status",
    "__version__",
    "acute_infection_3_1",
    "behavioral_health_decline_4_2",
    "bone_demineralization_1_2",
    "dehydration_2_1",
    "hypoxia_co2_2_2",
    "negative_energy_balance_2_3",
    "orthostatic_intolerance_1_1",
    "radiation_exposure_3_2",
    "sans_fluid_shift_1_3",
    "sleep_deficiency_4_1",
]

__version__ = "0.1.0"
