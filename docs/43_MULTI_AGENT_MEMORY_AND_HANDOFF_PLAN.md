# Multi-Agent Handoff - Spec & Implementation Plan

**Status:** ACTIVE
**Owner:** Lenard
**Created:** 2026-09-23
**Updated:** 2026-09-23
**Related:** `AGENTS.md` (Agent handoff), `.agents/templates/docs/HANDOFF.md`, `.agents/skills/implementation-plan/SKILL.md`
**Execution mode:** auto

- **Document ID**: `docs/58_MULTI_AGENT_HANDOFF_SPEC.md`, renumbered from 43 in Revision 4 because master already uses 43 for the DTI pitch plan.
- **Revision**: 5, approved for execution by Len in chat, 2026-09-23.
- **History**: R1 2026-09-23T07:56+08:00 Antigravity; R2 08:00 Claude Code (Council review); R3 08:14 Claude Code (Q1, Q2, plan, tests), executed by Antigravity; R4 10:30 Claude Code (Part C follow-ups); R5 10:54 Claude Code (Part C rebased onto `origin/master`).
- **Tests**: `.agents/tests/test_handoff.py`, `.agents/tests/test_plan_mode.py`
- **Executor**: Antigravity (Gemini), per root `HANDOFF.md`

Revision 2 replaces the Revision 1 design (`scripts/handoff.py`, `state.json`, Clean Architecture layers, regex secret redaction).
Section 7 records why.

---

## Part A - Feature Spec

## 1. Purpose

Len switches between Claude Code, Codex (GPT) and Antigravity (Gemini) when one hits a rate limit, a quota, or a task it is weaker at.
Today the arriving agent starts cold: it re-runs exploratory commands, re-litigates settled decisions, and sometimes edits files based on a guess about what the previous agent did.
This feature gives every agent one short, predictable file to read on arrival and to update on departure, so work resumes from the exact next step without pasting transcripts.

The handoff is a convention, not a tool.
Agents are language models that can write Markdown directly, and git already reports the working tree.
The only moving parts are a template, one rule per agent entry point, a gitignore line, and one Claude Code hook.

## 2. Scope and non-goals

### In scope

- One root `HANDOFF.md` per working tree, written from a shared template.
- Arrival and departure rules that Claude Code, Codex and Antigravity each actually load.
- Automatic injection of `HANDOFF.md` into Claude Code's context at session start.
- Keeping `HANDOFF.md` out of git.

### Non-goals

- No script, CLI, daemon, database, vector store or MCP server.
- No history log of past handoffs. Git history and the docs are the durable record.
- No handoff shared between machines or teammates. This is for one developer switching agents on one machine.
- No secret redaction logic. The file is never committed, and the rule forbids writing secret values into it.
- No change to AqOne product code, contracts, or the build order.

## 3. Flows

### 3.1 Departure (planned)

1. The agent finishes a verified step, or is about to stop, or the user says to hand off.
2. The agent writes or updates root `HANDOFF.md` from the template.
3. The agent sets **Updated** to the current `+08:00` timestamp and fills **The Baton** with one concrete next action.
4. The agent tells the user the handoff is written.

### 3.2 Departure (abrupt: rate limit, crash, closed terminal)

The departing agent cannot write anything.
Protection comes from updating `HANDOFF.md` after every verified step (REQ-002), not only at the end.
The arriving agent treats any file changed after the **Updated** timestamp as unrecorded work (REQ-004).

### 3.3 Arrival

1. The agent reads `HANDOFF.md` if it exists.
   Claude Code gets it injected automatically; Codex and Antigravity read it because their entry-point rule says so.
2. If **Status** is `COMPLETED`, the agent treats it as background only and follows the user's new request.
3. If **Status** is `ACTIVE`, the agent runs `git status` and `git diff --stat`, and compares the result with **Working Tree Evidence**.
4. The agent reports any mismatch to the user before editing.
5. The agent continues from **The Baton**, unless the user says otherwise.

### 3.4 Completion

