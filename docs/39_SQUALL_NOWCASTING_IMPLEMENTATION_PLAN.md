# Squall Nowcasting — Implementation Plan

**Status:** SUPERSEDED — the pressure-array nowcast is replaced by PAGASA weather API squall alerts (PRD §5.1).

> **Note (2026-09-25): barometer dropped.** The buoy barometer is no longer part of the
> architecture; squall alerts now come from the PAGASA weather API (PRD §5.1).
> References below to barometers, pressure readings or the pressure-based squall model
> describe that retired design and the code it left behind (`backend/app/ai/squall.py`,
> `barometric_readings`, `/api/v1/pressure-events`), which stays until it is removed.

## Purpose and delivery rule

Turn the existing synthetic squall demonstration into a truthful,
software-ready nowcasting path: trusted buoy pressure telemetry, explicit data
quality/freshness checks, source-aware warnings, and evidence before a live
`RETURN NOW` claim.

This plan does **not** build or modify buoy firmware, barometer hardware, LoRa
transport, or a new weather vendor integration.  It defines the backend
adapter those owners will send to and makes the product safe while that live
source is absent.  It also does not retune the classifier merely to make a
demo fire.  The current model is trained and evaluated on simulated events;
its published recall is weak, so a synthetic prediction must not masquerade
as a live emergency.

The plan complements the stale-safe squall work in
`docs/37_SHORT_MESSAGING_WEATHER_ADVISORIES_IMPLEMENTATION_PLAN.md`.  If that
plan's Phase 3 has already landed, reuse its implementation and tests instead
of overwriting or recommitting them.  This plan owns the live-telemetry and
operational-readiness steps that remain.

### Mandatory workflow

Before each phase, inspect the branch and preserve unrelated work.  Update the
contract before implementing a changed interface.  Stage only the phase's
named files, inspect the staged diff, run its checks, then create the stated
focused commit.  Never use `git add -A`, amend someone else's commit, commit
generated caches/model artefacts, or stage unrelated mobile work.

Do not start the next phase until the previous phase demonstrably works.  If a
required safety policy or field-data decision is missing, record the blocker
and stop at that gate rather than inventing emergency behaviour.

## Current findings that the implementation must correct

- `backend/app/api/squall.py` and `backend/app/api/public.py` load only rows
  marked `is_synthetic = TRUE`; the current public result therefore cannot be
  current field weather.
- Its `as_of` is the newest synthetic row.  If that data is old, the handset
  can receive a stale synthetic `RETURN NOW` result.
- `extract_pressure_features()` fills an absent series with a nominal
  `1013.25 hPa` value and carries forward arbitrarily old readings.  Missing
  observations must result in an unavailable/insufficient-data result, not a
  fabricated calm baseline or a confident forecast.
- The dashboard and handset already consume distinct protected and public
  routes.  The handset deliberately maps a failed/unknown response to
  `unknown`, not clear; retain that truthful rule.
- The repository's demo verification found the scripted pressure series can
  produce baseline false positives and wall-clock-dependent behaviour.  Keep
  demo data behind an explicit demo path and label it as simulated.

## Safety and acceptance boundary

The finished software must satisfy all of these conditions:

- A live squall computation uses only trusted, recent, valid pressure readings
  from the configured fixed buoy array; it never silently mixes synthetic and
  live rows.
- A missing, stale, malformed, or insufficiently distributed array yields
  `unknown`/`insufficient_data` with the last observation time.  It never
  yields `clear`, `watch`, or `RETURN NOW` by inventing values.
- Synthetic/demo results are available only through an explicitly labelled
  demo workflow and cannot alarm a production handset.
- Official PAGASA notices remain separately attributed official advisories.
  An AqOne model output is never styled or worded as a PAGASA warning.
- `RETURN NOW` is gated by documented field validation and MDRRMO operational
  approval.  Before that gate passes, a live model candidate can be visible as
  `watch` to authenticated responders, but cannot trigger a handset alarm.
- The existing public and dashboard responses report source, observed time,
  generated time, data age, model version/calibration, and an explicit reason
  when the model cannot safely evaluate.

## Phase 1 — Define the trusted pressure-ingest contract

### Work

