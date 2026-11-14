# Scenario 3 implementation plan: acute EVA dehydration & electrolyte depletion

**Scenario:** `FAULT_03_EVA_DEHYDRATION` — Finding 2.

**Source:** [Unhealthy simulation specification](hydrogfn_unhealthy_simulation_specification%20%281%29.md), Scenario 3.

**Pattern:** [Scenario 1](../badscenario1.md) and [Scenario 2](badscenario2.md). Paths below are relative to the simulator project root unless stated otherwise.

**Status:** Implementation plan only. Scenarios 1 and 2 are already implemented. This plan uses the source's 2.5-hour example, with explicit engineering assumptions for intake, patch-to-body scaling, response curves and sampling. Numerical targets are simulation requirements, not a validated dehydration or electrolyte-kinetics model. Enable all available readings at startup, as requested for the existing scenarios.

## 1. What can be reused, and what is missing

Most outputs already exist, but the sweat channel's physical meaning and the acquisition schedules need careful treatment.

| Area | Existing code | Planned use |
| --- | --- | --- |
| Validated scenarios | `models.Settings`, `SansScenario`, `HypercapniaScenario` | Add optional `EvaDehydrationScenario`, with one affected crew owner. |
| Deterministic trajectories | `scenarios.py`, `smoothstep()` | Add pure cumulative fluid-balance and response helpers. |
| Sweat sensing | `crew_values("sweat" / "sweat_summary")` | Preserve local-patch units and derive patch flow from the same whole-body fixture used by the mass balance. |
| Body mass and urine | `crew_values("mass" / "usg")` | Generate mass from integrated net loss and USG from the resulting deficit. |
| Cardiovascular signals | `heart_rate()`, `crew_values("bp")`, `rmssd()` | Couple HR/BP references to deficit; keep HR windows and HRV beat generation consistent. |
| Scheduler and initialization | `rules()`, `Rule`, `Scheduler` | Add explicit EVA acquisition, owner-specific schedule overrides and all-channel startup. |
| Metadata and preview | `registry`, `frequency`, `PreviewState.baseline()` | Register whole-body sweat separately and show matching baseline references. |
| Backend finding | `../backend/core/findings.py::dehydration_2_1()` | Reuse mass/USG evaluation with the correct initial body mass. |
| HTTP/SSE integration | `../backend/api/views.py`, `api/findings.py`, core `assessment.py` | Extend the existing channel catalog and verify the existing ingestion and finding stream. |

The backend now has `/api/readings/` and evaluates Finding 2 when mass or USG arrives. Do not carry forward the earlier plans' historical statement that ingestion is absent. However, Finding 2 returns a **boolean finding status**, not warning/critical severity, and does not use shock index or sweat sodium as inputs.

The current healthy sweat channel is a **local 10 cm² patch flow**. Sending 820 mL/h on that channel would silently change its meaning. Add a separate `whole_body_sweat_rate` channel and explicitly map the source document's whole-body `sweat_rate` example to it.

## 2. Exact signals and fluid-balance coupling

Use the demo's 75 kg baseline. Adopt 100 mL/h of drink-bag intake during EVA as the explicit low-intake fixture:

```text
Whole-body sweat:       0.820 L/h × 2.5 h = 2.050 L
Drink-bag intake:       0.100 L/h × 2.5 h = 0.250 L
Net fluid deficit:     2.050 − 0.250       = 1.800 L
Mass loss assumption:  1 L net water loss = 1 kg mass loss
Remaining mass:        75.000 − 1.800     = 73.200 kg
Baseline mass loss:    100 × 1.800 / 75   = 2.400%
```

Do not interpolate body mass independently to 2.4%. Derive it from sweat and intake at every time. Changing mass, sweat rate, intake or EVA duration must change the endpoint naturally. The 1 kg/L approximation matches the existing Finding 2 calculation. For this fixture, non-sweat losses and routine replacement cancel; no additional urine/respiratory loss is subtracted. The existing 24-hour urine output is not an extra loss term in this simplified budget.

