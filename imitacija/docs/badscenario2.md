# Scenario 2 implementation plan: acute cabin hypercapnia & mild hypoxia

**Scenario:** `FAULT_02_HYPERCAPNIA_CO2` — Finding 4.

**Source:** [Unhealthy simulation specification](hydrogfn_unhealthy_simulation_specification%20%281%29.md), Scenario 2.

**Pattern:** [Scenario 1 implementation plan](../badscenario1.md). Paths below are relative to the simulator project root unless stated otherwise.

**Status:** Implementation plan only. Scenario 1 is already implemented; extend its configuration, scenario helpers, channel-selection and startup patterns. Numerical endpoints and the 90-second cabin rise come from the supplied specification. Response delays, interpolation and EEG fixtures below are engineering assumptions for a reproducible demonstration, not a validated gas-exchange or clinical progression model.

## 1. What can be reused, and what is missing

Four of the five required signals already exist. Reuse their identifiers and schedules; add only the missing `eeg_cfe_ratio` channel.

| Area | Existing code | Planned use |
| --- | --- | --- |
| Validated configuration | `models.Settings`, `AstronautProfile`, `Environment`, `SansScenario` | Add optional `HypercapniaScenario` using the same frozen validation style. |
| Time-based scenarios | `scenarios.smoothstep()`, existing SANS helpers | Add a shared cabin trajectory and delayed physiological references. Preserve SANS helpers. |
| Cabin CO₂ | `physiology.environment_values("co2", ...)`, `ambient_ppco2` | Replace the healthy cabin curve only when this scenario is active. Existing source and wire units are both Pa. |
| Heart and respiration | `heart_rate()`, `crew_values("heart" / "respiration", ...)` | Apply changing references inside the existing completed-window calculations. |
| Oxygenation | `crew_values("spo2", ...)` | Use the scenario's 97 → 92% reference with existing small activity/noise terms. |
| HRV | `rmssd()` | Use the same affected heart-rate function for beat timing; add no independent HRV target reduction. |
| Acquisition and startup | `scheduler.rules()`, `Scheduler.acquire()`, `Scheduler.initialize()` | Preserve existing schedules and add a minute EEG-fixture group. |
| Metadata and channel selection | `registry.effective_channels()`, `dictionary()`, `frequency.FREQUENCIES` | Gate the new channel, describe synthetic EEG and export scenario settings. |
| Transport and preview | `Scheduler._publish()`, `Delivery`, `PreviewState` | Reuse four-field readings, source-unit display and provenance headers. |
| Finding 4 | `../backend/packages/hydrograph-core/src/hydrograph_core/findings.py::hypoxia_co2_2_2()` | Convert wire units and evaluate aligned cabin/crew observations. |

There are two integration gaps. EEG/CFE is currently excluded from the registry. Also, the backend API still exposes only a health endpoint: there is no telemetry receiver or five-second Finding 4 evaluation loop. The existing core function returns **WARNING**, not CRITICAL, for the specification's 4.8 mmHg / 92% example. Section 7 makes that discrepancy and the separate backend work explicit.

## 2. Exact signals to change

| Specification signal | Simulator channel | Healthy reference | Affected reference | Implementation |
| --- | --- | --- | --- | --- |
| `cabin_ppco2_mmHg` | `ambient_ppco2` | 2.2 mmHg | 4.8 mmHg | One shared cabin curve; convert mmHg to Pa before returning from `environment_values()`. |
| `heart_rate` | `heart_rate` | 72 bpm in demo profile | 104 bpm | Change the resting reference inside `heart_rate()`; retain activity, circadian and seeded noise terms. |
| `respiratory_rate` | `respiratory_rate` | 14 br/min | 24 br/min | Change the reference at every sample in the existing 60-second mean. |
| `spo2` | `spo2` | 97% | 92% | Scenario-specific baseline/reference plus the existing small activity/noise terms. |
| `eeg_cfe_ratio` | New `eeg_cfe_ratio` | 0.58 | 1.28 | Deterministic synthetic theta/alpha ratio fixture, emitted as completed minute means. |