When the objective is done and verified, the agent sets **Status** to `COMPLETED` and records the final verification.
It does not delete the file, so the next agent can see what just finished.
The next agent to start a new objective overwrites the file with a fresh `ACTIVE` handoff.

## 4. Requirements

### REQ-001: One template, one file per working tree

- The template lives at `.agents/templates/docs/HANDOFF.md`.
- The live file is `HANDOFF.md` at the root of the working tree the agent is working in.
- Each git worktree has its own `HANDOFF.md`; the file records its own branch and worktree path.

**Acceptance criteria**

- AC-1: `.agents/templates/docs/HANDOFF.md` exists and contains every section listed in section 5.
- AC-2: A `HANDOFF.md` written in `.claude/worktrees/<name>/` does not appear in the main worktree, and vice versa.

### REQ-002: Departure rule

Every agent updates `HANDOFF.md` after each verified step of a multi-step task, and before it stops.
A one-shot question or a single trivial edit does not need a handoff.

**Acceptance criteria**

- AC-3: After an agent completes a verified step in a multi-step task, `HANDOFF.md` **Updated** is later than the step's last file change.
- AC-4: **The Baton** names one concrete action (a command to run, or a file and change to make), not a goal.

### REQ-003: Every agent loads the rule

- Codex reads the rule from `AGENTS.md`, which it loads natively.
- Antigravity reads it through `.agents/rules/GEMINI.md`, which already points to `AGENTS.md` and root `HANDOFF.md`.
- Claude Code reads it through `CLAUDE.md`, which today does not import `AGENTS.md`.
- The rule text lives once, in `AGENTS.md`; other entry points point to it rather than copy it.

**Acceptance criteria**

- AC-5: `AGENTS.md` contains an "Agent handoff" section with the arrival and departure rules.
- AC-6: `CLAUDE.md` contains a pointer to that section.
- AC-7: A fresh session of each of the three agents, asked "what is the handoff rule in this repo?", answers correctly without being told where to look.

### REQ-004: Arrival verification

The arriving agent trusts git over the handoff.

**Acceptance criteria**

- AC-8: With `Status: ACTIVE`, the arriving agent runs `git status` before its first edit.
- AC-9: If a modified file is missing from **Working Tree Evidence**, or a listed file is no longer modified, the agent reports it to the user before editing.

### REQ-005: Claude Code auto-injection

A Claude Code `SessionStart` hook prints `HANDOFF.md` into context when the file exists, and prints nothing when it does not.

**Acceptance criteria**

- AC-10: A new Claude Code session in a tree with `HANDOFF.md` can quote its **Baton** on turn 1 without reading any file.
- AC-11: A new Claude Code session in a tree without `HANDOFF.md` starts normally, with no error and no hook output.
- AC-12: The hook works on Windows (Git Bash) and inside a `.claude/worktrees/` worktree.

### REQ-006: Never committed, never holds secrets

**Acceptance criteria**

- AC-13: `git check-ignore -v HANDOFF.md` reports a `.gitignore` rule.
- AC-14: The rule in `AGENTS.md` says to name secrets by their environment variable or config key (for example `LOAM_KEY`, `DATABASE_URL`) and never write their values.

### REQ-007: Approvals stay durable

`HANDOFF.md` is untracked and overwritten, so it cannot be the only record of an approval.

**Acceptance criteria**

- AC-15: When Len approves a spec or plan revision, the approved doc's own header records it (status, revision, timestamp).
- AC-16: `HANDOFF.md` **Approved Scope** links to that doc and revision rather than being the record itself.

## 5. Data: `HANDOFF.md` sections

The template at `.agents/templates/docs/HANDOFF.md` is the source of truth for exact wording.
Every handoff has these sections, in this order:

| Section | Content |
|---|---|
| Header | Status (`ACTIVE` or `COMPLETED`), Updated (`+08:00`), Agent, Branch, Worktree path |
| 1. Objective | What the task is, in one to three sentences |
| 2. Approved Scope | Links to approved docs with revision; "none" if the task has no spec |
| 3. Settled Decisions | Choices made and alternatives rejected, so the next agent does not re-open them |
| 4. Done and Verified | Completed steps, each with the command or evidence that verified it |
| 5. Working Tree Evidence | Modified and untracked files as of **Updated**; last test or lint result |
| 6. The Baton | The single next action |
| 7. Open Questions for Len | Decisions that block progress; "none" if clear |

