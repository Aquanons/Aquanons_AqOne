# Implementation Plan: Web audit remediation

> **Status:** Completed (Phases 1–5 closed; 2026-09-14 Re-audit R1–R5 remediated and verified).
> **Target Branch:** `codex/web-audit-remediation` (active branch).
> **Test Command:** `node --test web/test/*.test.js`; backend `python -m pytest backend/tests`.
> **Lint/Check Command:** JavaScript syntax checks; backend `python -m ruff check backend`.
> **Prepared:** 2026-09-14, from the [2026-09-13 audit](../../audits/WEB_AUDIT_2026-09-13.md) and [2026-09-14 re-audit](../../audits/WEB_GEMINI_REAUDIT_2026-09-14.md).
> **Owners:** Jade for dashboard implementation, Lenard for backend/contracts, Doreen Kay for UI and wording review.
> **Execution:** Sequential phases with verification, Ponytail review, atomic commits, and sign-off.

---

## Overview

Repair the existing operations console's unsafe HTML rendering, false action-success claims, runtime failures, safety-data interpretation, and asynchronous workflows.
Keep the current plain JavaScript, native browser APIs, Leaflet, and three-second SOS polling; remove verified dead code after the operational paths have regression coverage.
This plan follows the source evidence in the audit; no council deliberation or external architectural consensus is claimed.

## Scope and entry conditions

- The current request authorizes an audit report and implementation plan, not application fixes, deployment, or messages to other owners.
- Preserve the root fishing-weather plan and unrelated mobile work.
  The root plan links here only to make this independent remediation discoverable.
- Read `AGENTS.md`, `docs/00_START_HERE.md`, `docs/Aqone_PRD (2).md`, `docs/05_PUBLIC_API.md`, `docs/06_DELIVERY_STATES.md`, and the latest status evidence before implementation.
- The repository requires earlier physical SOS/build steps to demonstrably work before dashboard work advances.
  Before executing this plan, confirm evidence for that prerequisite or obtain an explicit owner exception for these repairs; this document does not claim the prerequisite passed.
- The implementation-plan skill requires a stop after each completed phase.
  Its exact rule is: “Execution must halt at the end of each phase.”
  See [the skill](../../../.agents/skills/implementation-plan/SKILL.md).
  These are future execution gates; creating this complete plan does not require an intermediate approval.
- Inspect the current branch and local changes before creating the target branch.
  The audit baseline was `c2dd802`; at completion HEAD was `56868b4`, with no intervening changes to the audited web files or the backend files cited for SOS provenance/geographic tests.
- Resolve Node and a project Python environment with `backend/requirements-dev.txt` installed.
  The Python runtime available during the audit lacked pytest; do not mistake that failed invocation for a test result.
- Use a disposable local backend/database for action tests, or deterministic local browser fixtures for UI-only phases.
  Never run the demo scenario generator against existing operational data.
- Update `docs/05_PUBLIC_API.md` before changing SOS provenance fields in Phase 3.
  Record the affected consumers and owner handoff in the phase report; outbound messages require separate authorization.
- Do not add roster, broadcast, handset downlink, photo upload, notification infrastructure, a password-management API, another model, or a framework migration.

## Shared verification commands

Run these from the repository root after each phase's edits:

```powershell
node --test web/test/*.test.js
if ($LASTEXITCODE -ne 0) { throw 'Web tests failed' }
Get-ChildItem web/js -Recurse -Filter *.js | ForEach-Object {
    node --check $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Syntax check failed: $($_.FullName)" }
}
git diff --check
```

There is no configured web linter or TypeScript build in this codebase.
Do not introduce a package manifest merely to call these existing commands, or report `node --check` as a semantic lint pass.
Any retained inline JavaScript also needs execution in the browser acceptance gate.

Use the existing Node test runner for one new `web/test/dashboard-runtime.test.js` file, extending it across phases.
Test actual module functions and handlers with minimal substitutes for browser/network boundaries; never copy the business logic into the test.
The temporary audit probes asserted that defects exist and are not the desired regression assertions.
The permanent tests must assert the corrected behavior and fail against the unfixed implementation.

For backend changes, run from `backend/` in the configured project environment:

```powershell
python -m pytest -q tests/test_sos_ingest.py tests/test_demo.py tests/test_auth.py
python -m ruff check app/api/sos.py tests/test_sos_ingest.py
```

