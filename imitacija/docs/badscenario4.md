# Scenario 4 implementation plan: acute infection, viral reactivation & sepsis escalation

**Scenario:** `FAULT_04_ACUTE_INFECTION` — Finding 3.

**Source:** [Unhealthy simulation specification](hydrogfn_unhealthy_simulation_specification%20%281%29.md), Scenario 4.

**Pattern:** [Scenario 1](../badscenario1.md), [Scenario 2](badscenario2.md) and [Scenario 3](badscenario3.md). File paths below are relative to the simulator root unless stated otherwise.

**Status:** Implementation plan only. Build on the three implemented scenarios and preserve the requested all-channel startup behavior. Source endpoints are fixture requirements. The compressed timeline, interpolation, specimen events and processing delays below are engineering assumptions, not a validated infection or sepsis progression model.

## 1. What can be reused, and what is missing

The vital channels, serum IL-6 assay, virus-specific PCR results, HTTP receiver and infection evaluator already exist. The source's explicit state inputs, GFET IL-6 and qSOFA require additions.

| Area | Existing code | Planned use |
| --- | --- | --- |
| Configuration | `models.Settings`, existing scenario models | Add optional `AcuteInfectionScenario` with a target owner. |
| Pure trajectories | `scenarios.py`, `smoothstep()` | One shared progression for fever, tachycardia, tachypnea, hypotension, oxygenation and IL-6. |
| Vitals | `heart_rate()`, `crew_values()`, `rmssd()` | Apply context inside HR/RR windows and HRV beat timing. |
| Specimen signals | `il6_serum`, `viral_ebv_detected`, `viral_vzv_detected`, `viral_cmv_detected` | Add target assay events and explicitly select EBV reactivation for the demo. |
| Acquisition | `Scheduler`, existing owner-specific EVA rule replacement | Add target BP/specimen rules and new context/GFET groups without duplicate acquisitions. |
| Startup and preview | `Scheduler.initialize()`, `PreviewState` | Emit every available baseline once; support a consciousness enum value. |
| Existing NEWS2 | `../backend/packages/hydrograph-core/src/hydrograph_core/assessment.py::news2()` | Extend its five measured parameters with explicit oxygen and consciousness inputs. |
| Existing Finding 3 | `findings.acute_infection_3_1()` | Preserve current severity thresholds; enrich the assessment result with score breakdown and qSOFA. |
| Ingestion and SSE | Backend `channels.py`, `api/serializers.py`, `api/findings.py`, `api/views.py` | Accept new state/GFET readings and recompute the infection finding when they change. |

The current `news2()` assumes alertness and room air. The assessment always supplies `post_ared_window=False`; it does not receive that context. The current `Reading` value type allows only numbers and booleans, so transmitting `consciousness_level="ALERT"` needs a coordinated, narrowly validated enum extension.

Unlike scenarios 2 and 3, the existing Finding 3 severity already agrees with the source: NEWS2 ≥7 yields `critical`. Its existing action text is less detailed than the source's example. qSOFA and the seven-component breakdown are currently absent.

## 2. Exact signals and identifier mapping

| Source signal | Simulator representation | Healthy fixture | Affected fixture |
| --- | --- | --- | --- |
| `zhf_core_temp` | Existing `body_temperature` | 36.8 °C | 38.7 °C |
| `heart_rate` | Existing `heart_rate` | 72 bpm | 116 bpm |
| `respiratory_rate` | Existing `respiratory_rate` | 14 br/min | 23 br/min |
| `bp_systolic` | Existing `bp_systolic` | 118 mmHg | 96 mmHg |
| `spo2` | Existing `spo2` | 97% | 94% |
| `consciousness_level` | New enum channel of the same name | `ALERT` | `ALERT` in the default example |
| `supplemental_o2` | New boolean channel of the same name | false | false |
| `post_ared_exercise_window` | New boolean channel of the same name | false | false |
| `il6_pg_mL` | New GFET fixture channel of the same name | 1.4 pg/mL | 8.4 pg/mL |
| Supporting serum IL-6 | Existing `il6_serum` | 1.4 pg/mL | 8.4 pg/mL at a configured specimen event |
| `latent_virus_shedding="DETECTED"` | Existing `viral_ebv_detected=true` | false | true at a positive saliva specimen event |
| NEWS2 / qSOFA | Backend-derived result fields | 0 / 0 | 8 / 2 |

