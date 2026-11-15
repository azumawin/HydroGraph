# Suspected spec problems

Things that look wrong in the master plan (`Tiered Master System Specification & Implementation Plan.pdf`, the 10-page "Verified Edition", cited by page) but are not yet checked against research. Confirmed problems go in `mismatches.md` instead.

## Section 2: Tier 1 findings (p.2-4)

Found while writing `core/findings.py`.

1. **Some criteria still have no cutoff.**
   - Finding 5: the sleep duration is "anchored to flight baseline (ISS mean 6.09 hrs vs. 8.5 hrs scheduled)" but no number triggers. Code: the parameter spec's 4.3 cutoff (nominal needs > 7.5 h).
   - Findings 5 and 6: PVT lapse counts and sleep debt. Code: required keyword-only arguments.
   - Finding 4: "rising respiratory rate". Code: a `bool` evaluated upstream.
   - Finding 2: sweat rate and Na+ flux are baseline-relative trends with no cutoff. Code: not used.
2. **Level 2 hypoglycemia is not marked urgent.** Finding 7 lists Level 1 (< 70 mg/dL) and Level 2 (< 54 mg/dL) but gives one action card and no severity. Code: both are WARNING, the trigger names the level. Tier 2 glucose (2.1) makes Level 2 CRITICAL.
3. **Finding 10 mixes a warning with a shelter alert.** The dose-rate spike is "> 50 µSv/h warning", but the finding has a single action, "Move to shielded storm shelter zone immediately". Code: the SPE flag is CRITICAL, the dose rate and the career dose are WARNING; all use the shelter card.
4. **Finding 2's "calculated fluid deficit" isn't defined.** Code: 1 kg of acute body-mass loss = 1 L, returned as `fluid_deficit_ml`.

## References (p.9-10)

1. **Saputra et al. 2025 looks like a renamed citation.** "Piezoelectric effect of κ-carrageenan as a tool for force sensor", Sensors 25(15), 4594 is the paper the earlier draft and `NSA_hydrograph.md` credit to Bučinskas, Žaimis, Udris, Petronienė & Dzedzickis (doi:10.3390/s25154594). It is also still about piezoelectric, not piezoresistive, behaviour.
2. **Lakshmanakumar et al. 2019 still doesn't match the troponin model.** It is an antibody-free electrochemical method; the Debye formula models a receptor layer on a GFET.
3. **Several entries can't be looked up.** Chen et al. 2025 (ACS Sensors), Bellando-Randone et al. 2023 (Biosensors and Bioelectronics) and Rajaratnam et al. 2023 (Journal of Pineal Research) have no volume, pages or DOI.
