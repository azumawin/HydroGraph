# Suspected spec problems

Things that look wrong in the master plan (`Tiered Master System Specification & Implementation Plan.pdf`, the 10-page "Verified Edition", cited by page) but are not yet checked against research. Confirmed problems go in `mismatches.md` instead.

## Section 2: Tier 1 findings (p.2-4)

Found while writing `hydrograph_core/findings.py`.

1. **Some criteria still have no cutoff.**
   - Finding 5: the sleep duration is "anchored to flight baseline (ISS mean 6.09 hrs vs. 8.5 hrs scheduled)" but no number triggers. Code: the parameter spec's 4.3 cutoff (nominal needs > 7.5 h).
   - Findings 5 and 6: PVT lapse counts and sleep debt. Code: required keyword-only arguments.
   - Finding 4: "rising respiratory rate". Code: a `bool` evaluated upstream.
   - Finding 2: sweat rate and Na+ flux are baseline-relative trends with no cutoff. Code: not used.
2. **Level 2 hypoglycemia is not marked urgent.** Finding 7 lists Level 1 (< 70 mg/dL) and Level 2 (< 54 mg/dL) but gives one action card and no severity. Code: both are WARNING, the trigger names the level. Tier 2 glucose (2.1) makes Level 2 CRITICAL.
3. **Finding 10 mixes a warning with a shelter alert.** The dose-rate spike is "> 50 µSv/h warning", but the finding has a single action, "Move to shielded storm shelter zone immediately". Code: the SPE flag is CRITICAL, the dose rate and the career dose are WARNING; all use the shelter card.
4. **Finding 2's "calculated fluid deficit" isn't defined.** Code: 1 kg of acute body-mass loss = 1 L, returned as `fluid_deficit_ml`.

## Section 3A: hydrogel gauge factor (p.4-5)

Found while writing `hydrograph_core/gauge_factor.py`.

1. **The plan doesn't say how GF runs inside a zone.**
   - It gives only spans ("114.86 – 1180.75", "9.53 – 54.24", "0.56 – 0.94"), low value first.
   - "Ultra-high initial contact sensitivity" and the p.8 example (GF 153.2 at 0.08 mm, near the top of zone 1) put the high value at the low end.
   - Code: a power law between the end points. It gives 144.0 at 0.08 mm, not the example's 153.2; linear would give 351.7.
2. **Resistance falls as the strip stretches.**
   - In every zone GF drops faster than strain rises, so ΔR/R0 = GF·ε goes down with displacement: zone 1 0.2362 → 0.2297, zone 2 0.2170 → 0.1906, zone 3 0.0752 → 0.0566.
   - Zone 1 is almost flat: a 1 % error in ΔR/R0 (0.0023) moves the inverted displacement by about 0.03 mm, a third of the zone.
   - Upside: the three ΔR/R0 bands don't overlap, so a reading maps to at most one zone (the old draft's three-way ambiguity is gone).
3. **Gaps and the open top.**
   - Nothing is defined for 0.10-0.20 mm, 1.00-4.00 mm, or below 0.01 mm.
   - Zone 3 is "4.00 – 5.05+ mm" but no GF is given above 5.05 mm.
   - Code: `ValueError` for all of these.
4. **The plan's own strain formula can't reach zone 3.**
   - ε = t_film·θ / (2·L0) with t_film = 1.2 mm and L0 = 50 mm gives at most 3.77 % (ΔL 1.88 mm) at θ = 180°, which falls in the 1.00-4.00 mm gap.
   - Zone 3 (ε ≥ 8 %) is described as "Knee, Shoulder & Lumbar ARED Kinematics" but needs θ ≥ 382°.
5. **The parameter spec still uses GF = 2.1.** `NSA_hydrograph.md` uses 2.1 for the same carrageenan strip (Parameters 1.1 and 3.2). The plan puts the neck patch in zone 1 (GF 114.86-1180.75). Code: 1.1 and 3.2 keep 2.1; decide which GF they should use.

## Example JSON payload (p.8)

1. **Hydrogel block.** displacement 0.08 mm, strain 0.16 %, GF 153.2, ΔR/R0 0.2451.
   - Internally consistent (153.2 × 0.0016 = 0.2451, 0.08 / 50 = 0.16 %), but 153.2 isn't on any simple curve through the zone 1 end points (see 3A item 1).
