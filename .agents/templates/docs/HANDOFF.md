# Agent Handoff

<!--
Template for the root HANDOFF.md. Spec: docs/58_MULTI_AGENT_HANDOFF_SPEC.md.
Copy to the working tree root, replace every {placeholder}, delete this comment.
Update after every verified step, not only at the end.
Keep it to about 60 lines: summaries only, no transcripts, tool dumps, or full diffs.
Never write secret values. Name them by key instead (LOAM_KEY, DATABASE_URL).
-->

- **Status**: ACTIVE
- **Updated**: {YYYY-MM-DDTHH:MM:SS+08:00}
- **Agent**: {Claude Code | Codex | Antigravity} ({model})
- **Branch**: `{branch}`
- **Worktree**: `{absolute path of this working tree}`

## 1. Objective

{What the task is, in one to three sentences.}

## 2. Approved Scope

- {`docs/NN_NAME.md` Revision N, approved by Len {timestamp}, or "none - no spec for this task"}

## 3. Settled Decisions

- {Decision} - rejected {alternative} because {reason}.

## 4. Done and Verified

- {Step} - verified by `{command}` ({result}).

## 5. Working Tree Evidence

As of **Updated** above.
Any file changed after that time is unrecorded work.

- **Modified**: `{path}`
- **Untracked**: `{path}`
- **Last check**: `{test or lint command}` - {pass / fail, with count}

## 6. The Baton

> {One concrete action: the exact command to run, or the file and the change to make.}

## 7. Open Questions for Len

- {Blocking decision, or "none"}
