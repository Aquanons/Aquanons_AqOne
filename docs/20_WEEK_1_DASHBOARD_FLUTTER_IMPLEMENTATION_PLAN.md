# AqOne Week 1: Dashboard and Flutter Implementation Plan

**Sprint window:** 17-23 August 2026
**Primary outcome:** a phone can save an SOS locally, hand it to the buoy over Wi-Fi, display an honest delivery state, and make the same SOS visible and actionable on the dashboard.

This file is the execution contract for the coding agent. It is not a statement that the described behavior already works.

## Scope

### In scope

- Flutter-to-buoy HTTP and WebSocket contract repair.
- Flutter outbox, delivery-state, buoy-status, and responder-ETA behavior.
- Dashboard live-feed honesty, incident handling, stale/error states, and safe rendering.
- Small backend/API changes required to support these two clients safely.
- Automated contract, unit, widget, and browser-JavaScript tests.
- Documentation and commit discipline.

### Explicitly out of scope

- LoRa relay, gateway implementation, radio firmware, TinyML, new AI models, PostGIS migration, full visual redesign, family portal, and secure OTA.
- Treating mock, generated, or hardcoded records as live telemetry.
- Editing the user-supplied `artifacts/competitions/technical-profile/AqOne_Technical_Profile_Aquanons-1.docx`.

## Hard reset: rules that override every task

1. **Inspect before changing.** At the start of every phase, read `AGENTS.md`, run `git status --short`, inspect the relevant source files, and compare the plan against the actual code. Do not assume a route, model field, endpoint, or test already exists.
2. **Do not guess.** If code, firmware, README, or API behavior conflicts with this plan, stop the phase. Mark it `BLOCKED` in the status table with exact file/line evidence and continue only with work that is independent of the conflict.
3. **One source of truth.** Canonical Wi-Fi endpoint, WebSocket endpoint, JSON field names/types, delivery states, and error messages must be documented and covered by fixtures/tests. Do not maintain parallel incompatible contracts.
4. **No fake operational state.** Demo and synthetic data must be visibly labelled. A failed refresh must show a stale/degraded state; it must never keep a permanent `LIVE` label.
5. **No invented test result.** Run every listed check. If a tool, dependency, hardware, or environment is unavailable, record the exact command and blocker; never report it as passing.
6. **No secret handling shortcuts.** Do not add credentials, API keys, Wi-Fi passwords, tokens, or personal data to source, fixtures, screenshots, commits, or documentation. Report existing exposed secrets rather than copying them.
7. **Preserve user work.** Never use `git reset --hard`, `git checkout --`, force-push, or `git add -A`. Do not stage the untracked technical-profile DOCX or any unrelated change.
8. **Keep scope small.** Do not refactor unrelated dashboard UI, introduce a framework, or start LoRa/ML work during this sprint without written user approval.
9. **Update this plan after every phase.** Set the phase status, record exact tests/evidence, blockers, and the commit hash in the status table before committing the phase.
10. **Commit meaningful checkpoints.** Each completed phase is one focused commit. Stage only the files belonging to that phase, review `git diff --staged`, run its required tests, then commit with the format `feat(week1): <phase outcome>` or `fix(week1): <phase outcome>`.

## Canonical contract decision for this sprint

The checked-in firmware currently serves its Wi-Fi access point at `http://192.168.4.1`, and its WebSocket service listens on port `81`. Flutter currently disagrees. The intended Week 1 contract is:

| Concern | Canonical value |
|---|---|
| Buoy HTTP base URL | `http://192.168.4.1` |
| Buoy WebSocket URL | `ws://192.168.4.1:81` |
| SOS handoff | `POST /v1/sos` |
| Buoy status | `GET /v1/status` |
| Offline responder status | `GET /v1/sos/status?vessel_id=<id>` |

Before applying this decision, verify the firmware still uses these values. If it does not, document the discrepancy and stop rather than silently changing both clients.

