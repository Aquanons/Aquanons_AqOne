# Implementation Plan: Ponytail Audit Cleanup

> **Status:** Completed and verified across Phases 1–5 on branch `codex/ponytail-audit-cleanup`.  
> **Target Branch:** `codex/ponytail-audit-cleanup` created from the current checkout after inspecting local changes.  
> **Test Command:** Backend: `python -m pytest -q`; mobile: `flutter test`; web: `node --test web/test/*.test.js`; firmware: `pio run -d firmware`.  
> **Lint/Check Command:** Backend: `python -m ruff check .`; mobile: `flutter analyze`; JavaScript: `node --check <changed-file>`; repository: `git diff --check`.  
> **Prepared:** 2026-09-18.  
> **Source:** Repository-wide Ponytail audit requested after the latest teammate feature merges.

---

## Overview

Remove verified dead code, generated output, obsolete compatibility paths, unused dependencies, and out-of-scope photo transport without redesigning AqOne.
Preserve the working SOS, text identity, catch-log aggregation, dashboard, firmware, localization source, and deployed database migration history.
The cleanup is split into five independently verified commits, with an explicit user approval stop after every phase.

## Gemini handoff and authorization

- The user requested a plan to hand these audit findings to Gemini.
- This document authorizes local repository cleanup only after Gemini re-verifies each caller and build input listed below.
- This document does not authorize deployment, Git history rewriting, release publishing, messages to teammates, schema drops, or automatic execution of later phases.
- Read `AGENTS.md`, `docs/00_START_HERE.md`, `docs/07_SCOPE_OUT.md`, `docs/Aqone_PRD (2).md`, and this plan before editing.
- Read `mobile/lib/l10n/README.md` before changing localization tracking or regeneration behavior.
- Apply `.agents/skills/ponytail/SKILL.md` throughout execution.
- Start with `git status --short`, `git branch --show-current`, and a recorded baseline of the relevant test and lint commands.
- Preserve unrelated user changes and untracked files.
- Never use `git reset --hard`, broad checkout restoration, `git add .`, or a history rewrite.
- Do not delete or edit historical migrations `013_fishing_spots.sql` or `028_vessel_avatar.sql`.
- Do not drop deployed database columns or tables as part of this cleanup.
- Do not manually edit generated localization Dart files.
- Stage only the exact phase-owned paths shown in each checkpoint, adjusted downward when a listed file does not need to change.
- Stop after every phase, report exact verification results and the commit hash, and wait for explicit user approval.

## Audit decisions

| Finding | Decision | Guardrail |
| --- | --- | --- |
| Legacy `arduino/data` web bundle | Remove after confirming firmware has no filesystem mount or static-serving path. | Do not touch the active `web/` dashboard or either firmware sketch. |
| Generated Flutter localization Dart | Stop tracking and regenerate from ARB files. | Keep all ARB sources, fallback delegates, and `l10n.yaml`; verify a clean checkout can regenerate before tests. |
| Exact-location fishing spots | Remove dormant runtime pipeline. | Keep aggregate `/api/public/hotspots`, catch-log aggregation, and migration history. Leave existing device/database rows untouched and inert. |
| Avatar upload and dispatcher delivery | Remove as out of scope. | Keep text vessel identity and the existing local-only profile photo UI unless a caller trace proves it also depends on backend transport. |
| Checked-in release APK | Remove only when an existing external release copy is verified or the user separately confirms it is no longer the distribution path. | Do not publish a GitHub Release or rewrite Git history under this plan. |
| Dashboard namespace exports | Delete exports with no repository caller. | Preserve script load order, behavior, and security escaping. Do not introduce a bundler or module framework. |
| Caller-free backend helpers | Delete after a fresh repository-wide search. | Do not remove FastAPI route handlers, documented evaluation entry points, or helpers used only through decorators/tests. |
| `DemoHotspots` | Delete the unused example surface and its self-test. | Preserve real hotspot parsing and rendering. |
| `pandas` and `url_launcher` | Remove if fresh searches still show zero imports. | Regenerate the Flutter lockfile normally; do not hand-edit it. |
| Backup and superseded pointer files | Remove. | Preserve the canonical PRD in `docs/` and the active `mobile/pubspec.yaml`. |

## Phase 1: Repository artifacts, generated output, and unused dependencies

**Goal:** Remove files and dependencies that are not runtime source while proving every active build still regenerates or resolves what it needs.

### Tasks

