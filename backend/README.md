# HydroGraph backend

Django + Django REST Framework API, plus the pure-logic packages it builds on.

```
backend/
├── pyproject.toml          uv workspace root (virtual project — not installable)
├── manage.py
├── config/                 Django project: settings, urls, asgi, wsgi
├── api/                    Django app — the DRF layer (views, serializers, urls)
└── packages/
    └── hydrograph-core/    domain logic, no Django imports
```

The split matters: `packages/*` hold logic that can be imported and tested without a
Django settings module. `api/` stays thin — validation, serialization, routing.

## Prerequisites

- Python 3.14
- uv

or just use Nix

## Getting started

From the repo root, `make sync` installs everything once; then `make dev` migrates,
starts the backend and the frontend (`frontend/`, http://127.0.0.1:5173), opens the
frontend and feeds it from the simulator; Ctrl+C stops all three. `make` lists every
target (`run`, `frontend`, `sim`, `test`, `lint`, `check`, ...).

create `.env` with env vars described in [here](##Configuration)

if u use nix:
```sh
cd backend
nix develop # entering the shell runs uv sync automatically
python manage.py migrate
python manage.py runserver
```

if u dont use nix:
```sh
cd backend
uv sync
python manage.py migrate
python manage.py runserver
```

Useful URLs once `runserver` is up:

| URL | What |
| --- | --- |
| http://localhost:8000/api/health/ | liveness probe |
| http://localhost:8000/api/environments/ | the predefined mission environments |
| http://localhost:8000/api/environment/ | the environment in effect; `PUT` switches it |
| http://localhost:8000/api/health-conditions/ | the findings the crew member may have |
| http://localhost:8000/api/readings/ | `POST` sensor readings |
| http://localhost:8000/api/stream/ | SSE stream for the frontend |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/api/schema/ | raw OpenAPI 3 schema (YAML) |

There is no auth: every endpoint is public.

`runserver` is daphne's (ASGI), so it can hold the SSE stream open. Under a WSGI server
the stream never sends anything.

## Environments endpoint

`GET /api/environments/` returns the environments the dashboard's switcher offers,
straight from core (`hydrograph_core.environments`):

```json
{
  "environments": [
    {
      "id": "lunar_surface",
      "name": "Lunar surface",
      "gravity_g": 0.166,
      "comm_delay_rt_s": 2.6,
      "baseline_dose_rate_usv_h": 57.1,
      "storm_shelter_available": true,
      "day_length_h": 708.7
    }
  ]
}
```

Four environments, in dropdown order: `iss_leo`, `lunar_surface`, `mars_transit`,
`mars_surface`. They cover the two axes without redundancy — gravity at 0 / 0.166 /
0.377 g, round-trip delay from 1.2 s to 26 min — with `mars_transit` as the worst
case (0 g, full autonomy, unshielded GCR).

| field | meaning |
| --- | --- |
| `comm_delay_rt_s` | **round-trip** delay: can the crew ask the ground at all |
| `baseline_dose_rate_usv_h` | measured nominal GCR rate inside the habitat, in Finding 10's unit |
| `storm_shelter_available` | whether Finding 10's "move to the storm shelter" is possible |
| `day_length_h` | natural light-dark cycle, Finding 5's circadian premise |

Delay is really a range (Mars round trip is 364–2684 s); each value is one
representative number for the demo. Dose rates are measured values, cited in
`hydrograph_core.environments` — note that `lunar_surface` (57.1) and `mars_transit`
(76.7) sit **above** Finding 10's fixed 50 µSv/h warning cutoff, so that finding warns
at rest in those environments until the cutoff becomes baseline-relative.

Static, so one fetch is enough. The stream `dictionary` event carries the same list
(both call `environments_payload()`), so a client that opens the stream needs neither
this endpoint nor a second fetch.

`GET /api/environment/` returns the environment in effect (`{"id": "iss_leo"}` until one
is chosen); `PUT` with `{"id": ...}` switches it (`api/environment.py`, stored as
`EnvironmentSelection` rows so it survives restarts). A switch is pushed to every
stream as an `environment` event, and a simulator with `follow_backend_environment`
picks it up within `environment_poll_wall_s`. The dose rate is graded above the
selected environment's baseline, so a switch also re-sends the latest dose-rate reading
and the radiation finding. The API answers any origin (`django-cors-headers`), since the
frontend dev server runs on another port.

## Health conditions endpoint

`GET /api/health-conditions/` takes the latest reading of every channel, runs the
Tier 1 findings over them, and returns the conditions those readings support:

```json
{
  "findings": [
    {
      "id": "radiation_exposure_3_2",
      "cumulative_dose_msv": 1.0,
      "dose_rate_usv_h": 18.0,
      "triggers": ["solar particle event"],
      "status": "critical",
      "action": "Move to shielded storm shelter zone immediately and confirm hatch closure"
    }
  ]
}
```

Each entry is exactly a stream `finding` event — both call `finding_payload()` over
`crew_findings()` — so the frontend can fetch the conditions once instead of opening
the stream, or re-sync after a dropped connection. A test asserts that equality.

A finding whose input channels have no reading yet is **left out**, not reported as
absent: an empty `findings` array means "nothing evaluated", not "all clear". Three of
the ten are never in the response at all, because the simulator sends none of their
channels (orthostatic, sleep, behavioral). The dictionary's `findings` lists all ten
with their input channels, empty for those three.

Entry shape and `status` semantics: `docs/json-shape.md`, section 3.

## Readings endpoints

Channels, units and thresholds live in core (`hydrograph_core.channels`); the backend
only stores and ships readings. `evaluation` is a `hydrograph_core.Evaluation` value
(`nominal` / `warning` / `critical` / `unspecified`).

Request and message shapes follow `docs/json-shape.md`.

`POST /api/readings/` takes one reading in SI wire units, with its scope as a header,
the way the simulator (`imitacija`) sends it:

```sh
curl -X POST localhost:8000/api/readings/ -H 'Content-Type: application/json' \
  -H 'X-Simulation-Scope: crew' \
  -d '{"channel": "spo2", "value": 0.89, "unit": "1", "measured_at": "2026-11-14T08:00:00Z"}'
```

`201` returns the reading with `evaluation` and `scope` added, and pushes the same
object to every open stream. `400` returns field errors: an unknown `channel`, a
`unit` other than the channel's wire unit, a `value` of the wrong type, or an
`X-Simulation-Scope` that doesn't match the channel. Other simulator headers
(`X-Owner-ID`, `Idempotency-Key`, ...) are ignored.

The backend monitors **one astronaut**: every crew reading is theirs, and findings use
the latest reading of each channel. A simulator config with several `[[crew]]`
members would mix their readings.

To feed it from the simulator, set `base_url = "http://127.0.0.1:8000"` and
`data_route = "/api/readings/"` in its config.

`GET /api/stream/` is a `text/event-stream`:

- one `dictionary` event: environments, each channel's `name`, `body_regions` and
  `explanation`, and each finding's `name` and input `channels`;
- one `environment` event with the environment in effect;
- then the latest `reading` per channel, and the current `finding`s;
- then, the moment a reading is POSTed, its `reading` event and a `finding` event
  for each finding that uses its channel; an `environment` event on every switch.

Findings come from core (`hydrograph_core.assessment`): seven of the master plan's ten
are monitored, from the latest crew and cabin readings (`api/findings.py`). The other
three (orthostatic, sleep, behavioral) need inputs the simulator does not send.

Delivery is an in-memory queue per open stream (`api/broadcast.py`), so it needs a
single server process, which `runserver` is. A reconnect (`EventSource`'s automatic
retry) gets a fresh snapshot.

```js
const es = new EventSource("/api/stream/");
es.addEventListener("dictionary", (e) => setDictionary(JSON.parse(e.data)));
es.addEventListener("reading", (e) => upsertReading(JSON.parse(e.data)));
es.addEventListener("finding", (e) => upsertFinding(JSON.parse(e.data)));
```

## Everyday commands

```sh
pytest                      # whole suite
pytest api/tests.py -k health
ruff check . --fix          # lint
black .                     # format
basedpyright                # type check
python manage.py makemigrations
python manage.py migrate
python manage.py shell
```

## Configuration

Settings read from the environment with dev-friendly fallbacks:

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | the insecure generated key | **must** be set outside local dev |
| `DJANGO_DEBUG` | `1` | any value other than `1` disables debug |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated |

The database is SQLite at `backend/db.sqlite3` (gitignored). Delete it and re-run
`migrate` to start clean.

## API documentation

`drf-spectacular` generates an OpenAPI 3 schema from the DRF views and serves Swagger UI
over it. Start the server and open <http://localhost:8000/api/docs/>:

```sh
python manage.py runserver
```

- `/api/schema/` serves the raw OpenAPI document the UI reads.
- Both URLs are public (`SERVE_PERMISSIONS` in `SPECTACULAR_SETTINGS`); tighten for production.
- Annotate views with `@extend_schema` to improve what the docs show — `health` has an example.

To swap the UI, change one line in `config/urls.py` — `SpectacularRedocView` for Redoc, or
drop the `api/docs/` path to remove the docs entirely.

## Adding a logic package

```sh
mkdir -p packages/hydrograph-foo/src/hydrograph_foo
```

Give it a `pyproject.toml` copied from `packages/hydrograph-core/pyproject.toml` (same
`uv_build` build system, new `name`), then declare it in the root `pyproject.toml`:

```toml
[project]
dependencies = [..., "hydrograph-foo"]

[tool.uv.sources]
hydrograph-foo = { workspace = true }
```

`uv sync` installs it editable — imports resolve immediately, no reinstall after edits.
The `members = ["packages/*"]` glob already covers the new directory.

## Adding an endpoint

1. Model in `api/models.py`, then `makemigrations` + `migrate`.
2. `ModelSerializer` in `api/serializers.py`.
3. `ModelViewSet` in `api/views.py`, delegating real work to a `packages/*` module.
4. Register it on the router in `api/urls.py` (there's a commented example).

## HydroGFN domain logic

`packages/hydrograph-core/` holds the HydroGFN health-monitor logic: the 10 Tier 1
health findings. It is stateless; the backend keeps sessions, user state and history.
How `api/` should call it: `packages/hydrograph-core/README.md`, "Using it from the
Django backend".
