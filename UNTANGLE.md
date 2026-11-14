# UNTANGLE.md

Working plan to unslop and untangle HydroGraph. Read-only analysis was done on
2026-11-15. No tests, lint, or edits were run as part of writing this document.

Decisions taken:
- Harden the demo boundary by moving fan-out to Django Channels.
- Keep the HTTP SSE contract and all JSON shapes in `docs/json-shape.md` stable.

---

## 1. System map

### 1.1 Components

| Path | Role |
| --- | --- |
| `backend/` | Django + DRF API. Owns persistence, grading, findings, SSE. |
| `backend/packages/hydrograph-core/` | Pure domain library. Channels, findings, environments. No Django. |
| `imitacija/` | Telemetry simulator. Config TOML -> physiology -> SI readings -> HTTP POST. |
| `frontend/` | React dashboard. EventSource + REST, Zustand store, charts, 3D body, WebGL background. |
| `e2e/` | Playwright tests that start the real stack. |

### 1.2 Runtime data flows

**Ingestion**

```
imitacija config.toml
  -> Settings (pydantic) -> Scheduler rules
  -> physiology/scenarios -> Reading in SI wire units
  -> Delivery (httpx)
       POST /api/readings/
       headers: X-Simulation-Scope, X-Owner-ID, Idempotency-Key, ...
  -> api/views.py:readings
       ReadingInSerializer validates channel, unit, value type, scope
       -> Reading row
       -> reading_payload() -> evaluate_reading() (environment-dependent only for dose rate)
       -> publish SSE "reading"
       -> affected_findings() -> crew_findings() -> core.evaluate_findings()
       -> publish SSE "finding"
```

**Stream**

```
api/stream.py:events()
  dictionary_payload()
  broadcast.subscribe()
  environment event
  latest reading per channel (40 queries)
  all crew_findings (N queries)
  queue.get() forever
```

**Read-only views**

```
GET /api/health-conditions/ -> crew_findings(current_environment())
GET /api/readings/?limit&channel -> latest N per channel, oldest first
GET /api/environments/ -> core.ENVIRONMENTS
GET /api/environment/ -> latest EnvironmentSelection, else DEFAULT_ENVIRONMENT
PUT /api/environment/ -> create EnvironmentSelection
  -> publish environment
  -> publish latest ambient_dose_rate re-graded
  -> publish radiation finding re-graded
```

**Assistant**

```
POST /api/assistant/
  -> rate limit per IP (LocMem cache)
  -> briefing(): environment + findings + latest reading per channel
  -> Ollama Cloud /api/chat
```

**Frontend**

```
main.tsx -> App -> VitalsDashboard
  -> useVitalsDashboardInit -> store.connectTelemetry() (once)
  -> Service.openTelemetryStream()
       dictionary  -> store.dictionary, then GET /api/readings/?limit=120
       reading     -> pending buffer -> 250ms flush -> readings + history
       finding     -> pending buffer -> flush -> findings
       environment -> environmentId
  -> PUT /api/environment/ via selectEnvironment()
  -> POST /api/assistant/ from HealthAssistant local state
```

### 1.3 Contracts

- `docs/json-shape.md` is the wire contract.
- `hydrograph_core.CHANNELS` determines accepted channels and display conversion.
- `hydrograph_core.FINDINGS` determines monitored findings and input channels.
- `imitacija` has its own registry and must stay compatible with core.
- The simulator owns SI values; the backend adds `evaluation`; the frontend applies `display`.

---

## 2. Slop inventory

Severity:
- P0: correctness or contract drift; fix before new features.
- P1: duplicate source of truth; causes future drift.
- P2: maintainability and performance.
- P3: repo hygiene.
- P4: product or scientific decisions.

### P0 - correctness / contract drift

1. Simulator schedule has four representations:
   - dead `_CHANNELS` schedule/window literals: `imitacija/src/imitacija/registry.py:105-633`
   - overwritten from `FREQUENCIES`: `registry.py:635-641`
   - hardcoded calendar/event rules: `scheduler.py:112-158`
   - scenario overrides: `scheduler.py:185-239`
   - dictionary overrides: `registry.py:731-767`
   Cortisol already drifts between `frequency.py`, `scheduler.py`, and `registry.py`.
