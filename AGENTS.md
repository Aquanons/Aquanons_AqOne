# AGENTS.md

Instructions for AI coding agents working in this repository. Read this before
changing anything. The canonical project brief is `docs/00_START_HERE.md`.
Before implementation, read [`docs/SPEC_INDEX.md`](docs/SPEC_INDEX.md), the [current work and ownership register](docs/README.md#current-register), this worktree's `HANDOFF.md` if present, and the applicable approved spec, contract, plan, and evidence.
`WHAT_NEEDS_TO_BE_DONE.md` is only a pointer to the current work register.

## One-line project

Offline SOS mesh for small-scale fishermen in New Washington, Aklan (no mobile
signal at sea): phones hand an SOS to anchored LoRa buoys over WiFi, buoys
relay over LoRa to a gateway with internet, the gateway forwards to a FastAPI
backend, and the backend pushes the SOS to an MDRRMO dashboard over SSE.

## Build order — strictly sequential

Do NOT start a step until the previous one demonstrably works. Do NOT skip
steps. If you are unsure whether a step is done, ask.

1. Deployed skeleton — FastAPI on Render, green `/health/ready`, migrations run.
2. Two radios talk — raw LoRa packet between two ESP32s, no protocol.
3. Buoy → gateway → backend — button press on a buoy creates a real SOS row.
4. Phone → buoy → backend — phone in airplane mode, SOS lands.
5. Dashboard live feed + acknowledge — full path visible, ack persists.
6. Range test outdoors — record actual metres in `docs/08_DEMO_AND_STATUS.md`.
7. Freeze, rehearse x3, record screencast.

## Ownership

| Person | Owns |
|---|---|
| Lenard | Lead dev — backend, architecture, deployment |
| Arnold | Dashboard, ingest pipeline, gateway |
| Daniel | Hardware/firmware — buoy. Critical path. |
| Jade | Flutter app (mobile) |
| Doreen Kay | UI/UX, pitch deck |

## Spec-first workflow

Before editing code, read the current work and ownership register in [`docs/README.md`](docs/README.md#current-register), check `git status` and `git diff --stat`, and read this worktree's `HANDOFF.md` if present.
Read the applicable approved product spec, decision, shared contract, implementation plan, acceptance criteria, and latest evidence before choosing an implementation.
Use the source hierarchy in `docs/README.md` when documents disagree; if the conflict affects scope, behavior, an interface, phase order, or ownership, stop and reconcile the documents before coding.
Do not implement from a draft, an unapproved plan, a stale handoff, or chat context when an approved source document exists.

Before starting work, make sure the current register names the human owner, active agent, branch and worktree, owned paths, current state, and one next action.
If no matching assignment exists, add one after the required spec and plan are approved.
Do not edit paths owned by another active agent or worktree; coordinate a handoff first.
Multiple plans may be active at once only when their path ownership is disjoint and the register records their dependencies.
Update the register when work starts, ownership or state changes, a phase gate passes or blocks, or work completes.
Record observed completion in the plan and relevant evidence document; the register summarizes that evidence and does not replace it.

## Skill routing

Repository skills live in `.agents/skills/`.
Read the relevant skill's `SKILL.md` before using it; skills guide the process but do not override approved specs, contracts, or ownership.

| Situation | Skill |
|---|---|
| Explore requirements or write a feature spec | `spec` |
| Ideate or compare consequential architecture and product tradeoffs | `council` |
| Break an approved feature into phases or resume execution | `implementation-plan` |
| Any code change, refactor, or dependency choice | `ponytail` (required by this repository) |
| Design or implement user interfaces | `ui-ux-pro-max` or `ui-styling` |
| Review security or perform an authorized security audit | `security-audit` |
| Change hard-to-test legacy code | `working-effectively-with-legacy-code` |
| Design data systems, schemas, or reliability behavior | `designing-data-intensive-applications` |

## Deliberately NOT building (do not implement)

These are scoped-out decisions, not gaps. See `docs/07_SCOPE_OUT.md` for the
full list and for the items that have since been amended into scope.

Still out: no photos, no fisheries-enforcement or surveillance features, no
LoRa downlink to the handset. Catch logging and its explicitly consented,
coarse aggregated activity heatmap are now in scope - see
`docs/07_SCOPE_OUT.md`'s "Amended — now in scope".

**Do not treat this file as the scope of record.** The canonical scope is
`Aqone_PRD (2).md` (v3.0); unbuilt sections there are tagged
`[Roadmap — not implemented]`. Advisories, accounts, "did not return" detection
and three AI models were once listed here as out of scope and now exist — an
outside audit read the stale version and reported the project as having built
neither AI nor a backend.

## Shared contracts (do not diverge from these)

All workstreams interoperate through these documents. If a contract needs to
change, update the doc first and tell the affected owners.

| Contract | Doc | Who consumes |
|---|---|---|
| LoRa binary frame | `docs/02_LOAM_PACKET_SPEC.md` | firmware (Daniel), gateway (Arnold) |
| Phone ↔ buoy WiFi HTTP | `docs/03_PHONE_BUOY_WIFI.md` | firmware (Daniel), mobile (Jade/Doreen) |
| Gateway → backend HTTPS | `docs/04_INGEST_API.md` | gateway (Arnold), backend (Lenard) |
| Public REST + SSE | `docs/05_PUBLIC_API.md` | backend (Lenard), dashboard (Arnold) |
| Delivery states | `docs/06_DELIVERY_STATES.md` | all — the four states are the product language |
| Mobile UI strings | `docs/22_LOCALIZATION_PLAN.md` | mobile (Jade/Doreen Kay) |

## Repository layout

```
backend/     FastAPI + PostgreSQL (Lenard)
  app/       application code
  migrations/  database migrations
  tests/
firmware/    ESP32-S3 + SX1262 firmware, PlatformIO
  buoy/      boat pod & sensor buoy firmware (Daniel)
  shore/     shore gateway receiver code (Arnold, Daniel)
mobile/      Flutter app (Jade, Doreen Kay)
  lib/l10n/  ARB translation files, en/fil/akl. Read its README first.
docs/        numbered specs; 00 is the brief, 08 is the status table
```

## Definition of done (whole build)

- [ ] Phone in airplane mode sends an SOS that reaches the dashboard
- [ ] Dashboard acknowledge persists across a reload
- [ ] The four delivery states are visible and honest in the app
- [ ] Deployed, healthcheck green, demo URL reachable from outside the venue
- [ ] Repo public, no secrets, README with setup instructions
- [ ] Screencast recorded
- [ ] `docs/08_DEMO_AND_STATUS.md` status table reflects reality

## Mobile UI strings are localized (en / fil / akl)

The handset app ships English, Tagalog and Aklanon. Full plan and phase order
in `docs/22_LOCALIZATION_PLAN.md`. Three rules that will cost you a debugging
session if you miss them:

- **New user-facing text goes in `mobile/lib/l10n/app_en.arb`** with an
  `@key` description, then is read via
  `AppLocalizations.of(context).yourKey`. Do not add bare `Text('...')`
  literals to `mobile/lib/`. Log messages, SQL, and wire values stay as
  literals — those are not UI.
- **Never put display text on an enum.** Const enum fields cannot see a
  `BuildContext`, so they can never be translated. `DeliveryState`,
  `SeaStatus` and `RiskLevel` keep only wire values, ordering and colours;
  their text lives in a `…L10n` extension that takes an `AppLocalizations`.
  Copy that pattern. `WeatherCondition` still carries English labels and has
  not been converted yet — it is the last one left.
- **The Tagalog locale code is `fil`, not `tl`,** and Aklanon (`akl`) has no
  Flutter localizations at all — `mobile/lib/core/l10n_fallback.dart` handles
  the second problem and its delegates must stay last in the list.

Translations in `app_fil.arb` and `app_akl.arb` are unreviewed drafts. Do not
treat them as correct; see `mobile/lib/l10n/README.md`.

## Conventions

- Do not add code comments unless asked. Prefer self-documenting names.
- No secrets in the repo. Use `.env` locally (gitignored) and platform
  env vars in deployment. `*.env.example` files are allowed.
- Follow the build order above. Do not build ahead of the current step.
- If a task is ambiguous, ask before doing surprising or large work.
- Verification before completion: run the project's lint/tests for whatever
  you changed. The backend uses pytest + ruff once scaffolded; firmware uses
  PlatformIO build; mobile uses `flutter analyze` + `flutter test`.
- Never use the em dash "-". Use plain dash "-" instead.
- When writing commit messages, NEVER auto-add your agent name as co-author.
- Never manually modify CHANGELOG.md files or any files marked as auto-generated.
- When writing or substantially editing long Markdown files, put each full sentence on its own line. Preserve normal Markdown structure, but avoid wrapping multiple sentences onto one physical line.
- When making technical decisions, do not give much weight to development cost. Instead, prefer quality, simplicity, robustness, scalability, and long term maintainability.
- When doing bug fixes, always start with reproducing the bug in an E2E setting as closely aligned with how an end user would use it. This makes sure you find the real problem so your fix will actually solve it.
- When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel perfection. If something clearly looks off, even if it is not directly related to what you are doing, try to get it fixed along.
- Apply that same high standard to engineering excellence: lint, test failures, and test flakiness. If you see one, even if it is not caused by what you are working on right now, still get it fixed.

## Agent handoff

The live handoff file is `HANDOFF.md` at the root of the current worktree, written from `.agents/templates/docs/HANDOFF.md`.
Each git worktree maintains its own `HANDOFF.md`, which is ignored and never committed.
The specification is in `docs/58_MULTI_AGENT_HANDOFF_SPEC.md`.
On arrival, read `HANDOFF.md` if present before taking action.
If **Status** is `COMPLETED`, treat the handoff as background context only and follow the user prompt.
If **Status** is `ACTIVE`, run `git status` and `git diff --stat` to inspect the working tree.
Compare that output against **Working Tree Evidence** and report any mismatch to the user before your first edit.
Treat any file changed after the **Updated** timestamp as unrecorded work.
Continue execution from **The Baton** unless the user directs otherwise.
On departure during multi-step tasks, update `HANDOFF.md` after every verified step and before stopping.
Set **Updated** to the current timestamp in ISO 8601 format with `+08:00`.
Specify exactly one concrete action in **The Baton**, giving a command or file edit rather than a vague goal.
Trivial single edits or one-shot questions require no handoff update.
When the overall objective is done and verified, set **Status** to `COMPLETED` with final verification evidence.
Do not delete `HANDOFF.md` on completion so the next arriving agent can see what just finished.
Name secrets by environment variable or config key, such as `LOAM_KEY` or `DATABASE_URL`, and never write their values.
Formal approvals are recorded in the approved doc header, and `HANDOFF.md` only links to that document.

## Ponytail: lazy senior dev mode

Applies to every change in this repo. Source: https://github.com/dietrichgebert/ponytail

You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern that's already here, don't re-write it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs after you understand the problem, not instead of it: read the task and the code it touches, trace the real flow end to end, then climb.

Bug fix = root cause, not symptom: a report names a symptom. Grep every caller of the function you touch and fix the shared function once — one guard there is a smaller diff than one per caller, and patching only the path the ticket names leaves a sibling caller still broken.

Rules:

- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins, but only once you understand the problem. The smallest change in the wrong place isn't lazy, it's a second bug.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Pick the edge-case-correct option when two stdlib approaches are the same size, lazy means less code, not the flimsier algorithm.
- Mark deliberate simplifications that cut a real corner with a known ceiling (global lock, O(n²) scan, naive heuristic) with a `ponytail:` comment naming the ceiling and upgrade path.

Not lazy about: understanding the problem (read it fully and trace the real flow before picking a rung, a small diff you don't understand is just laziness dressed up as efficiency), input validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs (the platform is never the spec ideal, a clock drifts, a sensor reads off), anything explicitly requested. Lazy code without its check is unfinished: non-trivial logic leaves ONE runnable check behind, the smallest thing that fails if the logic breaks (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.