The normal healthy simulator uses approximately 98.1% for SpO₂ and 250 Pa for cabin CO₂; those are not the specification's 97% and 2.2 mmHg. Override these references for this scenario, including startup, without changing ordinary healthy runs. HR and respiratory scheduled results retain normal variation; the table describes latent references, not exact equality for every published sample.

Use `units.MMHG_TO_PA = 133.322387415`: 2.2 mmHg becomes `293.309252313 Pa`, and 4.8 mmHg becomes `639.947459592 Pa`. The existing `ambient_ppco2` registry factor stays 1; do not convert a second time in `_publish()`. Optional ppm display must use `units.co2_ppm(value_pa, environment.pressure_pa)` rather than a fixed mmHg-to-ppm factor.

Treat the oxygenation and EEG changes as correlated scenario fixtures. The code does not model cabin oxygen depletion, alveolar gas exchange, individual CO₂ sensitivity or raw EEG. Do not invent a quantitative physiological law connecting 4.8 mmHg to 92% saturation.

This is a shared-cabin fault. The current simulator has one environment and no crew-to-module assignments, so all configured crew are exposed to the same cabin trajectory. Emit cabin readings once under `environment.id`; emit affected physiology once per crew member. An unaffected astronaut in a separate module requires a future compartment model. The demo contains one astronaut.

No direct offsets are specified for blood pressure, temperature, SANS signals, biochemical measurements, consciousness or supplemental oxygen. Do not synthesize headache reports, treatment actions, scrubber repair or recovery.

## 3. Proposed reproducible timeline

Use a 600-second demonstration with 120 seconds of baseline, the specified 90-second cabin rise, and enough plateau time for completed windows. All times are elapsed simulation seconds.

| Time | Behavior |
| --- | --- |
| 0–120 s | Healthy scenario references: CO₂ 2.2 mmHg, HR 72, RR 14, SpO₂ 97%, CFE 0.58. |
| 120–210 s | Cabin CO₂ smoothly rises to 4.8 mmHg over exactly 90 seconds. |
| 130–220 s | HR and respiratory references rise to 104 bpm and 24 br/min. |
| 150–240 s | SpO₂ reference falls to 92%; CFE rises to 1.28. Compensation begins before oxygenation declines. |
| 240–600 s | Hold all affected references. Existing windowed channels finish settling on their individual schedules. |

The 10-second compensation delay and 30-second oxygenation/cognitive delay are configurable demonstration assumptions. The source specifies ordering but gives no response-delay model. Use one onset and ramp duration with shifted copies of the same progression:

```python
# Illustrative formulas; validated config supplies the constants.
p = smoothstep(t, onset_s, onset_s + ramp_duration_s)
v = smoothstep(t, onset_s + compensation_delay_s,
               onset_s + compensation_delay_s + ramp_duration_s)
o = smoothstep(t, onset_s + oxygenation_delay_s,
               onset_s + oxygenation_delay_s + ramp_duration_s)

cabin_mmhg = 2.2 + (4.8 - 2.2) * p
hr_reference = profile.resting_hr_bpm + (104 - profile.resting_hr_bpm) * v
rr_reference = 14 + (24 - 14) * v
spo2_reference = 97 + (92 - 97) * o
cfe_reference = 0.58 + (1.28 - 0.58) * o
```

Suggested helpers in the existing `scenarios.py`:

- `hypercapnia_cabin_mmhg(t, scenario)`: cabin partial pressure in the scenario's configuration units.
- `hypercapnia_references(t, profile, scenario)`: HR, RR, SpO₂ and CFE references from the shared progression.
- `hypercapnia_eeg_values(t, scenario, *, startup=False)`: a baseline fixture or completed 60-second CFE mean.

Evaluate solely from elapsed time and configuration. Skipping polls, disabling channels or changing playback speed must not advance or reset the fault. No state transition may depend on whether the CO₂ channel was actually published.

For the default deterministic cabin curve, the first scheduled CO₂ reading strictly above 3.0 mmHg is at 154 s. A backend loop anchored at 5, 10, 15, … seconds can observe it at 155 s with zero communication delay. This is an expected cabin-trigger time, not a promise about HTTP arrival time or the first warning from other inputs.