The source does not supply an affected diastolic pressure, so retain its normal profile/model rather than inventing a target. Set the demo profile to 118/78 mmHg and RMSSD 48 ms. Do not change mass, hydration, sweat, radiation, cabin CO₂ or unrelated biochemical references.

**GFET versus serum:** Keep `il6_serum` as the existing serum laboratory channel. Add `il6_pg_mL` as a separate, explicitly synthetic interstitial/GFET concentration estimate. Both may share the 1.4 → 8.4 fixture curve for this demonstration, but equal numbers do not establish specimen equivalence or a real sensor calibration. No GFET current-transfer equation is supplied for IL-6; do not invent electrical output. The source's >3 pg/mL rule is used as its provisional simulation trigger for this new channel.

**Virus specificity:** Select EBV for the default saliva fixture. Continue publishing VZV=false and CMV=false on their own schedules. `DETECTED` is a display interpretation of the selected positive assay, not a new generic string channel or a reason to turn all viral channels positive. Do not claim a positive shedding assay independently establishes the cause of sepsis.

**State inputs:** Default alertness, room air and no post-ARED window are explicit simulation fixtures. They are not inferred from HR, EEG or task activity. Do not introduce a manual check-in UI or treatment command channel as part of this implementation.

## 3. Proposed reproducible timeline

Use a 3000-second run, with delayed confirmation after the vital progression. All times are elapsed simulation seconds.

| Time | Behavior |
| --- | --- |
| 0 | Publish every available startup reference once, including all state channels, GFET IL-6 and baseline-negative virus fixtures. |
| 0–600 s | Healthy scenario references. NEWS2 and qSOFA remain zero for the default resting demo. |
| 600–1800 s | Smoothly progress all six numeric references: temperature, HR, RR, SBP, SpO₂ and IL-6. |
| 1800 s onward | Hold affected references; default explicit state remains alert / no oxygen / no post-ARED window. |
| 1860 s | Collect a synthetic serum IL-6 specimen and saliva PCR specimen. EBV is positive; VZV remains negative. |
| 1980 s | Those results become available with the demo's 120-second lab delay, plus any communication delay. Their acquisition timestamps remain 1860 s. |
| 1980–3000 s | Hold a stable critical fixture with the laboratory/viral evidence available. No treatment response or recovery is modeled. |

The source provides endpoints but no onset duration. These 20-minute ramps and two-minute assay processing times are compressed demonstration assumptions, not statements about infection biology or real PCR turnaround.

Use the existing smoothstep:

```python
w = smoothstep(t, scenario.onset_s, scenario.affected_at_s)
# Each baseline comes from scenario settings or the target profile.
reference = baseline + (affected - baseline) * w
```

Proposed helpers: `infection_references(t, profile, scenario)`, `infection_context_values(t, scenario)`, `infection_gfet_values(t, scenario, *, startup=False)` and `infection_viral_values(group, t, scenario)`.

The GFET minute output is the mean concentration over its completed 60-second window, evaluated on a one-second midpoint grid. Serum concentration is evaluated at specimen collection time. EBV becomes positive for specimens collected at or after `reactivation_at_s=1800`, regardless of when the result is delivered. Never decide specimen positivity from result-arrival time.

Evaluate solely from simulation time, owner and configuration. Disabling GFET or PCR output must not stop the vital progression. Playback speed, skipped polls and delivery retries must not advance the fault itself.

## 4. Apply changes inside the existing signal models

Add optional keyword-only infection context through `crew_values()`, `heart_rate()`, `rmssd()` and startup handling. Gate it by `owner_id`, preserving no-scenario behavior and previous scenario paths.

