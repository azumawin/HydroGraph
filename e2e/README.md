# End-to-end tests

The real stack in a real browser: each test starts the Django backend on a fresh
temporary database, the Vite frontend and, for simulation tests, the simulator
(`imitacija`), then checks what the dashboard shows with Playwright.

- `tests/test_live_readings.py`: readings posted exactly as the simulator sends
  them (SI units) appear converted (bpm, mmHg, °C, mmol/L, %), with the right
  evaluation, a chart point each, the body scan and findings updated; late
  readings, rejected readings, reloads and a backend restart behave.
- `tests/test_simulation.py`: simulator configs drive the dashboard: the healthy
  run fills every vital and flags nothing, charts grow live, a reload mid-run
  resumes, the hypercapnia scenario escalates SpO2, heart rate and hypoxia, and
  the SANS scenario takes Finding 9 to critical.

From the repo root:

```sh
make sync                                  # once: backend, simulator, frontend deps
cd e2e && uv run playwright install chromium  # once: the browser
make e2e                                   # about 3 minutes
```

`E2E_CHROMIUM=/path/to/chrome` uses an already installed Chromium instead.
Nothing is shared with a running `make dev`: every server uses free ports and a
temporary database.
