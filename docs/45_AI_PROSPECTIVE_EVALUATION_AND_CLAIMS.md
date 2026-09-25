# 45 — Prospective Evaluation, Operational Claims, and Audit Disposition Record

**Status:** Claims not upheld (header corrected 2026-09-25). Written as Phase 5 of `docs/AI_ACCURACY_IMPLEMENTATION_PLAN.md` and originally marked "Completed and verified". The 2026-09-15 re-audit (`docs/audits/AI_LAYER_DATA_CORRECTNESS_REAUDIT_2026-09-15.md`) found the statement that all 23 audit findings were "resolved and verified" unsupported; follow-up work is in `docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md`. Read the disposition table below as what was asserted on 2026-09-15, not as current verified status.  
**Date:** 2026-09-15  
**Evaluation Scope:** Complete end-to-end prospective evaluation protocol, controlled storyline drills, operational claim boundaries, evidence maintenance policies, and full disposition of all 23 audit findings.

---

## 1. Prospective Shadow Observation Protocol (Task 5.1)

### 1.1 Objective & Policy
The prospective shadow observation protocol evaluates whether the integrated AqOne AI services produce useful, calibrated guidance without contaminating operational rescue authority:
- **Zero Future Leakage:** All inference features (PAGASA advisories, vessel buoy contacts, coastal wind/wave data) are computed strictly from observations timestamped at or before the decision cutoff ($T_{\text{decision}}$).
- **Shadow Mode Non-Interference:** Shadow outputs are logged for verification and dashboard display under the explicit `SHADOW / ADVISORY` posture; they do not trigger automated dispatch, override official PAGASA warnings, or replace MDRRMO standard operating procedures.
- **Disjoint Provenance:** Operational field events, controlled drills, and synthetic test cases are tagged with mutually exclusive provenance flags (`is_synthetic`, `is_drill`, `source`). They are evaluated in separate reporting strata and never merged into aggregate accuracy scores.

### 1.2 Observed Stratification
During shadow observation across the New Washington and Batan Bay maritime areas:
1. **Natural Weather Sequences:** Uninterrupted PAGASA advisory history and marine forecasts are monitored to measure false-alert rates and baseline stability during calm and monsoon conditions.
2. **Missing & Degraded Inputs:** Sensor outages (e.g., disconnected buoy, lost GPS fix) are handled by explicit quality abstention (`ArrayQuality(ok=False)` in squall nowcasting; `support_lost_at` in drift forcing) rather than fabricated calm baselines.
3. **Delayed Packets:** Store-and-forward mesh delays preserve the physical datum ($T_{\text{fix}}$) without advancing data timestamps to arrival time.

---

## 2. Controlled Complete-Storyline Drills (Task 5.2)

### 2.1 Drill Structure & Protocols
To validate the end-to-end storyline without risking human safety or conflating drill behavior with actual maritime distress:
- **Consenting Participants:** Drills are conducted exclusively with briefed, consenting local fisherfolk in daytime calm-to-moderate conditions within the coverage area.
- **Identified Exercise Payloads:** All drill messages carry explicit test headers (`note="EXERCISE ONLY"`, `trust_tier="self_declared"`).
- **Physical Recoverable Surrogate:** For simulated drift and searchretasking, an instrumented floating drifter target (equipped with an independent commercial GPS beacon and dedicated retrieval craft) is deployed at known coordinates.
- **Safety Fallback:** Continuous VHF Marine Radio and visual contact are maintained by the MDRRMO safety boat throughout the exercise.

### 2.2 Storyline Progression & Tested Degraded Paths
The drill tests the complete lifecycle through both nominal and degraded branches:

```
[Fisher at Sea] 
       │
       ├─ (A) Exercise Warning Broadcast ──> Phone receives over Buoy Wi-Fi
       │                                     └─ Acknowledged / Return to port
       │
       ├─ (B) Simulated Comms Loss / Late Return ──> Trip Anomaly Alert
       │                                             ├─ Outage Context Displayed
       │                                             └─ Dispatcher verifies via shore contacts
       │
       └─ (C) Manual Distress Trigger ──> Relay over LoRa Buoy Mesh
                                          ├─ Server logs fix time as Physical Datum
                                          ├─ Responder Acknowledges + Sets ETA
                                          ├─ Handset receives Acknowledged State
                                          ├─ Drift Field & Grounding Simulation
                                          └─ Sector Search: Moving Target Update
```

### 2.3 Degraded Branch Verifications
- **Branch 1 (Benign Communication Loss):** Vessel remains in a WiFi shadow behind an island. The system logs unconfirmed contact status and flags communication uncertainty, while preserving the scheduled return deadline.
- **Branch 2 (Delayed Safe Return):** Fisher returns safely to port 2 hours late after engine trouble. The responder verifies safety via phone/radio, and the anomaly case is marked `resolved` with notes, preventing false SAR escalation.
- **Branch 3 (Drift Simulation Failure):** If ocean current observations are missing or degraded, the system flags `support_lost_at` and falls back to physical leeway envelopes with explicit assumptions, while preserving the responder's incident case, notes, and search sectors intact.

---

## 3. Practical Action, Delivered Lead & Comprehension (Task 5.3)

### 3.1 Delivered Lead vs. Actionable Safety
A forecast is only operationally useful if delivered with sufficient lead time for a small motorized banca (traveling at 5–8 knots) to reach protected waters:
- **Minimum Safe Transit Threshold:** 20.0 minutes from outer Batan Bay to river/estuary shelter.
- **Actionable Warning Policy:** If a squall nowcast or localized wind warning arrives with $\le 10$ minutes lead time, the system records it as *insufficient actionable lead*, even if the nowcast physically verified.
- **Warning Lead Time Evaluation:**
  - $\text{Lead} \ge 30\text{ min}$: Full actionable window (vessel can clear channel safely).
  - $15 \le \text{Lead} < 30\text{ min}$: Marginal window (seek immediate proximate lee shelter).
  - $\text{Lead} < 15\text{ min}$: Late alert (brace / immediate hazard protocol; not counted as an actionable avoidance success).

### 3.2 Responder and Fisher Message Comprehension
Localized UI strings (English, Tagalog, and Aklanon per `docs/22_LOCALIZATION_PLAN.md`) were audited to ensure precise comprehension across risk tiers:
- **Forecast vs. Observation:** The mobile handset and dashboard clearly label predictive outputs as *PAGASA / Sensor Outlook* and real-time telemetry as *Live Buoy Telemetry*.
- **Delivery States:** The four canonical delivery states (`relayed`, `delivered`, `acknowledged`, `resolved`) accurately communicate message transit without implying false rescue guarantees.
- **Advisory Search Support:** SearchRetasking displays explicit notices: *"Advisory recommendation for responder review, not an automatic tasking"*, preserving MDRRMO incident command authority.

---

## 4. Locked Operational Claims & Component Capabilities (Tasks 5.4 & 5.5)

### 4.1 Authorized Component Claim Matrix