Use a consistent reference/variation policy:

- For HR and systolic BP, blend the healthy deterministic value excluding its noise term toward the affected reference using `w`, then add its original bounded noise once. This follows the EVA pattern and avoids adding the daily exercise rise on top of the full disease target. Leave diastolic BP unchanged.
- For temperature, RR and SpO₂, first use the scenario baseline (36.8, 14, 97) with the existing healthy residual terms; fade the activity/circadian residuals by `1-w` while moving the reference to its target. Retain only the bounded seeded measurement noise at the endpoint. This makes the final fixture independent of the daily exercise phase without changing global `activity()`.
- Compute HR and RR with the existing twelve five-second midpoint samples over the preceding minute. Evaluate infection progression at each sample time. Do not replace a completed window with an instantaneous endpoint.
- Pass affected HR into `rmssd()` beat timing. The source gives no infection-specific RMSSD reduction, so retain the existing RMSSD reference and extraction method.
- Use deterministic IL-6 concentration references for both the GFET window and synthetic serum specimens. Do not add post-exercise IL-6 variation to the explicitly non-ARED infection example.

At a fully affected resting plateau, target observation bounds are HR 116±0.8 bpm, RR 23±0.35 br/min, SBP 96±1.2 mmHg, temperature 38.7±0.025 °C and SpO₂ 94±0.25 percentage points. The current NEWS2 rounding policy assigns the expected bands throughout these bounds. Test that explicitly rather than requiring noisy values to equal their references.

Startup uses exact declared references for the affected channels. Normal scheduled outputs include the stated variation. All unrelated channels continue their ordinary models; a single shared active fault is supported at a time.

## 5. New channels, transport types and acquisition rules

| Channel | Source unit | Wire unit | Conversion / acquisition |
| --- | --- | --- | --- |
| `body_temperature` | °C (`degC`) | K | Existing +273.15; every second, first at 0.4 s. |
| `heart_rate` | bpm | `s^-1` | Existing /60; 60 s mean, first at 60 s. |
| `respiratory_rate` | `min^-1` | `s^-1` | Existing /60; 60 s mean, first at 77 s. |
| `bp_systolic`, `bp_diastolic` | mmHg | Pa | Existing `MMHG_TO_PA`; target-only paired point fixtures every 60 s. |
| `spo2` | % | `1` | Existing /100; every second, first at 0.2 s. |
| New `il6_pg_mL` | pg/mL | `kg/m^3` | Factor `1e-9`; new `infection_gfet` group, 60 s completed mean every minute. |
| Existing `il6_serum` | pg/mL | `kg/m^3` | Existing `1e-9`; configured specimen events with lab delay. |
| New `consciousness_level` | enum | `ACVPU` | No numeric conversion; `ALERT`, `CONFUSION`, `VOICE`, `PAIN`, `UNRESPONSIVE` only. |
| New `supplemental_o2` | boolean | boolean | No conversion. |
| New `post_ared_exercise_window` | boolean | boolean | No conversion. |
| Existing EBV/VZV channels | boolean | boolean | Paired saliva specimen events with lab delay. |

Group the three new state channels in `infection_context`, publishing point fixtures every 60 s beginning at 60 s. This is a configured-state heartbeat, not a new consciousness test every minute. Default states are constant. To support non-default scoring tests without changing the wire contract later, allow configured affected states to take effect at `affected_at_s`; before then, use healthy states. The default example uses `ALERT`, false, false at both stages.

Define `FREQUENCIES` for the two new groups before registry construction. GFET metadata must say synthetic concentration mean, no electrical waveform; use `raw_acquisition_hz=None`. State group has no raw acquisition rate or collection window. Both reference frequency-table row 3, and both are non-lab.

