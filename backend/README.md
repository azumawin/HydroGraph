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
python manage.py createsuperuser
python manage.py runserver
```

if u dont use nix:
```sh
cd backend
uv sync
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Useful URLs once `runserver` is up:

| URL | What |
| --- | --- |
| http://localhost:8000/api/health/ | liveness probe, public |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/api/schema/ | raw OpenAPI 3 schema (YAML) |
| http://localhost:8000/admin/ | Django admin |
| http://localhost:8000/api-auth/login/ | session login for the DRF browsable API |

DRF defaults to `IsAuthenticated`, so every endpoint except `health` needs a logged-in
session (or a token) — log in via `/api-auth/login/` to browse the API in your browser.

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

`packages/hydrograph-core/` holds the HydroGFN health-monitor logic: sensor formulas,
the 10 health findings, the adaptive polling table and the JSON telemetry
payload. It is stateless; the backend keeps sessions, user state and history.
How `api/` should call it: `packages/hydrograph-core/README.md`, "Using it from the
Django backend".
