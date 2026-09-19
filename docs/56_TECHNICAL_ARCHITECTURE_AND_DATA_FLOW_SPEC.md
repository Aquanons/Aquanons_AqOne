# 56 — Technical Architecture and Data Flow Specification

**Status:** ACTIVE  
**Owner:** Team Aquanons (Architecture & Systems)  
**Created:** 2026-09-18  
**Updated:** 2026-09-18  
**Related:** [`00_START_HERE.md`](00_START_HERE.md), [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md), [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md), [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md), [`04_INGEST_API.md`](04_INGEST_API.md), [`05_PUBLIC_API.md`](05_PUBLIC_API.md), [`06_DELIVERY_STATES.md`](06_DELIVERY_STATES.md), [`07_SCOPE_OUT.md`](07_SCOPE_OUT.md), [`17_AI_EXPLAINED_SIMPLY.md`](17_AI_EXPLAINED_SIMPLY.md), [`19_HELTEC_DATA_FLOW.md`](19_HELTEC_DATA_FLOW.md), [`45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`](45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md), [`55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`](55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md)

---

## 1. Executive Summary & Purpose

This specification establishes the canonical end-to-end technical architecture and data flow model for Project AqOne.

AqOne provides an offline emergency safety mesh and maritime decision-support platform for small-scale artisanal fishermen operating in New Washington, Aklan, and surrounding coastal waters where cellular connectivity is nonexistent.

To ensure extreme reliability during life-critical operations while enabling modern predictive safety intelligence, the system separates data processing into **five decoupled functional lanes** spanning **six architectural lifecycle phases**. This specification formally documents these pathways and accompanies the high-resolution architecture diagrams published in [`artifacts/`](../artifacts/).

---

## 2. Architectural Lifecycle Phases

The system architecture organizes all components into six sequential lifecycle phases:

```
┌─────────────────┐   ┌─────────────┐   ┌───────────┐   ┌─────────────────────┐   ┌─────────────────────────┐   ┌────────────────────────┐
│ SOURCE AND DATA │──►│ EDGE DEVICE │──►│ TRANSPORT │──►│ INGRESS AND STORAGE │──►│ PROCESSING AND DECISION │──►│ OUTPUT AND HUMAN ACTION│
└─────────────────┘   └─────────────┘   └───────────┘   └─────────────────────┘   └─────────────────────────┘   └────────────────────────┘
```

1. **Source and Data:** The physical, user, or environmental point of origin (fisherman button press, handset sensors, marine barometers, meteorological feeds, or user catch logs).
2. **Edge Device:** Local vessel and shore hardware responsible for local caching, store-and-forward queueing, cryptographic signing, and radio transmission (mobile handset, Heltec V3 ESP32-S3 boat pod, stationary relay buoys).
3. **Transport:** The physical communication channels (short-range WiFi SoftAP 2.4 GHz, long-range LoRa 915 MHz binary frames, and secure HTTPS over cellular/fiber internet).
4. **Ingress and Storage:** The backend intake layer (FastAPI), HMAC/API-key validation, idempotent deduplication, PostgreSQL append-only event logging, and state projection.
5. **Processing and Decision:** Business logic, predictive AI decision support (squall nowcasting, localized danger-zone scoring, trip anomaly detection, leeway drift modeling), and official emergency precedence enforcement.
6. **Output and Human Action:** Operator and end-user surfaces (MDRRMO live dashboard feed, mobile outbox reconciliation, LGU/BFAR aggregated heatmaps, and search-and-rescue dispatch coordination).

---

## 3. The Five Functional Data-Flow Lanes

```
Lane 1: EMERGENCY SOS            [Manual distress; 100% deterministic; zero AI dependencies]
Lane 2: ENVIRONMENTAL WARNING    [Sensor & weather nowcasting; official warnings take precedence]
Lane 3: TRIP ANOMALY             [Per-vessel departure/return tracking; human verification queue]
Lane 4: DRIFT AND SEARCH         [Post-incident SAR decision support; Bayesian search retasking]
Lane 5: CONSENTED CATCH ACTIVITY [Voluntary catch logging; k-anonymity; strictly isolated from LoRa]
```

