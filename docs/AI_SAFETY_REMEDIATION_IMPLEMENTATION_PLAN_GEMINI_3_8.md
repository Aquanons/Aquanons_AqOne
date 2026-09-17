# Implementation Plan: AqOne AI Safety Remediation for Gemini 3.8

> **Status:** Prepared for handoff; no implementation or field phase started.
> **Target Branch:** Proposed `codex/ai-safety-remediation`; create from the inspected working state only when execution is authorized and local changes are protected.
> **Test Command:** Backend: `python -m pytest -q` in `backend`; mobile: `flutter test` in `mobile`; web: `node --test web/test/*.test.js` at repository root.
> **Lint/Check Command:** Backend: `python -m ruff check .`; mobile: `flutter analyze`; firmware: `pio run -d firmware -e buoy -e shore`; changed web JavaScript: `node --check <path>`; documentation: `git diff --check`.
> **Prepared:** 2026-09-15.
> **Evidence revision:** `601288fa03111252c1a67dcb8c5faa3996385397`, branch `codex/ai-accuracy`, plus the existing re-audit and concurrent documentation edits.
> **Executing agent:** Gemini 3.8.
> **Non-negotiable:** Write and run the relevant failing test before every production code change, including migrations, firmware, scripts, configuration, and refactoring.

## Overview

Repair the actual warning, drift, and search paths, then establish trustworthy calibration and independent field evidence for the before/during/after fishing scenario.
Reuse the existing advisory transport, trip records, drift runs, particle simulator, and evaluation functions.
The deliverable is working, tested software with measured claim boundaries; missing physical evidence remains explicitly incomplete regardless of how many unit tests pass.

This document is the active Gemini handoff for the five named issues.
The original accuracy plan, simplification plan, and audits remain historical context.
This planning session creates this document and links it from the root plan; it does not implement tests or fixes.
The test specifications below are written before their corresponding implementation instructions so Gemini can first turn them into runnable failing tests.

## Execution instructions and scope

1. Read `AGENTS.md`, `docs/00_START_HERE.md`, `docs/Aqone_PRD (2).md`, this plan, and the relevant shared contracts.
   Read `mobile/lib/l10n/README.md` before touching handset display text.
2. Record the current revision, staged/unstaged/untracked paths, actual runtime locations, and baseline results.
   Preserve other work, including the existing re-audit and unrelated deadline/documentation edits.
   Do not reset, stash, stage, or commit somebody else's changes.
3. Verify the applicable sequential hardware prerequisites in `AGENTS.md` using evidence, or obtain an explicit applicable exception before executing work ahead of them.
   This planning request does not claim hardware steps are complete or authorize an unrelated build-order exception.
   Read-only investigation and writing the plan can proceed independently of hardware availability.
4. Execute only after the user authorizes implementation, then one phase at a time.
   Each phase ends with verification, Ponytail review, an atomic conventional commit of reviewed paths, and explicit user sign-off before the next phase.
   Planning alone does not authorize deployment, purchases, live database mutation, real alerts to fishermen, or scheduling field operations.
5. Update shared contracts before changing their producers or consumers.
   Name affected workstreams in the handoff: backend Lenard, gateway Arnold, firmware Daniel, dashboard Jade, mobile/UI Jade and Doreen Kay.
   Report coordination needs to the user; do not send external messages.
6. Scope is offline warnings, physical drift support, time-aligned search, calibration, and field validation.
   Include only the trip fixes necessary to validate the stated storyline and prevent loss of unresolved trips.
   Broad catch, danger-zone, mobile forecast, or cosmetic remediation remains a separate workstream.
7. Reuse existing libraries, clocks, HTTP guards, authentication, SQLite outbox patterns, NumPy, and test frameworks.
   Do not introduce an event platform, generic provider framework, second prediction service, new neural architecture, or bespoke cryptography.
   A necessary dependency for correct shoreline geometry needs a concrete capability comparison first; a home-grown incomplete geometry engine is not the preferred fallback.

### Mandatory test-first loop for every change

For each matrix row in a phase, perform these steps in order:

1. **Specify:** State the user-observable failure, actual entry point, input fixture, expected output, and claim being protected.
2. **RED:** Write the smallest runnable behavioral test and run it against unchanged production code.
   Record the exact command, failing assertion, exit code, revision, and test ID.
   An import error, unavailable tool, database connection failure, or a misspelled API is not a reproduction of the defect.
   Reach the real entry point with existing code before adding an intended new field or interface.
3. **Contract:** Where wire/storage semantics change, document the intended contract before the producer/consumer edit.
   Documentation does not require an invented executable test, but any executable implementation of the contract does.
4. **GREEN:** Make only the production change needed to satisfy that failing behavior.
   A new issue discovered while implementing requires another failing test before its fix.
5. **REFACTOR:** Improve only the touched path while the behavior test remains in place.
   For behavior-preserving cleanup, first add or identify a relevant characterization test; confirm it detects a temporary behavioral fault before editing, then restore the fault.
6. **VERIFY:** Run focused regressions, then the phase gates.
   Log red and green evidence separately; do not rewrite expected outcomes to match an incorrect implementation.

If a proposed defect already passes a meaningful test on the actual path, mark it verified/no change with evidence and investigate the next issue.
Do not force a failure or change correct source solely to satisfy an audit checklist.
For a newly introduced capability, first test its missing behavior through an existing integration boundary rather than generating code merely to satisfy imports.
Tests for the simulator must use analytical or independently constructed truth, not the same simulator as both predictor and oracle.
Stub external network and instruments where required, but do not stub the computation or persistence behavior under test.
Reuse existing test files and small fixtures; use a disposable PostgreSQL database where receipt filtering, transactions, uniqueness, migrations, or replay persistence must actually be exercised.
Mocks of SQL text alone do not prove those properties.
Never target the operational database with the synthetic generator or evaluation tools.

### Evidence record used throughout

Maintain one execution table in this document; leave it empty until execution produces evidence.

| Test ID | Entry point and fixture | RED command / assertion / exit | Production paths subsequently changed | GREEN command / result | Evidence class | Commit |
| --- | --- | --- | --- | --- | --- | --- |
| Pending | No execution during planning | Pending | None | Pending | None | None |