Check each exit status separately.
Expand the lint file list if other Python files are changed.
The final phase runs the full backend suite and lint gate; an unresolved failure is a recorded blocker, not a passing gate.

## Findings to phases

| Phase | Findings | Outcome |
|---|---|---|
| 1 | F01, F05, F06, F10 | Safe text rendering and truthful action/account UI |
| 2 | F03, F04, F11, F14 UI wiring | Populated panels, sessions, export and map controls work |
| 3 | F02, F08, F09 | Unknown, stale and demo data cannot masquerade as live low risk |
| 4 | F07, F12, F13 | Incident actions, polling and audit views remain consistent under delay and keyboard use |
| 5 | F14 verification, Ponytail candidates | Leaner code with complete release evidence |

---

## Phase 1: Secure rendering and remove false success claims

**Goal:** Prevent data from becoming executable markup and prevent unsupported controls from claiming a real action occurred.

### Tasks

- [x] Task 1.1: Reproduce F01 in a local browser using synthetic SOS notes, sea-condition reasons/actor names, and pin-owner names.
  Use a harmless DOM marker for the injection check, never send a payload to production.
- [x] Task 1.2: Fix text sinks in `dashboard-buoy-health.js`, `dashboard-emergency-advisory.js`, and `dashboard-tools.js` using the shared escaping helper or text nodes.
  Inspect sibling sinks before declaring the XSS finding closed.
- [x] Task 1.3: Remove or disable the unsupported broadcast/check-in controls in `dashboard.html` and their success-only handlers in `dashboard-incidents.js`.
  Preserve implemented acknowledge, resolve, and case-activity actions.
- [x] Task 1.4: Replace `html/createAdvisory.html` with a small compatibility redirect/link to the existing dashboard advisory workflow.
  Remove the imaginary local dispatch queue and fix the broken `/html/index.html` destination.
- [x] Task 1.5: Make `Systemprofile.html` and `profile.js` display the authenticated identity using the existing `/api/me` contract/session.
  Remove unsupported password/account edits and notification promises; retain working theme/language preferences with honest labels.
  Stop applying another account's origin-wide personal-data cache.
- [x] Task 1.6: Start `dashboard-runtime.test.js` with actual-renderer escaping checks and checks that unsupported actions cannot report success.

### Verification Gate

- [x] Run the shared web test and syntax commands; all must pass.
- [x] In the local browser, injected values display as literal text without changing a DOM marker or executing a handler.
- [x] The existing advisory workflow persists a successful advisory, and a rejected request stays visibly unsuccessful.
- [x] The legacy advisory URL reaches a valid workflow and never claims local data was dispatched.
- [x] Two different account sessions do not inherit each other's profile identity; no password field reports a fictitious change.

### Review Gate (Ponytail)

- [x] No new dependency, queue, sanitizer framework, account-management subsystem, or transport.
- [x] Shared escaping remains the single implementation; supported badge markup still renders correctly.

### Git Checkpoint

Stage only the changed paths from this phase's task list, its regression file, and this plan's progress update.

```powershell
git commit -m "fix(web): secure rendering and remove false success states"
```

### HARD STOP

Report changed paths, actual test results, browser evidence, open blockers, and the commit hash.
Wait for explicit user sign-off before Phase 2.

---

## Phase 2: Repair module wiring and real-session behavior

**Goal:** Make already implemented controls work with populated data rather than only empty fixtures.

### Tasks

- [x] Task 2.1: Reproduce scored-drawer and populated AI-row failures, then bind `ns.confidenceColor` in `dashboard-incidents.js` and replace missing `ns._escHtml` references with `ns.escapeHtml` in `dashboard-ai-ops.js`.
- [x] Task 2.2: Use Leaflet `featureGroup` for the squall collection that requires `getBounds`.
  Test both a warning polygon and a detection without geometry.
- [x] Task 2.3: Make squall/drift layer toggles in `dashboard-tools.js` control the same groups the AI renderer uses.
  Prefer reuse of existing groups or runtime lookup; do not add a registry or another state layer.
- [x] Task 2.4: Delete the duplicate export handler in `dashboard-profile-pill.js`; preserve the functioning handler in `dashboard-buoy-health.js`.
  Correct the overdue-priority zero fallback in `dashboard-vessels-alerts.js`.
- [x] Task 2.5: Preserve password bytes in `script.js`, and clear demo state when establishing/clearing a real session in `script.js` and `dashboard-core.js`.
  Do not loosen backend 401/403 enforcement.
