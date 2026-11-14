"""Research-based tests for hydrogfn.domain_1 (parameters 1.1-1.3)."""

import unittest

from hydrogfn import Status
from hydrogfn.domain_1 import (
    blood_pressure_heart_rate_1_3,
    cephalic_fluid_shift_1_1,
    troponin_1_2,
)


def _map_hr(map_mmhg: float, hr_bpm: float) -> Status:
    """Status for a target MAP/HR (ptt_ms=1.0 so ln term vanishes, MAP=b)."""
    return blood_pressure_heart_rate_1_3(1.0, 60.0 / hr_bpm, b=map_mmhg)["status"]


class TestDomain1Research(unittest.TestCase):
    def test_strain_gauge_factor(self) -> None:
        """Gauge factor: eps = (dR/R0)/GF (r0=100, r=102.1, GF=2.1 -> 1 %)."""
        res = cephalic_fluid_shift_1_1(102.1, r0=100.0, gf=2.1)
        self.assertAlmostEqual(res["strain_pct"], 1.0, places=6)

    def test_icp_baseline_nominal(self) -> None:
        """Normal ICP 7-15 mmHg (https://wikiwand.com/EN/Intracranial_pressure)."""
        res = cephalic_fluid_shift_1_1(0.45089)
        self.assertEqual(res["status"], Status.NOMINAL)

    def test_icp_21_critical(self) -> None:
        """ICH > 20 mmHg (https://www.stroke-manual.com/?p=40197)."""
        res = cephalic_fluid_shift_1_1(0.45089, k1=0.0, icp_baseline=21.0)
        self.assertEqual(res["status"], Status.CRITICAL)

    def test_icp_16_not_nominal(self) -> None:
        """16 mmHg exceeds the normal 7-15 range (wikiwand Intracranial_pressure)."""
        res = cephalic_fluid_shift_1_1(0.45089, k1=0.0, icp_baseline=16.0)
        self.assertNotEqual(res["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code's |dVt| grows with delta (3.46, 17.31, 55.39 mV at 3, 5, 8 nm) vs Debye screening says it decays as exp(-d/lambda_D) (arXiv 1708.08958, 2208.10742)
    @unittest.expectedFailure
    def test_debye_screening_decreases_with_height(self) -> None:
        """Bound-charge potential ~ exp(-d/lambda_D) (arXiv 1708.08958, 2208.10742)."""
        vals = [
            troponin_1_2(0.0, n_b=1e16, delta=d, lambda_d=1e-9)["delta_vt_mv"]
            for d in (3e-9, 5e-9, 8e-9)
        ]
        self.assertGreater(abs(vals[0]), abs(vals[1]))
        self.assertGreater(abs(vals[1]), abs(vals[2]))

    # RESEARCH MISMATCH: code gives 92.314 mV at delta=10 nm vs ~0 (<1% of near-field value) expected by Debye screening (arXiv 1708.08958, 2208.10742)
    @unittest.expectedFailure
    def test_debye_screening_vanishes_far_away(self) -> None:
        """delta >> lambda_D gives ~0 signal (arXiv 1708.08958, 2208.10742)."""
        near = troponin_1_2(0.0, n_b=1e16, delta=0.5e-9, lambda_d=1e-9)
        far = troponin_1_2(0.0, n_b=1e16, delta=10e-9, lambda_d=1e-9)
        self.assertLess(abs(far["delta_vt_mv"]), 0.01 * abs(near["delta_vt_mv"]))

    def test_ctni_above_99th_percentile_critical(self) -> None:
        """0.04 ng/mL upper limit of normal (https://www.bmj.com/content/364/bmj.l729.full)."""
        res = troponin_1_2(0.041)
        self.assertEqual(res["status"], Status.CRITICAL)

    def test_ctni_low_nominal(self) -> None:
        """0.005 ng/mL is below 0.04 ng/mL limit (bmj.l729)."""
        res = troponin_1_2(0.005, n_b=0.0)
        self.assertEqual(res["status"], Status.NOMINAL)

    def test_map_decreases_with_ptt(self) -> None:
        """P = a ln(PTT) + b, BP inverse to PTT (US patent 10517489)."""
        maps = [
            blood_pressure_heart_rate_1_3(p, 0.8)["map_mmhg"] for p in (150, 200, 250)
        ]
        self.assertGreater(maps[0], maps[1])
        self.assertGreater(maps[1], maps[2])

    def test_hr_from_rr_interval(self) -> None:
        """HR = 60/RR: 0.8 s -> 75 bpm (US patent 10517489)."""
        res = blood_pressure_heart_rate_1_3(200.0, 0.8)
        self.assertAlmostEqual(res["hr_bpm"], 75.0, places=6)

    def test_normal_map_hr_nominal(self) -> None:
        """MAP 70-100, HR 60-100 normal (https://openstax.org/books/medical-surgical-nursing/pages/23-1-shock-overview, https://hospitalhandbook.ucsf.edu/node/2676)."""
        self.assertEqual(_map_hr(85.0, 75.0), Status.NOMINAL)

    def test_map_60_not_nominal(self) -> None:
        """MAP < 65 is hypoperfusion (openstax shock overview)."""
        self.assertNotEqual(_map_hr(60.0, 75.0), Status.NOMINAL)

    # RESEARCH MISMATCH: code returns WARNING for HR 95 bpm vs normal resting HR 60-100 bpm is NOMINAL (https://hospitalhandbook.ucsf.edu/node/2676)
    @unittest.expectedFailure
    def test_hr_95_with_normal_map_nominal(self) -> None:
        """HR 95 is within normal resting 60-100 (UCSF hospital handbook)."""
        self.assertEqual(_map_hr(85.0, 95.0), Status.NOMINAL)


if __name__ == "__main__":
    _ = unittest.main()
