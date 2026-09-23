---
name: implementation-plan
description: >
  Create, execute, or resume a phased plan from Len's approved feature spec,
  or toggle plan execution mode. Use for implementation planning, phase
  execution, plan status, or mode toggles.
argument-hint: "[create <feature> | execute | status | mode auto|hard-stop]"
license: MIT
---

# Implementation planning and execution

Read project `AGENTS.md` and the current handoff for authority, commits, recovery, and evidence policy.
For planning, read the approved product baseline, architecture, and feature spec before choosing tasks.
An approved spec alone does not approve a new plan.

## Execution mode

| Mode | Behavior |
|---|---|
| `auto` | Run every approved phase in order; stop only for a failed gate, a real blocker, or a decision that is Len's. |
| `hard-stop` | After each phase's verification, stop, report, and wait for Len's explicit go-ahead before the next phase. |

The mode lives in the plan doc header as `**Execution mode:** auto` or `**Execution mode:** hard-stop`.
Default is `hard-stop` when the plan changes product code, a shared contract (`docs/02` to `docs/06`), migrations, firmware, or deployment config, or has more than 3 phases; `auto` otherwise.
The toggle is `/implementation-plan mode auto` or `/implementation-plan mode hard-stop` (or chat message).
It edits only the `**Execution mode:**` header field of the plan named in the active `HANDOFF.md` (or the single active plan; ask if ambiguous), and does not run tasks.
A toggle takes effect at the next phase boundary, never mid-phase.

## Create a plan

Use `.agents/templates/docs/IMPLEMENTATION_PLAN.md` or `templates/docs/IMPLEMENTATION_PLAN.md`.
Write the active feature plan under `docs/plans/FEAT-NNN-implementation.md` unless an existing convention applies.
Add `**Execution mode:**` to the plan header and propose the default by scale to Len.
Link tasks and verification to stable requirement IDs; choose phases by testable outcomes.
Inspect branch, edits, scripts, and environment before filling commands; unresolved placeholders cannot pass readiness gates.
Present the feature spec and plan to Len for chat approval and record exact approved revisions in the approved doc, linked from the current handoff.

## Execute or resume

Reread approved files and reconcile plan state with actual Git status and evidence.
Do not treat a checked box as proof that a command ran or a commit succeeded.
Implement only the approved phase, verify with required commands, and review the diff for correctness and Ponytail simplicity.
Update evidence, task progress, and handoff; stage only reviewed paths and complete checkpoints when Git confirms the commit.
In `auto` mode, proceed through remaining approved phases without requesting routine sign-off.
In `hard-stop` mode, stop after each phase's verification and await Len's explicit go-ahead before the next phase.
If interrupted, preserve edits uncommitted and record the exact next step.

## Failure report

Follow the shared three-attempt limit, counting attempted corrections followed by a check for the same problem.
Report the failed requirement or gate, actual error, attempts and results, outstanding edits, blocked work, and the smallest decision or access needed.
Do not reset counts between sessions or substitute a different architecture to force progress.
