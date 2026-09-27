# Evidence: Plan 72 dashboard tutorial mode

**Status:** COMPLETE
**Owner:** Claude Code (recording), Lenard (review)
**Created:** 2026-09-27
**Updated:** 2026-09-27
**Related:** `docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md`, `tools/render-check/README.md`

Environment unless stated: Windows 11, Python 3.11, Node 24.14, headless Microsoft Edge through `playwright-core`, a disposable PostgreSQL 18 cluster on port 55432, the backend on port 8765 with `DEMO_MODE=1` and `AQONE_SCHEDULER=0`, the generator at seed 42.

## Live honesty (`00527a3`)

- Red first: `backend/tests/test_public_buoys.py` failed on the unchanged route (no `buoy_marker`, `DEMO_BUOYS` present); the DEMO-07 source check in `web/test/dashboard-demo-mode.test.js` failed on "Displaying sample data" and the other invented figures.
- `/api/public/buoys` on the disposable database returned the eight generator buoys at their recorded positions with radii, gateway link, provenance and `last_heard_at`; the production feed had placed its two registered buoys at invented coordinates (observed on `https://aqone-backend.onrender.com/api/public/buoys`, 2026-09-27).
- The Live SOS, Return Now and Last Updated values were white on white (`color: rgb(255, 255, 255)` measured on `#banner-alert-count`); they now read in the text colour, the SOS count in red when calls are open.
- Gates at that commit: backend 595 passed, ruff clean; web 198 passed.

## Tutorial

- Recordings: `node record_tutorial.mjs` on a fresh `aqone_render_tutorial` database printed one line per lesson; every action the lessons teach was captured as its own phase:
  `warn: start:20 POST /api/sea-condition:2`, `trip-checks: ... POST /api/ai/anomaly/cases/1/acknowledge:3 POST /api/ai/anomaly/cases/1/escalate:2`, `sos: start:20 sos-arrives:4 POST /api/sos/9/acknowledge:1`, `drift: start:20 POST /api/ai/drift/cases:4 POST /api/ai/drift/incident/10/searched:4 POST /api/ai/drift/cases/10/rerun:2`, `close-out: start:20 POST /api/sos/9/resolve:3`.
  The drift run is `ok` (currents 96% from buoy observations, 8 nearby buoys).
- Walkthrough: every lesson driven step by step in headless Edge, doing each taught action through the UI; each waited-for action advanced its step, and the page made no `/api/` request on the network.
- No backend at all: the final screenshots below were taken with only `python -m http.server` serving `web/`, so the tutorial needs no API, database or account.
- Guest flow: login page, "Explore the tutorial without an account", the lesson menu, a lesson switch, and Exit back to the login page.
- Signed-in flow: profile page, Learn AqOne, Start; a real SOS posted to the disposable backend raised "A real SOS is waiting" within one poll; its Exit button returned to the live dashboard reading LIVE.
- Offline map: with the tile hosts blocked, the map switched to the service-area polygon on a land colour with its note, in the dark theme.
- Found and fixed on the way: the SAR Metrics tab ignored the `{status, data}` envelope `/api/ai/metrics` returns and always said the results "contain no metrics"; a dashboard modal sat under the coach card; drawers opened under the banner; resolved calls printed raw ISO times; the escalation badge ran off the drawer.
- Render check (Plan 71 tooling) on a fresh `aqone_render` database after all changes: 11 of 11 PASS (RND-01 to RND-11c and console).

## Gates

- Backend: `python -m pytest -q` with `AQONE_PROBE_PG_ADMIN_URL` set: 654 passed, 5 skipped, 1 xfailed; `python -m ruff check .` clean.
- Web: `node --test test/*.test.js` 210 passed; `node --check` clean on every file under `js/` and `test/`.

## Screenshots

| File | Shows |
|---|---|
| `lesson1-figures.png` | Lesson 1, banner, watermark, TUTORIAL feed status, spotlight on the metric cards |
| `lesson1-offline-map-dark.png` | Tiles blocked: the service-area polygon fallback, buoys and gateways, dark theme |
| `lesson5-acknowledged.png` | The recorded SOS after the learner acknowledged it: status, ETA countdown, note |
| `lesson6-searched-area.png` | Drift case `ok`, rings and the searched-area report |
| `profile-learn-tab.png` | The Learn AqOne tab on the profile page |
| `real-sos-bar.png` | A signed-in learner told a real SOS is waiting |

## Not verified

- The deployed Render site: this evidence is from local runs; check the tutorial there after the push deploys.
- Physical projectors, widths below 1280 px, and a real responder using the lessons.
