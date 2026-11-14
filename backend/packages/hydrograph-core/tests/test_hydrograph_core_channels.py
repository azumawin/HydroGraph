"""Tests for hydrograph_core.channels (cutoffs from the master plan, else NSA_hydrograph.md).

Values are in the SI wire units the simulator sends.
"""

import unittest

from hydrograph_core.channels import CHANNELS, evaluate_reading
from hydrograph_core.shared import Status

MMHG = 133.322  # Pa
USV_H = 1e-6 / 3600  # Sv/s


class TestEvaluateReading(unittest.TestCase):
    def test_boundaries(self) -> None:
        cases: list[tuple[str, float | bool, Status]] = [
            ("heart_rate", 45 / 60, Status.UNSPECIFIED),
            ("heart_rate", 90 / 60, Status.NOMINAL),
            ("heart_rate", 95 / 60, Status.WARNING),
            ("bp_systolic", 114 * MMHG, Status.UNSPECIFIED),
            ("spo2", 0.94, Status.NOMINAL),
            ("spo2", 0.939, Status.WARNING),
            ("spo2", 0.899, Status.CRITICAL),
            ("body_temperature", 273.15 + 38.0, Status.NOMINAL),
            ("body_temperature", 273.15 + 38.1, Status.WARNING),
            ("body_temperature", 273.15 + 35.9, Status.WARNING),
            ("glucose", 3.9, Status.NOMINAL),
            ("glucose", 3.8, Status.WARNING),
            ("glucose", 2.9, Status.CRITICAL),
            ("glucose", 7.1, Status.UNSPECIFIED),
            ("troponin_i", 0.04e-6, Status.NOMINAL),
            ("troponin_i", 0.05e-6, Status.CRITICAL),
            ("lactate", 4.0, Status.NOMINAL),
            ("lactate", 4.1, Status.WARNING),
            ("bone_ntx_pct_baseline", 0.25, Status.NOMINAL),
            ("bone_ntx_pct_baseline", 0.26, Status.WARNING),
            ("il6_serum", 3.0e-9, Status.NOMINAL),
            ("il6_serum", 3.1e-9, Status.WARNING),
            ("viral_ebv_detected", False, Status.NOMINAL),
            ("viral_cmv_detected", True, Status.WARNING),
            ("urine_specific_gravity", 1.020, Status.NOMINAL),
            ("urine_specific_gravity", 1.021, Status.WARNING),
            ("urine_volume_24h", 2.0e-3, Status.NOMINAL),
            ("urine_volume_24h", 1.9e-3, Status.WARNING),
            ("ambient_ppco2", 3.0 * MMHG, Status.NOMINAL),
            ("ambient_ppco2", 3.1 * MMHG, Status.WARNING),
            ("ambient_dose_rate", 50 * USV_H, Status.NOMINAL),
            ("ambient_dose_rate", 51 * USV_H, Status.WARNING),
            ("ambient_integrated_dose", 0.600, Status.NOMINAL),
            ("ambient_integrated_dose", 0.601, Status.WARNING),
            ("spe_flag", False, Status.NOMINAL),
            ("spe_flag", True, Status.CRITICAL),
            ("cortisol_saliva", 20e-6, Status.UNSPECIFIED),
        ]
        for channel, value, expected in cases:
            with self.subTest(channel=channel, value=value):
                self.assertIs(evaluate_reading(channel, value), expected)

    def test_every_channel_is_graded(self) -> None:
        for channel, info in CHANNELS.items():
            value: float | bool = True if info["value_type"] == "boolean" else 1.0
            with self.subTest(channel=channel):
                self.assertIsInstance(evaluate_reading(channel, value), Status)

    def test_unknown_channel_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unknown channel "heartrate"'):
            _ = evaluate_reading("heartrate", 72)
