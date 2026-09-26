# Implementation Plan: dashboard drift and trip-anomaly render fixes

**Status:** APPROVED - Revision 2; executing in `auto` mode
**Owner:** Lenard (approval; takes the web paths from Arnold for this plan), Claude Code (implementation and tests)
**Created:** 2026-09-26T22:45:00+08:00
**Updated:** 2026-09-26T23:10:00+08:00
**Related:** `docs/audits/DASHBOARD_DRIFT_TRIP_RENDER_AUDIT_2026-09-26.md` (findings F1-F11), `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`, `docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md`, `docs/05_PUBLIC_API.md`, `docs/47_VISUAL_DESIGN_GUIDE.md`, `docs/18_BACKEND_STRUCTURE.md`

Revision: 2
**Execution mode:** auto
Feature spec and revision: Len's chat request, 2026-09-26: "For the drift prediction and the trip anomaly can you check how those features renders", then "We will work on this instead, Arnold is busy. Create an /implementation-plan addressing these issues. /clean-architecture and make sure to update all the necessary docs in the repo."
The audit findings and the requirements below (RND-01 to RND-11) are the spec; no separate spec doc.
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0; `docs/38` and `docs/40` as approved; `docs/05_PUBLIC_API.md` as of `fc89fe7`.
Len's chat approval, 2026-09-26T23:00:00+08:00, of Revision 1: "For your other questions lets go with what you recommend. And dont use hard stop mode for now i need you to keep working until the task is finished."
Revision 2 records D1-D6 as recommended, sets the execution mode to `auto` (D7 overridden by Len), and moves the idea of sample data into a separate, toggleable demo mode, `docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md` (Len: "a toggleable demo mode ... is a seperate workload"); nothing else changed.
Target branch: `fix/dashboard-render` in its own worktree `../AqOne-render` with its own `HANDOFF.md` (`docs/58`); each verified phase merged to `master` and pushed (Len: push verified work straight to `master`).
Roles: Claude writes each phase's red tests first, implements, reruns the gate, and records evidence; Len approves each phase boundary.