2. Environment follow bypasses validation:
   - `Scheduler.set_environment()` uses `model_copy(update=...)`: `scheduler.py:244-264`
   - unknown environment IDs silently ignored: `main.py:63`
   - `float(str(...))` hides JSON type mistakes: `main.py:66-68`
   - `environment.id` and `pressure_pa` are not updated.
3. Preview baseline duplicates startup and misses SANS/infection context:
   - `preview.py:69-111` vs `scheduler.py:358-417`
4. Backend contract docs contradict themselves:
   - `imitacija/docs/backend_contract.md:10` says remove `environment_route`
   - `:98-109` documents and code uses it.
5. Channel counts are wrong in docs:
   - `docs/json-shape.md:149` and `backend/README.md:194` say 35
   - core has 40 (35 crew + 5 environment).

### P1 - duplicate sources of truth

6. ACVPU tuple duplicated:
   - `backend/api/serializers.py:27`
   - `backend/packages/hydrograph-core/src/hydrograph_core/channels.py:477`
   - `.../assessment.py:215` and `:403`
   - `imitacija/src/imitacija/models.py:32`
   - `imitacija/src/imitacija/registry.py:814`
7. "Latest reading" is implemented four times:
   - `backend/api/findings.py:28-47`
   - `backend/api/stream.py:36-41`
   - `backend/api/views.py:291-300`
   - `backend/api/assistant.py:70-85`
8. No single current-state service:
   - stream, health-conditions, and assistant each assemble env + readings + findings.
9. Dictionary version duplicated:
   - `imitacija/src/imitacija/delivery.py:123`
   - `imitacija/src/imitacija/registry.py:710`

### P2 - maintainability and performance

10. `backend/api/broadcast.py:11-17` uses unbounded per-stream queues, no heartbeat, no backpressure, single-process only.
11. Large inline `@extend_schema` dicts dominate `backend/api/views.py` (337 lines, schema + logic mixed).
12. `frontend/src/components/VitalsDashboardBackground.tsx` is 379 lines mixing shaders, WebGL engine, resize, theme, and JSX.
13. `frontend/src/components/HealthAssistant.tsx:107` uses array index as key.
14. `frontend/src/components/VitalsPanel.tsx:14` uses `flatMap` over a single reading.
15. Frontend README is stale:
    - `frontend/README.md:16` claims `VITALS_DISPLAY_UNITS` converts units.
    - Actual conversion is the backend dictionary `display` in `useTelemetryStore.ts:42-51`.
    - Vite proxy note no longer applies.
16. Unused dependencies/assets/dead code:
    - `frontend/package.json:18` `motion` unused
    - `frontend/src/assets/images/concept_art.png` unused
    - `backend/pyproject.toml` `markdown` unused
    - `backend/api/urls.py:6-7` dead `DefaultRouter` and commented register
17. Backend N+1 queries in findings, stream snapshot, history, and assistant.
18. `crew_findings` re-queries all latest readings for every new reading via `affected_findings`.

### P3 - repo hygiene

19. `.claude/worktrees/*` is about 893 MB of stale agent worktrees.
20. There is an external worktree at `/Users/user/projects/HydroGraph-imitation`.
21. No CI. `make lint` calls `basedpyright` but it is not in backend dev deps.
22. `Makefile:62` has the e2e formatter commented out.
23. `frontend/AGENTS.md` references `EXAMPLE_OLD_PROJ`, which is absent.
24. `imitacija` docs sprawl: 16 docs, about 2674 lines, stale channel counts in
    `readme.md`, `docs/channel_catalog.md`, `docs/model_assumptions.md`, and
    `badscenario*.md`.

### P4 - product and scientific decisions

25. `backend/api/assistant.py:20-35` hardcodes a blocklist of Chinese-lab model
    names. This is policy, not domain logic. Remove or make it configuration.
26. Simulator config is inert:
    - `sex` and `postmenopausal` (`models.py:55-56`) only validate.
    - `pressure_pa` (`models.py:83`) only participates in validation.
    - `co2_ppm` (`units.py:13-17`) is test-only.
    - `dose_offset_msv` is internal but accepted from TOML.
27. `mismatches.md` and `sus.md` contain scientific disagreements that need an
    owner decision, not a code refactor.

---

## 3. Target architecture

### 3.1 Metadata ownership

- `hydrograph_core` remains the backend authority for channels, findings, environments.
- `imitacija` keeps its own runtime registry, but `FREQUENCIES` becomes the only
  schedule/window authority. `_CHANNELS` stops carrying schedule literals.
