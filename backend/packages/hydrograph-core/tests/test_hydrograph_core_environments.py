"""Invariants of the mission environment catalog."""

import unittest

from hydrograph_core import ENVIRONMENTS
from hydrograph_core.environments import EnvironmentInfo


class TestEnvironments(unittest.TestCase):
    def test_covers_the_four_mvp_environments(self) -> None:
        self.assertEqual(
            list(ENVIRONMENTS),
            ["iss_leo", "lunar_surface", "mars_transit", "mars_surface"],
        )

    def test_every_entry_is_complete(self) -> None:
        for env in ENVIRONMENTS.values():
            self.assertEqual(env.keys(), EnvironmentInfo.__annotations__.keys())

    def test_values_are_physically_sane(self) -> None:
        for name, env in ENVIRONMENTS.items():
            with self.subTest(environment=name):
                self.assertGreaterEqual(env["gravity_g"], 0.0)
                self.assertLess(env["gravity_g"], 1.0)
                self.assertGreater(env["comm_delay_rt_s"], 0.0)
                self.assertGreater(env["baseline_dose_rate_usv_h"], 0.0)
                self.assertGreater(env["day_length_h"], 0.0)

    def test_gravity_and_delay_cover_distinct_points(self) -> None:
        """Four environments, no redundancy: each is a distinct (g, delay) pair."""
        axes = {(e["gravity_g"], e["comm_delay_rt_s"]) for e in ENVIRONMENTS.values()}
        self.assertEqual(len(axes), len(ENVIRONMENTS))
