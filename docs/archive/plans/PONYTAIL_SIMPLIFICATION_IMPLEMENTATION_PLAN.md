# Implementation Plan: Gemini Ponytail Simplification Pass

> **Status:** Phase 1, Phase 2, and Phase 3 complete; all 6 Ponytail findings resolved; verification gates passed.  
> **Target Branch:** `codex/ai-accuracy` after Gemini inspects the current checkout and user changes.  
> **Test Command:** Backend: `python -m pytest -q` from `backend`; mobile: `flutter test` from `mobile`; web: `node --test web/test/*.test.js` from the repository root.  
> **Lint/Check Command:** Backend: `python -m ruff check .` from `backend`; mobile: `flutter analyze` from `mobile`; JavaScript: `node --check <changed-file>`; all changed files: `git diff --check`.  
> **Prepared:** 2026-09-15.  
> **Source:** Ponytail audit and review of Gemini's changes after `e1e3904`.  

## Overview

Shorten only the unnecessary complexity introduced by Gemini's completed AI-accuracy work.
Preserve all corrected data semantics, safety boundaries, provenance fields, warning behavior, trip lifecycle behavior, physical drift constraints, and responder authority.
This is a cleanup pass, not a new model, data collection effort, API redesign, or behavior change.

Gemini must inspect the current working tree before editing because the repository may contain user changes.
Do not reset, squash, rewrite, or stage unrelated commits.
Do not modify the completed AI accuracy plan or audit reports except when a cleanup changes a directly referenced command or file path.

## Review findings to resolve

These six findings are the complete scope of this plan.

| ID | Finding | Location | Required simplification |
| --- | --- | --- | --- |
| PT-01 | Repeated `PropagationEstimate` and `SquallFeatureBundle` construction makes invariant tests long and fragile | `backend/tests/test_phase3_validation.py:73`, `:141`, `:190` | Reuse the existing object with `dataclasses.replace` or a small local fixture helper, while retaining every invariant assertion and changed field |
| PT-02 | Two tests only prove arithmetic or filtering over locally invented literals, not application behavior | `backend/tests/test_phase5_validation.py:195`, `:216` | Delete them, or replace them with a test that exercises the real production evaluation/provenance path; do not retain a test merely because its name sounds like a requirement |
| PT-03 | The synthetic demo gate is implemented twice with the same behavior | `backend/app/api/current_events.py:24`, `backend/app/api/pressure_events.py:33` | Reuse one existing guard or extract the smallest shared helper; preserve both demo-mode and constant-time key checks and the production rejection boundary |
| PT-04 | `degradedBuoyCount` has no caller after buoy health was removed from physical hazard scoring | `web/js/dangerZonePredictor.js:123` | Delete the unused function after confirming no dynamic or test reference; do not restore buoy health as a hazard feature |
| PT-05 | `_area_reduction_factor` retains an unused compatibility path and unused location arguments | `backend/app/ai/drift_eval.py:155` | Make `forecast_hours` required and remove only the dead fallback/arguments if repository-wide callers confirm this is private evaluation code |
| PT-06 | Warning delivery state uses a string plus a second validation set | `backend/app/api/advisories.py:399`, `:406`, `:418` | Use `typing.Literal` in the Pydantic request model and remove duplicate manual validation, preserving the same five accepted wire values and 422 behavior |

The review was intentionally limited to over-engineering.
Do not use this plan to fix unrelated correctness, security, performance, architecture, UI, deployment or field-validation findings.

## Required execution rules

- Read `AGENTS.md`, this plan, `docs/AI_ACCURACY_IMPLEMENTATION_PLAN.md`, and the diff that introduced each finding before editing.
- Start with `git status --short` and record unrelated paths.
- Search all callers and tests before deleting a helper, parameter, fixture, or validation branch.
- Keep the public API response shape, accepted warning strings, demo-only synthetic gate, and physical output semantics unchanged.
- Do not add a dependency, generic abstraction, model framework, fixture framework, compatibility shim, or new service.
- Prefer an existing dataclass/helper, Python's `dataclasses.replace`, Pydantic validation, and direct deletion.
- If a finding cannot be simplified without changing behavior, leave it unchanged and record why in the phase report.
- Do not remove a behavior test until an equivalent production-path test exists or the test is demonstrably only a tautology.
- Do not edit generated files, raw field data, model artifacts, migrations, or unrelated documentation.
- Run the relevant verification gate before committing each phase.
- Stage explicit paths and hunks only; never use `git add .`.
- Stop after each phase and wait for explicit user sign-off before beginning the next phase.

## Phase 1: Simplify tests without weakening behavioral coverage

**Goal:** Remove tautological test code and reduce duplicated fixture construction while preserving meaningful regression coverage.

### Tasks

- [x] **Task 1.1: Establish the baseline.**
  Record `git status --short`, the current commit, and the existing targeted test results for the files in this phase.
  Do not fix pre-existing failures as part of this cleanup.