Evidence classes are software regression, compiled firmware behavior, bench hardware, controlled field drill, prospective natural event, and independent held-out evaluation.
Report each separately.
Blocked, skipped, xfailed, or uncollected critical checks are not passes.
Find installed/bundled Python, Flutter, and PlatformIO runtimes before declaring them unavailable; never repeat historic test counts as current evidence.

## Grounding corrections before implementation

The September 15 re-audit is useful context, but it contains recommendations that require qualification.

| Verified current evidence | Consequence for this handoff |
| --- | --- |
| `BuoyClient.warnings()` exists in `mobile/lib/services/buoy_client.dart:165`; active squall polling uses `app_shell.dart` and `VentureFeeds.squall()` | Test the actual UI/feed consumer; another parser-only test cannot close offline delivery. |
| `firmware/shore/AqOneShore/AqOneShore.ino:554` polls `/api/public/advisories`, not the squall endpoint | Transporting authored warnings and transporting an AI-generated research signal are separate producer decisions. |
| `advisories.py:_serialise` emits date strings; `AqOneShore.ino:buildWarnPayload` parses them with a datetime parser | Use an actual serialized advisory as the transport test input; fabricated ISO timestamp fixtures miss expiry failures. |
| `current_observations.created_at` already exists in migration 024 | Reuse receipt time; do not add a second receipt column to fix DRIFT-11. |
| `current_field.py` accepts non-synthetic rows without qualification/depth checks; `as_of` filters observed time only | Enforce provenance, measurement support, and availability in the shared loader and geometry count. |
| `api/drift.py:_compute_and_persist_run` uses `as_of=last_at` | Separate datum time, decision time, forecast valid time, and receipt time; simply adding a second SQL predicate with the wrong cutoff remains wrong. |
| `sos_service.dart:raiseSos` sets `clientTs` from current device time | That is SOS creation time, not demonstrated GNSS acquisition time; `api/drift.py:_sos_case_inputs` currently labels it `client_fix`. |
| Production enables stranding without a polygon; `geo.py:WATER_POLYGON` explicitly includes artificial offshore boundaries | Do not fix this by passing the demo polygon as authoritative land. |
| `search.py:update_trajectory_weights` selects the nearest time and uses the final step if search time is absent | Wiring the helper alone is insufficient; reject/qualify missing and out-of-range time support first. |
| `drift.py` records NumPy trajectory arrays only when requested; API runs persist grids only | Introduce one bounded, serializable run trajectory state and one authoritative posterior computation. |
| `docs/49` allows two buoys within 111 km; `docs/50` says 15 km; `docs/45`, `docs/08`, and `docs/51` give differing lead-time claims | Treat them as unresolved proposals until evidence and a named decision reconcile them; neither radius nor lead threshold becomes validated by copying it. |
| `docs/52` includes a pressure condition inside its supposedly independent wind/squall label | Define an independently observed outcome before collecting labels; avoid selecting only events already visible to the pressure detector. |
| The re-audit lists `degradedBuoyCount` as dead code, but it is absent in the inspected predictor | Do not recreate or delete a nonexistent function; no blanket cleanup is authorized. |

### 🏛️ Council Deliberation: Test-first repair of the actual storyline

#### 1. Grounding

- **Observed Facts:** Existing firmware, mobile clients, trip records, observation tables, and drift/search helpers provide reusable foundations.
  Critical consumer and time/provenance gaps remain in the executed path.
- **Unverified Assumptions:** Field instruments, shoreline suitability, radio coverage, warning lead, independent labels, local search detection rates, and retrospective data availability.
  No written protocol establishes that these measurements have occurred.

#### 2. Perspectives & Debate

- **Devil's Advocate:** An old position with a freshly created SOS timestamp can make a precise-looking drift datum false.
  A local dictionary unchanged after a swallowed exception does not prove a persisted rescue case survives a model failure.
- **Simplicity Champion:** Reuse the warning feed and run tables, then replace the real static-grid posterior path with the existing trajectory approach once its assumptions are tested.
  Do not add optional model inputs before fixing the target and source support.
- **Security Auditor:** Source/date/expiry and relay authenticity are part of warning correctness.
  A queued frame, received bytes, displayed message, and deliberate acknowledgement require different evidence.
- **Architecture / DX:** Store decision-time provenance with immutable run inputs and keep readable old runs intact.
  Isolate software completion from field qualification so a correct insufficiency result can be delivered while collection remains pending.

#### 3. Consensus vs. Tension

- **Where all seats agree:** Tests must enter the actual consumer/API path, predictions need independent outcomes, and missing observations cannot become safety evidence.
- **Core Tension:** Full physical support may require equipment and data that do not exist yet.
  Resolve it by completing tested refusal/conditional behavior in software and retaining an unfinished field gate, rather than inventing local measurements or suppressing unresolved cases.

#### 4. The Verdict (Pragmatic Action)

- **Recommended Path:** Five sequential phases: warning delivery, drift support, search timing, calibration/replay integrity, and real field validation.
  Implement through red-green cycles and stop after each phase for review.
- **Revisit When:** Measured coverage cannot supply useful warning lead, or independent evaluations show the selected inputs cannot support the requested horizon.
  Consider a separately authorized carried radio bridge or additional physical data sources only when those results establish the need.

## Phase 1: Deliver an honest warning through the offline path

**Goal:** Show a valid warning on a phone with no cellular internet but an actual buoy WiFi opportunity, while preserving manual SOS behavior.

### Tests to write and run first

Extend `backend/tests/test_warning_transport.py`, `mobile/test/buoy_client_warnings_test.dart`, `mobile/test/squall_alert_test.dart`, and the existing feed/app-shell integration tests.
Add one focused offline-warning integration test file only if the active consumer has no suitable test home.
Add a small compiled firmware behavior harness for real frame encode/relay/decode and warning cache logic; source-string presence checks are insufficient.
Write the failing build/harness test before changing build configuration if current PlatformIO settings do not compile the intended sketches.