`hard-stop` would be the default by scale (product code, a shared contract, a model's output, more than three phases); Len chose `auto`, so phases run back to back and stop only on a failed gate, a real blocker, or a decision that is Len's.
Success condition: the dashboard walkthrough in Phase 7 shows every finding F1-F11 fixed on a freshly seeded disposable database, with screenshots, and all gates green.
Next hard stop: none planned; a failed gate or a decision that is Len's.

## Audit baseline (2026-09-26, `master` at `fc89fe7`)

The full evidence is in `docs/audits/DASHBOARD_DRIFT_TRIP_RENDER_AUDIT_2026-09-26.md`.
In short:

- Trip anomaly: the Trip Checks tab is off-screen (F1); every trip check says "No reason recorded." because `reasons` and `factors` leave the API as JSON strings with the wrong keys (F2); the risk feed hides scored rows while `monitoring` is `unavailable` (F3); the Vessels tab and map show hard-coded fake OVERDUE boats (F4).
- Drift: the synthetic-replay badge is invisible in the light theme (F5); there is no legend (F6); tied histogram counts make the labelled 95% ring the 100% ring, and the replay compares a 24 h forecast with 4 h of truth (F7); responders cannot open or rerun a case from the dashboard (F10); three smaller card issues (F11).
- Demo and seed data: beats 5 and 6 crash because the demo calls a FastAPI route function (F8); the generator leaves three id sequences at 1 (F9).

Test baseline on `fc89fe7`: backend 574 passed, 59 skipped (opt-in database probes), 1 xfailed; ruff clean; web 175 passed.

## Requirements

| ID | Finding | Requirement | Observable acceptance |
|---|---|---|---|
| RND-01 | F1 | Every stats tab, with its badge, is fully visible and clickable at 1280, 1440 and 1920 px wide. | Render check: each `.stats-tab` bounding box lies inside the tab bar's box at the three widths; screenshot per width. |
| RND-02 | F2 | `reasons` on `GET /api/ai/anomaly/cases/open` and `factors` on `GET /api/ai/anomaly/active` are JSON arrays of `{code, value, weight, contribution, description}`, as `docs/05` defines; the stored rows keep their current shape. A trip-check row shows the highest-contribution description. | Backend route tests with a fake pool whose row holds the text form: the response field is a list with exactly those keys. Web test: `tripCheckRowHtml` on the contract example prints "Late beyond the expected-contact window."; the risk-feed renderer prints each factor's `code` and `description`. |
| RND-03 | F3 | When `monitoring` is `unavailable`, the risk feed shows the "Not monitoring" notice and still lists any scored rows beneath it; a `synthetic` row carries the DEMO badge. With no rows, only the notice shows (existing behavior). | Web tests on the pure risk-feed renderer: (rows, unavailable) gives notice plus rows; (no rows, unavailable) gives the notice only; a synthetic row has the DEMO badge. |
| RND-04 | F4 | The dashboard shows no hard-coded vessel, overdue marker or overdue drawer. The Vessels tab shows the real risk feed, and its badge counts rows whose status is not `normal`. | Web test: the vessels module source contains no vessel literal and the badge equals the non-normal count of a fixture feed. Render check: no `overdue-marker-dot` on the map without a real overdue row. |
| RND-05 | F5 | The replay badge text has at least 4.5:1 contrast against its background in the light and dark themes. | Render check: computed colors of `.drift-replay-badge` and its background in both themes, contrast ratio printed and asserted; screenshot per theme. |
| RND-06 | F6 | A legend lists exactly the drift layers drawn for the selected case, each with its exact stroke color and label (`docs/47`). | Web test on a pure `driftLegendItems(payload)`: an `ok` case lists 95/75/50 and next area; a synthetic replay adds the ground-truth track; a case with sectors adds searched area; an insufficient case lists nothing and the legend is hidden. Render check screenshot. |
| RND-07 | F7 | Contour masses are honest: each ring is the smallest set of cells, taken in descending density, whose mass reaches the target, so 50% ⊆ 75% ⊆ 95% and each ring's mass is at most its target plus one cell. A synthetic replay is predicted with the same horizon and inputs `drift_eval` uses, and the payload states its `forecast_hours`. Published drift figures are re-measured. | Unit test on `_contour_polygon` with a tied, sparse histogram: selected mass for 0.75 is below the 0.95 selection and never 1.0 when the target is 0.95. API test: a synthetic replay's `forecast_hours` equals `(len(true_track) - 1) * 0.5`. `python -m app.ai.drift_eval` rerun, old and new figures recorded. |
| RND-08 | F8 | The SOS provenance rule (SEC-06) is pure policy, and the HTTP route and the demo both record an SOS through one application function instead of calling a route. Demo beats 0 to 6 all succeed. | Pure tests of the provenance rule (gateway key present or absent, device bound to the same or another vessel, requested tier). Probe test on a migrated, generated database: scenario start and beats 4, 5, 6 return 200, and an incident plus a searched sector exist for the run. |
| RND-09 | F9 | After the generator runs, the next default-id insert into `squall_events`, `incidents` and `sos_events` succeeds. | Probe test: regenerate, then insert one row per table without an id. |
| RND-10 | F10 | A responder can open a drift case from an escalated trip check and from an acknowledged SOS, choosing the object class, and can rerun an open case; ineligible sources offer no action. | Web tests on the pure eligibility functions for both sources. Render check: open a case from each source through the UI, it appears selected in the drift card; rerun increments the run number. |
| RND-11 | F11 | Insufficiency reasons read as plain sentences; "View Activity" looks like a button on the light card; once a run's forecast window has ended, search reporting is disabled with the reason "This run's forecast has ended - rerun the case first." | Web tests: every code in `app/ai/environment.py` maps to a sentence and an unknown code falls back to the code; `eligibleForSearchReport` refuses a payload whose `forecast_ends_at` has passed. API test: a real-case payload carries `forecast_ends_at`. Render check screenshot. |

## Decisions (answered by Len, 2026-09-26T23:00:00+08:00: "lets go with what you recommend", except D7)

| # | Question | Answer |
|---|---|---|
| D1 | Factor wire shape: map the stored `{name, explanation, ...}` to the contract's `{code, description, ...}` at the API boundary for both anomaly endpoints, and document the `factors` shape in `docs/05`? | Yes. The database and `app/ai` keep their shape, no migration, and the dashboard reads one shape everywhere. |
| D2 | Delete the hard-coded Vessels list, its overdue markers, its overdue drawers and the two sample overdue drawers in `dashboard-markers.js`, and make the Vessels tab the real risk feed without the coverage filter chips (no data source exists for coverage)? | Yes. Other sample content (Live Overview metrics, the sample squall drawer) stays until Plan 72, the toggleable demo mode, serves sample data through its own data source and deletes it. |
| D3 | Change contour selection (RND-07), which changes every drift ring and the synthetic evaluation figures, and correct the "100% containment" wording wherever it is quoted? | Yes. The current rings overstate their mass; a lower honest figure replaces an inflated one. |
| D4 | Add open-case and rerun actions to the dashboard in this plan (RND-10), closing `docs/40`'s manual acceptance? | Yes. Without them the real-case drift view is reachable only through the API. |
| D5 | Tab bar: let the tabs wrap onto a second row rather than shortening labels or scrolling? | Wrap. It keeps every label and badge visible at any width without a hidden scroll. |
| D6 | Commit a small render-check harness under `tools/render-check/` with its own `package.json` pinning `playwright-core`, driving the installed Edge? | Yes. Tab clipping, contrast and legends are layout facts `node --test` cannot see; the harness stays out of every product dependency. |
| D7 | Execution mode `hard-stop`? | No: `auto` (Len). |

## Architecture

This plan follows the clean architecture rules in `.claude/skills/clean-architecture/clean-architecture.mini.md` within the boundaries the repository already enforces.

| Layer | Owns | In this plan |
|---|---|---|
| `app/incidents/` (pure policy, enforced by `tests/test_incidents_is_pure.py`) | SOS rules with no framework, database or HTTP import | Receives `SosProvenance` and the SEC-06 decision `sos_provenance(...)` from `app/api/sos.py` (RND-08). |
| `app/ai/` (models, testable without a server) | Drift prediction, contours, evaluation | Contour selection fix and one replay-prediction function that `drift_eval` and the replay route both call (RND-07). |
| `app/api/` (humble adapters) | HTTP translation: credentials to plain values, domain values to the `docs/05` contract | The SOS route only translates headers and the device binding into plain arguments; anomaly routes map stored factors to the contract DTO (RND-02); drift payload adds `forecast_hours` and `forecast_ends_at`. |
| `app/api/sos.py` `record_sos` (application function, today `_upsert_sos`) | Persisting one SOS for a given provenance | Made public and called by both the route and the demo. The demo, an outer adapter, never calls a route function again (RND-08). |
| `app/demo/`, `app/simulation/` (outer tools) | Presenter scenario, synthetic seed data | Call application functions; the generator repairs its own sequences (RND-09). |
| `web/js/dashboard-utils.js` (pure presentation, tested without a DOM) | HTML builders and eligibility rules | Gains the risk-feed renderer, `driftLegendItems`, the insufficiency sentences, and the open-case and elapsed-run eligibility (RND-03, -06, -10, -11). |
| `web/js/dashboard/*.js` (humble DOM modules) | Fetching, polling, event wiring | Call the pure builders; no new business branching. |

The dependency rules are enforced by tests, not by folder names: the existing purity test covers the moved provenance rule, and each new pure web function is unit-tested without a DOM.

Architectural debt recorded, not fixed here:

- asyncpg has no `jsonb` codec, so each route decodes `jsonb` by hand (11 `json.loads` sites, 22 `::jsonb` writes). A pool-level codec would change every write that passes a pre-encoded string; it needs its own plan.
- `record_sos` stays in the `app/api/sos.py` module as a partial boundary; moving SOS persistence into its own application module is a larger refactor than these findings need.
- The legacy replay path recomputes a prediction on every read.
- Remaining sample data on the dashboard: Live Overview metrics and the sample squall and incident drawers in `dashboard-markers.js`; Plan 72 replaces them with a toggleable demo mode.

## Owned paths

- `backend/app/api/sos.py`, `backend/app/api/anomaly.py`, `backend/app/api/anomaly_cases.py`, `backend/app/api/drift.py`
- `backend/app/incidents/trust.py`, `backend/app/demo/scenarios.py`, `backend/app/simulation/generator.py`
- `backend/app/ai/drift.py`, `backend/app/ai/search.py`, `backend/app/ai/drift_eval.py`, `backend/app/ai/models/eval_results.json` (evaluator output only)
- The new and changed tests under `backend/tests/` and `web/test/`
- `web/js/dashboard-utils.js`, `web/js/dashboard/dashboard-ai-ops.js`, `web/js/dashboard/dashboard-trip-checks.js`, `web/js/dashboard/dashboard-vessels-alerts.js`, `web/js/dashboard/dashboard-markers.js`, `web/js/dashboard/dashboard-incidents.js`, `web/css/dashboard.css`, `web/html/dashboard.html`
- `tools/render-check/`, `docs/71_*`, `docs/render-fixes/`
- Shared docs edited in the named phases: `docs/05_PUBLIC_API.md` (anomaly and drift sections), `docs/16_QA_DISCLOSURES.md`, `docs/17_AI_EXPLAINED_SIMPLY.md`, `docs/18_BACKEND_STRUCTURE.md`, `docs/08_DEMO_AND_STATUS.md`, `docs/README.md`, `docs/SPEC_INDEX.md`

No other active plan claims these paths (Current Register, 2026-09-26).
Plan 69 Phase 3 would add backend routes if approved; it does not touch these files, and whichever merges second rebases once.

## Dependencies and order

| Phase | Outcome | Can start when |
|---|---|---|
| 1 | Demo, seed data and the render check run end to end | Plan approved |
| 2 | Anomaly reasons and factors honour the contract | Phase 1 |
| 3 | Trip anomalies are visible and honest on the dashboard | Phase 2 |
| 4 | The drift card and map explain themselves | Phase 1 |
| 5 | Drift rings are honest and the replay matches its evaluation | Phase 4 |
| 6 | Responders open and rerun cases; ended runs refuse reports | Phases 3 and 5 |
| 7 | Walkthrough, evidence and documentation close-out | Phase 6 |

## Common commands

Disposable database, used by the probe tests and the render check (from `docs/audits/DASHBOARD_DRIFT_TRIP_RENDER_AUDIT_2026-09-26.md`):

```bash
D="$TEMP/aqone_pg"; initdb -D "$D" -U postgres --auth=trust -E UTF8
pg_ctl -D "$D" -o "-p 55432" -l "$D.log" -w start
export AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@127.0.0.1:55432/postgres
```

- Backend gate: `cd backend && python -m pytest -q && python -m ruff check .`, then the same `pytest` with `AQONE_PROBE_PG_ADMIN_URL` set so the probes run instead of skipping.
- Web gate: `cd web && node --test test/*.test.js` and `node --check` on every `js/` and `test/` file (the directory form `node --test test/` fails on Node 24; use the glob).
- Render check (from Phase 1): `cd tools/render-check && npm ci && node render_check.mjs --out ../../docs/render-fixes/<phase>` against a backend started as in the audit recipe.

## Phase 1: demo, seed data and the render check run end to end

Requirements: RND-08, RND-09
State: Complete - 2026-09-26, evidence `docs/render-fixes/EVIDENCE.md`

### Tasks

- [x] Red tests: `backend/tests/test_sos_provenance.py` for the SEC-06 rule as a pure function; `backend/tests/test_demo_probe.py` (uses `probe_db`) that regenerates, starts `squall-fleet` and fires beats 4, 5 and 6; `backend/tests/test_generator_probe.py` that inserts one default-id row into each of the three tables after a regenerate.
- [x] Move `SosProvenance` into `app/incidents/trust.py` and add `sos_provenance(vessel_id, requested_tier, source, buoy_id, src_id, seq, *, device_vessel_id, gateway_authenticated)`; the route translates its header and dependency into those two plain values and calls it.
- [x] Rename `_upsert_sos` to `record_sos` and update every caller found by grep, including tests.
- [x] `app/demo/scenarios.py` `_write_incident`: build a direct, self-declared provenance through `sos_provenance` and call `record_sos` in its own transaction; delete the `ingest_sos` import.
- [x] `app/simulation/generator.py` `regenerate`: after the inserts, inside the same transaction, advance each sequence with `setval(pg_get_serial_sequence(<table>, 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL)` for `squall_events`, `incidents` and `sos_events`.
- [x] `tools/render-check/`: `package.json` pinning `playwright-core`, `render_check.mjs` (logs in through `login.html`, prints measurements as JSON, saves named screenshots), `seed_live_currents.sql` (marks recent synthetic currents live in a disposable database only, with a loud header), and a `README.md` holding the recipe above.
- [x] Update `docs/18_BACKEND_STRUCTURE.md` for the moved rule and `record_sos`.

### Verification

- [x] Red tests fail on `fc89fe7` for the stated reason, then pass.
- [x] Backend gate with and without `AQONE_PROBE_PG_ADMIN_URL`.
- [x] Manual: on a fresh disposable database, `curl` the scenario start and beats 0 to 6; every call returns 200.
- [x] Evidence in `docs/render-fixes/EVIDENCE.md`.

### Review and checkpoint

- [x] Review correctness, scope, dependencies, and unrelated changes; confirm `tests/test_incidents_is_pure.py` still passes with the moved rule.
- [x] Update plan, evidence, Current Register and handoff.
- [x] Stage only reviewed phase paths and verify the staged diff.
- [x] Commit, merge to `master`, push, and confirm `origin/master` moved.

Checkpoint message: `fix(demo): record demo SOS through the application function and repair seed sequences`
Continue automatically to the next phase.

## Phase 2: anomaly reasons and factors honour the contract

Requirements: RND-02
State: Complete - 2026-09-26, evidence `docs/render-fixes/EVIDENCE.md`

### Tasks

- [x] Amend `docs/05_PUBLIC_API.md` first: state the factor object `{code, value, weight, contribution, description}` once and use it for `reasons` and for each `factors` row of `GET /api/ai/anomaly/active`; note the change to the dashboard owner (Arnold) in the register.
- [x] Red tests: route tests for both endpoints with a fake pool whose `jsonb` column comes back as text; web tests for `tripCheckRowHtml` on the contract example and for the risk-feed factor rows.
- [x] One mapper in `app/api/anomaly.py` from a stored factor to the contract factor, decoding text defensively; `anomaly_cases.py` imports it. No change to `app/ai` or the database.
- [x] `dashboard-ai-ops.js` risk feed reads `code` and `description`.

### Verification

- [x] Backend and web gates.
- [x] Render check: after beat 4 and an evaluation, the trip-check row shows "Late beyond the expected-contact window." (screenshot; the tab is still clipped until Phase 3, so the harness opens it by script and says so).

### Review and checkpoint

- [x] Review, update plan, evidence, register and handoff; stage, commit, merge, push.

Checkpoint message: `fix(anomaly): serve reasons and factors in the contract shape`
Continue automatically to the next phase.

## Phase 3: trip anomalies are visible and honest on the dashboard

Requirements: RND-01, RND-03, RND-04
State: Complete - 2026-09-26, evidence `docs/render-fixes/EVIDENCE.md`

### Tasks

- [x] Red web tests: the pure risk-feed renderer (moved from `dashboard-ai-ops.js` into `dashboard-utils.js`) for RND-03; a source check that the vessels module has no vessel literal and a badge-count test for RND-04.
- [x] Tab bar wraps (`D5`): `.stats-tabs` `flex-wrap: wrap`, tabs keep their natural width; check the active underline on both rows.
- [x] Risk feed: notice plus rows when `unavailable`; DEMO badge on `synthetic` rows.
- [x] Delete the hard-coded vessels, their markers and drawers, the two sample overdue drawers in `dashboard-markers.js`, and the filter chips (`D2`); the unstyled `.vessel-next` line goes with them.
- [x] The Vessels tab renders the risk feed, and its badge counts non-`normal` rows.

### Verification

- [x] Web gate.
- [x] Render check at 1280, 1440 and 1920: every tab inside the bar; Trip Checks opened by a real click; risk feed shows V001 under the notice; no fake overdue marker.

### Review and checkpoint

- [x] Review, update plan, evidence, register and handoff; stage, commit, merge, push.

Checkpoint message: `fix(dashboard): show every tab, real vessel risk rows and no sample vessels`
Continue automatically to the next phase.

## Phase 4: the drift card and map explain themselves

Requirements: RND-05, RND-06, RND-11 (plain reasons and button style)
State: Complete - 2026-09-26, evidence `docs/render-fixes/EVIDENCE.md`

### Tasks

- [x] Red web tests: `driftLegendItems(payload)`; the insufficiency sentence map, including the fallback, and a test that reads the `INSUFFICIENT_*` constants from `backend/app/ai/environment.py` so a new code cannot ship without a sentence.
- [x] Replay badge colors from theme tokens with at least 4.5:1 in both themes.
- [x] Add `#ai-map-key` to `dashboard.html`; `updateAiMapKey` renders `driftLegendItems` and hides the key when it is empty; colors come from the existing `aiColors`.
- [x] Scoped light-card style for the "View Activity" button.

### Verification

- [x] Web gate.
- [x] Render check: synthetic replay, `ok` case and insufficient case, light and dark theme; contrast ratios printed.

### Review and checkpoint

- [x] Review, update plan, evidence, register and handoff; stage, commit, merge, push.

Checkpoint message: `fix(dashboard): drift legend, readable replay badge and plain insufficiency reasons`
Continue automatically to the next phase.

## Phase 5: drift rings are honest and the replay matches its evaluation

Requirements: RND-07
State: Not started

### Tasks

- [ ] Record the current `python -m app.ai.drift_eval` output on a freshly generated disposable database (seed 42) before any change.
- [ ] Red tests: tied sparse histogram in `test_drift*.py` (the audit's 500-particle, 250 m case selects 100% for every target today); API test for the replay `forecast_hours`.
- [ ] `_contour_polygon`: select the top cells in descending density up to the index `searchsorted` already finds, instead of `values >= cutoff`; `contours_from_grid` inherits it.
- [ ] One replay function in `app/ai/drift_eval.py` (horizon from the truth track, the evaluator's wind and current inputs) called by `drift_eval` and by the legacy branch of `GET /api/ai/drift/incident/{id}`; the payload adds `forecast_hours`.
- [ ] Rerun `drift_eval`; update `eval_results.json` through the evaluator only; correct `docs/16`, `docs/17` and the quoted figure in `docs/audits/AI_LAYER_DATA_SUFFICIENCY_AUDIT_2026-09-14.md` (append a dated correction, do not rewrite history).
- [ ] Amend `docs/05` for `forecast_hours` on the replay payload.

### Verification

- [ ] Backend gate with probes; before and after evaluator output in the evidence.
- [ ] Render check: the synthetic replay shows three distinct rings and the ground-truth track ends inside the displayed horizon's rings or the evidence says plainly that it does not.

### Review and checkpoint

- [ ] Review, update plan, evidence, register and handoff; stage, commit, merge, push.

Checkpoint message: `fix(drift): honest contour masses and replay at the evaluated horizon`
Continue automatically to the next phase.

## Phase 6: responders open and rerun cases; ended runs refuse reports

Requirements: RND-10, RND-11 (ended runs)
State: Not started

### Tasks

- [ ] Amend `docs/05`: the real-case drift payload adds `forecast_ends_at` (datum plus the run's horizon).
- [ ] Red tests: pure open-case eligibility for an escalated trip check and an acknowledged, unresolved SOS with a position; `eligibleForSearchReport` refuses an ended run; API test for `forecast_ends_at`.
- [ ] "Open drift case" on eligible trip-check rows and in the SOS drawer: object-class choice, `POST /api/ai/drift/cases`, then select the new case in the drift card; a 409 for an existing case selects that case instead.
- [ ] "Rerun" on an open, confirmed case: `POST /api/ai/drift/cases/{id}/rerun`, then reload the case.
- [ ] `drift.py` adds `forecast_ends_at` to the real-case payload.

### Verification

- [ ] Backend and web gates.
- [ ] Render check: open a case from each source through the UI, rerun it, and see search reporting disabled on an ended run with the new reason.

### Review and checkpoint

- [ ] Review, update plan, evidence, register and handoff; stage, commit, merge, push.

Checkpoint message: `feat(dashboard): open and rerun drift cases, refuse reports on ended runs`
Continue automatically to the next phase.

## Phase 7: walkthrough, evidence and documentation close-out

Requirements: RND-01 to RND-11
State: Not started

### Tasks

- [ ] Fresh disposable database, generator, full demo beats 0 to 6, one escalated trip check, one acknowledged SOS; run the whole render check and save every screenshot to `docs/render-fixes/`.
- [ ] Mark each audit finding fixed with its evidence line in `docs/render-fixes/EVIDENCE.md`.
- [ ] Add a dated `docs/08_DEMO_AND_STATUS.md` entry; update the Current Register and `docs/SPEC_INDEX.md`; set this plan to COMPLETE.
- [ ] Note in `docs/40` that its manual acceptance gap is closed by this plan, linking the evidence.

### Verification

- [ ] Backend gate with probes, web gate, render check all green.

### Review and checkpoint

- [ ] Review, stage, commit, merge, push.

Checkpoint message: `docs: record the dashboard render fixes walkthrough`

## Recovery

Follow project `AGENTS.md` for the three-attempt limit and immediate blockers.
Record unresolved work and attempt counts in the worktree's `HANDOFF.md`.
Interrupted or failing work remains uncommitted and the phase remains incomplete.
