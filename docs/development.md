# Running the dashboard locally

`make dev` starts the backend, frontend and simulator as one demo session. It
checks that ports 8000 and 5173 are free, waits for both servers to become ready,
then starts the simulator. A server failure stops the session; Ctrl+C stops all
three services and their child processes. Use `OPEN_BROWSER=0` to skip opening a
browser.

Each session uses a temporary database. The simulator restarts at its configured
timestamp, so reusing recordings from an earlier run can leave newer-dated old
readings on screen and mix different scenarios in the charts. The temporary
database is removed at shutdown. `backend/db.sqlite3` and any `DJANGO_DB_PATH`
provided for standalone use are left untouched. Reloading the page during a
session restores that session's history.

`make dev` uses the Makefile's `CONFIG` and the config's speed unless overridden.
Choose them explicitly when testing a particular scenario:

```sh
make dev CONFIG=config/badscenario4.toml SPEED=30
```

Lowercase `speed=30` also works. If both spellings are supplied, `SPEED` wins.

Scenario 1 (`config/badscenario1.toml`) defaults to **speed 1**. Its SANS
trajectory starts at second 10, reaches its warning endpoint at second 45,
starts the second ramp at second 60 and reaches the critical endpoint at second
90. The existing 60-second measurement windows publish the first warning at
approximately **one real minute** and the first critical result at **two real
minutes** in the ISS environment. Eye screens occur at seconds 60 and 120.
It then holds the critical state until stopped. This short synthetic timeline
does not accelerate other telemetry channels or change their alert thresholds.

```sh
make dev CONFIG=config/badscenario1.toml speed=1
```

Every enabled channel sends one startup baseline. Later measurements follow
their own schedules, in simulation time. `make dev` and `make sim` enable paired
blood pressure demo readings every **5 simulated seconds**, including for SANS
and hypercapnia. Both pressures vary smoothly by up to 3% around the scenario's
existing values. They are actual simulator readings sent through the backend,
chart history and blood pressure evaluator.

At `speed=1` this updates every five real seconds; at `speed=30`, about six times
per second before delivery/rendering limits. `BP_DEMO_INTERVAL=10` changes the
interval. `BP_DEMO_INTERVAL=0` restores the original pressure protocol without
the demo modulation. The standalone CLI enables it with `--bp-demo-interval 5`.

`make dev` and `make sim` also enable the assay and specimen demo every **5
simulated seconds**. Cortisol, troponin, lactate, vitamin D, IL-6, body mass,
urine volume, specific gravity, NTx and the sweat patch acquire on calendars
whose next result is hours, days or a month away, so the all-measurements tab
held one startup point for each of them. Every demo sample is this simulator's
own value one step further along that channel's own calendar, delivered without
the `lab_delay_s` laboratory hold; the values stay inside their nominal bands,
so no new alert appears. `LAB_DEMO_INTERVAL=0` restores the calendars, and
`--lab-demo-interval 5` enables the mode from the standalone CLI. A scenario
that gives its target crew member an explicit schedule for one of these groups,
such as the EVA mass points, keeps that schedule.

The original schedules, with the pressure demo disabled, are:

| Measurement | Healthy schedule after startup |
| --- | --- |
| Blood sugar | First at 343 seconds, then every 300 seconds |
| Blood pressure | First at hour 8, then hourly |
| Heart rate | Every 10 seconds (six per minute), first at second 10 |
| Temperature and oxygen | Every second |

A single chart dot means only one measurement is available. With the pressure
demo disabled, at speed 1 healthy
blood pressure will keep its startup dots for eight real hours. Infection and
EVA scenarios have their own minute-by-minute pressure schedules. See
`imitacija/docs/frequency_mapping.md` for the full schedule.

At accelerated speeds, acquisition can exceed HTTP delivery capacity. The
simulator's bounded queue thins the busiest channels first to preserve sparse
measurements such as pressure and glucose. Its `overflow` counter reports
discarded samples; acceleration does not guarantee delivery of every sample.

For persistent recordings, use `make run`, `make frontend` and `make sim` in
separate terminals. Pass the same `CONFIG` and `SPEED` to `make sim` to compare
the same scenario. Those standalone commands continue to use the persistent
backend database.