1. Read `AGENTS.md`, `docs/04_INGEST_API.md`, `docs/05_PUBLIC_API.md`,
   `docs/23_INTEGRATED_SYSTEM_DESIGN.md`, the current auth guards, squall API,
   migrations, and every current pressure-reading caller.  Reuse the existing
   trusted gateway credential mechanism.  If none exists, add only a dedicated
   gateway API-key guard from an environment variable; do not add an auth
   framework or use an operator token for a buoy.
2. Update `docs/04_INGEST_API.md` first with one gateway-only pressure event:
   immutable upstream event ID, configured buoy ID, observed-at timestamp,
   pressure in hPa, and source (`live` or `synthetic`).  Specify acceptable
   timestamp skew, pressure sanity limits, idempotent retry behaviour, and
   that an untrusted/public client cannot write telemetry.
3. Add the smallest additive migration for pressure-event provenance and a
   database uniqueness constraint on the upstream event ID.  Retain existing
   `barometric_readings` and synthetic demo rows; do not rewrite history or
   change buoy firmware protocols in this repository.
4. Add a gateway-authenticated ingest endpoint that validates, stores, and
   deduplicates the event.  Reuse the table and current `is_synthetic` flag;
   do not create a second telemetry service, broker, or queue.
5. Make synthetic writes demo-only: they require the existing demo mode and
   demo key, while normal gateway ingest rejects synthetic input in production.
   Do not make the public squall route a way to seed test data.

### Tests

- Migration/disposable-database test proves legacy readings remain, the event
  ID is unique, and a duplicate delivery creates one logical reading.
- API tests cover bad/missing gateway credentials, an unknown buoy, invalid
  pressure/timestamp, a valid live insert, retry idempotency, and rejection of
  synthetic data outside demo mode.
- Run `python -m pytest -q tests/test_squall.py` plus the new ingest tests and
  `ruff check .` from `backend`.

### Commit

`feat(telemetry): ingest trusted buoy pressure readings`

## Phase 2 — Make the pressure array quality-aware

### Work

1. Before coding, obtain and record one MDRRMO/technical-owner decision for:
   the intended sample interval, maximum acceptable age, minimum number of
   independent fixed buoys, minimum spatial geometry, and operational pressure
   sanity range.  The model needs at least three suitably distributed buoys to
   estimate propagation; do not guess a more permissive rule because a demo
   has fewer readings.
2. Add a small data-quality result to the existing squall service.  It must
   identify per-buoy freshness, valid recent history, array coverage, source,
   and an explicit insufficiency reason before feature extraction runs.
3. Stop `_latest_before()`/feature extraction from inventing a nominal pressure
   for an empty series or carrying forward data beyond the agreed freshness
   window.  A short, documented interpolation/hold may be used only when all
   quality rules still pass; otherwise return insufficient data.
4. Load one source at a time.  Production dashboard/public reads select live
   rows only; the demo control path selects synthetic rows only.  Use the
   server clock to compute data age, not the newest row as a surrogate for the
   current time.
5. Preserve the present deterministic feature/model code for a quality-passing
   array.  This phase is a gate before it, not a classifier rewrite or a new
   configuration system.

### Tests

- Unit tests cover a complete fresh array, one empty series, one stale buoy,
  out-of-order readings, a pressure outside the agreed sanity range, and
  collinear/insufficient geometry.
- Assert that no feature bundle is produced from an empty/stale series and
  that the result exposes `insufficient_data` with its newest real timestamp.
- Assert that synthetic rows are invisible to the live loader and vice versa.
- Run targeted squall/ingest tests and `ruff check .` from `backend`.

### Policy decision, recorded 2026-08-29

Satisfies Work item 1's stop condition. Approved by the MDRRMO/technical
owner via the user in this session:

- Sample interval: every 5 minutes.
- Latest-reading age: no more than 10 minutes behind server time.
- Minimum array: 3 distinct fixed buoys with valid readings.
- History requirement: each qualifying buoy must cover the 90-minute model
  lookback; no gap may exceed 10 minutes.
- Geometry: the qualifying buoy locations must be non-collinear, via the
  existing `geometry_degenerate == false` check — no new distance threshold.
