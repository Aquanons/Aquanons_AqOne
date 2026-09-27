# Drift Prediction and Search Re-tasking — Implementation Plan

## Purpose and delivery rule

Make the existing Monte Carlo drift model and Bayesian posterior update into a
truthful responder decision-support loop:

`confirmed incident → fixed, auditable drift snapshot → negative-sector report → updated posterior → next-area recommendation`

The result helps an authorized MDRRMO/PCG responder decide where to search
next.  It does not create an incident automatically, dispatch an asset,
navigate a boat, declare a person found, or replace SAR command judgement.

This work begins only after the Manual SOS/responder loop is demonstrably
working.  An automatic-distress candidate from Plan 38 becomes eligible only
after a responder explicitly escalates it.  The buoy/current hardware is not
in this handoff: this plan makes its absence visible and blocks a production
search field rather than fabricating a live current forecast.

### Mandatory workflow

Before each phase, inspect the branch and preserve unrelated work.  Update the
shared contract first when an interface changes.  Stage only the named phase
files, inspect the staged diff, run its checks, and create the stated focused
commit.  Never use `git add -A`, amend someone else's commit, commit secrets
or generated cache/model files, or stage unrelated mobile/SOS work.

Do not begin a phase until the preceding phase has passed.  Stop at a missing
operational policy decision rather than guessing a value that changes a real
search decision.

## Current findings that the implementation must correct

- The backend can already simulate drift, persist a prior/posterior grid, and
  update mass after a searched bounding box.  The basic Bayesian math and
  contour recalculation have focused tests.
- The incident route still exposes `true_track`, a synthetic evaluation field,
  through the normal responder payload.  Ground truth must never appear for a
  real incident.
- A new incident prediction is recomputed on reads while the prior is cached
  only when a search is recorded.  This can make a displayed prediction and
  its posterior belong to different environmental inputs.
- The current-field factory can fall back to the synthetic current equation
  whenever observations are absent.  Its fraction is displayed, but a zero
  observation fraction is not sufficient evidence for a production search map.
- Search reporting accepts raw metre offsets, allows detection probability
  `1.0`, has no responder/audit identity or idempotency key, and can lose a
  concurrent posterior update.  It is a demo primitive, not an operational
  record.

## Safety and acceptance boundary

The finished loop must meet all of these conditions:

- Only a confirmed Manual SOS incident or responder-escalated anomaly can open
  a real drift/search case.  A new anomaly, arbitrary client request, or
  public caller cannot do so.
- The selected object class, last-known point/time, environmental-input source,
  coverage, data age, run time, and model version are recorded with the first
  prediction.  Subsequent reads return that fixed snapshot.
- A production prediction requires the agreed minimum fresh observed-current
  coverage and non-degraded wind input.  If either is unavailable, it is
  `insufficient_environmental_data`, not a contour inferred from a synthetic
  fallback.  Synthetic inputs remain demo/evaluation-only and visibly labelled.
- A negative sector report reduces, but never eliminates, probability mass;
  it is attributable, idempotent, ordered, and applied atomically.
- The system returns a ranked *next area* from the remaining posterior.  It
  never assigns an asset, plots a navigation route, or automatically re-tasks
  a crew.
- The dashboard distinguishes prior versus updated posterior, searched areas,
  input quality, synthetic replay, and a human recommendation.  It never
  exposes synthetic ground truth for a real incident.

## Phase 1 — Define a responder-confirmed drift case

### Work

1. Read `AGENTS.md`, the PRD drift/search section, `docs/05_PUBLIC_API.md`,
   `docs/23_INTEGRATED_SYSTEM_DESIGN.md`, the Manual SOS and anomaly plans,
   `backend/app/api/drift.py`, current migrations, and dashboard callers.
2. Update `docs/05_PUBLIC_API.md` first with the protected case lifecycle:
   create/open only from a confirmed SOS or responder escalation; required
   last-known position/time; responder-selected object class; current case
   state; and read/action permissions.  Include the explicit non-goals of
   automated dispatch and navigation.
3. Add the smallest additive schema needed to link a drift/search case to its
   source incident/SOS/anomaly and record `confirmed`, `resolved`, or
   `cancelled` state plus creator/time.  Reuse the existing `incidents` and
   its prior/posterior fields; do not introduce a second incident system.