| ID | RED scenario through the real path | Expected behavior before implementing the fix |
| --- | --- | --- |
| W1 | Disable backend HTTP; inject an actual advisory through the buoy HTTP fixture; enter/resume the active app shell | Localized warning appears through normal feed wiring; no cellular connection required; producer source preserved. |
| W2 | Serialize a real date-only advisory, encode it using the gateway function, decode/cache it, query from the handset | Publication and expiry agree on an explicit Philippine calendar/date policy; missing expiry is visibly unknown and bounded by an approved retention policy, never silently immortal. |
| W3 | Signed frame traverses gateway, relay buoy, receiving buoy; then repeat with modified bytes, wrong key, malformed length and expired issue time | Authentic relayed payload verifies; altered payload does not enter cache or update clock; actual codec executes. |
| W4 | First broadcast is lost, or buoy boots after the gateway first sent an unchanged advisory | Active revision is delivered on a bounded retry/rebroadcast schedule; no permanent suppression after mere enqueue. |
| W5 | Warning revised/cancelled; old revision arrives later; handset/buoy reboot; clock unavailable | Older revision cannot resurrect a cancelled warning; retained content keeps original timestamps; unknown clock cannot make it fresh; cache limits are exercised. |
| W6 | Send duplicate and out-of-order gateway/buoy/phone events; attempt another vessel's acknowledgement; lose uplink after display | Events retain occurrence and receipt time, identity and revision; no duplicate acknowledgement; local receipt survives reconnect; missing events remain missing. |
| W7 | Backend AI throws; saturate warning retries; send SOS and verify persisted acknowledgement | Existing saved/relayed/delivered/acknowledged semantics survive; warning work cannot block the manual SOS path. |
| W8 | Phone has neither cellular nor buoy WiFi; later it re-enters buoy range | No claim of new delivery while disconnected; cache age remains honest; warning arrives at measured reconnection opportunity. |
| W9 | Trigger a research squall and inspect its explicit downlink representation alongside an authored advisory; repeat with demo-only synthetic input | Research signal retains its identity, precise valid time and uncalibrated status through the handset; it never becomes an official instruction or return command; synthetic demo cannot enter the real feed. |
| W10 | Real handset model parses date-only advisory, precise-expiry research signal, valid empty list, malformed object, truncated JSON and missing identity/source | Preserve ID, revision and source; honor exact expiry for instants and declared date policy for dates; a parse failure is unavailable, not a valid clear list. |

### Tasks after each relevant RED result

- [ ] 1.1 Establish current command/runtime/build baseline and reproduce W1-W2 using producer-shaped payloads.
- [ ] 1.2 Update `docs/02_LOAM_PACKET_SPEC.md`, `docs/03_PHONE_BUOY_WIFI.md`, `docs/04_INGEST_API.md`, `docs/05_PUBLIC_API.md`, and warning-specific wording in `docs/06_DELIVERY_STATES.md` only where their contracts change.
  Preserve the four canonical SOS delivery states; define warning events separately.
  Specify issue/expiry instants, revision/cancellation, origin, area, receipt authority and payload size without changing advisory date meaning silently.
- [ ] 1.3 After W1/W8 fail, connect `BuoyClient.warnings()` through the existing feed/sync lifecycle and active localized UI.
  Reuse existing timers, request ordering and cache/outbox facilities; preserve the original source and clock uncertainty across reconnection.
  Byte receipt does not prove display, comprehension, or obedience; acknowledge only on deliberate user action.
- [ ] 1.4 After W2-W5 fail, repair gateway serialization, verified relay behavior, bounded retransmission and cache/revision/expiry behavior at their shared boundaries.
  Trace every shared LoAM caller, including SOS/chat/ETA; keep buoy and shore codecs compatible and test old supported frames.
  If reboot persistence is required by the chosen contract, use existing durable storage with bounded writes; otherwise report loss explicitly and re-fetch/rebroadcast.
- [ ] 1.5 After W6 fails, tie receipt events to existing gateway/device identity and warning revision.
  A gateway may attest its own reception and forward source-specific receipts; it cannot assert a user saw a warning without evidence from that handset.
  Offline receipt may sync later; do not overwrite occurrence time with sync time or require receipt events to arrive in order.
- [ ] 1.6 After W9/W10 fail, define and carry a research-signal representation through the same transport, preserving its source, identity, revision, valid interval and uncalibrated status.
  Explicitly connect the squall producer; polling authored advisories alone cannot do this.
  Reuse transport and consumer infrastructure while keeping research data distinct from human-authored/reviewed operational instructions.
  Keep research distribution subordinate to SOS traffic and prevent demo source leakage or automatic official/return commands.
  Distinguish date-only human advisory semantics from precise research expiry in the actual `Advisory` parser/model or its smallest required extension.
  Parser tolerance must not convert malformed/missing evidence into a fresh clear list.
- [ ] 1.7 Run W7 through actual API persistence and the compiled firmware queue path.
  Add described ARB keys, use generated localization through tooling, and retain documented English fallback for unreviewed translations.

### 🧪 Verification Gate

- [ ] Backend: `python -m pytest -q tests/test_warning_transport.py` and `python -m pytest -q`; `python -m ruff check .`.
- [ ] Mobile: `flutter test test/buoy_client_warnings_test.dart test/squall_alert_test.dart`, new consumer test if required, full `flutter test`, and `flutter analyze`.
- [ ] Repository root: `pio run -d firmware -e buoy -e shore`; run the compiled firmware harness using its recorded exact command.
  A build of the wrong/empty source directory is a failure, even if the tool exits zero.
- [ ] Record a bench demonstration when devices are available; physical at-sea delivery remains Phase 5 evidence.
  Phase 1's completion claim is software/bench behavior only, never measured offshore delivery.

### 🔍 Review Gate (Ponytail)

- [ ] One warning consumer lifecycle, bounded caches/retries, no parallel notification platform or new cryptography.
  State whether the receiver verifies origin or merely trusts a gateway/buoy assertion; radio HMAC verification is not handset-verifiable authenticity of unsigned HTTP JSON.
  A public shared development key supports a bench demonstration only; reuse the project's credential provisioning for operational source identity.
- [ ] Tests execute producers and consumers; no fake claim of delivery based on parser/SQL mock success alone.

### 📦 Git Checkpoint

Stage only the reviewed Phase 1 test, contract, source, and plan paths; never use `git add .`.
Commit: `fix(warnings): connect and verify offline warning delivery`.

### 🛑 HARD STOP

