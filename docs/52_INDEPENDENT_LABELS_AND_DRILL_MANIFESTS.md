# Independent Labels and Controlled Drill Manifest Protocol

> **Document ID:** `docs/52_INDEPENDENT_LABELS_AND_DRILL_MANIFESTS.md`  
> **Status:** Approved / Operational  
> **Related Documents:** `docs/00_START_HERE.md`, `docs/08_DEMO_AND_STATUS.md`, `docs/50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md`, `docs/51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md`

---

## 1. Principles of Independent Evaluation

Predictive accuracy and decision-support reliability in AqOne cannot be validated using model outputs, synthetic simulations, or developer impressions as ground truth. In accordance with the Phase 2 requirements of `docs/AI_ACCURACY_IMPLEMENTATION_PLAN.md`:

1. **Independent Truth Custody:** Ground truth (actual wind onset, boat arrival/welfare, physical drifter trajectories) must be recorded and audited independently of the predictive models and warning triggers.
2. **Separation of Normal Trips, Drills, and Disasters:**
   - Normal fishing trips supply baseline contact cadences, ordinary durations, and non-events.
   - Controlled drills simulate communication delays, deadline exceedances, and search scenarios under safe, approved protocol. They **never deliberately endanger fishermen** or recreate severe maritime storms.
   - Recoverable surrogate objects (weighted drift buoys, radar reflectors) represent unpowered drift targets; human beings are never set intentionally adrift as test truth.
3. **Pre-Registered Dataset Splits & Manifests:** Manifest files freeze data partition assignments (development, calibration, and untouched evaluation) **before** feature extraction or model evaluation. Overlapping track segments or time windows from the same physical event must never leak across splits.

---

## 2. Label Adjudication Taxonomy

| Domain | Observed Target | Operational Definition | Independent Truth Source | Ground Truth Adjudicator |
|---|---|---|---|---|
| **Weather / Squall** | Severe Convective Front | Sustained wind $> 25\text{ knots}$ or peak gust $> 34\text{ knots}$ | Reference Ultrasonic Anemometer + PAGASA Kalibo station observations | Independent meteorologist / MDRRMO safety officer |
| **Vessel Trip** | Trip Completion | Vessel safely docked/beached and crew confirmed safe | Time-stamped shore observation, VHF call, or direct handset check-in | Landing site monitor / Port safety inspector |
| **Vessel Trip** | Overdue / Unresolved | Expected return elapsed by $> 60\text{ min}$ with zero communication | Time-stamped responder review log, verification phone call to family | Designated MDRRMO duty dispatcher |
| **Drift** | Object Trajectory | Geodetic position $(u, v, t)$ of drifting target | High-rate GNSS raw logging (1 Hz logged locally on drifter unit) | Research hydrographer / Truth custodian |
| **Search** | Visual / Radar Detection | Time, range, bearing, and sea state at moment of target sighting | Time-stamped logger on search craft + blinded observer logbook | Independent SAR exercise umpire |

---

## 3. Controlled Drill Protocol & Safety Safeguards

### 3.1 Controlled Drift Drill Procedure

1. **Surrogate Target:** A 1:1 scale simulated unpowered banca hull ballasted to 0.4 m draft and equipped with a standalone, waterproofed multi-constellation GNSS logger (1 Hz logging to internal flash).
2. **Safety Vessel Escort:** An escorted standby motor vessel remains 500 – 1,000 metres downwind of the surrogate target with active AIS and radar tracking.
3. **Execution Window:** Daylight hours only, calm to moderate sea state (Beaufort 2–4), falling or rising tide phase documented via NAMRIA tide station.
4. **Data Handling:** Raw GNSS binary logs are downloaded post-recovery via USB and archived with SHA-256 checksums in the truth vault prior to model comparison.

### 3.2 Delayed Contact & Welfare Drill Procedure

1. **Consenting Participant:** Partner vessel operating with an onboard reference GNSS logger and handset running a designated drill profile.
2. **Pre-Agreed Silence Window:** Vessel deliberately inhibits WiFi transmission for a pre-scheduled duration (e.g., 90 minutes) during daytime coastal operations.
3. **Safety Backchannel:** Vessel maintains active VHF marine radio contact on Channel 16/68 with MDRRMO shore station every 30 minutes to guarantee actual crew safety while the software pipeline evaluates anomaly detection.
4. **Outcome Adjudication:** Event is labeled `drill_delayed_contact` with verified status `safe`.

---

## 4. Manifest File Format & Schema Specification

Every curated dataset partition is cataloged in a version-controlled JSON manifest file:
`manifests/dataset_manifest_v1.json`

### 4.1 Schema Definition

```json
{
  "manifest_version": "1.0.0",
  "created_at": "2026-09-15T00:00:00Z",
  "custodian": "MDRRMO New Washington Research Team",
  "domain": "New Washington, Aklan (11.55N-11.75N, 122.35E-122.55E)",
  "records": [
    {
      "record_id": "TRIP-2026-09-NW-001",
      "event_id": "EVENT-TRIP-001",
      "record_type": "normal_trip",
      "split": "development",
      "vessel_id": "BANCA-04",
      "started_at": "2026-09-15T04:15:00Z",
      "ended_at": "2026-09-15T10:30:00Z",
      "outcome": "completed_safe",
      "unusable_intervals": [],
      "raw_evidence_sha256": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b"
    },
    {
      "record_id": "DRIFT-2026-09-DR-001",
      "event_id": "EVENT-DRIFT-001",
      "record_type": "controlled_drill_drift",
      "split": "held_out_test",
      "vessel_id": "SURROGATE-BANCA-01",
      "started_at": "2026-09-15T08:00:00Z",
      "ended_at": "2026-09-15T14:00:00Z",
      "outcome": "recovered_intact",
      "unusable_intervals": [
        {"from": "2026-09-15T08:00:00Z", "to": "2026-09-15T08:15:00Z", "reason": "deployment_settling"}
      ],
      "raw_evidence_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    },
    {
      "record_id": "DRIFT-2026-09-DR-002",
      "event_id": "EVENT-DRIFT-002",
      "record_type": "controlled_drill_drift",
      "split": "held_out_test",
      "vessel_id": "SURROGATE-BANCA-02",
      "started_at": "2026-09-16T08:00:00Z",
      "ended_at": "2026-09-16T14:00:00Z",
      "outcome": "beached_sandbar",
      "unusable_intervals": [],
      "raw_evidence_sha256": "7f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b947"
    }
  ]
}
```
*Note: `validate_manifest` (`app/ai/manifest.py`) rejects empty files, all-zero hashes, and the empty-string SHA-256 (`e3b0c4...`), requires explicit disjoint `event_id` partitions across splits, and verifies multi-class outcome diversity in evaluation splits.*

---

## 5. Replay Fixture Verification Gate

Before scaling any machine learning retraining or statistical evaluation:
1. A small end-to-end replay fixture (containing 3 normal trips, 1 delayed contact drill, and 1 controlled drifter track) must execute through the ingestion pipeline (`/api/v1/contacts`, `/api/v1/trips`, `/api/v1/current-events`).
2. Verification tests must confirm that delayed receipt timestamps do not rewrite historical occurrence timestamps.
3. Model evaluation scripts must load only facts strictly preceding the decision cutoff time.
