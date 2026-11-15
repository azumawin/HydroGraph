# Blood pressure on the dashboard

The existing `core.findings.blood_pressure_1_4()` evaluator was added
in commit `9483adf`. Its docstring references a "Blood Pressure Telemetry Guide"
in `message.md`, which is absent from the repository. `imitacija/ranges.md`
also discusses blood pressure, but its clinical categories differ from this
project evaluator. This integration preserves the implemented evaluator's
thresholds; it does not replace them with those categories.

The evaluator combines systolic pressure, diastolic pressure and optional heart
rate. Its existing rules are:

| Result | Implemented condition |
| --- | --- |
| Critical | SBP ≤90 or ≥140 mmHg, DBP ≥90 mmHg, or shock index >0.9 |
| Warning, unless already critical | SBP ≤100 or >120 mmHg, DBP <60 or >80 mmHg |
| Nominal | No warning or critical condition |
| Sensor error | SBP ≤DBP, or pulse pressure <15 mmHg |

MAP = DBP + (SBP − DBP)/3. Shock index = heart rate/SBP. Heart rate is converted
from `s^-1` to bpm and pressures from Pa to mmHg before evaluation. When heart
rate is missing, pressure is still evaluated and shock index remains unavailable.
These are project alert rules, not diagnoses.

the built-in rule `core/rules/blood_pressure_1_4.py` calls the evaluator when both
pressure channels are present. The finding catalog lists both pressure channels
and heart rate so updates to any of them trigger a new assessment. The backend
publishes `blood_pressure_1_4` through the existing `finding` stream, includes it
in reconnect snapshots and serves it through `/api/health-conditions/`. The
health assistant receives it through the same findings pipeline.

The dashboard's blood pressure row uses this combined finding for its status,
and displays MAP, available shock index and triggered criteria. Individual
pressure reading evaluations remain `unspecified`, since a single channel does
not supply the pair or shock index.

Invalid pairs produce an operational warning containing `values.sensor_error`,
without MAP or shock-index risk values. The pressure badge says "Sensor error".
This keeps ingestion and the stream running while paired readings arrive in
separate requests; the next valid pair clears the error.

`make dev` and `make sim` now enable paired pressure demo trends every five
simulated seconds. A smooth, seed-dependent variation of up to ±3% is applied
to the scenario values before SI conversion, so both curves and their displayed
values change. Those samples follow the same backend evaluation and history
path. Use `BP_DEMO_INTERVAL=0` for the original measurement schedules and model.
