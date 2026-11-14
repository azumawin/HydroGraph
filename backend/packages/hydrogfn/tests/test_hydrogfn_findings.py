"""Research-based tests for hydrogfn.findings (expected values from published sources)."""

import unittest

from hydrogfn import findings
from hydrogfn.shared import Status


def _sleep(hours: float) -> findings.SleepResult:
    return findings.sleep_deficiency_5(
        hours,
        90.0,
        2000.0,
        [],
        min_sleep_efficiency_pct=85.0,
        min_light_exposure_lux=1000.0,
        max_pvt_lapses=2,
    )


def _hypoxia(spo2: float, ppco2: float) -> findings.HypoxiaResult:
    return findings.hypoxia_co2_4(
        spo2,
        14.0,
        ppco2,
        False,
        max_respiratory_rate_bpm=20.0,
        max_ppco2_mmhg=3.0,
    )


def _energy(mmol: float) -> findings.EnergyBalanceResult:
    return findings.negative_energy_balance_7(
        0.0, mmol, False, min_body_mass_slope_kg_week=-0.5
    )


def _bone(litres: float) -> findings.BoneResult:
    return findings.bone_demineralization_8(0.0, litres, True, max_ntx_change_pct=20.0)


def _rad(cum: float, rate: float, spe: bool) -> findings.RadiationResult:
    return findings.radiation_exposure_10(cum, rate, spe, max_dose_rate_usv_h=50.0)