- [x] **Task 1.1: Record the execution baseline.**
  Capture `git status --short`, the current commit, current branch, installed Python/Flutter/Node/PlatformIO commands, and the relevant baseline test results.
- [x] **Task 1.2: Verify and remove the legacy Arduino web bundle.**
  Search firmware and documentation for `LittleFS`, `SPIFFS`, static file serving, `arduino/data`, and each bundled HTML entry point.
  Delete `arduino/data/` only if no active sketch or build process packages it.
- [x] **Task 1.3: Stop tracking generated localization Dart.**
  Add the exact generated `mobile/lib/l10n/app_localizations*.dart` paths or pattern to `mobile/.gitignore`.
  Remove those generated files from Git, run `flutter gen-l10n`, and confirm the regenerated ignored files allow analysis, tests, and a web build to succeed.
  Do not change any ARB translation or generated content in this phase.
- [x] **Task 1.4: Remove unused dependencies.**
  Re-run repository-wide import searches for `pandas` and `url_launcher`.
  Remove `pandas` from `backend/requirements.txt` and `url_launcher` from `mobile/pubspec.yaml` only if both remain unused.
  Run `flutter pub get` so `mobile/pubspec.lock` reflects the manifest rather than editing the lockfile manually.
  Update current dependency documentation that claims either package is installed, but leave historical implementation-plan requirements unchanged.
- [x] **Task 1.5: Remove obvious repository leftovers.**
  Delete `mobile/pubspec.yaml.bak` and `web/Aqone_PRD (2).md` after confirming no current link targets them.
  Keep `docs/Aqone_PRD (2).md` as the canonical PRD.
- [x] **Task 1.6: Resolve the checked-in APK safely.**
  Search README files, scripts, release instructions, and current external releases for `mobile/releases/aqone-release.apk` and its checksum.
  If a verified external copy already exists, delete the tracked APK and checksum and point current download documentation at that release.
  If no external copy exists, leave both files untouched, report the hold at the hard stop, and request separate authorization before publishing or removing the only distribution artifact.
  Never rewrite repository history to purge earlier APK blobs under this plan.

### Verification Gate

- [x] From `backend`, run `python -m pytest -q` and record exact pass/fail output.
- [x] From `backend`, run `python -m ruff check .` and record exact output.
- [x] From `mobile`, run `flutter gen-l10n`, `flutter test`, `flutter analyze`, and `flutter build web`.
- [x] From the repository root, run `node --test web/test/*.test.js`.
- [x] From the repository root, run `pio run -d firmware` when PlatformIO is available.
- [x] Confirm `git status --short --ignored` shows regenerated localization files as ignored rather than staged or missing during builds.
- [x] Run `git diff --check`.

### Review Gate (Ponytail)

- [x] No runtime replacement was written for deleted build output or backups.
- [x] No package was added.
- [x] The active dashboard, ARB sources, firmware sketches, and canonical PRD remain present.
- [x] Any retained APK is documented as an intentional authorization hold rather than silently skipped.

### Git Checkpoint

Stage only the Phase 1 paths that actually changed.

```text
git add mobile/.gitignore mobile/lib/l10n/app_localizations.dart mobile/lib/l10n/app_localizations_en.dart mobile/lib/l10n/app_localizations_fil.dart mobile/lib/l10n/app_localizations_akl.dart mobile/pubspec.yaml mobile/pubspec.lock mobile/pubspec.yaml.bak backend/requirements.txt docs/16_QA_DISCLOSURES.md "web/Aqone_PRD (2).md" arduino/data mobile/releases/aqone-release.apk mobile/releases/SHA256SUMS.txt
git commit -m "chore(repo): remove generated and obsolete artifacts"
```

Before committing, remove unchanged, held, or nonexistent paths from the staging command and inspect `git diff --cached --stat`.

### HARD STOP

> **PAUSE HERE.**
> Report every removed and retained artifact, exact dependency changes, test/lint/build output, diff size, and commit hash.
> Ask: "Phase 1 is complete, verified, and committed. Ready to proceed to Phase 2?"
> Do not touch Phase 2 files until the user confirms.

---

## Phase 2: Remove dormant exact-location fishing spots and demo hotspots

**Goal:** Delete the unused exact-point reporting pipeline while preserving the in-scope consented catch-log aggregation and real hotspot surface.

### Tasks