- Calendar and event-driven rules live in one place and are rendered into the
  dictionary from that same source.
- Docs that state counts are generated from `--dictionary` or asserted by tests.

### 3.2 Backend state service

Create `backend/api/state.py`:

```
latest_readings(channels) -> dict[str, Reading]
current_state(environment) -> State
    environment: EnvironmentInfo
    readings: dict[str, Reading]
    findings: dict[str, FindingResult]
```

- One query for latest readings (subquery or window function).
- `crew_findings`, `stream`, `health_conditions`, `reading_history`, and
  `assistant` consume it.
- `affected_findings` still computes only the findings for the new channel, but
  reads from a shared latest map instead of re-querying.

### 3.3 SSE via Django Channels

Keep the SSE contract; replace `api/broadcast.py`.

- Add `channels` dependency and `CHANNEL_LAYERS` in `config/settings.py`.
- Dev default: `channels.layers.InMemoryChannelLayer`.
- Production option: Redis channel layer, documented but not required for the demo.
- `config/asgi.py` can keep `get_asgi_application()` because SSE stays an async
  view; a channel layer does not require consumers.
- New `backend/api/events.py`:
  - `GROUP = "telemetry"`
  - `publish(message)` -> `async_to_sync(layer.group_send)(GROUP, {"type": "telemetry.message", "text": message})`
  - `subscribe()` -> async context manager:
    - `channel_name = await layer.new_channel()` or `uuid4().hex`
    - `await layer.group_add(GROUP, channel_name)`
    - yield a receiver that awaits `layer.receive(channel_name)`
    - finally `await layer.group_discard(GROUP, channel_name)`
- `api/stream.py`:
  - await `receive()` with `asyncio.wait_for(..., timeout=HEARTBEAT_S)`
  - on timeout yield `: keepalive\n\n`
  - on client disconnect exit the async generator and discard the group.
- `api/views.py` keeps calling `publish(...)`; only the import changes.
- Update `backend/api/test_stream.py`: remove access to `broadcast._queues`;
  test group membership through the new public API.

Boundedness:
- `InMemoryChannelLayer` does not provide backpressure. For the demo, a slow
  client is closed on write failure. For multi-worker production, use Redis and
  add a max lag policy.

### 3.4 Frontend boundaries

- `Service.ts` stays the runtime validation boundary.
- `useTelemetryStore` owns server state and live merge.
- Extract pure helpers:
  - `src/telemetry/mergeReadings.ts`
  - `src/telemetry/history.ts`
- Split the plasma background:
  - `src/components/background/plasmaShaders.ts`
  - `src/components/background/usePlasmaBackground.ts`
  - `VitalsDashboardBackground.tsx` becomes presentation plus status.
- Keep `Constants.ts` as the single constants module; do not create a constants
  tree unless a concrete need appears.
- Remove unused `motion` and `concept_art.png`.

---

## 4. Execution plan

### Phase 0 - hygiene

- [ ] Remove `.claude/worktrees/*` with `git worktree remove`; run `git worktree prune`.
- [ ] Add `.claude/` to root `.gitignore`.
- [ ] Remove `frontend/src/assets/images/concept_art.png`.
- [ ] Remove `motion` from `frontend/package.json` and update the lockfile.
- [ ] Remove `markdown` from `backend/pyproject.toml` and sync.
- [ ] Remove dead `DefaultRouter` and commented register from `backend/api/urls.py`.
- [ ] Fix `frontend/README.md:16` and the Vite proxy note.
- [ ] Fix channel counts in `docs/json-shape.md:149` and `backend/README.md:194`.
- [ ] Restore or delete the commented e2e formatter line in `Makefile:62`.
- [ ] Decide whether `frontend/AGENTS.md` keeps the absent `EXAMPLE_OLD_PROJ` references.

Acceptance:
- `make lint` passes.
- `make test` passes.
- No unused dependency or asset introduced by the changes.

### Phase 1 - metadata single source of truth

- [ ] Make `FREQUENCIES` the only schedule/window authority in `imitacija`.
- [ ] Delete or generate the dead `_CHANNELS` schedule/window literals.
- [ ] Unify calendar/event rules and scenario overrides into one rule registry.
- [ ] Render dictionary `collection_schedule` from the same source.
- [ ] Add tests:
  - every enabled channel has a frequency group
  - every group has a runtime rule
  - dictionary schedule equals runtime rule