- Pressure sanity range: 850.0–1100.0 hPa, finite numeric values only.
- Any failed requirement returns `unknown`/`insufficient_data`, never
  `clear` or `RETURN NOW`.
- Synthetic data remains demo-only and visibly labelled.
- `RETURN NOW` remains disabled for live use until the later
  field-validation and MDRRMO approval gate (Phase 4) is met.

Implemented as `assess_array_quality()` in `backend/app/ai/squall.py`,
using the constants above (`QUALITY_SAMPLE_INTERVAL_MINUTES`,
`QUALITY_MAX_READING_AGE_MINUTES`, `QUALITY_MIN_BUOYS`,
`QUALITY_MAX_GAP_MINUTES`, `QUALITY_PRESSURE_MIN_HPA`,
`QUALITY_PRESSURE_MAX_HPA`).

**Scope landed in this pass vs. deferred:** the quality-assessment function
itself is complete and unit-tested (`backend/tests/test_squall.py`). Wiring
it into `app/api/squall.py`/`app/api/public.py` — switching production
reads to live-only rows and rejecting an insufficient array before
`extract_pressure_features()` runs — is deferred to land together with
Phase 3's demo-only control surface, so the currently-working synthetic
demo path is never left unable to display anything in between. Until that
wiring lands, `_latest_before()`'s nominal-pressure fallback for an empty
series is also left as-is: it is only unsafe on an unguarded read path, and
today's only caller of that path is the synthetic demo, not a live array.

### Commit

`fix(squall): reject stale and incomplete pressure arrays`

## Phase 3 — Publish source-aware, alarm-safe nowcast status

### Work

1. Stabilize one shared response shape for the protected dashboard route and
   `GET /api/public/squall`: `source`, `calibration`, `observed_at`,
   `generated_at`, `data_age_seconds`, `status_reason`, `level`, and the
   existing detection details only when quality passes.  Update
   `docs/05_PUBLIC_API.md` before changing the response.
2. Use the smallest truthful states:

   - `unknown` — unavailable, stale, invalid, or incomplete telemetry;
   - `clear` — a fresh, quality-passing live array with no detection;
   - `watch` — an eligible model candidate, visible to responders;
   - `return_now` — only after the operational validation gate below is
     enabled.

   Do not downgrade unavailable data to clear.  Do not let a classifier score
   alone override the validation gate.
3. Keep the existing synthetic scenario usable through a demo-only API/control
   surface that carries `source: synthetic` and a visible simulation label.
   Remove any production route path where old synthetic rows can create a
   dashboard banner or handset alarm.
4. Apply the stale/unknown contract from Plan 37 to `SquallWatch`, the banner,
   and alert page.  Show the most recent observation time/reason where space
   permits, preserve an already displayed warning during a transient fetch
   failure, and never create a new alarm for stale/synthetic data.
5. Update the dashboard squall panel to show freshness/source/calibration and
   a neutral insufficient-data state.  Reuse its existing polling and map
   layers; do not add WebSockets or a second weather panel.

### Tests

- Route tests prove no current telemetry is `unknown`, fresh valid non-event
  data is `clear`, a fresh qualified model candidate is `watch` before the
  validation gate, and stale/synthetic data cannot be public `RETURN NOW`.
- Test public-route access remains unauthenticated while the dashboard route
  remains protected; telemetry ingest remains gateway-only.
- Add/extend mobile tests for parsing `status_reason`, no new stale alarm, and
  server-side level precedence.  Run the smallest dashboard rendering check
  for clear, watch, and insufficient data.
- Run `python -m pytest -q`, `ruff check .`, `flutter analyze`, and the
  targeted squall/mobile tests.

### Commit

`feat(squall): publish source-aware nowcast status`

## Phase 4 — Establish evidence before enabling RETURN NOW

### Work

1. Repair the evaluation protocol before changing any threshold: separate
   events in time and, where possible, location; report precision, recall,
   lead time, calibration/Brier score, false-alert rate, and the count of
   excluded low-quality windows.  Retain the existing simulated evaluation as
   explicitly labelled demo evidence, not field validation.
