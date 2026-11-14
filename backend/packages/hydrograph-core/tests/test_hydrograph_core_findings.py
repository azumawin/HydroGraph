"""Research-based tests for hydrograph_core.findings (expected values from published sources)."""

import unittest

from hydrograph_core import findings


def _ortho(
    sbp: tuple[float, float],
    dbp: tuple[float, float],
    hr: tuple[float, float],
    ctni: float | None = None,
) -> findings.OrthostaticResult:
    """(supine, standing) pairs for SBP, DBP and HR."""
    return findings.orthostatic_intolerance_1_1(*sbp, *dbp, *hr, ctni)


def _infection(
    news2: int, max_param: int = 0, temp: float = 37.0, il6: float = 1.0
) -> findings.InfectionResult:
    return findings.acute_infection_3_1(news2, max_param, temp, il6, False, False)


def _sleep(hours: float, cfe: float = 0.5) -> findings.SleepResult:
    return findings.sleep_deficiency_4_1(hours, [], cfe, max_pvt_lapses=2)


def _hypoxia(spo2: float, ppco2: float) -> findings.HypoxiaResult:
    return findings.hypoxia_co2_2_2(spo2, False, ppco2, False)


def _energy(mmol: float) -> findings.EnergyBalanceResult:
    return findings.negative_energy_balance_2_3(0.0, mmol, 1.0)


def _bone(litres: float) -> findings.BoneResult:
    return findings.bone_demineralization_1_2(0.0, litres)


def _rad(cum: float, rate: float, spe: bool) -> findings.RadiationResult:
    return findings.radiation_exposure_3_2(cum, rate, spe)


