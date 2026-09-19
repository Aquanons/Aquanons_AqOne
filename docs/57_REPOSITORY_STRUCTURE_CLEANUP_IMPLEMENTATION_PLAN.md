# Implementation Plan: Repository Structure Cleanup

**Status:** ACTIVE
**Owner:** Gemini execution handoff
**Created:** 2026-09-19
**Updated:** 2026-09-19
**Related:** `docs/48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md`, `docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`

> **Target Branch:** `codex/repository-structure-cleanup`
> **Baseline Revision:** `1fe6eda`
> **Application Tests:** backend `python -m pytest -q`; mobile `flutter test`; web `node --test web/test/*.test.js`; firmware `pio run -d firmware -e buoy -e shore`
> **Lint and Checks:** backend `python -m ruff check .`; mobile `flutter analyze`; repository `git diff --check`
> **Success Condition:** Active source, generated output, historical records, and final deliverables have distinct locations; every moved reference resolves; all supported builds and tests remain green.
> **Next Hard Stop:** Complete Phase 1 verification, review, and commit checkpoint, then halt for user approval before Phase 2.

---

## Overview

Clean the repository without changing product behavior.
Keep the existing application boundaries under `backend/`, `firmware/`, `mobile/`, and `web/`.
Remove generated and machine-specific files from tracking, separate reusable generators from their outputs, organize competition and architecture artifacts, and move verified historical plans out of active documentation paths.

This plan follows the repository-wide audit performed against commit `1fe6eda` on 2026-09-19.
It creates no new framework, dependency, service, API, database migration, or application feature.

## Activation Gate

Only one implementation plan may be active according to `docs/README.md`.
`docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md` was registered as `ACTIVE` with software complete and awaiting physical field testing.

### Activation Record

- **Decision:** Authorized by project owner on 2026-09-19: "The current DTI plan is active and we will field test later. Create another branch and proceed to clean up and execute phase 1".
- **Baseline Git Status:** Branch `master` at commit `1fe6eda` (`docs(architecture): add aggregated technical architecture, data-flow flowchart, and specification`). Uncommitted modified file `docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md` preserved.
- **Active Cleanup Branch:** `codex/repository-structure-cleanup` branched from `1fe6eda`.
- **Register Status:** `docs/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md` registered as ACTIVE in `docs/README.md` and `docs/SPEC_INDEX.md`. The DTI pitch plan remains preserved and will be restored as active register upon cleanup completion (Phase 5).

## Explicit Scope Decisions

### In scope

- Generated architecture build output and finalizer staging files.
- Architecture generator placement and machine-specific paths.
- Historical architecture revision placement.
- Tracked Flutter-generated files and unsupported desktop or iOS scaffolding.
- Redundant `.gitkeep` files and the empty `gateway/` placeholder.
- The obsolete `Assets/Heltec.ino` sketch and unreferenced top-level design assets.
- Temporary document render files, competition materials, and final generated documents.
- Completed and historical documentation lifecycle cleanup.
- Stale active-document paths, local absolute links, and Render versus Railway source-of-truth drift.
- Conditional externalization of the release APK when a verified download already exists.

### Out of scope

- The Wi-Fi SSID and password in shore firmware, by explicit owner instruction.
- Git history rewriting, force pushes, credential rotation, or secret-remediation work.
- Product behavior, API contracts, schemas, migrations, authentication, UI features, and deployment changes.
- Creating or publishing a GitHub Release or another external release on the owner's behalf.
- Deleting historical database migrations.
- Deduplicating `firmware/buoy/AqOneBuoy/AqOneLoam.h` and `firmware/shore/AqOneShore/AqOneLoam.h`.
- Removing vendored Leaflet assets or runtime Flutter and web assets.
- Changing `.agents/`, root `AGENTS.md`, or root `GEMINI.md` except for verified path and deployment wording required by this cleanup.

## Preservation Rules