| Signal | Healthy scenario reference | Example endpoint | Implementation |
| --- | --- | --- | --- |
| New `whole_body_sweat_rate` | 45 mL/h = 0.045 L/h | 820 mL/h = 0.820 L/h | Whole-body fixture; drives cumulative water loss. |
| Existing `sweat_rate` | 0.045 / 1800 L/h | 0.820 / 1800 L/h | Local patch flow from an explicit configurable body-to-patch multiplier. |
| `sweat_sodium_concentration` | 38 mmol/L | 74 mmol/L | Same concentration fixture used by patch sodium flux. |
| `sweat_sodium_flux` | `(0.045 / 1800) * 38` mmol/h | `(0.820 / 1800) * 74` mmol/h | Completed minute mean of local flow × concentration. |
| `body_mass` | 75 kg | 73.2 kg | Baseline mass minus integrated net fluid deficit. |
| `body_mass_loss_pct` | 0% | 2.4% | Derived helper/backend result, not an additional telemetry channel. |
| `urine_specific_gravity` | 1.012 | 1.026 | Synthetic deficit-dependent spot result. |
| `heart_rate` | 72 bpm reference | 122 bpm reference | Deficit-dependent reference inside existing HR and beat calculations. |
| `bp_systolic` | 118 mmHg reference | 98 mmHg reference | Paired synthetic pressure result. |
| `bp_diastolic` | 78 mmHg reference | 74 mmHg reference | Same deficit response as systolic pressure. |
| Pulse pressure / shock index | Derived from paired readings | 24 mmHg / `122 / 98 ≈ 1.245` | Backend or preview derivation, not independent sensor values. |

A multiplier of 1800 matches the existing healthy model's scaling convention. Make it a scenario setting and document it as an assumed uniform-sweating conversion, not a calibrated whole-body estimate from a real patch. Whole-body flow is the primary latent fixture; both local flow and body mass derive from it.

Gross whole-body sodium loss at the endpoint is `2.050 L * 74 mmol/L = 151.7 mmol`; the local patch accumulates `151.7 / 1800 mmol`. These are sweat sodium losses, not serum sodium changes or a diagnosis of hyponatremia. Intake is water-only for this first fixture. Do not infer serum electrolyte concentrations or add unprovided electrolyte channels.

## 3. Proposed reproducible timeline

Use elapsed simulation seconds with explicit EVA onset and duration. `EVA_ACTIVE` is a derived scenario state, not a currently supported global environment mode.

| Time | Behavior |
| --- | --- |
| 0 | Emit every available baseline once, including new whole-body sweat and existing laboratory/environment channels. |
| 0–600 s | Healthy target references; no active EVA sweat acquisition. Baseline mass 75 kg and USG 1.012. |
| 600–9600 s | EVA exposure: whole-body sweat 820 mL/h, sodium 74 mmol/L, intake 100 mL/h. Net deficit grows at 720 mL/h for exactly 2.5 hours. |
| During EVA | Mass falls from the integrated deficit. HR rises, BP falls and USG rises using that same deficit. |
| 9600 s | Final completed active sweat windows; mass 73.2 kg, 2.4% loss, USG 1.026, HR/BP references 122 and 98/74. |
| 9600–10200 s | Freeze the accumulated deficit and affected references for a short review plateau; stop active sweat publications. No recovery model is implied. |

Use a step to the specified sweat/sodium plateau at EVA onset. The source asks for 820 mL/h for 2.5 hours; a ramp inside those 2.5 hours would change the integrated deficit. A future ramp must integrate its actual area and revise the expected intake/endpoint rather than retaining an inconsistent 2.4% assertion.

Proposed pure helpers in `scenarios.py`:

```python
# Validated config supplies constants; hours are derived from elapsed seconds.
exposure_h = min(max(t - onset_s, 0), eva_duration_s) / 3600
sweat_loss_l = whole_body_sweat_l_h * exposure_h
intake_l = drink_rate_l_h * exposure_h
deficit_l = sweat_loss_l - intake_l
mass_kg = profile.mass_kg - deficit_l
loss_pct = 100 * deficit_l / profile.mass_kg

# response_loss_pct = 2.4 for the example; never overrides the mass balance.
p = min(1.0, max(0.0, loss_pct / response_loss_pct))
w = p * p * (3 - 2 * p)
usg = 1.012 + (1.026 - 1.012) * w
hr_reference = profile.resting_hr_bpm + (122 - profile.resting_hr_bpm) * w
sbp_reference = profile.sbp_mmhg + (98 - profile.sbp_mmhg) * w
dbp_reference = profile.dbp_mmhg + (74 - profile.dbp_mmhg) * w
```

Suggested responsibilities: `eva_balance(t, profile, scenario)`, `eva_references(t, profile, scenario)`, `eva_sweat_values(t, scenario)` and `eva_sweat_summary(t, scenario)`. Include cumulative gross sodium loss in the balance helper for validation, even if it is not transmitted. Integrate by elapsed time or exact interval overlap; never accumulate by emitted sample count. Disabling a channel or skipping a poll must not change the deficit.