class TestHydrogfnFindings(unittest.TestCase):
    # 1 Orthostatic
    def test_orthostatic_normal_response_nominal(self) -> None:
        """Source: normal shock index 0.5-0.7, Shock index https://pmc.ncbi.nlm.nih.gov/articles/PMC6698590"""
        r = _ortho((120.0, 115.0), (80.0, 78.0), (70.0, 80.0))
        self.assertEqual(r["status"], "nominal")

    def test_orthostatic_sbp_drop_20_is_warning(self) -> None:
        """Source: OH = SBP drop >= 20 mmHg, Freeman 2011 via Merck https://www.merckmanuals.com/professional/cardiovascular-disorders/symptoms-of-cardiovascular-disorders/orthostatic-hypotension"""
        r = _ortho((120.0, 100.0), (80.0, 78.0), (70.0, 70.0))
        self.assertEqual(r["status"], "warning")

    def test_orthostatic_hr_rise_30_is_warning(self) -> None:
        """Source: POTS HR rise >= 30 bpm, Freeman 2011 via Merck https://www.merckmanuals.com/professional/cardiovascular-disorders/symptoms-of-cardiovascular-disorders/orthostatic-hypotension"""
        r = _ortho((120.0, 120.0), (80.0, 78.0), (60.0, 90.0))
        self.assertEqual(r["status"], "warning")

    def test_orthostatic_shock_index_above_0_9_is_warning(self) -> None:
        """Source: SI > 0.9 associated with occult shock, Shock index https://pmc.ncbi.nlm.nih.gov/articles/PMC6698590"""
        r = _ortho((118.0, 115.0), (80.0, 78.0), (85.0, 110.0))
        self.assertEqual(r["status"], "warning")

    def test_orthostatic_shock_index_value(self) -> None:
        """Source: SI = HR/SBP, 80/115 ~ 0.70, Shock index https://pmc.ncbi.nlm.nih.gov/articles/PMC6698590"""
        r = _ortho((120.0, 115.0), (80.0, 78.0), (70.0, 80.0))
        self.assertAlmostEqual(r["shock_index"], 0.70, delta=0.01)

    def test_orthostatic_dbp_drop_10_is_warning(self) -> None:
        """Source: OH = SBP drop >= 20 or DBP drop >= 10 mmHg within 3 min, Freeman 2011 via Merck https://www.merckmanuals.com/professional/cardiovascular-disorders/symptoms-of-cardiovascular-disorders/orthostatic-hypotension"""
        r = _ortho((120.0, 115.0), (80.0, 70.0), (70.0, 80.0))
        self.assertEqual(r["status"], "warning")

    def test_orthostatic_troponin_above_0_04_is_critical(self) -> None:
        """Source: master plan p.2, event-triggered hs-cTnI > 0.04 ng/mL critical."""
        r = _ortho((120.0, 115.0), (80.0, 78.0), (70.0, 80.0), 0.05)
        self.assertEqual(r["status"], "critical")
        self.assertIn("restrict EVA", r["action"])

    # 2 Dehydration
    def test_dehydration_small_loss_nominal(self) -> None:
        """Source: BML < 2 % and USG < 1.020 euhydrated, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2_1(99.0, 100.0, 1.010)
        self.assertIs(r["status"], False)

    # RESEARCH MISMATCH: code warns only when mass loss > 2 % (98 kg gives NOMINAL) vs research BML >= 2 % is hypohydration (Munoz, PMC9214901)
    @unittest.expectedFailure
    def test_dehydration_bml_exactly_2pct_warning(self) -> None:
        """Source: Munoz BML >= 2 % hypohydration, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2_1(98.0, 100.0, 1.010)
        self.assertIs(r["status"], True)

    # RESEARCH MISMATCH: code warns only when USG > 1.020 (1.020 gives NOMINAL) vs research USG >= 1.020 is hypohydration (PMC4912946)
    @unittest.expectedFailure
    def test_dehydration_usg_exactly_1020_warning(self) -> None:
        """Source: euhydration USG < 1.020, so >= 1.020 hypohydrated, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2_1(100.0, 100.0, 1.020)
        self.assertIs(r["status"], True)

    def test_dehydration_fluid_deficit(self) -> None:
        """Source: 1 kg acute body-mass loss ~ 1 L fluid, Sawka 2007 ACSM https://pubmed.ncbi.nlm.nih.gov/17277604/"""
        self.assertEqual(
            findings.dehydration_2_1(97.4, 100.0, 1.010)["fluid_deficit_ml"], 2600
        )

    def test_dehydration_usg_1030_warning(self) -> None:
        """Source: USG >= 1.020 hypohydration, https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901, https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946"""
        r = findings.dehydration_2_1(100.0, 100.0, 1.030)
        self.assertIs(r["status"], True)

    # 3 Infection
    def test_infection_low_scores_nominal(self) -> None:
        """Source: NEWS2 < 5 no urgent trigger, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        r = _infection(4)
        self.assertEqual(r["status"], "nominal")

    def test_infection_news2_5_warning(self) -> None:
        """Source: NEWS2 >= 5 urgent response, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        r = _infection(5)
        self.assertEqual(r["status"], "warning")

    def test_infection_news2_7_critical(self) -> None:
        """Source: NEWS2 >= 7 emergency response, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        r5 = _infection(5)
        r7 = _infection(7)
        self.assertEqual(r7["status"], "critical")
        self.assertNotEqual(r7["status"], r5["status"])

    def test_infection_single_vital_3_warning(self) -> None:
        """Source: a single NEWS2 parameter scoring 3 triggers urgent review, RCP NEWS2 https://www.rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf"""
        self.assertEqual(_infection(3, max_param=3)["status"], "warning")

    def test_infection_sirs_temperature(self) -> None:
        """Source: SIRS temperature > 38.0 or < 36.0 C, MDCalc SIRS https://www.mdcalc.com/calc/1096/sirs-sepsis-septic-shock-criteria"""
        self.assertEqual(_infection(0, temp=38.3)["status"], "warning")
        self.assertEqual(_infection(0, temp=35.8)["status"], "warning")
        self.assertEqual(_infection(0, temp=37.0)["status"], "nominal")

    def test_infection_il6_gated_after_ared(self) -> None:
        """Source: master plan p.3, IL-6 > 3.0 pg/mL warns only outside the 2-hr post-ARED window."""
        self.assertEqual(_infection(0, il6=4.0)["status"], "warning")
        r = findings.acute_infection_3_1(0, 0, 37.0, 4.0, True, False)
        self.assertEqual(r["status"], "nominal")

    # 4 Hypoxia / CO2
    def test_hypoxia_normal_nominal(self) -> None:
        """Source: SpO2 94-98 %, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template; ppCO2 limit 3 mmHg, NASA https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf"""
        self.assertEqual(_hypoxia(97.0, 2.0)["status"], "nominal")

    def test_hypoxia_spo2_93_warning(self) -> None:
        """Source: target SpO2 94-98 %, so 93 is low, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template"""
        self.assertEqual(_hypoxia(93.0, 2.0)["status"], "warning")

    def test_hypoxia_spo2_94_nominal(self) -> None:
        """Source: target SpO2 94-98 %, 94 is in range, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template"""
        self.assertEqual(_hypoxia(94.0, 2.0)["status"], "nominal")

    def test_hypoxia_spo2_below_90_critical(self) -> None:
        """Source: SpO2 < 90 % is hypoxemia, BTS https://www.brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-4-local-oxygen-policy-template"""
        self.assertEqual(_hypoxia(88.0, 2.0)["status"], "critical")

    def test_hypoxia_ppco2_above_limit_warning(self) -> None:
        """Source: ppCO2 1-h limit 3 mmHg, NASA https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf"""
        self.assertEqual(_hypoxia(97.0, 3.5)["status"], "warning")

    # 5 Sleep
    def test_sleep_pvt_lapse_threshold(self) -> None:
        """Source: PVT lapse = RT > 500 ms, Basner 2011 PVT https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786"""
        r = findings.sleep_deficiency_4_1(
            8.0, [500.0, 501.0, 300.0], 0.5, max_pvt_lapses=2
        )
        self.assertEqual(r["pvt_lapses"], 1)

    def test_sleep_cfe_bands(self) -> None:
        """Source: master plan p.3, CFE 0.70-1.20 warning, > 1.20 critical."""
        self.assertEqual(_sleep(8.0, 0.69)["status"], "nominal")
        self.assertEqual(_sleep(8.0, 0.70)["status"], "warning")
        self.assertEqual(_sleep(8.0, 1.21)["status"], "critical")

    def test_sleep_6h_warning(self) -> None:
        """Source: <= 6 h inadequate, AASM https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/"""
        self.assertEqual(_sleep(6.0)["status"], "warning")

    # RESEARCH MISMATCH: code warns when sleep <= 7.5 h (7.2 h gives WARNING) vs research adults need >= 7 h (AASM/SRS)
    @unittest.expectedFailure
    def test_sleep_7_2h_nominal(self) -> None:
        """Source: adults need >= 7 h, AASM https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/"""
        self.assertEqual(_sleep(7.2)["status"], "nominal")

    # 6 Behavioral
    def test_behavioral_pvt_lapses_counted(self) -> None:
        """Source: PVT lapse = RT > 500 ms, Basner 2011 PVT https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786"""
        r = findings.behavioral_health_decline_4_2(
            0,
            0,
            [450.0, 520.0, 700.0],
            0.0,
            False,
            10.0,
            max_pvt_lapses=5,
            max_sleep_debt_hours=10.0,
        )
        self.assertEqual(r["pvt_lapses"], 2)
        self.assertEqual(r["status"], "nominal")

    def test_behavioral_phq9_10_warning(self) -> None:
        """Source: PHQ-9 >= 10 moderate depression, Kroenke 2001 https://pmc.ncbi.nlm.nih.gov/articles/PMC1495268/"""
        r = findings.behavioral_health_decline_4_2(
            10, 0, [], 0.0, False, 10.0, max_pvt_lapses=5, max_sleep_debt_hours=10.0
        )
        self.assertEqual(r["status"], "warning")

    # 7 Energy balance
    def test_energy_normal_glucose_nominal(self) -> None:
        """Source: hypoglycemia < 70 mg/dL (3.9 mmol/L), 5-Minute Clinical Consult https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic"""
        self.assertIs(_energy(5.0)["status"], False)

    def test_energy_low_glucose_warning(self) -> None:
        """Source: level 1 hypoglycemia < 70 mg/dL, 5-Minute Clinical Consult https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic"""
        self.assertIs(_energy(3.8)["status"], True)

    def test_energy_level_2_hypoglycemia_named(self) -> None:
        """Source: level 2 hypoglycemia < 54 mg/dL (3.0 mmol/L), IHSG & ADA 2017 https://diabetesjournals.org/care/article/40/1/155/37135"""
        r = _energy(2.9)
        self.assertIs(r["status"], True)
        self.assertIn("Level 2 hypoglycemia < 54 mg/dL", r["triggers"])

    def test_energy_glucose_conversion(self) -> None:
        """Source: mg/dL = mmol/L x 18.016, 5-Minute Clinical Consult https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic"""
        r = _energy(5.0)
        self.assertAlmostEqual(r["glucose_mg_dl"], 5.0 * 18.016, delta=0.005 * 90.08)

    # 8 Bone / renal
    def test_bone_3l_urine_nominal(self) -> None:
        """Source: urine volume >= 2.5 L/day, AUA https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline"""
        self.assertIs(_bone(3.0)["status"], False)

    # RESEARCH MISMATCH: code warns only below 2.0 L/day (2.2 L gives NOMINAL) vs AUA urine volume target >= 2.5 L/day (AUA kidney stones guideline)
    @unittest.expectedFailure
    def test_bone_2_2l_urine_warning(self) -> None:
        """Source: below AUA 2.5 L/day target, AUA https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline"""
        self.assertIs(_bone(2.2)["status"], True)

    def test_bone_1_5l_urine_warning(self) -> None:
        """Source: below AUA 2.5 L/day target, AUA https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline"""
        self.assertIs(_bone(1.5)["status"], True)

    # 9 SANS
    def test_sans_jugular_distension_bands(self) -> None:
        """Source: master plan p.4, < 1.1 % nominal, 1.1-1.8 % warning, > 1.8 % critical (Roy et al., 2024)."""
        self.assertEqual(findings.sans_fluid_shift_1_3(1.0)["status"], "nominal")
        self.assertEqual(findings.sans_fluid_shift_1_3(1.1)["status"], "warning")
        self.assertEqual(findings.sans_fluid_shift_1_3(1.8)["status"], "warning")
        self.assertEqual(findings.sans_fluid_shift_1_3(1.9)["status"], "critical")

    # 10 Radiation
    def test_radiation_below_limits_nominal(self) -> None:
        """Source: career limit 600 mSv, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        self.assertEqual(_rad(300.0, 5.0, False)["status"], "nominal")

    def test_radiation_spe_critical_with_shelter(self) -> None:
        """Source: SPE limit with sheltering countermeasure, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        r = _rad(300.0, 5.0, True)
        self.assertEqual(r["status"], "critical")
        self.assertIn("shelter", r["action"].lower())

    def test_radiation_dose_rate_above_50_warning(self) -> None:
        """Source: master plan p.4, acute SPE dose-rate spike > 50 uSv/h warning."""
        self.assertEqual(_rad(300.0, 60.0, False)["status"], "warning")

    def test_radiation_cumulative_601_not_nominal(self) -> None:
        """Source: career effective dose limit 600 mSv, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        self.assertNotEqual(_rad(601.0, 5.0, False)["status"], "nominal")

    # RESEARCH MISMATCH: code sends crew to shelter at 601 mSv cumulative vs 600 mSv is a career limit; sheltering is the SPE countermeasure (https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf)
    @unittest.expectedFailure
    def test_radiation_career_dose_no_shelter(self) -> None:
        """Source: 600 mSv career limit vs SPE sheltering, NASA-STD-3001 https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"""
        self.assertNotIn("shelter", _rad(601.0, 5.0, False)["action"].lower())


if __name__ == "__main__":
    _ = unittest.main()
