# Scenario 1 implementation plan: gradual SANS / cephalic fluid shift

**Scenario:** `FAULT_01_SANS_CEPHALIC` — Finding 9.

**Current demo timing:** `config/badscenario1.toml` now runs at speed 1, with
onset at 10 s, warning endpoint at 45 s, critical ramp from 60–90 s, and eye
screens at 60/120 s. Completed-minute strain measurements first warn at 60 s
and become critical at 120 s. The original implementation plan and longer
timeline below are historical; the shared `SansScenario` defaults still retain
that longer timeline. Only the shipped scenario 1 config is shortened.

**Source:** [Unhealthy simulation specification, Scenario 1](docs/hydrogfn_unhealthy_simulation_specification%20%281%29.md#scenario-1-spaceflight-associated-neuro-ocular-syndrome-sans--cephalic-fluid-shift).

**Status:** Implementation plan only. The proposed configuration, functions and new channels below do not exist yet. Numerical targets from the supplied document are treated as simulation requirements. Timing, interpolation and additional fixture values below are engineering assumptions, not a validated clinical progression model.

## 1. What can be reused, and what is missing

The simulator can already publish independent measurements, calculate completed windows, convert source units to wire units, preview JSON and deliver readings. However, only `hrv_rmssd` from this scenario currently exists in its channel registry. Jugular strain, hydrogel resistance, ICP indicators and visual tests are explicitly excluded by `registry.EXCLUDED`.

| Area | Existing code | Planned use |
| --- | --- | --- |
| Validated configuration | `models.Settings`, `AstronautProfile`, `Environment` | Add optional scenario settings; retain a healthy starting profile. |
| Healthy physiology | `physiology.crew_values()`, `heart_rate()`, `rmssd()` | Apply scenario changes to the selected astronaut while preserving the existing signal calculations. |
| Time and schedules | `scheduler.rules()`, `Rule`, `Scheduler.acquire()` | Add a minute-based cephalic group and sparse eye-screen events. |
| Startup fixtures | `startup_crew_values()`, `Scheduler.initialize()` | Emit healthy references once at time zero for enabled new channels. |
| Metadata and units | `registry.Channel`, `CHANNELS`, `dictionary()`, `frequency.FREQUENCIES` | Register all new channels, units, windows and schedules. |
| Transmission | `Scheduler._publish()`, `Delivery`, `PreviewState` | Reuse four-field readings, provenance headers and normal communication delays. |
| Finding 9 evaluation | `../backend/packages/hydrograph-core/src/hydrograph_core/findings.py::sans_fluid_shift_1_3()` | Evaluate jugular strain after converting back to percentage units. |

The backend finding function exists, but the current Django API only exposes a health endpoint; `api/views.py`, `api/urls.py` and `api/serializers.py` do not implement telemetry ingestion. Preview and direct evaluator tests can be completed first. End-to-end HTTP alerts additionally require a receiver and evaluator integration.

## 2. Exact signals to change

Use the source document's strain values as percentage numbers: `0.65` means `0.65%`. Do not reinterpret `1.55%` as a 1.55% increase over the initial 0.65% reading. The baseline is the neck-patch reference strain, not a second percentage-change calculation.

| Signal | Healthy start | Warning endpoint | Critical endpoint | Implementation |
| --- | --- | --- | --- | --- |
| `jugular_strain_pct` | 0.65% | 1.55% | 2.05% | New continuous latent strain function with gradual ramps. |
| `delta_R_over_R0` | 0.10075 | 0.24025 | 0.31775 | Always derive from the same strain: `15.5 * strain_pct / 100`. Never generate independently. |
| `hrv_rmssd` | 48 ms reference | Approximately 36 ms at rest | Hold the same 36 ms reference | Modify the target inside `rmssd()` before generating NN intervals. The source gives no further critical HRV reduction. |
| `icp_risk_indicator_mmHg` | 10.0 mmHg fixture assumption | 16.2 mmHg from source | 19.0 mmHg fixture assumption | New explicitly synthetic indicator driven by the same progression. No strain-to-ICP calibration is provided by the source. |
| `visual_acuity_logmar` | 0.00 reference | +0.20 when an eye screen occurs after progression | Hold +0.20 on later screens | New sparse screen-result channel. |
| `amsler_grid_distortion` | false reference | true on a screen after reaching the warning endpoint | true on later screens | New boolean screen-result channel. |

The 10.0 and 19.0 mmHg indicator fixtures must remain configurable and identified as assumptions in the dictionary. They are not measured ICP and do not drive the existing backend severity function.

No disease offsets are specified for heart rate, blood pressure, SpO2, temperature, IL-6 or the other channels in Scenario 1. They continue to follow their existing healthy models. If included, the source's resting profile values can be set with existing fields: `resting_hr_bpm = 72`, `sbp_mmhg = 118`, `dbp_mmhg = 78`, `rmssd_ms = 48`. These are references; scheduled values still have normal model variation. Reproducing every nominal value listed elsewhere in the source document is outside this scenario's scope.

Use existing `environment.gravity_g = 0`. The string `0G_MICROGRAVITY` is not a supported environment mode. Gravity is currently configuration metadata, not a fluid-shift trigger; scenario activation must be explicit.

## 3. Proposed reproducible timeline

For an integration demonstration, use the following compressed timeline. The document does not specify onset duration; these times exercise healthy, warning and critical behavior within one run. They do not assert that visual pathology develops within minutes. All times are elapsed simulation seconds.

| Time | Behavior |
| --- | --- |
| 0–600 s | Healthy baseline. Strain 0.65%; RMSSD reference 48 ms. |
| 600–1800 s | Smooth deterioration toward strain 1.55%, RMSSD reference 36 ms, indicator 16.2 mmHg. |
| 1800–2400 s | Hold the warning endpoint. Simulated eye screen at 1860 s reports +0.20 and distortion. |
| 2400–3600 s | Optional second ramp to strain 2.05% and indicator 19.0 mmHg. HRV reference remains 36 ms. |
| 3600–4200 s | Hold the critical endpoint. Repeat eye screen at 3660 s. |

A warning-only variant omits the second ramp and remains at 1.55%. Recovery or treatment response is not specified by this source and needs a separate trajectory before it can be simulated.

Add pure helpers in a proposed `src/imitacija/scenarios.py`:

```python
def smoothstep(t: float, start: float, end: float) -> float:
    u = min(1.0, max(0.0, (t - start) / (end - start)))
    return u * u * (3.0 - 2.0 * u)

# Illustrative formulas; validated config supplies these constants.
w = smoothstep(t, 600, 1800)
c = smoothstep(t, 2400, 3600) if escalate_to_critical else 0.0

strain_pct = 0.65 + (1.55 - 0.65) * w + (2.05 - 1.55) * c
resistance_ratio = 15.5 * strain_pct / 100
rmssd_reference_ms = 48 + (36 - 48) * w
icp_fixture_mmhg = 10 + (16.2 - 10) * w + (19 - 16.2) * c
logmar_fixture = 0.20 * w  # Only emitted at configured screen events.
distortion_fixture = t >= 1800  # Explicit fixture policy, observed only on a screen.
```

Suggested helper responsibilities:

- `sans_state(t, scenario)`: return strain, resistance ratio and indicator from one shared progression.
- `sans_rmssd_reference(t, profile, scenario)`: return the profile reference before onset, then smoothly reach 36 ms; return the original reference for unaffected astronauts.
- `sans_eye_screen_values(t, scenario)`: return the paired LogMAR and Amsler fixture at an actual configured screen event.

Keep these calculations dependent on elapsed time, configuration and owner. Do not increment severity per emitted sample: skipping a poll or changing playback speed must not change the underlying trajectory. The first version can use deterministic strain without added noise so threshold tests are predictable. Existing physiological noise remains seeded.

## 4. Apply HRV changes inside the existing signal model

In `physiology.rmssd()`, the current per-beat target is:

```python
target = profile.rmssd_ms / 1000 * (1 - 0.5 * activity(beat))
```

Replace the profile reference with `sans_rmssd_reference(beat, profile, scenario)` when this scenario applies. Pass optional scenario context through `crew_values()` into `rmssd()`, preserving the existing behavior when no scenario applies.

Evaluate the new reference at each `beat` time inside the 60-second window. Reuse the existing pulse generation, peak localization and RMSSD calculation. This preserves a partially affected window when onset falls inside it. Multiplying only the final published HRV reading would bypass that calculation.

The 48 → 36 ms transition is the latent resting reference. Published RMSSD can differ because of beat quantization, exercise and window boundaries. Test its resting trend and a calibrated tolerance; do not require every scheduled result to equal exactly 36 ms. `exercise_test_days` controls lactate sessions, not the daily `activity()` waveform, so emptying it does not disable exercise physiology.

## 5. New channels, units and acquisition rules

Add groups `cephalic` and `eye_screen` to `FREQUENCIES` before registering their channels; the registry indexes this mapping when constructing `CHANNELS`.

| Channel identifier | Source unit | Wire unit | Conversion factor | Group / publication |
| --- | --- | --- | --- | --- |
| `jugular_strain_pct` | `%` | `1` | 0.01 | `cephalic`: completed 60 s mean, every 60 s |
| `delta_R_over_R0` | `1` | `1` | 1 | Same cephalic window and timestamp |
| `icp_risk_indicator_mmHg` | `mmHg` | `Pa` | `units.MMHG_TO_PA` | Same cephalic window and timestamp; synthetic proxy |
| `hrv_rmssd` | `ms` | `s` | Existing 0.001 | Existing `hrv`: every 60 s, first at 61 s |
| `visual_acuity_logmar` | `logMAR` | `1` | 1 | `eye_screen`: configured point events |
| `amsler_grid_distortion` | `boolean` | `boolean` | Boolean bypass | Same eye-screen event |

All new channels have `scope="crew"` and `lab=False`. The logarithmic meaning of LogMAR must be explicit in metadata even though its wire unit is dimensionless.

`docs/frequency_table.md`, row 9, requests 50 Hz raw acquisition and minute outputs. For a full implementation, evaluate 3,000 latent samples at the midpoints of each completed 60-second window and compute the mean strain and indicator. Derive mean resistance from that same mean strain; the linear gauge-factor equation guarantees consistency. Raw samples are temporary and never become 3,000 HTTP requests. This models a strain trend at that sampling grid; adding a realistic jugular pulse waveform is separate work and must not be claimed by metadata.

In `scheduler.rules()` add:

```python
Rule("cephalic", phase=60, interval=60)
Rule("eye_screen", points=scenario.eye_screen_times_s)
```

Route these groups in `Scheduler.acquire()` to new cephalic/window and eye-screen functions. Filter scenario-specific groups by the configured target owner during scheduler construction; simply adding global rules currently schedules them for every crew member. Preserve the existing enabled-channel filtering.

The eye-screen events stand in for an astronaut completing the prompted test. There is no incoming command/control channel today. A genuinely interactive “backend requests a screen, user completes it” workflow requires a separate API and cannot be inferred from an outgoing alert. An empty screen-event list must produce no later screen results, rather than continuously publishing false/normal results.

## 6. Configuration and startup behavior

Add optional `Settings.sans_scenario: SansScenario | None = None` using the existing frozen Pydantic style. The following is a proposed `config/badscenario1.toml`, not a file that can run with the current parser:

```toml
seed = 42
speed = 10
duration_s = 4200
enabled_channels = [
  "jugular_strain_pct", "delta_R_over_R0", "icp_risk_indicator_mmHg",
  "hrv_rmssd", "visual_acuity_logmar", "amsler_grid_distortion",
]

[environment]
gravity_g = 0

[[crew]]
id = "crew-1"
resting_hr_bpm = 72
sbp_mmhg = 118
dbp_mmhg = 78
rmssd_ms = 48

[sans_scenario]
id = "FAULT_01_SANS_CEPHALIC"
owner_id = "crew-1"
onset_s = 600
warning_at_s = 1800
escalate_to_critical = true
critical_start_s = 2400
critical_at_s = 3600
baseline_strain_pct = 0.65
warning_strain_pct = 1.55
critical_strain_pct = 2.05
gauge_factor = 15.5
affected_rmssd_ms = 36
baseline_icp_indicator_mmhg = 10.0
warning_icp_indicator_mmhg = 16.2
critical_icp_indicator_mmhg = 19.0
affected_logmar = 0.20
eye_screen_times_s = [1860, 3660]
```

Validate finite values, a real crew owner, positive ramp durations, ordered non-overlapping stages, nonnegative unique sorted screen times, positive gauge factor/HRV references, and strain targets in their intended nominal/warning/critical bands. Require `gravity_g = 0` for this initial microgravity scenario. New SANS channels require scenario configuration; old healthy configs keep their existing channel set. Implement one shared effective-channel selection helper for scheduler, startup and dictionary so registering new channels does not silently activate them in every healthy run.

Extend `startup_crew_values()` / `Scheduler.initialize()` to provide the new baseline values for the target astronaut without attempting a negative-time collection window. At time zero, emit strain 0.65, ratio 0.10075, indicator 10.0, HRV reference 48, LogMAR 0 and Amsler false, subject to enabled-channel selection. Use `sample_kind="startup_baseline"` and `window_s=0`; normal communication delay still applies.

The startup eye values are synthetic reference fixtures, not evidence that a self-test was performed. Only later `scheduled` eye-screen events count as completed screens. The backend must distinguish those using the existing sample-kind metadata. Re-running the same scheduler must not repeat initialization.

## 7. Backend mapping and expected evaluation

The source document's “all keys match 1:1” statement does not match this repository's transport or evaluator. Preserve the simulator's one-reading-per-request body, for example at the warning plateau:

```json
{
  "channel": "jugular_strain_pct",
  "value": 0.0155,
  "unit": "1",
  "measured_at": "2026-11-14T00:31:00Z"
}
```

At the receiver, map `jugular_strain_pct` to the existing evaluator argument `jugular_distension_pct`, using `100 * reading.value` after checking the unit. Call:

```python
findings.sans_fluid_shift_1_3(jugular_distension_pct=1.55)
```

The existing function yields nominal below 1.1%, warning from 1.1% through 1.8%, and critical above 1.8%. It uses only jugular distension: HRV, the indicator and eye-screen results are contextual outputs, not current inputs to this function. No diagnosis or treatment instruction belongs in the simulator payload. The existing backend returns the eye-test/LBNP action text for both warning and critical; scenario tests can assert that existing behavior without adding new treatment logic.

For the latent fixture, warning starts at 1200 s (midpoint of the first smooth ramp), and strain reaches 1.8% at 3000 s (still warning at equality). Published 60-second means cross later than the instantaneous curve. On the proposed 60-second schedule with no added strain noise, the first warning sample is at 1260 s and the first critical sample is at 3060 s. Delivery adds communication delay. An hourly sustained-shift evaluator from frequency-table row 9 would have its own additional evaluation timing; the existing finding function itself has no persistence or scheduling state.

Implement backend ingestion separately: accept and validate four-field readings plus owner/run metadata, convert units, deduplicate retries, preserve timestamps, and dispatch eligible strain observations to the finding function. Keep startup fixtures distinguishable from scheduled evidence. Do not claim a dashboard alert works merely because JSON preview works.

## 8. Suggested implementation order and verification

1. Add `SansScenario` and pure trajectory helpers; test onset boundaries, endpoint holds, warning-only behavior and deterministic evaluation at arbitrary times.
2. Add HRV context to the beat-level model; verify healthy results are unchanged without the scenario and a second astronaut is unaffected.
3. Add registry/frequency entries, explicit channel selection and cephalic/eye schedules. Update `EXCLUDED` narrowly so it no longer claims these specific implemented channels are absent; retain unrelated exclusions.
4. Add startup references and dictionary descriptions, including assumed indicator values, scenario ID/owner/timing, source-document reference, collection windows and screen-event semantics. Preview can reuse its registry-based source-unit conversion; optionally extend `PreviewState.baseline()` for the new references.
5. Add `config/badscenario1.toml` and document preview execution. After implementation: `uv run imitacija --config config/badscenario1.toml --preview`. Remove `--preview` only after configuring a working telemetry receiver.
6. Add direct integration checks against `sans_fluid_shift_1_3()` and implement the separate HTTP receiver path if end-to-end alerts are required.

Required scenario tests:

- Initial healthy fixtures appear once with correct ownership and zero collection windows; empty enabled channels remain empty.
- At settled window endpoints, strain/ratio pairs are `(0.65, 0.10075)`, `(1.55, 0.24025)` and `(2.05, 0.31775)` in source units. Every window obeys `ratio = 15.5 * strain_pct / 100` within numerical tolerance.
- Wire conversion produces 0.0065 / 0.0155 / 0.0205 for strain, seconds for HRV, and Pa for the indicator. The receiver converts strain back before threshold evaluation.
- No scheduled cephalic reading occurs before 60 s. Windows crossing onset include both healthy and affected samples. Exact threshold boundaries 1.1% and 1.8% retain the existing backend semantics.
- HRV decreases toward the configured resting target through the generated NN intervals; unrelated channels retain their original values at equal model times.
- Scheduled visual results appear only at 1860 and 3660 s in the full demo, both report +0.20 / true, and no scheduled screen results appear when the event list is empty.
- A two-crew run affects only the selected owner. Default healthy configs remain usable and do not acquire SANS channels implicitly.
- Deterministic `ManualClock` runs reproduce values and timestamps. Real-clock acceleration may coalesce acquisitions, so do not require identical HTTP message counts under different CPU loads.
- Mock HTTP delivery preserves the four-field body, sample-kind headers, converted units and acquisition timestamps; direct backend evaluation returns nominal → warning → critical.

Run the existing project checks after implementation: `uv run --frozen pytest`, `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .`, and `uv run --frozen mypy`.

## 9. Completion criteria

This scenario is implemented when an explicit scenario config starts the selected astronaut at healthy references, gradually raises the coupled cephalic signals, lowers the HRV reference through the existing beat model, emits eye-test results only at specified events, and produces the expected backend threshold transitions after correct unit conversion. A warning-only run and a warning-to-critical run must both be reproducible. HTTP alerts additionally require the receiver integration described above.

## Implementation status

The simulator portion is implemented in `src/imitacija/scenarios.py`, optional
`SansScenario` settings, channel/frequency registration, beat-level HRV integration,
and target-owner scheduler rules. Run `config/badscenario1.toml` with `--preview`.
Scenario settings are exported in the dictionary. Existing healthy configs keep
29 active channels; the full registry contains 34 entries. Startup, windows,
wire conversions, ownership, screen events, invalid configurations and mock HTTP
transport are covered by `tests/test_sans.py`.

Backend HTTP ingestion remains the separate prerequisite described in section 7;
this implementation does not add a receiver or user-driven eye-screen control.
