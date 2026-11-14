# HydroGFN Unhealthy Simulation Specification: 5 Core Fault Scenarios

This document defines the **5 highest-priority physiological fault scenarios** for a single-astronaut personal health simulation. Each scenario is structured so the software team can inject realistic, mathematically consistent multi-parameter shifts into the simulation engine and verify that the Autonomous Co-Pilot triggers the correct personal health alerts and countermeasures.

## Nominal Baseline Reference (Healthy Resting State in `0G`)

Before injecting any fault scenario, the simulation engine runs at the astronaut's healthy personal baseline:

* **Vitals:** `heart_rate`: `72 bpm` | `bp_systolic / bp_diastolic`: `118 / 78 mmHg` | `spo2`: `97%` | `respiratory_rate`: `14 br/min` | `zhf_core_temp`: `36.8 °C` | `hrv_rmssd`: `48 ms` | `consciousness_level`: `"ALERT"` | `supplemental_o2`: `false`

* **Hydrogel & GFET:** `jugular_strain_pct`: `0.65%` (`delta_R_over_R0`: `0.101`, computed via $15.5 \times 0.0065 = 0.10075$) | `sweat_rate`: `45 mL/h` | `sweat_sodium`: `38 mmol/L` | `isf_cortisol_nM`: `11.5 nM` (`delta_Ids_over_I0`: `0.284`) | `ntx_pct_baseline`: `+6%` | `il6_pg_mL`: `1.4 pg/mL` | `eeg_cfe_ratio`: `0.58`

* **Environment:** `cabin_ppco2_mmHg`: `2.2 mmHg` | `radiation_dose_rate`: `0.28 µSv/h` | `spe_flag`: `false`

## Scenario 1: Spaceflight-Associated Neuro-Ocular Syndrome (SANS) & Cephalic Fluid Shift

* **Scenario ID:** `FAULT_01_SANS_CEPHALIC`

* **Category:** Microgravity Fluid Redistribution / Neuro-Ocular Risk (Finding 9)

* **Physiological Description:** In `0G`, the absence of hydrostatic pressure shifts `1.5–2.0 L` of fluid headward, engorging the internal jugular veins and elevating intracranial/intraocular pressure. Sustained cephalic pooling flattens the posterior globe and causes optic disc edema, risking permanent visual impairment if unmitigated.

### Multi-Parameter Shift Rules

1. **Primary Trigger (`jugular_strain_pct`):** Increase from `0.65%` nominal into the Warning (`1.10%–1.80%`) or Critical (`> 1.80%`) zone.

2. **Derived Hydrogel Electrical Output (`delta_R_over_R0`):** Scales dynamically via $\frac{\Delta R}{R_0} = GF \cdot \epsilon$ (using empirical Zone 2 Gauge Factor $GF \approx 15.5$ at \~0.7–0.9 mm neck skin dilation; nominal baseline `0.0065` $\rightarrow$ `0.101`).

3. **Secondary Correlated Shifts:** Derived `icp_risk_indicator_mmHg` rises above `15.0 mmHg` (experimental baseline-relative indicator); `hrv_rmssd` dips slightly (`36 ms`) due to baroreceptor loading; `visual_acuity_logmar` shifts from `0.00` to `+0.20` when the user runs the triggered eye screen.

### Concrete Simulation Example

* **Action:** Toggle environment to `0G_MICROGRAVITY` and ramp `jugular_strain_pct` from **`0.65%` → `1.55%`** (Warning) or **`2.05%`** (Critical).

* **Resulting Multi-Parameter Payload:**

  * `jugular_strain_pct`: `1.55%`

  * `delta_R_over_R0`: `0.240` ($15.5 \times 0.0155 = 0.24025$)

  * `icp_risk_indicator_mmHg`: `16.2 mmHg` (Warning > `15.0 mmHg`)

  * `amsler_grid_distortion`: `true` (upon self-test)

* **Expected Co-Pilot Output:** Amber/Red Alert → *"Elevated cephalic fluid shift (+1.55% jugular strain). Launch on-screen LogMAR & Amsler eye screen and initiate 20-min LBNP session at -35 mmHg."*

## Scenario 2: Acute Cabin Hypercapnia ($\text{CO}_2$ Scrubber Failure) & Mild Hypoxia

* **Scenario ID:** `FAULT_02_HYPERCAPNIA_CO2`

* **Category:** Closed-Environment Life Support Emergency (Finding 4)