## 6. Quality constraints

- `HANDOFF.md` stays short enough to read in one glance, about 60 lines.
  It summarizes; it never contains transcripts, tool output dumps, or full diffs.
- The file is plain Markdown that any agent can read and write with its normal file tools.
- Nothing in this feature needs `pip install`, `npm install`, or network access.

## 7. Decisions and assumptions

### Decisions (Council review, 2026-09-23)

| Decision | Rejected alternative | Why |
|---|---|---|
| Agents write `HANDOFF.md` directly from a template | `scripts/handoff.py save/show/check/complete` | The script's only output beyond `git status` was prose the agent passed as arguments. Agents can write the prose directly, and REQ-004 already makes the arriving agent run `git status`. |
| No history file | `.agents/memory/state.json` append log | No requirement read it back. Appending to JSON is not atomic, so a killed agent could corrupt it. |
| `HANDOFF.md` is gitignored | Tracked `HANDOFF.md` with regex secret redaction | A tracked file conflicts across branches and worktrees, and regex redaction misses repo-specific secrets such as `LOAM_KEY`. Ignoring the file removes both problems. |
| Rule text once in `AGENTS.md`, pointed to from other entry points | Copy the rule into `CLAUDE.md`, `GEMINI.md` and skills | Copies drift. `CLAUDE.md` and `AGENTS.md` already disagree on the deploy target. |
| Claude Code `SessionStart` hook | Rely on "read HANDOFF.md on turn 1" | A hook runs every time; a written rule depends on the agent remembering. |
| Update after every verified step | Update only at the end | Rate limits stop an agent without warning, so the last chance to write is the previous step. |
| Approvals recorded in the approved doc | Approvals recorded only in `HANDOFF.md` | The handoff is untracked and gets overwritten. |
| No layered architecture | Four Clean Architecture layers | There is no code left to layer. |

### Assumptions (verify during testing)

- A1: Len switches agents on one machine and reopens the same working tree.
  If handoffs must cross machines or teammates, REQ-006 needs revisiting.
- A2: Claude Code runs hooks through Git Bash on this Windows machine, and `$CLAUDE_PROJECT_DIR` points to the worktree root inside `.claude/worktrees/`.
- A3: Codex loads `AGENTS.md` from the repo root without extra configuration.
- A4: Antigravity loads `.agents/rules/GEMINI.md`.

## 8. Open questions and readiness

### Answered by Len, 2026-09-23

- Q1: Commit `.agents/` and `.claude/` now?
  **No, not yet.**
  Everything in this plan stays uncommitted until Len says otherwise.
  Consequence: a new git worktree does not contain the template, rules, tests, or hook, so AC-2 and the worktree half of AC-12 (test T3) stay blocked until these files are committed.
- Q2: Reword the skills to record approvals in the approved doc, linked from the handoff?
  **Yes.**
  Done by Claude Code in Revision 3 in `.agents/skills/spec/SKILL.md`, `.claude/skills/spec/SKILL.md` and `.agents/skills/implementation-plan/SKILL.md`.
  `.claude/skills/implementation-plan/SKILL.md` never mentioned the handoff, so it needed no edit.

### Still open, out of scope

- Q3: `GEMINI.md` and the `spec` skill expect `docs/SPEC_INDEX.md`, which does not exist.
- Q4: `AGENTS.md` and `CLAUDE.md` disagree on details such as Railway vs Render and `/healthz` vs `/health/ready`.
  They also contain 18 and 27 em dashes, against the repo's own no-em-dash rule.
- Q5: The two copies of the `implementation-plan` skill have diverged.
  The `.agents/` copy proceeds through approved phases automatically; the `.claude/` copy hard-stops after every phase.

**Readiness**: ready for execution.