class TestHydrogfnFindings(unittest.TestCase):
    # 1 Orthostatic
    def test_orthostatic_normal_response_nominal(self) -> None:
        """Source: normal shock index 0.5-0.7, Shock index https://pmc.ncbi.nlm.nih.gov/articles/PMC6698590"""
        r = findings.orthostatic_intolerance_1(120.0, 115.0, 70.0, 80.0)
        self.assertEqual(r["status"], Status.NOMINAL)

    def test_orthostatic_sbp_drop_20_is_warning(self) -> None:
        """Source: OH = SBP drop >= 20 mmHg, Freeman 2011 via Merck https://www.merckmanuals.com/professional/cardiovascular-disorders/symptoms-of-cardiovascular-disorders/orthostatic-hypotension"""
        r = findings.orthostatic_intolerance_1(120.0, 100.0, 70.0, 70.0)
        self.assertEqual(r["status"], Status.WARNING)

    def test_orthostatic_hr_rise_30_is_warning(self) -> None:
        """Source: POTS HR rise >= 30 bpm, Freeman 2011 via Merck https://www.merckmanuals.com/professional/cardiovascular-disorders/symptoms-of-cardiovascular-disorders/orthostatic-hypotension"""
        r = findings.orthostatic_intolerance_1(120.0, 120.0, 60.0, 90.0)
        self.assertEqual(r["status"], Status.WARNING)

    def test_orthostatic_shock_index_above_0_9_is_warning(self) -> None:
        """Source: SI > 0.9 associated with occult shock, Shock index https://pmc.ncbi.nlm.nih.gov/articles/PMC6698590"""
        r = findings.orthostatic_intolerance_1(118.0, 115.0, 85.0, 110.0)
        self.assertEqual(r["status"], Status.WARNING)

    def test_orthostatic_shock_index_value(self) -> None:
        """Source: SI = HR/SBP, 80/115 ~ 0.70, Shock index https://pmc.ncbi.nlm.nih.gov/articles/PMC6698590"""
        r = findings.orthostatic_intolerance_1(120.0, 115.0, 70.0, 80.0)
        self.assertAlmostEqual(r["shock_index"], 0.70, delta=0.01)

    # 2 Dehydration
    def test_dehydration_small_loss_nominal(self) -> None:
        """Source: BML < 2 % and USG < 1.020 euhydrated, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2(99.0, 100.0, 1.010)
        self.assertEqual(r["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code warns only when mass loss > 2 % (98 kg gives NOMINAL) vs research BML >= 2 % is hypohydration (Munoz, PMC9214901)
    @unittest.expectedFailure
    def test_dehydration_bml_exactly_2pct_warning(self) -> None:
        """Source: Munoz BML >= 2 % hypohydration, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2(98.0, 100.0, 1.010)
        self.assertEqual(r["status"], Status.WARNING)

    # RESEARCH MISMATCH: code warns only when USG > 1.020 (1.020 gives NOMINAL) vs research USG >= 1.020 is hypohydration (PMC4912946)
    @unittest.expectedFailure
    def test_dehydration_usg_exactly_1020_warning(self) -> None:
        """Source: euhydration USG < 1.020, so >= 1.020 hypohydrated, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2(100.0, 100.0, 1.020)
        self.assertEqual(r["status"], Status.WARNING)

    def test_dehydration_usg_1030_warning(self) -> None:
        """Source: USG >= 1.020 hypohydration, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2(100.0, 100.0, 1.030)
        self.assertEqual(r["status"], Status.WARNING)

    # 3 Infection
    def test_infection_low_scores_nominal(self) -> None:
        """Source: NEWS2 < 5 no urgent trigger, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        r = findings.acute_infection_3(4, 1, False)
        self.assertEqual(r["status"], Status.NOMINAL)

    def test_infection_news2_5_warning(self) -> None:
        """Source: NEWS2 >= 5 urgent response, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        r = findings.acute_infection_3(5, 0, False)
        self.assertEqual(r["status"], Status.WARNING)

    def test_infection_news2_7_critical(self) -> None:
        """Source: NEWS2 >= 7 emergency response, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        r5 = findings.acute_infection_3(5, 0, False)
        r7 = findings.acute_infection_3(7, 0, False)
        self.assertEqual(r7["status"], Status.CRITICAL)
        self.assertNotEqual(r7["status"], r5["status"])

    def test_infection_qsofa_2_not_nominal(self) -> None:
        """Source: qSOFA >= 2 high risk, qSOFA https://www.mdcalc.com/qsofa-quick-sofa-score-sepsis"""
        r = findings.acute_infection_3(0, 2, False)
        self.assertNotEqual(r["status"], Status.NOMINAL)

    # 4 Hypoxia / CO2
    def test_hypoxia_normal_nominal(self) -> None:
        """Source: SpO2 94-98 %, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template; ppCO2 limit 3 mmHg, NASA https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf"""
        self.assertEqual(_hypoxia(97.0, 2.0)["status"], Status.NOMINAL)

    def test_hypoxia_spo2_93_warning(self) -> None:
        """Source: target SpO2 94-98 %, so 93 is low, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template"""
        self.assertEqual(_hypoxia(93.0, 2.0)["status"], Status.WARNING)

    def test_hypoxia_spo2_94_nominal(self) -> None:
        """Source: target SpO2 94-98 %, 94 is in range, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template"""
        self.assertEqual(_hypoxia(94.0, 2.0)["status"], Status.NOMINAL)

    def test_hypoxia_ppco2_above_limit_warning(self) -> None:
        """Source: ppCO2 1-h limit 3 mmHg, NASA https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf"""
        self.assertEqual(_hypoxia(97.0, 3.5)["status"], Status.WARNING)

    # 5 Sleep
    def test_sleep_pvt_lapse_threshold(self) -> None:
        """Source: PVT lapse = RT > 500 ms, Basner 2011 PVT https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786"""
        r = findings.sleep_deficiency_5(
            8.0,
            90.0,
            2000.0,
            [500.0, 501.0, 300.0],
            min_sleep_efficiency_pct=85.0,
            min_light_exposure_lux=1000.0,
            max_pvt_lapses=2,
        )
        self.assertEqual(r["pvt_lapses"], 1)

    def test_sleep_6h_warning(self) -> None:
        """Source: <= 6 h inadequate, AASM https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/"""
        self.assertEqual(_sleep(6.0)["status"], Status.WARNING)

    # RESEARCH MISMATCH: code warns when sleep <= 7.5 h (7.2 h gives WARNING) vs research adults need >= 7 h (AASM/SRS)
    @unittest.expectedFailure
    def test_sleep_7_2h_nominal(self) -> None:
        """Source: adults need >= 7 h, AASM https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/"""
        self.assertEqual(_sleep(7.2)["status"], Status.NOMINAL)

    # 6 Behavioral
    def test_behavioral_pvt_lapses_counted(self) -> None:
        """Source: PVT lapse = RT > 500 ms, Basner 2011 PVT https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786"""
        r = findings.behavioral_health_decline_6(
            0,
            0,
            [450.0, 520.0, 700.0],
            0.0,
            False,
            min_phq9_score=10,
            min_gad7_score=10,
            max_pvt_lapses=5,
            max_sleep_debt_hours=10.0,
        )
        self.assertEqual(r["pvt_lapses"], 2)
        self.assertEqual(r["status"], Status.NOMINAL)

    # 7 Energy balance
    def test_energy_normal_glucose_nominal(self) -> None:
        """Source: hypoglycemia < 70 mg/dL (3.9 mmol/L), 5-Minute Clinical Consult https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic"""
        self.assertEqual(_energy(5.0)["status"], Status.NOMINAL)

    def test_energy_low_glucose_warning(self) -> None:
        """Source: level 1 hypoglycemia < 70 mg/dL, 5-Minute Clinical Consult https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic"""
        self.assertEqual(_energy(3.8)["status"], Status.WARNING)

    def test_energy_glucose_conversion(self) -> None:
        """Source: mg/dL = mmol/L x 18.016, 5-Minute Clinical Consult https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic"""
        r = _energy(5.0)
        self.assertAlmostEqual(r["glucose_mg_dl"], 5.0 * 18.016, delta=0.005 * 90.08)

    # 8 Bone / renal
    def test_bone_3l_urine_nominal(self) -> None:
        """Source: urine volume >= 2.5 L/day, AUA https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline"""
        self.assertEqual(_bone(3.0)["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code warns only below 2.0 L/day (2.2 L gives NOMINAL) vs AUA urine volume target >= 2.5 L/day (AUA kidney stones guideline)
    @unittest.expectedFailure
    def test_bone_2_2l_urine_warning(self) -> None:
        """Source: below AUA 2.5 L/day target, AUA https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline"""
        self.assertEqual(_bone(2.2)["status"], Status.WARNING)

    def test_bone_1_5l_urine_warning(self) -> None:
        """Source: below AUA 2.5 L/day target, AUA https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline"""
        self.assertEqual(_bone(1.5)["status"], Status.WARNING)

    # 9 SANS (no research threshold; caller cutoff only)
    def test_sans_index_above_cutoff_not_nominal(self) -> None:
        """Source: none (caller-supplied cutoff); index above cutoff flags."""
        r = findings.sans_fluid_shift_9(2.0, max_fluid_shift_index=1.0)
        self.assertNotEqual(r["status"], Status.NOMINAL)

    # 10 Radiation
    def test_radiation_below_limits_nominal(self) -> None:
        """Source: career limit 600 mSv, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        self.assertEqual(_rad(300.0, 5.0, False)["status"], Status.NOMINAL)

    def test_radiation_spe_critical_with_shelter(self) -> None:
        """Source: SPE limit with sheltering countermeasure, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        r = _rad(300.0, 5.0, True)
        self.assertEqual(r["status"], Status.CRITICAL)
        self.assertIn("shelter", r["action"].lower())

    def test_radiation_cumulative_601_not_nominal(self) -> None:
        """Source: career effective dose limit 600 mSv, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        self.assertNotEqual(_rad(601.0, 5.0, False)["status"], Status.NOMINAL)

    # RESEARCH MISMATCH: code sends crew to shelter at 601 mSv cumulative vs 600 mSv is a career limit; sheltering is the SPE countermeasure (https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf)
    @unittest.expectedFailure
    def test_radiation_career_dose_no_shelter(self) -> None:
        """Source: 600 mSv career limit vs SPE sheltering, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        self.assertNotIn("shelter", _rad(601.0, 5.0, False)["action"].lower())


if __name__ == "__main__":
    _ = unittest.main()
