"""Research-based tests for hydrogfn.domain_2 (parameters 2.1-2.2)."""

import math
import unittest

from hydrogfn import Status
from hydrogfn.domain_2 import core_temperature_2_2, glucose_2_1

_GM = 120.0
_VGS = 0.4
_K = 0.185


def _glucose(mmol_l: float):
    """Run glucose_2_1 on a reading from the forward GFET equation."""
    ids = _GM * _VGS * (1.0 - math.exp(-_K * mmol_l))
    return glucose_2_1(ids)


def _temp(celsius: float):
    """Run core_temperature_2_2 with r_t=1, a=1/T, b=c=0 so ln terms vanish."""
    return core_temperature_2_2(1.0, a=1.0 / (celsius + 273.15), b=0.0, c=0.0)


class TestDomain2Research(unittest.TestCase):
    def test_glucose_conversion_factor(self) -> None:
        """1 mmol/L = 18.016 mg/dL (https://calculover.com/health-fitness/clinical/mmol-mgdl-glucose/)."""
        res = _glucose(5.0)
        ratio = res["glucose_mg_dl"] / res["glucose_mmol_l"]
        self.assertLess(abs(ratio - 18.016) / 18.016, 0.005)

    def test_glucose_5_5_nominal(self) -> None:
        """5.5 mM is normal, above 3.9 (https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic)."""
        self.assertEqual(_glucose(5.5)["status"], Status.NOMINAL)

    def test_glucose_3_7_not_nominal(self) -> None:
        """Level 1 hypoglycemia < 70 mg/dL = 3.9 mM (unboundmedicine 5-Minute Clinical Consult)."""
        self.assertNotEqual(_glucose(3.7)["status"], Status.NOMINAL)

    def test_glucose_2_9_critical(self) -> None:
        """Level 2 hypoglycemia < 54 mg/dL = 3.0 mM (unboundmedicine 5-Minute Clinical Consult)."""
        self.assertEqual(_glucose(2.9)["status"], Status.CRITICAL)

    def test_glucose_3_95_nominal(self) -> None:
        """3.95 mM (~71 mg/dL) is not hypoglycemic (unboundmedicine 5-Minute Clinical Consult)."""
        self.assertEqual(_glucose(3.95)["status"], Status.NOMINAL)

    def test_ntc_10k_reads_25c(self) -> None:
        """TI generic 10 kOhm NTC Steinhart-Hart set: 25 C at 10 kOhm (https://education.ti.com/html/webhelp/EG_Innovator/EN/content/eg_innovsys/m_hub-comm/calibrate/temp_i__c1c2c3r1.HTML)."""
        res = core_temperature_2_2(10000.0)
        self.assertAlmostEqual(res["temperature_c"], 25.0, delta=0.05)

    def test_ntc_temperature_decreases_with_resistance(self) -> None:
        """NTC thermistor: resistance falls as temperature rises (TI Steinhart-Hart page)."""
        t = [
            core_temperature_2_2(r)["temperature_k"] for r in (5000.0, 10000.0, 20000.0)
        ]
        self.assertGreater(t[0], t[1])
        self.assertGreater(t[1], t[2])

    def test_temp_37_nominal(self) -> None:
        """Normal 36.5-37.5 C (https://ncbi.nlm.nih.gov/books/NBK507838/)."""
        self.assertEqual(_temp(37.0)["status"], Status.NOMINAL)

    def test_temp_38_5_warning(self) -> None:
        """Fever >= 38.0 C (https://healthanswers.pfizer.com/support/self-care/about-body-temperature)."""
        self.assertEqual(_temp(38.5)["status"], Status.WARNING)

    def test_temp_34_5_not_nominal(self) -> None:
        """Hypothermia < 35 C (https://ncbi.nlm.nih.gov/books/NBK507838/)."""
        self.assertNotEqual(_temp(34.5)["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code returns WARNING at 37.8 C vs fever threshold >= 38.0 C (https://healthanswers.pfizer.com/support/self-care/about-body-temperature)
    @unittest.expectedFailure
    def test_temp_37_8_not_warning(self) -> None:
        """37.8 C is below the 38.0 C fever threshold (Pfizer body temperature page)."""
        self.assertNotEqual(_temp(37.8)["status"], Status.WARNING)


if __name__ == "__main__":
    _ = unittest.main()
