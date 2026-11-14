"""HydroGFN health monitor: the 10 Tier 1 findings of the master plan.

Each ``<finding>_N`` function implements Finding N and lives in
:mod:`hydrograph_core.findings`.
"""

from .findings import (
    acute_infection_3,
    behavioral_health_decline_6,
    bone_demineralization_8,
    dehydration_2,
    hypoxia_co2_4,
    negative_energy_balance_7,
    orthostatic_intolerance_1,
    radiation_exposure_10,
    sans_fluid_shift_9,
    sleep_deficiency_5,
)
from .shared import Status

__all__ = [
    "Status",
    "__version__",
    "acute_infection_3",
    "behavioral_health_decline_6",
    "bone_demineralization_8",
    "dehydration_2",
    "hypoxia_co2_4",
    "negative_energy_balance_7",
    "orthostatic_intolerance_1",
    "radiation_exposure_10",
    "sans_fluid_shift_9",
    "sleep_deficiency_5",
]

__version__ = "0.1.0"
