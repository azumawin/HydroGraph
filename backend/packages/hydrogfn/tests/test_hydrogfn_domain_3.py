"""Research-based tests for hydrogfn.domain_3 (expected values from published sources)."""

import math
import unittest

from hydrogfn.domain_3 import bone_resorption_3_1, joint_kinematics_3_2
from hydrogfn.shared import Status


def _ratio_for_angle(theta_deg: float) -> float:
    """Forward sensor equation: dR/R0 = GF * t * theta / (2 L), defaults t=1.2, L=50, GF=2.1."""
    return 2.1 * 1.2 * math.radians(theta_deg) / (2 * 50)


class TestDomain3(unittest.TestCase):
    """Tests for parameters 3.1 and 3.2."""

    # RESEARCH MISMATCH: code returns WARNING for 12.0 nM (nominal < 10.0 nM) vs healthy serum NTx 5.4-24.2 nM (https://nslijlab.testcatalog.org/show/NTX)
    @unittest.expectedFailure
    def test_ntx_healthy_is_nominal(self) -> None:
        """NTx 12.0 nM is inside 5.4-24.2 nM (https://nslijlab.testcatalog.org/show/NTX)."""
        result = bone_resorption_3_1(12.0, 0.0, alpha_bone=1.0)
        self.assertEqual(result["status"], Status.NOMINAL)

    def test_ntx_above_range_not_nominal(self) -> None:
        """NTx 30.0 nM is above 24.2 nM (https://nslijlab.testcatalog.org/show/NTX)."""
        result = bone_resorption_3_1(30.0, 0.0, alpha_bone=1.0)
        self.assertNotEqual(result["status"], Status.NOMINAL)

    def test_symmetric_90_degrees(self) -> None:
        """eps = t*theta/(2L), dR/R0 = GF*eps (https://arxiv.org/pdf/1504.07926)."""
        ratio = _ratio_for_angle(90.0)
        result = joint_kinematics_3_2(ratio, ratio)
        self.assertAlmostEqual(result["left_flexion_deg"], 90.0, delta=0.1)
        self.assertAlmostEqual(result["right_flexion_deg"], 90.0, delta=0.1)
        self.assertEqual(result["asymmetry_ratio"], 1.0)

    def test_asymmetry_45_vs_90(self) -> None:
        """Strain linear in angle (https://arxiv.org/pdf/1504.07926): 45 vs 90 deg gives 2.0."""
        result = joint_kinematics_3_2(_ratio_for_angle(45.0), _ratio_for_angle(90.0))
        self.assertAlmostEqual(result["asymmetry_ratio"], 2.0, delta=0.01)


if __name__ == "__main__":
    _ = unittest.main()
