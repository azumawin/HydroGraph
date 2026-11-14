# Spec problems

Fix first: replace the Debye term in `NSA_hydrograph.md:99` (Parameter 1.2). It is physically wrong at the spec's own default values.

This lists only problems in the two spec documents: `NSA_hydrograph.md` (the parameter spec) and `Tiered Master System Specification & Implementation Plan.pdf` (the master plan, cited by page). Problems in the code are tracked by the `RESEARCH MISMATCH` tests in `tests/`, not here.

Time estimates are for whoever owns the spec. "Edit" means changing a number or a line. "Decision" means someone has to choose a source or model first.

## 1. Wrong against research (fix first)

1. **Parameter 1.2: Debye term** (`NSA_hydrograph.md:99`). About 1 hour (decision).
   - The spec uses `ΔVt = qN_b/(ε_r ε_0) · δ · (1 − δ/(2λ_D))`.
   - Research: the potential of charge bound farther from the graphene than the Debye length decays as `exp(−d/λ_D)`, so the shift falls toward zero as δ grows.
   - With the spec defaults (δ = 3.5 nm, λ_D = 1 nm), the bracket is −0.75. The model predicts a reversed signal that grows with distance.
   - Fix: use an exponential screening factor, for example `· exp(−δ/λ_D)`, and re-derive the 1.2 mV flag.
   - Sources: [arXiv 1708.08958](https://arxiv.org/pdf/1708.08958), [arXiv 2208.10742](https://arxiv.org/pdf/2208.10742), [arXiv 2402.02707 (λ_D ≈ 1 nm in sweat/saliva)](https://arxiv.org/pdf/2402.02707)
2. **Parameter 4.1: cortisol thresholds** (`NSA_hydrograph.md:337-341`; master plan p.3). About 1 hour (decision).
   - The parameter spec says NOMINAL < 15 nM and CRITICAL > 30 nM. The master plan says WARNING from 22.4 nM.
   - Research: healthy morning salivary cortisol is about 28–75 nM, and sweat cortisol about 22–389 nM. A normal morning reading would be CRITICAL.
   - Fix: say which fluid the sensor measures, take that fluid's reference range, and decide whether the thresholds depend on time of day.
   - Sources: [PMC6787562 (CortiWatch)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6787562/), [Sci Rep s41598-017-13684-7](https://link.springer.com/article/10.1038/s41598-017-13684-7)
3. **Parameter 3.1: NTx thresholds, units and decay term** (`NSA_hydrograph.md:248`, `:265-269`). About 1 hour (decision).
   - The spec says WARNING from 10 nM. Research: the healthy serum NTx range is about 5.4–24.2 nM BCE (males) and 6.2–19.0 (females).
   - The spec doesn't say whether the value is serum or urine, or how it is normalised. Urinary NTx is reported per mmol creatinine.
   - The `e^(−β·t_MET)` term makes the response fade over the mission. In spaceflight, NTx rises and stays high (median 23 → 33–38 nmol/mmol creatinine).
   - Sources: [Northwell NTx reference range](https://nslijlab.testcatalog.org/show/NTX), [PMC8862023 (spaceflight NTx)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8862023/table/T2)

## 2. Thresholds off from clinical guidelines

All five are a few minutes each: change the number.

1. **Parameter 1.3: heart rate** (`NSA_hydrograph.md:158-160`).
   - The spec has nominal HR 50–90 bpm and WARNING at 100–120 bpm, which leaves 90–100 undefined.
   - Research: normal resting HR is 60–100 bpm, and tachycardia is > 100.
   - Fix: nominal 60–100, warning > 100. Decide whether 50–60 is acceptable for trained crew.
   - Sources: [UCSF Hospital Handbook](https://hospitalhandbook.ucsf.edu/node/2676), [OpenStax shock overview](https://openstax.org/books/medical-surgical-nursing/pages/23-1-shock-overview)
2. **Parameter 2.1: glucose** (`NSA_hydrograph.md:194-198`).
   - The spec has nominal 4.0–7.0 mM, WARNING 3.5–4.0 and CRITICAL < 3.5. The warning and nominal bands overlap at 4.0.
   - Research (ADA/EASD): level 1 hypoglycemia is < 3.9 mM (70 mg/dL) and level 2 is < 3.0 mM (54 mg/dL).
   - Fix: warning < 3.9, critical < 3.0. This also matches the master plan's own Tier 1 "< 70 mg/dL".
   - Source: [5-Minute Clinical Consult: Hypoglycemia](https://www.unboundmedicine.com/5minute/view/5-Minute-Clinical-Consult/116305/1.1/Hypoglycemia_Diabetic)
3. **Parameter 4.3: sleep hours** (`NSA_hydrograph.md:399-401`).
   - The spec requires more than 7.5 h for nominal. Research (AASM/SRS): adults need 7 or more hours, and 6 or fewer is inadequate.
   - Fix: nominal ≥ 7 h, warning ≤ 6 h.
   - Sources: [AASM](https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/), [PMC4434546](https://pmc.ncbi.nlm.nih.gov/articles/PMC4434546/)
4. **Finding 2: dehydration boundaries** (master plan p.2).
   - The plan says body-mass loss "> 2 %" and USG "> 1.020". Research: euhydration is USG < 1.020, and the field criterion is a body-mass loss of ≥ 2 %.
   - Fix: change both to `≥`.
   - Sources: [PMC9214901](https://pmc.ncbi.nlm.nih.gov/articles/PMC9214901), [PMC4912946](https://pmc.ncbi.nlm.nih.gov/articles/PMC4912946)
5. **Finding 8: urine volume** (master plan p.2).
   - The plan triggers below 2.0 L/day. The AUA guideline targets ≥ 2.5 L/day of urine for stone prevention, and the plan's own action card says "raise daily water target to 2.5 L".
   - Fix: trigger below 2.5 L/day.
   - Source: [AUA Kidney Stones guideline](https://www.auanet.org/guidelines/guidelines/kidney-stones-medical-mangement-guideline)

## 3. Missing or misapplied criteria

About 15 minutes each.

1. **Finding 10: career dose triggers a shelter alert** (master plan p.2, p.4).
   - The plan sends the crew to shelter when the cumulative dose passes 600 mSv. That is a lifetime career limit, not an acute hazard.
   - Sheltering is the countermeasure for solar particle events, which have a separate 250 mSv per-event limit.
   - Fix: give the career limit its own action, and keep shelter for SPE / dose rate.
   - Source: [NASA OCHMO radiation brief](https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf)
2. **Finding 1: no diastolic criterion** (master plan p.2).
   - The consensus definition of orthostatic hypotension is a systolic drop of ≥ 20 mmHg **or** a diastolic drop of ≥ 10 mmHg within 3 minutes. The plan only lists the systolic drop.
   - Fix: add ΔDBP ≥ 10 mmHg.
   - Source: [Merck Manual: Orthostatic hypotension](https://www.merckmanuals.com/professional/cardiovascular-disorders/symptoms-of-cardiovascular-disorders/orthostatic-hypotension)
3. **Finding 3: qSOFA used as a trigger on its own** (master plan p.2).
   - qSOFA ≥ 2 predicts poor outcome. Sepsis-3 says it should prompt a full SOFA assessment, not treatment by itself.
   - Fix: make qSOFA ≥ 2 a "review" flag, not a protocol trigger.
   - Source: [MDCalc qSOFA](https://www.mdcalc.com/qsofa-quick-sofa-score-sepsis)
4. **Parameter 2.2: no hypothermia protocol** (`NSA_hydrograph.md:231`).
   - The spec only defines hyperthermia (> 38.0 °C), even though its own pathology text names "severe hypothermia". Hypothermia is < 35 °C.
   - Fix: add a band below 35 °C with an action.
   - Sources: [NCBI body temperature](https://ncbi.nlm.nih.gov/books/NBK507838/), [Pfizer body temperature](https://healthanswers.pfizer.com/support/self-care/about-body-temperature)
5. **Finding 4: no ppCO2 limit** (master plan p.2).
   - The plan names ambient ppCO2 but gives no number. NASA-STD-3001 Vol 2 sets a 1-hour average limit of 3 mmHg, and headaches are reported from about 2.8 mmHg.
   - Fix: add 3 mmHg.
   - Source: [NASA OCHMO CO2 brief](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf)

## 4. No supporting source found

These need a citation or a different model. About 1–2 hours each (decision).

1. **Parameter 1.1: ICP from skin strain** (`NSA_hydrograph.md:57`). We found no validation for `ICP = k₁·ε + ICP_baseline`. The thresholds are fine: normal is 7–15 mmHg and intracranial hypertension is > 20 mmHg ([Intracranial pressure](https://wikiwand.com/EN/Intracranial_pressure), [Stroke manual](https://www.stroke-manual.com/?p=40197)).
2. **Parameter 4.3: SQI and mood index** (`NSA_hydrograph.md:394`). Neither formula matches a validated instrument we could find.
3. **Parameter 4.2: CFE cutoffs 0.70 / 1.20** (`NSA_hydrograph.md:371`). Theta/alpha rising with fatigue is supported, but we found no source for these numbers. Theta and alpha both rise with fatigue, so the ratio may not separate fatigue from high workload ([arXiv 2202.12937](https://arxiv.org/pdf/2202.12937), [PMC7820710](https://pmc.ncbi.nlm.nih.gov/articles/PMC7820710)).
4. **Parameter 1.2: cTnI cutoff depends on the assay** (`NSA_hydrograph.md:120-124`). 0.04 ng/mL is a common manufacturer limit, but high-sensitivity assays have 99th-percentile limits of about 5–53 ng/L, and they differ by sex. The spec should name the assay ([BMJ 2019;364:l729](https://www.bmj.com/content/364/bmj.l729.full), [PMC6559611](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6559611/)).
5. **Parameter 5.1: no weights, IL-6 cutoff too low** (`NSA_hydrograph.md:417-425`). The spec never gives w1 or w2, so the code makes them required arguments. Its nominal IL-6 < 3.0 pg/mL flags normal people: healthy-adult IL-6 pools at about 5.2 pg/mL, the Labcorp 95th percentile is 7 pg/mL, and the spec's own example payload (4.2 pg/mL) would be WARNING. TNF-α ranges depend heavily on the assay (Labcorp: 0.0–2.2 pg/mL). The spec should give the weights and name the assay ([Said et al. 2021](https://zendy.io/title/10.1002/jmv.26654), [Labcorp IL-6](https://www.labcorp.com/test-menu/29791/interleukin-6-serum), [Labcorp TNF-α](https://www.labcorp.com/tests/140673/tumor-necrosis-factor-a)).

## 5. The two documents contradict themselves or each other

About 5–15 minutes each.

1. **Cortisol warning threshold:** 15.0 nM in `NSA_hydrograph.md:339`, but 22.4 nM in the master plan (p.3).
2. **Glucose:** the Tier 2 critical threshold is < 3.5 mM (`NSA_hydrograph.md:198`), while Tier 1 hypoglycemia is < 70 mg/dL ≈ 3.9 mM (master plan p.2).
3. **Urine:** Finding 8 triggers below 2.0 L/day, but its own action card sets a 2.5 L target (master plan p.2).
4. **Steinhart–Hart units:** `NSA_hydrograph.md:224-225` calls the coefficients "unitless", then labels C as K⁻³. Every term must be K⁻¹ for `1/T` to balance.
5. **Gauge factor** (master plan p.3, p.6):
   - Ranges B and C give a span of values (233.48–389.58 and 74.34–114.86) instead of one value.
   - The JSON example doesn't add up: 1.42 % strain with ΔR/R₀ = 0.145 implies GF ≈ 10, not the 312.4 it shows.

Next: open `NSA_hydrograph.md` at line 99 and decide on the screening model for 1.2.
