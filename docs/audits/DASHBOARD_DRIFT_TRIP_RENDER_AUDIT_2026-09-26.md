# Audit: dashboard rendering of drift prediction and trip anomalies

**Status:** COMPLETE
**Owner:** Lenard (review), Claude Code (audit)
**Created:** 2026-09-26
**Updated:** 2026-09-26
**Related:** `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md`, `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`, `docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md`, `docs/05_PUBLIC_API.md`, `docs/47_VISUAL_DESIGN_GUIDE.md`

Read-only audit.
No product file was changed.
The fixes are planned in `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md`.

## Environment

- Date: 2026-09-26, `master` at `fc89fe7`, Windows 11, Python 3.11, Node 24.14, Microsoft Edge (headless) driven by `playwright-core` 1.x installed in a temporary directory.
- Database: a disposable PostgreSQL 18 cluster created with `initdb` on port 55432 with trust authentication, deleted afterwards.
  The existing server on port 5432 was not used, and no password was guessed.
- Data: `python migrate.py`, then `python -m app.simulation.generator` (seed 42, 14 days).
- Backend: `python -m uvicorn app.main:app --port 8765` with `DEMO_MODE=1`, `DEMO_CONTROL_KEY`, `JWT_SECRET` and `ADMIN_SETUP_KEY` set; one `mdrrmo` account created through `POST /api/admin-signup`.
- Dashboard: served by the backend at `/html/dashboard.html`, logged in through `/html/login.html`, viewport 1440 x 900 (tab bar also measured at 1920).
- Trip anomaly input: `POST /api/demo/scenario/squall-fleet/start`, `POST /api/demo/beat/4`, `POST /api/ai/anomaly/evaluate`.
- Real drift cases: trip check 1 escalated through the API, then `POST /api/ai/drift/cases`; one SOS case opened with `forecast_hours=1` after the disposable database's recent current observations were relabelled as live, qualified, and created at observation time, so an `ok` run could be rendered.
  That relabelling is a test fixture only; it says nothing about field data.

Baseline on the same commit: backend `python -m pytest -q` 574 passed, 59 skipped, 1 xfailed; `python -m ruff check .` clean; web `node --test test/*.test.js` 175 passed.

## Reproduction recipe

```bash
D="$TEMP/aqone_pg"          # keep the path short: a long scratch path broke initdb (Windows MAX_PATH)
initdb -D "$D" -U postgres --auth=trust -E UTF8
pg_ctl -D "$D" -o "-p 55432" -l "$D.log" -w start
psql -h 127.0.0.1 -p 55432 -U postgres -c "create database aqone_render"
cd backend
export DATABASE_URL=postgresql://postgres@127.0.0.1:55432/aqone_render
python migrate.py && python -m app.simulation.generator
DEMO_MODE=1 DEMO_CONTROL_KEY=demo JWT_SECRET=<long random> ADMIN_SETUP_KEY=<setup> \
  python -m uvicorn app.main:app --port 8765
```

The same cluster serves the opt-in probe tests with `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@127.0.0.1:55432/postgres`.

## Findings

Severity: **High** hides or misstates safety information, or breaks the presenter demo; **Medium** misleads a responder or blocks a documented workflow; **Low** is polish.

