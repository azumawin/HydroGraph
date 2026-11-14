"""Tests for hydrogfn.polling (expected values from master plan p.6, section 4)."""

import unittest

from hydrogfn.polling import Mode, UserState, alert_allowed, poll_interval


class TestPollInterval(unittest.TestCase):
    """Interval lookup per channel and state."""

    def test_radiation_continuous_in_every_state(self) -> None:
        """Radiation & SPE Safety: continuous 1 Hz, independent of state."""
        for state in UserState:
            result = poll_interval("dose_rate", state)
            self.assertEqual(result["mode"], Mode.CONTINUOUS)
            self.assertEqual(result["max_interval_s"], 1.0)

    def test_heart_rate_active_range(self) -> None:
        """Cardiovascular, active: every 15-30 s."""
        result = poll_interval("heart_rate", UserState.ACTIVE)
        self.assertEqual(
            (result["min_interval_s"], result["max_interval_s"]), (15.0, 30.0)
        )

    def test_cortisol_sleeping_hourly(self) -> None:
        """Metabolic & GFET, sleeping: every 60 min."""
        self.assertEqual(
            poll_interval("cortisol", UserState.SLEEPING)["min_interval_s"], 3600.0
        )

    def test_kinematics_suspended_in_sleep(self) -> None:
        """Hydrogel Strain & Sweat, sleeping: suspended."""
        result = poll_interval("kinematics", UserState.SLEEPING)
        self.assertEqual(result["mode"], Mode.SUSPENDED)
        self.assertIsNone(result["min_interval_s"])

    def test_sleep_exceptions_unspecified(self) -> None:
        """Passive SANS tracking, EEG and PVT have no sleep rate in the plan."""
        for channel in ("cephalic_fluid_index", "eeg_theta_alpha_ratio", "pvt_rt"):
            result = poll_interval(channel, UserState.SLEEPING)
            self.assertEqual(result["mode"], Mode.UNSPECIFIED)

    def test_actigraphy_continuous_in_sleep(self) -> None:
        """Neuro-Cognitive & Sleep, sleeping: "Continuous Actigraphy", no rate given."""
        result = poll_interval("actigraphy", UserState.SLEEPING)
        self.assertEqual(result["mode"], Mode.CONTINUOUS)
        self.assertIsNone(result["min_interval_s"])

    def test_il6_is_a_gfet_channel(self) -> None:
        """GFET Molecular Markers now lists il6, every 30 min while resting."""
        self.assertEqual(
            poll_interval("il6", UserState.RESTING)["min_interval_s"], 1800.0
        )

    def test_unknown_channel_raises(self) -> None:
        """SpO2 is a Tier 1 vital but not in the polling table."""
        with self.assertRaises(ValueError):
            _ = poll_interval("spo2", UserState.ACTIVE)


class TestAlertAllowed(unittest.TestCase):
    """Sleep-protection lock and safety override."""

    def test_radiation_overrides_sleep(self) -> None:
        """Safety channels alert in sleep even when only warning."""
        self.assertTrue(alert_allowed("dose_rate", UserState.SLEEPING, "warning"))

    def test_sleep_locks_non_critical(self) -> None:
        """Sleeping: warning is locked out, critical gets through."""
        self.assertFalse(alert_allowed("sweat_rate", UserState.SLEEPING, "warning"))
        self.assertTrue(alert_allowed("heart_rate", UserState.SLEEPING, "critical"))

    def test_awake_warning_alerts(self) -> None:
        """Awake: any non-nominal status alerts."""
        self.assertTrue(alert_allowed("glucose", UserState.RESTING, "warning"))

    def test_nominal_never_alerts(self) -> None:
        """Nominal readings raise no alert."""
        self.assertFalse(alert_allowed("spe_flag", UserState.ACTIVE, "nominal"))


if __name__ == "__main__":
    _ = unittest.main()