## Phase 0 - Baseline and contract fixtures

### Work

1. Inspect `mobile/lib/core/config.dart`, `mobile/lib/services/buoy_client.dart`, `mobile/lib/models/buoy_contact.dart`, `mobile/lib/ui/chathubb.dart`, `firmware/buoy/AqOneBuoy/AqOneBuoy.ino`, `web/js/dashboard.js`, and the SOS API routes.
2. Create one concise contract document or fixture set covering the real JSON returned by:
   - `POST /v1/sos`
   - `GET /v1/status`
   - `GET /v1/sos/status`
   - dashboard `GET /api/sos/active`
3. Add non-sensitive JSON fixtures for accepted SOS, full queue, buoy offline, no ETA, and acknowledged ETA.
4. Establish the baseline commands and write their actual result below.

### Required checks

```text
cd backend && pytest -q
cd backend && ruff check .
cd mobile && flutter analyze
cd mobile && flutter test
node --check web/js/dashboard.js
```

### Commit

`docs(week1): add dashboard and Flutter contract fixtures`

## Phase 1 - Flutter buoy contract and delivery states

### Work

1. Set one configurable buoy HTTP/WebSocket endpoint using the verified canonical contract.
2. Update Android cleartext configuration only for the chosen local buoy endpoint; do not weaken transport settings globally.
3. Make `BuoyStatus` and `BuoyAck` parse the actual firmware response types, including the string buoy identifier and queue/uplink fields.
4. Repair chat WebSocket host/port/path only after verifying the firmware endpoint.
5. Add graceful buoy errors: unreachable, queue full, invalid response, and no shore link.
6. Preserve the outbox before any network attempt. Delivery state must advance only on confirmed evidence.
7. Add unit/widget tests using Phase 0 fixtures.

### Required checks

```text
cd mobile && flutter analyze
cd mobile && flutter test
```

### Commit

`fix(week1): align Flutter with buoy contract`

## Phase 2 - Offline acknowledgement and ETA

### Work

1. Add a `BuoyClient` method for `GET /v1/sos/status?vessel_id=<id>`.
2. When the cloud is unreachable, reconcile pending SOS records through the buoy endpoint instead of giving up.
3. Parse responder acknowledgement, ETA, responder status, and notes without reducing an already confirmed delivery state.
4. Clearly distinguish these messages in the UI:
   - "Saved on this phone"
   - "Held by buoy"
   - "Reached shore"
   - "MDRRMO has responded"
5. Add tests for cloud unavailable + buoy ETA, no events, malformed buoy response, and delayed ETA.

### Required checks

```text
cd mobile && flutter analyze
cd mobile && flutter test
```

### Commit

`feat(week1): return responder ETA through buoy`

## Phase 3 - Dashboard operational honesty and safety

### Work

1. Replace the unconditional `LIVE` presentation with one driven by the most recent successful SOS refresh.
2. Display `Live`, `Stale`, `Offline`, or `Demo data` only when supported by actual state.
3. Show the last successful refresh time and a visible failure state.
4. Ensure sample buoy/vessel/incidents cannot be mistaken for live records. Keep them in a clearly labelled demo mode or remove them from the operational view.
5. Escape all server-provided text before rendering it into HTML, tooltips, or popups.
6. Keep the current polling approach unless a tested backend streaming endpoint exists; do not claim SSE.
7. Extract pure JavaScript helpers for escaping text and classifying feed freshness into a testable module.
8. Add Node tests for escaping, fresh/stale/offline transitions, and synthetic/demo badges.

### Required checks

```text
node --check web/js/dashboard.js
node --test web/test/dashboard-utils.test.js
cd backend && pytest -q
cd backend && ruff check .
```

### Commit

`fix(week1): make dashboard incident state honest and safe`

## Phase 4 - Minimal API safety and release evidence

### Work

