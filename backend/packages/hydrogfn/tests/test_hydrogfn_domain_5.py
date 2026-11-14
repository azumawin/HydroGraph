"""Research-based tests for hydrogfn.domain_5 (parameter 5.1)."""

import unittest

from hydrogfn import Status
from hydrogfn.domain_5 import inflammatory_cytokines_5_1


def _cytokines(il6: float, tnf: float):
    """Run inflammatory_cytokines_5_1 with equal weights (spec gives none)."""
    return inflammatory_cytokines_5_1(il6, tnf, False, w1=1.0, w2=1.0)


class TestDomain5Research(unittest.TestCase):
    def test_index_is_weighted_sum(self) -> None:
        """I_inf = w1*[IL-6] + w2*[TNF-a] (NSA_hydrograph.md Parameter 5.1)."""
        res = inflammatory_cytokines_5_1(2.0, 4.0, False, w1=0.5, w2=2.0)
        self.assertAlmostEqual(res["inflammatory_index"], 9.0)

    def test_healthy_levels_nominal(self) -> None:
        """IL-6 1.5 pg/mL is below the 7 pg/mL healthy 95th percentile (https://www.labcorp.com/test-menu/29791/interleukin-6-serum); TNF-a 1.0 is within 0.0-2.2 pg/mL (https://www.labcorp.com/tests/140673/tumor-necrosis-factor-a)."""
        self.assertEqual(_cytokines(1.5, 1.0)["status"], Status.NOMINAL)

    def test_elevated_il6_not_nominal(self) -> None:
        """IL-6 15 pg/mL is above the 7 pg/mL healthy upper limit (Labcorp IL-6)."""
        self.assertNotEqual(_cytokines(15.0, 1.0)["status"], Status.NOMINAL)

    def test_elevated_tnf_not_nominal(self) -> None:
        """TNF-a 10 pg/mL is above the 0.0-2.2 pg/mL reference range (Labcorp TNF-a)."""
        self.assertNotEqual(_cytokines(1.0, 10.0)["status"], Status.NOMINAL)

    def test_il6_ignored_after_ared(self) -> None:
        """Master plan p.5: IL-6 is gated to ignore post-ARED spikes (< 2 hrs post-workout)."""
        res = inflammatory_cytokines_5_1(4.0, 0.0, True, w1=1.0, w2=1.0)
        self.assertEqual(res["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code returns WARNING at IL-6 4.2 pg/mL vs healthy pooled mean 5.19 pg/mL (https://zendy.io/title/10.1002/jmv.26654) and 95th percentile 7 pg/mL (Labcorp IL-6)
    @unittest.expectedFailure
    def test_il6_4_2_nominal(self) -> None:
        """IL-6 4.2 pg/mL (the spec's own example payload) is a normal healthy-adult level (Said et al. 2021 meta-analysis, Labcorp IL-6)."""
        self.assertEqual(_cytokines(4.2, 0.5)["status"], Status.NOMINAL)


if __name__ == "__main__":
    _ = unittest.main()