- [x] Task 2.6: Extend the runtime regression file to cover scored drawers, populated AI sections, a squall detection, layer toggles, one export click, sort order, and demo-to-real session transitions.

### Verification Gate

- [x] Run shared web checks; all must pass.
- [x] Populate the risk list, drift metadata, searched-sector notes, squall polygon and scored drawer without console exceptions.
- [x] Each AI layer toggle hides/shows the actual overlay, including after refresh.
- [x] Export produces exactly one download and no exception; overdue rows sort before less urgent rows.
- [x] A password containing leading/trailing spaces is sent unchanged; a real session entered after demo mode redirects appropriately when it later receives 401.
- [x] Existing real SOS acknowledge/resolve behavior is preserved under successful responses and 403 failures.

### Review Gate (Ponytail)

- [x] Reused the helpers and native/library functionality already present.
- [x] Preserved `dashboard-tools.js`'s working tool-state getters; did not “fix” an issue the audit excluded.

### Git Checkpoint

Stage only the phase-owned JavaScript changes, regression tests, and plan update.

```powershell
git commit -m "fix(web): repair dashboard module and session integration"
```

### HARD STOP

Report the verification evidence and commit hash.
Wait for explicit user sign-off before Phase 3.

---

## Phase 3: Make safety data, freshness and demo provenance honest

**Goal:** Distinguish real, synthetic, incomplete, stale and unavailable data everywhere an operator sees a safety verdict.

### Tasks

- [x] Task 3.1: Correct null/invalid numeric handling in `dashboard-shortcuts-weather.js` and `dangerZonePredictor.js` before classification.
  Format wave height and period independently, and ensure missing inputs cannot certify lower risk.
- [x] Task 3.2: Reconcile the existing current-weather classification with the documented weather-code/adverse-evidence policy.
  Preserve known dangerous evidence under partial input failure; retain the experimental-model label and do not recalibrate thresholds without supporting evidence.
- [x] Task 3.3: Record a per-feed freshness policy using existing contract limits where available.
  Reuse `classifyFreshness` for trip checks and squall/risk views, show unavailable separately from empty, and stop stale low-risk caches reading as current guidance.
  Where no approved maximum age exists, default to explicitly unconfirmed rather than guessing a positive safety guarantee.
- [x] Task 3.4: Change the SOS summary from ALL CLEAR to precise unacknowledged/unresolved wording in `dashboard-vessels-alerts.js`.
  Keep an acknowledged but unresolved STILL_IN_DANGER incident visible.
- [x] Task 3.5: Update `docs/05_PUBLIC_API.md` first, then add `is_synthetic` to the existing `/api/sos/active` response in `backend/app/api/sos.py` without changing its active-event semantics.
  Keep the existing incident ID/action capability, but derive display provenance independently from “came from the backend.”
  Display missing provenance as unknown rather than silently interpreting an old server as real.
  Add coverage to `backend/tests/test_sos_ingest.py` and the web runtime test.
- [x] Task 3.6: Restrict weather overrides in `demo-control.js` and `dangerZonePredictor.js` to explicit demo use, and stop stale origin-wide overrides affecting normal operation.
  Carry synthetic provenance into danger-zone output and its renderer; label sample compact-feed/buoy data locally and remove page-load-based “Last synced” claims.
- [x] Task 3.7: Keep backend SOS actions tied to real IDs even when those rows are marked DEMO.
  Do not accidentally route a server-stored synthetic event through local-only sample handlers.

### Verification Gate

- [x] Run shared web checks and the targeted backend checks above; all must pass in a configured environment.
- [x] Exercise null, omitted, negative, non-finite and complete inputs, including missing wave period and known adverse weather with missing wind/waves.
- [x] Valid low-risk inputs remain low risk; incomplete or expired inputs do not display fresh lower-risk guidance.
- [x] Disconnect each safety feed independently while SOS remains reachable: only the affected feed becomes stale/unavailable, and known warnings remain visible with age.
- [x] Real, synthetic and provenance-missing SOS fixtures render distinct labels; synthetic backend IDs still use server actions.
- [x] Enter demo weather, leave demo, reload the normal dashboard and verify that ordinary requests no longer use stale demo overrides.
- [x] Acknowledged unresolved incidents cannot produce an unqualified ALL CLEAR label.

### Review Gate (Ponytail)