Hold the balance after EVA end. The short post-EVA plateau freezes the response fixture as well; it does not represent continued exertion or predict recovery. Keep the default run finite at 10200 s to avoid presenting that hold as an indefinite physiological model.

## 4. Integration with physiology and ownership

Add optional keyword-only dehydration context through `crew_values()`, `heart_rate()`, `rmssd()`, startup handling and scheduler calls. Apply it only to `scenario.owner_id`. Other crew retain their existing healthy values and schedules; cabin/environment signals remain independent.

**Mass and USG:** For the target, replace the existing small `hydration()` mass drift with the scenario balance, including before onset and after EVA. Do not add both deficits. Use the same scenario USG helper wherever USG is returned, including the existing `urine`/`ntx` value dictionary, while preserving group filtering. Do not fabricate additional daily urine collections during the short demo.

**HR and BP:** Avoid counting normal exercise twice on top of the explicit 122 bpm / 98 mmHg targets. For the target, blend the existing healthy deterministic HR/BP values (excluding their noise term) toward the configured endpoint with `w`, then add the existing bounded seeded noise once. At `w=0`, the old HR/BP function is unchanged; at `w=1`, the reference is the specified endpoint regardless of the daily exercise peak. A simple reference replacement plus the existing `+48 * activity()` or `+18 * activity()` would exceed these targets if EVA overlaps the daily exercise bout.

Evaluate HR at each of the existing twelve five-second midpoint samples in a completed 60-second heart window. Pass the same affected instantaneous HR into `rmssd()` for beat timing. Keep the existing RMSSD target; the source gives no dehydration-specific RMSSD endpoint. Small extraction/quantization changes are expected.

**Activity and sweat:** Do not modify global `activity()` to force the EVA. It also drives unrelated temperature, glucose, lactate, HRV and urine behavior. The target's sweat gates and acquisition rules must explicitly use the configured EVA interval. Emptying `exercise_test_days` only removes exercise test events; it does not disable the daily activity waveform.

**Other signals:** Preserve ordinary healthy models for respiration, SpO₂, temperature, chemistry, radiation and cabin CO₂. This plan does not claim to simulate every exercise response. At startup, use existing profiles for unrelated channels and explicit scenario references for affected channels.

## 5. Channels, units and acquisition rules

| Channel | Source unit | Wire unit | Factor | Scenario acquisition |
| --- | --- | --- | --- | --- |
| New `whole_body_sweat_rate` | L/h | `m^3/s` | `1 / 3_600_000` | New `eva_sweat` group; completed 1 s mean every second during EVA. |
| `sweat_rate` | L/h, local patch | `m^3/s` | Existing `1 / 3_600_000` | Existing `sweat` group, with target-specific EVA gate. |
| `sweat_sodium_concentration` | mmol/L | `mol/m^3` | 1 | Same one-second patch window. |
| `sweat_sodium_flux` | mmol/h, local patch | `mol/s` | Existing `1 / 3_600_000` | Completed 60 s mean, every minute during EVA. |
| `body_mass` | kg | kg | 1 | Target-specific point estimate every 60 s. |
| `urine_specific_gravity` | 1 | 1 | 1 | Explicit target spot events at 600, 3600, 6000, 7800, 9600 and 10200 s. |
| `heart_rate` | bpm | `s^-1` | Existing `1 / 60` | Existing 60 s mean and phase. |
| `bp_systolic`, `bp_diastolic` | mmHg | Pa | Existing `MMHG_TO_PA` | Paired target fixture every 60 s. |

The minute mass/BP schedule is an explicit synthetic demonstration override. It is not evidence of continuous in-suit weighing or minute cuff measurements. The urine events are synthetic completed spot-result fixtures, not automatic urine sampling or an implemented user prompt. Metadata must state these assumptions. Other crew retain the default pre/post mass/USG schedule and cuff rules.

At the plateau, `whole_body_sweat_rate` is `0.820 / 3_600_000 ≈ 2.27777778e-7 m^3/s`. Local flow is that value divided by 1800. Sodium concentration remains numerically 74 in `mol/m^3`; never apply a further 1000 multiplier. Whole-body sodium loss rate is 60.68 mmol/h internally; local flux is `60.68 / 1800 mmol/h`, then divided by 3,600,000 for transport.