4. Replace/retire the unrestricted ad-hoc production path as appropriate.
   A protected responder action opens a case only after the source is
   confirmed, and requires an explicit object-class choice rather than deriving
   a real-world target solely from a vague abnormal reason.  Keep a narrowly
   scoped demo fixture path for synthetic cases.
5. Remove `true_track` from normal responder payloads.  Return it only from a
   demo/evaluation-only route guarded by the existing demo controls, and make
   the dashboard render it only for a clearly synthetic replay.

### Tests

- API/auth tests cover anonymous access, a normal operator lacking a confirmed
  source, a valid confirmed SOS/escalation, duplicate case creation, and
  resolved/cancelled cases being unavailable for new search reports.
- Serialization tests prove a real incident response contains no ground-truth
  field, while a demo response is visibly marked synthetic.
- Run targeted drift/API/auth tests and `ruff check .` from `backend`.

### Commit

`feat(drift): open responder-confirmed search cases`

## Phase 2 — Freeze honest environmental-input snapshots

### Work

1. Before coding, document and obtain owner approval for the minimum observed
   current coverage, maximum current age, maximum wind-forecast age, and
   acceptable field geometry for a production search field.  These are safety
   policy values; do not choose them to make a synthetic demo work.
2. Split environment loading into explicit live and synthetic/demo modes.
   Production uses only observed `observed_u_mps`/`observed_v_mps` values and a
   non-degraded wind source.  Never select simulator `true_*` columns.  If the
   quality gate fails, return `insufficient_environmental_data` with the
   source, coverage, and ages; do not fall back to the synthetic equation.
3. At case opening, compute one initial prediction and persist its prior grid
   and compact immutable metadata: inputs, input ages/coverage, object class,
   forecast horizon, model/build identifier, and computed time.  A `GET` must
   read the stored run; it must not quietly recompute an incompatible prior.
4. Provide one explicit responder-only “new drift run” action for materially
   newer validated inputs.  It creates a numbered successor snapshot and keeps
   the original plus its search history intact.  Do not automatically replace
   the posterior while crews are acting on it.
5. Preserve the existing NumPy particle model, leeway classes, and contour
   calculation.  No OpenDrift dependency, queue, live retraining, or new
   current model is needed for this phase.

### Tests

- Unit tests cover fresh quality-passing observations, no observations, stale
  observations, insufficient geometry, degraded/missing wind, and a synthetic
  demo run.  The production cases must create no contour when input quality
  fails.
- Test snapshot stability: repeated case `GET`s return the identical stored
  prior/metadata; an explicit rerun creates a separate version without
  modifying the first.
- Regression test proves the estimator reads `observed_*` and never `true_*`.
- Run `python -m pytest -q tests/test_current_field.py tests/test_drift.py
  tests/test_drift_api.py` and `ruff check .` from `backend`.

### Commit

`fix(drift): make prediction inputs and snapshots honest`

## Phase 3 — Harden posterior updates and recommend the next area

### Work

1. Update the documented protected search-report contract before code.  Accept
   a map-space rectangle (south/west/north/east) or the existing grid bounds
   only through one canonical form, validate non-zero in-grid area, and convert
   at the backend boundary.  Do not force a responder to hand-calculate metre
   offsets from a map.
2. Obtain and record the responder-approved detection-probability presets and
   their operational meaning (for example, search method/visibility), with an
   upper bound strictly below one.  The UI submits a named approved preset, not
   a free-form claim of perfect detection.
3. Extend `search_sectors` minimally with run identity, reporter identity,
   report time, selected coverage preset/method, optional concise notes, and an
   idempotency key.  Preserve existing synthetic sectors and replay ability.
4. Make the report transaction atomic: lock the current search-run state,
   reject a stale/superseded run, deduplicate the idempotency key, apply the
   negative-evidence update once, save the next posterior, then append the
   audit record.  Validate bounds/order before any write.
5. From the updated posterior, return one simple **recommended next area**:
   the highest remaining grid cell (or contiguous highest-mass cell group) as
   a geographic rectangle/centroid and remaining mass.  Label it
   “recommendation for responder review,” not an asset task.  Do not add route
   optimization, crew rosters, automatic assignments, sighting fusion, or a
   separate search-planning service.

### Tests

- Preserve existing normalization/mass-reduction tests and add invalid/reversed
  bounds, out-of-grid sector, duplicate idempotency key, and two sequential
  reports against the same run.