2. Add a transparent pressure-tendency baseline to the *evaluation only*.
   Compare it with the current logistic model.  Keep the simpler baseline if
   the model does not improve time-separated validation; do not add another ML
   library, ensemble, or live retraining.
3. Create a compact field-validation log template in `docs/08_DEMO_AND_STATUS.md`:
   fixed buoy locations, clock sync, sampling continuity, calibration checks,
   official-event/observer ground truth, false alerts, misses, lead time, and
   outage periods.  Field collection and weather-event labelling require the
   responsible hardware/operations owners; this plan does not fabricate them.
4. Set an explicit release gate in documentation and code: a named MDRRMO
   approver must review a recorded field-validation set and enable an existing
   deployment environment flag before `return_now` is allowed.  Default off.
   No hidden threshold override and no production training endpoint.

### Tests

- Regression test proves the evaluator does not train and score the same event
  group on both sides of its split, and emits each required metric.
- Regression test covers a quality-failing event window and verifies it is
  counted as excluded rather than scored as calm.
- Tests prove the release flag defaults to watch-only and can enable
  `return_now` only for fresh, quality-passing live input.
- Run the evaluator against the committed synthetic fixture, targeted tests,
  `python -m pytest -q`, and `ruff check .`.

### Status, recorded 2026-08-29

Work items 1-3 and the code half of item 4 are done. Item 4's *approval*
half — a named MDRRMO approver, an actual completed field-validation set —
is explicitly not done and not fabricated, per the user's direction.

- **Evaluation protocol repaired** (`backend/app/ai/squall_eval.py`):
  `evaluate()` is now a pure, database-free function that splits *events* by
  time (train on the earlier half, score only the later half — a model
  never sees a "future" event during training), runs
  `assess_array_quality()` on every candidate window before scoring it
  (a quality-failing window is excluded, never scored as calm), and reports
  precision, recall, mean lead time, a Brier score, false-alert rate, and
  excluded-window counts for both the model and the baseline below. No
  longer trains or saves the deployed model bundle as a side effect — that
  stayed `POST /api/ai/squall/train` alone (`ALLOW_TRAINING`-gated), closing
  the "no production training endpoint" requirement in item 4 more firmly
  than before. `train_from_rows()`'s own internal random-split
  self-evaluation still runs as part of training, for that endpoint's own
  use, but is no longer what `squall_eval.py`/`GET /api/ai/metrics` report —
  every section this script writes is tagged `"note": "synthetic demo
  evidence only - not field validation"`.
- **Transparent baseline added**: a fixed, untuned 1.5 hPa array-pressure-drop
  threshold (`BASELINE_ARRAY_DROP_THRESHOLD_HPA`), scored on the same
  held-out split. `evaluate()` reports which one the held-out numbers
  actually favor (`recommendation: "model" | "baseline"`) rather than
  assuming the logistic model wins. The deployed detection path
  (`current_detection`/`build_squall_status`) has **not** been switched to
  the baseline this session — that would be a real model-swap decision, not
  evidence-gathering, and is left for deliberate follow-through once real
  (not synthetic-fixture) numbers exist.
- **Field-validation log template added**: `docs/08_DEMO_AND_STATUS.md`
  "Squall field-validation log" — blank, dated-copy-per-deployment template
  covering buoy locations, clock sync, sampling continuity, calibration
  checks, event-by-event official/observer ground truth, and summary
  figures. Explicitly not filled with placeholder numbers.
