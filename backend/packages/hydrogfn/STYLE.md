# hydrogfn style guide

`hydrogfn` implements the HydroGFN health monitor from two documents in this directory:

- `Tiered Master System Specification & Implementation Plan.pdf` (the
  **master plan**): the Tier 1 / Tier 2 split, the 10 health findings, polling.
- `NSA_hydrograph.md` (the **parameter spec**): formulas and thresholds for
  each sensor "Parameter N.M".

When they disagree, **the master plan wins**. Note the override in the
function's docstring.

## Layout

This package is one uv workspace member of `backend/`. `src/hydrogfn/` is one
self-contained, flat module: no subpackages, no imports from outside its
directory, standard library only. Its docs stay in this package directory.

```
hydrogfn/
  __init__.py         public API: the 11 parameter functions (1.1-5.1) + Status
  shared.py           code shared across files (the Status enum)
  domain_N.py         Tier 2: parameters N.1-N.M of spec domain N
  findings.py         Tier 1: main-window health findings 1-10 (not exported
                      from __init__; import hydrogfn.findings)
  gauge_factor.py     Tier 2: master plan section 3A, segmented hydrogel gauge
                      factor (not exported; import hydrogfn.gauge_factor)
  payload.py          master plan section 5, the JSON telemetry payload built
                      from results the backend has computed (not exported;
                      import hydrogfn.payload)
  polling.py          master plan section 4, the adaptive polling table and
                      alert gating (not exported; import hydrogfn.polling)
```

Tier 2 turns raw sensor readings (ΔR/R0, ΔIds/I0, PSD, ...) into physical
values plus a status. Tier 1 combines vitals and Tier 2 values into the 10
findings and their action cards. Everything here is a stateless library for the backend, which keeps all state
(user state, history, poll times). The dashboard consumes both tiers; it does
not live here.

| Param | Tier 2 panel section | Feeds Tier 1 finding | Polling group |
| --- | --- | --- | --- |
| 1.1 ICP / strain | Hydrogel piezoresistive strain | #9 SANS & cephalic fluid shift | Biomechanics & Fluids |
| 1.2 cTnI | GFET signal gating | none (Tier 2 only) | Metabolic & GFET |
| 1.3 MAP / HR | none | #1 Orthostatic intolerance | Cardiovascular |
| 2.1 Glucose | GFET signal gating | #7 Negative energy balance | Metabolic & GFET |
| 2.2 Core temp | none | Tier 1 vitals row | none listed |
| 3.1 NTx | Biomarker kinetics | #8 Bone demineralization | Metabolic & GFET |
| 3.2 Joint angles | Hydrogel strain | 3D kinematic body model | Biomechanics & Fluids |
| 4.1 Cortisol | Biomarker kinetics | #6 Behavioral health decline | Metabolic & GFET |
| 4.2 CFE | Neural spectrum | #5 Sleep, #6 Behavioral | Neuro-Cognitive |
| 4.3 SQI / mood | none | #5 Sleep, Tier 1 mood score | Neuro-Cognitive |
| 5.1 IL-6 / TNF-α | none | none (Tier 2 only) | none listed |

## Tooling

Python >= 3.14, standard library only at runtime. Dev tools come from the
backend workspace (`backend/pyproject.toml`). From `backend/`:

```sh
uv sync                              # dev tools
black packages/hydrogfn              # format; commit only black-clean code
ruff check packages/hydrogfn         # lint
basedpyright packages/hydrogfn       # must report 0 errors, 0 warnings
pytest packages/hydrogfn             # tests
```

Inside the module, always import relatively (`from .shared import Status`)
so it works under any directory name.

## Module shape

```python
"""Domain N: <spec domain title> (parameters N.1-N.M)."""

from __future__ import annotations
import math
from typing import TypedDict

from .shared import Status


class GlucoseResult(TypedDict):
    param: str
    glucose_mmol_l: float
    status: Status
    action: str


def glucose_N_1(...) -> GlucoseResult:
    ...
```

- Standard library only. `math` is usually all you need.
- No classes other than the result `TypedDict`s, no recursion, no I/O, no global state.
- Each parameter / finding function is self-contained: no shared helpers between parameters. A
  small amount of repeated code is preferred over coupling.
- Physical constants are local variables with a comment giving the value and units.

## Names

Names put the number(s) **after** a descriptive name:

- Tier 2 file: `domain_N.py` for spec domain N.
- Tier 2 function: `<quantity>_N_M` for parameter N.M, matching the md
  (`glucose_2_1`, `cognitive_fatigue_4_2`). Every one is exported from
  `__init__.py` and listed in `__all__`.
- Tier 1 function: `<finding>_N` for finding N (`orthostatic_intolerance_1`,
  `radiation_exposure_10`).

## Signatures