## 4. Apply the changes inside the existing signal model

Add optional, clearly named hypercapnia context to `crew_values()`, `environment_values()`, `heart_rate()`, `rmssd()` and startup handling. Preserve existing SANS calls and defaults; preferably add new arguments as keyword-only parameters so the existing positional `scenario` argument still means SANS.

**Heart rate:** Replace only the resting reference in `heart_rate()` when hypercapnia is configured. `crew_values("heart")` must continue to average its twelve five-second midpoint samples over the preceding 60 seconds, evaluating the new reference at each sample time. Do not overwrite the final minute average with the instantaneous endpoint.

**Respiration:** Extract a small instantaneous respiratory helper if useful. Use the scenario reference plus the existing `9 * activity(t)` and `0.35 * noise(...)` terms at each of the same twelve midpoint samples. Preserve the completed-window guard.

**SpO₂:** Substitute the scenario reference for the hard-coded healthy 98.1 term. Retain `-0.25 * activity(t) + 0.25 * noise(...)`. The default resting plateau is therefore approximately 92%, within ±0.25 percentage points. Scenario startup emits the declared 97% reference as a fixture; scheduled measurements include model variation.

**HRV consistency:** Pass hypercapnia context into the `heart_rate(beat, ...)` call inside `rmssd()`. Keep the existing RMSSD target reference and pulse extraction. The source specifies no separate HRV reduction for this scenario. Published RMSSD may change slightly because mean beat spacing and quantization change; do not assert bitwise HRV equality in an affected run. No-scenario and SANS-only results must remain unchanged.

**CFE:** For the first version, average 60 one-second midpoint samples of the synthetic ratio reference over a completed minute. This is a mean of a fixture ratio, not a ratio calculated from EEG band powers. Frequency-table row 5 describes 250 Hz raw EEG and spectral processing; this implementation does not satisfy that raw acquisition requirement. Set `raw_acquisition_hz=None` and explicitly document the adaptation. Raw waveforms, FFT and artifact rejection are separate work.

## 5. Channels, units and acquisition rules

| Channel | Source unit | Wire unit | Factor | Schedule / collection |
| --- | --- | --- | --- | --- |
| `ambient_ppco2` | Pa | Pa | 1 | Existing `co2`: every 1 s, first scheduled sample at 1 s. |
| `heart_rate` | `bpm` | `s^-1` | 1/60 | Existing `heart`: 60 s mean, first at 60 s, then every 60 s. |
| `respiratory_rate` | `min^-1` | `s^-1` | 1/60 | Existing `respiration`: 60 s mean, first at 77 s, then every 60 s. |
| `spo2` | % | 1 | 0.01 | Existing `spo2`: every 1 s, first at 0.2 s. |
| `eeg_cfe_ratio` | 1 | 1 | 1 | New `eeg_cfe`: completed 60 s mean, first at 60 s, then every 60 s. |

Add `FREQUENCIES["eeg_cfe"]` before registering the new channel, with interval/window 60 seconds, row 5 and an explicit synthetic-fixture description. Register `eeg_cfe_ratio` with `scope="crew"`, `lab=False`, and add `Rule("eeg_cfe", phase=60, interval=60)` only for this scenario. The demonstration assumes continuous synthetic EEG monitoring from startup through run end.

Route the new group to the scenario helper; pass hypercapnia settings through existing crew/environment acquisition paths. Apply the same context when initializing the environment so its startup CO₂ matches later baseline measurements.

With default timings, the first fully affected HR window is at 300 s, the first fully affected respiratory window at 317 s, and the first fully affected CFE window at 300 s. Do not force these independent streams into a simultaneous five-field payload. Five-second acute checks belong to the backend; they are not a reason to change the existing acquisition rates.

Extend `effective_channels()` with a separate hypercapnia-only set containing `eeg_cfe_ratio`. Healthy defaults retain 29 enabled channels; SANS-only defaults retain 34; hypercapnia-only defaults enable 30. The full registry becomes 35 entries. Explicit empty channel selection stays empty. Explicit EEG selection without hypercapnia configuration raises a clear validation error. Existing CO₂/vital channels remain usable in healthy runs.