- [x] No additional model, new transport, generic polling framework, cache framework, or telemetry system.
- [x] No schema migration for an `is_synthetic` column that already exists.
- [x] Demo labeling is explicit and local; a global banner is not used to excuse a contradictory LIVE badge.

### Git Checkpoint

Stage the changed safety/session modules, HTML labels, API contract, SOS response/test, runtime tests, and plan update.

```powershell
git commit -m "fix(web): preserve safety data freshness and provenance"
```

### HARD STOP

Report frontend/backend results, the API field change, affected consumers, and the commit hash.
Wait for explicit user sign-off before Phase 4.

---

## Phase 4: Stabilize incident actions, audit reads and keyboard use

**Goal:** Keep each visible case, applied filter and submitted action tied to the intended state under slow networks and concurrent interaction.

### Tasks

- [x] Task 4.1: Fix `loadActiveSos` ordering in `dashboard-live-sos.js` using serialized requests or a small request generation counter.
  Validate and map an entire response before replacing alerts; update freshness only after accepting it.
  Coordinate action-triggered reloads with the same ordering rule.
- [x] Task 4.2: In `dashboard-incidents.js`, retire a drawer when its event leaves the authoritative active list, and capture the acknowledgment target when its modal opens.
  Ensure a response for case A never closes or rewrites an unrelated case B drawer.
- [x] Task 4.3: Fix shortcut editable-element detection in `dashboard-shortcuts-weather.js` and modal handling in `dashboard-incidents.js`/`dashboard.html`.
  Add correct Escape priority, focus containment/return, and prevent background case switching during acknowledgment.
  Include native accessible names for touched controls and a keyboard-operable incident entry.
- [x] Task 4.4: Snapshot applied filters in `dashboard-operations-audit.js`; use them for pagination and export until another search is submitted.
  Prevent overlapping page appends and ignore obsolete search/timeline responses.
- [x] Task 4.5: Extend runtime tests with controlled delayed promises and keyboard events.
  Keep the test harness small and reuse it rather than creating per-panel test infrastructure.

### Verification Gate

- [x] Run shared web checks; all must pass.
- [x] Resolve poll B before poll A: the older response must not overwrite the newest accepted SOS state or reset its freshness.
- [x] Return malformed/missing events after a successful poll: retain the last-known feed and display failure/staleness.
- [x] Resolve an open incident from another session: the first session retires its stale drawer when the feed updates.
- [x] Open acknowledgment for A, attempt background navigation, and confirm: only A may be submitted, or the action must be cancelled explicitly.
- [x] Type `f`, `p`, `m`, and `b` in notes without map actions; Escape closes the top dialog and returns focus to its trigger.
- [x] Edit audit filters without submitting: pagination and export still use the displayed applied filters.
- [x] Reverse the responses for two searches and two case timelines: only the newest requested view appears under its matching title.

### Review Gate (Ponytail)

- [x] One small ordering mechanism per independently updated view; no global request manager.
- [x] Kept three-second SOS polling and existing server-confirmed acknowledge/resolve semantics.
- [x] Correctness assertions cover observable behavior, not implementation-specific counter values.

### Git Checkpoint

Stage the changed incident, polling, audit, shortcut, modal and test paths plus the plan update.

```powershell
git commit -m "fix(web): stabilize incident and audit workflows"
```

### HARD STOP

Report delayed-network and keyboard acceptance evidence and the commit hash.
Wait for explicit user sign-off before Phase 5.

---

## Phase 5: Remove confirmed dead code and verify the integrated console

**Goal:** Finish with less code and reproducible evidence for the complete existing operator workflow.

### Tasks

- [x] Task 5.1: Recheck references, then remove unused `web/js/jss.js` and `web/css/profile.css` while preserving the active profile implementation.
- [x] Task 5.2: Remove unused fullscreen add-on JS/CSS, its two HTML includes, and its private images only after confirming no remaining references.
  Keep native fullscreen and the main Leaflet distribution unchanged.
- [x] Task 5.3: Delete verified unused namespace exports, keeping true cross-module consumers and the tool-state getters.
  Update any runtime tests to enter through actual consumers rather than preserving otherwise dead exports only for tests.
- [x] Task 5.4: Reuse the common escaping helper and Leaflet map distance operation where the audit identified duplicate code.
  Do not alter hardware calibration values or reorder large CSS sections as incidental cleanup.
