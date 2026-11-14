# HydroGraph dev commands. Run `make` for the list.
# One terminal: `make dev`. Or three: `make run` (backend), `make frontend`, `make sim`.

CONFIG ?= config/healthy.toml
# SPEED overrides the config's own speed, e.g. `make dev SPEED=30`.
SPEED ?=
SIM = uv run imitacija --config $(CONFIG) $(if $(SPEED),--speed $(SPEED))
FRONTEND_URL = http://127.0.0.1:5173
VITE = ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort

.PHONY: help sync migrate run frontend sim open dev test lint fmt check

help: ## List targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'
	@echo "  Variables: CONFIG=$(CONFIG) SPEED=$(or $(SPEED),from config)"

sync: ## Install backend, simulator and frontend dependencies
	cd backend && uv sync
	cd imitacija && uv sync
	cd frontend && npm ci

migrate: ## Create or update the backend database
	cd backend && uv run python manage.py migrate

run: migrate ## Start the backend on http://127.0.0.1:8000
	cd backend && uv run python manage.py runserver

frontend: ## Start the frontend on http://127.0.0.1:5173 (proxies /api to the backend)
	cd frontend && $(VITE)

sim: ## Feed the running backend from the simulator (CONFIG, SPEED)
	cd imitacija && $(SIM)

open: ## Open the frontend in the browser
	uv run --no-project python -m webbrowser $(FRONTEND_URL)

dev: migrate ## Backend + frontend + simulator, frontend opened; Ctrl+C stops all
	@(cd backend && exec uv run python manage.py runserver --noreload) & backend=$$!; \
	(cd frontend && exec $(VITE)) & frontend=$$!; \
	trap 'kill $$backend $$frontend 2>/dev/null' EXIT INT TERM; \
	sleep 3; uv run --no-project python -m webbrowser $(FRONTEND_URL); \
	cd imitacija && $(SIM)

test: ## Run backend, core and simulator tests
	cd backend && uv run pytest -q
	cd imitacija && uv run pytest -q

lint: ## Check formatting, lint and types
	cd backend && uv run black --check . && uv run ruff check . && uv run basedpyright
	cd imitacija && uv run ruff check src tests && uv run mypy
	cd frontend && npm run lint && npx oxfmt --check src && npx tsc -b

fmt: ## Format and auto-fix
	cd backend && uv run black . && uv run ruff check --fix .
	cd imitacija && uv run ruff check --fix src tests
	cd frontend && npm run format

check: lint test ## Everything CI would run