- [x] **Task 2.1: Reconfirm the runtime caller graph.**
  Search mobile source, tests, backend routes, dashboard code, and public contracts for `FishingSpot`, `FishingSpotStore`, `FishingSpotService`, `postFishingSpot`, `/api/spots`, `spotsPath`, and `reportSpot`.
  Confirm no visible UI can create or display an exact-location report and no supported external contract depends on `/api/spots`.
- [x] **Task 2.2: Remove the mobile exact-spot pipeline.**
  Delete the fishing-spot model, store, and service.
  Remove their imports, construction, timers, disposal, backend-client method/result types, config values, and fresh-install table creation.
  Do not drop or erase an existing device table or its rows.
  Do not recreate the separate catch-logging feature as part of this cleanup.
- [x] **Task 2.3: Remove the backend exact-spot route.**
  Delete `backend/app/api/spots.py` and remove its import and router registration from `backend/app/main.py`.
  Keep `backend/migrations/013_fishing_spots.sql` unchanged because deployed migration history is immutable.
- [x] **Task 2.4: Remove the unused demo hotspot surface.**
  Delete `mobile/lib/data/demo_hotspots.dart` and its dedicated test.
  Remove only branches and fields that exist solely to support that unused example surface.
  Keep `HotspotCell`, backend response parsing, `VentureFeeds.hotspots`, map rendering, minimum-reporter privacy behavior, and `/api/public/hotspots` unchanged.
- [x] **Task 2.5: Update current documentation.**
  Remove current references that claim community exact-point reporting is active.
  Retain the canonical language for consented catch logs and coarse aggregated cells.

### Verification Gate

