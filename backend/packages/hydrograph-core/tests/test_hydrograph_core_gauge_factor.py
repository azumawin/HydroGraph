"""Tests for hydrograph_core.gauge_factor (expected values from master plan p.4-5, section 3A)."""

import unittest

from hydrograph_core.gauge_factor import dynamic_gauge_factor, strain_from_resistance


class TestDynamicGaugeFactor(unittest.TestCase):
    """Forward map: displacement -> strain, GF and dR/R0."""

    def test_zone_end_points(self) -> None:
        """Each zone's GF span runs from the high value at the low end."""
        cases = (
            (0.01, "1", 1180.75),
            (0.10, "1", 114.86),
            (0.20, "2", 54.24),
            (1.00, "2", 9.53),
            (4.00, "3", 0.94),
            (5.05, "3", 0.56),
        )
        for displacement, zone, gf in cases:
            result = dynamic_gauge_factor(displacement)
            self.assertEqual(result["zone"], zone)
            self.assertAlmostEqual(result["gauge_factor"], gf, places=2)

    def test_strain_from_displacement(self) -> None:
        """Plan p.5: 0.01 mm is 0.02 %, 4.00 mm is 8.00 % over L0 = 50 mm."""
        self.assertEqual(dynamic_gauge_factor(0.01)["strain_pct"], 0.02)
        self.assertEqual(dynamic_gauge_factor(4.00)["strain_pct"], 8.0)

    def test_plan_example_neighbourhood(self) -> None:
        """p.8 example: 0.08 mm, strain 0.16 %, GF 153.2, dR/R0 0.2451; power law gives 144."""
        result = dynamic_gauge_factor(0.08)
        self.assertEqual(result["strain_pct"], 0.16)
        self.assertAlmostEqual(result["gauge_factor"], 143.96, places=2)
        self.assertAlmostEqual(result["delta_r_over_r0"], 0.2303, places=4)

    def test_gaps_and_outside_raise(self) -> None:
        """The plan defines no GF below 0.01 mm, in the gaps, or above 5.05 mm."""
        for displacement in (0.005, 0.15, 2.0, 5.1):
            with self.assertRaises(ValueError):
                _ = dynamic_gauge_factor(displacement)


class TestStrainFromResistance(unittest.TestCase):
    """Inverse map: dR/R0 -> displacement."""

    def test_round_trip_every_zone(self) -> None:
        """Inverting the forward map recovers the displacement and zone."""
        for displacement in (0.01, 0.08, 0.10, 0.20, 0.6, 1.0, 4.0, 4.5, 5.05):
            forward = dynamic_gauge_factor(displacement)
            result = strain_from_resistance(forward["delta_r_over_r0"])
            self.assertAlmostEqual(result["displacement_mm"], displacement, places=3)
            self.assertEqual(result["zone"], forward["zone"])

    def test_reading_between_bands_raises(self) -> None:
        """dR/R0 between zone bands (e.g. 0.1, 0.22) or above zone 1 matches nothing."""
        for ratio in (0.1, 0.22, 0.3, -0.1):
            with self.assertRaises(ValueError):
                _ = strain_from_resistance(ratio)


if __name__ == "__main__":
    _ = unittest.main()