* **Physiological Description:** A malfunction in the Carbon Dioxide Removal Assembly (CDRA) causes ambient $\text{ppCO}_2$ to rise rapidly inside the astronaut's module. Excess inhaled $\text{CO}_2$ triggers cerebral vasodilation (causing throbbing headaches and cognitive slowing) and forces compensatory hyperventilation and tachycardia before $\text{SpO}_2$ drops.

### Multi-Parameter Shift Rules

1. **Primary Trigger (`cabin_ppco2_mmHg`):** Increase from `2.2 mmHg` nominal to **`3.5 – 6.0 mmHg`** (`~4,600 – 7,900 ppm`; ISS headache threshold is `> 3.0 mmHg`).

2. **Respiratory & Cardiac Compensation:** `respiratory_rate` climbs from `14` to **`22 – 26 br/min`**; `heart_rate` climbs from `72` to **`96 – 112 bpm`**.

3. **Oxygenation & Cognitive Impact:** `spo2` drops from `97%` to **`91% – 93%`** (Warning `< 94%`); `eeg_cfe_ratio` ($\Theta/\alpha$) rises from `0.58` to **`1.28`** (`> 1.20` cognitive impairment).

### Concrete Simulation Example

* **Action:** Inject scrubber fault by increasing `cabin_ppco2_mmHg` from **`2.2 mmHg` → `4.8 mmHg`** over 90 seconds.

* **Resulting Multi-Parameter Payload:**

  * `cabin_ppco2_mmHg`: `4.8 mmHg`

  * `spo2`: `92%`

  * `respiratory_rate`: `24 br/min`

  * `heart_rate`: `104 bpm`

  * `eeg_cfe_ratio`: `1.28`

* **Expected Co-Pilot Output:** Critical Red Alert → *"Acute CO₂ accumulation (4.8 mmHg) with mild hypoxemia (SpO₂ 92%). Check air scrubber, increase ventilation, or relocate module immediately."*

## Scenario 3: Acute EVA Dehydration & Electrolyte Depletion

* **Scenario ID:** `FAULT_03_EVA_DEHYDRATION`

* **Category:** Fluid & Electrolyte Homeostasis (Finding 2)

* **Physiological Description:** During a 6-hour Extravehicular Activity (EVA), microgravity blunts the astronaut's thirst reflex while heavy metabolic exertion drives high sweat loss. Plasma volume contracts, narrowing pulse pressure, elevating heart rate, and concentrating urine—creating immediate heat-stress and fainting risks.

### Multi-Parameter Shift Rules

1. **Primary Hydrogel Trigger (`sweat_rate` & `sweat_sodium`):** During `EVA_ACTIVE` mode, increase `sweat_rate` from `45` to **`650 – 950 mL/h`** and `sweat_sodium` conductivity from `38` to **`68 – 85 mmol/L`** (baseline-relative surge).

2. **Fluid Deficit & Mass Loss:** Cumulative `body_mass_loss_pct` crosses **`> 2.0%`** (`2.1% – 3.2%`), and `urine_specific_gravity` rises from `1.012` to **`1.024 – 1.030`** (`> 1.020` threshold).

3. **Hemodynamic Compensation:** `heart_rate` climbs to **`115 – 132 bpm`**, while `bp_systolic` drops to **`96 – 102 mmHg`** and `bp_diastolic` holds at `74 mmHg` (narrowed pulse pressure `22–28 mmHg`; Shock Index `HR/SBP > 1.1`).

### Concrete Simulation Example

* **Action:** Set mode to `EVA_ACTIVE` and increase `sweat_rate` to **`820 mL/h`** for 2.5 simulated hours with low drink-bag intake.

* **Resulting Multi-Parameter Payload:**

  * `sweat_rate`: `820 mL/h` | `sweat_sodium`: `74 mmol/L`

  * `body_mass_loss_pct`: `2.4%` | `urine_specific_gravity`: `1.026`

  * `heart_rate`: `122 bpm` | `bp_systolic / bp_diastolic`: `98 / 74 mmHg` (Shock Index `1.24`)

* **Expected Co-Pilot Output:** Critical Red Alert → *"Acute dehydration (>2.4% mass loss, Shock Index 1.24). Drink 600 mL electrolyte solution within 30 minutes and reduce EVA workload."*

## Scenario 4: Acute Infection / Latent Viral Reactivation & Sepsis Escalation

* **Scenario ID:** `FAULT_04_ACUTE_INFECTION`

* **Category:** Immune Dysregulation & Clinical Triage (Finding 3)