Use target-specific rule replacement for BP, serum IL-6 and saliva PCR, following the EVA owner-rule pattern. Target BP repeats every 60 s; this is a synthetic demo override, not an assertion of minute cuff testing. Serum/saliva events come from the scenario settings; non-target owners keep existing rules and results. Empty specimen-event lists produce no later specimen results, but retain startup references. Reject conflicting target BP/assay overrides rather than silently discarding explicit user settings.

With the default timings, the first fully affected HR and GFET windows end at 1860 s, and the first fully affected respiratory window ends at 1877 s. Temperature/SpO₂ are point measurements and settle on their respective first ticks after 1800 s. A minute-spaced backend snapshot at 1920 s therefore has fully affected vitals, even before the 1980 s lab results arrive.

### Preserve the four-field body while adding a validated enum

Extend simulator `Reading.value`, physiology/context value aliases and `PreviewEntry.source_value` to admit the five ACVPU literals. Add per-channel value-kind/allowed-values metadata, so numeric channels still reject strings and boolean channels still reject 0/1 or text. Use strict validation before Pydantic coercion where necessary. Merely adding unrestricted `str` to the shared union would weaken every channel's contract.

In `_publish()` and preview source conversion, bypass conversion for enum and boolean kinds; apply numeric conversion only to validated numbers. Update dictionary `value_schema` and enum metadata. Serialization and delivery must retain this body:

```json
{
  "channel": "consciousness_level",
  "value": "ALERT",
  "unit": "ACVPU",
  "measured_at": "2026-11-14T00:00:00Z"
}
```

Update backend `ChannelInfo`, channel constructors, `evaluate_reading()`, serializer input/output types, assessment types and API casts for the same restricted enum. Validate the allowed values specifically for `consciousness_level` and grade it as contextual/unspecified at the single-reading level; composite scoring owns its clinical contribution. The existing database value is JSONField and can store strings, so no schema migration is expected. Review any frontend numeric formatting and SSE consumers so they render `ALERT` instead of attempting arithmetic.

Use a shared value type and explicit typed numeric accessor in core assessment; avoid calling `float()` on arbitrary enum values after widening the mapping. Existing numeric and boolean channel behavior and four-field request shape must remain compatible.

## 6. Configuration and all-channel startup

Add optional `Settings.acute_infection_scenario: AcuteInfectionScenario | None = None`. Proposed `config/badscenario4.toml`:

```toml
seed = 42
speed = 10
duration_s = 3000
lab_delay_s = 120
# No enabled_channels: all available readings initialize once and follow schedules.
base_url = "http://127.0.0.1:8000"
data_route = "/api/readings/"

[environment]
gravity_g = 0

[[crew]]
id = "crew-1"
resting_hr_bpm = 72
sbp_mmhg = 118
dbp_mmhg = 78
rmssd_ms = 48

[acute_infection_scenario]
id = "FAULT_04_ACUTE_INFECTION"
owner_id = "crew-1"
onset_s = 600
affected_at_s = 1800
baseline_temp_c = 36.8
affected_temp_c = 38.7
baseline_respiratory_rate_br_min = 14
affected_respiratory_rate_br_min = 23
affected_heart_rate_bpm = 116
affected_sbp_mmhg = 96
baseline_spo2_pct = 97
affected_spo2_pct = 94
baseline_il6_pg_ml = 1.4
affected_il6_pg_ml = 8.4
reactivation_at_s = 1800
reactivated_virus = "EBV"
serum_il6_event_times_s = [1860]
saliva_pcr_event_times_s = [1860]
affected_consciousness_level = "ALERT"
affected_supplemental_o2 = false
affected_post_ared_exercise_window = false
```

Use the existing frozen configuration style. Validate finite values, a real owner, positive ramp duration, nonnegative onset/reactivation times, sorted unique positive event times and allowed enum values. Require rising temperature/HR/RR/IL-6 and falling systolic BP/SpO₂. Keep affected source ranges: temperature 38.4–39.2, HR 108–125, RR 22–25, SBP 94–99, IL-6 6.8–12.0. For this first example keep affected SpO₂ 94% by default and constrain configurable values to a documented range such as 91–95%; alternate scores must be calculated, not forced to 8. Validate target systolic pressure remains above profile diastolic pressure. A configurable virus may be EBV or VZV for the saliva group; supporting CMV would need its urine-specimen event configuration too.