Report W1-W10 red/green results, actual build/harness commands, physical checks still pending, reviewed diff and commit hash.
Ask whether to proceed to Phase 2 and wait for explicit confirmation.
This stop comes from `.agents/skills/implementation-plan/SKILL.md`: “Execution must halt at the end of each phase.”

## Phase 2: Make every real drift run respect its evidence

**Goal:** Preserve the case and last-known information while rejecting unqualified data and unsupported time/space claims.

### Tests to write and run first

Extend `backend/tests/test_current_ingest.py`, `test_drift_api.py`, `test_drift.py`, `test_phase4_validation.py`, and the relevant SOS/location tests in backend/mobile.
Use a disposable database test for loader filters and persisted run behavior, with fixture times and known physical vectors.

| ID | RED scenario | Required assertion |
| --- | --- | --- |
| D1 | Mix qualified, uncalibrated, synthetic and contradictory source flags; known surface/deep/unknown-depth measurements | Only physically applicable, qualified, available observations influence geometry count and motion; a caller-provided label alone cannot manufacture a calibration record. |
| D2 | Observation 08:00, receipt 08:20; replay decisions 08:10 and 08:30; datum 07:00 | Row excluded at 08:10 and available at 08:30 within physical support; cutoff is decision time, not datum time; retrospective reconstruction explicitly distinguished. |
| D3 | SOS created now with a 90-minute-old cached GNSS fix; legacy packet has no acquisition time | Creation and position-fix times stay distinct; unknown fix time stays unknown; legacy event IDs/deduplication stay compatible; uncertainty/override decision persists. |
| D4 | Two co-located or one-sided buoys, a point across a headland, deep estuary flow used for surface object | Buoy count alone cannot establish water-connected support; unsupported depth/domain remains insufficient rather than zero flow. |
| D5 | Early supported steps followed by all/partial unsupported particles while average exceeds 0.5; exact 3,600-second current-age boundary | No full-horizon qualified contour; geometry and forcing agree at the age cutoff; first unsupported time/affected mass survives API persistence; missing motion is never interpreted as measured still water. |
| D6 | Equivalent wind timestamps in UTC and +08:00, naive upstream local timestamps, forecast starts after datum or ends early, NaN/nonfinite values | Host timezone cannot shift forcing; invalid/unsupported intervals fail or explicitly shorten the conditional horizon; fetch age does not substitute for forecast issue/valid time. |
| D7 | Trajectory crosses a thin island and exits back into water within one step; exits an artificial offshore domain edge; initial spread contains land points | Land crossing is treated as a collision, open boundary as loss of support, and all mass is accounted for; no invisible particle deletion/renormalization. |
| D8 | Open/rerun/read a real case with no run, stale run, or failed wind/prediction; repeat for explicit demo case | No synthetic real-case fallback; case, datum and search evidence survive; reads remain read-only; a failed rerun does not silently relabel an old run current. |

### Tasks after each relevant RED result

- [ ] 2.1 Correct timestamp/qualification contracts before migration or callers.
  Reuse `current_observations.created_at` and keep unknown historic receipt times unknown; migration backfill time is not historic availability.
  Add only missing calibration reference, measurement depth/coordinate frame, decision cutoff and run provenance fields needed for these tests.
  Preserve old schemas through a new migration; do not rewrite already applied migrations.
- [ ] 2.2 After D1/D2 fail, apply one shared qualification and availability predicate for both geometry counting and forcing.
  Qualification must identify instrument, calibration record/version, applicable depth, timing and uncertainty; unqualified rows may remain stored for diagnosis but cannot support a qualified simulation.
  A run may use later-than-datum observations already available by decision time for reconstruction; future forecasting needs an explicit supported forcing assumption.
  For historical prospective evaluation, both observation and forecast availability must precede decision time.
- [ ] 2.3 After D3 fails, preserve actual position-acquisition time/accuracy when the location source supplies it and carry it through handset, mesh, backend and run datum.
  Do not repurpose `client_ts`, which participates in existing SOS contracts and identity.
  Keep observed position, presumed drift onset, responder override and their uncertainties separate.
  Missing timing permits explicit conditional scenarios or an insufficiency result; never claim `client_fix` merely from send time.
- [ ] 2.4 After D4/D5 fail, make physical support a space/time/depth property of each run, not an unvalidated radius plus average count.
  Reconcile the 111 km/15 km proposals in docs 49/50 as provisional, evidence-dependent policies.
  Until a domain is qualified, return insufficiency for operational contours while keeping explicit research scenarios available and labelled.
  Persist supported horizon, support loss and uncertainty so later GETs match the computed result.
- [ ] 2.5 After D6 fails, parse provider time with explicit UTC/offset semantics and record available forecast valid interval and retrieval time.
  Leave model issue time unknown when the source does not provide it.
  Refuse silent endpoint clamping outside the supported interval; a persistence assumption is a separately labelled conditional input requiring evaluation.
- [ ] 2.6 After D7 fails, distinguish shoreline/land polygons from the open operating-domain edge.
  Validate geographic source, resolution, coordinate order, channel/island geometry and segment crossing, including step-size sensitivity.
  Do not pass `geo.WATER_POLYGON` as an authoritative shoreline fix.
  Account for grounded, afloat and outside-domain probability mass; do not improve containment by discarding unsupported particles.
- [ ] 2.7 After D8 fails, route every real open/rerun/read through the qualified-run behavior and explicitly restrict legacy synthetic computation to demo cases.
  Store usable evidence before attempting simulation; on failure keep responder records and a truthful failure/insufficiency state.

### 🧪 Verification Gate

- [ ] `python -m pytest -q tests/test_current_ingest.py tests/test_drift_api.py tests/test_drift.py tests/test_phase4_validation.py` from backend, plus new database tests with their actual configured disposable connection.
- [ ] Full backend `python -m pytest -q` and `python -m ruff check .`.
- [ ] If SOS wire/location paths changed, repeat Phase 1 firmware checks and mobile `flutter test` / `flutter analyze`, including replay of old packets.
- [ ] Demonstrate both a complete synthetic analytical fixture and a truthful real-input insufficiency result.
  Software phase closure does not imply suitable real forcing or shoreline data was collected.

### 🔍 Review Gate (Ponytail)

