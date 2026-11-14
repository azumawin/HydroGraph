# Demo stack

Three containers, one command: the React dashboard behind nginx, the Django
API, and the simulator pushing a scenario into it.

```sh
docker compose up --build
docker compose up                    # again, without rebuilding
```

- Dashboard: <http://localhost:5173>
- API: <http://localhost:8000>, Swagger UI at `/api/docs/`

The dashboard calls `/api/` on its own origin and nginx proxies it to the
backend, so the demo also works from a phone or another laptop at
`http://<your-host>:5173` — nothing is pinned to loopback.

## Picking a scenario

```sh
SCENARIO=badscenario1 docker compose up     # SANS / cephalic fluid shift
SCENARIO=badscenario4 SPEED=30 docker compose up
```

| `SCENARIO`      | What it plays                                |
| --------------- | -------------------------------------------- |
| `healthy`       | nominal crew and cabin (default)             |
| `badscenario1`  | SANS, cephalic fluid shift                   |
| `badscenario2`  | hypercapnia                                  |
| `badscenario3`  | EVA dehydration                              |
| `badscenario4`  | acute infection                              |
| `research_demo` | six months of sparse labs in ~26 seconds     |

`SPEED` (simulation seconds per wall second) and `DURATION` override the
scenario's own pacing, as `make dev SPEED=30` does. Copy `.env.example` to
`.env` to keep a choice instead of retyping it.

## The health assistant

The chat needs an Ollama Cloud key. `backend/.env` is read when it exists, so
the key `make dev` already uses works here too; `OLLAMA_API_KEY=... docker
compose up` works as well. Without a key the dashboard runs normally and only
`/api/assistant/` answers 503. The key is never built into an image.

## The database

Every launch starts from an empty database: the backend deletes it before
migrating, so a scenario always plays from its own beginning and a switch never
leaves the previous run's readings on the graph. Switching `SCENARIO` restarts
the backend for that reason.

- `RESET_DB=0 docker compose up` keeps what the last run recorded.
- `docker compose down -v` also discards the volume it lives on.

## Relation to the Makefile

`make dev` stays the inner-loop setup: it runs the Vite dev server with hot
reload against your working tree. This stack builds the frontend instead, needs
no `uv`, `npm` or Python on the host, and resets state on its own — so it is the
one to reach for when showing the app to someone. Code changes need
`docker compose up --build`.