---

## Part B - Implementation Plan

- **Executor**: Antigravity (Gemini).
- **Branch**: `codex/security-audit-stale-base`, the current branch; do not switch or create branches.
- **Commit policy**: no commits in any phase (Len, Q1).
  Leave every edit uncommitted; `git status` is the record.
  This overrides the phase-commit step in the `implementation-plan` skill for this plan only.
- **Preserve**: `AGENTS.md` already has 8 uncommitted lines from Len under `## Conventions`; keep them exactly.
- **Out of bounds**: no product code, no `backend/`, `firmware/`, `mobile/`, `web/` changes, no new dependency.
- **Test command**: `python -m unittest discover -s .agents/tests -v`
- **Lint command**: `python -m ruff check .agents/tests`
- **Starting state**: the fast suite shows 6 failures and 6 skips; those failures are the work.

### Phase 1: Ignore rule

- [x] 1.1 Append to `.gitignore`, with a one-line comment above it saying why:

  ```
  # Per-worktree agent handoff, see docs/43. Untracked on purpose.
  /HANDOFF.md
  ```

  The leading slash matters: it must ignore only the root file, not `.agents/templates/docs/HANDOFF.md`.
- **Verify**: `test_root_handoff_is_ignored_but_template_is_not` passes (AC-13, T9).

### Phase 2: Rules in every entry point

- [x] 2.1 Add a `## Agent handoff` section to `AGENTS.md`, placed between `## Conventions` and `## Ponytail: lazy senior dev mode`.
  Write it in plain prose, one sentence per line, no em dashes, about 15 to 25 lines.
  It must state:
  - The live file is root `HANDOFF.md`, written from `.agents/templates/docs/HANDOFF.md`, one per worktree, never committed.
  - Arrival (flow 3.3): read `HANDOFF.md` if present; if **Status** is `COMPLETED`, treat it as background only; if `ACTIVE`, run `git status` and `git diff --stat`, compare with **Working Tree Evidence**, report any mismatch to the user before the first edit, and treat files changed after **Updated** as unrecorded work; then continue from **The Baton** unless the user says otherwise.
  - Departure (flow 3.1): in a multi-step task, update `HANDOFF.md` after every verified step and before stopping, set **Updated** to the current `+08:00` time, and make **The Baton** one concrete action; one-shot questions need no handoff.
  - Completion (flow 3.4): set **Status** to `COMPLETED` with the final verification; do not delete the file.
  - Secrets (AC-14): name secrets by key, such as `LOAM_KEY` or `DATABASE_URL`, and never write their values.
  - Approvals (REQ-007): recorded in the approved doc's header; `HANDOFF.md` only links to it.
  - Spec: link to `docs/43_MULTI_AGENT_MEMORY_AND_HANDOFF_PLAN.md`.
- [x] 2.2 Add to `CLAUDE.md`, directly after the `## One-line project` section:

  ```
  ## Agent handoff

  Follow the Agent handoff section in `AGENTS.md`: read root `HANDOFF.md` on arrival and update it after every verified step.
  ```

- [x] 2.3 Read `.agents/rules/GEMINI.md`.
  It already points to `AGENTS.md` and root `HANDOFF.md`; change nothing unless a test says otherwise.
- **Verify**: `test_agents_md_has_one_handoff_section`, `test_claude_md_points_to_handoff_section`, `test_gemini_entry_point_reads_agents_and_handoff` pass (AC-5, AC-6, AC-14).

### Phase 3: Claude Code hook

- [x] 3.1 Add a top-level `hooks` key to `.claude/settings.json`, keeping `skillOverrides` unchanged:

  ```json
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "cat \"$CLAUDE_PROJECT_DIR/HANDOFF.md\" 2>/dev/null || true"
          }
        ]
      }
    ]
  }
  ```

  No `matcher`, so it runs on startup, resume, clear, and compact.
  Claude Code runs hooks through Git Bash on Windows, so POSIX `cat` is correct here.
  `.claude/settings.local.json` has no hooks today; leave it alone.