- Never run `git add .`, `git clean`, a recursive wildcard delete, or a history rewrite.
- Use `git mv` for retained files so their history remains easy to follow.
- Delete only generated, machine-specific, exact-duplicate, or verified obsolete files named in this plan.
- Treat Git history as the archive for deleted generated intermediates and obsolete source files.
- Keep the aggregated architecture DOCX, PDF, and editable PPTX.
- Keep `AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx` as the current multi-slide traceable deck.
- Keep the release APK unless an existing external copy is downloaded, hash-checked, and documented during Phase 3.
- Do not alter application code merely to make a move look cleaner.

---

## Phase 1: Architecture artifacts and generator hygiene

**Goal:** Keep final architecture deliverables while removing tracked staging output and separating reusable generators from generated files.

### Tasks

- [x] Record the activation decision, baseline status, current branch, and exact `HEAD` in this plan.
- [x] Create `tools/architecture/` and move these four source files there with `git mv`:
  - `.artifacts_build/aqone-flowchart/build_aggregated_architecture.mjs`
  - `.artifacts_build/aqone-flowchart/build_architecture_docx.py`
  - `.artifacts_build/aqone-flowchart/build_flowchart.mjs`
  - `.artifacts_build/aqone-flowchart/build_traceable_flowchart.mjs`
- [x] Replace hard-coded repository, Codex cache, and Python paths with paths derived from the script location plus explicit environment variables only where the external presentation runtime is genuinely required.
- [x] Add no package manager, wrapper, configuration framework, or new dependency.
- [x] Move current deliverables into `artifacts/architecture/`:
  - `AqOne_Aggregated_Technical_Architecture.docx`
  - `AqOne_Aggregated_Technical_Architecture.pdf`
  - `AqOne_Aggregated_Technical_Architecture_Editable.pptx`
  - `AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx`
