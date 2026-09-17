# 54 — Field Readiness, Measurement Protocols, and Collection Handoff

> **Document ID:** `docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md`  
> **Phase:** Phase 5 Preparation & Readiness Protocol (`docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md`)  
> **Status:** Software & Evaluation Gate Passed; Physical Field Deployment & In-Water Collection Pending Handoff  
> **Date:** 2026-09-16  
> **Related Documents:** `docs/00_START_HERE.md`, `docs/08_DEMO_AND_STATUS.md`, `docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`, `docs/49_AI_ACCURACY_DATA_PROTOCOL.md`, `docs/50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md`, `docs/51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md`, `docs/52_INDEPENDENT_LABELS_AND_DRILL_MANIFESTS.md`, `manifests/field_eval_manifest_v1.json`

---

## 1. Instrument & Operational Inventory (Task 5.1)

In accordance with Phase 5 Task 5.1, this inventory explicitly distinguishes verified software/lab assets from physical oceanographic assets that remain proposed or pending in-water commissioning:

### 1.1 Currently Available & Software-Verified Assets
1. **Core Processing & Backend Platform:**
   - FastAPI + PostgreSQL/PostGIS database schema and migrations (`backend/`).
   - Software ingestion endpoints: `/api/sos`, `/api/contacts`, `/api/trips`, `/api/current-events`, `/api/advisories`.
   - Verified event-level manifest validation engine (`backend/app/ai/manifest.py`).
   - Causal, uncorrupted trip profiling and anomaly scoring service (`backend/app/ai/anomaly_service.py`, `trip_profile.py`).
   - Physical particle drift simulation with high-resolution coastline collision/stranding polygon (`backend/app/ai/drift.py`, `app/geo.py`).
   - Time-aligned trajectory likelihood attenuation (`backend/app/ai/search.py`).
   - Synthetic & controlled track drift evaluator with supported horizon checks (`backend/app/ai/drift_eval.py`).
   - Gated squall nowcasting pipeline capping unvalidated/synthetic calibration bundles to `watch` (`backend/app/ai/squall.py`, `app/api/squall.py`).
2. **Handset & Client Platform:**
   - Flutter mobile client (`mobile/`) with offline WiFi advisory caching, trip declaration, and manual SOS trigger.
   - Operations web dashboard (`web/`) with live SSE feed, audit log, and incident management.
3. **Firmware & Lab Radio Nodes:**
   - Reference ESP32-S3 + SX1262 LoAM binary frame codec with authenticated HMAC-SHA256 frame integrity and deduplication (`firmware/buoy/`).

### 1.2 Physical In-Water Assets (Proposed / Pending Deployment)
The following physical instruments and field arrangements described in research protocols (`docs/50`) represent target field specifications and are **pending physical deployment**:
1. **Anchored Offshore Buoys:** Physical marine buoy hulls with moorings, solar charging, and SX1262 LoRa/WiFi nodes deployed at outer New Washington waters (awaiting open-water deployment).
2. **Moored Reference ADCP:** Bottom-mounted 600 kHz acoustic Doppler current profiler in the Batan Channel throat (awaiting municipal marine survey equipment).
3. **Directional Wave Reference Buoy:** Spectral wave buoy at New Washington Outer Shoal (pending oceanographic deployment).
4. **Shore Tower Ultrasonic Anemometer:** 10 m mast-mounted 2-axis ultrasonic sensor at MDRRMO station (pending shore station erection).
5. **Consented Vessel Fleet:** Real artisanal bancas operating with signed data consent agreements for GPS truth collection.

---

## 2. Operating Domain, Vessel Classes & Event Definitions (Task 5.2)

### 2.1 Geographic Domain Boundaries
- **Bounding Box:** $11.60^\circ\text{N}$ to $11.75^\circ\text{N}$, $122.40^\circ\text{E}$ to $122.55^\circ\text{E}$ (New Washington and Batan Bay, Aklan Province).
- **Hydrodynamic Strata:**
  - *Inner Estuary:* Tidal current dominant ($\le 2.5\text{ m/s}$ reversing flow), sheltered from deep swell.
  - *Lagatik Corridor:* Channel transit zone subject to tidal currents and shallow bathymetry.
  - *Outer Bay Waters:* Exposed coastal sea subject to Habagat/Amihan open swell, wind-chop, and convective squalls.

