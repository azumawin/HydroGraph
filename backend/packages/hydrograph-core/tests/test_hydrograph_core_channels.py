"""Tests for hydrograph_core.channels (cutoffs from the master plan, else NSA_hydrograph.md)."""

import unittest

from hydrograph_core.channels import CHANNELS, evaluate_reading
from hydrograph_core.shared import Status


class TestEvaluateReading(unittest.TestCase):
    def test_boundaries(self) -> None:
        cases = [
            ("heart_rate", 45, Status.UNSPECIFIED),
            ("heart_rate", 90, Status.NOMINAL),
            ("heart_rate", 95, Status.WARNING),
            ("bp_systolic", 118, Status.UNSPECIFIED),
            ("bp_diastolic", 76, Status.UNSPECIFIED),
            ("spo2", 94, Status.NOMINAL),
            ("spo2", 93.9, Status.WARNING),
            ("spo2", 89.9, Status.CRITICAL),
            ("core_temp", 38.0, Status.NOMINAL),
            ("core_temp", 38.1, Status.WARNING),
            ("core_temp", 35.9, Status.WARNING),
            ("glucose", 3.9, Status.NOMINAL),
            ("glucose", 3.8, Status.WARNING),
            ("glucose", 2.9, Status.CRITICAL),
            ("glucose", 7.1, Status.UNSPECIFIED),
            ("ppco2", 3.0, Status.NOMINAL),
            ("ppco2", 3.1, Status.WARNING),
            ("dose_rate", 50, Status.NOMINAL),
            ("dose_rate", 51, Status.WARNING),
            ("jugular_distension", 1.0, Status.NOMINAL),
            ("jugular_distension", 1.1, Status.WARNING),
            ("jugular_distension", 1.9, Status.CRITICAL),
        ]
        for channel, value, expected in cases:
            with self.subTest(channel=channel, value=value):
                self.assertIs(evaluate_reading(channel, value), expected)

    def test_every_channel_is_graded(self) -> None:
        for channel in CHANNELS:
            with self.subTest(channel=channel):
                self.assertIsInstance(evaluate_reading(channel, 1.0), Status)

    def test_unknown_channel_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unknown channel "heartrate"'):
            _ = evaluate_reading("heartrate", 72)
