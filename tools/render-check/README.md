# Dashboard render check

A headless Microsoft Edge run over the real MDRRMO dashboard, for the layout facts `node --test` cannot see: clipped tabs, text contrast, legends, and what a panel actually prints.
It was added by `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md` and is not a product dependency.
It drives the Edge already installed on Windows, so nothing downloads a browser.

## Disposable database

Never point this at a real database: the setup writes demo rows, and `seed_live_currents.sql` fabricates field data (it refuses any database not named `aqone_render*`).

```bash
D="$TEMP/aqone_pg"   # keep this path short; a long path breaks initdb on Windows (MAX_PATH)
initdb -D "$D" -U postgres --auth=trust -E UTF8
pg_ctl -D "$D" -o "-p 55432" -l "$D.log" -w start
psql -h 127.0.0.1 -p 55432 -U postgres -c "create database aqone_render"

cd backend
export DATABASE_URL=postgresql://postgres@127.0.0.1:55432/aqone_render
python migrate.py && python -m app.simulation.generator
psql "$DATABASE_URL" -f ../tools/render-check/seed_live_currents.sql   # optional: an `ok` live drift case
DEMO_MODE=1 DEMO_CONTROL_KEY=demo JWT_SECRET=<48+ random chars> ADMIN_SETUP_KEY=setup \
  python -m uvicorn app.main:app --port 8765
curl -s -XPOST localhost:8765/api/admin-signup -H 'Content-Type: application/json' \
  -d '{"setup_key":"setup","email":"render.check@example.com","password":"rendercheck123","full_name":"Render Check"}'
```

The same cluster runs the opt-in database probes: `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@127.0.0.1:55432/postgres python -m pytest -q`.

## Run

```bash
cd tools/render-check
npm ci
node render_check.mjs --setup --live-case --out ../../docs/render-fixes/phase-N --require RND-01,RND-02
```

- `--setup` runs the presenter scenario (beats 1 to 6) and one anomaly evaluation.
- `--live-case` also acknowledges the demo SOS and opens a one-hour drift case from it (an `ok` run; it needs `seed_live_currents.sql`), acknowledges a second SOS and opens a one-hour case that ended an hour ago, and escalates the first trip check and opens a 24-hour case from it (an insufficient run).
- `--require` lists the checks whose failure makes the exit code non-zero; every check is still printed and written to `report.json`.
- Environment: `AQONE_BASE` (default `http://localhost:8765`), `AQONE_EMAIL`, `AQONE_PASSWORD`, `AQONE_DEMO_KEY` (default `demo`).

## Checks

| ID | What it measures |
|---|---|
| RND-01 | Every `.stats-tab` lies inside the tab bar and its clipping ancestor at 1280, 1440 and 1920 px. |
| RND-02 | With an open trip check, the Trip Checks list never says "No reason recorded". |
| RND-03 | Every row of `GET /api/ai/anomaly/active` appears in the Vessels tab. |
| RND-04 | No sample vessel name and no overdue marker on the dashboard. |
| RND-05 | The synthetic-replay badge has at least 4.5:1 contrast in the light and dark themes. |
| RND-06 | The drift legend is visible with rows whenever contours are drawn, and hidden otherwise. |
| RND-07 | The synthetic replay has three distinct rings and `forecast_hours` equal to its truth track's span. |
| RND-10 | From the UI: an escalated trip check opens or selects its drift case, the SOS drawer offers "Open drift case" for an acknowledged SOS, and "Rerun drift" adds the next run. |
| RND-11c | A live case whose forecast window has ended refuses a search report. |
| RND-11a | No drift card prints a raw `insufficient_*` code. |
| console | No console error and no 5xx response during the run. |

## Tutorial recordings

`record_tutorial.mjs` records the dashboard tutorial's lessons (`docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md`) into `web/data/tutorial/<lesson>.json`.
It runs the presenter scenario beat by beat, does each lesson's actions through the real dashboard in headless Edge, and saves every API response the dashboard saw.
The tutorial replays those files, so re-record whenever an API the dashboard reads changes shape.

Use a fresh disposable database, then run the two seeds in this order:

```bash
psql -h 127.0.0.1 -p 55432 -U postgres -c "create database aqone_render_tutorial"
cd backend
export DATABASE_URL=postgresql://postgres@127.0.0.1:55432/aqone_render_tutorial
python migrate.py && python -m app.simulation.generator
psql "$DATABASE_URL" -f ../tools/render-check/seed_live_currents.sql
psql "$DATABASE_URL" -f ../tools/render-check/seed_tutorial.sql
DEMO_MODE=1 DEMO_CONTROL_KEY=demo JWT_SECRET=<48+ random chars> ADMIN_SETUP_KEY=setup AQONE_SCHEDULER=0 \
  python -m uvicorn app.main:app --port 8765
cd ../tools/render-check && npm ci && node record_tutorial.mjs
```

- The recorder creates its own account, `duty.officer@example.com`, through the setup key.
- Lessons build on each other (the SOS acknowledged in one is the drift case of the next), so record them all in one run; `--only <lesson>` still prepares the earlier ones but writes one file.
- `--out <dir>` writes elsewhere, for comparing a new recording with the committed one.
- Then run `node --test web/test/*.test.js`: the lesson tests check that every step's target exists and every action a step waits for was recorded.