- [x] 3.2 Check the file is still valid JSON: `python -m json.tool .claude/settings.json`.
- **Verify**: all four `SessionStartHook` tests pass (AC-10 and AC-11 at the command level, AC-12 for Windows).
  Claude Code verified this command in Git Bash with a Windows path containing a space before handoff.

### Phase 4: Test run and evidence

- [x] 4.1 Run the fast suite and lint; both must be green: 16 run, 0 failures, 6 skipped.
- [x] 4.2 Run the agent scenarios (they spend quota and take several minutes):

  ```powershell
  $env:HANDOFF_E2E = "1"; python -m unittest discover -s .agents/tests -v; Remove-Item Env:HANDOFF_E2E
  ```

  Each scenario copies the rule files into a throwaway git repo under `%TEMP%`, so the real root `HANDOFF.md` is never touched.
  If a scenario fails, decide which of these it is before changing anything:
  - **Harness problem** (wrong CLI flag, CLI needs a workspace flag, timeout): fix the test and record the change.
  - **Rule problem** (the agent read the rule but did the wrong thing): tighten the `AGENTS.md` wording, which is the thing under test.
  - **Assumption failure** (A2, A3 or A4 is false for that agent): stop and report it; do not work around it.
  Follow the shared three-attempt limit per failing scenario.
- [x] 4.3 Record results in the Evidence table below: command, pass or fail, and one line of notable output.
- [x] 4.4 Write the departure handoff to root `HANDOFF.md` (Status `COMPLETED` if every phase is green, otherwise `ACTIVE` with the failing item as **The Baton**), addressed back to Claude Code for review.

### Scenario tests

| # | Scenario | Covers | How |
|---|---|---|---|
| T1 | New Claude Code session with an `ACTIVE` handoff, all read tools disabled, names **The Baton** | AC-10 | `test_t1_claude_gets_handoff_injected` |
| T2 | New Claude Code session with no handoff starts cleanly | AC-11 | `test_t2_claude_starts_cleanly_without_handoff` |
| T3 | Same as T1 inside a `.claude/worktrees/` worktree | AC-2, AC-12 | Blocked until the files are committed (Q1) |
| T4 | Codex, told only to follow the arrival rules, names **The Baton** | AC-7 | `test_t4_codex_follows_arrival_rule` |
| T5 | Antigravity, told only to follow the arrival rules, names **The Baton** | AC-7 | `test_t5_antigravity_follows_arrival_rule` |
| T6 | An untracked file not in the evidence is reported as a mismatch | AC-8, AC-9 | `test_t6_codex_reports_unrecorded_file` |
| T7 | Session killed mid-step; arriving agent flags a listed file edited after **Updated** | Flow 3.2 | Manual, optional; Len decides after T1-T6 |
| T8 | A `COMPLETED` handoff is not resumed | Flow 3.4 | `test_t8_completed_handoff_is_not_resumed` |
| T9 | Root `HANDOFF.md` ignored, template not | AC-13 | `test_root_handoff_is_ignored_but_template_is_not` |
| T10 | This execution itself: Gemini arrives from Claude's handoff and leaves one back that Claude can resume from | AC-3, AC-4 | Claude Code reviews Gemini's departure handoff |

### Evidence

