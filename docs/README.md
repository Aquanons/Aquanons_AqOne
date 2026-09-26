# Documentation Map and Naming Convention

Use this page before creating a document.
It keeps active delivery work separate from reference material and historical plans.

## Start Here

Agents should begin with the fast [SPEC_INDEX.md](SPEC_INDEX.md), then use this
page for source precedence, current work ownership, naming, status, and authoring rules.

| Need | Document |
|---|---|
| Current product priorities | [`../README.md`](../README.md) |
| Current work, owners, agents, worktrees, and next actions | [Current Register](#current-register) |
| Project brief and build order | [`00_START_HERE.md`](00_START_HERE.md) |
| Scope exclusions and amendments | [`07_SCOPE_OUT.md`](07_SCOPE_OUT.md) |
| Current hybrid transport decision | [`55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`](55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md) |
| Aggregated architecture and data flow | [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) |
| Honest demo status and evidence | [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md) |
| Pitch plan (blocked on handset, buoy and rehearsal evidence) | [`43_DTI_PITCH_IMPLEMENTATION_PLAN.md`](43_DTI_PITCH_IMPLEMENTATION_PLAN.md) |
| External event deadlines | [`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md) |
| Shared technical contracts | [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md), [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md), [`04_INGEST_API.md`](04_INGEST_API.md), [`05_PUBLIC_API.md`](05_PUBLIC_API.md), [`06_DELIVERY_STATES.md`](06_DELIVERY_STATES.md), [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) |

The project documents have distinct authority.
Use this order to resolve what each one controls:

1. [`Aqone_PRD (2).md`](Aqone_PRD%20(2).md) controls product scope and roadmap.
2. An approved feature spec or decision controls that feature's behavior and architecture.
3. The relevant shared contract controls cross-workstream interfaces.
4. The approved implementation plan controls phase order, gates, and acceptance criteria.
5. The newest dated evidence controls what has actually been observed or verified.
6. This page's [Current Register](#current-register) controls current assignments, ownership, worktree, state summary, and next action.
7. Source code and tests show what is implemented now; they do not approve a scope or contract change.
8. Each worktree's ignored `HANDOFF.md` carries only that worktree's local baton and working-tree evidence.

If sources disagree on a decision, stop before changing affected code, record the disagreement in the relevant spec or plan, and get the decision owner to reconcile it.
Do not select a winner by filename, recency, or chat alone.
The shared Current Register is a committed team-wide ownership ledger; it does not replace per-worktree `HANDOFF.md` files.

## File Names

Keep the existing files where they are.
Do not renumber or mass-rename them because other documents and team prompts link to them.

New numbered documents use this format:

```text
NN_TOPIC_TYPE.md
```

`NN` is the next unused two-digit number in `docs/`.
Numbers are permanent and are never reused.
Use uppercase words separated by underscores.

| Type | Use for | Example |
|---|---|---|
| `SPEC` | Stable product or technical contract | `43_GATEWAY_RETRY_SPEC.md` |
| `IMPLEMENTATION_PLAN` | A bounded plan that someone can execute | `44_SOS_DEMO_IMPLEMENTATION_PLAN.md` |
| `DECISION` | A choice that changes scope, architecture, or a plan | `45_PITCH_SCOPE_DECISION.md` |
| `VERIFICATION` | Observed test, field, or rehearsal evidence | `46_RANGE_TEST_VERIFICATION.md` |
| `AUDIT` | Read-only findings and recommendations | `47_MOBILE_SCOPE_AUDIT.md` |
| `FIX_PROMPTS` | Prompt sets generated from a specific audit | `48_MOBILE_FIX_PROMPTS.md` |
| `GUIDE` | How-to material that is not a contract | `49_DEMO_REHEARSAL_GUIDE.md` |

Several implementation plans may be `ACTIVE` at the same time when their owned paths do not overlap and their dependencies are recorded in the Current Register.
Only the assigned owner or agent may edit an owned path.
Coordinate a handoff before another agent takes over or edits those paths.
Keep completed plans in `docs/archive/plans/` as the permanent delivery record.

## Required Header for New Work Documents

Put this block immediately below the title in every new plan, decision, verification, audit, or guide.

```markdown
**Status:** DRAFT | ACTIVE | COMPLETE | BLOCKED | SUPERSEDED
**Owner:** Name or team
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD
**Related:** `docs/NN_RELATED_DOCUMENT.md`
```

Plans also state their success condition and the next hard stop.
Verification documents state the exact environment, date, result, and any limitation.
Decisions state what changed, why, and which document they replace or amend.

## Status Rules

The Current Register lists every approved plan that still has work or a gate outstanding, including work that is waiting or queued.
Use `IN PROGRESS`, `WAITING`, or `QUEUED` in the register to distinguish live work from approved work that has not started.
Mark a finished plan `COMPLETE` after its evidence and commit are recorded.
Mark an obsolete plan `SUPERSEDED` and link the replacement at the top.
Do not delete historical documents. When a plan is verified complete, it may move to `docs/archive/plans/`. When a record is verified superseded or completed historical context, it may move to `docs/archive/history/` after all references are updated. They remain part of the project record and explain earlier code, architectural decisions, and pitch material.

Update the register when work starts, an owner or agent changes, a phase gate passes or blocks, a worktree changes materially, or work completes.
Each row must link its approved spec or plan and state the human owner, active agent (or `none`), branch and worktree (or `not assigned`), owned paths, work completed, blockers or dependencies, and one next action.
Include the time of any live worktree observation and treat `git status` as the latest evidence when a working tree may have changed since that observation.
Never record secret values.

## Current Register

This is the committed source of truth for who owns current work and what each workstream needs next.
Plan documents remain the source of detailed requirements and acceptance criteria; `docs/08_DEMO_AND_STATUS.md` remains the evidence ledger.

Last checked: 2026-09-26 14:17 +08:00.

| Workstream and approved source | Current state and completed work | Human owner, active agent, workspace, and owned paths | Next action and gate |
|---|---|---|---|
| [Plan 70: Aklanon first](70_AKLANON_FIRST_IMPLEMENTATION_PLAN.md), Rev 2 | **IN PROGRESS**, confirmed by Len on 2026-09-26. Commits `6aa01d5`, `53ce666`, `f6022d8`, and `792d88a` match the plan's Phase 1 through Phase 4 checkpoints. At the 14:17 +08:00 observation, branch `feat/aklanon-first` in `../AqOne-aklanon` was at `792d88a` with six modified files: `mobile/lib/core/l10n_fallback.dart`, `mobile/lib/models/daily_outlook.dart`, `mobile/lib/ui/widgets/advisory_card.dart`, `mobile/lib/ui/widgets/weather_card.dart`, `mobile/test/aklanon_below_ui_test.dart`, and `mobile/test/weather_card_test.dart`. These paths suggest Phase 5 is underway; this phase mapping is inferred because the plan's phase headings still say `Awaiting approval` and the worktree has no `HANDOFF.md`. | Len approves and proofreads. Len confirms another AI model is translating; the plan names Claude as implementer, but the model identity is not confirmed here. Workspace: `../AqOne-aklanon`, branch `feat/aklanon-first`. Scope: `mobile/**` plus the plan's evidence and localization docs in that worktree. Do not edit or stage its files. | The active implementer continues Phase 5 against its acceptance criteria, records the current phase and next action in that worktree's `HANDOFF.md`, and reconciles the stale phase labels in Plan 70 at its next handoff. Len proofreads the Aklanon drafts after the plan is complete. |
| [Plan 66: critical edge cases](66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md), Rev 2 | **WAITING** on shore hardware evidence for Phase 1. C3, the C6 browser half, C7, and the deployed-backend half of C9 are recorded; the C9/C13 shore reflash is open. SMS escalation is also unconfigured, and the C7 vessel-feed check was only confirmed through the API. | Daniel owns the shore reflash. Len supplies required secrets privately. The prior root handoff names Claude to record evidence when Daniel returns logs; no current evidence agent is confirmed. Workspace: hardware session; evidence worktree is not assigned. Evidence paths: `docs/edge-remediation/EVIDENCE-critical.md`, this plan, and `docs/08_DEMO_AND_STATUS.md`. | Daniel flashes the shore gateway and pod per [`edge-remediation/HANDOFF-daniel-shore-reflash.md`](edge-remediation/HANDOFF-daniel-shore-reflash.md), then returns sanitized logs and the phone screenshot. The assigned evidence owner records the result and updates the plan and `docs/08`. Firmware phases remain gated on Daniel's two-board bench. |
| [Plan 65: fisher friction](65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md), Rev 3 | **WAITING**. Phase 1, the countdown fix, and Phase 3 are merged. Phase 0a's team term study has not started. Phase 2 now follows Plan 70 and Plan 66's Phase 5 gate; later phases remain queued. | Len owns approval. Doreen Kay and Jade own the people-led term study. No implementation agent is currently assigned. `mobile/**` is currently being used by Plan 70 in its separate worktree; do not start overlapping handset edits. | Doreen Kay and Jade complete the term study, then Len reviews it. Recheck Plan 65's phase gates after Plan 70 completes and Plan 66 reaches Phase 5. |
| [Plan 69: weather-tiered check-ins](69_WEATHER_TIERED_CHECKINS_IMPLEMENTATION_PLAN.md), Rev 2, with [spec 68](68_WEATHER_TIERED_CHECKINS_SPEC.md) | **WAITING FOR APPROVAL**. Phases 1 and 2 are complete; Phase 3 storage, tier, and slot endpoints is awaiting Len's approval. The saved `../AqOne-fleet-watch` worktree is clean at `feat/fleet-watch`, `10f320a`. | Len owns the Phase 3 decision. No implementation agent is currently assigned. Saved workspace: `../AqOne-fleet-watch`; no active paths are claimed until approval. | Len approves Phase 3 or defers the plan. If approved, assign an agent and worktree in this register before editing backend paths. |
| [Plan 62: edge-case remediation](62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md) | **QUEUED / WAITING**. Tracks B, M, and W are merged. Phase 0a still needs UptimeRobot and the NTC inquiry; Phase I integration has not started. B8, M7, and Track F remain gated. | Len owns the Phase 0a actions. No active coding agent or dedicated worktree is confirmed. Before Phase I, reconcile any overlap with Plan 66. | Len completes or assigns the Phase 0a actions. Before Phase I coding, record its owner, agent, workspace, and non-overlapping paths here. |

The project-wide release gates remain in [`00_START_HERE.md`](00_START_HERE.md) and the latest dated evidence in [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md).
Use those records to confirm the current state of the full phone-to-dashboard path, persistent acknowledgement, physical-device checks, measured outdoor range, three rehearsals, and screencast.

## Existing Records

| Group | Files |
|---|---|
| Foundation and shared contracts | `00` to `08` |
| Earlier planning and implementation records | `13` to `25`, `29` to `31`, `33`, `34`, `36` to `42` (`11` and `26` are in `archive/history/`; `46` is in `archive/plans/`) |
| Edge-case remediation | `60` findings, `61` design, `62` plan with tracks `62A` to `62D`, evidence in [`edge-remediation/`](edge-remediation/); `59` and `63` are completed plans in `archive/plans/` |
| Operations runbooks | [`runbooks/`](runbooks/) |
| Dated audits and verification | [`audits/`](audits/) |
| Current pitch plan | `43` |
| Visual design guide | `47` |
| Historical records and legacy guides | [`archive/history/`](archive/history/) |
| Archived completed plans | [`archive/plans/`](archive/plans/) |
| Reference guides | [`guides/`](guides/) |
| Hybrid transport decision and technical architecture spec | `55`, `56` |
| Draft plans not yet started | `67` (stagnant mode) |
| Design references and competition materials | [`design-reference/`](design-reference/), [`competitions/`](competitions/) |
| Canonical PRD | [`Aqone_PRD (2).md`](Aqone_PRD%20(2).md) |

`Aqone_PRD (2).md` retains its supplied filename because it is the canonical PRD.