1. Validate public SOS text lengths and reject invalid payloads safely.
2. Ensure only authorized roles can acknowledge, resolve, or publish advisories; do not change the unauthenticated SOS intake without a documented emergency-access design.
3. Add backend tests for authorization, length validation, and escaped dashboard input fixtures.
4. Update the root README and demo/status document only for behavior actually verified this week.
5. Build a fresh APK only after all Flutter tests pass. Record version, checksum, build command, and installation test result in this plan.

### Required checks

```text
cd backend && pytest -q
cd backend && ruff check .
cd mobile && flutter analyze
cd mobile && flutter test
node --check web/js/dashboard.js
node --test web/test/dashboard-utils.test.js
```

### Commit

`feat(week1): verify dashboard and Flutter release slice`

## Definition of done

Week 1 is complete only when all statements below are demonstrated and recorded:

- [ ] Flutter and firmware use one verified Wi-Fi/JSON contract. — code fixed and matches the firmware source (docs/21); **not verified by `flutter analyze`/`flutter test`**, no Flutter SDK was available in this environment.
- [ ] A local SOS is persisted before network calls. — confirmed by reading `sos_service.dart` (`_outbox.insert()` before `_attemptRelay()`); not exercised by a running test.
- [ ] Flutter correctly handles buoy accepted, full, unreachable, and no-uplink cases. — covered by `mobile/test/buoy_client_test.dart`; tests are written and manually reviewed, **not run**.
- [ ] An offline handset can receive a responder ETA through the buoy endpoint. — implemented (`BuoyClient.sosStatus`, `SosService.reconcile` buoy fallback) and covered by tests; **not run**.
- [x] Dashboard incident state shows freshness/error truthfully and escapes user-provided text. — genuinely demonstrated: `node --test web/test/dashboard-utils.test.js` passes 21/21 for real in this environment, covering escaping and the live/stale/offline transitions.
- [ ] Demo/synthetic data is visibly identified. — `DEMO` badge and "(simulated)" buoy-popup labels implemented and the badge logic is unit-tested; full visual confirmation in an actual browser was not done (no browser available here).
- [ ] Authorization and input-validation tests pass. — written (`test_auth.py`, `test_sos_ingest.py`), `ruff`-clean and `py_compile`-clean; **`pytest` cannot run** in this sandbox (Python 3.10, backend requires 3.11+), so they have not actually executed.
- [x] Flutter, backend, and dashboard checks have recorded results. — every required command was either run for real or recorded as blocked with the exact reason, every phase, per Hard Reset rule 5. Recorded ≠ passing - see the individual boxes above for which actually ran.
- [ ] A fresh APK is built and installed on a physical Android device. — **not done**. No Flutter/Android toolchain is available in this environment. `mobile/AqOne.apk` is unchanged from before this sprint (sha256 `3e08365bda94eedfb765ff71f7205cefabffe4fd21b00aa7add3eb6ceebe5ccb`, unmodified).
- [x] This plan, README, and status documentation match the demonstrated behavior. — README's new "Week 1 dashboard/Flutter contract sprint" section and this table both distinguish verified-by-running-a-check from implemented-but-unverified; neither overclaims.

## Phase status and evidence log

The coding agent must update this table after completing or blocking every phase, then include this file in that phase's commit.

