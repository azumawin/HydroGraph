"""Research-based tests for hydrograph_core.domain_4 (expected values from published sources)."""

import unittest

from hydrograph_core.domain_4 import cognitive_fatigue_4_2, cortisol_4_1, sleep_mood_4_3
from hydrograph_core.shared import Status

_SEVERITY: dict[Status, int] = {
    Status.NOMINAL: 0,
    Status.WARNING: 1,
    Status.CRITICAL: 2,
}


def _grid() -> list[float]:
    """Dense 0-30 Hz grid, step 0.25 Hz."""
    return [i * 0.25 for i in range(121)]


def _psd(
    theta: float = 1.0, bumps: tuple[tuple[float, float], ...] = ()
) -> list[float]:
    """PSD of 1.0 uV^2/Hz with a theta-band amplitude and optional (freq, value) bumps."""
    out: list[float] = []
    for f in _grid():
        v = theta if 4.0 <= f <= 8.0 else 1.0
        for bf, bv in bumps:
            if f == bf:
                v = bv
        out.append(v)
    return out


def _ratio_for_cortisol(c_nm: float) -> float:
    """Langmuir forward equation: ratio = i_max * C / (k_d + C)."""
    return 0.65 * c_nm / (14.8 + c_nm)


class TestDomain4(unittest.TestCase):
    """Tests for parameters 4.1, 4.2 and 4.3."""

    def test_cortisol_half_saturation(self) -> None:
        """Langmuir half-saturation at C = Kd (https://pmc.ncbi.nlm.nih.gov/articles/PMC8945915/figure/biosensors-12-00142-f004)."""
        result = cortisol_4_1(0.325)
        self.assertAlmostEqual(result["cortisol_nm"], 14.8, delta=0.01)

    def test_cortisol_saturation_raises(self) -> None:
        """Langmuir response saturates at Imax (https://pmc.ncbi.nlm.nih.gov/articles/PMC8945915/figure/biosensors-12-00142-f004)."""
        for ratio in (0.65, 0.7):
            with self.assertRaises(ValueError):
                _ = cortisol_4_1(ratio)

    # RESEARCH MISMATCH: code returns CRITICAL for 40 nM (threshold 30 nM) vs healthy morning salivary cortisol 28-75 nM (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6787562/)
    @unittest.expectedFailure
    def test_cortisol_40nm_not_critical(self) -> None:
        """40 nM is normal morning cortisol (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6787562/)."""
        result = cortisol_4_1(_ratio_for_cortisol(40.0))
        self.assertNotEqual(result["status"], Status.CRITICAL)

    # RESEARCH MISMATCH: code returns CRITICAL for 50 nM (threshold 30 nM) vs healthy morning salivary cortisol 28-75 nM (https://link.springer.com/article/10.1038/s41598-017-13684-7)
    @unittest.expectedFailure
    def test_cortisol_50nm_not_critical(self) -> None:
        """50 nM is within healthy range (https://link.springer.com/article/10.1038/s41598-017-13684-7)."""
        result = cortisol_4_1(_ratio_for_cortisol(50.0))
        self.assertNotEqual(result["status"], Status.CRITICAL)

    def test_cfe_ignores_out_of_band_power(self) -> None:
        """Theta is 4-8 Hz, alpha 8-13 Hz (https://arxiv.org/pdf/2202.12937)."""
        base = cognitive_fatigue_4_2(_grid(), _psd())
        bumped = cognitive_fatigue_4_2(
            _grid(), _psd(bumps=((2.0, 500.0), (20.0, 500.0)))
        )
        self.assertAlmostEqual(base["cfe_ratio"], bumped["cfe_ratio"], delta=0.001)
        self.assertAlmostEqual(
            base["theta_power_uv2"], bumped["theta_power_uv2"], delta=0.001
        )

    def test_cfe_flat_psd_band_widths(self) -> None:
        """Band widths theta 4 Hz, alpha 5 Hz (https://arxiv.org/pdf/2202.12937)."""
        result = cognitive_fatigue_4_2(_grid(), _psd())
        self.assertAlmostEqual(result["theta_power_uv2"], 4.0, delta=0.001)
        self.assertAlmostEqual(result["alpha_power_uv2"], 5.0, delta=0.001)
        self.assertAlmostEqual(result["cfe_ratio"], 0.8, delta=0.001)

    def test_cfe_monotonic_in_theta(self) -> None:
        """Theta/alpha rises with fatigue (https://pmc.ncbi.nlm.nih.gov/articles/PMC7820710)."""
        prev_cfe = -1.0
        prev_sev = 0
        for amp in (0.1, 0.5, 1.0, 2.0, 5.0, 20.0):
            result = cognitive_fatigue_4_2(_grid(), _psd(theta=amp))
            self.assertGreater(result["cfe_ratio"], prev_cfe)
            sev = _SEVERITY[result["status"]]
            self.assertGreaterEqual(sev, prev_sev)
            prev_cfe, prev_sev = result["cfe_ratio"], sev

    def test_sleep_six_hours_not_nominal(self) -> None:
        """6 h is inadequate (https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/)."""
        result = sleep_mood_4_3(1.0, 1.5, 3.5, 8.0, 8.0, 8.0, 2.0)
        self.assertNotEqual(result["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code returns WARNING for 7.2 h (needs > 7.5 h) vs AASM/SRS adults need >= 7 h (https://pmc.ncbi.nlm.nih.gov/articles/PMC4434546/)
    @unittest.expectedFailure
    def test_sleep_7_2_hours_nominal(self) -> None:
        """7.2 h meets AASM >= 7 h (https://pmc.ncbi.nlm.nih.gov/articles/PMC4434546/)."""
        result = sleep_mood_4_3(2.0, 2.0, 3.2, 7.0, 8.0, 8.0, 2.0)
        self.assertEqual(result["status"], Status.NOMINAL)


if __name__ == "__main__":
    _ = unittest.main()