### 2.2 Target Craft Classes
- **Class A (Non-motorized Banca):** Paddled outrigger, length $< 5\text{ m}$, freeboard $< 0.35\text{ m}$, cruise speed $1.5\text{--}3.0\text{ knots}$.
- **Class B (Motorized Pumpboat):** Single-cylinder engine outrigger, length $6\text{--}10\text{ m}$, $< 3\text{ GT}$, cruise speed $5\text{--}8\text{ knots}$.
- **Safety Criticality:** High sensitivity to short-period steep wave chop ($> 1.0\text{ m}$) and sudden squall wind escalations ($> 22\text{ knots}$).

### 2.3 Independent Event Taxonomy
1. **Natural Squall Wind Event:** Sustained wind $> 25\text{ knots}$ or peak gust $> 34\text{ knots}$ verified by PAGASA Kalibo or shore anemometer, accompanied by barometric rate drop.
2. **Normal Trip Baseline:** Consented vessel trip departing from designated landing port, returning within declared deadline, with crew safety independently confirmed by dock inspector.
3. **Overdue / Missed-Deadline Event:** Registered trip exceeding declared expected return time by $> 60\text{ minutes}$ with zero buoy contact, initiating dispatcher shore verification.
4. **Controlled Drift Target:** 1:1 scale unpowered banca hull surrogate ballasted to $0.4\text{ m}$ draft with onboard 1 Hz GNSS logging, monitored by dedicated safety craft.

---

## 3. Pre-Registered Acceptance Protocols (F1–F8)

Before unblinded inspection of field evaluation data, the following decision criteria, baselines, and denominators are frozen:

| Protocol | Procedure / Scope | Baseline Comparison | Decision Rule & Acceptance Threshold |
|---|---|---|---|
| **F1** | Collocated sensor commissioning (barometer, wind, current, GNSS). | PAGASA Kalibo station / calibrated lab standard. | Barometer zero-offset $\le \pm 0.3\text{ hPa}$; clock synchronization error $\le \pm 5.0\text{ s}$ across mesh; raw IMU motion never labeled as calibrated wave height. |
| **F2** | Handset WiFi opportunity and blind interval logging on transiting bancas. | Direct continuous cellular connection (theoretical ceiling). | Empirical contact window $\ge 60\text{ s}$ per encounter; raw issue, arrival, and display timestamps logged; expired warnings rejected. |
| **F3** | Prospective weather onset recording and matched non-event periods. | Transparent single-sensor pressure drop baseline ($\Delta P \ge 0.5\text{ hPa} / 30\text{ min}$). | Composed decision must achieve higher precision at matched recall than simple threshold baseline; false alarms reported per exposure hour. |
| **F4** | Rehearsed delayed return and normal trip monitoring under consented safety protocol. | Fixed 12-hour expiration rule (legacy baseline). | Zero dropped open trips; overdue trips scored as overdue with low confidence under outage; no false escalation of confirmed safe returns. |
| **F5** | Supervised recoverable drifter track with independent GNSS logger. | Independent circular expansion envelope ($A = \pi (V_{\max} \cdot t)^2$). | Live drift contour must achieve $\ge 80\%$ containment within supported horizon with area reduction factor $\ge 2.0$ vs unconstrained envelope. |
| **F6** | Blinded search trials on recoverable targets with documented sweep footprints. | Prior-only geographic cell ranking. | Time-aligned likelihood update attenuates prior mass within searched area at search time; zero or negative $p_d$ leaves prior unchanged. |
| **F7** | Complete integrated before/during/after storyline drill. | Manual standalone SOS intake (absolute baseline). | Manual SOS ingest (`POST /api/sos`) and responder acknowledgment survive model crashes or simulation failures with 100% availability. |
| **F8** | Frozen candidate model evaluation on untouched held-out events. | Prespecified physical baselines above. | Evaluated strictly against disjoint event partitions from manifest; all failures, abstentions, and missing samples included in denominators. |

---

## 4. Delivered Lead Accounting Standard (Task 5.8)