2. **ICP.** `estimated_icp_mmHg` is 14.2. With k1 = 185.4 and baseline 9.5, the strain 0.16 % gives 9.80 mmHg and the jugular shift 1.38 % gives 12.06 mmHg.
3. **Actions don't match the kinematics.** The third action is "Re-Balance Right Knee Alignment", but the flagged value is `lumbar_asymmetry_ratio`.

The old draft's cortisol mismatch is gone: 18.2 nM now gives ΔIds/I0 = 0.358 as in the example.

## References (p.9-10)

1. **Saputra et al. 2025 looks like a renamed citation.** "Piezoelectric effect of κ-carrageenan as a tool for force sensor", Sensors 25(15), 4594 is the paper the earlier draft and `NSA_hydrograph.md` credit to Bučinskas, Žaimis, Udris, Petronienė & Dzedzickis (doi:10.3390/s25154594). It is also still about piezoelectric, not piezoresistive, behaviour.
2. **Lakshmanakumar et al. 2019 still doesn't match the troponin model.** It is an antibody-free electrochemical method; the Debye formula models a receptor layer on a GFET.
3. **Several entries can't be looked up.** Chen et al. 2025 (ACS Sensors), Bellando-Randone et al. 2023 (Biosensors and Bioelectronics) and Rajaratnam et al. 2023 (Journal of Pineal Research) have no volume, pages or DOI.

## Section 4: adaptive polling (p.6)

Found while writing `hydrograph_core/polling.py`.

1. **It is called a state machine but has no transitions.**
   - The plan never says how ACTIVE, RESTING and SLEEPING are detected or when the state changes.
   - Code: out of scope for the library. The backend keeps the state and passes it in; the backend still needs detection rules from somewhere.
2. **Sleep rates missing.**
   - Hydrogel Strain & Sweat is "Suspended (SANS passive)" while sleeping, and passive neck SANS monitoring continues, with no rate. Code: `cephalic_fluid_index` is UNSPECIFIED; `sweat_rate` and `kinematics` are suspended.
   - Neuro-Cognitive & Sleep says "Continuous Actigraphy" with no rate, and nothing for EEG and PVT. Code: `actigraphy` is CONTINUOUS with no interval; `eeg_theta_alpha_ratio` and `pvt_rt` are UNSPECIFIED. (The old draft had "Hourly EEG".)
3. **PVT is polled like a sensor.** The table polls `pvt_rt` every 15 min (active) and hourly (resting). Finding 5 (p.3) describes a 5-minute test the user takes.
4. **Tier 1 inputs missing from the table.**
   - SpO2, core temperature, respiratory rate, ppCO2, NEWS2, sleep debt and mood score are on the Tier 1 window or payload but have no polling row. Neither do hs-cTnI (event-triggered in Finding 1) and TNF-α.
   - Code: `poll_interval` raises `ValueError` for them.
5. **No broadcast rate.** The old draft broadcast the payload every 1000 ms; the new one gives no rate.

## Section 5: JSON payload (p.8)

Found while writing `hydrograph_core/payload.py`. The example-value mismatches are listed above under "Example JSON payload".

1. **The kinematics block doesn't match Parameter 3.2.**
   - The example has `left_knee_flexion_deg` and `right_shoulder_abduction_deg`, two different joints. Parameter 3.2 measures one left/right pair of the same joint.
   - `lumbar_asymmetry_ratio` names a lumbar sensor that no parameter defines.
   - Code: the backend passes any joint angles plus one `JointResult` and names its pair (`form_joint="lumbar"`).
2. **It isn't clear which GFET `delta_Ids_over_I0` comes from.** Code: the cortisol reading, which matches the example's numbers.
3. **No rule for `primary_hazard` or `recommended_actions`.**
   - The example reads as the names of the non-nominal results joined with " + ", but the plan never says so. Its actions split Finding 9's card in two.
   - Code: names of the results at the worst status; actions from all WARNING and CRITICAL results, worst first.
4. **Enumerations shown with one value only.** `latent_virus_shedding` is `"NO_DETECT"` and `cortisol_diurnal_slope_status` is `"NOMINAL"`; the other values aren't given. Code: shedding is passed through as a string; the slope status is a `Status`, upper case like the other statuses.
5. **Missing vitals.** Sleep debt and mood score are Tier 1 vitals (p.1) but have no payload field. Code: they can only appear through `others` in the copilot block.
