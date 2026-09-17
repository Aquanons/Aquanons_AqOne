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
| Demo evidence and implementation status | [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md) | Evidence ledger |
| Current pitch handoff | [`43_DTI_PITCH_IMPLEMENTATION_PLAN.md`](43_DTI_PITCH_IMPLEMENTATION_PLAN.md) | Active |
| External event deadlines | [`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md) | Active |

## Shared contracts

| Subsystem | Contract |
|---|---|
| Architecture | [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) |
| Buoy-to-gateway LoRa frame | [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md) |
| Phone-to-buoy WiFi | [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md) |
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
| Workshop material | [`dti-workshop/`](dti-workshop/) |

## Organization rules

- Stable contract paths remain unchanged.
- A document is moved only after all repository references are found and updated.
- `ACTIVE` and `COMPLETE` status comes from the document header or current register, not the filename number alone.
- Dated audit reports are read-only records and belong in `audits/` after their links are rewritten.
- Completed plans belong in `archive/plans/` only when no code, test, agent rule, or active document depends on their current path.

See [`48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md`](48_DOCS_REORGANIZATION_IMPLEMENTATION_PLAN.md) for the phased move and verification gates.