Add `FREQUENCIES["eva_sweat"]` before registry construction: raw/interval 1 Hz/1 s, window 1 s, frequency-table row 2. Registry entry is crew-scoped, non-lab, with explicit whole-body fixture metadata. Keep existing local sweat identifiers and methods.

Build effective rules **per owner** in scheduler construction, replacing the target's `sweat`, `sweat_summary`, `mass`, `usg` and `bp` rules rather than adding duplicate rules. The current `Rule.active_only` jumps directly to the healthy 17:30 exercise period; changing only `crew_values()` would therefore miss this EVA entirely. Non-target owners keep those healthy rules. The new whole-body group exists only for the target.

For the default timeline:

- One-second local/whole-body windows end at 601 through 9600 s, inclusive: 9000 completed active windows.
- Sweat summaries end at 660, 720, …, 9600 s: 150 full active windows.
- Target mass/BP point estimates begin at 60 s, then repeat every 60 s through the run. HR retains its existing schedule.
- USG occurs only at the configured spot events after its startup reference. An empty event list yields no scheduled spot samples.

Keep `Rule.end`'s exclusive semantics explicit when constructing finite sweats rules: for integer-second EVA boundaries, an end bound at `eva_end_s + 1` admits the final second at `eva_end_s`. Apply an acquisition-time guard too, so a late/coalesced poll after the exposure cannot publish an extra active window. Require whole-minute EVA durations for this initial constant-rate fixture so summary windows finish exactly at EVA end. Compute matching whole-body and local windows from the same interval definitions; do not sample opposite sides of the onset/end step.

## 6. Configuration and all-channel startup

Add `Settings.eva_dehydration_scenario: EvaDehydrationScenario | None = None`. Proposed `config/badscenario3.toml`:

```toml
seed = 42
speed = 10
duration_s = 10200
# No enabled_channels: publish all available startup readings and normal streams.
base_url = "http://127.0.0.1:8000"
data_route = "/api/readings/"

[environment]
gravity_g = 0

[[crew]]
id = "crew-1"
mass_kg = 75
resting_hr_bpm = 72
sbp_mmhg = 118
dbp_mmhg = 78
rmssd_ms = 48

[eva_dehydration_scenario]
id = "FAULT_03_EVA_DEHYDRATION"
owner_id = "crew-1"
onset_s = 600
eva_duration_s = 9000
baseline_whole_body_sweat_l_h = 0.045
active_whole_body_sweat_l_h = 0.820
drink_rate_l_h = 0.100
whole_body_to_patch_multiplier = 1800
baseline_sweat_sodium_mmol_l = 38
active_sweat_sodium_mmol_l = 74
response_loss_pct = 2.4
baseline_usg = 1.012
affected_usg = 1.026
affected_heart_rate_bpm = 122
affected_sbp_mmhg = 98
affected_dbp_mmhg = 74
usg_event_times_s = [600, 3600, 6000, 7800, 9600, 10200]
```

Validate finite values, an existing owner, nonnegative integer-second onset, positive whole-minute EVA duration, positive multiplier and flow, and `0 <= drink_rate_l_h < active_whole_body_sweat_l_h`. Require active flow 0.650–0.950 L/h, sodium 68–85 mmol/L, HR 115–132 bpm, systolic 96–102 mmHg, USG 1.024–1.030 and response loss 2.1–3.2%, following the source's target ranges. Validate ordered baseline/affected values, positive pressure with systolic above diastolic, and the fully integrated loss remaining below starting mass. Spot-event times must be finite, positive, unique and sorted. Do not require every valid configuration to end at exactly 2.4%; that is the default example's arithmetic result.

Reject simultaneous SANS, hypercapnia and EVA fault configuration in this first implementation. Preserve existing healthy profile limits; disease BP targets belong in the scenario object. Gravity zero is the demo context, not an activation switch for dehydration. Reject conflicting stand-test/session overrides for the target if they would be silently discarded, or make the precedence explicit in validation and metadata.

Add an EVA-only channel set containing `whole_body_sweat_rate`. Extend `effective_channels()` so it is enabled by default only with the EVA scenario, and explicit selection without scenario settings fails clearly. Preserve an explicitly empty selection. The complete registry becomes 36 channels; default healthy runs remain 29, SANS 34, hypercapnia 30, and single-crew EVA runs have **30 startup readings: 25 crew and 5 environment**. SANS-only and CFE-only channels do not acquire fabricated EVA baselines.