- [x] **Task 1.2: Consolidate propagation fixtures.**
  Inspect the `PropagationEstimate` and `SquallFeatureBundle` dataclasses in `backend/app/ai/squall.py`.
  Use `dataclasses.replace` or a local test-only factory to vary only coordinate origin, intercept, timestamp, or geometry fields.
  Keep the coordinate-origin invariant, common-timestamp shift invariant, degenerate-front rejection, low-`r2` rejection, and all assertions unchanged in meaning.
  Do not introduce a production abstraction for test setup.
- [x] **Task 1.3: Replace tautological phase-five tests.**
  For `test_distinguishes_forecast_lead_from_actionable_warning`, first search for a real evaluation function that computes delivered lead or actionability.
  If one exists, test that function with a late and sufficient warning.
  If none exists, delete the arithmetic-only test and retain the requirement in the protocol documentation rather than inventing a test helper.
  For `test_strict_provenance_separation`, first search for the real manifest, evaluator, or storage path that separates natural, drill, and synthetic records.
  Test that path if it exists; otherwise delete the list-filtering tautology and leave the protocol requirement documented.
- [x] **Task 1.4: Update only affected test names and imports.**
  Remove imports made unused by the deletion or fixture consolidation.
  Keep test descriptions aligned with the behavior actually exercised.

### 🧪 Verification Gate

- [x] Run `python -m pytest -q tests/test_phase3_validation.py tests/test_phase5_validation.py` from `backend`.
- [x] Run `python -m pytest -q` from `backend`.
- [x] Run `python -m ruff check .` from `backend`.
- [x] Confirm no test was deleted solely to hide a failure.
- [x] Confirm the diff contains no new dependency, production helper, or altered safety output.
- [x] Run `git diff --check` from the repository root.

### 🔍 Review Gate (Ponytail)

- [x] The repeated dataclass setup is shorter and still tests each distinct invariant.
- [x] Any deleted test was a tautology or replaced by a production-path assertion.
- [x] No test framework, fixture layer, or generic builder was added.

### 📦 Git Checkpoint

Stage only the phase-owned test files and commit them atomically:

```text
git add backend/tests/test_phase3_validation.py backend/tests/test_phase5_validation.py
git commit -m "test(ai): simplify accuracy regression fixtures"
```

### 🛑 HARD STOP

> **PAUSE HERE.** Report the exact tests retained, deleted, or replaced, the verification output, the diff size, and the commit hash.
> Ask for explicit user confirmation before Phase 2.

---

## Phase 2: Collapse duplicated backend validation and dead evaluation paths

**Goal:** Reuse one minimal demo guard, use native request validation, and remove the private evaluation compatibility branch without changing accepted behavior.

**Entry condition:** Phase 1 is verified, committed, and explicitly approved.

### Tasks

- [x] **Task 2.1: Consolidate the synthetic demo gate.**
  Compare `backend/app/api/current_events.py`, `backend/app/api/pressure_events.py`, and the existing demo-key helper.
  Reuse the existing guard when its contract matches, or move the exact shared check to the smallest appropriate existing module.
  Preserve `DEMO_MODE`, `DEMO_CONTROL_KEY`, `hmac.compare_digest`, the 403 boundary, and the fact that synthetic current/pressure writes remain demo-only.
  Keep route-specific error text only if callers or tests rely on it; otherwise use one clear message.
  Do not broaden gateway authorization or make real measurements require the demo key.
- [x] **Task 2.2: Replace warning-state duplication with `Literal`.**
  Import `Literal` in `backend/app/api/advisories.py` and type `WarningDeliveryIn.delivery_state` with exactly `generated`, `gateway_accepted`, `buoy_received`, `phone_received`, or `user_acknowledged`.
  Remove `VALID_DELIVERY_STATES` and the manual membership branch only after confirming Pydantic produces the expected 422 response for an invalid value.
  Preserve the database constraint, response shape, accepted strings, ordering, and delivery-event storage.
- [x] **Task 2.3: Remove the dead buoy helper.**
  Search JavaScript source, tests, HTML event handlers and dynamic references for `degradedBuoyCount`.
  Delete it only when the search confirms no caller.
  Keep `buoyAdjustment: 0` only if it is part of an existing response contract; otherwise document any removal separately and do not alter hazard scoring in this phase.
- [x] **Task 2.4: Shrink the private drift evaluator.**
  Search repository-wide callers of `_area_reduction_factor`.
  Make `forecast_hours: float` required and remove `last_lat`, `last_lon`, and the old `max_radius_m` fallback only if no external or test caller depends on them.
  Keep the independent maximum-speed baseline and its numerical output unchanged.
  Do not change the physical constant, area calculation, evaluation dataset, or claim wording.
