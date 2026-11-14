"""Research-based tests for hydrograph_core.domain_1 (parameters 1.1-1.3)."""

import math
import unittest

from hydrograph_core import Status
from hydrograph_core.domain_1 import (
    blood_pressure_heart_rate_1_3,
    cephalic_fluid_shift_1_1,
    troponin_1_2,
)


def _map_hr(map_mmhg: float, hr_bpm: float) -> Status:
    """Status for a target MAP/HR, inverting the spec's MAP = -45.2 ln(PTT) + 280.5."""
    ptt_ms = math.exp((280.5 - map_mmhg) / 45.2)
    return blood_pressure_heart_rate_1_3(ptt_ms, 60.0 / hr_bpm)["status"]


class TestDomain1Research(unittest.TestCase):
    def test_strain_gauge_factor(self) -> None:
        """Gauge factor: eps = (dR/R0)/GF (r0=100, r=102.1, GF=2.1 -> 1 %)."""
        res = cephalic_fluid_shift_1_1(102.1, r0=100.0)
        self.assertAlmostEqual(res["strain_pct"], 1.0, places=6)

    def test_icp_baseline_nominal(self) -> None:
        """Normal ICP 7-15 mmHg (https://wikiwand.com/EN/Intracranial_pressure)."""
        res = cephalic_fluid_shift_1_1(0.45089)
        self.assertEqual(res["status"], Status.NOMINAL)

    def test_icp_21_critical(self) -> None:
        """ICH > 20 mmHg (https://www.stroke-manual.com/?p=40197)."""
        res = cephalic_fluid_shift_1_1(0.45089, icp_baseline=21.0)
        self.assertEqual(res["status"], Status.CRITICAL)

    def test_icp_16_not_nominal(self) -> None:
        """16 mmHg exceeds the normal 7-15 range (wikiwand Intracranial_pressure)."""
        res = cephalic_fluid_shift_1_1(0.45089, icp_baseline=16.0)
        self.assertNotEqual(res["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code gives 0.151 mV (bracket 1 - delta/(2 lambda_D) = -0.75, magnitude taken) vs 0.006 mV with exp(-delta/lambda_D) screening (arXiv 1708.08958, 2208.10742)
    @unittest.expectedFailure
    def test_debye_screening_at_spec_values(self) -> None:
        """Bound-charge potential ~ exp(-d/lambda_D): delta 3.5 nm, lambda_D 1 nm keeps ~3 % (arXiv 1708.08958, 2208.10742)."""
        unscreened_mv = 1.602e-19 * 2.5e14 / (78.4 * 8.854e-12) * 3.5e-9 * 1000
        screened_mv = unscreened_mv * math.exp(-3.5)
        res = troponin_1_2(0.0)
        self.assertAlmostEqual(res["delta_vt_mv"], screened_mv, delta=0.002)

    def test_ctni_above_99th_percentile_critical(self) -> None:
        """0.04 ng/mL upper limit of normal (https://www.bmj.com/content/364/bmj.l729.full)."""
        res = troponin_1_2(0.041)
        self.assertEqual(res["status"], Status.CRITICAL)

    def test_ctni_low_nominal(self) -> None:
        """0.005 ng/mL is below 0.04 ng/mL limit (bmj.l729)."""
        res = troponin_1_2(0.005)
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