- **Release gate**: `SQUALL_RETURN_NOW_ENABLED` (added in Phase 3, ahead of
  this phase, because the safety boundary is global and applies from the
  moment production reads live rows — see Phase 3's own note). Confirmed
  here to default off (`backend/.env.example`), to be the single choke point
  for `return_now` on live data (`build_squall_status()` is the only place
  `level` is ever set, across the dashboard/public/demo routes), and to have
  no override. The field-validation log template's own "Release gate
  sign-off" checklist is the actual mechanism item 4 asks for: an approver
  cannot sign off a log that does not exist yet, and none has been created
  or fabricated. `RETURN NOW` remains unavailable for live use.

### Commit

`test(squall): add time-split nowcast evaluation`

## Phase 5 — Deploy and rehearse without overstating readiness

### Work

1. Configure the gateway credential and any approved validation gate only as
   Railway environment variables.  Do not commit values or print them in logs.
   Keep the validation gate disabled until Phase 4's field evidence is signed
   off.
2. In a non-production or explicitly approved demo environment, ingest a
   complete fresh pressure fixture, verify a clear/watch transition, then age
   or remove a buoy reading and verify the state becomes insufficient/unknown.
   Separately run the synthetic demo route and verify that it is labelled and
   cannot alarm a production handset.
3. Verify the current Railway health endpoint, ingest authorization, public
   stale/unknown response, dashboard status rendering, handset no-new-alarm
   behaviour, and the absence of synthetic rows from production output.
4. Update `docs/08_DEMO_AND_STATUS.md` and the README only with exact observed
   environment, timestamps, source type, checks, results, and the remaining
   hardware/field-validation dependency.  Keep the existing disclosure that
   synthetic calibration is not a PAGASA warning or a field-proven alert.

### Tests

- `python -m pytest -q` and `ruff check .` pass in `backend`.
- `flutter analyze` and the targeted squall tests pass in `mobile`.
- Manual acceptance: a responder can distinguish live quality-passing status,
  insufficient telemetry, a demo simulation, and an official advisory; a
  fisherman never receives a new alarm from stale or synthetic data.

### Status, recorded 2026-08-29

Full results in `docs/08_DEMO_AND_STATUS.md`'s dated entry for this phase
and in the README's "Squall nowcasting Phase 5 verification" section. Summary
against each work item:

1. **Not performed.** Configuring Railway environment variables requires
   deployment-platform access this session does not have. No credential or
   flag value was set, printed, or fabricated anywhere.
2. **Partially performed.** No live database was available to POST a real
   pressure fixture and watch an HTTP-observed clear→watch→unknown
   transition end to end (same constraint every prior phase recorded; a
   local Postgres service is running on this machine, but its credentials
   are unknown and the user declined pursuing them further for this phase).
   Substituted with: the full automated suite, which exercises the identical
   code paths against fake pools (`backend/tests/test_squall.py`), and a
   real local browser DOM check of the frontend's rendering of that same
   state machine with no backend reachable at all - which is itself the
   `unknown` end of the transition, confirmed live in a real browser rather
   than only asserted in a unit test.
3. **Partially performed**, directly against the real Railway deployment
   (read-only checks, one deliberately-unauthenticated POST, no writes):
   Railway health endpoint ✅ confirmed; ingest authorization ✅ confirmed
   (`POST /api/v1/pressure-events` correctly 401s with no key); public
   stale/unknown response ✅ confirmed, though it reflects the pre-Phase-3
   build still running in production; dashboard status rendering — confirmed
   locally (real browser, static frontend, no backend) rather than against
   the live deployment, since production has not been redeployed with this
   session's work; handset no-new-alarm behaviour — confirmed via the mobile
   automated suite only, no physical device; absence of synthetic rows from
   production output — true by construction once this branch is deployed
   (production reads live rows only), not independently observable from
   outside without a database credential.
4. **Done.** `docs/08_DEMO_AND_STATUS.md` and the README updated with exact
   environment, timestamps, checks, and results; no other files touched for
   this item.

**Net effect on readiness:** unchanged from Phase 4 - `RETURN NOW` remains
unavailable for live use, both because `SQUALL_RETURN_NOW_ENABLED` defaults
off in code and because the code that enforces any of this has not yet been
merged to `master`/redeployed to the live instance this session could reach.

### Commit

`docs(squall): record staged nowcast verification`

## Handoff checklist for Claude Code

- Read the PRD's squall section, `docs/23_INTEGRATED_SYSTEM_DESIGN.md`,
  `docs/31_DEMO_VERIFICATION_01.md`, and Plan 37 before touching code.
- Preserve the existing Manual SOS, messaging/advisories, and anomaly-plan
  work in the dirty workspace.  Do not reformat, stage, or commit it.
- Do not run `POST /api/ai/squall/train` in deployment and do not replace the
  committed model artefact as part of telemetry plumbing.
- Report the exact test commands and commit hash at the end of every phase.
  Stop before the next phase if a test, policy gate, or field-data prerequisite
  has not passed.
