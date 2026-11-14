# Backend integration

Run the receiver separately. All crew and environment measurements use one configured `data_route`:

```toml
base_url = "http://127.0.0.1:8000"
data_route = "/api/readings/"
```

Both scopes send `POST http://127.0.0.1:8000/api/readings/`, the HydroGraph backend (`backend/`, run with `python manage.py runserver`). `data_route` is a shared path, without owner/channel placeholders or per-channel overrides. It replaces the previous `crew_route`, `environment_route` and `channel_routes` settings; remove those keys from older configuration files.

Run normal delivery with `uv run imitacija --config config/healthy.toml` (without `--preview`). Set `IMITACIJA_TOKEN` if a Bearer token is required. The receiver distinguishes records using `X-Simulation-Scope` (`crew` / `environment`), `X-Owner-ID`, and the body’s `channel`. Multiple crew members produce independent records; each compartment sample is posted once. Add `[[crew]]` records with unique IDs to configure more crew.

The JSON body contains exactly four fields. Evaluation and result classification belong to a separate backend:

```json
{
  "channel": "bp_systolic",
  "value": 15198.75216531,
  "unit": "Pa",
  "measured_at": "2026-11-14T08:00:00Z"
}
```

The `unit` field names the wire unit of `value`, as defined by the channel registry. This illustrative 114 mmHg BP is transmitted in Pa. Boolean flags use `unit: "boolean"`; dimensionless numerical ratios use `"1"`. Temperature is K, pulse/respiration s⁻¹, saturation a fraction, volume m³, and dose Sv; consult the dictionary for every unit. The legacy `bone_ntx_pct_baseline` identifier is retained, but its SI-wire value is fractional **change** (0 = baseline, 0.03 = +3%), explicitly documented in the dictionary. The `ambient_light_lux` identifier uses lx. Boolean virus/SPE values remain JSON booleans.

`measured_at` is UTC point acquisition time or the end of the declared observation window. Laboratory results can arrive later and out of order. A receiver should not treat HTTP arrival order as collection order or overwrite a fresh sample with an older delayed specimen. It should not treat a missing/dry/unsampled channel as normal.

Headers supply the context without changing nigelNote's body:

| Header | Meaning |
| --- | --- |
| `Idempotency-Key` | Run + owner + channel + sequence; unchanged on retry. Receiver should deduplicate. |
| `X-Simulation-Run` | New unique delivery run on each process start. |
| `X-Simulation-Scope` | `crew` or `environment`. |
| `X-Owner-ID` | Crew ID or compartment ID according to scope. |
| `X-Sample-Kind` | `startup_baseline` for one immediately available run-start fixture; `scheduled` for normal acquisitions. |
| `X-Sensor-ID` | Owner + acquisition group; paired results share the physical acquisition group. |
| `X-Window-Seconds` | 0 for point sampling; duration ending at `measured_at` otherwise. |
| `X-Simulation-Start`, `X-Simulation-Speed` | Mapping of run time to timestamps; acceleration must be explicit to the backend. |
| `X-Result-Available-Seconds` | Result eligibility time in elapsed simulation seconds, including configured lab/communication delay. |
| `X-Dictionary-Version` | Static registry schema/version, currently `1`. |
| `Authorization` | Optional Bearer token from the `IMITACIJA_TOKEN` environment variable. |

Return 2xx after accepting a reading. The HydroGraph backend answers `201` with the reading's `channel`, `value` and `measured_at` plus its `evaluation` (`docs/json-shape.md`, section 2), and `400` with field errors for an unknown channel, wrong unit, wrong value type or mismatched `X-Simulation-Scope`; the simulator counts a 400 as a failed delivery. It monitors one astronaut and ignores `X-Owner-ID`, so configure a single `[[crew]]` member. Permanent authentication/schema failures count as failed delivery; selected transient failures retry with the same body/key. Finite runs may discard delayed results at their bounded shutdown deadline. The ending counters report delivery, overflow, expiry, failure, retry and shutdown-drop totals. Reconcile accepted results with idempotency keys rather than expecting exactly-once network delivery.

Export static configuration-specific metadata before integration:

```sh
uv run imitacija --config config/healthy.toml --dictionary
```

Dictionary JSON retains nigelNote's `environment` and `channels` fields, and adds units, source units, specimen/method, collection/window/availability definitions, citations, enabled flags and exclusions. It is exported explicitly; the worker does not register it automatically or persist it. The receiver decides how to import/serve it and whether its ingestion contract accepts the proposed headers/routes.


## Local JSON preview

`--preview` exposes raw JSON at `/`, `/readings` and `/json`, and metadata at `/dictionary`. It replaces backend delivery with bounded latest-result state held only in RAM. The four-field `reading` object is the exact POST body; surrounding preview context includes conventional values, baselines and run/clock/owner metadata. Refresh to obtain another snapshot. Normal backend delivery does not start this local server.


## Startup initialization

Every enabled owner/channel emits exactly once with `measured_at` equal to the configured run start, including lab-only, windowed and normally dry/inactive channels. It is a synthetic known-at-start profile value, marked `X-Sample-Kind: startup_baseline`, not a newly processed assay or completed pre-start collection. It bypasses `lab_delay_s` while respecting communication delay and bounded delivery. The four-field body is unchanged.

