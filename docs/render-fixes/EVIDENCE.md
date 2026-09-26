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
