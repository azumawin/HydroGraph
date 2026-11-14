# hydrograph-core

Pure domain logic for the HydroGFN health monitor: the master plan's 10 Tier 1
health findings, the sensor channel catalog (the simulator's 29 channels, in SI
wire units) with single-reading thresholds, and the mission environments. No Django imports, no I/O, no state. The backend
consumes it; any rule about what a value means belongs here, not in `api/`.

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

A self-contained flat module in `src/hydrograph_core/` (Python >= 3.14, no
runtime dependencies). `import hydrograph_core` exports the 10 finding
functions, named `<finding>_D_S` (D = hazard domain, S = place in it;
map to plan finding numbers in the `findings.py` docstring),
`CHANNELS` + `evaluate_reading(channel, value)`, and `ENVIRONMENTS`. Conventions: `STYLE.md`.

Each function returns only the values it can actually produce: a finding with
one severity has `status: bool` (`True` = present); one with several has
`status: Severity` (`"nominal" | "warning" | "critical"`). `evaluate_reading`
returns an `Evaluation`, which adds `"unspecified"` for readings the specs give
no cutoff for.

```python
import hydrograph_core

finding = hydrograph_core.sans_fluid_shift_1_3(1.5)
finding["status"], finding["triggers"]  # "warning", ["jugular distension >= 1.1%"]
```

## Using it from the Django backend

The package is a stateless library. The backend owns all state: sessions,
reading history, sensor processing. Every function takes plain numbers and
returns a plain `dict` of numbers, strings, booleans and lists that `json.dumps`
accepts as-is, so results can go straight into a JSON column (e.g. Django
`JSONField`) or a response.

1. It is already a workspace dependency of `backend/pyproject.toml`, so `uv sync`
   installs it editable. Import it from `api/` views.
2. Call a finding with values the backend has collected or computed upstream
   (e.g. supine and standing BP; `None` for an hs-cTnI assay that was not run):

   ```python
   from hydrograph_core import orthostatic_intolerance_1_1

   finding = orthostatic_intolerance_1_1(120, 95, 80, 72, 70, 105, None)
   ```

   Store whatever history a finding needs; the library keeps none.

The backend also has to:

- Turn raw sensor readings into the physical values findings take (the Tier 2
  parameters of `NSA_hydrograph.md`); this package no longer does that.
- Attach timestamps. Functions take no time argument.
