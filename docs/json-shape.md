# JSON shapes

Two kinds of JSON: **readings** and **findings**, which change every few seconds,
and the **dictionary**, which is static and sent once. Everything that describes a
channel rather than a measurement (`name`, `scope`, `unit`, `display`,
`body_regions`, `explanation`) lives in the dictionary, so readings carry only what
changes. Every dictionary section is an object keyed by id.

Endpoints: the device sends `POST /api/readings/`; the frontend opens
`GET /api/stream/` (server-sent events), which sends the dictionary first, then the
environment in effect, then readings and findings; the frontend fills its charts
with `GET /api/readings/` (section 2a) and switches the environment with
`PUT /api/environment/`. `GET /api/environments/` serves the environment catalog
keyed by id, and `GET /api/health-conditions/` serves the current finding set
without the stream. Details: `backend/README.md`.

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
  `consciousness_level` is the one text channel: unit `"ACVPU"`, value one of
  `"ALERT"`, `"CONFUSION"`, `"VOICE"`, `"PAIN"`, `"UNRESPONSIVE"`.
- `measured_at` is UTC acquisition time, or the end of the observation window.
  Readings can arrive late and out of order; never overwrite a newer reading with
  an older one.
- Scope comes from the `X-Simulation-Scope` header, not the body. The backend
  monitors one astronaut and ignores `X-Owner-ID`.

## 2. Backend → frontend: reading