- [x] Search again for every deleted symbol and `/api/spots`; only historical migration or archived documentation references may remain.
- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`.
- [x] From `mobile`, run `flutter test`, `flutter analyze`, and `flutter build web`.
- [x] From the repository root, run `node --test web/test/*.test.js`.
- [x] Verify a fresh mobile database opens successfully and an upgraded database with the old table opens without destructive migration behavior.
- [x] Run `git diff --check`.

### Review Gate (Ponytail)

- [x] No compatibility uploader, placeholder endpoint, replacement service, or speculative migration was added.
- [x] The smallest behavior-preserving path was deletion plus caller cleanup.
- [x] Aggregate hotspot and consent boundaries remain unchanged.

### Git Checkpoint

Stage only the exact changed files.

```text
git add backend/app/main.py backend/app/api/spots.py mobile/lib/main.dart mobile/lib/core/config.dart mobile/lib/data/app_database.dart mobile/lib/data/fishing_spot_store.dart mobile/lib/data/demo_hotspots.dart mobile/lib/models/fishing_spot.dart mobile/lib/services/backend_client.dart mobile/lib/services/fishing_spot_service.dart mobile/test/demo_hotspots_test.dart docs/05_PUBLIC_API.md docs/18_BACKEND_STRUCTURE.md
git commit -m "refactor(spots): remove dormant exact-location pipeline"
```

Do not stage `backend/migrations/013_fishing_spots.sql`.

### HARD STOP

> **PAUSE HERE.**
> Report the caller search, preserved aggregate hotspot path, database upgrade result, tests, diff size, and commit hash.
> Obtain explicit confirmation before Phase 3.

---

## Phase 3: Remove out-of-scope avatar transport while preserving text identity

**Goal:** Keep dispatcher-visible vessel and owner text while removing photo upload, database use, API delivery, and dashboard rendering.

### Tasks

- [x] **Task 3.1: Reconfirm the scope boundary and data flow.**
  Trace the avatar from the local profile picker through `readAvatarBytes`, `registerVesselProfile`, the `vessels.avatar_png` column, active SOS serialization, and dashboard rendering.
  Confirm the text profile fields work independently.
- [x] **Task 3.2: Remove backend avatar transport.**
  Remove the avatar field, base64 decoding, avatar update branches, active-SOS encoding, and response field.
  Keep text profile upsert behavior, validation, and unauthenticated emergency-compatible registration behavior.
  Keep `backend/migrations/028_vessel_avatar.sql` unchanged and do not drop its columns.
- [x] **Task 3.3: Remove mobile upload support.**
  Delete the three `avatar_bytes` conditional files and remove backend-client upload encoding.
  Remove the extra best-effort profile re-push that exists only to carry an avatar, unless it is also required to heal text identity after a direct SOS.
  Preserve the minimal text-profile registration path.
  Keep the local profile photo picker and local display only if they have independent user value and compile without the deleted transport.
- [x] **Task 3.4: Remove dashboard avatar rendering.**
  Remove avatar fields from live SOS mapping, incident rows, drawer markup, and avatar-only CSS.
  Preserve the sender name, boat, license, and phone presentation added by the text-profile feature.
- [x] **Task 3.5: Shrink tests around the retained behavior.**
  Delete avatar-only tests and fixtures.
  Consolidate repetitive fake pools only where the shorter setup still exercises real text-profile and active-feed behavior.
  Keep validation, text upsert, unauthenticated access, and true-owner regression coverage.

### Verification Gate

- [x] Search repository-wide for `avatar_png`, `avatar_updated_at`, `readAvatarBytes`, and backend SOS `avatar` mapping; only the historical migration and intentional local-only profile path may remain.
- [x] From `backend`, run `python -m pytest -q tests/test_vessel_profile.py tests/test_sos_ingest.py tests/test_responder_loop.py`.
- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`.
- [x] From `mobile`, run `flutter test test/sos_service_test.dart test/identity_store_encryption_test.dart test/widget_test.dart`.
- [x] From `mobile`, run `flutter test`, `flutter analyze`, and `flutter build web`.
- [x] From the repository root, run `node --test web/test/*.test.js` and syntax-check every changed dashboard script with `node --check`.
- [x] Run `git diff --check`.

### Review Gate (Ponytail)

- [x] The retained text identity path has one registration implementation and no photo-shaped placeholders.
- [x] No object-storage service, image endpoint, replacement avatar abstraction, or schema rollback was added.
- [x] Emergency SOS delivery remains independent of profile registration success.

### Git Checkpoint

Stage only the avatar transport and directly affected tests/presentation paths.

```text
git add backend/app/api/vessel_profile.py backend/app/api/sos.py backend/tests/test_vessel_profile.py mobile/lib/data/avatar_bytes.dart mobile/lib/data/avatar_bytes_io.dart mobile/lib/data/avatar_bytes_web.dart mobile/lib/services/backend_client.dart mobile/lib/services/sos_service.dart mobile/test/sos_service_test.dart web/css/dashboard.css web/html/dashboard.html web/js/dashboard/dashboard-buoy-health.js web/js/dashboard/dashboard-incidents.js web/js/dashboard/dashboard-live-sos.js web/js/dashboard/dashboard-vessels-alerts.js web/test/dashboard-runtime.test.js
git commit -m "refactor(profile): remove out-of-scope avatar transport"
```

Do not stage `backend/migrations/028_vessel_avatar.sql`.

### HARD STOP

> **PAUSE HERE.**
> Report the preserved text fields, removed photo flow, SOS regression results, diff size, and commit hash.
> Obtain explicit confirmation before Phase 4.

---

## Phase 4: Remove dead dashboard exports and caller-free backend helpers

**Goal:** Delete internal names and helpers with no caller without changing product behavior or introducing a new module system.

### Tasks

- [x] **Task 4.1: Recompute the dashboard export set.**
  Enumerate every `ns.<name> = ...` assignment in `web/js/dashboard/`.
  Search all dashboard scripts, HTML, tests, and inline handlers for each property.
  Delete only assignments with no read outside their defining assignment.
  Keep actual cross-file dependencies and any documented test seam.
- [x] **Task 4.2: Remove redundant dashboard fallbacks only where one security implementation remains guaranteed.**
  Keep one tested HTML-escaping implementation and the existing safe script order.
  Do not replace escaping with raw strings and do not weaken live/demo or freshness fail-safe behavior.
  Do not add ES modules, a bundler, a loader, or a registry.
- [x] **Task 4.3: Reconfirm backend dead helpers.**
  Search source, tests, scripts, and current docs for `_route_path`, `_choose_target_vessel`, `nearest_water_point`, `max_radius_m`, `get_weather_snapshot`, and `_synthetic_weather_snapshot`.
  Account for FastAPI decorators and CLI entry points before classifying anything as dead.
- [x] **Task 4.4: Delete caller-free helpers and their private support state.**
  Remove only confirmed dead functions plus imports, cache variables, and constants used exclusively by them.
  Do not remove documented field-evaluation functions such as `validate_manifest`, `evaluate_drift_track`, or `contour_area_km2` merely because production routes do not call them.
- [x] **Task 4.5: Remove stale documentation claims for deleted helpers.**
  Update current architecture/status documentation only when it claims a deleted helper is operational.
  Leave dated audit records and historical plans intact unless they falsely present themselves as current instructions.

### Verification Gate

- [x] Re-run the namespace-property caller scan and record the final exported property count.
- [x] Re-run repository-wide searches for each deleted backend helper.
- [x] From the repository root, run `node --test web/test/*.test.js`.
- [x] Run `node --check` for every changed JavaScript file.
- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`.
- [x] Run `git diff --check`.

### Review Gate (Ponytail)

- [x] Every deleted export was write-only and every deleted helper had no executable caller.
- [x] No generic module abstraction or replacement helper was introduced.
- [x] Security escaping, failure visibility, and safety claims were not simplified away.

### Git Checkpoint

Stage the exact changed dashboard and backend paths only.

```text
git add web/js/dashboard/dashboard-alarm.js web/js/dashboard/dashboard-ai-ops.js web/js/dashboard/dashboard-buoy-health.js web/js/dashboard/dashboard-core.js web/js/dashboard/dashboard-emergency-advisory.js web/js/dashboard/dashboard-incidents.js web/js/dashboard/dashboard-live-sos.js web/js/dashboard/dashboard-markers.js web/js/dashboard/dashboard-operations-audit.js web/js/dashboard/dashboard-panels.js web/js/dashboard/dashboard-profile-pill.js web/js/dashboard/dashboard-sar.js web/js/dashboard/dashboard-shortcuts-weather.js web/js/dashboard/dashboard-tools.js web/js/dashboard/dashboard-trip-checks.js web/js/dashboard/dashboard-vessels-alerts.js backend/app/ai/trip_profile.py backend/app/ai/drift.py backend/app/demo/scenarios.py backend/app/geo.py backend/app/simulation/generator.py docs/08_DEMO_AND_STATUS.md docs/18_BACKEND_STRUCTURE.md
git commit -m "refactor(core): delete unused exports and helpers"
```

If a test file changes to preserve a real regression assertion, stage that exact test path separately after inspecting its diff.

### HARD STOP

> **PAUSE HERE.**
> Report the deleted export/helper list, exact verification output, diff size, and commit hash.
> Obtain explicit confirmation before Phase 5.

---

## Phase 5: Full regression verification and cleanup record

**Goal:** Prove the combined deletion set is reproducible, behavior-preserving, and accurately documented.

### Tasks

- [x] **Task 5.1: Review the complete cleanup range.**
  Compare the Phase 1 base commit with `HEAD`.
  Confirm only approved cleanup paths changed and no migration, secret, raw field data, model artifact, generated localization output, or unrelated teammate work was committed.
- [x] **Task 5.2: Verify fresh regeneration and installation.**
  Confirm backend dependencies install without `pandas` when it was removed.
  Confirm `flutter pub get` and `flutter gen-l10n` recreate every ignored generated localization file from the checked-in ARB sources.
- [x] **Task 5.3: Run the full applicable checks.**
  Run backend tests/lint, mobile tests/analyze/web build, web tests/syntax checks, firmware builds, and `git diff --check`.
  Record any unavailable hardware or environment check honestly.
- [x] **Task 5.4: Run the final Ponytail audit.**
  Recheck all ten original findings.
  Report remaining items only when a concrete authorization hold or verified runtime dependency prevented deletion.
- [x] **Task 5.5: Record measured impact.**
  Record exact lines/files/dependencies removed from the committed diff.
  Record current working-tree binary reduction separately from historical Git pack size.
  Do not claim Git history shrinkage without an explicitly authorized history rewrite.
- [x] **Task 5.6: Update this handoff.**
  Mark completed tasks and phases, add commit hashes and verification evidence, and set status to complete only when no required local work remains.

### Verification Gate

- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`.
- [x] From `mobile`, run `flutter pub get`, `flutter gen-l10n`, `flutter test`, `flutter analyze`, and `flutter build web`.
- [x] From the repository root, run `node --test web/test/*.test.js` and syntax-check all active dashboard JavaScript files.
- [x] From the repository root, run `pio run -d firmware` when PlatformIO is available (PlatformIO not installed on Windows environment; documented).
- [x] Run `git status --short`, `git diff --check`, and a repository-wide search for all deleted symbols.
- [x] Confirm the current branch contains no generated localization files or build artifacts.

### Review Gate (Ponytail)

- [x] The final tree is smaller without a replacement framework.
- [x] No new dependency, compatibility shim, speculative abstraction, or duplicate source of truth was introduced.
- [x] The SOS path, delivery states, responder acknowledgement, text identity, real hotspot surface, and two firmware roles remain intact.

### Git Checkpoint

Stage only this plan and any directly necessary current documentation updates.

```text
git add docs/PONYTAIL_AUDIT_CLEANUP_IMPLEMENTATION_PLAN.md IMPLEMENTATION_PLAN.md
git commit -m "docs(maintenance): record ponytail cleanup verification"
```

Do not create an empty commit when the verification record was already included in the Phase 4 commit.

### HARD STOP

> **PAUSE HERE.**
> Report all phase commits, exact net deletion, retained findings with reasons, and full verification output.
> Hand the branch back for user review.
> Do not deploy, merge, publish releases, or rewrite history automatically.

## Expected outcome

- Generated localization output is reproducible but not tracked.
- Obsolete Arduino web assets, backups, and superseded pointers are gone.
- Dormant exact fishing-spot reporting and unused demo hotspots are gone.
- Out-of-scope avatar transport is gone while text sender identity remains.
- Write-only dashboard exports and caller-free backend helpers are gone.
- Unused dependency declarations are gone.
- The checked-in APK is either safely moved out of the repository through a separately authorized release workflow or explicitly retained with a documented blocker.
- Historical migrations and existing local/database data are preserved.
- Every phase is independently tested, committed, and approved before the next begins.

---

## Final Verification and Impact Record

### Phase Commits

- **Phase 1:** `85d75a4` `chore(repo): remove generated and obsolete artifacts`
- **Phase 2:** `0b21ceb` `refactor(spots): remove dormant exact-location pipeline`
- **Phase 3:** `b9357c2` `refactor(profile): remove out-of-scope avatar transport`
- **Phase 4:** `fe19b39` `refactor(core): delete unused exports and helpers`
- **Phase 5:** This documentation and handoff record commit.

### Measured Impact (Net Deletion)

- **Total Files Changed:** 65 files across the repository.
- **Line Impact:** 31 insertions(+), 14,312 deletions(-) (net **-14,281 lines**).
- **Binary Reduction:** 9 deleted legacy binary images (~129.5 KB) removed from active working tree without historical rewrite.
- **Dependencies Removed:** `pandas` removed from `backend/requirements.txt`; `url_launcher` removed from `mobile/pubspec.yaml` and resolved in `pubspec.lock`.

### Findings Status

1. *Legacy `arduino/data` web bundle:* Fully removed.
2. *Generated Flutter localization Dart:* Untracked and ignored via `.gitignore`; regenerated on demand via `flutter gen-l10n`.
3. *Exact-location fishing spots:* Removed dormant runtime pipeline, stores, models, and routes; preserved aggregate `/api/public/hotspots` and historical migration `013_fishing_spots.sql`.
4. *Avatar upload and dispatcher delivery:* Removed photo upload and dispatcher transport; preserved text vessel identity and historical migration `028_vessel_avatar.sql`.
5. *Checked-in release APK:* Retained under documented blocker / authorization hold (no external distribution release established yet; no history rewrite authorized).
6. *Dashboard namespace exports:* Removed 88 dead `ns.*` exports across 12 files; 107 active properties retained with active cross-file or test callers.
7. *Caller-free backend helpers:* Removed 5 dead helpers (`_route_path`, `_choose_target_vessel`, `nearest_water_point`, `max_radius_m`, `get_weather_snapshot` + unused cache/`httpx` import).
8. *`DemoHotspots`:* Removed example surface and dedicated tests; preserved real hotspot parser.
9. *`pandas` and `url_launcher`:* Removed from backend and mobile requirements/lockfile with 0 remaining imports.
10. *Backup and superseded pointer files:* Removed `mobile/pubspec.yaml.bak` and `web/Aqone_PRD (2).md`.

### Full Test and Lint Suite Verification

- **Backend:** `pytest -q` passed (371 passed, 5 skipped, 1 xfailed); `ruff check .` clean (all checks passed).
- **Mobile:** `flutter test` passed (257 passed); `flutter analyze` clean (0 issues found); `flutter build web` passed (code 0, 65.9s).
- **Web Dashboard:** `node --test web/test/*.test.js` passed (148 passed, 0 failed); `node --check` clean across all 16 `web/js/dashboard/*.js` scripts.
- **Firmware:** PlatformIO (`pio`) not installed in local Windows environment; hardware verification skipped per protocol.
- **Repository Hygiene:** `git diff --check` clean. Deployed migrations, secrets, and raw sensor data remain untouched.
