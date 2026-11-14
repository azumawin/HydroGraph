# Suspected spec problems

Things that look wrong in the master plan (`Tiered Master System Specification & Implementation Plan.pdf`, cited by page) but are not yet checked against research. Confirmed problems go in `mismatches.md` instead.

## Section 3A: hydrogel gauge factor (p.3)

Found while writing `hydrogfn/gauge_factor.py`.

1. **The GF ranges make resistance readings ambiguous.**
   - GF drops sharply at 5 % and 15 %, so ΔR/R0 = GF·ε falls too: 59.04 at the top of range A, 11.67 at the bottom of B, 58.44 at the top of B, 11.15 at the bottom of C.
   - A reading such as ΔR/R0 = 20 fits a strain in all three ranges (1.69 %, 7.39 % and 21.66 %).
   - Every reading B or C can produce, A also produces at a lower strain. If the lowest match is taken, B and C are never reported. No reading above 59.04 has any match.
   - Code: `strain_from_resistance` returns the lowest match and lists all matches in `candidates_pct`.
2. **The plan doesn't say which way GF runs inside B and C.**
   - It gives only the spans "233.48 – 389.58" and "74.34 – 114.86".
   - Code: interpolates linearly from the first value at the low strain to the second at the high strain. If GF falls with strain instead, the numbers change but the ambiguity in item 1 stays.
3. **GF 1180.75 disagrees with the parameter spec by a factor of 560.**
   - `NSA_hydrograph.md` uses GF = 2.1 for the same carrageenan strip (Parameters 1.1 and 3.2).
   - At 5 % strain, GF 1180.75 means resistance rises by a factor of 60 (ΔR/R0 = 59). That is very high for micro-strain.
   - Decide which GF the ICP and joint-angle code should use.
4. **The plan's own strain formula never leaves range A.**
   - ε = t_film·θ / (2·L0) with t_film = 1.2 mm and L0 = 50 mm gives at most 3.77 %, even at θ = 180°.
   - Range B is described as "elbow, wrist, and knee joint flexion" but no joint angle can reach it.
   - ΔL = 0–9.99 mm over L0 = 50 mm caps strain at 19.98 %, so range C (up to 30 %) is never fully reached.
5. **Some cases are undefined.**
   - Section 3A says "elongation and compression ranges" but gives no compression range (ε < 0) and nothing above 30 %. Code: raises `ValueError` for both.
   - 5 % and 15 % each belong to two ranges. Code: the lower range wins.

## Example JSON payload (p.6)

The example values don't match the plan's own formulas.

1. **Hydrogel block.** strain 1.42 %, GF 312.4, ΔR/R0 0.145.
   - 312.4 × 0.0142 = 4.44, not 0.145.
   - 1.42 % is in range A, so GF should be 1180.75. 312.4 is a range B value.
2. **ICP.** `estimated_icp_mmHg` is 14.8. With the spec's k1 = 185.4 and baseline 9.5, a strain of 1.42 % gives 12.1 mmHg.
3. **Cortisol.** 18.2 nM and ΔIds/I0 0.312.
   - The Langmuir formula on p.3 (Imax 0.65, Kd 14.8 nM) gives 0.359 for 18.2 nM.
   - A reading of 0.312 corresponds to 13.7 nM.

## References (p.3, p.6)

1. **Bučinskas et al. 2025 is about a different effect.** The title is "Piezoelectric Effect of k-Carrageenan". Section 3A uses it to support piezoresistive (resistance-change) gauge factors.
2. **Tong et al. 2026 uses a different method.** It is a SERS (Raman) chip, cited for a GFET current-shift formula.
3. **Lakshmanakumar et al. 2019 doesn't match the troponin model.** It is an antibody-free electrochemical method, but the troponin Debye formula models an "antibody-antigen binding layer".

## Section 4: adaptive polling (p.4-5)

Found while writing `hydrogfn/polling.py`.

1. **It is called a state machine but has no transitions.**
   - The plan never says how ACTIVE, RESTING and SLEEPING are detected or when the state changes.
   - Code: out of scope for the library. The backend keeps the state and passes it in; the backend still needs detection rules from somewhere.
2. **Passive SANS tracking during sleep contradicts the table.**
   - The Biomechanics & Fluids row says "Suspended / Paused" while sleeping, but its logic column says "passive SANS tracking continues". No rate is given.
   - Code: `cephalic_fluid_index` is UNSPECIFIED while sleeping; `sweat_rate` and `joint_kinematics` are suspended.
3. **PVT is polled like a sensor.**
   - The table polls `pvt_reaction_time` every 15 min (active) and hourly (resting). Finding 5 (p.2) describes PVT as a daily 5-minute test the user takes.
   - The sleeping column names only actigraphy and EEG. Code: PVT is UNSPECIFIED while sleeping.
4. **Tier 1 vitals missing from the table.**
   - SpO2, core temperature, respiratory rate, sleep debt and mood score are on the Tier 1 window (p.1) but have no polling row. Cytokines (Parameter 5.1) and troponin have none either.
   - Code: `poll_interval` raises `ValueError` for them.
5. **The 1000 ms payload doesn't fit the polling rates.**
   - The JSON payload (p.6) is broadcast every 1000 ms, but most channels are sampled every 15 s to 60 min. The plan doesn't say whether the payload repeats the last value or omits stale channels.

## Section 5: JSON payload (p.6)

Found while writing `hydrogfn/payload.py`. The example-value mismatches are listed above under "Example JSON payload".

1. **The kinematics block doesn't match Parameter 3.2.**
   - The example has `left_knee_flexion_deg` and `right_shoulder_abduction_deg`, two different joints. Parameter 3.2 measures one left/right pair of the same joint.
   - `lumbar_asymmetry_ratio` names a lumbar sensor that no parameter defines.
   - Code: the backend passes any joint angles plus one `JointResult` and names its pair (`form_joint="lumbar"`).
2. **It isn't clear which GFET `delta_Ids_over_I0` comes from.** It sits next to cortisol and troponin, and only cortisol uses ΔIds/I0 in the plan. Code: the cortisol reading.
3. **No rule for `primary_hazard` or `recommended_actions`.**
   - The example ("SANS Fluid Shift + ARED Lifting Asymmetry") reads as the names of the non-nominal results joined with " + ", but the plan never says so.
   - Code: names of the results at the worst status; actions from all WARNING and CRITICAL results, worst first.
4. **Status casing differs.** The payload uses `"WARNING"`; nothing else in either spec gives a casing. Code: upper case in the payload only.
5. **Missing vitals.** SpO2, sleep debt and mood score are Tier 1 vitals (p.1) but have no payload field. Code: they can only appear through `others` in the copilot block.