`event: reading` on the stream, and the `201` body of the POST. It is the device
body minus `unit` (always the channel's dictionary `unit`), plus the backend's
evaluation:

```json
{
  "channel": "bp_systolic",
  "value": 15198.75216531,
  "measured_at": "2026-11-14T08:00:00Z",
  "evaluation": "unspecified"
}
```

`value` stays in the SI wire unit; show it with the channel's dictionary `display`.

On connect the stream sends the latest reading per `channel`,
then every new one. Late readings are sent too; keep whichever has the newer
`measured_at`.

## 2a. Backend → frontend: reading history

`GET /api/readings/` returns the latest `limit` readings (default 120, 1–1000) of
each channel, oldest first, in the section 2 shape, keyed by channel; channels
without readings are left out. `?channel=` (repeatable) narrows the channels; an
unknown channel or out-of-range `limit` is a `400`.

```json
{ "readings": { "heart_rate": [{ "channel": "heart_rate", "value": 1.2, "measured_at": "2026-11-14T08:00:00Z", "evaluation": "nominal" }] } }
```

The stream's snapshot sends only the latest reading per channel, so the dashboard
requests history once the dictionary arrives (on every (re)connect) and merges it
with live readings by `measured_at`. Evaluations use the environment in effect.

`evaluation` is one of `"nominal" | "warning" | "critical" | "unspecified"`
(`core.Evaluation`). `unspecified` means the specs give no threshold for
this value; it is not "normal".

## 3. Backend → frontend: finding

`event: finding` on the stream: one of the master plan's 10 Tier 1 health
findings. Sent on connect, then again whenever a reading arrives on one of the
finding's input channels.

```json
{
  "id": "radiation_exposure_3_2",
  "status": "critical",
  "triggers": ["solar particle event"],
  "action": "Move to shielded storm shelter zone immediately and confirm hatch closure",
  "values": { "cumulative_dose_msv": 2.8, "dose_rate_usv_h": 19.4 }
}
```

- `id` is the finding (a key of the dictionary's `findings`).
- `status` is `"nominal" | "warning" | "critical"` for every finding. The three
  with one severity (dehydration, energy balance, bone) are `"warning"` when
  present, `"nominal"` when not.
- `triggers` names each criterion that fired; empty when none did.
- `action` is the plan's action card, or `"No finding"`.
- `values` holds the finding's own evaluated quantities, in the units their names
  end in; the keys differ per finding.
- Seven findings are monitored; the other three need inputs the simulator does
  not send and are never sent (their dictionary `channels` is empty).
- `GET /api/health-conditions/` returns the same objects as a JSON array under
  `findings`, for a client that wants them without the stream. A finding whose inputs
  have no reading yet is left out, so an empty array means "nothing evaluated", not
  "all clear".

## 4. Backend → frontend: dictionary

`event: dictionary`, the first message on every stream connection. Static;
join it to readings by `channel` and to findings by `id`.

```json
{
  "environments": {
    "lunar_surface": {
      "name": "Lunar surface",
      "gravity_g": 0.166,
      "comm_delay_rt_s": 2.6,
      "baseline_dose_rate_usv_h": 57.1,
      "storm_shelter_available": true,
      "day_length_h": 708.7
    }
  },
  "channels": {
    "bp_systolic": {
      "name": "Blood pressure (systolic)",
      "scope": "crew",
      "unit": "Pa",
      "display": { "unit": "mmHg", "scale": 0.0075006, "offset": 0.0 },
      "body_regions": ["heart", "chest"],
      "explanation": "Why this is measured, what it means…",
      "schedule_s": 3600
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

- `channels` has one entry per channel the backend accepts (the simulator's 40).
  `scope` is the `X-Simulation-Scope` the device must send; `unit` is the SI wire
  unit of every reading's `value`.
- `display` converts a numeric value for people: `value * scale + offset`, in
  `display.unit`, the spec's clinical unit (mmHg, bpm, °C, µSv/h, ...). It is `""`
  with scale 1 for booleans and dimensionless ratios.
- `schedule_s` is the expected seconds between readings of a routinely sampled
  channel (`core.SCHEDULES`, following the simulator's schedule); `null` for
  event-driven and scenario-only channels. The frontend flags a channel as overdue
  from it.
- `findings` has every **enabled** rule (the 10 built-in ones unless some are disabled, plus custom rules; `backend/README.md`, "Rules endpoints"). The dictionary is re-sent whenever the rule set changes; `channels` lists each one's inputs, empty for
  the three that are not monitored.
- `environments` has four entries, keyed by id, in dropdown order: `iss_leo`, `lunar_surface`,
  `mars_transit`, `mars_surface`. `name` is the dropdown label.
- `comm_delay_rt_s` is the **round-trip** delay — the one that decides whether the
  crew can ask the ground. It is really a range (Mars round trip is 364–2684 s);
  simplified to one number per environment for the demo.
- `baseline_dose_rate_usv_h` is the measured nominal GCR rate inside the habitat, in
  the same unit as finding 10's `dose_rate_usv_h`, so a client can show "elevated"
  against the local baseline instead of an absolute number.
- `storm_shelter_available` says whether finding 10's shelter action is possible; it
  is `true` for all four habitat interiors, and would be `false` for an EVA.
- `day_length_h` is the natural light-dark cycle (1.52 h in LEO, 24.66 h on Mars,
  708.7 h on the Moon; 24 h in transit, where the crew sets its own schedule).
- The selection is display and simulation metadata, with one exception: the dose rate
  (`ambient_dose_rate` and finding 10) is graded as a spike of more than 50 µSv/h above
  the selected environment's `baseline_dose_rate_usv_h`, since the lunar and
  Mars-transit backgrounds alone exceed the plan's absolute 50 µSv/h.
- `body_regions` makes the 3D body figure data-driven: each id is a region of the
  frontend's body model (`frontend/src/components/model/ModelConstants.ts`:
  `head`, `neck`, `chest`, `abdomen`, `pelvis`, limbs) or `heart`; empty when a
  value has no place on the body (blood markers, cabin readings).

## 5. The environment in effect

`event: environment`, sent right after the dictionary and again on every switch, to
every open stream:

```json
{ "id": "mars_transit" }
```

`GET /api/environment/` returns the same object; `PUT /api/environment/` with
`{"id": "mars_transit"}` switches it (`400` for an id not a key of `environments`).
`GET /api/environments/` returns `{"environments": …}`, the dictionary's object. The
default is `iss_leo`. A switch also re-sends the latest `ambient_dose_rate` reading and
the radiation finding, re-graded against the new baseline. The simulator follows the
switch (see `backend-integration.md`, "Following the backend environment").

## Not in scope for the demo

- `Idempotency-Key` deduplication: realistic, since microcontrollers retry, but
  not needed for the demo.
- Uploading a health-history baseline.
