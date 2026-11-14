# JSON shapes

Two kinds of JSON: **readings**, which change every few seconds, and the
**dictionary**, which is static and fetched once. Everything that describes a
channel rather than a measurement (`name`, `explanation`, `body_regions`) lives
in the dictionary, so readings stay small.

Endpoints: the device sends `POST /api/readings/`; the frontend opens
`GET /api/stream/` (server-sent events), which sends the dictionary first, then
readings and findings. Details: `backend/README.md`.

## 1. Device → backend: reading body

The simulator (`imitacija`) posts one reading per request. Transport, headers,
retries and the full channel registry: `backend-integration.md`.

```json
{
  "channel": "bp_systolic",
  "value": 15198.75216531,
  "unit": "Pa",
  "measured_at": "2026-11-14T08:00:00Z"
}
```

- Exactly these four fields.
- `unit` is the SI wire unit of `value` (here 114 mmHg sent as Pa). Booleans use
  `"boolean"` and a JSON `true`/`false` value; dimensionless ratios use `"1"`.
- `measured_at` is UTC acquisition time, or the end of the observation window.
  Readings can arrive late and out of order; never overwrite a newer reading with
  an older one.
- Scope comes from the `X-Simulation-Scope` header, not the body. The backend
  monitors one astronaut and ignores `X-Owner-ID`.

## 2. Backend → frontend: reading

`event: reading` on the stream, and the `201` body of the POST. It is the device
body plus the backend's evaluation and the scope header:

```json
{
  "channel": "bp_systolic",
  "value": 15198.75216531,
  "unit": "Pa",
  "evaluation": "unspecified",
  "measured_at": "2026-11-14T08:00:00Z",
  "scope": "crew"
}
```

On connect the stream sends the latest reading per `channel`,
then every new one. Late readings are sent too; keep whichever has the newer
`measured_at`.

`evaluation` is one of `"nominal" | "warning" | "critical" | "unspecified"`
(`hydrograph_core.Evaluation`). `unspecified` means the specs give no threshold for
this value; it is not "normal".

## 3. Backend → frontend: finding

`event: finding` on the stream: one of the master plan's 10 Tier 1 health
findings. Sent on connect, then again whenever a reading arrives on one of the
finding's input channels.

```json
{
  "id": "radiation_exposure_3_2",
  "cumulative_dose_msv": 2.8,
  "dose_rate_usv_h": 19.4,
  "triggers": ["solar particle event"],
  "status": "critical",
  "action": "Move to shielded storm shelter zone immediately and confirm hatch closure"
}
```

- `id` is the finding (a key of the dictionary's `findings`); the keys between
  `id` and `triggers` are that finding's evaluated values.
- `triggers` names each criterion that fired; empty when none did.
- `status` is `true` / `false` (finding present or not) for findings with one
  severity (dehydration, energy balance, bone), otherwise
  `"nominal" | "warning" | "critical"`.
- `action` is the plan's action card, or `"No finding"`.
- Seven findings are monitored; the other three need inputs the simulator does
  not send and are never sent (their dictionary `channels` is empty).

## 4. Backend → frontend: dictionary

`event: dictionary`, the first message on every stream connection. Static;
join it to readings by `channel` and to findings by `id`.

```json
{
  "environments": [
    { "id": "lunar_surface", "gravity_g": 0.166, "comm_delay_s": 2.6 },
    { "id": "mars_surface", "gravity_g": 0.377, "comm_delay_s": 600 }
  ],
  "channels": {
    "bp_systolic": {
      "name": "Blood pressure (systolic)",
      "body_regions": ["heart", "chest"],
      "explanation": "Why this is measured, what it means…"
    }
  },
  "findings": {
    "radiation_exposure_3_2": {
      "name": "Radiation dose & solar particle events",
      "channels": ["ambient_integrated_dose", "ambient_dose_rate", "spe_flag"]
    }
  }
}
```

- `channels` has one entry per channel the backend accepts (the simulator's 35).
- `findings` has all 10 findings; `channels` lists each one's inputs, empty for
  the three that are not monitored.
- `comm_delay_s` is really a range; simplified to one number for the demo.
- `body_regions` makes the clickable body figure data-driven instead of a
  hardcoded SVG switch statement.

## Not in scope for the demo

- `Idempotency-Key` deduplication: realistic, since microcontrollers retry, but
  not needed for the demo.
- Uploading a health-history baseline.
