"""Tests for hydrogfn.gauge_factor (expected values from master plan p.3, section 3A)."""

import unittest

from hydrogfn.gauge_factor import dynamic_gauge_factor, strain_from_resistance


class TestDynamicGaugeFactor(unittest.TestCase):
    """Forward map: strain -> GF and dR/R0."""

    def test_range_a_is_constant(self) -> None:
        """Range A, 0-5 %: GF1 = 1180.75."""
        result = dynamic_gauge_factor(2.5)
        self.assertEqual(result["range"], "A")
        self.assertEqual(result["gauge_factor"], 1180.75)
        self.assertAlmostEqual(result["delta_r_over_r0"], 29.5188, places=4)

    def test_range_b_midpoint(self) -> None:
        """Range B, 5-15 %: GF2 = 233.48-389.58, midpoint 311.53 at 10 %."""
        result = dynamic_gauge_factor(10.0)
        self.assertEqual(result["range"], "B")
        self.assertAlmostEqual(result["gauge_factor"], 311.53, places=2)

    def test_range_c_top(self) -> None:
        """Range C, 15-30 %: GF3 = 74.34-114.86, so 114.86 at 30 %."""
        result = dynamic_gauge_factor(30.0)
        self.assertEqual(result["range"], "C")
        self.assertAlmostEqual(result["gauge_factor"], 114.86, places=2)

    def test_shared_boundaries_go_to_lower_range(self) -> None:
        """5 % and 15 % appear in two ranges; the lower one wins."""
        self.assertEqual(dynamic_gauge_factor(5.0)["range"], "A")
        self.assertEqual(dynamic_gauge_factor(15.0)["range"], "B")

    def test_outside_defined_strain_raises(self) -> None:
        """The plan defines GF only for 0-30 %."""
        with self.assertRaises(ValueError):
            _ = dynamic_gauge_factor(-1.0)
        with self.assertRaises(ValueError):
            _ = dynamic_gauge_factor(30.1)


class TestStrainFromResistance(unittest.TestCase):
    """Inverse map: dR/R0 -> strain."""

    def test_round_trip_range_a(self) -> None:
        """Inverting the forward map recovers the strain."""
        ratio = dynamic_gauge_factor(1.42)["delta_r_over_r0"]
        result = strain_from_resistance(ratio)
        self.assertAlmostEqual(result["strain_pct"], 1.42, places=2)
        self.assertEqual(result["range"], "A")

    def test_ambiguous_reading_lists_all_ranges(self) -> None:
        """dR/R0 = 20 fits A (1.694 %), B and C: the GF drops make it ambiguous."""
        result = strain_from_resistance(20.0)
        self.assertEqual(len(result["candidates_pct"]), 3)
        self.assertAlmostEqual(result["strain_pct"], 1.694, places=3)
        for pct in result["candidates_pct"]:
            ratio = dynamic_gauge_factor(pct)["delta_r_over_r0"]
            self.assertAlmostEqual(ratio, 20.0, delta=0.01)

    def test_range_b_only_reading_unreachable_by_lowest(self) -> None:
        """dR/R0 = 58.0 fits A (4.912 %) and B; the lowest-strain answer is A."""
        result = strain_from_resistance(58.0)
        self.assertEqual(result["range"], "A")
        self.assertEqual(len(result["candidates_pct"]), 2)

    def test_above_range_a_maximum_raises(self) -> None:
        """Top of range A, 1180.75 * 0.05 = 59.0375, is the largest dR/R0 the plan allows."""
        self.assertEqual(strain_from_resistance(59.0375)["strain_pct"], 5.0)
        with self.assertRaises(ValueError):
            _ = strain_from_resistance(59.1)

    def test_negative_reading_raises(self) -> None:
        """Compression (dR/R0 < 0) has no range in the plan."""
        with self.assertRaises(ValueError):
            _ = strain_from_resistance(-0.1)


if __name__ == "__main__":
    _ = unittest.main()
