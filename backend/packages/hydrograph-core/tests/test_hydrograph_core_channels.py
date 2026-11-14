"""Tests for hydrograph_core.channels (cutoffs from the master plan, else NSA_hydrograph.md).

Values are in the SI wire units the simulator sends.
"""

import unittest
from typing import get_args

from hydrograph_core.channels import CHANNELS, Evaluation, evaluate_reading

MMHG = 133.322  # Pa
USV_H = 1e-6 / 3600  # Sv/s


class TestEvaluateReading(unittest.TestCase):
    def test_boundaries(self) -> None:
        cases: list[tuple[str, float | bool, Evaluation]] = [
            ("heart_rate", 45 / 60, "unspecified"),
            ("heart_rate", 90 / 60, "nominal"),
            ("heart_rate", 95 / 60, "warning"),
            ("bp_systolic", 114 * MMHG, "unspecified"),
            ("spo2", 0.94, "nominal"),
            ("spo2", 0.939, "warning"),
            ("spo2", 0.899, "critical"),
            ("body_temperature", 273.15 + 38.0, "nominal"),
            ("body_temperature", 273.15 + 38.1, "warning"),
            ("body_temperature", 273.15 + 35.9, "warning"),
            ("glucose", 3.9, "nominal"),
            ("glucose", 3.8, "warning"),
            ("glucose", 2.9, "critical"),
            ("glucose", 7.1, "unspecified"),
            ("troponin_i", 0.04e-6, "nominal"),
            ("troponin_i", 0.05e-6, "critical"),
            ("lactate", 4.0, "nominal"),
            ("lactate", 4.1, "warning"),
            ("bone_ntx_pct_baseline", 0.25, "nominal"),
            ("bone_ntx_pct_baseline", 0.26, "warning"),
            ("il6_serum", 3.0e-9, "nominal"),
            ("il6_serum", 3.1e-9, "warning"),
            ("viral_ebv_detected", False, "nominal"),
            ("viral_cmv_detected", True, "warning"),
            ("urine_specific_gravity", 1.020, "nominal"),
            ("urine_specific_gravity", 1.021, "warning"),
            ("urine_volume_24h", 2.0e-3, "nominal"),
            ("urine_volume_24h", 1.9e-3, "warning"),
            ("ambient_ppco2", 3.0 * MMHG, "nominal"),
            ("ambient_ppco2", 3.1 * MMHG, "warning"),
            ("ambient_dose_rate", 50 * USV_H, "nominal"),
            ("ambient_dose_rate", 51 * USV_H, "warning"),
            ("ambient_integrated_dose", 0.600, "nominal"),
            ("ambient_integrated_dose", 0.601, "warning"),
            ("spe_flag", False, "nominal"),
            ("spe_flag", True, "critical"),
            ("cortisol_saliva", 20e-6, "unspecified"),
            ("eeg_cfe_ratio", 0.69, "nominal"),
            ("eeg_cfe_ratio", 0.70, "warning"),
            ("eeg_cfe_ratio", 1.20, "warning"),
            ("eeg_cfe_ratio", 1.21, "critical"),
            ("jugular_strain_pct", 0.0109, "nominal"),
            ("jugular_strain_pct", 0.0110, "warning"),
            ("jugular_strain_pct", 0.0181, "critical"),
            ("icp_risk_indicator_mmHg", 11.9 * MMHG, "nominal"),
            ("icp_risk_indicator_mmHg", 12.0 * MMHG, "warning"),
            ("icp_risk_indicator_mmHg", 18.1 * MMHG, "critical"),
            ("delta_R_over_R0", 0.1, "unspecified"),
            ("visual_acuity_logmar", 0.2, "unspecified"),
            ("amsler_grid_distortion", True, "unspecified"),
        ]
        for channel, value, expected in cases:
            with self.subTest(channel=channel, value=value):
                self.assertEqual(evaluate_reading(channel, value), expected)

    def test_every_channel_is_graded(self) -> None:
        for channel, info in CHANNELS.items():
            value: float | bool | str = (
                "ALERT"
                if info["value_type"] == "enum"
                else True if info["value_type"] == "boolean" else 1.0
            )
            with self.subTest(channel=channel):
                self.assertIn(evaluate_reading(channel, value), get_args(Evaluation))

    def test_unknown_channel_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unknown channel "heartrate"'):
            _ = evaluate_reading("heartrate", 72)