- [ ] Reuse receipt time and existing run/source tables; no duplicated loader policy or fabricated defaults for missing physical data.
- [ ] One coherent support decision drives API fields, storage and contours.

### 📦 Git Checkpoint

Stage only the reviewed Phase 2 paths, new forward migration if needed, relevant contracts/tests and this plan.
Commit: `fix(drift): enforce qualified time and spatial support`.

### 🛑 HARD STOP

Report D1-D8 red/green evidence, compatibility/migration results, unqualified physical sources, and commit hash.
Wait for user confirmation before Phase 3 under the implementation-plan skill's phase-stop rule.

## Phase 3: Apply search evidence when and where the search happened

**Goal:** Update the positions of the same simulated objects at the search time, then display their weighted positions at the requested output time.

### Tests to write and run first

Extend `backend/tests/test_search.py`, `test_drift_api.py`, and `test_phase4_validation.py`.
Extend the existing dashboard SAR test module for the submitted and displayed time/probability semantics.

| ID | RED scenario | Required assertion |
| --- | --- | --- |
| S1 | Two equal-weight trajectories; at search time A is in S and B outside; at display time A left and B entered; submit via responder endpoint with illustrative POD 0.8 | A/B final weights are 1/6 and 5/6; present mass of B in S is preserved; persisted grid and displayed contours use those weights. |
| S2 | Search before first/after last trajectory time, absent time, naive ambiguous time, or unsupported interval | No nearest-endpoint/final-step substitution; event remains recorded as unassimilated with a reason or request rejected clearly. |
| S3 | Search spans multiple steps; overlapping repeat sweeps; actual track excludes most of a rectangle | Footprint/time meaning is explicit; one full-operation POD is not repeatedly multiplied per step; correlated repeats do not create artificial certainty. |
| S4 | Retry same report; submit out of order; rerun with changed grid origin/extent; retry stale run | Stable event identity, one application per run, geographic footprint preserved, atomic update and immutable older run inputs. |
| S5 | Unknown detection likelihood versus explicit illustrative POD 0; POD negative, >1 or nonfinite; near-total mass rejection | Unknown stays unknown; invalid rejected; zero leaves prior unchanged; all-zero/degenerate result reports failure rather than fabricating a normalized map. |
| S6 | Persist trajectories, restart process, fetch and update; historical run has grids only | Same weights/coordinates after restart; legacy run remains readable but time-aware update requires supported state; no fake reconstructed trajectories from a centroid. |
| S7 | Rerun decision predates receipt of an earlier search report | That report cannot change the historical prospective posterior; retrospective processing is separately labelled. |

### Tasks after each relevant RED result

- [ ] 3.1 Update search contract with search occurrence interval or explicitly instantaneous observation, report receipt time, geodetic footprint, method, likelihood provenance/uncertainty, run/output time and idempotency.
  Existing `searched_at DEFAULT now()` is report time unless actual occurrence is supplied; do not backfill it as a known search time.
- [ ] 3.2 After S1/S6 fail, persist the existing bounded trajectory representation with run input/version/seed metadata using ordinary serializable arrays and one weight vector.
  At the present 2,000 particles and 10-minute/24-hour settings, estimate storage and enforce request bounds before widening horizons.
  Use the existing database and NumPy; no separate trajectory service or object-store platform without a demonstrated constraint.
- [ ] 3.3 After S1-S3 fail, repair and use `update_trajectory_weights` in the real endpoint and rerun path.
  Adopt a documented temporal interpolation and footprint model with supported resolution; never use nearest-step matching for unsupported times.
  For a finite search interval lacking a time-resolved footprint/detection model, record it as unassimilated rather than pretending it was instantaneous or multiplying a whole-operation likelihood at every step.
  Histogram final particle positions using their posterior weights; derive contours and recommendations from that same state.
- [ ] 3.4 After S4/S7 fail, use geographic search evidence independent of old grid origin, receipt-aware replay, transaction/idempotency protection and explicit rerun state.
  Retain unassimilated reports and reasons for responder review.
  Treat dependent repeat searches conservatively until a justified likelihood model exists.
- [ ] 3.5 After S5 fails, remove the implication that poor/moderate/good are measured 0.3/0.6/0.9 detection rates.
  Default operational unknown likelihood to no quantitative assimilation; allow visibly hypothetical sensitivity scenarios separately.
  Do not replace unknown POD with 0 in stored evidence; only an explicit zero has that meaning.
  Phase 5 can enable calibrated likelihoods for supported method/object/conditions only.
- [ ] 3.6 Update existing responder controls and labels to show search time, output time, evidence status and conditional ranking.
  Retain responder authority and never label the top cell the exact rescue location or an optimal full search plan.

### 🧪 Verification Gate

- [ ] Backend: `python -m pytest -q tests/test_search.py tests/test_drift_api.py tests/test_phase4_validation.py`, then full pytest and Ruff.
- [ ] Disposable database: restart, rerun, migration and duplicate/concurrent-report tests with actual persistence; record exact command.
- [ ] Repository root: `node --test web/test/*.test.js`; `node --check web/js/dashboard/dashboard-sar.js` and every additional changed JavaScript file.
- [ ] Confirm S1's 1/6 and 5/6 analytical oracle through the real route after restart, not just in the helper.

### 🔍 Review Gate (Ponytail)

- [ ] One real posterior calculation and one serialized run state; any surviving static updater is explicitly demo-only or required compatibility.
- [ ] No recomputation on GET, hidden second weight store, unused new options, or trajectory reconstruction from an average.

### 📦 Git Checkpoint

Stage only reviewed Phase 3 backend/web/tests/contracts/migration and plan paths.
Commit: `fix(search): assimilate time-aligned negative evidence`.

### 🛑 HARD STOP

Report S1-S7 red/green evidence, unassimilated legacy/POD limitations and commit hash.
Wait for user confirmation before Phase 4 under the implementation-plan skill's phase-stop rule.

## Phase 4: Establish calibration and replay that cannot manufacture accuracy

**Goal:** Correct claim gates and evaluation logic before training on local measurements, and make the during-stage inputs testable in the full scenario.

### Tests to write and run first

Extend existing squall/profile/evaluation tests and `test_phase5_validation.py` with actual route/service cases.
Add one small manifest/replay test module if required; a manifest validator should use the standard library and existing storage conventions.

