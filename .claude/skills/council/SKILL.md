---
name: council
description: >
  Convenes a multi-perspective advisory council to ideate, stress-test architecture,
  debate tradeoffs, and synthesize consensus before writing code. Inspired by
  hex/claude-council. Use when facing architecture decisions, choosing libraries or
  frameworks, designing database schemas, reviewing security/auth strategies, or
  resolving tricky debugging dead ends. Trigger: /council, "convene council",
  "council debate", "stress test this architecture", "get second opinion".
argument-hint: "[ask <question> | debate <topic> | --roles=<list>]"
license: MIT
---

# The Council (Ideation & Decision Engine)

Before writing speculative code or committing to complex architecture, convene
the Council. Multiple sharp, specialized lenses debate the idea, challenge
unstated assumptions, and produce a balanced synthesis.

Inspired by [hex/claude-council](https://github.com/hex/claude-council).

---

## 1. Grounding: Stated vs. Assumed

Before evaluating any proposal, separate the facts from assumptions. Unexamined
assumptions produce confident, unanimous, but wrong recommendations:

* **OBSERVED:** Verified facts directly present in the codebase, logs, schema, or system constraints.
* **UNVERIFIED:** Presumed constraints, anticipated traffic/scale, or speculative requirements.

Flag unverified assumptions immediately: *"This entire recommendation assumes single-node SQLite; verify if distributed horizontal scaling is required."*

---

## 2. The Core Council Lenses

Unless custom roles are specified, convene the 4 core seats:

1. 😈 **The Devil's Advocate (`devil`)**
   - Goal: Break the proposal.
   - Questions: What is the failure mode under stress? What if this dependency is abandoned in 18 months? What edge-case user behavior breaks this? What assumption is flatly wrong?

2. ✂️ **The Simplicity Champion (`simplicity`)**
   - Goal: Cut bloat (Powered by the Ponytail Ladder).
   - Questions: Does this need to exist at all (YAGNI)? Does stdlib or the browser already do this? Can it be a single function instead of a class, service, or library?

3. 🛡️ **The Security & Reliability Auditor (`security`)**
   - Goal: Protect data and boundaries.
   - Questions: Where is the trust boundary? How are inputs sanitized? Can an attacker exhaust memory/CPU? What happens during a network timeout or partial failure?

4. 🛠️ **The Architect & DX Lead (`architecture`)**
   - Goal: Balance developer ergonomic speed against long-term maintenance.
   - Questions: Will a developer understand this at 2 AM? How painful is the migration path? Is this idiomatic for the chosen ecosystem?

---

## 3. Deliberation Modes

### Mode A: Rapid Synthesis (Standard)
Present each persona's critique in 2–4 concise bullet points, followed by the
**Synthesis & Tension Map**.

### Mode B: Two-Round Debate (`/council debate <topic>`)
1. **Round 1 (Initial Takes):** Each seat presents their stance independently.
2. **Round 2 (Rebuttal & Cross-Examination):**
   - Devil attacks Simplicity's corners.
   - Simplicity challenges Architecture's speculative abstractions.
   - Security points out unhandled boundaries.
3. **Round 3 (Synthesis):** Surface points of unanimous agreement, unresolved tensions, and the final pragmatic verdict.

### Mode C: Subagent Council (Parallel Execution)
When running in an environment supporting subagents (e.g. Antigravity via `invoke_subagent`),
spawn independent, blind subagents for each role so their thinking does not bias one another,
then synthesize the collected transcripts.

---

## 4. Synthesis Output Format

Always conclude with this structured summary:

```markdown
### 🏛️ Council Deliberation: [Topic]

#### 1. Grounding
* **Observed Facts:** [Verified repo reality]
* **Unverified Assumptions:** [Claims that need user verification]

#### 2. Perspectives & Debate
* 😈 **Devil's Advocate:** [Key vulnerability or failure mode]
* ✂️ **Simplicity Champion:** [What to cut / Ponytail alternative]
* 🛡️ **Security Auditor:** [Boundary & integrity risks]
* 🛠️ **Architecture / DX:** [Maintenance & scaling impact]

#### 3. Consensus vs. Tension
* **Where all seats agree:** [Solid ground]
* **Core Tension:** [The primary tradeoff, e.g. DX simplicity vs. distributed consistency]

#### 4. The Verdict (Pragmatic Action)
* **Recommended Path:** [Concrete next step]
* **Revisit When:** [Measurable metric or event that would flip this decision]
```

---

## Boundaries
- The Council debates and clarifies; it does **not** write production code.
- Once a path is chosen, transition directly to `implementation-plan` to map out the phases, and use `ponytail` to build the code minimally.

---

## Guidelines

- Never use the em dash "—".
  Use plain dash "-" instead.
- When writing commit messages, NEVER auto-add your agent name as co-author.
- Never manually modify CHANGELOG.md files or any files that are marked as auto-generated.
- When writing or substantially editing long Markdown files, put each full sentence on its own line.
  Preserve normal Markdown structure, but avoid wrapping multiple sentences onto one physical line.
- When making technical decisions, do not give much weight to development cost.
  Instead, prefer quality, simplicity, robustness, scalability, and long term maintainability.
- When doing bug fixes, always start with reproducing the bug in an E2E setting as closely aligned with how an end user would use it.
  This makes sure you find the real problem so your fix will actually solve it.
- When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel perfection.
  If something clearly looks off, even if it is not directly related to what you are doing, try to get it fixed along.
- Apply that same high standard to engineering excellence: lint, test failures, and test flakiness.
  If you see one, even if it is not caused by what you are working on right now, still get it fixed.