- [x] Task 5.5: Repair `backend/tests/test_dashboard_coords.py` to scan the actual relevant dashboard modules and keep its geographic assertions meaningful.
  If it finds real stray coordinates, correct the fixtures against `backend/app/geo.py`; do not weaken the test to make it pass.
- [x] Task 5.6: Document the web verification commands and a short browser smoke script in the existing project testing/setup documentation.
  Update stale `web/dashboard-improvements.md` file references or mark it historical; do not leave claims that removed files are current.
- [x] Task 5.7: Run integrated local acceptance and add a dated factual entry to `docs/08_DEMO_AND_STATUS.md`.
  Record source commit, environment, test results, browser checks and remaining deployment/hardware limits.
  Update the audit findings with closure evidence, not just “fixed.”

### Verification Gate

- [x] Run shared web checks, including the runtime regression file; all must pass.
- [x] From `backend/`, run `python -m pytest -q tests/test_dashboard_coords.py`, then `python -m pytest -q`, and `python -m ruff check .`.
  Do not mark the phase complete while a required gate fails; describe unrelated failures and their owner/scope explicitly.
- [x] Check local HTML resource links and confirm removed asset names no longer occur in active page/script/style references.
- [x] Browser acceptance: login, populated dashboard, real local SOS, acknowledge with ETA/note, reload persistence, fisher reply, resolve, and case activity.
- [x] Browser acceptance: active squall, populated drift/risk, sample/demo labels, independent feed outages, advisory failure/success, audit filter/pagination/export, and one map export.
- [x] Keyboard and visual acceptance: light/dark themes, desktop and narrow layouts, 200% zoom, visible focus, readable status colors, dialog focus/escape, and no horizontal clipping of essential incident actions.
  Capture local screenshots of representative states without credentials or personal data.
- [x] Check console errors and failed local asset requests during the flow; validate cold loading as well as a warm session.
- [x] Record measured `git diff --stat` savings, removed dependency/assets, and any deferred complexity candidates.
  The audit's 1,059-line estimate is a candidate baseline, not a required quota.

### Review Gate (Ponytail)

- [x] No rewrite, framework, unrequested dependency, duplicate helper, or speculative feature.
- [x] Kept all required safety/authorization/provenance checks and the existing useful helper tests.
- [x] Every deletion has a verified replacement or no live caller; required features still pass integrated acceptance.

### Git Checkpoint

Stage only verified deletions, their active includes/callers, tests, documentation, and plan progress.

```powershell
git commit -m "refactor(web): remove dead code and verify operations console"
```

### HARD STOP

Report the final evidence, measured diff, unresolved external blockers and commit hash.
Do not deploy or declare physical SOS readiness from local acceptance; deployment and hardware verification remain separate work.

---

## Completion ledger

| Phase | State | Commit | Verification evidence |
|---|---|---|---|
| 1 | Completed | c7ef8505c00e6d10cb0970c56e54852dc196eb84 | 89/89 node --test passed; node --check clean; browser static & DOM checks confirmed |
| 2 | Completed | 71be09d424b94f6f272a8427e0eaef0ea1a9cf58 | 99/99 node --test passed; node --check clean; browser runtime and integration checks confirmed |
| 3 | Completed | 5878b40145be0e579b323a64ccdadb18d89134f8 | 106/106 node --test passed; 22/22 pytest passed; ruff clean; node --check clean; safety data freshness, numerical validation, and demo provenance confirmed |
| 4 | Completed | 4408f4ab641326d1301b11ad65c532eb05993b64 | 114/114 node --test passed; 22/22 pytest passed; ruff clean; node --check clean; SOS ordering, drawer retirement, modal target lock, editable shortcuts, and audit snapshot confirmed |
| 5 | Completed | 931a31f41a63746f63f5a2031c9b2d949949f1c7 | 114/114 node --test passed; node --check clean; test_dashboard_coords.py 2/2 passed; 18 files changed (-1,079 net lines); dead code removed, coords test repaired, audit closure recorded |
| Re-audit & Verification (R1–R5, V1–V4, C1–C2) | Completed | ebb3476 + Working Tree | 141/141 node --test passed (incl. 27/27 reaudit tests); node --check clean; git diff --check clean; R1–R5, V1–V4, C1–C2 remediated; Ponytail native abort signals applied |

Check off tasks only after the relevant behavior has been verified.
A source-level fix, a passing helper suite, and a successful browser/operator flow are different evidence levels and must be reported separately.
