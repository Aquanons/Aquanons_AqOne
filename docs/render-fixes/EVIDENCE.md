# Evidence: Plan 71 dashboard render fixes

**Status:** ACTIVE
**Owner:** Claude Code (recording), Lenard (review)
**Created:** 2026-09-26
**Updated:** 2026-09-26
**Related:** `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md`, `docs/audits/DASHBOARD_DRIFT_TRIP_RENDER_AUDIT_2026-09-26.md`, `tools/render-check/README.md`

Environment for every phase unless stated: Windows 11, Python 3.11, Node 24.14, a disposable PostgreSQL 18 cluster on port 55432 (`tools/render-check/README.md`), the backend from the `fix/dashboard-render` worktree on port 8765 with `DEMO_MODE=1` and `AQONE_SCHEDULER=0`, the generator at seed 42, `seed_live_currents.sql` applied, and `node render_check.mjs --setup --live-case`.
Screenshots are kept for Phase 1 (before) and Phase 7 (after); the phases between keep `report.json` and `drift.json` only, to keep the repository small.

## Phase 1: demo, seed data and the render check

Date: 2026-09-26.

- Red first: `tests/test_demo_pg.py` failed on the unchanged code with `squall_events: next id 1 collides with 29` and, with the sequence repaired but the old demo code, `AttributeError: 'Depends' object has no attribute 'get'`; `tests/test_sos_provenance.py` failed to import `SosProvenance` from `app.incidents.trust`.
- After the change: `python -m pytest -q` 581 passed, 61 skipped, 1 xfailed; with `AQONE_PROBE_PG_ADMIN_URL` set, 637 passed, 5 skipped, 1 xfailed; `python -m ruff check .` clean.
- The render check's `--setup` drove `POST /api/demo/scenario/squall-fleet/start` and beats 1 to 6 on a freshly generated database; every call returned 200 (beats 5 and 6 returned 500 in the audit).
- Baseline render check (`phase-1/report.json`, before any dashboard fix): RND-01, -02, -03, -04, -05, -06, -07, -10 and -11a FAIL as the audit describes; the console check PASSES.
  RND-05 measured the replay badge at 1.04:1 in the light theme and 5.72:1 in the dark theme.

## Phase 2: anomaly reasons and factors honour the contract

Date: 2026-09-26.

- `docs/05_PUBLIC_API.md` amended first with the shared "Factor object".
- Red first: `tests/test_anomaly_factor_contract.py` failed with the JSON string `'[{"name": "overdue", ... "explanation": ...}]'` where a list of `{code, description}` objects was expected, and on the missing `contract_factors`; `web/test/dashboard-render-fixes.test.js` failed on the missing `riskFeedHtml`.
- The risk-feed renderer moved from `dashboard-ai-ops.js` into `dashboard-utils.js` as the pure `riskFeedHtml`; the module now only writes its result. `check_needed` rows now sort and color with the urgent rows. Three runtime-test stubs now inject the real utilities, as `dashboard-core.js` does, and one source check reads the utilities file.
- Gates: backend 585 passed, 61 skipped, 1 xfailed, ruff clean; web 180 passed, `node --check` clean on every file.
- Render check (`phase-2/report.json`): RND-02 PASS, the trip check now reads "Late beyond the expected-contact window."; console PASS.

## Phase 3: trip anomalies are visible and honest

Date: 2026-09-26.

- Red first: the five Phase 3 tests in `web/test/dashboard-render-fixes.test.js` failed (rows hidden while not monitoring, no DEMO badge, no `attention` count, sample vessel names in four source files).
- The stats tabs wrap onto a second row; every tab and badge is inside the card at 1280, 1440 and 1920 px.
- The risk feed shows the "Not monitoring" notice above any scored rows, and a DEMO badge on synthetic rows; the Vessels tab badge counts rows that are not `normal`.
- Deleted: the five hard-coded vessels, their markers, drawers and filter chips, the two sample overdue incidents and drawers, `createOverdueIcon`, the vessel-list CSS, and the filter labels in both dashboard languages. The Live Overview "vessels in contact range" figure, which was computed from the hard-coded boats, now reads `--` until a real source exists (Plan 72).
- The runtime test for the deleted sorted vessel list was removed with it.
- Gates: web 184 passed, `node --check` clean; backend unchanged since Phase 2.
- Render check (`phase-3/report.json`): RND-01, -02, -03, -04 and console PASS.

## Phase 4: the drift card and map explain themselves

Date: 2026-09-26.

- Red first: six Phase 4 tests failed on the missing `driftLegendItems`, `driftLegendHtml`, `insufficiencyText` and `DRIFT_COLORS`, and on the drift card printing the raw code.
- `DRIFT_COLORS` in `dashboard-utils.js` is now the one source for the drift map's stroke colors and the legend chips.
- The legend overlays the map's lower left and lists exactly the drawn layers; it is hidden for an insufficient case and when no case is selected.
- The insufficiency test reads the `INSUFFICIENT_*` and `DEGRADED_*` codes from `backend/app/ai/environment.py`, so a new backend code cannot ship without a sentence.
- The replay badge text is `#334155` in the light theme (7.26:1, was 1.04:1) and keeps `#cbd5e1` in the dark theme (5.72:1). "View Activity" has a light-card button style.
- Gates: web 190 passed, `node --check` clean.
- Render check (`phase-4/report.json`): RND-01 to -06, RND-11a and console PASS; RND-07 and RND-10 are the remaining phases.
