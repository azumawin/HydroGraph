"""HydroGFN sensor telemetry: the 11 parameters of NSA_hydrograph.md (1.1-5.1).

Each ``<quantity>_N_M`` function implements Parameter N.M and lives in
``domain_N``. The 10 Tier 1 health findings of the master plan are in
:mod:`hydrograph_core.findings`.
"""

from .domain_1 import (
    blood_pressure_heart_rate_1_3,
    cephalic_fluid_shift_1_1,
    troponin_1_2,
)
from .domain_2 import core_temperature_2_2, glucose_2_1
from .domain_3 import bone_resorption_3_1, joint_kinematics_3_2
from .domain_4 import cognitive_fatigue_4_2, cortisol_4_1, sleep_mood_4_3
from .domain_5 import inflammatory_cytokines_5_1
from .shared import Status

__all__ = [
    "Status",
    "__version__",
    "blood_pressure_heart_rate_1_3",
    "bone_resorption_3_1",
    "cephalic_fluid_shift_1_1",
    "cognitive_fatigue_4_2",
    "core_temperature_2_2",
    "cortisol_4_1",
    "glucose_2_1",
    "inflammatory_cytokines_5_1",
    "joint_kinematics_3_2",
    "sleep_mood_4_3",
    "troponin_1_2",
]

__version__ = "0.1.0"
