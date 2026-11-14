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
| http://localhost:8000/api/readings/ | `POST` sensor readings |
| http://localhost:8000/api/stream/ | SSE stream for the frontend |
| http://localhost:8000/static/demo/index.html | live demo of the stream |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/api/schema/ | raw OpenAPI 3 schema (YAML) |

There is no auth: every endpoint is public.

`runserver` is daphne's (ASGI), so it can hold the SSE stream open. Under a WSGI server
the stream never sends anything.

## Readings endpoints

Channels, units and thresholds live in core (`hydrograph_core.channels`); the backend
only stores and ships readings. `evaluation` is a `hydrograph_core.Evaluation` value
(`nominal` / `warning` / `critical` / `unspecified`).

Request and message shapes follow `docs/json-shape.md`.

`POST /api/readings/` takes one reading in SI wire units, with owner and scope as
headers, the way the simulator (`imitacija`) sends it:

```sh
curl -X POST localhost:8000/api/readings/ -H 'Content-Type: application/json' \
  -H 'X-Owner-ID: crew-1' -H 'X-Simulation-Scope: crew' \
  -d '{"channel": "spo2", "value": 0.89, "unit": "1", "measured_at": "2026-11-14T08:00:00Z"}'
```

`201` returns the reading with `evaluation`, `owner_id` and `scope` added, and pushes
the same object to every open stream. `400` returns field errors: an unknown
`channel`, a `unit` other than the channel's wire unit, a `value` of the wrong type,
a missing `X-Owner-ID`, or an `X-Simulation-Scope` that doesn't match the channel.
Other simulator headers (`Idempotency-Key`, ...) are ignored for now.

To feed it from the simulator, set `base_url = "http://127.0.0.1:8000"` and
`data_route = "/api/readings/"` in its config.

`GET /api/stream/` is a `text/event-stream`:

- one `dictionary` event: environments and each channel's `name`, `body_regions`
  and `explanation`;
- then the latest `reading` per owner and channel;
- then a `reading` event for every new reading, pushed the moment it is POSTed.

Delivery is an in-memory queue per open stream (`api/broadcast.py`), so it needs a
single server process, which `runserver` is. A reconnect (`EventSource`'s automatic
retry) gets a fresh snapshot.

```js
const es = new EventSource("/api/stream/");
es.addEventListener("dictionary", (e) => setDictionary(JSON.parse(e.data)));
es.addEventListener("reading", (e) => upsertReading(JSON.parse(e.data)));
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