For the target, startup mass is exactly the configured 75 kg reference; USG is 1.012; whole-body sweat is 0.045 L/h; local sweat is 0.045/1800 L/h; sodium is 38; local sodium flux is their product. These scenario references override the profile's ordinary patch references without relaxing its healthy validation limits. HR/BP startup references remain 72 and 118/78. All other available channels use their existing startup fixtures, including lab/dry channels. Mark every startup observation `startup_baseline`, `window_s=0`, with communication delay and no lab delay. Initialization remains idempotent.

Update preview reference handling so it displays these scenario patch/whole-body values and initial mass, rather than the old profile patch baseline. Export scenario settings, affected owner, synthetic schedule overrides and source assumptions in the dictionary. Update channel catalog, frequency mapping, model assumptions and backend contract; keep the original frequency table as the source requirement.

## 7. Backend mapping and expected evaluation

Reuse the current four-field body and metadata headers. A settled mass observation is:

```json
{
  "channel": "body_mass",
  "value": 73.2,
  "unit": "kg",
  "measured_at": "2026-11-14T02:40:00Z"
}
```

The existing evaluator already derives mass-loss percentage and fluid deficit:

```python
findings.dehydration_2_1(
    body_mass_kg=73.2,
    baseline_body_mass_kg=75.0,
    urine_specific_gravity=1.026,
)
# body_mass_loss_pct = 2.4, fluid_deficit_ml = 1800, status = True
```

It triggers when **mass loss >2.0% OR USG >1.020**. Equality does not trigger that particular condition. Its status is boolean; it does not return a Critical Red category, shock index or a workload-reduction recommendation. Sweat and sodium are contextual channels, not current Finding 2 inputs. Do not substitute standing-test inputs into Finding 1 to force a shock-index alert: an EVA is not an orthostatic test.

With the proposed response and spot schedule, USG exceeds 1.020 at the 6000 s spot event, so Finding 2 can become true before mass loss crosses 2%. The latent mass loss equals 2% at 8100 s; on the minute schedule the first mass reading strictly beyond it is 8160 s. Floating-point subtraction can perturb exact threshold equality: test an exactly representable mass pair (100 → 98 kg) for the core boundary, and use an explicit documented rounding convention in integration tests for the demo's 75 → 73.5 kg boundary. Do not hide a boundary discrepancy by weakening the expected strict comparison.

The API's current assessment reads the latest values by channel and uses the earliest stored body mass as baseline; it is single-astronaut and does not isolate runs using simulator owner/run headers. For repeatable HTTP tests, use a fresh test database/isolated receiver seeded with this run's startup mass. Do not erase the user's existing readings. Reusing a database containing another run can yield the wrong baseline. Run-scoped baselines, freshness and ownership remain separate backend improvements.

Register `whole_body_sweat_rate` in the backend core channel catalog and relevant channel typing/validation before claiming all 30 readings are accepted over HTTP. Describe it as a whole-body fixture, use `m^3/s`, and return an ungraded/unknown evaluation where the existing catalog supports it rather than inventing a threshold. Preserve local `sweat_rate` semantics. Verify `/api/readings/`, dictionary output and SSE accept/display the new identifier.

The source's Critical Red Alert and 600 mL wording are a separate policy/presentation requirement. The current action refers to the calculated fluid deficit and gives 600 mL as an example; this fixture calculates 1800 mL, so do not relabel that deficit as 600 mL. Keep the simulator free of treatment commands. Full red-alert compliance requires an explicit backend policy change; the simulator/direct-finding acceptance result is healthy `False` → dehydration finding `True`.

If all available channels are streamed, other findings may also react to changing body mass (for example, the current nutrition finding uses mass history). Record actual backend outputs; do not assert that Finding 2 is the only possible card or manufacture chronic nutrition inputs to suppress them.

## 8. Suggested implementation order and verification

1. Add `EvaDehydrationScenario`, mutual-exclusion/owner validation and exact balance helpers. Verify the default 2.050 L sweat / 0.250 L intake / 1.800 L deficit arithmetic before integrating outputs.
2. Add owner-scoped physiology context: patch/whole-body sweat, sodium flux, mass, USG, HR and BP. Reuse affected HR in HRV beat timing and retain existing healthy/SANS/hypercapnia behavior.
3. Add the whole-body registry/frequency entry, effective-channel gating and owner-specific scheduler rules. Keep the healthy exercise optimization for unaffected owners and replace it for the EVA target.
4. Add all-channel startup and preview references; export schedule overrides and assumptions in metadata. Add `config/badscenario3.toml` with no channel whitelist and document `uv run imitacija --config config/badscenario3.toml --preview`.
5. Add `tests/test_eva_dehydration.py` using existing `ManualClock`, sink and mock-delivery patterns. Use short runs for mechanics and one complete default timeline for integration.
6. Extend the backend catalog for the new channel, verify direct Finding 2 and HTTP/SSE integration in isolated tests. Keep red-alert policy work explicitly separate from the existing boolean behavior.