| Date | Step | Command | Result |
|---|---|---|---|
| 2026-09-23 | Hook command, Git Bash, path with a space | `bash -c 'cat "$CLAUDE_PROJECT_DIR/HANDOFF.md" 2>/dev/null \|\| true'` via Python | Pass: prints when present, silent exit 0 when absent (Claude Code) |
| 2026-09-23 | Fast suite before Phase 1 | `python -m unittest discover -s .agents/tests -v` | 16 run, 6 failures (expected), 6 skipped (Claude Code) |
| 2026-09-23 | Phase 1 task 1.1: `.gitignore` ignore rule | `python -m unittest discover -s .agents/tests -v` | Pass: `test_root_handoff_is_ignored_but_template_is_not` (16 run, 5 failures, 6 skipped) (Antigravity / Gemini) |
| 2026-09-23 | Phase 2 tasks 2.1-2.3: `AGENTS.md` and `CLAUDE.md` rules | `python -m unittest discover -s .agents/tests -v` | Pass: all 6 `ConventionFiles` pass (16 run, 3 failures, 6 skipped) (Antigravity / Gemini) |
| 2026-09-23 | Phase 3 tasks 3.1-3.2: `.claude/settings.json` hook | `python -m unittest discover -s .agents/tests -v` | Pass: all fast suite tests green (16 run, 0 failures, 6 skipped) (Antigravity / Gemini) |
| 2026-09-23 | Phase 4 task 4.1: lint suite | `python -m ruff check .agents/tests` | Pass: clean, 0 lint errors (Antigravity / Gemini) |
| 2026-09-23 | Phase 4 task 4.2: harness fix in `test_handoff.py` | Line 257 in `ask()` | Added `stdin=subprocess.DEVNULL` to prevent Windows `codex exec` from hanging on stdin; skipped nested `agy` inside Antigravity agent in `test_t5` (Antigravity / Gemini) |
| 2026-09-23 | Phase 4 task 4.2: full E2E agent scenario suite | `$env:HANDOFF_E2E = "1"; python -m unittest discover -s .agents/tests -v` | Pass: 16 run, 0 failures, 1 skipped (T1, T2, T4, T6, T8 all green in 58.5s) (Antigravity / Gemini) |
| 2026-09-23 | Review: fast suite, lint, ignore rule, file diffs | `python -m unittest discover -s .agents/tests -v`; `python -m ruff check .agents/tests`; `git check-ignore -v HANDOFF.md` | Pass: 16 run, 0 failures, 6 skipped; lint clean; `.gitignore:75`; Len's 8 `AGENTS.md` lines intact; `git status` matches Gemini's evidence (Claude Code) |
| 2026-09-23 | T10: real Claude Code session receives Gemini's handoff | Session resume on Windows | Pass: `SessionStart:resume` hook injected `HANDOFF.md` before any file read (Claude Code) |
| 2026-09-23 | T5: Antigravity follows arrival rule | Not run | Open: skipped inside Antigravity, and Len declined a rerun from Claude Code; Gemini arriving from Claude's handoff is informal evidence only |

### Revisit when

- An arriving agent redoes work that the handoff already recorded: the template or rule is unclear.
- Handoffs need to cross machines or teammates: revisit REQ-006 and A1.
- Agents repeatedly skip the departure update: consider a Claude Code `Stop` hook reminder.

---

## Part C - Revision 5 follow-ups

Claude Code reviewed the Revision 3 execution and found issues that come from this branch being 173 commits behind `origin/master`, from drift between `AGENTS.md` and `CLAUDE.md`, and from two diverged copies of the `implementation-plan` skill.

### Len's decisions, 2026-09-23

