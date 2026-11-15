"""Tests for hydrograph_core.assessment (NEWS2 bands from RCP 2017; SI inputs)."""

import unittest
from typing import cast

from hydrograph_core.assessment import FINDINGS, evaluate_findings, news2
from hydrograph_core.channels import CHANNELS
from hydrograph_core.environments import ENVIRONMENTS
from hydrograph_core.findings import EnergyBalanceResult

MMHG = 133.322  # Pa
ISS = ENVIRONMENTS["iss_leo"]

HEALTHY: dict[str, float | bool] = {
    "heart_rate": 70 / 60,
    "bp_systolic": 120 * MMHG,
    "bp_diastolic": 80 * MMHG,
    "spo2": 0.98,
    "body_temperature": 273.15 + 36.8,
    "respiratory_rate": 14 / 60,
    "glucose": 5.0,
    "lactate": 1.0,
    "bone_ntx_pct_baseline": 0.03,
    "il6_serum": 1.5e-9,
    "viral_ebv_detected": False,
    "viral_vzv_detected": False,
    "viral_cmv_detected": False,
    "body_mass": 75.0,
    "urine_specific_gravity": 1.010,
    "urine_volume_24h": 2.7e-3,
    "ambient_ppco2": 2.0 * MMHG,
    "ambient_dose_rate": 14.6e-6 / 3600,
    "ambient_integrated_dose": 0.001,
    "spe_flag": False,
    "jugular_strain_pct": 0.0065,
}