| ID | Severity | Feature | Finding | Evidence |
|---|---|---|---|---|
| F1 | High | Trip anomaly | The Trip Checks tab, with its badge, is outside the visible stats tab bar at every width, so the trip-check queue cannot be seen. | Tab bar 336 px wide, content 436 px, `overflow-x: visible` inside a clipping card; at 1440 px the tab starts at x=1397, exactly the bar's right edge (1920 px: 1877 and 1877). `web/css/dashboard.css:985-995`. |
| F2 | High | Trip anomaly | Every trip-check row says "No reason recorded." | `GET /api/ai/anomaly/cases/open` returns `reasons` as a JSON string (asyncpg returns `jsonb` as text; `app/api/anomaly_cases.py:23-26` passes it through), and its items use `name`/`explanation`, while `docs/05_PUBLIC_API.md` and `web/js/dashboard-utils.js:303-308` expect an array of `code`/`description`. `GET /api/ai/anomaly/active` returns `factors` as a string the same way, so the risk feed's factor rows are always empty. |
| F3 | Medium | Trip anomaly | The vessel risk feed shows only "Not monitoring - no live contact source" and hides a scored ALERT row (V001, 0.98) whenever `monitoring` is `unavailable`. | `web/js/dashboard/dashboard-ai-ops.js:620-625` returns before rendering rows. `docs/05` says `unavailable` means an empty list proves nothing; it does not say rows are hidden. |
| F4 | High | Trip anomaly | The Vessels tab and the map show five hard-coded vessels, two of them fake OVERDUE boats with pulsing markers and invented drawers, under the LIVE badge, while the real overdue vessel is hidden (F3). The Vessels badge counts the two fake boats. | `web/js/dashboard/dashboard-vessels-alerts.js:15-126`, `web/js/dashboard/dashboard-markers.js:239-259`. `.vessel-next` has no CSS, so "Expected next" renders at 16 px, larger than the vessel name. |
| F5 | High | Drift | The "REPLAY - SYNTHETIC INCIDENT" badge is an empty grey box in the light theme, which is the default and the view shown on load. The badge exists so a synthetic 95% contour is not read as a live emergency. | `#cbd5e1` text on the `#f8fafc` meta background, about 1.4:1 contrast. `web/css/dashboard.css:5606-5618`, `:5355-5360`. |
| F6 | Medium | Drift | The map has no legend for the 95% / 75% / 50% contours, next-area box, searched sectors or ground-truth track. | `updateAiMapKey()` always sets `display: none` (`dashboard-ai-ops.js:78-82`) and `#ai-map-key` is not in `web/html/dashboard.html`; the CSS for it exists (`dashboard.css:1871-1900`). `docs/47` requires a legend entry for every visible layer. |
| F7 | Medium | Drift (AI) | Synthetic replay incident 8: the 75% ring is identical to the 95% ring, so only two rings are visible; and the ground-truth track ends outside the 95% area. | Both rings span lat 11.694-12.038, lon 122.589-122.919. Cause: `_contour_polygon` selects `values >= cutoff` (`app/ai/drift.py:369-370`, also used by `app/ai/search.py:224` `contours_from_grid`), so tied low histogram counts pull the same cells into several masses. Confirmed on a synthetic histogram (500 normal particles, 250 m cells): the 50%, 75% and 95% selections are all 434 cells holding 100% of the mass, so every labelled ring is really the 100% ring. The dashboard always requests `forecast_hours=24` (`dashboard-ai-ops.js:856`), while the truth track spans 4 h (9 points, 06:21 to 10:21) and `app/ai/drift_eval.py:86` evaluates at the truth span, so the map compares a 24 h forecast with 4 h of truth. Knock-on: `drift_eval.py:102` counts containment inside `contours[-1]`, the labelled 95% ring, so the stored synthetic `containment_rate` of 1.0 (`backend/app/ai/models/eval_results.json`, 2026-08-04, quoted as "100% containment" in `docs/audits/AI_LAYER_DATA_SUFFICIENCY_AUDIT_2026-09-14.md`) was measured on a ring that can hold 100% of the mass, and is likely inflated. |
| F8 | High | Demo | `POST /api/demo/beat/5` and `/6` return 500, so the presenter's incident, drift and search beats never run. | `app/demo/scenarios.py:275-307` calls the FastAPI route function `ingest_sos` directly, so its `vessel_device` default is a `Depends` object: `AttributeError: 'Depends' object has no attribute 'get'` at `app/api/sos.py:157`. Introduced by `a1d5cc5` (2026-09-23); `tests/test_demo.py` does not cover beats 5 and 6. |
| F9 | High | Demo and seed data | After `python -m app.simulation.generator`, the next default-id insert into `squall_events`, `incidents` or `sos_events` fails with a duplicate key, so `POST /api/demo/scenario/squall-fleet/start` returns 500, and the first real SOS inserts after a reseed would fail too. | The generator inserts explicit ids (`app/simulation/generator.py:1076`, `:1148`, `:1182`) after `TRUNCATE ... RESTART IDENTITY` (`:940-949`) and never advances the sequences: `max(id)` 29 / 8 / 8, each sequence `last_value` 1. |
| F10 | Medium | Drift | A responder cannot open a drift case, or rerun one, from the dashboard, so the real-case drift view is only reachable through the API. | Nothing in `web/` calls `POST /api/ai/drift/cases` or `/cases/{id}/rerun`. `docs/40` manual acceptance expects "a responder can open only an eligible case". |
| F11 | Low | Drift | Three smaller issues on the drift card. | (a) The insufficiency reason prints the raw code, for example `insufficient_current_coverage` (`dashboard-ai-ops.js:263`). (b) "View Activity" uses the dark-theme `.action-btn` style (`dashboard.css:929-946`) inside the light meta box and reads as plain text. (c) After a run's forecast window has passed, "Mark a searched area" is still offered and submitting fails with 422 `searched_at is outside trajectory time range`. |

## What rendered correctly

- A live case with sufficient inputs draws the 95%, 75% and 50% contours and the dashed next-area box, and its meta lines state the observed-current share, wind source and nearby buoy count.
- A live case without sufficient inputs shows the orange INSUFFICIENT ENVIRONMENTAL DATA badge, draws no contour, and disables search reporting with a reason.
- The two-click searched-area interaction and its confirmation panel render and cancel correctly.
- A trip-check row shows its case type, OPEN and DEMO badges, confidence score, data age, and all five actions; escalation through the API persisted.

## Not covered

- No physical handset, pod or gateway; all contacts were synthetic demo contacts.
- Dark theme was not screenshotted.
- Screen widths below 1280 px were not checked.
- Other sample data on the dashboard (Live Overview metrics, the sample squall incident drawer) is outside this audit.