- Transaction/API test proves the second report sees the first report's
  posterior rather than overwriting it, and a report cannot use a resolved or
  superseded case.
- Assert a detection probability of `1.0` is rejected and the returned next
  area lies within the grid with positive remaining probability.
- Run targeted search/drift API tests and `ruff check .` from `backend`.

### Commit

`feat(search): persist negative-search re-tasking`

## Phase 4 — Complete the responder dashboard loop

### Work

1. Reuse the existing drift selector, contour layers, and searched-sector
   rendering in `web/js/dashboard/dashboard-ai-ops.js`.  Do not create a
   second map or add a drawing-library dependency.
2. Add the smallest map interaction for a responder to mark a rectangle:
   select the case/run, choose two map corners using native Leaflet events,
   select an approved search-coverage preset, review a clear confirmation, and
   submit the protected search report with an idempotency key.  Disable the
   action when the case is not confirmed, inputs are insufficient, or it is a
   demo replay.
3. After a successful report, reload the case and render the updated posterior
   contours, labelled searched rectangle, audit time/reporter/method, and the
   next-area recommendation.  Preserve the original prior as an optional
   reference, not the active map state.
4. Show environmental source, observation fraction/coverage, age, wind state,
   snapshot time, synthetic status, and any insufficiency reason.  Remove the
   generic “ground truth” copy for real cases.  Keep map text as responder-only
   operational UI; no fisherman-facing drift screen is part of this plan.

### Tests

- Add the smallest existing dashboard test/check for: no eligible case,
  insufficient input, a real confirmed case, a synthetic replay, and a
  successful sector update/reload.  Manually verify the two-corner rectangle
  against the displayed map and server validation.
- Verify the UI never presents the recommendation as an assigned asset or
  navigation instruction.
- Run the dashboard checks plus targeted backend tests and `ruff check .`.

### Commit

`feat(dashboard): support search-sector re-tasking`

## Phase 5 — Evaluate, deploy, and record the exact evidence

### Work

1. Keep `backend/app/ai/drift_eval.py` explicitly synthetic until a separately
   approved, ground-truthed field dataset exists.  Report containment inside
   the 95% contour, area reduction against the documented baseline, runtime,
   observed-current fraction, excluded low-quality runs, and the post-search
   posterior change for a fixed synthetic incident.  Do not call this live SAR
   accuracy.
2. Run the evaluator before and after the input/snapshot work and record both
   outputs.  If observed input lowers containment or broadens the search area,
   record it; do not keep a flattering synthetic fallback.
3. In an approved non-production/demo environment, open a synthetic confirmed
   case, inspect the initial contours, submit a negative sector, reload, and
   verify the posterior/next-area change and audit history.  Then verify a
   production-mode case without adequate current/wind data stops at the honest
   insufficiency state.
4. Verify the Railway health endpoint, protected case/search endpoints,
   dashboard reload persistence, and that no real payload leaks ground truth.
   Update `docs/08_DEMO_AND_STATUS.md` and README only with exact environment,
   source type, commands, observed results, and remaining field-validation
   limits.  Correct any current “live” claim that the verification cannot
   support.

### Tests

- `python -m pytest -q` and `ruff check .` pass in `backend`.
- Run the dashboard checks from Phase 4.
- Manual acceptance: a responder can open only an eligible case, see an honest
  stable search field or insufficiency reason, record one negative search,
  reload the updated posterior, and review—not auto-dispatch—the next area.
  Gap found 2026-09-26: the dashboard had no way to open or rerun a case, so
  this could only be done through the API. Closed 2026-09-27 by
  `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md` (RND-10),
  evidence `docs/render-fixes/EVIDENCE.md`.

### Commit

`docs(drift): record responder search-loop verification`

## Handoff checklist for Claude Code

- Read the PRD drift/search section, `docs/14_PRD_AUDIT.md`,
  `docs/15_AUDIT_FIX_PROMPTS.md`, and the preceding Manual SOS/anomaly plans
  before coding.
- The project currently contains simulated incidents, currents, and ground
  truth.  Treat those as demo/evaluation assets, never as production evidence.
- Do not modify the particle model or introduce an external SAR dependency in
  this handoff.  The safety work is provenance, input quality, immutable runs,
  audited negative evidence, and a human-readable next-area recommendation.
- Report the exact tests and commit hash after every phase; stop before the
  next phase if a test, policy choice, or environment-data prerequisite fails.