---

### Lane 1: Emergency SOS Data Flow

The emergency SOS pathway is the core safety spine of AqOne. It is designed to be **100% deterministic, resilient to connectivity outages, and strictly independent of any AI model**.

```
[Fisherman] ──► [Phone UI / Outbox] ──WiFi HTTP──► [Boat Pod (Heltec V3)] ──LoRa 915MHz──► [Tall Shore Gateway]
                                                                                                  │
                                                                                                HTTPS
                                                                                                  ▼
[Fisherman Handset] ◄──Acknowledged State── [MDRRMO Dashboard] ◄──SSE / REST── [FastAPI + PostgreSQL]
```

#### Detailed Execution Steps:
1. **Trigger:** A fisherman taps the emergency SOS button on the Flutter mobile app or presses the physical distress button wired to the boat safety pod.
2. **Handset Queuing:** If triggered from the phone, the app encapsulates the payload (`local_id`, `vessel_id`, `timestamp`, `lat`, `lon`, `emergency_type`, `optional_note`).
3. **Transport Selection:**
   - *Direct Internet Available:* If the phone unexpectedly has cellular data, it posts directly to `POST /api/sos` (`S1` connector).
   - *Offline (Standard):* The phone connects to the boat pod's local WiFi access point (`AqOne-Pod-XXXX`, `192.168.4.1`) and issues `POST /v1/sos` ([`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md)).
   - *Disconnected:* If neither is reachable, the message persists in the local SQLite outbox in state `SAVED`.
