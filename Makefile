# HydroGraph dev commands. Run `make` for the list.
# Two terminals: `make run` (backend), then `make sim` (simulator). Or one: `make dev`.

CONFIG ?= config/healthy.toml
# SPEED overrides the config's own speed, e.g. `make dev SPEED=30`.
SPEED ?=
SIM = uv run imitacija --config $(CONFIG) $(if $(SPEED),--speed $(SPEED))
DEMO_URL = http://127.0.0.1:8000/static/demo/index.html

.PHONY: help sync migrate run sim demo dev test lint fmt check

help: ## List targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-8s %s\n", $$1, $$2}'
	@echo "  Variables: CONFIG=$(CONFIG) SPEED=$(or $(SPEED),from config)"

sync: ## Install backend and simulator dependencies
	cd backend && uv sync
	cd imitacija && uv sync

migrate: ## Create or update the backend database
	cd backend && uv run python manage.py migrate

run: migrate ## Start the backend on http://127.0.0.1:8000
	cd backend && uv run python manage.py runserver

sim: ## Feed the running backend from the simulator (CONFIG, SPEED)
	cd imitacija && $(SIM)

demo: ## Open the live demo page
	uv run --no-project python -m webbrowser $(DEMO_URL)

dev: migrate ## Backend + simulator together, demo opened; Ctrl+C stops both
	@(cd backend && exec uv run python manage.py runserver --noreload) & server=$$!; \
	trap 'kill $$server 2>/dev/null' EXIT INT TERM; \
	sleep 3; uv run --no-project python -m webbrowser $(DEMO_URL); \
	cd imitacija && $(SIM)

test: ## Run backend, core and simulator tests
	cd backend && uv run pytest -q
	cd imitacija && uv run pytest -q

lint: ## Check formatting, lint and types
	cd backend && uv run black --check . && uv run ruff check . && uv run basedpyright
	cd imitacija && uv run ruff check src tests && uv run mypy

fmt: ## Format and auto-fix
	cd backend && uv run black . && uv run ruff check --fix .
	cd imitacija && uv run ruff check --fix src tests

check: lint test ## Everything CI would run