- [x] **Task 2.5: Keep imports and type annotations minimal.**
  Remove imports made unused by the simplifications.
  Do not create a new “validation framework” or replace a three-line helper with a class.

### 🧪 Verification Gate

- [x] Run `python -m pytest -q tests/test_current_ingest.py tests/test_warning_transport.py tests/test_phase4_validation.py tests/test_drift_api.py` from `backend`.
- [x] Run `python -m pytest -q` and `python -m ruff check .` from `backend`.
- [x] Run `node --test web/test/*.test.js` and `node --check web/js/dangerZonePredictor.js` from the repository root.
- [x] Confirm invalid delivery states still return 422 and all five valid states still persist and read back.
- [x] Confirm synthetic current and pressure writes still fail outside demo mode and real live writes still use gateway authentication only.
- [x] Confirm drift evaluation output is numerically unchanged for the same input.
- [x] Run `git diff --check` from the repository root.

### 🔍 Review Gate (Ponytail)

- [x] One validation implementation serves both synthetic ingest routes.
- [x] Native Pydantic validation replaces hand-maintained duplicate membership logic.
- [x] The dead JavaScript helper and private evaluator fallback are gone only after caller searches.
- [x] No public contract, data provenance rule, physical threshold, or delivery state changed.

### 📦 Git Checkpoint

Stage only the reviewed backend and JavaScript paths that actually changed.
If a test was updated to preserve an API assertion, add that specific test path separately.

```text
git add backend/app/api/current_events.py backend/app/api/pressure_events.py backend/app/api/advisories.py backend/app/ai/drift_eval.py web/js/dangerZonePredictor.js
git commit -m "refactor(ai): remove duplicate validation paths"
```

Before staging, remove any unrelated test path from the command and inspect the staged diff.

### 🛑 HARD STOP

> **PAUSE HERE.** Report which guard was reused or extracted, the caller searches, API compatibility results, test/lint output, and the commit hash.
> Ask for explicit user confirmation before Phase 3.

---

## Phase 3: Final cross-surface minimality review

**Goal:** Verify the cleanup is complete, behavior-preserving, and limited to Gemini's reviewed changes.

**Entry condition:** Phase 2 is verified, committed, and explicitly approved.

### Tasks

- [x] **Task 3.1: Review the combined diff.**
  Compare the cleanup commits with the Gemini implementation range beginning at `e1e3904` and the working-tree baseline recorded in Phase 1.
  Confirm that no unrelated user change, field-data file, model artifact, migration, or prior audit was staged.
- [x] **Task 3.2: Run the full applicable checks.**
  Run the full backend, mobile, web, and changed-file checks already used by the AI accuracy work.
  Do not claim field calibration, operational accuracy, or hardware delivery from software tests.
- [x] **Task 3.3: Re-run the Ponytail review.**
  Search for the six original findings and confirm each is either removed, reduced, or explicitly documented as intentionally retained.
  Report any additional simplification only if it is directly part of these six findings; do not expand scope during the final review.
- [x] **Task 3.4: Update the handoff status.**
  Mark only completed cleanup tasks in this plan.
  Do not mark the AI accuracy implementation plan's evidence phases as changed or complete because of this cleanup.

### 🧪 Verification Gate

- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`.
- [x] From `mobile`, run `flutter test` and `flutter analyze`.
- [x] From the repository root, run `node --test web/test/*.test.js`, `node --check web/js/dangerZonePredictor.js`, and `git diff --check`.
- [x] Confirm the working tree contains only the intended cleanup commits and pre-existing user changes.
- [x] Confirm no dependency manifest changed.

### 🔍 Review Gate (Ponytail)

- [x] The cleanup diff is shorter than the Gemini code it replaces where code deletion or fixture reuse was the finding.
- [x] Every retained line has a behavior, safety, provenance, or verification purpose.
- [x] No speculative abstraction, compatibility layer, or second validation source remains.

### 📦 Git Checkpoint

Stage only this plan's completion record and any directly necessary cleanup documentation:

```text
git add docs/PONYTAIL_SIMPLIFICATION_IMPLEMENTATION_PLAN.md
git commit -m "docs(ai): record ponytail simplification handoff"
```

If Phase 3 required no code or documentation change beyond the already committed phase records, do not create an empty commit.

### 🛑 HARD STOP

> **PAUSE HERE.** Report the final net line change, retained findings, full verification output, and all commit hashes.
> Do not automatically continue to another cleanup pass or modify production behavior.

## Gemini handoff

1. Read this plan and the prior Ponytail findings before editing.
2. Start with Phase 1 and stop at its hard stop.
3. Treat the previous finding as a request to simplify, not permission to redesign.
4. Preserve the safety claim boundaries established by the AI accuracy plan.
5. Ask for sign-off after every phase before touching the next phase.

This document is an instruction plan only.
No code, tests, configuration, generated files, database files, or model artifacts were changed while creating it.
