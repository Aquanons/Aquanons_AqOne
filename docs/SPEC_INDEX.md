# AqOne documentation index

This is the fast entry point for agents and contributors.
The detailed naming, status, and authoring rules live in [`README.md`](README.md).

## Current sources of truth

| Need | Document | Status |
|---|---|---|
| Current priorities and setup | [`../README.md`](../README.md) | Active |
| Project brief and build order | [`00_START_HERE.md`](00_START_HERE.md) | Foundation |
| Product scope and roadmap | [`Aqone_PRD (2).md`](Aqone_PRD%20(2).md) | Canonical product scope |
| Scope exclusions and amendments | [`07_SCOPE_OUT.md`](07_SCOPE_OUT.md) | Foundation |
| Hybrid transport architecture decision | [`55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`](55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md) | Active decision |
| Aggregated architecture and data flow | [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) | Active specification |
| Demo evidence and implementation status | [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md) | Evidence ledger |
| Pitch handoff | [`43_DTI_PITCH_IMPLEMENTATION_PLAN.md`](43_DTI_PITCH_IMPLEMENTATION_PLAN.md) | Blocked - Phase 4 needs handset, buoy and rehearsal evidence |
| Repository structure cleanup | [`57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md`](archive/plans/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md) | Completed cleanup plan |
| External event deadlines | [`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md) | Active |
| Cross-agent memory and handoff | [`58_MULTI_AGENT_HANDOFF_SPEC.md`](58_MULTI_AGENT_HANDOFF_SPEC.md) | Active specification |
| Edge-case remediation plan | [`62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`](62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md) (tracks `62A` to `62D`), design [`61`](61_EDGE_CASE_REMEDIATION_DESIGN.md), findings [`60`](60_EXTREME_EDGE_CASE_REPORT.md), evidence [`edge-remediation/`](edge-remediation/) | Active - B, M, W merged; Phase I pending |
| Critical edge cases (C1-C14) | [`66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md`](66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md), evidence [`edge-remediation/EVIDENCE-critical.md`](edge-remediation/) | Approved Rev 2 (Phase 6 needs approval) - Phase 1 next |
| Fisher friction reduction (handset UX) | Spec [`64_FISHER_FRICTION_REDUCTION_SPEC.md`](64_FISHER_FRICTION_REDUCTION_SPEC.md), plan [`65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md`](65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md) | Approved Rev 2 - queued behind plan 66 (Critical edge cases); field session after RSTW |
| Render free-tier database rotation | [`runbooks/RENDER_FREE_DB_ROTATION.md`](runbooks/RENDER_FREE_DB_ROTATION.md) | Active runbook (expiry around 2026-10-15) |
| Security audit remediation | [`archive/plans/59_SECURITY_AUDIT_REMEDIATION_IMPLEMENTATION_PLAN.md`](archive/plans/59_SECURITY_AUDIT_REMEDIATION_IMPLEMENTATION_PLAN.md), evidence [`security-audit/`](security-audit/) | Completed plan |

## Shared contracts

| Subsystem | Contract |
|---|---|
| Architecture | [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) |
| Technical architecture and data flow | [`56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md) |
| Boat pod and relay LoRa frame | [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md) |
| Phone-to-pod WiFi | [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md) |
| Gateway ingest | [`04_INGEST_API.md`](04_INGEST_API.md) |
| Public REST and SSE | [`05_PUBLIC_API.md`](05_PUBLIC_API.md) |
| Delivery states | [`06_DELIVERY_STATES.md`](06_DELIVERY_STATES.md) |
| Mobile localization | [`22_LOCALIZATION_PLAN.md`](22_LOCALIZATION_PLAN.md) |
| Mobile test fixtures | [`21_WEEK1_CONTRACT_FIXTURES.md`](21_WEEK1_CONTRACT_FIXTURES.md) |
| AI accuracy and data protocol | [`49_AI_ACCURACY_DATA_PROTOCOL.md`](49_AI_ACCURACY_DATA_PROTOCOL.md) |
| Field measurement & commissioning | [`50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md`](50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md) |
| Communication opportunity & delivered lead | [`51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md`](51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md) |
| Independent labels & drill manifests | [`52_INDEPENDENT_LABELS_AND_DRILL_MANIFESTS.md`](52_INDEPENDENT_LABELS_AND_DRILL_MANIFESTS.md) |
| Field readiness & measurement handoff | [`54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md`](54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md) |

## Find documents by lifecycle

| Lifecycle | Location or starting point |
|---|---|
| Active work | [`README.md#current-register`](README.md#current-register) |
| Audits and verification | [`audits/`](audits/) |
| Completed plans | [`archive/plans/`](archive/plans/) — only records whose header says `COMPLETE` and have no live path references |
| Engineering guides | [`guides/`](guides/) |
| Design references | [`design-reference/`](design-reference/) |
| Competition and workshop materials | [`competitions/`](competitions/) |

## Organization rules

- Stable contract paths remain unchanged.
- A document is moved only after all repository references are found and updated.
- `ACTIVE` and `COMPLETE` status comes from the document header or current register, not the filename number alone.
- Dated audit reports are read-only records and belong in `audits/` after their links are rewritten.
- Completed plans belong in `archive/plans/` only when no code, test, agent rule, or active document depends on their current path.

See [`48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md`](archive/plans/48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md) for the phased move and verification gates.