Narrow `EXCLUDED` from `EEG/CFE/PVT` to raw EEG acquisition/spectral processing and PVT, retaining the distinction between a synthetic CFE fixture and a sensor model. Export the scenario configuration in `Dictionary`, and update `docs/channel_catalog.md`, `docs/frequency_mapping.md`, `docs/model_assumptions.md` and `docs/backend_contract.md`. Keep the original frequency table as the source requirement and explain the EEG adaptation in the mapping.

## 6. Configuration and startup behavior

Add `Settings.hypercapnia_scenario: HypercapniaScenario | None = None`. The following proposed `config/badscenario2.toml` becomes runnable only after implementation:

```toml
seed = 42
speed = 10
duration_s = 600
enabled_channels = [
  "ambient_ppco2", "heart_rate", "respiratory_rate", "spo2", "eeg_cfe_ratio",
]

[environment]
id = "iss_cabin"
gravity_g = 0
pressure_pa = 101325

[[crew]]
id = "crew-1"
resting_hr_bpm = 72
sbp_mmhg = 118
dbp_mmhg = 78
rmssd_ms = 48

[hypercapnia_scenario]
id = "FAULT_02_HYPERCAPNIA_CO2"
environment_id = "iss_cabin"
onset_s = 120
ramp_duration_s = 90
compensation_delay_s = 10
oxygenation_delay_s = 30
baseline_ppco2_mmhg = 2.2
affected_ppco2_mmhg = 4.8
baseline_respiratory_rate_br_min = 14
affected_respiratory_rate_br_min = 24
affected_heart_rate_bpm = 104
baseline_spo2_pct = 97
affected_spo2_pct = 92
baseline_cfe_ratio = 0.58
affected_cfe_ratio = 1.28
```

Validate finite values, nonnegative onset/delays, positive ramp duration, and `compensation_delay_s < oxygenation_delay_s`. Require `environment_id == settings.environment.id` and at least one crew member. Validate baseline CO₂ in the nominal band (positive and ≤3.0 mmHg), affected CO₂ within the supplied 3.5–6.0 range, affected HR within 96–112, affected RR within 22–26, baseline SpO₂ within 94–100 and affected SpO₂ within 91–93. Require rising HR/RR/CFE targets, falling SpO₂, positive CFE values and an affected CFE above 1.20. Check cabin partial pressure remains below total pressure after conversion.

Keep healthy `AstronautProfile` limits unchanged; disease targets belong to the scenario model. Do not require microgravity to activate a scrubber fault: gravity remains environment metadata. For this first implementation, reject simultaneous `sans_scenario` and `hypercapnia_scenario` configuration with a clear error; combined-fault physiology is outside this plan. Each scenario remains independently usable.

At initialization, emit one baseline per enabled owner/channel: cabin CO₂ 293.309252313 Pa under the environment owner; HR profile reference, RR 14, SpO₂ 97% and CFE 0.58 under each crew owner. Preserve `sample_kind="startup_baseline"`, `window_s=0`, communication delay and idempotent initialization. Windowed startup values are reference fixtures, not completed collections. Disabled channels must not generate readings, although the latent fault still affects enabled dependent channels.

## 7. Backend mapping and expected evaluation

Preserve the existing four-field body. A settled cabin reading is:

```json
{
  "channel": "ambient_ppco2",
  "value": 639.947459592,
  "unit": "Pa",
  "measured_at": "2026-11-14T00:05:00Z"
}
```

SpO₂ near 92% is sent near `0.92` with unit `1`; reference HR 104 and RR 24 correspond to `104 / 60` and `0.4` with wire unit `s^-1`, subject to the model/window variation above. CFE 1.28 remains dimensionless. Ownership and run provenance stay in existing headers, never in extra body fields.

At the receiver, verify units and map:

- `ambient_ppco2` → `ppco2_mmhg = value / MMHG_TO_PA`.
- `spo2` → `spo2_pct = 100 * value`.
- `respiratory_rate` → breaths/min via `60 * value`, then derive `respiratory_rate_rising` upstream.
- HR and CFE → contextual display; neither is an input to the current Finding 4 function.