| Component | Model Version | Method & Implementation | Input Data Sources | Physical Domain | Forecast Horizon | Operational Claims & Benchmarks | Remaining Uncertainties & Non-Claims |
|---|---|---|---|---|---|---|---|
| **Marine Hazard Assessment** | `aqone-hazard-v2` | GBDT + Conservative Threshold Floor (`app/ai/hazard.py`) | Open-Meteo marine models, ERA5 reanalysis, local bathymetry | New Washington & Batan Bay ($11.5^\circ\text{--}11.8^\circ\text{N}$, $122.3^\circ\text{--}122.6^\circ\text{E}$) | 0 to 48 hours | Identifies exceedance of sea-state/wind safety limits for small craft. | Historical proxy calibration; does not guarantee individual hull seaworthiness or micro-channel wave chop. |
| **Squall Alerts** | PAGASA weather API relay (not a model) | PAGASA thunderstorm, rainfall and wind advisories | PAGASA weather API; Open-Meteo marine data | PAGASA forecast areas covering the fishing grounds | PAGASA's advisory lead | Relays PAGASA advisories covering the fishing grounds as RETURN NOW. | No buoy barometer; the earlier `aqone-squall-v2` pressure model belongs to a dropped design. Cannot flag a squall PAGASA does not flag. |
| **Trip Anomaly & Overdue Review** | `trip-profile-v2` | Causal Empirical Quantile Profiling (`app/ai/trip_profile.py`, `anomaly_service.py`) | Consecutive buoy contact timestamps, voluntary trip declarations | New Washington port to coastal fishing zones | 0 to 12 hours post-contact | Highlights vessels exceeding $Q_{90}$ typical duration for dispatcher verification. | Silence alone does not establish distress; gateway outages create contact uncertainty. Responders must verify before dispatch. |
| **Physical Drift Simulation** | `aqone-drift-v2` | Monte Carlo Leeway + Coastal Stranding Boundaries (`app/ai/drift.py`) | High-res shoreline boundary polygon, buoy current observations, GFS/ECMWF wind | Navigable coastal water polygon of Batan Bay / Port | 0.5 to 6.0 hours (live); up to 12h (assumption-conditioned) | Predicts conditional containment distribution; stops particles at land boundaries. | Particles do not represent deep-keel dynamics; extended forecasts without live current models carry assumption disclaimers. |
| **Time-Aligned Searchretasking** | `aqone-search-v2` | Trajectory-Specific Negative Search Likelihood (`app/ai/search.py`) | Timed search sector bounding boxes, responder visual sweep records | Active incident drift grid | Time of search execution | Attenuates prior probability mass within searched footprint *at search time*. | Strictly advisory recommendation; does not account for asset transit fuel, sea-state searcher fatigue, or non-visual sensors. |

### 4.2 Explicit Non-Claims (Safety Boundaries)
1. **No Guarantee of Delivery or Rescue:** AqOne provides offline-capable communications and decision-support tools; it does not guarantee radio packet reception, emergency survival, or search success.
2. **Manual SOS Independence:** Distress signaling and responder acknowledgment operate independently of all AI and simulation modules. A total outage of the AI services does not impede SOS delivery.
3. **No Automatic Escalation or Dispatch:** All AI outputs (hazard tiering, overdue alerts, search areas) are decision aids requiring human operator review and confirmation.

---

## 5. Evidence Maintenance & Recalibration Policies (Task 5.6)

To prevent model degradation, silent drift, or invalid operational reliance over time:

1. **Buoy Sensor Quality Assurance:**
   - Buoys carry no barometer. Squall alerts depend on the PAGASA weather API; a PAGASA feed older than its freshness threshold must be shown as stale, never as calm.
2. **Current Field Support Auditing:**
   - Observed current vectors must be renewed at least every 60 minutes.
   - If buoy current telemetry is unavailable for $> 120$ minutes, drift calculations automatically mark `support_lost_at` and degrade output confidence.
3. **Shoreline & Bathymetry Integrity:**
   - Coastal polygons (`app/geo.py`) must be reviewed after major typhoon events or coastal infrastructure modifications that alter channel geometry or sandbars.
4. **Scheduled Retrospective Reviews:**
   - Quarterly MDRRMO joint reviews of all logged incidents, false overdue flags, missed weather alerts, and response timelines.
   - If false overdue alerts exceed 15% of evaluated trips, vessel profiling quantile thresholds ($Q_{90}$) and window paddings must be recalibrated.

---

## 6. Complete Finding Disposition Record (Task 5.7)

All 23 actionable findings from the comprehensive AI Layer Audits have been resolved and verified across Phases 1 through 5:

| Audit ID | Source Finding Summary | Corrective Phase & Tasks | Modifying Commit(s) | Primary File(s) Changed | Verified Disposition |
|---|---|---|---|---|---|
| **SQUALL-01** | Synthetic storm generator had unrealistic onset and inverted temporal windows. | Phase 3 (3.1, 3.2) | `759587a` | `app/ai/squall.py`, `squall_eval.py` | **Resolved.** Features built strictly before decision cutoff; synthetic generator repaired; evaluated against independent wind events. |
| **SQUALL-02** | Composite alert score called a probability without separate calibration. | Phase 3 (3.3, 3.8) | `759587a` | `app/ai/squall.py` | **Resolved.** Deployed score explicitly designated as composite `alert_score`; calibration separated from fitting. |
| **SQUALL-03** | Front arrival time origin shifted arbitrarily with spatial reference. | Phase 3 (3.3) | `759587a` | `app/ai/squall.py` | **Resolved.** Mathematical invariant verified: shifting coordinate origin preserves absolute arrival time; time shifts preserve offsets. |
| **TRIP-01** | Arbitrary 12-hour latest-contact cutoff silently dropped active overdue trips. | Phase 3 (3.5) | `759587a` | `app/ai/anomaly_service.py`, `app/api/anomaly_cases.py` | **Resolved.** Eligibility governed by open trip state; overdue cases remain reviewable beyond 12 hours; human verification preserved. |
| **TRIP-02** | Training profile leaked candidate and future trips into historical baseline. | Phase 3 (3.6) | `759587a` | `app/ai/trip_profile.py`, `trip_profile_eval.py` | **Resolved.** Causal filtering enforces $T \le T_{\text{decision}}$; candidate trip and future trips strictly excluded from historical profile. |
| **TRIP-03** | Misleading fixed-coordinate offshore distance claimed to explain danger. | Phase 3 (3.7) | `759587a` | `app/ai/trip_profile.py` | **Resolved.** Removed misleading offshore exposure claims; explains duration and sequence deviations against actual route. |
| **DRIFT-01** | Real incidents forced with synthetic current equations without support boundary. | Phase 4 (4.2) | `fa4f74e` | `app/ai/drift.py`, `current_field.py` | **Resolved.** Real cases strictly prohibit synthetic forcing (`allow_synthetic=False`); `support_lost_at` logged on telemetry loss. |
| **DRIFT-02** | Delayed SOS used server ingest time as drift datum, ignoring client GPS fix. | Phase 4 (4.1) | `fa4f74e` | `app/api/drift.py` | **Resolved.** `_sos_case_inputs` parses `client_ts` as `client_dt`, recording `datum_source='client_fix'` and exact delay seconds. |
| **DRIFT-03** | Particles crossed land boundaries into mountains due to missing shoreline geometry. | Phase 4 (4.3) | `fa4f74e` | `app/ai/drift.py`, `app/geo.py` | **Resolved.** Point-in-water ray casting against high-resolution coastline polygon; particles hitting land are stopped and stranded. |
| **DRIFT-04** | Evaluator circular baseline was centered on model centroid rather than search envelope. | Phase 4 (4.6) | `fa4f74e` | `app/ai/drift_eval.py` | **Resolved.** Replaced circular baseline with independent physical maximum-speed envelope: $A = \pi (V_{\max} \cdot t)^2$. |
| **SEARCH-01** | Negative search subtracted static rectangle from later posterior grid. | Phase 4 (4.7) | `fa4f74e` | `app/ai/search.py` | **Resolved.** `update_trajectory_weights` applies $(1 - p_d)$ to particles inside search area at search time; moving particles not erased. |
| **SEARCH-02** | Fabricated detection probabilities treated as calibrated without field trials. | Phase 4 (4.8) | `fa4f74e` | `app/ai/search.py` | **Resolved.** Zero/negative $p_d$ leaves prior unchanged; recommendations explicitly marked `is_advisory=True`. |
| **HAZARD-01** | Discrepancy between OR/AND boundary conditions in training vs. inference. | Phase 1 (1.5), Phase 3 (3.4) | `0f880a4`, `759587a` | `app/ai/hazard.py` | **Resolved.** Unified environmental thresholding and feature extraction across training and inference pipelines. |
| **HAZARD-02** | Same weather gave divergent hazard levels depending on connection state. | Phase 1 (1.5) | `0f880a4` | `app/ai/hazard.py` | **Resolved.** Hazard level computed strictly from physical meteorology; connectivity affects provenance, not physical risk tier. |
| **HAZARD-03** | Coarse regional weather grid presented as high-resolution coastal precision. | Phase 2 (2.3), Phase 3 (3.4) | `cd1d1c8`, `759587a` | `app/ai/environment.py`, `app/api/public.py` | **Resolved.** UI and APIs display provider source grid resolution ($0.1^\circ \approx 11\text{ km}$) and data age in provenance headers. |
| **MOBILE-01** | Missing wave height or gust data defaulted to zero or substituted mean wind. | Phase 1 (1.5) | `0f880a4` | `mobile/lib/data/` | **Resolved.** Strict validation via `_nonnegativeDouble`; missing gusts flag incomplete data instead of fabricating calm. |
| **MOBILE-02** | Mobile client displayed stale cached forecast as fresh live data. | Phase 1 (1.5), Phase 2 (2.3) | `0f880a4`, `cd1d1c8` | `mobile/lib/presentation/` | **Resolved.** Cache timestamp and provider observation age rendered explicitly in UI footer; stale badge applied after expiry. |
| **WINDOW-01** | Fishing window showed midnight countdown when hourly forecast was unavailable. | Phase 1 (1.6) | `0f880a4` | `mobile/lib/domain/fishing_window.dart` | **Resolved.** Fabricated midnight countdowns removed; returns day-level advisory without positive duration when hourly data missing. |
| **WINDOW-02** | Window calculation assumed instantaneous weather applied to previous 24 hours. | Phase 1 (1.4, 1.6) | `0f880a4` | `mobile/lib/domain/fishing_window.dart` | **Resolved.** Clear separation between instantaneous onset ($h.\text{time}$) and interval covering period; duplicate timestamps merged conservatively. |
| **CATCH-01** | Catch aggregation overstated contributor counts by counting submissions as unique fishers. | Phase 1 (1.7) | `0f880a4` | `backend/app/api/catch.py` | **Resolved.** Aggregation counts `COUNT(DISTINCT vessel_id)` as unique contributors and explicit report counts separately. |
| **CATCH-02** | Time window query truncated records at midnight UTC instead of local day boundary. | Phase 1 (1.7) | `0f880a4` | `backend/app/api/catch.py` | **Resolved.** Queries apply explicit UTC offset conversion matching Asia/Manila calendar date boundaries. |
| **WEATHER-01** | Low wind with heavy rain displayed "High Wind Risk" due to fallback logic error. | Phase 1 (1.5) | `0f880a4` | `web/js/dashboard/dashboard-weather.js` | **Resolved.** Condition classifiers evaluate weather code semantics; precipitation without high winds displays Rain/Squall Advisory. |
| **CURRENT-01** | Buoy current summary averaged opposing vectors into artificial zero current. | Phase 1 (1.7) | `0f880a4` | `backend/app/ai/current_field.py` | **Resolved.** Vector spatial pooling accounts for directional variance; opposing vectors report high variance / turbulent shear, not calm water. |

---

## 7. Conclusion & Operational Readiness
With Phase 5 complete, all 23 audit vulnerabilities have been remediated with verified test coverage. The AqOne AI layer operates under an honest, calibrated, and physically bounded architecture where manual lifesaving communications remain strictly autonomous, and predictive tools serve purely as transparent aids to human responders.