* **Physiological Description:** Cumulative cosmic radiation and circadian stress weaken cellular immunity, allowing latent herpesviruses (EBV/VZV) to reactivate or a bacterial infection to escalate. Systemic inflammation drives fever, tachypnea, tachycardia, and early vasodilatory hypotension.

### Multi-Parameter Shift Rules

1. **Primary Thermal & Vital Triggers (Adapted `NEWS2` & `SIRS`):** Increase `zhf_core_temp` from `36.8 °C` to **`38.4 – 39.2 °C`** (`> 38.0 °C` SIRS fever; `≥ 39.1 °C` scores 2 on NEWS2), `heart_rate` to **`108 – 125 bpm`**, `respiratory_rate` to **`22 – 25 br/min`**, and drop `bp_systolic` to **`94 – 99 mmHg`** (`≤ 100 mmHg` triggers qSOFA point).

2. **Full 7-Parameter Adapted NEWS2 Scoring Function:** The backend scoring function evaluates all 7 Royal College of Physicians NEWS2 inputs:
   * **5 Automated Telemetry Channels:** `zhf_core_temp`, `heart_rate`, `respiratory_rate`, `bp_systolic`, and `spo2` (Scale 1, room air).
   * **2 Explicit State / Prompted Inputs:** `consciousness_level` (ACVPU scale: `"ALERT"` = `0 pts`, `"CONFUSION" | "VOICE" | "PAIN" | "UNRESPONSIVE"` = `3 pts`, defaulted to `"ALERT"` until a cognitive/PVT or manual check-in flags altered mentation) and `supplemental_o2` (`false` = `0 pts` on cabin air, `true` = `2 pts` if emergency $\text{O}_2$ mask is engaged).

3. **GFET Molecular & Saliva Confirmation:** Set `post_ared_exercise_window` = `false` (confirming inflammation is not workout-induced), raise GFET `il6_pg_mL` from `1.4` to **`6.8 – 12.0 pg/mL`** (`> 3.0 pg/mL` provisional warning), and switch `latent_virus_shedding` to **`"DETECTED"`**.

4. **Composite Score:** `news2_aggregate_score` jumps from `0` to **`7 – 9`** (`≥ 7` Emergency threshold) and `qsofa_score` reaches **`2`** (`RR ≥ 22` and `SBP ≤ 100`).

### Concrete Simulation Example

* **Action:** Inject systemic infection state by increasing `zhf_core_temp` from **`36.8 °C` → `38.7 °C`** and setting `latent_virus_shedding` = `"DETECTED"` on cabin air (`supplemental_o2` = `false`) with intact alertness (`consciousness_level` = `"ALERT"`).

* **Resulting Multi-Parameter Payload & NEWS2 Breakdown:**

  * `zhf_core_temp`: `38.7 °C` (`+1 pt`) | `heart_rate`: `116 bpm` (`+2 pts`) | `respiratory_rate`: `23 br/min` (`+2 pts`) | `bp_systolic`: `96 mmHg` (`+2 pts`) | `spo2`: `94%` (`+1 pt`)

  * `consciousness_level`: `"ALERT"` (`0 pts`) | `supplemental_o2`: `false` (`0 pts`)

  * `news2_aggregate_score`: `8` (`1 + 2 + 2 + 2 + 1 + 0 + 0 = 8`) | `qsofa_score`: `2`

  * `il6_pg_mL`: `8.4 pg/mL` (`post_ared_exercise_window`: `false`) | `latent_virus_shedding`: `"DETECTED"`

* **Expected Co-Pilot Output:** Critical Red Alert → *"NEWS2 Score 8 / qSOFA 2: Acute febrile illness & immune reactivation detected. Initiate onboard medical-kit antipyretic/antibiotic protocol, suspend physical tasks, and flag urgent flight-surgeon review."*

## Scenario 5: Chronic Circadian Misalignment, HPA-Axis Burnout & Bone/Renal Stone Drift

* **Scenario ID:** `FAULT_05_CHRONIC_TRANSIT_DRIFT`

* **Category:** Long-Duration Isolation & Musculoskeletal/Metabolic Degradation (Findings 5, 6 & 8)

* **Physiological Description:** Over weeks of deep-space transit, heavy operational schedules cut sleep to `< 5.5 h/night`, flattening the astronaut's diurnal cortisol rhythm and degrading prefrontal executive attention. Simultaneously, skipped or asymmetrical ARED resistive workouts plus low fluid intake accelerate bone mineral resorption and urinary calcium supersaturation (kidney stone risk).