| ID | RED scenario | Required assertion |
| --- | --- | --- |
| C1 | Synthetic/unvalidated bundle plus return-now environment flag; wrong-version or missing evaluation metadata | Live detector cannot promote itself to an operational calibrated return instruction; explicit human advisories continue independently. |
| C2 | Rule score exceeds classifier score; evaluate and serve the same examples | Metrics and threshold selection use the actual composed runtime decision; report classifier probability and pattern score with distinct meanings. |
| C3 | Same storm/trip/track split into multiple windows across partitions; held-out data offered to fit/calibration; future/late records injected | Entire events stay disjoint; held-out records cannot influence fit, thresholds, feature choices or historical decisions. |
| C4 | Manifest has example hashes, missing raw evidence, invented provenance, drill mixed into natural incidents, empty or one-class target set | Verification rejects unverifiable files or reports insufficient evidence; never “100% accuracy,” zero false alarms, or passed field validation from an empty sample. |
| C5 | Registered open trip with no contact; return deadline missed during shared outage; no data for baseline | Candidate remains visible, expected return obligation remains, current welfare unknown; missing contacts do not mean normal or safe. |
| C6 | Trip-state query fails; later return amendment applied to old decision; prior abnormal/unfinished trip enters normal baseline | Explicit unavailable state, receipt-aware historical state and only known-completed normal history; no silent 12-hour fallback or future amendment leakage. |
| C7 | Model failure injected into an actual case-open/rerun API and SOS request | Database case/evidence and manual delivery survive; test cannot pass by catching arbitrary exceptions around an untouched local dictionary. |
| C8 | Controlled two-track/prediction example with known containment, area, direction error and miss; unsupported horizons | Metrics match manual arithmetic, include failures/abstentions and do not report unsupported horizons as successes; baseline uses independent physical assumptions. |

### Tasks after each relevant RED result

- [ ] 4.1 Reconcile docs 45, 49, 50, 51 and 52 and the relevant completion statements in README/status with actual evidence.
  Keep old measurement claims only if raw records, method and provenance can be produced; otherwise mark them proposed/unmeasured and explain the correction.
  Explicitly distinguish a calibration protocol, calibrated instrument, calibrated probability, and externally validated model.
  Resolve the 20/30-minute lead and 111/15-km support disagreements as open decisions; this plan supplies no invented numeric answer.
- [ ] 4.2 After C1/C2 fail, gate live squall promotion on the specific supported artifact/evaluation/domain rather than an environment flag alone.
  Leave it in research/watch mode until empirical acceptance is met.
  Evaluate the exact decision function, thresholds, geometry and alert timing used by the active API; retain synthetic results in their own stratum.
- [ ] 4.3 After C3/C4 fail, establish one event-level manifest with raw-file checksums, provenance class, instrument/calibration references, occurrence/receipt times, independent outcome, exclusions and frozen split.
  Example manifests are fixtures only; no placeholder hash or invented custodian becomes evidence of collection.
  Use existing evaluators with explicit dataset/split selection; prevent writing field results into synthetic demo artifacts or operational case tables.
- [ ] 4.4 Define the weather target from independently measured local wind/gust onset and location/horizon.
  If a convective-squall diagnosis is claimed, specify independent adjudication; otherwise narrow to wind-event prediction.
  Do not require the same pressure-drop feature as a condition of the label or sample only detector-triggered windows.
  Record non-event periods as well as events, and declare every threshold/duration/unit before holdout inspection.
- [ ] 4.5 After C5/C6 fail, include explicit no-contact open trips and preserve agreed return obligations under outage.
  Missing personal history produces low-confidence/unknown expectations rather than fabricated personal normality.
  Preserve confirmed return and self-reported welfare as distinct time-qualified evidence.
  Weather may be shown as location/time-qualified context if available; do not add a weather weight or distress model without an independently defined target and benefit evidence.
- [ ] 4.6 After C7/C8 fail, replace hollow success checks with real request/persistence regressions and independently computed metric fixtures.
  No broad exception catch around the test stimulus; fail on the wrong exception and assert the expected stored state.
  Preserve synthetic evaluation as numerical/software evidence, not field containment.
- [ ] 4.7 Prepare executable training/calibration/evaluation commands on a dedicated dataset, each behind its previously written tests.
  Do not retrain on fabricated field data if collection has not occurred.
  Record baseline, data IDs, split, selected hyperparameters, code/artifact version and exact invocation; freeze candidate before Phase 5 evaluation.

### 🧪 Verification Gate

- [ ] Backend: `python -m pytest -q tests/test_squall.py tests/test_squall_eval.py tests/test_trip_profile.py tests/test_trip_profile_eval.py tests/test_anomaly_source.py tests/test_vessel_trips.py tests/test_phase5_validation.py`, plus the manifest/replay tests if added.
- [ ] Full backend pytest and Ruff; mobile/web suites for any touched consumers.
- [ ] Show an illustrative manifest accepted, a leaking/unverifiable manifest rejected, and empty real data reported as insufficient, with fixtures visibly marked synthetic.
- [ ] Show no claim of field accuracy and no automatic model promotion until the independent evidence gate passes.

### 🔍 Review Gate (Ponytail)

- [ ] Existing loaders/evaluators extended rather than a second ML platform; no speculative feature or model added to match a circular label.
- [ ] No nominal passing test that merely asserts a literal dictionary, imports a symbol or searches source strings.

### 📦 Git Checkpoint

Stage the exact Phase 4 data-contract, evaluator, model/service, tests, claim-correction and plan paths reviewed.
Commit: `fix(ai): verify calibration lineage and historical decisions`.

### 🛑 HARD STOP

Report C1-C8 red/green evidence, available/absent physical datasets, frozen protocols and commit hash.
Wait for explicit Phase 5 authorization and actual field arrangements under the implementation-plan skill's phase-stop rule.

## Phase 5: Collect real measurements and run controlled drills

**Goal:** Determine the actual operating domain and measured performance of the complete before/during/after workflow.

### Tests and acceptance protocol to write before collection or new code

Freeze the measurement protocol, outcome definitions, analysis code checks, split rules and decision criteria before looking at held-out results.
The following tests are physical acceptance procedures backed by the software checks already written.
They are not claims that a natural squall or a rescue event can safely be recreated on demand.

