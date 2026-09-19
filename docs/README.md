# Documentation Map and Naming Convention

Use this page before creating a document.
It keeps active delivery work separate from reference material and historical plans.

## Start Here

Agents should begin with the fast [SPEC_INDEX.md](SPEC_INDEX.md), then use this
page for naming, status, and authoring rules.

| Need | Document |
|---|---|
| Current product priorities | [`../README.md`](../README.md) |
| Project brief and build order | [`00_START_HERE.md`](00_START_HERE.md) |
| Scope exclusions and amendments | [`07_SCOPE_OUT.md`](07_SCOPE_OUT.md) |
| Current hybrid transport decision | [`55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`](55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md) |
| Aggregated architecture and data flow | [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) |
| Honest demo status and evidence | [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md) |
| Current executable pitch plan | [`43_DTI_PITCH_IMPLEMENTATION_PLAN.md`](43_DTI_PITCH_IMPLEMENTATION_PLAN.md) |
| External event deadlines | [`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md) |
| Shared technical contracts | [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md), [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md), [`04_INGEST_API.md`](04_INGEST_API.md), [`05_PUBLIC_API.md`](05_PUBLIC_API.md), [`06_DELIVERY_STATES.md`](06_DELIVERY_STATES.md), [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) |

`README.md` defines the current pitch priorities.
The numbered documents preserve decisions and evidence from earlier work.
When they conflict, record the conflict and follow the current README until the older document is reconciled.

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

Only one implementation plan may be `ACTIVE` at a time.
Add it to the current register below when work begins.
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

Only `ACTIVE` plans belong in the current work discussion.
Mark a finished plan `COMPLETE` after its evidence and commit are recorded.
Mark an obsolete plan `SUPERSEDED` and link the replacement at the top.
Do not delete historical documents. When a plan is verified complete, it may move to `docs/archive/plans/`. When a record is verified superseded or completed historical context, it may move to `docs/archive/history/` after all references are updated. They remain part of the project record and explain earlier code, architectural decisions, and pitch material.

## Current Register

| Status | Document | Purpose |
|---|---|---|
| ACTIVE | [`57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md`](57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md) | Repository structure cleanup without behavior change |

Add a row here when a document becomes `ACTIVE`.
Remove it when the document becomes `COMPLETE`, `BLOCKED`, or `SUPERSEDED`.

## Existing Records

| Group | Files |
|---|---|
| Foundation and shared contracts | `00` to `08` |
| Earlier planning and implementation records | `11`, `13` to `26`, `29` to `31`, `33`, `34`, `36` to `42`, `46` |
| Dated audits and verification | [`audits/`](audits/) |
| Current pitch plan | `43` |
| Visual design guide | `47` |
| Historical records and legacy guides | [`archive/history/`](archive/history/) |
| Archived completed plans | [`archive/plans/`](archive/plans/) |
| Reference guides | [`guides/`](guides/) |
| Hybrid transport decision, technical architecture spec, and cleanup plan | `55`, `56`, `57` |
| Design references and competition materials | [`design-reference/`](design-reference/), [`competitions/`](competitions/) |
| Canonical PRD | [`Aqone_PRD (2).md`](Aqone_PRD%20(2).md) |

`Aqone_PRD (2).md` retains its supplied filename because it is the canonical PRD.