- [ ] Export one `ACVPU` constant from `hydrograph_core`.
- [ ] Use that constant in `serializers.py`, `channels.py`, `assessment.py`.
- [ ] Add a simulator/backend contract test for ACVPU when the backend checkout exists.
- [ ] Generate channel counts/catalog from `imitacija --dictionary`.

Acceptance:
- `make test` passes.
- No schedule literal remains in `_CHANNELS`.
- A single ACVPU definition exists per package.

### Phase 2 - backend read path and SSE

- [ ] Add `latest_readings()` using one query.
- [ ] Add `state.py:current_state()`.
- [ ] Rewire `crew_findings`, `stream`, `health_conditions`, `reading_history`, `assistant`.
- [ ] Add `channels` dependency and `CHANNEL_LAYERS`.
- [ ] Add `api/events.py` with group publish/subscribe.
- [ ] Replace `broadcast.py` while keeping `publish()` call sites stable.
- [ ] Add heartbeat and client-disconnect cleanup to `stream.events()`.
- [ ] Move inline `@extend_schema` payload dicts into `api/schema.py`.
- [ ] Update `test_stream.py` to the new public API.
- [ ] Decide whether `current_environment()` is cached per request.

Acceptance:
- `make test` passes.
- Stream behaves the same for e2e.
- No `broadcast._queues` access in tests.

### Phase 3 - frontend untangle

- [ ] Extract pure reading/history merge helpers.
- [ ] Make reconnect semantics explicit: reset or merge by `measured_at`.
- [ ] Split the plasma background into shaders, hook, and presentation.
- [ ] Fix `HealthAssistant` message keys with stable turn IDs.
- [ ] Replace `flatMap` in `VitalsPanel` with `map`/`filter`.
- [ ] Remove stale `VITALS_DISPLAY_UNITS` documentation.
- [ ] Decide whether `.mcp.json` and `components.json` stay.

Acceptance:
- `npm run lint` passes.
- `npx tsc -b` passes.
- `npm run build` passes.
- `make e2e` passes.

### Phase 4 - guardrails

- [ ] Add CI running `make lint` and `make test` on push.
- [ ] Add nightly `make e2e`.
- [ ] Add `basedpyright` to backend dev dependencies.
- [ ] Add architecture tests:
  - core has no Django imports
  - every finding input channel exists in `CHANNELS`
  - dictionary counts match registry
  - ACVPU consistent within each package
- [ ] Add a `make clean` or `make prune` target for local artifacts.

Acceptance:
- CI is green from a clean checkout.

### Phase 5 - product/spec decisions

- [ ] Remove or configure the assistant model blocklist.
- [ ] Implement or delete `sex`, `postmenopausal`, `pressure_pa`, `co2_ppm`, `dose_offset_msv`.
- [ ] Triage `mismatches.md` and `sus.md`; mark in scope or out of scope.
- [ ] Update the simulator docs after decisions.

Acceptance:
- No inert config remains without a documented reason.

---

## 5. Verification commands

```
make sync
make migrate
make lint
make test
make e2e
cd frontend && npm run lint && npx tsc -b && npm run build
```

Optional focused checks:

```
cd backend && uv run pytest api/test_stream.py -q
cd backend && uv run pytest packages/hydrograph-core -q
cd imitacija && uv run pytest -q
```

---

## 6. Non-goals and risks

- Do not change `docs/json-shape.md` semantics while untangling.
- Do not rewrite the frontend or replace Zustand/Recharts/Three.
- Do not delete scientific spec documents without checking code references.
- Django Channels with `InMemoryChannelLayer` is still single-process. That is
  acceptable for the demo; Redis is the production step.
- The SSE contract stays HTTP. Do not switch the frontend to WebSocket in this pass.
- Keep changes incremental and keep `make test` and `make e2e` green.

---

## 7. Open decisions

1. Should the simulator's `sex`/`postmenopausal` actually affect assay timing,
   or be deleted?
2. Should `pressure_pa` emit a pressure channel or be removed?
3. Is the assistant model blocklist a product requirement or accidental policy?
4. Which `mismatches.md` items are in scope for this demo?
5. Should `frontend/AGENTS.md` keep references to the absent `EXAMPLE_OLD_PROJ`?