Require baseline vital references in the existing NEWS2 zero-score bands for the demo. Reject simultaneous infection/SANS/hypercapnia/EVA scenarios using a single shared validation check rather than accumulating conflicting pairwise checks. Do not widen healthy profile limits to store diseased endpoints. Zero gravity is demo metadata, not the infection trigger.

The four new channels form `INFECTION_CHANNELS`. Default healthy runs retain 29 active channels; SANS retains 34, hypercapnia 30 and EVA 30. The full simulator registry becomes 40 entries. A single-crew infection run emits **33 startup readings: 28 crew and 5 environment**. New infection channels require the infection configuration and belong only to its target; other scenario-only channels are excluded. Explicit empty channel selection stays empty.

Initialize exact healthy target references, all four new channels, both serum/GFET IL-6 at 1.4 and all viral detections false. Preserve `sample_kind="startup_baseline"`, zero windows, no lab delay, communication delay and idempotent initialization. These are synthetic references, not completed specimens or observed consciousness exams. Export the scenario settings, owner, specimen schedules, state semantics and override metadata in the dictionary; update preview baselines and all relevant docs.

## 7. Backend scoring, readiness and expected output

### Seven-parameter NEWS2 and qSOFA

Extend the existing `news2()` with keyword-only `consciousness_level` and `supplemental_o2`, defaulting to `ALERT` and false for backward-compatible callers. Preserve the current rounding and five vital bands. Add oxygen contribution 2 when true, and consciousness contribution 3 for any allowed state other than `ALERT`. Calculate `max_parameter_score` over all seven components. The five vital components can contribute at most 15 points; adding oxygen (2) and consciousness (3) gives the full seven-component maximum of 20. Keep the documented 0–20 range and clarify that all seven inputs now contribute.

Return the existing `score` and `max_parameter_score` plus a named seven-component breakdown. In the default settled fixture:

| Component | Value | NEWS2 contribution |
| --- | --- | --- |
| Respiratory rate | 23 br/min | 2 |
| SpO₂, Scale 1 | 94% | 1 |
| Systolic pressure | 96 mmHg | 2 |
| Heart rate | 116 bpm | 2 |
| Core temperature | 38.7 °C | 1 |
| Supplemental oxygen | false | 0 |
| Consciousness | ALERT | 0 |
| **Total** | | **8** |

Add a pure backend `qsofa()` helper using the supplied thresholds: RR ≥22 contributes 1, SBP ≤100 contributes 1, and altered consciousness contributes 1. For this explicitly configured ACVPU fixture, map any non-ALERT state to altered consciousness; document that this is the chosen adaptation and that no GCS value is measured. Apply the qSOFA thresholds to converted physical values without silently reusing NEWS2's rounding. The example yields 2, and the adapted helper has range 0–3.

Extend the infection assessment result with `qsofa_score`, the NEWS2 component breakdown and explicit context/provenance fields. Retain the existing `news2_score` result key; label it as the aggregate score in presentation rather than creating a duplicate telemetry channel. Keep the current Finding 3 severity rule (critical at NEWS2 ≥7). qSOFA is additional context and must not silently become a new severity rule.

### GFET/serum source selection and context dependencies

Register all four new channels in the backend catalog. Do not gate acute vital scoring on delayed positive confirmation. Define readiness for Finding 3 using the five vital channels; IL-6 and viral observations supply additional triggers when available. Startup labs may be the latest known references until actual results arrive, but must never be described as a newly completed negative test.

Update `FINDINGS` dependencies to include all relevant trigger channels, including GFET, serum and the three state channels, so API ingestion recomputes the finding on those updates. Separate this dependency set from mandatory-input readiness: the current `has()` requires every listed channel, which would otherwise break healthy runs lacking the new scenario channels or suppress urgent vitals until assays arrive. Have `api.findings` fetch optional dependencies as well as required vitals.

