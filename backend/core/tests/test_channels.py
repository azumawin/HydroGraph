"""Tests for core.channels (cutoffs from the master plan, else NSA_hydrograph.md).

Values are in the SI wire units the simulator sends.
"""

import unittest
from typing import get_args

from core.channels import CHANNELS, SCHEDULES, Evaluation, evaluate_reading
from core.environments import ENVIRONMENTS

MMHG = 133.322  # Pa
ISS = ENVIRONMENTS["iss_leo"]  # 14.6 uSv/h baseline
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
            ("ambient_dose_rate", 64.6 * USV_H, "nominal"),
            ("ambient_dose_rate", 64.7 * USV_H, "warning"),
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
                self.assertEqual(
                    evaluate_reading(channel, value, environment=ISS), expected
                )

    def test_every_channel_is_graded(self) -> None:
        for channel, info in CHANNELS.items():
            value: float | bool | str = (
                "ALERT"
                if info["value_type"] == "enum"
                else True if info["value_type"] == "boolean" else 1.0
            )
            with self.subTest(channel=channel):
                self.assertIn(
                    evaluate_reading(channel, value, environment=ISS),
                    get_args(Evaluation),
                )

    def test_unknown_channel_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unknown channel "heartrate"'):
            _ = evaluate_reading("heartrate", 72, environment=ISS)

    def test_dose_rate_is_graded_above_the_environment_baseline(self) -> None:
        cases = [
            ("lunar_surface", 57.1, "nominal"),
            ("lunar_surface", 107.1, "nominal"),
            ("lunar_surface", 107.2, "warning"),
            ("mars_transit", 76.7, "nominal"),
            ("mars_transit", 126.8, "warning"),
            ("mars_surface", 76.8, "warning"),
        ]
        for environment, usv_h, expected in cases:
            with self.subTest(environment=environment, usv_h=usv_h):
                self.assertEqual(
                    evaluate_reading(
                        "ambient_dose_rate",
                        usv_h * USV_H,
                        environment=ENVIRONMENTS[environment],
                    ),
                    expected,
                )


class TestDisplay(unittest.TestCase):
    def test_converts_wire_values_to_spec_units(self) -> None:
        cases: list[tuple[str, float, str, float]] = [
            ("heart_rate", 72 / 60, "bpm", 72.0),
            ("bp_systolic", 114 * MMHG, "mmHg", 114.0),
            ("spo2", 0.97, "%", 97.0),
            ("body_temperature", 310.15, "°C", 37.0),
            ("il6_serum", 3e-9, "pg/mL", 3.0),
            ("ambient_dose_rate", 14.6 * USV_H, "µSv/h", 14.6),
            ("ambient_integrated_dose", 0.0028, "mSv", 2.8),
        ]
        for channel, wire, unit, shown in cases:
            with self.subTest(channel=channel):
                display = CHANNELS[channel]["display"]
                self.assertEqual(display["unit"], unit)
                self.assertAlmostEqual(
                    wire * display["scale"] + display["offset"], shown
                )

    def test_booleans_have_no_display_unit(self) -> None:
        for channel, info in CHANNELS.items():
            if info["value_type"] == "boolean":
                with self.subTest(channel=channel):
                    self.assertEqual(
                        info["display"], {"unit": "", "scale": 1.0, "offset": 0.0}
                    )


def test_every_schedule_names_a_known_channel_with_a_positive_interval() -> None:
    for channel, interval in SCHEDULES.items():
        assert channel in CHANNELS
        assert interval > 0