Delivered lead time is strictly computed as:
$$\text{Delivered Lead} = T_{\text{hazard\_onset}} - T_{\text{handset\_display}}$$

- **Actionable Avoidance Lead:** $\ge 20.0\text{ minutes}$ (required for motorized banca to transit from outer bay to lee shelter).
- **Marginal Lead:** $10.0\text{--}19.9\text{ minutes}$ (immediate proximate shelter protocol).
- **Late / Ineffective Lead:** $< 10.0\text{ minutes}$ (recorded as failure of actionable warning).
- **Accounting Rule:** An alert generated by the model but never displayed on the handset (due to WiFi shadow or delayed encounter) is accounted as **undelivered / missed lead**, not as an excluded successful nowcast.

---

## 5. Canonical Dataset Manifest Fixture

The repository maintains an illustrative, verified field evaluation manifest at:
[`manifests/field_eval_manifest_v1.json`](file:///C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/manifests/field_eval_manifest_v1.json)

- **Verification:** Validated by `validate_manifest` (`backend/app/ai/manifest.py`) and tested under `test_canonical_field_eval_manifest_validates_cleanly` in `backend/tests/test_calibration_and_replay.py`.
- **Integrity Constraints Enforced:**
  - Verifiable 64-character SHA-256 hashes of raw evidence files.
  - Complete event-level partition disjointness (no storm, drifter track, or trip spans both development and held-out test splits).
  - Target diversity in test splits ($> 1$ distinct outcome class).

---

## 6. Current Evidence Ledger & Honest Claim Boundaries (Task 5.9)

| Capability | Current Verified Evidence | Physical Field Status | Authorized Operational Claim Boundary |
|---|---|---|---|
| **Manual Distress Signaling (SOS)** | Automated API & relay tests pass (`test_sos_ingest.py`, `test_responder_loop.py`, `test_c7`). | Hardware prototype bench-verified; outdoor LoRa range tests pending. | **Operational Core:** SOS intake and acknowledgment operate independently of all AI services. |
| **Squall Nowcasting** | Mathematical invariants verified; synthetic bundle promotion capped at `watch` (`test_c1`, `test_c2`). | Array pressure sensors pending in-water buoy deployment. | **Advisory / Watch Only:** Cannot trigger automated evacuation (`return_now`); displays uncalibrated research notice. |
| **Trip Anomaly Scoring** | Causal profiling verified; overdue trips with zero contacts remain reviewable (`test_c5`, `test_c6`). | Consented vessel tracking pending municipal pilot registration. | **Decision Aid:** Highlights overdue obligations for human dispatcher telephone/radio verification. |
| **Physical Drift Modeling** | Coastline stranding, supported horizons, and negative search likelihood verified (`test_c8`, `test_search.py`). | In-water surrogate drifter trials pending field deployment. | **Conditional Simulation:** Advisory search sectors for responder review; flagged as unforced leeway envelope if live telemetry lost. |

---

## 7. Concrete Blockers & Field Collection Handoff

In accordance with Phase 5 requirements, Phase 5 remains **Preparation & Protocol Complete; Physical In-Water Collection Pending Handoff** due to the following real-world prerequisites:
1. **Marine Deployment Permitting:** Coastal municipal clearance from LGU New Washington and Philippine Coast Guard (PCG) for anchoring autonomous sensor buoys in shipping/fishing lanes.
2. **Physical Moorings:** Construction and deployment of compliant marine anchorages capable of surviving monsoon wave energy.
3. **Surrogate Target Construction:** Fabrication and ballasting of the 1:1 scale test banca surrogate with sealed GNSS logger.
4. **Safety Escort Vessel Scheduling:** Coordination with MDRRMO New Washington for safety escort boats during active drifter and communication drills.

**Handoff to Field Team:**
- **Hardware / Firmware Owner (Daniel):** Build and bench-qualify the moored buoys according to the LoAM codec specification (`docs/02`) and sensor commissioning protocol (`docs/50`).
- **Gateway / Full Stack Owner (Arnold):** Establish shore gateway tower connectivity, HTTPS backhaul, and NTP synchronization.
- **Lead Dev / Backend Owner (Lenard):** Ingest raw field logs into pre-registered manifest records (`manifests/`) and execute frozen evaluation scripts.
