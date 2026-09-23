---
name: spec
description: >
  Explore Len's product with questions, then create or revise organized product
  and feature specs with observable acceptance criteria and explicit approval.
  Use for spec writing, requirements discovery, or organizing overlapping specs.
  Execution tasks belong in the implementation-plan skill.
license: MIT
---

# Spec discovery and maintenance

Read project `AGENTS.md` for Len's authority, evidence, and preservation rules.
Read `docs/SPEC_INDEX.md` and `HANDOFF.md` when present, then inventory existing specs before creating any file.
Adopt an established project convention rather than silently creating a second documentation tree.
If conflicting documents exist, identify the conflict for Len; do not arbitrarily pick the newest filename as authoritative.

## Discover the product

Explore the whole product first, then detail one feature at a time.
Ask focused rounds of roughly 4-6 questions in chat, with sensible defaults labeled as proposals.
Cover users, real scenarios, all planned features, main flows, shared data, system boundaries, architecture, and major constraints.
Summarize confirmed decisions and remaining gaps after each round.
Use Council perspectives for consequential architecture decisions, not routine wording choices.
Choose frameworks and libraries per project; do not assume a universal Flutter stack.

For Flutter Android features, consider offline behavior, permissions, storage and recovery, navigation, accessibility, error states, and supported Android versions.
For hardware features, separate desired capabilities, assumptions, operating conditions, and evidence from bench or field checks.
Ask only questions relevant to the project and never add a requirement solely to fill a heading.
Resolve blocking decisions before presenting the baseline for Len's chat approval.

## Author and reuse

Read the relevant templates in `.agents/templates/docs/`, installed by `len-toolkit start`.
In the toolkit source checkout, their source is `templates/docs/`.
Create only documents that are useful now; use an index and product categories as the project baseline grows.
Keep one stable `FEAT-NNN-name.md` per feature and allocate its ID after checking the index.
Refinements update that file instead of making daily copies.
Record creation and substantive-update timestamps as ISO 8601 with `+08:00`, revision, and status.
Archive superseded documents, link them to their replacement, update incoming links and the index, and preserve existing history.

A feature spec contains purpose, scope and non-goals, flows, requirements with observable acceptance criteria, data/interfaces, quality constraints, decisions/assumptions, and open questions/readiness.
Use `REQ-001` IDs within a feature and `FEAT-001/REQ-001` in cross-document references.
Cover relevant loading, empty, error, recovery, permission-denied, and offline states.
Reference shared requirements instead of copying them into every feature.
Keep task checkboxes, commands to execute, phase progress, and file-edit recipes in the implementation plan.

## Approval and handoff

Present the baseline and architecture for Len's explicit approval, then each detailed feature spec and its implementation plan together.
Record actual chat approval against exact revisions in the approved doc's own header (status, revision, timestamp); draft prose is not approval.
A behavior, architecture, or acceptance-criteria change requires a revised approval for affected work.
Editorial corrections do not authorize new behavior.
After approval, update the single root `HANDOFF.md` from `.agents/templates/docs/HANDOFF.md`, linking the approved doc and revision, and the execution scope.
When asked only to draft or review specs, do not start implementation.