4. **Pod Queueing:** The boat pod verifies the frame, stores it in non-volatile flash memory, transitions the reported delivery state to `RELAYED`, and constructs a binary LoAM frame ([`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md)) signed with the device HMAC key.
5. **LoRa Transmission:** The pod transmits over LoRa 915 MHz (`HOPS = 0`). If the shore gateway is out of line-of-sight, an optional moored relay buoy receives the packet, validates the seen-set cache, decrements TTL, and forwards the packet.
6. **Gateway Intake:** The tall shore gateway receives the LoRa frame, verifies the signature, maps external hardware IDs to internal backend UUIDs, and forwards the packet via HTTPS `POST /api/sos` ([`04_INGEST_API.md`](04_INGEST_API.md), [`19_HELTEC_DATA_FLOW.md`](19_HELTEC_DATA_FLOW.md)).
7. **Backend Ingestion:** FastAPI validates the payload, applies idempotency deduplication on `(src_ext_id, seq)` or `sos_id`, writes to the append-only `events` log, updates the `sos_events` projection, and pushes the event across Server-Sent Events (SSE) to connected dashboard clients. State becomes `DELIVERED`.
8. **MDRRMO Responder Loop:** An MDRRMO operator sees the new emergency row on the live dashboard, confirms dispatch details, and clicks "Acknowledge" with optional ETA and response notes.
9. **Return Acknowledgement:** The acknowledge action persists in PostgreSQL and broadcasts via SSE/REST. Where downlink return traffic is supported, the pod receives the ack and returns it to the handset outbox, advancing the state to `ACKNOWLEDGED`. If no downlink exists, the handset state remains honestly at `DELIVERED`.

---

### Lane 2: Environmental Warning Data Flow

Provides localized marine hazard intelligence and squall nowcasting based on coastal barometer telemetry and open weather feeds.

```
[Buoy/Pod Barometer + Marine Forecasts] ──► [Normalization & Ingest] ──► [Quality & Freshness Gate]
                                                                                 │
                                                  ┌──────────────────────────────┴──────────────────────────────┐
                                                  ▼                                                             ▼
                                      [Squall Nowcasting Model]                                     [Danger-Zone GBDT Model]
                                                  └──────────────────────────────┬──────────────────────────────┘
                                                                                 ▼
                                                                     [Combine Model Evidence]
                                                                                 │
                                                    ┌────────────────────────────┴────────────────────────────┐
                                         [Official Warning Exists?]                                [No Official Warning]
                                                    │                                                         │
                                                    ▼                                                         ▼
                                       [Official Warning Precedence]                               [Candidate Advisory]
                                                    └────────────────────────────┬────────────────────────────┘
                                                                                 ▼
                                                                [Publish Advisory to PostgreSQL]
                                                                                 ▼
                                                          [Mobile Warning & Dashboard Marine Map]
```

#### Detailed Execution Steps:
1. **Inputs:** Buoy-mounted barometers (BMP280/MS5611), boat pod telemetry, PAGASA bulletins, and Open-Meteo marine wave/wind models.
2. **Quality Gate:** Data without valid timestamps or failing freshness thresholds (<3 hours) is discarded or marked degraded. The system refuses to declare conditions "safe" in the absence of valid data.
3. **Predictive Processing:**
   - *Squall Nowcaster:* Evaluates 1-hour and 3-hour barometric pressure tendencies ($\Delta P / \Delta t$) alongside wind gust ratios.
   - *Danger-Zone GBDT:* Evaluates bathymetry, swell direction, and coastline topography to assign localized risk tiers.
4. **Precedence Policy:** If PAGASA or MDRRMO issues an active gale warning, tropical cyclone wind signal, or sea travel advisory, that official determination **strictly overrides** any statistical model output.
5. **Dissemination:** Published advisories are cached in PostgreSQL and rendered on the MDRRMO operations dashboard and cached to mobile handsets before vessels depart cell range.

---

### Lane 3: Trip Anomaly Detection Data Flow

Monitors departures, active maritime transits, and expected return windows to detect overdue or anomalous vessel behavior before an emergency SOS is manually triggered.

```
[Vessel Departure Event] ──► [Causal History Filter] ──► [Sufficient Baseline?]
                                                                 │
                                    ┌────────────────────────────┴────────────────────────────┐
                                   YES                                                        NO
                                    ▼                                                         ▼
                       [Build Per-Vessel Profile]                                  [Cold-Start Review Queue]
                                    │                                                         │
                        [Deviation > Threshold?]                                              ▼
                                    │                                              [Manual Watchlist]
                       ┌────────────┴────────────┐
                      YES                        NO
                       ▼                         ▼
             [Create Anomaly Case]     [Continue Monitoring]
                       ▼
             [MDRRMO Responder Review]
                       │
              [Escalate to Incident?]
                       │
             ┌─────────┴─────────┐
            YES                  NO
             ▼                   ▼
    [Connector D1: Drift]   [Dismiss / Note]
```

#### Detailed Execution Steps:
1. **Trip Registration:** When a registered vessel departs, an active trip session is initiated (via handset check-in or shore radio log).
2. **Causal History Filter:** To eliminate data leakage, the anomaly engine filters history strictly causally (only voyages completed prior to the current trip are evaluated).
3. **Baseline Verification:**
   - *Sufficient Profile ($\ge 5$ prior trips):* The model calculates vessel-specific expected trip duration, usual gear type, and customary fishing grounds.
   - *Insufficient Profile (Cold Start):* The trip is routed to the "Cold-Start Watchlist", prompting human dispatchers to verify float plans manually.
4. **Deviation Evaluation:** If elapsed trip duration exceeds $1.5\times$ historical average or the vessel fails to return before the declared curfew without contact, an `ANOMALY_CASE` record is logged in PostgreSQL.
5. **Human Verification:** The case surfaces on the MDRRMO dashboard. Responders initiate a marine VHF radio check or contact the vessel's emergency shore contact.
6. **Escalation Boundary:** An anomaly case **never** triggers autonomous SAR deployment. Only after responder confirmation is the event escalated to an official incident, passing the last known position datum (`D1`) to Lane 4.

---

### Lane 4: Drift and Search Decision Support Data Flow

Provides probabilistic search sector retasking for search-and-rescue (SAR) teams following a confirmed distress event or escalated anomaly.

```
[Confirmed Incident Datum (D1)] ──► [Environmental Forcing (Wind, Currents, Coastline)]
                                                    │
                                     [Live Current Field Available?]
                                                    │
                                ┌───────────────────┴───────────────────┐
                               YES                                      NO
                                ▼                                       ▼
                     [Use Observed Current]                  [Mark Degraded Mode]
                                └───────────────────┬───────────────────┘
                                                    ▼
                                    [Monte Carlo Leeway Simulation]
                                 (Run particles with windage coefficients)
                                                    ▼
                                     [Search Probability Grid]
                                   (50%, 75%, 95% search contours)
                                                    ▼
                                         [Rank Search Sectors]
                                                    │
                                      [Negative Search Evidence?]
                                                    │
                                ┌───────────────────┴───────────────────┐
                               YES                                      NO
                                ▼                                       ▼
                       [Update Posterior]                     [Base Search Plan]
                                ▼                                       ▼
                      [Revised Search Plan]                   [Publish to Store]
                                └───────────────────┬───────────────────┘
                                                    ▼
                                        [MDRRMO SAR Command Map]
```

#### Detailed Execution Steps:
1. **Incident Datum (`D1`):** Ingests confirmed incident coordinates, timestamp, vessel class (e.g., motorized banca with outriggers), and occupant count.
2. **Environmental Forcing:** Loads HYCOM/Copernicus surface currents, coastal tidal models for Aklan/Sibuyan Sea, and hourly wind velocity fields. If live currents are missing, the system explicitly flags the run as **Degraded Mode (Uncalibrated Climatology)**.
3. **Leeway Simulation:** Executes Monte Carlo ensemble runs (typically 1,000–5,000 particles) using empirical drift leeway coefficients appropriate for Philippine outrigger bancas. Coastline boundary conditions simulate beaching/stranding.
4. **Probability Density Grid:** Aggregates particles into spatial probability contours:
   - **50% Core Probability Zone:** Highest priority search sector.
   - **75% Secondary Zone:** Expansion search box.
   - **95% Outer Envelope:** Maximum containment area.
5. **Bayesian Posterior Update:** If SAR assets search a sector and report **negative visual contact**, the model incorporates this negative evidence, updates the probability distribution, and re-ranks the remaining search sectors.
6. **Advisory Surface:** The ranked sectors are delivered to the MDRRMO operations console. The system acts purely as an advisory decision-support tool; tactical SAR command remains with the Philippine Coast Guard and MDRRMO incident commander.

---

### Lane 5: Consented Catch Activity Data Flow

Supports sustainable fisheries documentation and municipal livelihoods. This pathway is **strictly isolated from emergency distress channels and is never transmitted over LoRa mesh bandwidth**.

```
[Fisherman Mobile App] ──► [Device Token Authentication] ──► [Catch Entry UI]
                                                                    │
                                                      [Local SQLite Secure Storage]
                                                                    │
                                                           [Cellular / WiFi Sync]
                                                                    │
                                                       [Backend Validation & Store]
                                                                    │
                                                      [Consent for Coarse Sharing?]
                                                                    │
                                        ┌───────────────────────────┴───────────────────────────┐
                                       YES                                                      NO
                                        ▼                                                       ▼
                             [Coarse Aggregation Engine]                             [Private Record Only]
                                        │
                           [Reporter Threshold Met (k>=5)?]
                                        │
                            ┌───────────┴───────────┐
                           YES                      NO
                            ▼                       ▼
                [Publish Heatmap Cell]     [Withhold Cell Display]
                            │                       │
                            ▼                       ▼
            [LGU / BFAR Aggregated Analytics]   [Preserve Fisher Privacy]
```

#### Detailed Execution Steps:
1. **Consent Gate:** Fishermen explicitly opt-in to record catch data (species, estimated weight, gear type, time).
2. **Offline Handset Storage:** Catches are logged locally into SQLite.
3. **Sync over High-Bandwidth Medium:** Logs sync **only** when the handset connects to cellular data or home WiFi; catch records are strictly prohibited from utilizing the LoRa radio link.
4. **Differential Privacy & k-Anonymity:** When generating aggregated fisheries maps for the municipal agriculture office (LGU) or BFAR:
   - Catch coordinates are snapped to a coarse grid (e.g., $1\times 1$ km or larger).
   - If fewer than $k$ (e.g., $k=5$) independent vessels reported catch in that cell, the cell data is withheld to prevent exposing individual honey-holes or identifying specific fishermen.

---

## 4. Architectural Rules and Non-Negotiables

| Principle | Architectural Rule | Enforcement Mechanism |
|---|---|---|
| **Distress Independence** | Emergency SOS must never depend on AI models, internet availability, or cloud services. | Pure deterministic C++/Python pipeline; flash queueing on pod; direct shore LoRa path. |
| **Honest Delivery States** | No UI surface may show a state that has not been cryptographically or protocol-acknowledged. | 4 explicit enum states: `SAVED` ➔ `RELAYED` ➔ `DELIVERED` ➔ `ACKNOWLEDGED`. No speculative states. |
| **LoRa Bandwidth Conservation** | LoRa airtime is reserved exclusively for emergency frames and critical telemetry. | Strict frame specification ([`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md)); non-emergency catch data blocked from LoRa. |
| **Human-in-the-Loop** | AI outputs are strictly decision-support advisories; they never trigger emergency alerts autonomously. | Mandatory responder review queue for trip anomalies and SAR sector deployment. |
| **Fisher Privacy** | Spatial fishing activities must never be exposed without explicit consent and aggregation. | k-anonymity aggregation engine with minimum reporter thresholds ($k \ge 5$). |