| Phase | Status | Evidence / exact test result | Commit |
|---|---|---|---|
| Phase 0 - Baseline and contract fixtures | DONE (checks partially blocked by sandbox environment) | Contract doc `docs/21_WEEK1_CONTRACT_FIXTURES.md` + fixtures in `fixtures/week1_contract/` added, ground-truthed against firmware/backend source, not docs. Canonical contract (192.168.4.1, ws port 81, /v1/sos, /v1/status, /v1/sos/status) confirmed correct against firmware. Found: config.dart buoyBaseUrl wrong (10.0.0.1 vs 192.168.4.1), chathubb.dart WS URL wrong (missing :81, wrong path), BuoyStatus/BuoyAck field mismatches (buoy_id is a string not int; status uses queue_depth not queued; no batt/mesh fields exist), docs/03 stale, dashboard LIVE badge is static markup with no stale/offline state, XSS gap in alert `desc` rendering, hardcoded WiFi password in firmware source (`Sams21_Hotel` / reported not reproduced further). Checks: `node --check web/js/dashboard.js` PASS. `cd backend && ruff check .` PASS except 1 finding (`app/api/metrics.py:31` W292 missing trailing newline, not fixed this phase - out of Phase 0 work list). `cd backend && pytest -q` BLOCKED - sandbox Python is 3.10.12, `requirements.txt` numpy==2.4.6 needs >=3.11; minimal install collects but fails on `datetime.UTC` (3.11+) in `app/api/advisories.py` and `tests/test_trip_profile.py`, 15 collection errors, 0 tests run. `cd mobile && flutter analyze` / `flutter test` BLOCKED - no Flutter SDK present in this sandbox. | `8133add3888824d17581ba4a0ece22b5aa91a574` |
| Phase 1 - Flutter buoy contract and delivery states | DONE (checks BLOCKED - no Dart/Flutter toolchain in this sandbox, code reviewed manually instead) | Set `AqOneConfig.buoyBaseUrl` to `http://192.168.4.1` (was `10.0.0.1`) and added `AqOneConfig.buoyWsUrl(host)` as the one source of truth for the buoy WS URL; `network_security_config.xml` cleartext exception moved from `10.0.0.1` to `192.168.4.1` (was permitting cleartext for a host the app never talks to while blocking the real one). `chathubb.dart` now connects to `ws://192.168.4.1:81` via `AqOneConfig.buoyWsUrl` instead of `ws://192.168.4.1/ws` (wrong port, wrong path - firmware's chat WS has no path routing). `BuoyStatus`/`BuoyAck.buoyId` changed `int`→`String` to match the firmware's string `BUOY_ID`; `BuoyStatus` now parses `uplink`/`queue_depth`/`clients` (the fields the firmware actually sends) instead of the fictional `batt`/`mesh`/`queued`; `BuoyAck.srcId` removed (firmware's `POST /v1/sos` response has no such field). Propagated the `buoyId` type change through `SosRecord`, `OutboxStore.advance()`, `app_database.dart` (schema v5→v6, `buoy_id` column `INTEGER`→`TEXT`, no data migration needed since SQLite already stores TEXT fine in that column) and the two UI widgets that render it. `BuoyStatusCard` rewritten to show the firmware's real `uplink` state with the buoy's own captive-portal wording, and to never show a battery percentage (the firmware sends none). Added `BuoyInvalidResponse` to `buoy_client.dart`, distinct from `BuoyUnreachable`, for a buoy that answers with malformed/truncated JSON (the firmware's 320-byte response cache can truncate an ETA reply mid-JSON) instead of misreporting it as "no buoy nearby." Outbox-before-network-attempt and forward-only delivery-state merge were already correct in `sos_service.dart`/`outbox_store.dart` - verified, not changed. New `mobile/test/buoy_client_test.dart` exercises `handoff()`/`status()` against `fixtures/week1_contract/accepted_sos.json` and `queue_full.json` plus a simulated unreachable buoy and a simulated truncated response. Updated `mobile/test/widget_test.dart` and `mobile/test/sos_record_test.dart` for the new field shapes. Checks: `cd mobile && flutter analyze` / `flutter test` BLOCKED - no Flutter or Dart SDK installed in this sandbox (confirmed via `which flutter`/`which dart`, both empty). All edited/created `.dart` files were instead read back in full and manually checked for syntax/type consistency (matching constructor params, consistent `buoyId` typing end-to-end, no remaining references to the removed `MeshHealth`/`srcId`/`battery` symbols - verified by grep). This is not a substitute for `flutter analyze`/`flutter test` and both must be run on a machine with the Flutter SDK before this phase is trusted. | `pending` |
| Phase 2 - Offline acknowledgement and ETA | DONE (checks BLOCKED - no Dart/Flutter toolchain in this sandbox, code reviewed manually instead) | Added `BuoyClient.sosStatus(vesselId)` for `GET /v1/sos/status?vessel_id=<id>`, reusing `RemoteSos.fromJson` from `backend_client.dart` rather than a second parser, since the firmware proxies `GET /api/sos/vessel/{id}` verbatim (docs/21). `SosService.reconcile()` now checks `_backend.isReachable()` once per tick and, when the cloud is down, calls `_buoy.sosStatus(vesselId)` per pending vessel instead of returning immediately as it did before; matching/merge logic was extracted into `_applyRemote()` and is shared by both sources so behavior cannot drift between them. A buoy failure (unreachable/rejected/invalid JSON) for one vessel is caught and skipped per-vessel so it cannot block reconciliation for other vessels in the same tick. Delivery-state advancement continues to go through `OutboxStore.advance()`'s forward-only merge, so neither source can regress an already-confirmed state. Verified the plan's four required distinct UI messages ("saved on this phone" / "held by buoy" / "reached shore" / "MDRRMO has responded") are already satisfied by `DeliveryState`'s existing `title`/`description` pairs, which are the docs/06_DELIVERY_STATES.md canonical copy - deliberately did not add a second, possibly-conflicting set of labels elsewhere (rule 3, one source of truth). New tests in `mobile/test/buoy_client_test.dart` (`BuoyClient.sosStatus` group) cover the plan's four required scenarios: buoy ETA (`eta_acknowledged.json`), no events (`no_eta.json`), a body truncated by the firmware's real 320-byte cache limit, and a delayed responder status (5) carried through intact for the countdown UI. Manual review caught and fixed a real bug before commit: `reconcile()` initially called `_applyRemote()` without `await` (a `Future<bool>` used directly in an `if`), which `flutter analyze` would have caught instantly - recorded here precisely because the toolchain that should have caught it is unavailable in this sandbox. Checks: `cd mobile && flutter analyze` / `flutter test` BLOCKED - no Flutter/Dart SDK in this sandbox (same blocker as Phase 1). Every touched file was read back in full after editing and checked by hand for type/control-flow consistency; this is not a substitute for the real checks. | `418651aba1e954044fe25f32c76541af9364826e` |
| Phase 3 - Dashboard operational honesty and safety | DONE (checks ran for real - Node is available in this sandbox) | New `web/js/dashboard-utils.js`: UMD module (`window.AqOneDashboardUtils` in-browser, `module.exports` under Node, matching the existing `window.AqOneDangerZonePredictor` convention) exporting `escapeHtml`, `classifyFreshness`, `freshnessLabel`, `alertBadge`. `escapeHtml` is pure string replacement (not the DOM-textNode trick the existing `_escHtml` used), so it runs identically in the browser and under `node --test` with no DOM shim; `_escHtml`'s ~15 existing call sites now delegate to it rather than duplicating logic. Header `LIVE` badge (`web/html/dashboard.html` `#sync-text`) and the banner's "Last updated" text are now both driven by `updateSyncStatus()` off one real timestamp (`lastSosSuccessMs`, set only when `/api/sos/active` actually succeeds), ticking every second so STALE/OFFLINE appears promptly; removed a second, independent 30s counter that had been faking the "Last updated" text regardless of whether any poll had succeeded. Added `.is-stale`/`.is-offline` CSS states (amber/red) so a degraded feed looks different, not just reads different words in the same green pill. Fixed real unescaped-HTML-injection points found in Phase 0: `liveAlertFromEvent`'s `desc` (server `boat`/`note`) and `stage` (server `buoy_id` via `deliveryPath`) rendered into `renderAlerts()`'s `innerHTML`; the same `desc` also fed a Leaflet `bindTooltip()`, which renders as HTML, not text; and `showToast()`'s `title`/`msg`, reachable with server text from the new-SOS toast in `loadActiveSos()`. Confirmed `openIncidentDrawer()` was already safe (uses `.textContent` throughout, verified by reading it in full - not assumed). Added a `DEMO` badge (mirroring the existing `LIVE` badge, both now driven by the shared `alertBadge()` function) on the hardcoded `alertData` rows so a scripted sample incident cannot be mistaken for one from `/api/sos/active`; added "(simulated)" to buoy popup battery/signal readings, since `initialBuoys`' battery/pressure/signal values are fixed sample data, not live telemetry from any deployed hardware, and presenting them bare would be exactly the fake operational state Hard Reset rule 4 bans. Did not touch the Buoy Health Monitor drawer, shore-station markers, or other non-incident panels beyond that - kept to the plan's explicit scope (live/demo incident distinction and text escaping) rather than a wider redesign (rule 8). Kept polling (`LIVE_SOS_POLL_MS = 3000`); did not introduce or claim SSE. Checks - all run for real, Node v22.22.3 is present in this sandbox: `node --check web/js/dashboard.js` PASS. `node --check web/js/dashboard-utils.js` PASS. `node --test web/test/dashboard-utils.test.js` PASS, 21/21 (escaping incl. a literal `<img onerror=...>` injection case, live/stale/offline transitions and boundaries, clock-skew safety, custom thresholds, and the live-vs-demo badge distinction incl. the fail-safe default for a malformed/undefined `isLive`). `cd backend && ruff check .` PASS except the same pre-existing `app/api/metrics.py:31` W292 noted in Phase 0 (untouched this phase, not part of this phase's file set). `cd backend && pytest -q` BLOCKED, same as Phase 0 - sandbox Python 3.10.12, backend needs 3.11+ (`numpy==2.4.6`, `datetime.UTC`); unrelated to this phase's changes (no backend files touched). No Flutter/Dart work this phase. | `cc663f8e602680f9dc0feccd0757ef1fe498a48b` |
| Phase 4 - Minimal API safety and release evidence | DONE except APK (BLOCKED - no Android/Flutter toolchain in this sandbox); pytest still BLOCKED (Python 3.10 vs required 3.11+, unchanged since Phase 0) | `SosIn` (`app/api/sos.py`, the unauthenticated ingest model) now enforces `vessel_id`/`boat` ≤32 chars, `note` ≤64 chars - mirroring `mobile/lib/core/config.dart`'s own caps and the firmware's fixed C buffers (`SosItem` in the `.ino`) - plus `lat`/`lon` range checks. `trust_tier` is normalised to a known value via a validator instead of 422-rejecting, since it is corroboration metadata that must never be a reason to drop a real distress call (only routing-relevant fields 422). Found and fixed a real, live authorization gap: `POST /api/advisories/alert` had no auth dependency at all (not even `require_user`) despite publishing directly to `status: 'Published'`, visible on the unauthenticated `GET /api/public/advisories`; grepped the entire repo (`web/js/*`, `backend/app/*`) and found no caller anywhere - it was a dead, unauthenticated public-advisory-injection endpoint. Now requires a token like every other write in that router. Confirmed the one other unauthenticated write, `POST /api/sos/{id}/reply`, already has a documented rationale in its own docstring (fisher has no account) and left it alone per Hard Reset rule 2. Confirmed every other POST/PUT/DELETE route in the backend is already covered by a router-level `dependencies=[Depends(require_user)]` in `main.py` - checked by grepping every `@router.<verb>` decorator against that list, not assumed. Updated the stale `main.py` comment that no longer matched reality ("Advisories handles its own auth per-route to avoid breaking JS alert triggers" - no such JS trigger exists). New tests: `backend/tests/test_sos_ingest.py` (oversized vessel_id/boat/note rejected, boundary-length accepted, out-of-range lat/lon rejected, unrecognised trust_tier normalised not rejected, an HTML-injection-shaped note accepted and preserved verbatim - pairing with Phase 3's dashboard-side escaping test to pin both halves of that contract) and `backend/tests/test_auth.py` (`POST /api/advisories/alert` requires a token). Updated `README.md` with a new "Week 1 dashboard/Flutter contract sprint" section that explicitly separates genuinely-verified-by-running-a-check items from implemented-but-unverified ones (does not upgrade any Flutter/pytest-dependent claim to "working" since neither could run here); added a callout at the top of `docs/08_DEMO_AND_STATUS.md` pointing to the current status instead of rewriting that pre-existing, already-stale Day 1-3 hackathon doc (out of this phase's scope). APK: **not rebuilt** - no Flutter/Android toolchain in this sandbox (`which flutter`/`dart`/`android`/`adb` all empty, no SDK found on disk); `mobile/AqOne.apk` is unchanged, sha256 `3e08365bda94eedfb765ff71f7205cefabffe4fd21b00aa7add3eb6ceebe5ccb`, dated before this sprint. Per the plan's own rule ("Build a fresh APK only after all Flutter tests pass"), building would be doubly blocked even if a toolchain existed, since `flutter test` has not run. Checks: `cd backend && ruff check .` PASS except the same pre-existing `app/api/metrics.py:31` W292 (untouched, not part of this phase's file set). `cd backend && pytest -q` BLOCKED, identical reason/output to Phase 0 (15 collection errors, Python 3.10 vs 3.11+ required) - re-ran to confirm no regression, none found; new test files also fail to collect for the same interpreter-version reason, confirmed syntactically valid instead via `python3 -m py_compile` (clean) and `ruff` (clean). `cd mobile && flutter analyze` / `flutter test` BLOCKED, same as Phases 1-2. `node --check web/js/dashboard.js` PASS. `node --test web/test/dashboard-utils.test.js` PASS, 21/21 (re-run, unchanged from Phase 3 - no dashboard JS touched this phase). | `43bdd02a7151f163b4b5e162b8f868437e85b9cf` |