Use the GFET channel when explicitly present, otherwise the existing serum channel. Record `il6_source_channel` in the finding result and apply the selected source's supplied provisional threshold. Do not average specimens, compare their disagreement as an error or let a delayed normal serum value replace a current GFET fixture. If neither exists, omit the IL-6 trigger and mark it unavailable; never fabricate a measured zero. Likewise, use available virus-specific results for positive triggers while recording which assays are unavailable. This requires optional confirmation inputs or a dedicated assessment wrapper around the existing core function; avoid passing fabricated values that appear as measured evidence in its result.

If all three explicit context channels are absent, preserve existing legacy assumptions (alert, room air, no post-ARED window) and label them as assumed. For partial explicit context, use supplied values and label each missing value's fallback independently. The complete scenario supplies all three at startup. This prevents sequential POST arrival from temporarily disabling vital alarms while avoiding claims that unobserved context was measured.

Pass explicit `post_ared_exercise_window` into the existing IL-6 trigger gate. The gate suppresses only the IL-6 trigger when true; fever, NEWS2 and viral evidence still apply. State-only changes must update the infection finding without waiting for another vital observation.

### Units, timing and integration

Use existing SI conversions: temperature K→°C, HR/RR `s^-1`→per minute, pressure Pa→mmHg, SpO₂ fraction→percent, and IL-6 `kg/m^3`→pg/mL. Default settled values include `body_temperature≈311.85 K`, `spo2≈0.94`, `heart_rate≈116/60 s^-1`, `respiratory_rate≈23/60 s^-1`, `bp_systolic≈96*MMHG_TO_PA` and GFET `8.4e-9 kg/m^3`.

Keep each reading independent; the receiver evaluates from the latest observations. The API currently recomputes on arrival rather than using an atomic seven-parameter snapshot, so intermediate scores during a ramp or batch can differ. Test the stable settled state after all relevant readings have arrived, and verify critical severity can occur before confirmatory assay delivery. Preserve acquisition timestamps and normal laboratory/communication delay.

Use an isolated backend test database. The current receiver stores one astronaut's readings by channel and does not isolate owners/runs. Simulator two-crew tests must verify target isolation, but real HTTP demonstration uses one crew. Run-scoped history and freshness are separate receiver improvements; do not silently use records from previous demos in integration assertions.

Expected settled result: NEWS2 8, max component 2, qSOFA 2, `status="critical"`, IL-6 source GFET at 8.4, EBV positive after its result becomes available, and explicit alert/room-air/non-ARED context. Preserve the existing backend medical-kit action text; showing qSOFA and confirmation alongside it is required, but automated medication selection or treatment execution is outside the simulator. Exact wording matching the source's example is a separate presentation change.

Other findings may also react to these vitals. Do not assert that only the infection card changes when all available readings are supplied.

## 8. Suggested implementation order and verification

1. Add strict value-kind/ACVPU support across simulator, preview, backend catalog, serializer and SSE types. Test the four-field contract and rejection of invalid enum/numeric/boolean combinations before adding scenario behavior.
2. Add `AcuteInfectionScenario`, shared active-fault validation and pure time-based references/context/viral helpers. Test exact latent endpoints, holds and owner isolation.
3. Integrate vitals inside their existing window/beat models. Add GFET minute means, explicit context heartbeats and target BP/specimen schedule replacement.
4. Add all-channel startup, effective-channel gating, dictionary/preview metadata and `config/badscenario4.toml` with no whitelist. Update channel catalog, model assumptions, frequency mapping and backend contract.
5. Extend NEWS2, add qSOFA, update infection result typing and implement explicit context/optional-confirmation readiness and source selection. Update dependency-driven API recomputation and any frontend enum/score rendering.
6. Add deterministic simulator tests plus direct backend and isolated HTTP/SSE tests. Document `uv run imitacija --config config/badscenario4.toml --preview` and normal delivery to the existing receiver.