Required tests:

- Default startup emits exactly 30 observations once, matching every effective channel: 25 crew and 5 environment. Includes labs and dry-patch references, zero windows, exact initial mass and the scenario-specific sweat/USG baselines. Calling initialization again produces no duplicates.
- At 5100 s (1.25 hours of EVA), gross sweat is 1.025 L, intake 0.125 L, deficit 0.900 L, mass 74.1 kg and loss 1.2%. At 9600 s, these become 2.050 / 0.250 / 1.800 L, 73.2 kg and 2.4%. Balance holds before onset and freezes after exposure.
- For the default constant-rate fixture, integrated active sweat is 2.050 L and gross sodium loss 151.7 mmol; local flow/flux and their integrals consistently differ by the configured multiplier. Changing intake or baseline mass changes the percentage rather than forcing 2.4%.
- Exact latent endpoint HR/BP/USG references are 122, 98/74 and 1.026. Once windows settle, HR is within ±0.8 bpm and BP within ±1.2/±0.8 mmHg of these references. Check the completed HR plateau at 9660 s rather than requiring the final ramp window at 9600 s to equal its endpoint.
- Sweat schedules activate at the configured EVA time even outside the daily exercise window, emit all complete windows through EVA end, and stop afterward. Late/coalesced polls never manufacture an out-of-exposure result. USG is event-only and empty event lists yield no later spots.
- Correct SI conversions for whole-body/local flow, sodium concentration and flux, HR and BP. Mass stays kg and USG stays dimensionless. Derive shock index only after converting HR to bpm and SBP to mmHg.
- Two-crew runs alter only the target; there is one environment stream. The new whole-body channel belongs only to the target. Target rule replacement produces no duplicate mass/BP/USG or sweat events.
- Disabled channels and changed playback speeds do not change the latent balance. Empty enabled-channel selection remains empty; selecting whole-body sweat without scenario settings fails clearly.
- Invalid ownership, timing, target ranges, intake, multiplier, non-finite values, duplicate spot events and combined faults fail validation. Finite positive mass is maintained for the configured exposure.
- Existing healthy, SANS and hypercapnia tests pass; unrelated outputs stay unchanged at equal model times. HRV retains its reference target while using the affected beat timing.
- Direct core tests cover healthy false, USG-only true, mass-only true and final 2.4% / 1800 mL / true. Test threshold equality and floats explicitly. No test falsely expects a `critical` string from the current boolean evaluator.
- Mock delivery covers all startup channels, four-field bodies, units, owners, run/sample-kind metadata, preserved acquisition times and lab/communication delays. Real receiver tests confirm the new channel is accepted and mass/USG updates produce the expected Finding 2 SSE result against the correct initial baseline.

Run the simulator checks after implementation: `uv run --frozen pytest`, `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .`, and `uv run --frozen mypy`. Run backend core/API checks for the catalog and integration changes. Planning alone requires document/arithmetic verification, not an application test run.

## 9. Completion criteria

Scenario 3 is implemented when it starts with all available references, explicitly activates the target astronaut's EVA, derives mass loss from integrated whole-body sweat minus intake, preserves local patch meaning and sodium coupling, produces the specified correlated endpoints and scheduled observations, and passes healthy/SANS/hypercapnia regressions.

Direct backend acceptance is healthy `False` → dehydration `True` with 2.4% loss and 1800 mL deficit. End-to-end telemetry additionally requires backend catalog support for the new whole-body channel and a correct run baseline. The source's Critical Red Alert remains a distinct policy/presentation acceptance item.

## Implementation status

Implemented optional EVA configuration, pure fluid/sodium balance, coupled
physiology, target-specific rules, whole-body sweat registration, all 30 startup
readings, preview references and backend catalog support. The default example
uses `config/badscenario3.toml`. Simulator tests cover the full timeline and
backend-core mapping; an isolated API test verifies whole-body channel acceptance
and the final dehydration finding. The existing boolean Finding 2 semantics remain
as described in section 7; red severity is still a separate policy requirement.