The existing function requires a headache boolean, but the simulator has no symptom-report channel. Direct demo tests can explicitly supply `headache=False`, meaning no reported headache for this fixture. A real receiver should retain missing/reporting provenance; do not derive headache from cabin CO₂ or CFE. Do not turn elevated CFE into a sleep-deficiency diagnosis by fabricating sleep/PVT inputs.

For the direct core test, this call currently returns **WARNING** with scrubber/ventilation/relocation action text:

```python
findings.hypoxia_co2_2_2(
    spo2_pct=92.0,
    respiratory_rate_rising=True,
    ppco2_mmhg=4.8,
    headache=False,
)
```

Current semantics are CRITICAL only below 90% SpO₂; otherwise WARNING for SpO₂ below 94%, CO₂ above 3.0 mmHg, rising respiration or headache. Equality at 94% and 3.0 mmHg does not trigger those respective checks; 90% is warning, not critical. The respiratory trend can return false once RR plateaus without clearing the CO₂/oxygenation warning.

**Specification reconciliation:** Do not lower the scenario's 92% target below 90% just to manufacture a red alert, and do not silently alter the core thresholds while implementing simulator support. Track the specification's red severity as a separate backend-policy requirement. One concrete proposed rule is CRITICAL when `ppco2_mmhg > 3.0 and spo2_pct < 94.0`, in addition to the existing `<90%` rule; isolated CO₂ or mild oxygenation triggers remain warning. This joint rule is a proposed engineering interpretation, not a threshold defined by the source or current core. Its adoption requires a documented backend policy decision and dedicated boundary/regression tests. Until that decision is implemented, the honest expected result is nominal → warning, with the red-alert requirement outstanding.

For end-to-end evaluation, add a receiver and a five-second evaluator as a separate backend workstream:

1. Validate and deduplicate readings using the existing transport identity, preserve acquisition timestamps, and associate the shared environment with each crew member in the run.
2. Keep the latest scheduled CO₂ and SpO₂ values per run/owner. Join by acquisition time, not arrival order. With zero demo delay, use a proposed maximum age of 5 seconds for each fast channel and maximum timestamp skew of 2 seconds; mark stale/missing input explicitly rather than substituting nominal values. Document these as receiver fixture policies and account for configured communication delay in integration tests.
3. Derive rising respiration from consecutive scheduled 60-second estimates: a proposed demo policy is an increase of at least 2 br/min over consecutive windows, with the latest estimate no older than 90 seconds. Require both samples, reject gaps/out-of-order updates, and retain unknown trend when unavailable. Startup references do not constitute a preceding completed window. Missing RR must not suppress a CO₂/SpO₂ alert; the adapter can supply false for unavailable trend while recording its unknown provenance.
4. Evaluate every five seconds of simulation time in deterministic integration tests, using only observations available by that tick. Do not allow future or delayed observations to leak into an earlier evaluation. Surface data unavailability instead of emitting a nominal finding when required fast inputs are missing.
5. Preserve the current action text and report the actual core severity. A dashboard's red badge and dynamic 4.8/92 wording require the separate severity/presentation integration; JSON preview alone does not demonstrate an alert.

## 8. Suggested implementation order and verification

1. Add `HypercapniaScenario`, settings validation and pure progression helpers. Test source endpoints, 90-second cabin rise, response ordering and long plateau behavior.
2. Apply scenario references inside cabin, heart, respiration, SpO₂ and HRV beat-timing paths. Preserve healthy and SANS-only behavior at equal model times.
3. Add CFE frequency/registry entries, effective-channel gating and scheduler routing. Include scenario startup values for both environment and crew.
4. Export scenario configuration and update documentation/preview reference metadata where applicable. Check that preview labels cabin CO₂ as Pa and does not display the old baseline as the scenario reference.
5. Add `config/badscenario2.toml` and `tests/test_hypercapnia.py`, following the existing `tests/test_sans.py` sink and `ManualClock` patterns. Document execution from the simulator root: `uv run imitacija --config config/badscenario2.toml --preview`.
6. Test the actual backend core function in its own test environment using converted scenario values. Record the warning-versus-red mismatch explicitly. Add backend ingestion/evaluation and any approved severity-policy change separately if end-to-end source compliance is in scope.