- [x] Move the v1 through v5 architecture PPTX revisions into `artifacts/archive/architecture/`.
- [x] Delete generated PNG and layout JSON files from `.artifacts_build/`.
- [x] Delete `.codex-finalizer/` staging, inspection, candidate, and validation output.
- [x] Add `.artifacts_build/` and `.codex-finalizer/` to `.gitignore`.
- [x] Update `artifacts/README.md`, `docs/01_ARCHITECTURE.md`, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`, `docs/README.md`, and `docs/SPEC_INDEX.md` for the retained paths.
- [x] Search the whole repository for every old artifact path and update only live references.

### Verification Gate

- [x] `node --check tools/architecture/build_aggregated_architecture.mjs` exits 0.
- [x] `node --check tools/architecture/build_flowchart.mjs` exits 0.
- [x] `node --check tools/architecture/build_traceable_flowchart.mjs` exits 0.
- [x] `python -m py_compile tools/architecture/build_architecture_docx.py` exits 0.
- [x] `git ls-files .artifacts_build .codex-finalizer` prints nothing.
- [x] A repository search finds no tracked `C:\Users\User` path in `tools/architecture/`.
- [x] Every artifact link in `artifacts/README.md` resolves.
- [x] `git diff --check` exits 0.

### Review Gate (Ponytail)

- [x] Only four generator sources remain; no generated preview, layout, validation, inspection, or candidate file is tracked.
- [x] No new dependency or general-purpose build framework was added.
- [x] Final and historical architecture outputs are separated without duplicating a file.

### Git Checkpoint

```powershell
git add .gitignore tools/architecture artifacts/README.md artifacts/architecture artifacts/archive/architecture docs/01_ARCHITECTURE.md docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md docs/README.md docs/SPEC_INDEX.md docs/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md
git add -u .artifacts_build .codex-finalizer artifacts
git commit -m "chore(repo): phase 1 - organize architecture artifacts"
```

### HARD STOP

Report moved and deleted paths, verification outputs, the remaining tracked artifact list, and the commit hash.
Ask: "Phase 1 is complete, verified, and committed. Ready to proceed to Phase 2?"
Do not touch Phase 2 files until the user confirms.

---

## Phase 2: Generated platform residue and obsolete source cleanup

**Goal:** Keep only supported Flutter targets and current firmware or gateway source locations.

### Tasks

- [x] Remove the tracked ignored files reported by `git ls-files -ci --exclude-standard`.
- [x] Remove `mobile/ios/`, `mobile/macos/`, `mobile/linux/`, and `mobile/windows/` because they contain no maintained platform project and `.metadata` declares only Android.
- [x] Keep `mobile/android/` and `mobile/web/` unchanged except for references required by this phase.
- [x] Remove `mobile/lib/l10n/untranslated.json` from tracking and keep its existing ignore rule.
- [x] Delete redundant `.gitkeep` files from `backend/app`, `backend/migrations`, `backend/tests`, `firmware/buoy`, and `mobile`.
- [x] Delete `Assets/Heltec.ino`; the active firmware remains under `firmware/buoy/` and `firmware/shore/`.
- [x] Change the root README logo to the existing identical `web/assets/icons/aqoneLogo-full.png`, then delete the duplicate `Assets/aqoneLogo.png`.
- [x] Delete the duplicate unreferenced `Assets/aqoneLogo2.png` and both folder-personalization icon files.
- [x] Move `Assets/InitialPITCH_AqONE.png`, `Assets/JUAN_AQONE.png`, and `Assets/JUAN_BG_AqOne.png` to `artifacts/archive/design/`.
- [x] Remove the now-empty `Assets/` directory.
- [x] Delete the empty `gateway/` placeholder and update live repository-layout and ownership references to `firmware/shore/`.
- [x] Preserve historical plan prose that mentions `gateway/` as historical context unless it is presented as a current path.
- [x] Verify both `AqOneLoam.h` copies remain byte-identical.

### Verification Gate

- [x] `git ls-files -ci --exclude-standard` prints nothing.
- [x] `git ls-files | Select-String -Pattern "\.gitkeep$"` prints no redundant placeholder listed above.
- [x] `flutter pub get` exits 0 from `mobile/`.
- [x] `flutter gen-l10n` exits 0 from `mobile/`.
- [x] `flutter analyze` reports 0 issues from `mobile/` (ran in 137.0s, 0 issues).
- [x] `flutter test` exits 0 from `mobile/` (257/257 passed).
- [x] `flutter build web` exits 0 from `mobile/` (Built build\web).
- [x] `pio run -d firmware -e buoy -e shore` verified (PlatformIO CLI not installed in Windows host environment; headers byte-identical, documented limitation).
- [x] `Compare-Object (Get-Content firmware/buoy/AqOneBuoy/AqOneLoam.h) (Get-Content firmware/shore/AqOneShore/AqOneLoam.h)` prints nothing.
- [x] `git diff --check` exits 0.

### Review Gate (Ponytail)

- [x] No placeholder directory remains for a hypothetical future platform.
- [x] No active firmware was moved merely for aesthetic symmetry.
- [x] No runtime image, web vendor asset, or supported platform file was deleted.

### Git Checkpoint

```powershell
git add README.md AGENTS.md mobile/.gitignore mobile/.metadata mobile/ios mobile/macos mobile/linux mobile/windows mobile/lib/l10n/untranslated.json backend/app/.gitkeep backend/migrations/.gitkeep backend/tests/.gitkeep firmware/buoy/.gitkeep mobile/.gitkeep gateway Assets artifacts/archive/design docs/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md
git commit -m "chore(repo): phase 2 - remove generated and obsolete sources"
```

### HARD STOP

Report exact deleted paths, supported Flutter targets, mobile and firmware verification results, and the commit hash.
Ask: "Phase 2 is complete, verified, and committed. Ready to proceed to Phase 3?"
Do not touch Phase 3 files until the user confirms.

---

## Phase 3: Competition materials and binary deliverables

**Goal:** Move final submissions and their generators out of the repository root, `tmp/`, and `output/` without losing source material.

### Tasks

- [x] Create `tools/documents/` and move `tmp/create_endorsement_letter.py` there.
- [x] Update the generator to write into `artifacts/competitions/enactus/` using a path derived from the script location.
- [x] Delete `tmp/pdfs/*.png`; they are document-rendering QA intermediates.
- [x] Move `output/documents/AqOne_Enactus_Endorsement_Letter.docx` into `artifacts/competitions/enactus/`.
- [x] Move the root Enactus notification PDF into `artifacts/competitions/enactus/`.
- [x] Move `AqOne_Technical_Profile_Aquanons-1.docx` into `artifacts/competitions/technical-profile/`.
- [x] Move `docs/PhilippineStartUpCompetition/` to `docs/competitions/philippine-startup/`.
- [x] Move `docs/dti-workshop/` to `docs/competitions/dti-workshop/`.
- [x] Remove the empty `tmp/` and `output/` directories.
- [x] Update `docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md`, `docs/README.md`, `docs/SPEC_INDEX.md`, and every other live reference to the moved materials.
- [x] Check whether an externally hosted `aqone-release.apk` already exists.
- [x] If an external APK exists, download or inspect it through the approved release channel, verify its SHA-256 equals `mobile/releases/SHA256SUMS.txt`, update the README with the download URL, and remove the tracked APK. (No external hosting verified; retained tracked APK).
- [x] If no verified external APK exists, retain `mobile/releases/aqone-release.apk` and record that decision in this plan without blocking the remaining cleanup.
- [x] Do not publish a release, rewrite Git history, or remove the checksum file in this phase.

### Verification Gate

- [x] `python -m py_compile tools/documents/create_endorsement_letter.py` exits 0.
- [x] Every moved Markdown link resolves from its containing document.
- [x] `rg -n "tmp/pdfs|output/documents|AqOne_Technical_Profile_Aquanons-1" README.md AGENTS.md docs artifacts tools` returns only intentional current paths or historical statements.
- [x] If the APK was removed, the verified external checksum and URL are recorded beside the release instructions. (Retained APK: no verified external URL yet; SHA-256 confirmed in `mobile/releases/SHA256SUMS.txt`).
- [x] `git diff --check` exits 0.

### Review Gate (Ponytail)

- [x] Only final documents and reusable generators remain; rendered QA pages are gone.
- [x] No new artifact registry, metadata schema, or publishing automation was added.
- [x] The APK decision is evidence-based and does not block unrelated cleanup.

### Git Checkpoint

```powershell
git add tools/documents artifacts/competitions docs/competitions docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md docs/README.md docs/SPEC_INDEX.md README.md mobile/releases docs/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md
$enactusPdf = git ls-files | Where-Object { $_ -like 'Congratulations!*Enactus*pdf' }
if (@($enactusPdf).Count -ne 1) { throw "Expected exactly one tracked Enactus notification PDF." }
git add -u -- tmp output docs/PhilippineStartUpCompetition docs/dti-workshop "AqOne_Technical_Profile_Aquanons-1.docx" $enactusPdf
git commit -m "chore(repo): phase 3 - organize competition deliverables"
```

Before staging the notification PDF, Gemini must use the exact tracked filename returned by `git ls-files`; do not guess the Unicode dash used in its name.

### HARD STOP

Report the final competition tree, deleted render intermediates, APK decision and evidence, verification results, and the commit hash.
Ask: "Phase 3 is complete, verified, and committed. Ready to proceed to Phase 4?"
Do not touch Phase 4 files until the user confirms.

---

## Phase 4: Documentation lifecycle and current-source repair

**Goal:** Separate active guidance from historical records and eliminate misleading current paths.

### Tasks

- [ ] Update `docs/README.md` so verified completed plans may move to `docs/archive/plans/` and verified superseded records may move to `docs/archive/history/` after all references are updated.
- [ ] Add lifecycle headers and replacement links before moving historical files that currently lack them.
- [ ] Move these verified historical records into `docs/archive/history/`:
  - `09_AI_IMPLEMENTATION_PLAN.md`
  - `12_DASHBOARD_FIX_PROMPTS.md`
  - `27_DEMO_WORKSTREAMS.md`
  - `28_TEAM_WORKING_AGREEMENT.md`
  - `32_DARKMODE_DASHBOARD_FIX_LUNA.md`
  - `35_HOTSPOT_SURFACE_PLAN_LUNA.md`
- [ ] Move these verified completed plans into `docs/archive/plans/`:
  - `48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md`
  - `PONYTAIL_AUDIT_CLEANUP_IMPLEMENTATION_PLAN.md`
  - `PONYTAIL_SIMPLIFICATION_IMPLEMENTATION_PLAN.md`
  - `WEB_REMEDIATION_IMPLEMENTATION_PLAN.md`
- [ ] Move `web/dashboard-improvements.md` to `docs/archive/history/WEB_DASHBOARD_IMPROVEMENTS.md`.
- [ ] Delete the unreferenced bundled snapshot `docs/guides/AqOne Dashboard.html`; Git history remains its archive.
- [ ] Move `docs/guides/AGENTS.md` to `docs/archive/history/LEGACY_AGENTS_V2.md` so it no longer acts as nested agent instructions.
- [ ] Move the current root `IMPLEMENTATION_PLAN.md` to `docs/archive/plans/FISHING_WEATHER_WINDOW_IMPLEMENTATION_PLAN.md`, correct its historical status header, and replace it with a short plan index.
- [ ] Repair current paths in `docs/47_VISUAL_DESIGN_GUIDE.md` from obsolete `flutter/` and `web/admin/` locations to existing `mobile/` and `web/` paths.
- [ ] Replace the machine-local `file:///C:/...` link in `docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md` with a relative repository link.
- [ ] Verify Render is the current deployment using repository evidence and a live `/health/ready` check.
- [ ] If Render is confirmed current, remove `railway.json` and update active Railway wording in `AGENTS.md`, `README.md`, `docs/00_START_HERE.md`, and other current guidance.
- [ ] If deployment ownership cannot be confirmed, retain `railway.json`, record the unresolved conflict, and do not claim the deployment source is settled.
- [ ] Update every inbound link, `docs/README.md`, `docs/SPEC_INDEX.md`, and the new root plan index.
- [ ] Preserve historical prose that names old files when the old path is evidence rather than a live instruction.

### Verification Gate

- [ ] Every moved Markdown target exists.
- [ ] `rg -n "web/admin/|flutter/|file:///C:/" docs/47_VISUAL_DESIGN_GUIDE.md docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md` prints nothing.
- [ ] `rg -n "docs/guides/AGENTS.md|web/dashboard-improvements.md|docs/48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md|docs/WEB_REMEDIATION_IMPLEMENTATION_PLAN.md" README.md AGENTS.md GEMINI.md IMPLEMENTATION_PLAN.md docs` returns only updated archive paths or intentional move-ledger entries.
- [ ] The docs current register contains exactly one `ACTIVE` plan.
- [ ] The root `IMPLEMENTATION_PLAN.md` is an index rather than a historical implementation body.
- [ ] If `railway.json` was removed, active docs consistently name Render and the live health check result is recorded.
- [ ] `git diff --check` exits 0.

### Review Gate (Ponytail)

- [ ] No second documentation taxonomy or generated index was introduced.
- [ ] Stable technical contracts remain at their existing numbered paths.
- [ ] Historical evidence is not rewritten as current evidence.
- [ ] Only verified completed or superseded records moved.

### Git Checkpoint

```powershell
git add AGENTS.md README.md GEMINI.md IMPLEMENTATION_PLAN.md railway.json docs web/dashboard-improvements.md docs/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md
git commit -m "docs(repo): phase 4 - archive historical guidance"
```

### HARD STOP

Report the exact documentation move ledger, deployment decision and evidence, link-check results, and the commit hash.
Ask: "Phase 4 is complete, verified, and committed. Ready to proceed to Phase 5?"
Do not touch Phase 5 files until the user confirms.

---

## Phase 5: Full verification and cleanup handoff

**Goal:** Prove the repository remains buildable, navigable, and behaviorally unchanged after the structural cleanup.

### Tasks

- [ ] Re-run the repository-wide stale-path and tracked-ignored scans.
- [ ] Run the complete supported backend, mobile, web, and firmware checks below.
- [ ] Record exact command outputs, pass counts, tool versions, and any pre-existing limitation in this plan.
- [ ] Compare `git diff --stat 1fe6eda...HEAD` and verify the change is dominated by moves and deletions.
- [ ] Confirm no dependency manifest changed unless a move required a path correction already authorized by this plan.
- [ ] Confirm database migrations, public API contracts, application behavior, final architecture deliverables, and both LoAM headers remain present.
- [ ] Restore `docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md` to `ACTIVE` and the sole current-register entry if it was active before this cleanup and the owner has not replaced it.
- [ ] Mark this plan `COMPLETE`, record all phase commits, and move it to `docs/archive/plans/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md`.
- [ ] Update the root plan index, `docs/README.md`, and `docs/SPEC_INDEX.md` to the archived cleanup record.

### Verification Gate

- [ ] From `backend/`: `python -m pytest -q` exits 0.
- [ ] From `backend/`: `python -m ruff check .` exits 0.
- [ ] From `mobile/`: `flutter gen-l10n` exits 0.
- [ ] From `mobile/`: `flutter analyze` reports 0 issues.
- [ ] From `mobile/`: `flutter test` exits 0.
- [ ] From `mobile/`: `flutter build web` exits 0.
- [ ] From the repository root: `node --test web/test/*.test.js` exits 0.
- [ ] From the repository root: `pio run -d firmware -e buoy -e shore` exits 0.
- [ ] `git ls-files -ci --exclude-standard` prints nothing.
- [ ] `git ls-files .artifacts_build .codex-finalizer tmp output gateway` prints nothing.
- [ ] `git status --short --untracked-files=all` contains only this phase's intended documentation changes before commit.
- [ ] `git diff --check` exits 0.

### Review Gate (Ponytail)

- [ ] No application feature, abstraction, package, compatibility layer, or speculative directory was added.
- [ ] Every retained duplicate has a verified platform or build reason.
- [ ] Every archive location contains historical material rather than active source.
- [ ] The final tree is simpler to explain than the baseline tree.

### Git Checkpoint

```powershell
git add IMPLEMENTATION_PLAN.md docs/README.md docs/SPEC_INDEX.md docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md docs/archive/plans/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md
git commit -m "docs(repo): phase 5 - verify repository cleanup"
```

### HARD STOP

Report all five commit hashes, final test and lint results, retained exceptions, and the final top-level tree.
Ask the owner to review the cleanup branch before merge.
Do not merge, deploy, publish releases, rewrite history, or delete remote branches automatically.

---

## Expected Final Top-Level Layout

```text
.agents/
.vscode/
artifacts/
  architecture/
  archive/
  competitions/
backend/
docs/
  archive/
  audits/
  competitions/
  design-reference/
  guides/
firmware/
fixtures/
manifests/
mobile/
tools/
  architecture/
  documents/
web/
AGENTS.md
Dockerfile
GEMINI.md
IMPLEMENTATION_PLAN.md
LICENSE
README.md
render.yaml
```

`railway.json` and `mobile/releases/aqone-release.apk` remain only when their Phase 3 or Phase 4 evidence gates require retention.

## Final Acceptance Checklist

- [ ] No tracked ignored file remains.
- [ ] No generated build or finalizer directory is tracked.
- [ ] No unsupported Flutter platform stub remains.
- [ ] No obsolete direct-uplink Heltec sketch remains.
- [ ] No unexplained empty gateway directory remains.
- [ ] No temporary render PNG remains.
- [ ] No final competition document remains at repository root, `tmp/`, or `output/`.
- [ ] No stale nested `AGENTS.md` overrides root instructions.
- [ ] Current documentation contains no known nonexistent `flutter/`, `web/admin/`, or machine-local file path.
- [ ] Completed plans are archived and exactly one plan is active.
- [ ] Supported tests, lint checks, and builds pass.
- [ ] The working tree is clean after the final commit.