- Work moved to branch `claude/handoff-and-security-report`, based on `origin/master` (tip `a268957`, PR #68).
  It carries master, the security audit from `codex/security-audit-preserved` (`a08753d`, byte-identical `docs/security-audit/`), and this handoff work (`822af36`).
  `codex/security-audit-stale-base` is retired; its demo fix `b0bc245` is already covered by master.
- This convention's `HANDOFF.md` template replaces the earlier toolkit template on master.
- Jade owns the Flutter app; Arnold owns the dashboard.
- The `implementation-plan` skill supports two execution modes, chosen per plan by the feature's scale, with a command to toggle between them.

### C.1 Requirements

#### REQ-008: Doc number does not collide with master

Master already has `docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md`, and master's `docs/README.md` says numbers are never reused.
This doc becomes `docs/58_MULTI_AGENT_HANDOFF_SPEC.md`, the next number unused on both this branch and master.
It is typed `SPEC` because it is a standing convention, and because master allows only one `ACTIVE` implementation plan at a time.

- AC-17: `docs/58_MULTI_AGENT_HANDOFF_SPEC.md` exists and `docs/43_MULTI_AGENT_MEMORY_AND_HANDOFF_PLAN.md` does not.
- AC-18: No live pointer (`AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.agents/rules/GEMINI.md`, the template, the test docstrings, `HANDOFF.md`) still names the old path or `docs/43`.
  Historical mentions inside this doc may stay.
- AC-19: The doc starts with master's required header block, plus `**Execution mode:**`.
- AC-29: `docs/SPEC_INDEX.md` links the renamed doc.

#### REQ-009: Entry files agree on facts

- AC-20: `AGENTS.md` build step 1 is character-for-character the same as master's, including master's em dash (U+2014) after "Deployed skeleton": `1. Deployed skeleton <U+2014> FastAPI on Render, green /health/ready, migrations run.`
  Already true on the new base; master made this change.
- AC-21: Neither `AGENTS.md` nor `CLAUDE.md` mentions Railway.
- AC-22: In both files, the ownership row for Jade names the Flutter app, and the row for Arnold names the dashboard.
- AC-23: In both files, the `Public REST + SSE` contract row names `dashboard (Arnold)`.

#### REQ-010: Plan execution modes

The two skill copies merge into one skill with two execution modes.

| Mode | Behavior |
|---|---|
| `auto` | Run every approved phase in order; stop only for a failed gate, a real blocker, or a decision that is Len's. |
| `hard-stop` | After each phase's verification, stop, report, and wait for Len's explicit go-ahead before the next phase. |

- The mode lives in the plan doc header as `**Execution mode:** auto` or `**Execution mode:** hard-stop`, so every agent reads the same value from the same file.
- When creating a plan, the skill proposes a default by scale, and Len confirms it with the plan:
  `hard-stop` when the plan changes product code, a shared contract (`docs/02` to `docs/06`), migrations, firmware, or deployment config, or has more than 3 phases; `auto` otherwise.
- The toggle is `/implementation-plan mode auto` or `/implementation-plan mode hard-stop` in Claude Code, or the same words as a chat message to any agent.
  It edits only the header field of the plan named in the active `HANDOFF.md` (or the single active plan), and asks if that is ambiguous.
  A toggle takes effect at the next phase boundary, never mid-phase.
- Mode does not change the commit policy; a plan may still override commits, as Part B does.

Acceptance criteria:

- AC-24: `.agents/skills/implementation-plan/SKILL.md` and `.claude/skills/implementation-plan/SKILL.md` are byte-identical.
- AC-25: The skill names both modes, the header field, both toggle forms, and the next-phase-boundary rule.
- AC-26: The skill frontmatter has an `argument-hint` that includes `mode`.
- AC-27: The skill keeps the handoff wording "in the approved doc, linked from the current handoff".
- AC-28: A Claude Code session given `/implementation-plan mode hard-stop` in a repo with an `auto` plan changes that plan's header to `hard-stop` and leaves its phases untouched.

### C.2 Implementation plan

Work in the worktree `.claude/worktrees/handoff-on-master` on branch `claude/handoff-and-security-report`.
No commits, no product code, no em dashes in new text, and never touch `docs/security-audit/`.

- **Execution mode**: auto (docs and agent tooling only, 3 phases).
- **Test command**: `python -m unittest discover -s .agents/tests -v`
- **Lint command**: `python -m ruff check .agents/tests`
- **Starting state**: new tests fail for REQ-008, REQ-009 and REQ-010; those failures are the work.

#### Phase C1: Renumber (REQ-008)

- [ ] C1.1 Rename with `git mv docs/43_MULTI_AGENT_MEMORY_AND_HANDOFF_PLAN.md docs/58_MULTI_AGENT_HANDOFF_SPEC.md`.
- [ ] C1.2 Replace every live pointer to the old path or to `docs/43`: the `AGENTS.md` handoff section, the `.gitignore` comment, the template comment, the `test_handoff.py` docstring, and `HANDOFF.md`.
  Find them with `grep -rn -e "docs/43" -e "43_MULTI_AGENT" AGENTS.md CLAUDE.md .gitignore HANDOFF.md .agents`.
- [ ] C1.3 Update the Phase 1.1 code block in Part B to the new `.gitignore` comment so the doc matches the file.
- [ ] C1.4 Add a row for the doc to the "Current sources of truth" table in `docs/SPEC_INDEX.md`, with status `Active specification`.
- **Verify**: `test_spec_renumbered`, `test_no_live_pointer_to_old_spec`, `test_spec_is_indexed`, `test_spec_has_required_header`.

#### Phase C2: Entry-file facts (REQ-009)

- [x] C2.1 `AGENTS.md` line 18 already matches AC-20 on master; no edit.
- [ ] C2.2 `AGENTS.md` ownership table: Jade row to the Flutter app (mobile), Arnold row to the dashboard, ingest pipeline and gateway.
- [ ] C2.3 `Public REST + SSE` row in both `AGENTS.md` and `CLAUDE.md`: `backend (Lenard), dashboard (Arnold)`.
- [ ] C2.4 Check nothing else in either file says Railway.
- **Verify**: `test_entry_files_say_render_not_railway`, `test_ownership_matches_len`, `test_public_api_consumer_is_arnold`.

#### Phase C3: Plan execution modes (REQ-010)

- [ ] C3.1 Write one merged `implementation-plan` skill, starting from Len's toolkit version, which already has the handoff wording.
  On this branch the tracked `.agents/` copy is master's older hard-stop version, so start from `git show e5c538a:.agents/skills/implementation-plan/SKILL.md`, and add:
  - frontmatter `argument-hint: "[create <feature> | execute | status | mode auto|hard-stop]"`;
  - an "Execution mode" section with the table, default-by-scale rule, toggle forms, target-plan rule, and next-phase-boundary rule from REQ-010;
  - in "Create a plan", add `**Execution mode:**` to the plan header and propose the default to Len;
  - in "Execute or resume", replace "Proceed automatically through the remaining approved phases without requesting routine sign-off." with behavior that depends on the mode.
  Keep it short: the current `.agents/` copy is 42 lines, so aim for under 70.
- [ ] C3.2 Write the result byte-for-byte to both `.agents/skills/implementation-plan/SKILL.md` and `.claude/skills/implementation-plan/SKILL.md`; the `.claude/` copy is new on this branch.
- **Verify**: the `PlanModeSkill` tests pass; then run the opt-in `test_claude_toggles_plan_mode` (AC-28) with `HANDOFF_E2E=1`.

#### Phase C4: Evidence and handoff

- [ ] C4.1 Fast suite and lint green.
- [ ] C4.2 Record results in the Evidence table.
- [ ] C4.3 Write the departure handoff to Claude Code, `COMPLETED` if green.

### C.3 Scenario tests added

| # | Scenario | Covers | How |
|---|---|---|---|
| T11 | Renumbered spec, no stale pointers, required header | AC-17 to AC-19 | `test_handoff.py` `SpecDocument` |
| T12 | Entry files agree on Render and ownership | AC-20 to AC-23 | `test_handoff.py` `EntryFileFacts` |
| T13 | Skill copies identical and declare modes | AC-24 to AC-27 | `test_plan_mode.py` `PlanModeSkill` |
| T14 | Claude Code toggles a plan to `hard-stop` | AC-28 | `test_plan_mode.py` `test_claude_toggles_plan_mode`, opt-in |

### C.4 Follow-ups outside Part C

The move to `origin/master` unblocked these; each is a separate task for Len to schedule.

- Railway references still on master: `README.md`, contracts `docs/04_INGEST_API.md` and `docs/05_PUBLIC_API.md` (base URLs), `firmware/README.md`, and mobile comments and a test name.
  The contract base URLs are the priority because agents and teammates copy them; changing a contract means telling its owners first.
- Em dash cleanup in `AGENTS.md` and `CLAUDE.md`.
- Other skills differ between Len's local `.agents/skills/` and `.claude/skills/` toolkit copies: `council`, `security-audit`, and the six `ponytail` skills.
- T3 (worktrees) can now run, since the hook and rules are committed; T5 (Antigravity) needs a run outside Antigravity.
