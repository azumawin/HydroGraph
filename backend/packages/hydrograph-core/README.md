# hydrograph-core

Pure domain logic for the HydroGFN health monitor: sensor formulas, the 10
health findings, the adaptive polling table and the telemetry payload. No
Django imports, no I/O, no state. Consumed by the `api` app in the backend.

Built from two spec documents in this directory:

- `Tiered Master System Specification & Implementation Plan.pdf` (the master plan)
- `NSA_hydrograph.md` (the parameter spec)

Conventions are in `STYLE.md`. Suspected spec errors are in `sus.md`, and
confirmed ones are in `mismatches.md`.

```sh
cd backend
pytest packages/hydrograph-core  # this package's tests
```

## hydrograph_core

HydroGFN sensor telemetry, a self-contained flat module in `src/hydrograph_core/` (Python
>= 3.14, no runtime dependencies). `import hydrograph_core` exports the 11 parameter
functions of `NSA_hydrograph.md` (`cephalic_fluid_shift_1_1` ... `inflammatory_cytokines_5_1`);
the master plan's 10 Tier 1 findings are in `hydrograph_core.findings`, and its
segmented hydrogel gauge factor (section 3A) is in `hydrograph_core.gauge_factor`, and
its adaptive polling table (section 4) is in `hydrograph_core.polling`. Conventions: `STYLE.md`.

```python
import hydrograph_core

reading = hydrograph_core.glucose_2_1(24.0)
reading["glucose_mmol_l"], reading["status"]  # 3.75, Status.WARNING
```

## hydrograph_core.polling

The master plan's adaptive polling table (section 4): `poll_interval(channel, state)` gives the sampling interval and
`alert_allowed(channel, state, status)` applies the sleep-protection lock and
the radiation override.

```python
from hydrograph_core.polling import UserState, poll_interval

poll_interval("heart_rate", UserState.SLEEPING)["min_interval_s"]  # 900.0
```

## Using it from the Django backend

The package is a stateless library. The backend owns all state: sessions,
user state, reading history, last poll times. Every function takes plain
numbers and returns a plain `dict` that `json.dumps` accepts as-is (`Status`
and `UserState` are `str` enums and serialize to `"warning"`, `"ACTIVE"`, ...),
so results can go straight into a JSON column (e.g. Django `JSONField`) or a
response.

1. It is already a workspace dependency of `backend/pyproject.toml`, so `uv sync`
   installs it editable. Import it from `api/` views or another package; it has
   no Django imports, like `hydrograph-core`.
2. On each incoming reading, run the Tier 2 parameter for that sensor, then
   any Tier 1 finding it feeds (table in `STYLE.md`, "Layout"):

   ```python
   import hydrograph_core
   from hydrograph_core.findings import orthostatic_intolerance_1

   reading = hydrograph_core.glucose_2_1(24.0)
   finding = orthostatic_intolerance_1(120, 95, 80, 72, 70, 105, None)
   ```

   Tier 1 findings take values the backend has collected or computed upstream (e.g.
   supine and standing BP; `None` for an hs-cTnI assay that was not run). Store whatever history a finding needs; the library keeps none.
3. Gate alerts with the stored user state:

   ```python
   from hydrograph_core.polling import UserState, alert_allowed

   state = UserState(session.user_state)  # "ACTIVE" / "RESTING" / "SLEEPING"
   if alert_allowed("glucose", state, reading["status"]):
       ...  # send reading["action"] to the client
   ```

   Radiation channels always alert; while sleeping, other channels alert only when critical.
4. Schedule the next poll per channel:

   ```python
   from hydrograph_core.polling import poll_interval

   interval = poll_interval("glucose", state)
   if interval["min_interval_s"] is not None:
       due = now - last_polled_at["glucose"] >= interval["min_interval_s"]
   ```

   `SUSPENDED` and `UNSPECIFIED` have no interval, nor does sleeping
   `actigraphy` (`CONTINUOUS`, but the plan gives no rate); the backend
   decides what to do for those.

5. Build the p.8 telemetry payload from the results of one tick:

   ```python
   from hydrograph_core.payload import telemetry_payload

   payload = telemetry_payload(timestamp=..., user_state=state.value, glucose=reading, ...)
   ```

   `copilot_decision_engine` (overall status, hazard, numbered actions) is
   derived from the results passed in, so filter them with `alert_allowed`
   first. Sending the payload and reusing last values between polls is the
   backend's job; the plan gives no broadcast rate.

The backend also has to:

- Detect user state transitions. The master plan gives no rules (`sus.md`, section 4).
- Attach timestamps. Functions take no time argument other than the elapsed-time inputs some parameters need (e.g. `t_met_days`).
- Catch `ValueError`. It is raised for readings a formula cannot invert and for channels missing from the polling table.
