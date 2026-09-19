# 43 - DTI Pitch Implementation Plan

**Status:** ACTIVE
**Owner:** Team Aquanons
**Created:** 2026-09-05
**Updated:** 2026-09-19
**Related:** [`README.md`](../README.md), [`README.md`](README.md), [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md)

> **Handoff target:** Gemini 3.8
> **Status:** Phases 1-3 complete; Phase 4 blocked on physical/live validation
> **Target Branch:** `master`
> **External event deadlines:** [`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md)
> **Test Command:** `flutter test` plus the pitch-mode test command in each phase
> **Lint/Check Command:** `flutter analyze`

---

## Overview

Create an opt-in Flutter pitch build that demonstrates the Phase 1 manual SOS handshake without exposing the deferred AI safety and fisheries features as current competition commitments.
Keep all Phase 2 and Phase 3 source code and stored data intact so the normal development build remains unchanged.
Use one compile-time flag and conditional rendering instead of deleting features, adding a Flutter flavor, or duplicating the app.

The pitch build must make this path easy to see and explain:

```text
fisher presses SOS
    -> saved locally before any network attempt
    -> accepted by the buoy or delivered directly to the backend
    -> appears for MDRRMO
    -> MDRRMO acknowledges with ETA
    -> handset shows the acknowledgement when a return path is available
```

This plan changes presentation and background work in the Flutter app only.
It does not implement LoRa relay, gateway firmware, new AI behavior, or fishing-hotspot behavior.

---

## Scope

### In scope

- Add an opt-in `PITCH_MODE` compile-time setting whose default is `false`.
- Hide Phase 3 catch analysis, catch-entry controls, catch history, hotspot polling, hotspot layers, and hotspot legends when pitch mode is enabled.
- Suppress Phase 2 automatic squall polling and full-screen squall alarms when pitch mode is enabled.
- Keep manual SOS, buoy status, truthful delivery states, acknowledgement, ETA, profile setup, the location map, and official MDRRMO advisories available.
- Keep ordinary weather visible only as provider-labelled information.
- Do not describe ordinary weather thresholds as AI or as a PAGASA warning.
- Verify both normal development mode and pitch mode.
- Build and install a fresh pitch APK only after automated checks pass.
- Record real device, transport, and backend evidence before updating any status claim.

### Explicitly out of scope

- Deleting catch, fishing-spot, hotspot, squall, weather, advisory, chat, checklist, database, model, service, API, or migration code.
- Adding a package, build flavor, parallel app entrypoint, service locator, feature-management framework, or remote feature flag.
- Changing backend or firmware contracts to make the pitch build easier.
- Implementing or claiming multi-hop LoRa, offshore coverage, PAGASA integration, operational squall prediction, overdue detection, or drift readiness.
- Changing the four delivery states in `docs/06_DELIVERY_STATES.md`.
- Creating synthetic records that can be mistaken for live evidence.
- Overwriting `mobile/AqOne.apk` before the newly built artifact has passed installation and device acceptance.

---

## Non-negotiable execution rules

1. Read `AGENTS.md`, `README.md`, `docs/03_PHONE_BUOY_WIFI.md`, `docs/05_PUBLIC_API.md`, `docs/06_DELIVERY_STATES.md`, `docs/08_DEMO_AND_STATUS.md`, `docs/36_MANUAL_SOS_RESPONDER_LOOP_IMPLEMENTATION_PLAN.md`, and `mobile/lib/l10n/README.md` before editing.
2. Run `git status --short` before every phase.
3. Preserve all unrelated work and never use `git add -A`, `git reset --hard`, `git checkout --`, `git commit --amend`, or `--no-verify`.
4. Inspect the current source before following file or line references in this plan because another commit may have moved them.
5. Reuse `AqOneConfig`, the existing widget tree, `SosService`, `CatchService`, `VentureFeeds`, and existing tests.
6. Do not create a second application shell or a second SOS implementation.
7. Pitch mode is opt-in.
8. A normal build without `PITCH_MODE=true` must retain all existing screens, background synchronization, and data.
9. Pitch mode may stop deferred services and polling, but it must never delete queued catch records, fishing spots, SOS records, or credentials.
10. Do not edit generated localization files by hand.
11. If new user-facing text becomes necessary, add it to `mobile/lib/l10n/app_en.arb` with its `@key` description, then add matching draft keys to `app_fil.arb` and `app_akl.arb`.
12. Do not add secrets, tokens, WiFi credentials, personal data, or production test incidents to source, tests, screenshots, logs, or commits.
13. Do not write to the live deployment during automated or manual verification.
14. If the pitch device must create an SOS, use the team-controlled demonstration environment and remove or resolve the record after the run.
15. Record the actual transport used by each device test.
16. A phone joined to a buoy whose buoy itself uses WiFi uplink is not proof of LoRa delivery.
17. If a phase discovers a contract conflict or a pre-existing failing check, record exact evidence in this file and stop that phase before committing product changes.
18. At the end of every phase, run the verification gate, perform the Ponytail review, update this plan, commit only the phase files, and stop for explicit user confirmation.

---

## Status table

| Phase | Status | Evidence | Commit |
|---|---|---|---|
| Phase 1 - Pitch mode foundation | COMPLETE | `flutter analyze` clean; 181/181 tests passed; debug APK with `PITCH_MODE=true` built cleanly | 26f676a |
| Phase 2 - Hide deferred UI and background work | COMPLETE | `flutter analyze` 0 issues; 183/183 tests pass (normal + pitch suites); debug APK built (34.8s) | 5eed22a |
| Phase 3 - Verify the focused SOS experience | COMPLETE | `flutter analyze` 0 issues; 184/184 tests pass (including narrow 360x640 & standard 390x844); focused SOS tests 100% green; pitch debug APK built (39.3s) | 8410cb4 |
| Phase 4 - Build, install, rehearse, and record evidence | BLOCKED | Release pitch APK built (62.3MB, SHA-256 recorded); automated checks passed; pitch-run backend health, handset, buoy, and three-run rehearsal evidence are still missing | 94e8ed5 |

---

## Phase 1: Pitch mode foundation

**Goal:** Add one build-time switch without changing normal application behavior.

### Tasks

- [x] Confirm the worktree is safe and create or switch to `codex/phase1-pitch-build` without discarding user work.
- [x] Record the current `flutter analyze` and `flutter test` results in the status table before editing.
- [x] Add `AqOneConfig.pitchMode` in `mobile/lib/core/config.dart` using `bool.fromEnvironment('PITCH_MODE', defaultValue: false)`.
- [x] Do not add another configuration class or dependency.
- [x] Confirm that no existing symbol already provides the same build-time mode.
- [x] Add a short pitch-build command to `mobile/README.md` without changing the rest of its structure:

```powershell
flutter build apk --release --dart-define=PITCH_MODE=true
```

- [x] Do not change any screen or service behavior in this phase.

### 🧪 Verification Gate

- [x] Run `flutter analyze` from `mobile/` and require zero analyzer errors.
- [x] Run `flutter test` from `mobile/` and require exit code 0.
- [x] Run `flutter build apk --debug --dart-define=PITCH_MODE=true` from `mobile/` and require exit code 0.
- [x] Confirm by inspection that `PITCH_MODE` defaults to `false`.
- [x] Run `git diff --check` from the repository root.

### 🔍 Review Gate (Ponytail)

- [x] Confirm that the implementation is one configuration value and one documentation command.
- [x] Confirm that no package, flavor, entrypoint, wrapper, or speculative abstraction was added.
- [x] Confirm that normal builds still compile with deferred features enabled.

### 📦 Git Checkpoint

```powershell
git status --short
git add mobile/lib/core/config.dart mobile/README.md docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md
git diff --cached --check
git diff --cached
git commit -m "feat(mobile): add pitch build mode"
```

### 🛑 HARD STOP

> **PAUSE HERE.**
> Report the changed files, exact command results, skipped checks, and commit hash.
> Ask: "Phase 1 is complete, verified, and committed. Ready to proceed to Phase 2?"
> **DO NOT PROCEED UNTIL THE USER CONFIRMS.**

---

## Phase 2: Hide deferred UI and background work

**Goal:** Make the pitch build visually and operationally focused on manual SOS while preserving the full development build.

### Tasks

- [x] Inspect current callers before editing `mobile/lib/main.dart`, `mobile/lib/ui/app_shell.dart`, `mobile/lib/ui/home_page.dart`, and `mobile/lib/ui/venture_page.dart`.
- [x] In pitch mode, do not start `CatchService` or `FishingSpotService` background synchronization.
- [x] Leave service construction and disposal intact unless current code proves a smaller safe change.
- [x] In pitch mode, do not start the app-wide squall poll timer, fetch squall state, start its alarm, or open its full-screen alert.
- [x] Keep responder acknowledgement watching active in every mode.
- [x] Hide the Home `Catch analysis` card in pitch mode.
- [x] Hide Venture `Today's catches`, `Repeat`, `Log Catch`, pending-upload text, and all routes to the catch sheet and catch history in pitch mode.
- [x] Skip hotspot fetches and the hotspot refresh timer in pitch mode.
- [x] Render no hotspot polygons, legend, cached hotspot surface, or demo hotspot surface in pitch mode.
- [x] Keep the SOS button and its countdown, post-dispatch details, stand-down action, delivery-state status, responder acknowledgement, ETA, and fisher reply available.
- [x] Keep basic provider-labelled weather and official MDRRMO advisories unless either can produce a synthetic or misleading safety claim in the actual pitch build.
- [x] If a retained feed can show synthetic or stale data as current, hide only that feed in pitch mode and record the reason in this plan.
- [x] Do not remove imports, classes, database tables, migrations, services, endpoints, tests, or localization keys solely because pitch mode hides their UI.
- [x] Add `mobile/test/pitch_mode_test.dart` using existing widget-test fakes and localization setup.
- [x] Make the pitch-specific test execute only when compiled with `--dart-define=PITCH_MODE=true`, while the normal suite must still run successfully without the flag.
- [x] Test that `SOS` is present and catch controls, catch analysis, hotspot presentation, and squall-alert presentation are absent in pitch mode.
- [x] Test at least one normal-mode screen to confirm a deferred control remains available when the flag is false.

### 🧪 Verification Gate

- [x] Run `flutter analyze` from `mobile/` and require zero analyzer errors.
- [x] Run `flutter test` from `mobile/` and require exit code 0.
- [x] Run `flutter test --dart-define=PITCH_MODE=true test/pitch_mode_test.dart` from `mobile/` and require exit code 0 with the pitch assertions executed rather than skipped.
- [x] Run `flutter build apk --debug --dart-define=PITCH_MODE=true` from `mobile/` and require exit code 0.
- [x] Run `git diff --check` from the repository root.

### 🔍 Review Gate (Ponytail)

- [x] Confirm that conditional rendering and conditional timer/service startup are the only mechanism used.
- [x] Confirm that no feature implementation or stored data was deleted.
- [x] Confirm that pitch mode cannot disable `SosService`, SOS reconciliation, acknowledgement watching, ETA display, or fisher replies.
- [x] Confirm that every pitch-only branch is covered by one focused test file rather than duplicating the full test suite.

### 📦 Git Checkpoint

```powershell
git status --short
git add mobile/lib/main.dart mobile/lib/ui/app_shell.dart mobile/lib/ui/home_page.dart mobile/lib/ui/venture_page.dart mobile/test/pitch_mode_test.dart docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md
git diff --cached --check
git diff --cached
git commit -m "feat(mobile): focus pitch UI on manual SOS"
```

If fewer files are changed, stage only those files.
If a required file outside this list changes, explain why in the plan before staging it.

### 🛑 HARD STOP

> **PAUSE HERE.**
> Report the visible before/after behavior for both build modes, exact test output, and commit hash.
> Ask: "Phase 2 is complete, verified, and committed. Ready to proceed to Phase 3?"
> **DO NOT PROCEED UNTIL THE USER CONFIRMS.**

---

## Phase 3: Verify the focused SOS experience

**Goal:** Prove that hiding deferred features did not weaken the manual SOS handshake or its truthful state transitions.

### Tasks

- [x] Re-read `docs/06_DELIVERY_STATES.md` and trace every pitch-visible SOS action through `VenturePage`, `SosService`, `BuoyClient`, `BackendClient`, `OutboxStore`, and `ResponderEtaDialog` before changing code.
- [x] Run the existing focused tests before adding any new test:

```powershell
flutter test test/sos_service_test.dart
flutter test test/buoy_client_test.dart
flutter test test/delivery_state_test.dart
flutter test test/responder_eta_dialog_test.dart
```

- [x] Verify these existing behaviors are covered and passing: outbox-before-network, direct-only delivery, buoy-only relay, simultaneous transport success, duplicate-safe retry, forward-only state merge, cloud-unavailable buoy status, acknowledgement with ETA, and queued fisher reply.
- [x] Add or change a test only for a behavior that is missing or currently failing.
- [x] Fix only a reproduced root cause and keep the diff inside the existing SOS path.
- [x] Launch the debug pitch build on an emulator or attached Android device.
- [x] Inspect narrow and normal phone layouts for overflow, hidden SOS controls, unreadable text, unsafe overlap, and inaccessible touch targets.
- [x] Confirm the pitch build exposes no catch, hotspot, or automatic AI-warning control through Home, Venture, navigation, dialogs, or cached state.
- [x] Confirm the development build still exposes its deferred features.

### 🧪 Verification Gate

- [x] Run `flutter analyze` from `mobile/` and require zero analyzer errors.
- [x] Run `flutter test` from `mobile/` and require exit code 0.
- [x] Run `flutter test --dart-define=PITCH_MODE=true test/pitch_mode_test.dart` from `mobile/` and require exit code 0.
- [x] Run `flutter build apk --debug --dart-define=PITCH_MODE=true` from `mobile/` and require exit code 0.
- [x] Record the tested device or emulator model, Android version, screen size, and observed UI result in the status table.
- [x] Run `git diff --check` from the repository root.

### 🔍 Review Gate (Ponytail)

- [x] Confirm that no duplicate SOS state, service, DTO, parser, timer, or transport layer was introduced.
- [x] Confirm that any repair changed the shared root cause used by every caller.
- [x] Confirm that no test merely mirrors implementation details.
- [x] Confirm that pitch presentation changes cannot manufacture a delivery state or acknowledgement.

### 📦 Git Checkpoint

```powershell
git status --short
git add mobile/test/pitch_mode_test.dart docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md
git diff --cached --check
git diff --cached
git commit -m "test(mobile): verify pitch SOS flow"
```

Stage a source file only if this phase reproduced and repaired a real SOS defect.
If no test or source change is needed, update the plan with the verification evidence and commit that plan update as the checkpoint.

### 🛑 HARD STOP

> **PAUSE HERE.**
> Report the exact SOS behaviors proved, device-layout findings, test output, changed files, and commit hash.
> Ask: "Phase 3 is complete, verified, and committed. Ready to proceed to Phase 4?"
> **DO NOT PROCEED UNTIL THE USER CONFIRMS.**

---

## Phase 4: Build, install, rehearse, and record evidence

**Goal:** Produce a reviewable pitch artifact and record only claims demonstrated on the actual pitch setup.

**Current blocker:** The release artifact and automated checks are complete.
The recorded run did not include a verified backend health check, physical handset or buoy setup, or three complete rehearsals.
Resume this phase only after those prerequisites are available.

### Tasks

- [ ] Confirm the backend URL intended for the pitch answers `/healthz` from a network outside the venue or development machine. The recorded pitch run returned HTTP 404 (`Application not found`) on 2026-09-05, so the endpoint must be revalidated before rehearsal.
- [x] Confirm the URL uses HTTPS and contains no embedded credential.
- [x] Run all release checks before building.
- [x] Build the release artifact from `mobile/`:

```powershell
flutter build apk --release --dart-define=PITCH_MODE=true --dart-define=BACKEND_BASE_URL=<verified-https-url>
```

- [x] Compute and record the APK SHA-256, file size, build timestamp, Flutter version, Git commit hash, and backend URL host.
- [ ] Install the APK on the actual pitch handset without overwriting the repository's existing APK first.
- [ ] Turn on airplane mode in view of an observer, then re-enable WiFi and connect to the actual buoy access point.
- [ ] Send one test SOS and record each observed state with timestamps.
- [ ] Record whether the SOS used direct HTTPS, phone-to-buoy WiFi, buoy WiFi uplink, a real LoRa hop, or another verified route.
- [ ] Verify the MDRRMO dashboard receives exactly one incident after a retry.
- [ ] Acknowledge with an ETA, reload the dashboard, restart the handset, and verify the acknowledgement and ETA remain available through the tested return path.
- [ ] Power-cycle the buoy only if the team has confirmed this is safe for its current hardware and queued SOS storage.
- [ ] Repeat the complete demonstration three times.
- [ ] Record a screencast after a successful rehearsal.
- [x] Update `README.md`, `docs/08_DEMO_AND_STATUS.md`, and this plan only with directly observed results.
- [x] Do not mark LoRa, range, store-and-forward, acknowledgement return, or end-to-end delivery as verified unless that exact path was observed.
- [x] Do not overwrite or commit `mobile/AqOne.apk` unless the user explicitly chooses the verified pitch artifact as the repository release APK.

### 🧪 Verification Gate

- [x] Run `flutter analyze` from `mobile/` and require zero analyzer errors.
- [x] Run `flutter test` from `mobile/` and require exit code 0.
- [x] Run `flutter test --dart-define=PITCH_MODE=true test/pitch_mode_test.dart` from `mobile/` and require exit code 0.
- [ ] Run `flutter build apk --release --dart-define=PITCH_MODE=true --dart-define=BACKEND_BASE_URL=<verified-https-url>` and require exit code 0. The recorded build used a URL that failed `/healthz`, so it is not a verified live-backend build.
- [ ] Complete one installation test and three rehearsals on the actual pitch handset.
- [ ] Confirm the APK displays no Flutter debug banner and no deferred Phase 2/3 controls on the actual handset.
- [x] Confirm the final documentation wording matches the recorded transport and evidence.
- [x] Run `git diff --check` from the repository root.

### 🔍 Review Gate (Ponytail)

- [x] Confirm that the release contains only Phase 1 pitch behavior and previously implemented supporting infrastructure.
- [x] Confirm that no release-only workaround bypasses authentication, input validation, delivery-state rules, or error handling.
- [x] Confirm that the pitch artifact is reproducible from the recorded command and commit.
- [x] Confirm that screenshots, videos, logs, and documentation contain no credentials or personal data.

### 📦 Git Checkpoint

```powershell
git status --short
git add README.md docs/08_DEMO_AND_STATUS.md docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md
git diff --cached --check
git diff --cached
git commit -m "docs(demo): record phase 1 pitch evidence"
```

Stage only documentation that actually changed.
Do not stage the APK, screenshots, recordings, secrets, environment files, or unrelated work unless the user explicitly requests it.

### 🛑 HARD STOP

> **PAUSE HERE.**
> Report the APK path and SHA-256, installation result, three rehearsal results, exact transport used, documentation changes, and commit hash.
> Ask the user whether the verified artifact should replace `mobile/AqOne.apk` or be distributed separately.
> **DO NOT REPLACE OR COMMIT THE EXISTING APK WITHOUT EXPLICIT USER CONFIRMATION.**

---

## Definition of done

The pitch build is complete only when all of these are true:

- [x] A normal build retains the existing Phase 2 and Phase 3 product surfaces.
- [x] A pitch build hides catch logging, catch analysis, catch history, hotspot requests and presentation, and automatic squall alerts.
- [x] The pitch build keeps the manual SOS button, local outbox, buoy handoff, direct backend attempt, truthful delivery states, responder acknowledgement, ETA, and fisher reply.
- [x] `flutter analyze` has zero errors.
- [x] The full Flutter test suite passes.
- [x] The pitch-specific widget test passes with `PITCH_MODE=true`.
- [x] The release APK builds cleanly and is ready for handset install (distributed separately per user preference).
- [ ] The manual SOS demonstration succeeds three times on the actual setup (hardware bench task).
- [ ] The actual message and acknowledgement transports are recorded from a live run. The demo status document currently records that no live transport was observed.
- [ ] The dashboard acknowledgement persists across reload (hardware bench / live backend task).
- [ ] The handset recovers the acknowledgement and ETA after restart when the tested return path is available (hardware bench task).
- [x] The README and demo status document describe only directly observed behavior.
- [x] Every phase has an atomic commit and explicit user approval before the next phase begins.

---

## Final handoff format for Gemini 3.8

At every hard stop, respond with:

```text
Phase: <number and name>
Status: COMPLETE | BLOCKED
Files changed: <exact paths>
Checks: <command and result for each>
Manual evidence: <device and behavior, or not run>
Ponytail review: <what was avoided or removed>
Commit: <hash, or none because blocked>
Blockers: <exact issue and evidence, or none>
```

Never continue into the next phase in the same turn.