| ID | Controlled procedure or independently observed event | Evidence and success decision |
| --- | --- | --- |
| F1 | Collocate each instrument with an independently calibrated reference; record clock error, mounting, depth, axes, units and missing intervals | Measured bias/uncertainty and dynamic response for pressure, wind and current; qualification only within observed limits; raw IMU motion is not calibrated significant wave height. |
| F2 | Phone in airplane mode, WiFi enabled, real gateway/relay/buoy; stationary, passing, app background/resume, reboot, first-frame loss and uplink outage | Raw issue/send/cache/phone/display/ack times and receipt rates with denominators; empirical WiFi opportunity, blind intervals and failed deliveries; published warning still respects expiry and source. |
| F3 | Record naturally occurring independent weather onsets and matched non-event periods prospectively | Detection precision/recall, false alerts per vessel-hour/day, abstention and location/horizon skill; model creation lead and actual displayed lead reported separately. |
| F4 | Consented normal trips and rehearsed missed-contact/late-return/no-contact/shared-outage cases with independent safety communications | Confirmed return versus self-reported safe versus unresolved; missed-deadline detection, false review workload and latency; drills never become confirmed-distress training labels. |
| F5 | Recoverable surrogate/drifter with independent GNSS logger, measured object state/draft/leeway and a supervised recovery plan | Track separation/direction error, nominal 50/75/95% containment versus searched area, coast grounding and unsupported-mass rates at prespecified supported horizons; no person intentionally set adrift. |
| F6 | Blinded search trials on recoverable targets across method, object, spacing, daylight and visibility categories | Actual searched track and footprint, detections and non-detections, conditional POD with uncertainty and repeat dependence; report unrepresented categories as unknown. |
| F7 | Integrated storyline and benign/degraded alternatives, using independent time-stamped truth | Before warning received or missed honestly; during unresolved trip retained; after responder confirms case, conditional drift and time-correct search update; manual SOS works despite AI failure. |
| F8 | Frozen model/parameter candidate evaluated once on untouched events and then prospectively in shadow operation | Compare prespecified baseline, calibration, accuracy, workload, coverage and delivery criteria with uncertainty; insufficient evidence or failed criteria leave the claim unqualified. |

### Tasks and evidence sequence

- [ ] 5.1 Inventory the instruments, data licenses/access, trained operators, local coordinators, safe operating conditions and budget actually available.
  Treat named sites, ADCP/GNSS specifications, institutional approvals, radio channels and numerical ranges in previous protocols as proposals until confirmed.
  Do not purchase, contact third parties, organize field deployments or publish warnings without applicable authorization.
- [ ] 5.2 Before collecting evaluation data, record the operating area, object/vessel classes, seasonal/sea-state coverage and independent event definitions.
  A local expert and responsible responder must determine actionable response time, acceptable false-alert workload, desired containment/area tradeoff and measurement tolerances.
  Choose event counts/stopping criteria from the required uncertainty and realistic event rates, not arbitrary “three drills prove accuracy” targets.
  If no decision criterion is agreed, report descriptive results only and leave operational qualification open.
- [ ] 5.3 Conduct F1/F2 commissioning and communication measurements under the authorized field plan.
  Timestamp acquisition and arrival separately and preserve raw logs with checksum, instrument ID and calibration record.
  Archive rejected/missing samples and reasons as well as successful samples.
- [ ] 5.4 Conduct F3/F4 observational and safe scenario collection.
  Never recreate dangerous weather or distress involving people; controlled drills test the workflow while real natural observations establish weather skill.
  Never use a protocol table, synthetic event, or an assumed WiFi radius as field data.
- [ ] 5.5 Conduct F5/F6 with supervised recoverable objects and independent truth custody.
  Quantify object-specific leeway/current bias using development tracks only; represent tide/current shear/wave-induced motion if measurements show material residual errors at the same target.
  Use bathymetry, shoreline, tide and wave/Stokes information only with their actual physical meaning and adequate scale; tide height is not horizontal current.
  A calm-water surrogate trial cannot validate storm seas or all object classes.
- [ ] 5.6 Train/tune on development data, calibrate on the separate calibration split and freeze all model/threshold/POD/geometry settings before F8.
  If any analysis or training code needs correction, write its failing test first and rerun software gates before using its results.
  Event-level confidence intervals must respect correlated samples from one storm/track/trip; repeated time samples are not independent field events.
- [ ] 5.7 Execute F7/F8 with a complete case log and every failure/abstention included in the denominator.
  Reused holdout data become development data after tuning; collect a new untouched evaluation cohort rather than repeatedly tuning to the test set.
  Compare with prespecified simple baselines: transparent weather thresholds, explicit trip deadlines, independent drift-envelope/constant-forcing scenarios and prior-only search ranking.
- [ ] 5.8 Measure delivered lead as hazard onset minus handset display time; separately report receipt lead and acknowledgement time.
  Missing receipt/display is a failed delivery or unobserved outcome, not an excluded successful warning.
  Compare the measured lead distribution to the agreed action requirement including actual communication opportunity.
  If blind intervals exceed useful warning lead, narrow the stationary-buoy delivery domain and prepare a separate carried-radio/hardware decision; no model can send information through an absent link.
- [ ] 5.9 Publish a versioned evidence-backed claim table with dataset IDs, source provenance, supported geography/horizon/object/conditions, uncertainty, measured performance and remaining exclusions.
  Field evidence can support predictive usefulness and calibration; do not infer a causal reduction in casualties from drill success or correlation.
  Leave unknown mechanisms and unobserved deployment conditions explicitly unknown.

### Minimum required evidence by claimed outcome

| Outcome | Already available | Must be qualified or collected | Honest state if absent |
| --- | --- | --- | --- |
| Warning delivered to fisherman | Gateway/buoy/client code and advisory records | Working active consumer, authenticated event chain, actual contact opportunity and observed display | Cached/research advisory; delivery unconfirmed outside observed contact |
| Local weather early warning | Pressure detector and forecast inputs | Local independent wind/event labels, pre-decision features, seasonal holdout, actual delivered lead | Research pressure signal and explicit forecast/official advisory |
| Missed return/contact review | Trip/contact tables and expected-return fields | Agreed expectation, actual normal-trip history, communication context, independent return/welfare outcome | Unresolved/unknown review state; no safety/distress probability |
| Drift search distribution | Particle simulator, current ingestion, wind fetch | Actual fix/drift datum, qualified depth/time/space forcing, shoreline, object parameters and independent tracks | Conditional research simulation or environmental insufficiency |
| Time-aligned posterior | Existing trajectory helper and search tables | Persisted trajectory/time/footprint semantics, measured method/object POD, calibrated prior | Time-qualified hypothetical update or report recorded without assimilation |