Required tests:

- Exactly 33 startup readings for the single-crew demo, one per available channel, with 28 crew and 5 environment entries. Healthy target values, all context fields and negative viral fixtures are correct; initialization cannot duplicate them. Empty selection stays empty.
- Latent baselines through onset, correct midpoint progression and exact endpoint references at 1800 s. Window outputs straddling onset contain both baseline and affected samples; fully affected windows occur at the times in section 5.
- Settled noisy vitals produce the seven NEWS2 components `2,1,2,2,1,0,0`, total 8, max 2, and qSOFA 2. Test score boundaries and the existing rounding convention separately, including oxygen true and every non-ALERT state. With the same vitals, adding oxygen and altered consciousness yields NEWS2 13 and qSOFA 3.
- Infection severity tests retain existing boundaries: nominal healthy state, warning with fever/IL-6/virus or NEWS2 5–6, critical at NEWS2 ≥7, and urgent review for any component scoring 3. Post-ARED suppresses only its IL-6 trigger.
- Serum/PCR use collection-time values and become available at collection + lab delay + communication delay. A specimen collected before reactivation remains negative even if delivered afterward. No scheduled serum/PCR results occur with empty event lists.
- Critical vitals can generate a finding before confirmations arrive, and with optional assay channels disabled. Missing confirmations/context are visibly distinguished from measured negative/normal values. Legacy healthy/SANS/hypercapnia/EVA payloads still evaluate using documented fallback context.
- GFET and serum remain distinct channels; the default assay fixtures share the configured latent concentration without implying calibration. Source selection is deterministic and delayed serum cannot override present GFET context. Correct concentration/temperature/pressure/rate conversions are exercised through actual received payloads.
- Enum serialization preserves exact strings and rejects unknown/lowercase states, numeric strings on numerical channels, strings/numbers on boolean channels and enum values on unrelated channels. Preview/dictionary/SSE display the state without numeric conversion or serialization failure.
- Target-specific BP and specimen overrides produce no duplicates and leave other owners' values/schedules unchanged. All new infection channels belong only to the target. Ordinary cabin signals remain single environment streams.
- Invalid timing, owners, target ranges, non-finite values, enum values, duplicate specimen events, conflicting overrides and simultaneous faults fail clearly. Other scenario regression suites pass.
- Mock delivery checks all startup channels, enum/boolean/numeric bodies, preserved timestamps, owners, sample kinds and retry identity. Direct core tests verify result types and score fields; API tests verify acceptance, state-triggered recomputation, lab updates and critical Finding 3 SSE output from a clean baseline.

Run all simulator checks after implementation: `uv run --frozen pytest`, `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .`, and `uv run --frozen mypy`. Run backend core/API tests and the repository's formatting/type checks for changed backend files. This planning-only change needs document/configuration and scoring-example verification, not a full application test run.

## 9. Completion criteria

The scenario is complete when it starts with all available healthy references, produces the configured coupled vital/molecular progression for its target, emits correctly timed specimen and explicit state observations, and retains the healthy and previous-scenario regressions.

Backend completion requires seven-parameter NEWS2, adapted qSOFA, validated state transport, declared IL-6 source selection, optional-confirmation readiness, and an HTTP/SSE demonstration of NEWS2 8 / qSOFA 2 / critical with the supplied example. Startup assumptions and delayed confirmations must remain identifiable. Exact treatment wording and recovery are separate from this implementation.

## Implementation status

Implemented `AcuteInfectionScenario`, the default config, time-based coupled
physiology, owner-specific BP/specimen rules, all 33 startup readings, GFET
concentration means and explicit context heartbeats. Enum transport is validated
through simulator, preview, receiver and SSE. The backend computes seven-component
NEWS2 and adapted qSOFA, records context provenance and IL-6 source, and evaluates
critical vitals without waiting for optional confirmations. The demo displays
NEWS2/qSOFA and source context. Existing treatment wording remains unchanged.
