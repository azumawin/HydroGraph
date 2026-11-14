"""Tests for hydrograph_core.payload (structure from master plan p.8, section 5)."""

import json
import unittest
from collections.abc import Mapping, Sequence

import hydrograph_core as h
from hydrograph_core.findings import radiation_exposure_10
from hydrograph_core.gauge_factor import dynamic_gauge_factor
from hydrograph_core.payload import TelemetryPayload, telemetry_payload


def _thermistor_ohm(target_c: float) -> float:
    """Bisect the thermistor resistance that core_temperature_2_2 reads as target_c."""
    lo, hi = 100.0, 100000.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if h.core_temperature_2_2(mid)["temperature_c"] > target_c:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _payload(
    icp_strain: float, right_ratio: float, others: Sequence[Mapping[str, object]] = ()
) -> TelemetryPayload:
    """A tick with nominal vitals; ICP strain and the right joint strip vary."""
    freqs = [4 + 0.5 * i for i in range(19)]
    return telemetry_payload(
        timestamp="2026-11-14T12:00:00Z",
        user_state="ACTIVE",
        heart_rate_bpm=74,
        bp_systolic_mmhg=118,
        bp_diastolic_mmhg=78,
        respiratory_rate_br_min=15,
        spo2_pct=97.4,
        glucose=h.glucose_2_1(30.0),
        temperature=h.core_temperature_2_2(_thermistor_ohm(36.8)),
        news2_score=0,
        cabin_ppco2_mmhg=2.4,
        gauge=dynamic_gauge_factor(0.08),
        icp=h.cephalic_fluid_shift_1_1(0.45089 * (1 + 2.1 * icp_strain)),
        cortisol=h.cortisol_4_1(0.25),
        cortisol_di_ds_ratio=0.25,
        cortisol_slope_status=h.Status.NOMINAL,
        ntx_change_pct=18.5,
        il6_pg_ml=1.8,
        post_ared_window=False,
        latent_virus_shedding="NO_DETECT",
        troponin=h.troponin_1_2(0.005),
        cfe=h.cognitive_fatigue_4_2(freqs, [1.0 if f < 8 else 2.0 for f in freqs]),
        joint_angles_deg={"left_knee_flexion": 112.4},
        form=h.joint_kinematics_3_2(0.04, right_ratio),
        form_joint="lumbar",
        others=others,
    )


class TestTelemetryPayload(unittest.TestCase):
    """Payload layout and copilot decision."""

    def test_layout_matches_plan_example(self) -> None:
        """Top-level and block keys are those of the p.6 example."""
        payload = _payload(0.005, 0.04)
        self.assertEqual(
            list(payload),
            [
                "timestamp",
                "user_state",
                "standard_vitals",
                "advanced_biotransduction",
                "kinematics_3d_dummy",
                "copilot_decision_engine",
            ],
        )
        self.assertEqual(
            sorted(payload["kinematics_3d_dummy"]),
            ["form_status", "left_knee_flexion_deg", "lumbar_asymmetry_ratio"],
        )
        self.assertEqual(
            list(payload["standard_vitals"]),
            [
                "heart_rate_bpm",
                "blood_pressure_sys_mmHg",
                "blood_pressure_dia_mmHg",
                "respiratory_rate_br_min",
                "spo2_pct",
                "blood_glucose_mg_dL",
                "zhf_core_temp_celsius",
                "news2_aggregate_score",
                "cabin_ppco2_mmHg",
            ],
        )
        blocks = payload["advanced_biotransduction"]
        self.assertEqual(
            list(blocks["carrageenan_hydrogel"]),
            [
                "displacement_mm",
                "strain_percentage",
                "dynamic_gauge_factor",
                "delta_R_over_R0",
                "jugular_fluid_shift_pct",
                "estimated_icp_mmHg",
            ],
        )
        self.assertEqual(
            list(blocks["graphene_gfet"]),
            [
                "isf_cortisol_nM",
                "cortisol_diurnal_slope_status",
                "bone_ntx_pct_baseline",
                "il6_pg_mL",
                "post_ared_exercise_window",
                "latent_virus_shedding",
                "hs_troponin_ng_mL",
                "delta_Ids_over_I0",
                "eeg_theta_alpha_ratio",
            ],
        )
        self.assertAlmostEqual(
            payload["standard_vitals"]["zhf_core_temp_celsius"], 36.8, delta=0.02
        )

    def test_json_serializable(self) -> None:
        """Statuses come out as plain strings."""
        text = json.dumps(_payload(0.005, 0.04))
        self.assertIn('"form_status": "NOMINAL"', text)

    def test_all_nominal(self) -> None:
        """No hazard and no action when every result is nominal."""
        copilot = _payload(0.005, 0.04)["copilot_decision_engine"]
        self.assertEqual(copilot["overall_status"], "NOMINAL")
        self.assertEqual(copilot["primary_hazard"], "None")
        self.assertEqual(copilot["recommended_actions"], [])

    def test_two_warnings_like_plan_example(self) -> None:
        """ICP and form warnings give the p.8 example's two-hazard shape."""
        copilot = _payload(0.0142, 0.03)["copilot_decision_engine"]
        self.assertEqual(copilot["overall_status"], "WARNING")
        self.assertEqual(
            copilot["primary_hazard"],
            "SANS Jugular Fluid Shift + Exercise Form Asymmetry",
        )
        self.assertEqual(
            copilot["recommended_actions"],
            [
                "1. Engage LBNP at -35 mmHg for 20 min",
                "2. Highlight joint in red on 3D mannequin, trigger form correction prompt",
            ],
        )

    def test_critical_finding_ranks_first(self) -> None:
        """A critical finding in others becomes the hazard and the first action."""
        shelter = radiation_exposure_10(100, 10, True)
        copilot = _payload(0.0142, 0.04, (shelter,))["copilot_decision_engine"]
        self.assertEqual(copilot["overall_status"], "CRITICAL")
        self.assertEqual(copilot["primary_hazard"], "Radiation Exposure")
        self.assertEqual(
            copilot["recommended_actions"][0],
            "1. Move to shielded storm shelter zone immediately and confirm hatch closure",
        )


if __name__ == "__main__":
    _ = unittest.main()