### Multi-Parameter Shift Rules

1. **Neuro-Cognitive & Sleep Shift:** `sleep_duration` drops from `6.4 h` to **`4.8 – 5.4 h`**; prefrontal dry graphene `eeg_cfe_ratio` ($\Theta/\alpha$) climbs from `0.58` to **`1.35 – 1.55`** (`> 1.20` microsleep risk); daily `pvt_lapses` (`> 500 ms`) rise from `0` to **`6 – 9 lapses`**.

2. **GFET Cortisol & Langmuir Shift:** `isf_cortisol_nM` stays persistently elevated in the evening at **`26.0 – 34.0 nM`** (flattening `diurnal_cortisol_slope` from `-0.42` to **`-0.08`**). Using the Langmuir equation $\frac{\Delta I_{ds}}{I_0} = \frac{0.65 \cdot [\text{Cortisol}]}{14.8 + [\text{Cortisol}]}$, GFET `delta_Ids_over_I0` saturates from `0.284` up to **`0.415 – 0.453`**.

3. **Bone Resorption & Renal Stone Risk:** GFET `ntx_pct_baseline` climbs from `+6%` to **`+32% – +45%`** (`> +25%` warning), `urine_volume_24h_L` drops from `2.3 L` to **`1.3 – 1.6 L/day`** (`< 2.0 L/day` stone risk), and hydrogel `joint_asymmetry_ratio` hits **`1.32`** (`> 1.25` form warning).

### Concrete Simulation Example

* **Action:** Fast-forward Mission Elapsed Time (`MET_days` = `45`) with `sleep_debt` and `low_ared_compliance` enabled.

* **Resulting Multi-Parameter Payload:**

  * `sleep_duration`: `5.1 h` | `eeg_cfe_ratio`: `1.42` | `pvt_lapses`: `7`

  * `isf_cortisol_nM`: `29.5 nM` | `delta_Ids_over_I0`: `0.433` | `diurnal_cortisol_slope`: `-0.09`

  * `ntx_pct_baseline`: `+36%` | `urine_volume_24h_L`: `1.45 L/day` | `joint_asymmetry_ratio`: `1.32`

* **Expected Co-Pilot Output:** Multi-Card Amber Alert →

  1. *"High cognitive fatigue (CFE 1.42) & HPA stress: defer complex tasks, run 45-min 480 nm blue-light therapy, schedule 30-min nap."*

  2. *"Elevated bone resorption (+36% NTx) & renal stone risk: raise daily water target to 2.5 L and rebalance ARED squat stance."*

## Quick Developer Cheat Sheet: Parameter Trigger Summary

*(All variable keys below match the exact JSON payload schema keys 1:1)*

| Fault Scenario | Primary Knob to Turn in Simulator | Correlated Secondary Parameters That Must Shift Together |
| :--- | :--- | :--- |
| **1. SANS / Cephalic Shift** | `jugular_strain_pct`: `0.65%` → **`1.55%`** | `delta_R_over_R0` (`0.240`), `icp_risk_indicator_mmHg` (`16.2`), `visual_acuity_logmar` (`+0.20`) |
| **2. Cabin** $\text{CO}_2$ **/ Hypoxia** | `cabin_ppco2_mmHg`: `2.2` → **`4.8 mmHg`** | `spo2` (`92%`), `respiratory_rate` (`24`), `heart_rate` (`104`), `eeg_cfe_ratio` (`1.28`) |
| **3. EVA Dehydration** | `sweat_rate`: `45` → **`820 mL/h`** | `sweat_sodium` (`74 mmol/L`), `body_mass_loss_pct` (`2.4%`), `heart_rate` (`122`), `bp_systolic` (`98`) |
| **4. Acute Infection** | `zhf_core_temp`: `36.8` → **`38.7 °C`** | `heart_rate` (`116`), `respiratory_rate` (`23`), `bp_systolic` (`96`), `spo2` (`94%`), `consciousness_level` (`"ALERT"`), `supplemental_o2` (`false`), `news2_aggregate_score` (`8`), `il6_pg_mL` (`8.4`), `latent_virus_shedding` (`"DETECTED"`) |
| **5. Chronic Transit Drift** | `MET_days`: `0` → **`45`** | `sleep_duration` (`5.1 h`), `eeg_cfe_ratio` (`1.42`), `isf_cortisol_nM` (`29.5 nM`), `ntx_pct_baseline` (`+36%`), `urine_volume_24h_L` (`1.45 L/day`) |