---

## 5. Artifact Directory Inventory

The diagrams representing this specification are maintained in the [`artifacts/architecture/`](../artifacts/architecture/) directory:

| Artifact | Format | Description |
|---|---|---|
| [`artifacts/architecture/AqOne_Aggregated_Technical_Architecture.docx`](../artifacts/architecture/AqOne_Aggregated_Technical_Architecture.docx) | Word Document | Landscape 22"x14.7" document containing the comprehensive single-page aggregated technical architecture. |
| [`artifacts/architecture/AqOne_Aggregated_Technical_Architecture.pdf`](../artifacts/architecture/AqOne_Aggregated_Technical_Architecture.pdf) | PDF Document | Direct standalone printable PDF of the aggregated architecture. |
| [`artifacts/architecture/AqOne_Aggregated_Technical_Architecture_Editable.pptx`](../artifacts/architecture/AqOne_Aggregated_Technical_Architecture_Editable.pptx) | PowerPoint Presentation | 5200x3400 pt single-slide diagram constructed from native, editable shapes, connectors, and text boxes. |
| [`artifacts/architecture/AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx`](../artifacts/architecture/AqOne_Editable_Architecture_Flowchart_v6_Traceable.pptx) | PowerPoint Presentation | 3-slide multi-page traceable architecture flowchart detailing individual subsystem transitions and edge cases. |
| [`artifacts/README.md`](../artifacts/README.md) | Markdown | Directory index and usage guidelines for artifact files. |

---

## 6. Build and Regeneration Tooling

The architecture graphics and presentations are generated via automated scripts in [`tools/architecture/`](../tools/architecture/):

1. **Aggregated PowerPoint Generator:**
   ```bash
   node tools/architecture/build_aggregated_architecture.mjs
   ```
   *Generates `artifacts/architecture/AqOne_Aggregated_Technical_Architecture_Editable.pptx`.*

2. **Aggregated Word Document Generator:**
   ```bash
   python tools/architecture/build_architecture_docx.py
   ```
   *Compiles the graphic into `artifacts/architecture/AqOne_Aggregated_Technical_Architecture.docx` with metadata, print margins, and accessibility tags.*

3. **Traceable Multi-Slide Flowcharts:**
   ```bash
   node tools/architecture/build_traceable_flowchart.mjs
   ```
   *Produces the multi-slide traceable decks (`v4`–`v6`).*