class TestNews2(unittest.TestCase):
    def test_all_normal_scores_zero(self) -> None:
        """Source: NEWS2 chart, RCP 2017 (0 for RR 12-20, SpO2 >= 96, SBP 111-219, HR 51-90, T 36.1-38.0)."""
        self.assertEqual(
            {
                k: v
                for k, v in news2(14, 98, 120, 70, 36.8).items()
                if k != "components"
            },
            {"score": 0, "max_parameter_score": 0},
        )

    def test_band_edges(self) -> None:
        """Source: NEWS2 chart, RCP 2017."""
        cases = [
            ((8, 98, 120, 70, 36.8), 3),
            ((21, 98, 120, 70, 36.8), 2),
            ((14, 93, 120, 70, 36.8), 2),
            ((14, 95, 120, 70, 36.8), 1),
            ((14, 98, 100, 70, 36.8), 2),
            ((14, 98, 220, 70, 36.8), 3),
            ((14, 98, 120, 91, 36.8), 1),
            ((14, 98, 120, 131, 36.8), 3),
            ((14, 98, 120, 70, 36.0), 1),
            ((14, 98, 120, 70, 39.1), 2),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(news2(*args)["score"], expected)

    def test_max_parameter_score(self) -> None:
        self.assertEqual(
            {
                k: v
                for k, v in news2(25, 95, 120, 95, 36.8).items()
                if k != "components"
            },
            {"score": 5, "max_parameter_score": 3},
        )


class TestEvaluateFindings(unittest.TestCase):
    def test_blood_pressure_reuses_combined_thresholds_with_si_units(self) -> None:
        cases = [
            (120, 80, None, "nominal"),
            (121, 80, None, "warning"),
            (100, 70, None, "warning"),
            (90, 60, None, "critical"),
            (140, 80, None, "critical"),
            (120, 90, None, "critical"),
            (120, 80, 108, "nominal"),
            (120, 80, 109, "critical"),
        ]
        for sbp, dbp, hr, expected in cases:
            latest = {"bp_systolic": sbp * MMHG, "bp_diastolic": dbp * MMHG}
            if hr is not None:
                latest["heart_rate"] = hr / 60
            with self.subTest(sbp=sbp, dbp=dbp, hr=hr):
                result = evaluate_findings(latest, None, None, ISS)[
                    "blood_pressure_1_4"
                ]
                self.assertEqual(result["status"], expected)
                self.assertEqual(
                    result.get("map_mmhg"), round(dbp + (sbp - dbp) / 3, 1)
                )
                self.assertEqual(
                    result.get("shock_index"),
                    round(hr / sbp, 2) if hr is not None else None,
                )

    def test_blood_pressure_waits_for_both_pressures(self) -> None:
        result = evaluate_findings({"bp_systolic": 120 * MMHG}, None, None, ISS)
        self.assertNotIn("blood_pressure_1_4", result)

    def test_bad_pressure_pair_reports_sensor_error_without_breaking_findings(
        self,
    ) -> None:
        result = evaluate_findings(
            {**HEALTHY, "bp_systolic": 85 * MMHG, "bp_diastolic": 80 * MMHG},
            75.0,
            None,
            ISS,
        )
        self.assertIn("sensor_error", result["blood_pressure_1_4"])
        self.assertNotIn("map_mmhg", result["blood_pressure_1_4"])
        self.assertIn("acute_infection_3_1", result)

    def test_catalog_channels_exist(self) -> None:
        for finding, info in FINDINGS.items():
            with self.subTest(finding=finding):
                self.assertTrue(set(info["channels"]) <= set(CHANNELS))

    def test_healthy_crew_member_has_no_findings(self) -> None:
        results = evaluate_findings(HEALTHY, 75.0, None, ISS)
        monitored = {f for f, info in FINDINGS.items() if info["channels"]}
        self.assertEqual(set(results), monitored)
        for finding, result in results.items():
            with self.subTest(finding=finding):
                self.assertIn(result["status"], (False, "nominal"))
                self.assertEqual(result["action"], "No finding")

    def test_missing_input_leaves_finding_out(self) -> None:
        latest = {k: v for k, v in HEALTHY.items() if k != "urine_volume_24h"}
        self.assertNotIn(
            "bone_demineralization_1_2", evaluate_findings(latest, 75.0, None, ISS)
        )
        self.assertNotIn("dehydration_2_1", evaluate_findings(HEALTHY, None, None, ISS))

    def test_si_inputs_are_converted(self) -> None:
        sick = {
            **HEALTHY,
            "bone_ntx_pct_baseline": 0.30,
            "body_mass": 73.0,
            "spo2": 0.89,
            "spe_flag": True,
            "viral_cmv_detected": True,
            "jugular_strain_pct": 0.0155,
        }
        results = evaluate_findings(sick, 75.0, None, ISS)
        self.assertIn(
            "NTx > +25% from baseline", results["bone_demineralization_1_2"]["triggers"]
        )
        self.assertIs(results["dehydration_2_1"]["status"], True)
        self.assertEqual(results["hypoxia_co2_2_2"]["status"], "critical")
        self.assertEqual(results["radiation_exposure_3_2"]["status"], "critical")
        self.assertEqual(results["acute_infection_3_1"]["status"], "warning")
        self.assertEqual(results["sans_fluid_shift_1_3"]["status"], "warning")

    def test_jugular_strain_boundary_survives_float_noise(self) -> None:
        results = evaluate_findings({"jugular_strain_pct": 0.011}, None, None, ISS)
        self.assertEqual(results["sans_fluid_shift_1_3"]["status"], "warning")

    def test_weekly_loss_prefers_week_before(self) -> None:
        latest = {**HEALTHY, "body_mass": 74.0}

        def loss(week_before: float | None) -> float:
            result = evaluate_findings(latest, 80.0, week_before, ISS)
            energy = cast("EnergyBalanceResult", result["negative_energy_balance_2_3"])
            return energy["body_mass_loss_pct_week"]

        self.assertGreater(loss(None), 7.0)
        self.assertLess(loss(74.5), 1.0)

    def test_radiation_dose_rate_is_relative_to_the_environment(self) -> None:
        transit = ENVIRONMENTS["mars_transit"]
        background = {**HEALTHY, "ambient_dose_rate": 76.7e-6 / 3600}
        spike = {**HEALTHY, "ambient_dose_rate": 127.0e-6 / 3600}
        calm = evaluate_findings(background, 75.0, None, transit)[
            "radiation_exposure_3_2"
        ]
        alarm = evaluate_findings(spike, 75.0, None, transit)["radiation_exposure_3_2"]
        self.assertEqual(calm["status"], "nominal")
        self.assertEqual(alarm["triggers"], ["dose rate > 50 µSv/h above baseline"])