### Evaluation measures to freeze before holdout inspection

| Component | Required measurements | Decision rule |
| --- | --- | --- |
| Weather and warning | Event precision/recall, false alerts per exposure hour, missed events, abstention, probability reliability/Brier score only for a probability target, delivered/displayed lead and successful receipt denominator | Improvement against the agreed simple threshold baseline at the same target/horizon; uncertainty and measured delivery meet the locally agreed action criterion. |
| Trip review | False reviews per trip, missed return obligations, delay to review, unresolved/no-contact coverage and calibration of contact timing where probabilities exist | Improve the explicit deadline baseline without erasing unresolved trips; no conversion to distress accuracy without real independent distress/non-distress labels. |
| Drift | Error versus horizon, nominal contour containment with event-level uncertainty, contour area at comparable containment, grounded/outside/unsupported mass and abstention | Meet prespecified containment/area goals on independent object tracks in the qualified domain; a larger contour alone does not establish better accuracy. |
| Search | Detection rates by complete search operation, conditional method/object/visibility POD uncertainty, prior calibration and posterior predictive performance on independently observed target positions | Support a quantitative likelihood only for represented strata; otherwise retain hypothetical/unknown status and preserve all reports. |

Sensor offset/gain/timing calibration, probability calibration and field validation are distinct activities with separate records.
If the held-out sample is too small for the agreed precision or lacks relevant conditions, the result is insufficient evidence even when point estimates look good.

### 🧪 Verification Gate

- [ ] Record F1-F8 procedures, raw evidence references, actual outcomes and prespecified acceptance comparison.
- [ ] Run full affected backend/mobile/web/firmware regression gates and the exact frozen evaluation command for each dataset/artifact.
  Record tool versions, configuration, code revision and artifact/data hashes.
- [ ] Field scorecards report uncertainty, unsupported conditions, failures, missingness and non-events, not just successful examples.
- [ ] If equipment, funding, independent events, raw evidence or agreed criteria are absent, Phase 5 remains incomplete with a concrete blocker and collection handoff.
  A protocol written or software suite passed is never sufficient to check off this phase.

### 🔍 Review Gate (Ponytail)

- [ ] Every new physical input addresses a measured error or required claim; no shopping list of theoretically correlated features.
- [ ] One evidence manifest and versioned evaluation workflow; retain physical calibration controls and diagnostic information that field evidence requires.

### 📦 Git Checkpoint

After the acceptance evidence passes, stage the reviewed plan, claim documents, anonymized/consented evidence manifests and required model/evaluation artifacts according to repository data rules.
Do not commit raw personal locations, credentials, unconsented records or unrelated working changes.
Commit: `docs(ai): record independent field evidence and supported claims`.
If only preparation is done, a checkpoint must say preparation and must leave Phase 5 unchecked; never use the completion message for uncollected evidence.

### 🛑 HARD STOP

Report the complete software/bench/field/holdout evidence separately and list claims still unqualified.
Return the work for user review; no automatic operational activation or deployment follows.
The implementation-plan skill requires an explicit phase-end stop, and safety-critical translation review follows `mobile/lib/l10n/README.md` before real user use.

## Finding-to-phase traceability

| Scope / finding | Phase | Required closure evidence |
| --- | --- | --- |
| Offline delivery SQUALL-04/06 and newly verified date/relay/rebroadcast gaps | 1, 5 | W1-W10 plus F2/F7; receipt state alone never substitutes for observed display |
| Synthetic calibration SQUALL-05 and original SQUALL-01/02 | 4, 5 | C1-C4 plus F3/F8; no label constructed from the same detector pressure threshold |
| Drift qualification/support DRIFT-05/06/07/08/09/10/11 | 2, 5 | D1-D8 plus F1/F5/F8; correct decision cutoff, actual fix time, shoreline versus open boundary |
| Original DRIFT-03 wind validity and DRIFT-04 synthetic containment limitations | 2, 4, 5 | D6, C8 and independent F5/F8; no current forecast clamping across missing historic/future support |
| Time-aligned search SEARCH-03/04 and original SEARCH-01/02 | 3, 5 | S1-S7 plus F6/F8; correct weighted terminal mass through persistence |
| Trip support for full scenario TRIP-04/06 and original TRIP-02 | 4, 5 | C5-C7 plus F4/F7; explicit no-contact state, normal baseline and historical amendments |
| TRIP-05 weather context | 4, conditional | No invented live-weather explanation; optional matched context, new score weight requires independent benefit evidence |
| Unsupported completion/measurement claims in docs 45/49/50/51/52 | 4, 5 | Corrections distinguish proposed values from measurements; eventual claims link raw evidence |
| HAZARD/WINDOW/CATCH and unrelated Ponytail deletions | Separate workstream | No closure claimed by this plan; reverify reports before planning further work |

## Gemini phase-end response format

Provide completed task/test IDs, the smallest meaningful before/after example, exact red and green evidence, changed paths, actual checks and failures, physical evidence still missing, and the phase commit hash.
Then ask for confirmation for the next phase and cite the skill's required stop.
Do not claim “all findings resolved” from helper tests, status prose, or a count of passing tests.

## Planning verification record

- Source, contracts, existing tests and both audits were inspected; two independent council reviewers supplied devil's-advocate and reliability critiques, with architecture and simplicity synthesis performed locally.
- No production code, tests, migrations, firmware, model artifacts, datasets, branches or commits were changed in this planning session.
- Application tests and field evaluations were not executed for this documentation-only deliverable; all execution evidence is pending.
- Document structure, task-to-test mapping, referenced existing test paths and whitespace were checked during planning.
- The existing root plan is preserved with an active-handoff pointer; the September 15 re-audit remains unchanged as historical context, including corrections identified above.