Required scenario tests:

- Five startup observations for the single-crew demo, all at zero with zero collection windows; repeated initialization does not duplicate them. Source/wire values and owners are correct.
- Exact latent references before onset and after completion; CO₂ reaches 4.8 mmHg at 210 s, compensation reaches its references at 220 s, oxygenation/CFE at 240 s. Before the delayed onset, each reference remains at baseline.
- Scheduled cabin samples use the existing 1 Hz cadence and first exceed 3.0 mmHg at 154 s. No double conversion occurs. Pressure-dependent ppm conversion still works.
- HR/RR/CFE windows crossing onset contain both baseline and affected samples. First scheduled HR/CFE at 60 s and RR at 77 s; negative-time windows are never calculated. Fully affected windows occur at the times in section 5.
- Settled resting HR is within ±4 bpm of 104, RR within ±0.35 br/min of 24, SpO₂ within ±0.25 percentage points of 92, and deterministic CFE equals 1.28 within numerical tolerance. Test exact latent targets separately from these observation tolerances.
- A two-crew run produces one shared cabin stream and two affected crew streams; owner IDs and sensor IDs stay correct. Disabling CO₂ output does not disable the physiological fault.
- Default healthy and SANS-only configurations retain their channel sets and values; existing `tests/test_sans.py` passes unchanged. Unrelated channel outputs remain equal at equal model times; HRV has unchanged target but uses affected beat timing.
- Invalid ordering, non-finite values, wrong environment, missing crew, invalid target bands, impossible partial pressure and simultaneous scenario configurations fail clearly. Empty enabled channels produce no observations; EEG without scenario configuration is rejected.
- Deterministic `ManualClock` runs reproduce values and timestamps; real-clock acceleration may coalesce acquisitions, so message-count equality across CPU loads is not required.
- Mock delivery preserves the four-field body, SI conversions, startup/scheduled headers, environment/crew ownership and acquisition timestamps under delay/retry.
- Direct Finding 4 tests assert nominal baseline, warning at 4.8/92, and exact threshold semantics. Keep any proposed joint-critical policy tests in the separate backend change, including isolated-trigger regressions.
- If the receiver is implemented, test independent stream phases, five-second checks, stale/missing readings, delayed/reordered delivery, duplicate retries, trend availability and one shared cabin association per crew. Verify an alert without waiting for minute HR/RR/CFE windows.

After implementation, run the existing simulator checks: `uv run --frozen pytest`, `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .`, and `uv run --frozen mypy`. Run backend core/API checks separately for any backend changes. This planning-only change does not require running the simulator test suite.

## 9. Completion criteria

The simulator portion is complete when explicit configuration produces the specified 90-second shared-cabin CO₂ rise, the ordered and correlated HR/RR/SpO₂/CFE changes, correct completed windows and source-to-wire conversions, and a reproducible preview without regressing healthy or SANS behavior.

Direct integration is complete when converted readings produce the current Finding 4 nominal → warning behavior and the mismatch with the source's red alert is documented. Full source-output compliance additionally requires a resolved backend severity policy, telemetry receiver, five-second evaluation and alert presentation. These are separate acceptance items; do not mark the expected Critical Red Alert complete based solely on simulator output.

## Implementation status

The simulator portion is implemented: `HypercapniaScenario` configuration,
time-based shared cabin/physiological trajectories, HRV beat-timing integration,
synthetic minute CFE fixtures, startup values, channel selection and preview
references. Run from the simulator root:

```sh
uv run imitacija --config config/badscenario2.toml --preview
```

`tests/test_hypercapnia.py` covers deterministic progression, windows, units,
startup, ownership, invalid configuration, channel gating, mock HTTP delivery,
preview baselines and direct evaluation against the backend core when its checkout
is available. The backend still returns WARNING for the source's 4.8 mmHg / 92%
example. HTTP ingestion, five-second backend evaluation and the red-alert policy
remain the separate prerequisites described in section 7.
