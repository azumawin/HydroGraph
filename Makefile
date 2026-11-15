# HydroGraph dev commands. Run `make` for the list.
# One terminal: `make dev`. Or three: `make run` (backend), `make frontend`, `make sim`.

CONFIG ?= config/badscenario1.toml
# Accept both `speed=30` and `SPEED=30`; uppercase takes precedence.
SPEED ?= $(speed)
OPEN_BROWSER ?= 1
PYTHON ?= python3
# Paired synthetic pressure trends for the dashboard; 0 restores protocol timing.
BP_DEMO_INTERVAL ?= 5
BP_DEMO_ARG = $(if $(filter-out 0,$(BP_DEMO_INTERVAL)),--bp-demo-interval $(BP_DEMO_INTERVAL))
# Synthetic CGM trend for the dashboard; 0 restores the 5-minute sensor window,
# whose first completed result is 343 simulated seconds into the run.
GLUCOSE_DEMO_INTERVAL ?= 5
GLUCOSE_DEMO_ARG = $(if $(filter-out 0,$(GLUCOSE_DEMO_INTERVAL)),--glucose-demo-interval $(GLUCOSE_DEMO_INTERVAL))
SIM = uv run imitacija --config $(CONFIG) $(if $(SPEED),--speed $(SPEED)) $(BP_DEMO_ARG) $(GLUCOSE_DEMO_ARG)
FRONTEND_URL = http://127.0.0.1:5173
VITE = ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort

.PHONY: help sync migrate run frontend sim open dev test e2e lint fmt check

help: ## List targets
	@grep -E '^[a-z0-9]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'
	@echo "  Variables: CONFIG=$(CONFIG) SPEED=$(or $(SPEED),from config)"

sync: ## Install backend, simulator, frontend and e2e dependencies
	cd backend && uv sync
	cd imitacija && uv sync
	cd frontend && npm ci
	cd e2e && uv sync

migrate: ## Create or update the backend database
	cd backend && uv run python manage.py migrate

run: migrate ## Start the backend on http://127.0.0.1:8000
	cd backend && uv run python manage.py runserver

frontend: ## Start the frontend on http://127.0.0.1:5173 (streams from the backend on :8000)
	cd frontend && $(VITE)

sim: ## Feed the running backend from the simulator (CONFIG, SPEED)
	cd imitacija && $(SIM)

open: ## Open the frontend in the browser
	uv run --no-project python -m webbrowser $(FRONTEND_URL)

dev: ## Fresh demo database + backend + frontend + simulator; Ctrl+C stops all
	$(PYTHON) scripts/dev.py --config "$(CONFIG)" $(if $(SPEED),--speed "$(SPEED)") $(BP_DEMO_ARG) $(GLUCOSE_DEMO_ARG) $(if $(filter 0,$(OPEN_BROWSER)),--no-open)

test: ## Run backend, core, simulator and dashboard tests
	cd backend && uv run pytest -q
	cd imitacija && uv run pytest -q
	cd frontend && npm test

e2e: ## Browser tests: simulator -> backend -> frontend (see e2e/README.md)
	cd e2e && uv run pytest -q

lint: ## Check formatting, lint and types
	cd backend && uv run black --check . && uv run ruff check . && uv run basedpyright
	cd imitacija && uv run ruff check src tests && uv run mypy
	cd frontend && npm run lint && npx oxfmt --check src && npx tsc -b
	cd e2e && uv run ruff format --check . && uv run ruff check .

fmt: ## Format and auto-fix
	cd backend && uv run black . && uv run ruff check --fix .
	cd imitacija && uv run ruff check --fix src tests
	cd frontend && npm run format
	cd e2e && uv run ruff format . && uv run ruff check --fix .

check: lint test ## Everything CI would run
