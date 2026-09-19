# Implementation Plan: Documentation organization

> **Status:** Complete — all four phases verified and committed
> **Target Branch:** `codex/web-audit-remediation`
> **Test Command:** repository reference scan plus Markdown link validation
> **Lint/Check Command:** `git diff --check`
> **Prepared:** 2026-09-14
> **Owner:** Codex with team review

## Overview

Reduce the visual load of `docs/` while preserving stable contract paths and the permanent numbered project record.
Use an index first, then move only dated audits and verified unreferenced completed plans.

## Phase 1: Index and migration ledger

**Goal:** Make the intended taxonomy discoverable without changing existing paths.

- [x] Add `docs/SPEC_INDEX.md` for the Gemini entry point and contributor navigation.
- [x] Record lifecycle-based move rules rather than inferring status from numeric ranges.
- [x] Preserve `docs/README.md` as the detailed naming and status register.

### Verification Gate

- [x] Confirm every link in `SPEC_INDEX.md` resolves.
- [x] Run `git diff --check`.

### Review Gate (Ponytail)

- [x] Reuse the existing documentation register; do not create a second taxonomy system.
- [x] Add no dependency or custom link-checking framework.

### Git Checkpoint

```powershell
git add docs/SPEC_INDEX.md docs/48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md
git commit -m "docs: add documentation organization index"
```

### Hard Stop

Phase 1 is complete and committed.
Wait for explicit approval before moving audit or plan files.

## Phase 2: Move dated audits

**Goal:** Move only dated audit and verification records into `docs/audits/`.

- [x] Inventory every repository reference to each selected file.
- [x] Create `docs/audits/` and move only files with updated links.
- [x] Update README navigation and audit cross-links.
- [x] Run the reference scan and Markdown link checks.

### Git Checkpoint

```powershell
git add docs README.md GEMINI.md
git commit -m "docs: organize dated audit records"
```

### Hard Stop

Phase 2 is complete and committed.
Wait for explicit approval before archiving completed plans.

## Phase 3: Archive completed plans

**Goal:** Move only completed, unreferenced plans into `docs/archive/plans/`.

- [x] Check each candidate header and repository reference.
- [x] Leave active plans and referenced contract/history documents in place.
- [x] Update links and the documentation register.
- [x] Run the reference scan and Markdown link checks.

### Verification Gate

- [x] Confirm the archived plans have `COMPLETE` headers.
- [x] Confirm no repository path reference points to the old locations.
- [x] Run `git diff --check`.

### Review Gate (Ponytail)

- [x] Move only the two merged, unreferenced plans; retain unresolved or referenced plans in place.
- [x] Add no dependency, archive wrapper, or duplicate index.

### Git Checkpoint

```powershell
git add docs README.md AGENTS.md GEMINI.md
git commit -m "docs: archive completed plans"
```

### Hard Stop

Phase 3 is complete and committed.
Wait for explicit approval before final verification.

## Phase 4: Final verification

**Goal:** Confirm the new layout is navigable and no active consumer points at an old path.

- [x] Verify `GEMINI.md`, `AGENTS.md`, root `README.md`, code comments, tests, and all moved documents.
- [x] Run `git diff --check` and the final repository reference scan.
- [x] Record the final moved-file list and any intentionally retained root records.

### Verification Results

- No active repository consumer points to either pre-archive path; the final moved-file ledger below is the only intentional historical mention.
- `GEMINI.md`, `AGENTS.md`, root `README.md`, `docs/README.md`, and `docs/SPEC_INDEX.md` point to the current navigation paths.
- Stable contracts `00`–`08`, `21`, and `22` remain at their required root paths.
- The two archived plans have `COMPLETE` headers and no live consumers of their former paths.
- Root records intentionally retained: `09`, `11`–`43`, `46`–`48`, `WEB_REMEDIATION_IMPLEMENTATION_PLAN.md`, the canonical PRD, and foundation/reference records.
- `git diff --check` passes and the working tree is clean before this checkpoint.

### Final Moved Files

- `docs/44_DASHBOARD_LAYOUT_REDESIGN_IMPLEMENTATION_PLAN.md` → `docs/archive/plans/44_DASHBOARD_LAYOUT_REDESIGN_IMPLEMENTATION_PLAN.md`
- `docs/45_DASHBOARD_LOGIN_BYPASS_IMPLEMENTATION_PLAN.md` → `docs/archive/plans/45_DASHBOARD_LOGIN_BYPASS_IMPLEMENTATION_PLAN.md`

### Git Checkpoint

```powershell
git add docs README.md AGENTS.md GEMINI.md
git commit -m "docs: verify organized documentation tree"
```