## Required final handoff

At the end of Week 1, report:

1. Completed phases and commit hashes.
2. Commands run and their complete pass/fail summaries.
3. Exact unresolved blockers, especially hardware or dependency blockers.
4. What is real, mocked, simulated, and untested.
5. The next recommended task for Week 2.

## Week 1 final handoff

### 1. Completed phases and commit hashes

All five phases done (Phase 0 doc/fixtures, Phases 1-4 code). Two commits per
phase (the phase's changes, then a follow-up doc commit recording that
phase's own hash once known):

| Phase | Commit(s) |
|---|---|
| 0 - Baseline and contract fixtures | `8133add3888824d17581ba4a0ece22b5aa91a574` |
| 1 - Flutter buoy contract and delivery states | `29df9f6150d374f2d4e0e9a02e14c4a64561aa71` |
| 2 - Offline acknowledgement and ETA | `418651aba1e954044fe25f32c76541af9364826e` |
| 3 - Dashboard operational honesty and safety | `cc663f8e602680f9dc0feccd0757ef1fe498a48b` |
| 4 - Minimal API safety and release evidence | `43bdd02a7151f163b4b5e162b8f868437e85b9cf` |

### 2. Commands run and their complete pass/fail summaries

| Command | Result |
|---|---|
| `node --check web/js/dashboard.js` | **PASS** (Phases 0, 3, 4) |
| `node --check web/js/dashboard-utils.js` | **PASS** (Phase 3) |
| `node --test web/test/dashboard-utils.test.js` | **PASS**, 21/21 (Phases 3, 4) |
| `cd backend && ruff check .` | **PASS** except one pre-existing, untouched finding: `app/api/metrics.py:31` `W292` missing trailing newline (every phase) |
| `cd backend && pytest -q` | **BLOCKED every phase** - sandbox Python is 3.10.12; `requirements.txt` pins `numpy==2.4.6` (needs ≥3.11) and `app/api/advisories.py`/several test files use `datetime.UTC` (stdlib, added in 3.11). 15 collection errors, 0 tests ever run, unchanged across all phases. |
| `cd mobile && flutter analyze` | **BLOCKED every phase** - no Flutter SDK installed in this sandbox (`which flutter` empty, no SDK found on disk) |
| `cd mobile && flutter test` | **BLOCKED every phase**, same reason |
| APK build (`flutter build apk --release`) | **BLOCKED** - no Flutter/Android toolchain; also blocked transitively because its own precondition (`flutter test` passing) never ran |

Where a required check could not run, the affected `.dart`/`.py` files were
instead read back in full after every edit and checked by hand for
type/control-flow consistency, and Python files were confirmed syntactically
valid with `python3 -m py_compile`. This caught at least one real bug before
commit (a missing `await` on an async call in Phase 2's `reconcile()`) but is
explicitly not a substitute for the real toolchain.

### 3. Exact unresolved blockers

- **Python 3.10 vs backend's 3.11+ requirement.** Blocks `pytest` entirely,
  every phase. Needs a Python 3.11+ interpreter; attempted `uv python install
  3.11` in this sandbox and it failed - outbound access to
  `objects.githubusercontent.com` (where `uv` fetches the standalone Python
  build) is not reachable from here, though `github.com` itself returns 200.
- **No Flutter/Dart SDK.** Blocks `flutter analyze`, `flutter test`, and any
  APK build. Every `.dart` change in Phases 1-2 is unverified by the actual
  toolchain.
- **No Android device or emulator.** Even with a Flutter SDK, the plan's
  "install and test on a physical device" step needs real hardware this
  sandbox does not have.
- **Environment git quirk** (not a plan blocker, but worth flagging): this
  repo's `.git` directory intermittently produces stray `index.lock`/
  `HEAD.lock` files that fail to `rm`/`git`-unlink from this sandbox
  (`Operation not permitted`, even though the files are owned by the same
  user). Commits still succeeded by moving the stale lock files aside before
  each git operation. If a real git client on the host machine reports
  "another git process is running," this is likely the same issue.

### 4. What is real, mocked, simulated, and untested

- **Real and independently verified this week:** the dashboard's freshness
  indicator and HTML-escaping logic (`web/js/dashboard-utils.js`) - genuinely
  exercised by `node --test`, 21/21 passing, in this same environment.
- **Real code changes, verified only by manual review + `ruff`/`py_compile`
  (not by the toolchain the plan actually requires):** all Flutter changes
  (Phases 1-2), backend validation/authorization changes (Phase 4).
- **Simulated/demo, and now honestly labelled as such** (this week's Phase 3
  work): `web/js/dashboard.js` `alertData` (scripted sample incidents, now
  carry a `DEMO` badge) and `initialBuoys` (fixed battery/signal/pressure
  values, now labelled "(simulated)" in the buoy popup). These were
  previously indistinguishable from live data on screen.
- **Untested/unexercised end-to-end:** the entire Flutter↔firmware contract
  fix (Phase 1) and offline-ETA-via-buoy path (Phase 2) have never run
  against real hardware or even a Flutter test runner this week - only
  read and reasoned about.
- **Unchanged, not touched this week:** LoRa mesh/relay (still out of scope
  per the plan), the buoy firmware itself (read for the contract audit,
  not modified), `mobile/AqOne.apk` (still the pre-sprint build).

### 5. Next recommended task for Week 2

Run the actual toolchain this sandbox couldn't: `flutter analyze` and
`flutter test` on a machine with the Flutter SDK, and `pytest -q` on Python
3.11+. Treat every Phase 1/2/4 code change as provisional until then - fix
whatever those tools find before building a release APK per the plan's own
ordering (tests green, then build). Once Flutter tests pass, build and
install the APK on a physical device and record its version/checksum here,
completing the one Definition-of-Done item that could not be closed this
week.