- Live sensor readings come first and have no default.
- Calibration constants that the spec supplies come after, with the spec value as
  the default. Never invent a default the spec does not give; make it required.
- `snake_case` names, lowercase even for symbols (`n_b`, `lambda_d`, `k_enz`).
- Add a unit suffix when the unit is not obvious from the name:
  `_mm`, `_ms`, `_s`, `_days`, `_hours`, `_nm`, `_ng_ml`, `_pct`.
- Each function returns its own `TypedDict`, named after the quantity
  (`GlucoseResult`, `CfeResult`), declared at the top of the module with keys
  in return order.

## Docstring

Raw string, in this order. Formulas are LaTeX, indented under a short label.

```python
r"""
Parameter N.M: <spec parameter title> (<sensor, short>).

<Formula name from the spec>:
    <LaTeX as given in the spec>

Solved for <x> (what the sensor reading gives us):
    <rearranged LaTeX, only if the code inverts the spec formula>

References:
    <every citation the specs give for this parameter, copied in full (all
    authors, title, journal, year, DOI) from NSA_hydrograph.md section 4, or
    "None given in the spec for this sensor.">

Args:
    name: Description :math:`symbol` [unit].

Returns:
    ``param``, ``<value keys>``, ``status``, ``action``.
    <How status is derived; every boundary choice or spec gap you resolved.>

Raises:
    ValueError: <only if the function raises>.
"""
```

Write a `#` comment in the body only for something the docstring cannot carry,
e.g. why a value is rounded before classification.

## Return value

```python
return {
    "param": "N.M",
    "<value>_<unit>": round(value, k),
    ...
    "status": status,
    "action": action,
}
```

- Keys: `param`, then computed values in the order they are derived, then
  `status`, `action`.
- Round returned values to a display precision suited to the quantity
  (usually 1-3 decimals). Classify on the **unrounded** value; if rounding first
  is necessary (floating-point noise exactly at a threshold), say so in a comment.
- Inputs echoed back unchanged (e.g. `ctni_ng_ml`) are not rounded.

## Classification

Use `Status` from `shared.py`, assigned as a pair:

```python
if value > hi:
    status, action = Status.CRITICAL, "..."
elif value >= lo:
    status, action = Status.WARNING, "..."
else:
    status, action = Status.NOMINAL, "..."
```

- **Actions** are the spec's own wording, shortened, imperative, no trailing
  period. The nominal action is the spec's nominal label (e.g. `"Normal baseline"`).
  Actions are data; nothing here executes them.
- **Boundaries.** For a spec band `A - B` followed by `> B`, both `A` and `B`
  belong to the band (`>= A`, `<= B`). Where the spec's bands overlap, the
  shared value goes to the less severe band; note it in the docstring.
- **Gaps on a defined side.** A value between nominal and a defined
  non-nominal band on the same side (e.g. asymmetry 1.15-1.25), or beyond the
  most severe band defined on that side, takes the nearest more severe defined
  status and its action.
- **Undefined sides.** A value on a side the spec never addresses
  (hyperglycemia, hypothermia, low MAP) is `Status.UNSPECIFIED` with action
  `"No protocol defined in spec"`. Never attach an action to a reading it was
  not written for (e.g. "consume a gel packet" for high glucose).
- **Several metrics.** Status is the worst across metrics in the order
  CRITICAL > WARNING > UNSPECIFIED > NOMINAL; the action is the one belonging
  to that status. Nominal requires every metric to be nominal.

## Validation

Callers supply finite inputs and valid calibration values; do not check for
NaN, infinity or sign of constants. The one exception: when a function inverts
a saturating sensor response, raise `ValueError` for readings outside the range
the inverse is defined on (e.g. `0 <= reading < saturation`) instead of
returning a plausible-looking but meaningless value. Document it under `Raises`.

## Tier 1 findings

`findings.py` follows the same rules as the Tier 2 modules, plus:

- One function per finding (see Names), all in `findings.py`.
- Docstring heading is `Finding N: <master plan title> (<primary domain>).`
- Return `finding` (`"1"`-`"10"`), the evaluated values, `triggers` (a
  `list[str]` naming each criterion that fired, for the dashboard's
  `primary_hazard`), `status`, `action`.
- The action is the master plan's action card verbatim, minus the quotes and
  trailing period. No finding: `Status.NOMINAL`, `"No finding"`.
- Any criterion fired is `WARNING`, unless the plan marks it urgent or an
  immediate shelter alert (`CRITICAL`).
- Criteria with a numeric cutoff in the master plan (or else the parameter
  spec) are hard-coded. A **numeric** criterion with no cutoff in either
  document is a required keyword-only argument (`*, max_ppco2_mmhg`); a
  **qualitative** one (headache, SPE, vitamin D trend) is a `bool` argument
  evaluated upstream. Never invent a cutoff.