Startup `X-Window-Seconds` is 0: a nominal 24-hour urine baseline must not be interpreted as urine actually collected during a zero-duration interval. Profile RMSSD, nominal daily urine volume (2.7 L), glucose baseline and configured local sweat references stand in for windows that do not yet exist. Normal scheduled readings use `X-Sample-Kind: scheduled` and their real collection windows/processing delays. Preview snapshots expose the same `sample_kind` as metadata around `reading`.

The first normal acquisition remains at its original time; no time-zero acquisition is duplicated. Empty IL-6/troponin event lists suppress later assay collections, not startup initialization. Use `enabled_channels` to omit a metric entirely. A new process run creates fresh baseline readings with a new run identifier; resuming an existing scheduler does not repeat initialization.

## Optional SANS inputs

The dictionary includes `sans_scenario` settings (or null). The five new channels
and their conversions are listed in `channel_catalog.md`. For Finding 9, map
`jugular_strain_pct` wire fractions to the evaluator's `jugular_distension_pct`
percentage argument by multiplying by 100. A value of 0.0155 becomes 1.55.
Keep `startup_baseline` visual fixtures separate from completed scheduled screens.
The existing finding function does not use HRV, ICP indicators or visual results
as classification inputs. Readings arrive at `/api/readings/`; the HydroGraph
backend grades `jugular_strain_pct` and `icp_risk_indicator_mmHg` and runs Finding 9
from `jugular_strain_pct`, as above.

## Scenario 2 mapping and severity

`ambient_ppco2` remains an environment-owned Pa reading; convert to mmHg by
`value / 133.322387415`. Convert `spo2` to percent using `100 * value` and
respiratory/heart rates from `s^-1` using `60 * value`. The CFE ratio is contextual
and dimensionless. Bodies retain exactly four fields; existing headers carry
scope, owner, run identity, sample kind and window provenance.

The existing `hypoxia_co2_2_2()` returns WARNING at 4.8 mmHg / 92% SpO₂,
whereas the source scenario asks for red. CRITICAL currently requires SpO₂ below
90%. No severity-policy change is included in simulator support. RR trend and reported headache remain upstream inputs; missing symptom
reports must not be inferred from the generated CFE or cabin signal. Registering
the new CFE channel in the receiver, a five-second evaluation loop and a resolved
severity policy remain prerequisites
for the source's end-to-end Critical Red Alert. See `badscenario2.md`, section 7.


## Following the backend environment

With `follow_backend_environment = true` (set in `healthy.toml`, `badscenario1.toml`
and `badscenario2.toml`), the simulator polls `GET environment_route`
(`/api/environment/`, every `environment_poll_wall_s`, default 2 s) and, once,
`GET environments_route` (`/api/environments/`, keyed by environment id) for each environment's values. When
the dashboard switches environment, the running simulation takes that environment's
`baseline_dose_rate_usv_h` as its cabin dose rate, its `gravity_g`, and half its
round-trip `comm_delay_rt_s` as the one-way result delay. The integrated monitor dose
stays continuous across the switch. A failed poll is reported once and retried; the
run never stops for it. Scenario validation (SANS needs 0 g) applies only at load, so
a SANS run keeps its fault after a switch to a gravity environment.
## Scenario 3 EVA balance

`whole_body_sweat_rate` is a synthetic crew-owned whole-body fixture in `m^3/s`,
accepted by the backend catalog without a single-reading threshold. Existing
`sweat_rate` remains local patch flow. The default EVA integrates 2.050 L sweat
minus 0.250 L intake to 1.800 L net deficit, 73.2 kg mass and 2.4% loss from 75 kg.
Finding 2 uses mass and USG and returns a boolean status; red severity and shock
index are separate presentation/policy work. Isolate run baselines in HTTP tests:
the current backend uses the earliest stored mass, not the simulation run header.

## Scenario 4 explicit infection context

`consciousness_level` uses wire unit `ACVPU` and exactly one of `ALERT`,
`CONFUSION`, `VOICE`, `PAIN`, `UNRESPONSIVE`; other channels retain strict numeric
or boolean values. Bodies still contain exactly four fields. `supplemental_o2`
and `post_ared_exercise_window` are boolean state fixtures. `il6_pg_mL` is a
separate synthetic GFET/interstitial fixture (`kg/m^3`), distinct from serum IL-6.
The finding selects GFET when present, otherwise serum, recording its source.

Finding 3 becomes ready from the five vitals; optional assays add triggers when
available. NEWS2 includes oxygen and consciousness, with component scores;
qSOFA uses RR ≥22, SBP ≤100 and non-ALERT consciousness. Missing context retains
legacy assumptions with per-field provenance. Missing assays are explicitly
listed, and missing IL-6 is null. The example yields NEWS2 8 / qSOFA 2 / critical.
The demo renders the two scores and IL-6 source. The receiver still monitors one
astronaut and does not isolate runs; use a clean test database for integration.
