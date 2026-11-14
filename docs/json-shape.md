# JSON shapes

Two kinds of JSON: **readings**, which change every few seconds, and the
**dictionary**, which is static and fetched once. Everything that describes a
channel rather than a measurement (`name`, `explanation`, `body_regions`) lives
in the dictionary, so readings stay small.

Endpoints: the device sends `POST /api/readings/`; the frontend opens
`GET /api/stream/` (server-sent events), which sends the dictionary first, then
readings. Details: `backend/README.md`.

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
- Owner and scope come from headers (`X-Owner-ID`, `X-Simulation-Scope`), not the
  body.

## 2. Backend → frontend: reading

`event: reading` on the stream, and the `201` body of the POST. It is the device
body plus the backend's evaluation and the owner and scope headers:

```json
{
  "channel": "bp_systolic",
  "value": 15198.75216531,
  "unit": "Pa",
  "evaluation": "unspecified",
  "measured_at": "2026-11-14T08:00:00Z",
  "owner_id": "crew-1",
  "scope": "crew"
}
```

On connect the stream sends the latest reading per `owner_id` and `channel`,
then every new one. Late readings are sent too; keep whichever has the newer
`measured_at`.

`evaluation` is one of `"nominal" | "warning" | "critical" | "unspecified"`
(`hydrograph_core.Status`). `unspecified` means the specs give no threshold for
this value; it is not "normal".

## 3. Backend → frontend: dictionary

`event: dictionary`, the first message on every stream connection. Static;
join it to readings by `channel`.

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
  }
}
```

- `channels` has one entry per channel the backend accepts (the simulator's 29).
- `comm_delay_s` is really a range; simplified to one number for the demo.
- `body_regions` makes the clickable body figure data-driven instead of a
  hardcoded SVG switch statement.

## Not in scope for the demo

- Auth: the user id will come from a request header.
- `Idempotency-Key` deduplication: realistic, since microcontrollers retry, but
  not needed for the demo.
- Uploading a health-history baseline.
