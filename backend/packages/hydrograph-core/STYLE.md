# hydrograph-core style guide

`hydrograph_core` implements the HydroGFN health monitor from two documents in this directory:

- `Tiered Master System Specification & Implementation Plan.pdf` (the
  **master plan**): the Tier 1 / Tier 2 split, the 10 health findings.
- `NSA_hydrograph.md` (the **parameter spec**): formulas and thresholds for
  each sensor "Parameter N.M".

When they disagree, **the master plan wins**. Note the override in the
function's docstring.

## Layout

This package is one uv workspace member of `backend/`. `src/hydrograph_core/` is one
self-contained, flat module: no subpackages, no imports from outside its
directory, standard library only. Its docs stay in this package directory.

```
hydrograph_core/
  __init__.py         public API: the 10 finding functions, Status, the
                      channel and environment catalogs
  shared.py           code shared across files (the Status enum)
  findings.py         Tier 1: main-window health findings 1-10
  channels.py         sensor channels: display info (CHANNELS) and the grade of
                      one reading on its own (evaluate_reading)
  environments.py     mission environments (ENVIRONMENTS)
```

Tier 1 combines vitals and Tier 2 values (sensor readings turned into
physical values, computed outside this package) into the 10 findings and their
action cards. Everything here is a stateless library for the backend, which
keeps all state. The dashboard does not live here.

Which Tier 2 parameter of the parameter spec feeds which finding:

| Param | Tier 2 panel section | Feeds Tier 1 finding |
| --- | --- | --- |
| 1.1 ICP / strain | Hydrogel piezoresistive strain | #9 SANS & cephalic fluid shift |
| 1.2 cTnI | GFET signal gating | #1 Orthostatic intolerance (event-triggered) |
| 1.3 MAP / HR | none | #1 Orthostatic intolerance |
| 2.1 Glucose | none | #7 Negative energy balance |
| 2.2 Core temp | none | #3 Acute infection (SIRS), Tier 1 vitals row |
| 3.1 NTx | GFET signal gating, biomarker kinetics | #8 Bone demineralization |
| 3.2 Joint angles | Hydrogel strain | 3D kinematic body model |
| 4.1 Cortisol | GFET signal gating, biomarker kinetics | #6 Behavioral health & HPA-axis |
| 4.2 CFE | Neuro-cognitive spectrum | #5 Sleep, #6 Behavioral |
| 4.3 SQI / mood | none | #5 Sleep, Tier 1 mood score |
| 5.1 IL-6 / TNF-α | GFET signal gating | #3 Acute infection |

## Tooling

Python >= 3.14, standard library only at runtime. Dev tools come from the
backend workspace (`backend/pyproject.toml`). From `backend/`:

```sh
uv sync                                     # dev tools
black packages/hydrograph-core              # format; commit only black-clean code
ruff check packages/hydrograph-core         # lint
basedpyright packages/hydrograph-core       # must report 0 errors, 0 warnings
pytest packages/hydrograph-core             # tests
```

Inside the module, always import relatively (`from .shared import Status`)
so it works under any directory name.

## Module shape

```python
"""Tier 1: the 10 personal health findings (master plan, section 2)."""

from __future__ import annotations
import math
from typing import TypedDict

from .shared import Status


class SansResult(TypedDict):
    finding: str
    jugular_distension_pct: float
    triggers: list[str]
    status: Status
    action: str


def sans_fluid_shift_1_3(...) -> SansResult:
    ...
```

- Standard library only. `math` is usually all you need.
- No classes other than the result `TypedDict`s, no recursion, no I/O, no global state.
- Each finding function is self-contained: no shared helpers between findings. A
  small amount of repeated code is preferred over coupling.
- Spec constants (physical constants, model coefficients, fixed sensor
  geometry) are local variables with a comment giving the units, not arguments.

## Names

Names put the number(s) **after** a descriptive name:

- Finding function: `<finding>_D_S`, D the finding's hazard domain and S its
  place within that domain (`orthostatic_intolerance_1_1`,
  `radiation_exposure_3_2`). The master plan does not number domains; the
  numbering and the map to plan finding numbers are in the `findings.py`
  module docstring. Every one is exported from `__init__.py` and listed in
  `__all__`.

## Signatures

- Live sensor readings come first and have no default.
- Only values measured per sensor or per person are arguments after them, with
  the spec value as the default (`r0`, the sensor's resistance at t = 0;
  `icp_baseline`, the person's supine ICP). Everything else the spec fixes is a
  local constant.
- A value the spec needs but never gives is a required keyword-only argument
  (`*, w1, w2`). Never invent a default.
- `snake_case` names, lowercase even for symbols (`n_b`, `lambda_d`, `k_enz`).
- Add a unit suffix when the unit is not obvious from the name:
  `_mm`, `_ms`, `_s`, `_days`, `_hours`, `_nm`, `_ng_ml`, `_pct`.
- Each function returns its own `TypedDict`, named after the quantity
  (`GlucoseResult`, `CfeResult`), declared at the top of the module with keys
  in return order.

## Docstring

Raw string, in this order.

```python
r"""
Finding N: <master plan title> (<primary domain>).

References:
    <every citation the master plan gives for this finding, copied in full>

Args:
    name: Description [unit], e.g. from Parameter N.M.

Returns:
    ``finding``, ``<value keys>``, ``triggers``, ``status``, ``action``.
    <How status is derived; every boundary choice or spec gap you resolved.>
"""
```

Write a `#` comment in the body only for something the docstring cannot carry,
e.g. why a value is rounded before classification.

## Return value

```python
return {
    "finding": "N",
    "<value>_<unit>": round(value, k),
    ...
    "triggers": triggers,
    "status": status,
    "action": action,
}
```

- Keys: `finding` (`"1"`-`"10"`), then the evaluated values in the order they
  are derived, then `triggers` (a `list[str]` naming each criterion that
  fired, for the dashboard's `primary_hazard`), `status`, `action`.
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

Callers supply finite inputs; do not check for NaN, infinity or sign of
inputs.

## Findings

- One function per finding (see Names), all in `findings.py`.
- The action is the master plan's action card verbatim, minus the quotes and
  trailing period. No finding: `Status.NOMINAL`, `"No finding"`.
- Any criterion fired is `WARNING`, unless the plan marks it urgent or an
  immediate shelter alert (`CRITICAL`).
- Criteria with a numeric cutoff in the master plan (or else the parameter
  spec) are hard-coded. A **numeric** criterion with no cutoff in either
  document is a required keyword-only argument (`*, max_ppco2_mmhg`); a
  **qualitative** one (headache, SPE, vitamin D trend) is a `bool` argument
  evaluated upstream. Never invent a cutoff.

## Channels

`channels.py` grades one reading of one channel, for the backend's per-reading
`evaluation`. It follows the Classification rules above, with three differences:

- `evaluate_reading` returns a bare `Status`, no result dict or action: the
  channel's `explanation` in `CHANNELS` carries the text.
- Values arrive in SI wire units (the simulator's registry). Each `case`
  converts to the spec's unit first (`bpm = value * 60.0`), so cutoffs read
  exactly as in the document, and comments the document and band they come from.
- Boolean channels take `True` / `False`.
- An unknown channel raises `ValueError`.
