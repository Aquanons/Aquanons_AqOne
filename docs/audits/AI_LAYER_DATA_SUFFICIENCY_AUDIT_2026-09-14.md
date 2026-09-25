# AqOne AI Layer Data Sufficiency Audit

> **Note (2026-09-25): barometer dropped.** The buoy barometer is no longer part of the
> architecture; squall alerts now come from the PAGASA weather API (PRD §5.1).
> References below to barometers, pressure readings or the pressure-based squall model
> describe that retired design and the code it left behind (`backend/app/ai/squall.py`,
> `barometric_readings`, `/api/v1/pressure-events`), which stays until it is removed.

Date: 2026-09-14

Branch: `codex/ai-layer-audit`

Scope: backend AI modules, browser danger-zone model, mobile forecast heuristics, synthetic data generator, API contracts, model artifacts, evaluation outputs, and responsible-AI documents.

## Executive verdict

AqOne does not contain one AI system.

It contains an umbrella decision-support layer made from five different technology types:

1. A supervised logistic-regression classifier for squall candidates.
2. Per-vessel statistical profiling for trip anomalies.
3. A physics-based Monte Carlo drift simulator.
4. Bayesian probability-grid updating for search re-tasking.
5. A supervised gradient-boosted classifier for environmental hazard proxies.

The mobile risk score, fishing-window calculation, and catch-activity heatmap are rules or aggregation, not machine-learning models.

The data is enough for a controlled demo and for proving that each pipeline can execute.
It is not enough to claim operationally validated rescue, distress, casualty, or official safety predictions.

The main limiting factor is not model sophistication.
It is the absence of real AqOne buoy observations, real local incident labels, real recovery outcomes, and a long enough history of real vessel behaviour.

## Data inventory

| Data class | Current source | Provenance | What it can support | What it cannot support yet |
|---|---|---|---|---|
| Buoy pressure | `barometric_readings`, generated at 5-minute intervals | Synthetic in the repository; live gateway ingest exists but no field history is evidenced | Pipeline execution, feature extraction, synthetic squall demonstration | Local meteorological skill, real squall hit rate, safe `RETURN NOW` release |
| Buoy current | `current_observations`, 15-minute intervals | Synthetic generator; real current-sensor hardware is not available in the submitted system | Current-field interpolation and drift demo | Local current-field accuracy, real search containment |
| Vessel contacts | `buoy_contacts` with vessel, trip, buoy, time, and coordinates | Synthetic trip generator; live contact ingest contract exists | Per-vessel profile construction and overdue scoring mechanics | Population-level false-alarm rate, irregular real-world behaviour, coverage bias measurement |
| Synthetic incidents | `incidents.true_track` and synthetic SOS rows | Generated from the same current/wind assumptions used by the evaluator | Regression checks and self-consistency tests | Independent SAR validation or real recovery performance |
| Weather and marine forecast | Open-Meteo live forecast and marine endpoints | External operational feed, not AqOne sensor data | Current environmental context and transparent forecast guidance | Localized incident probability, nearshore truth, guaranteed sea-state accuracy |
| Historical hazard training data | Open-Meteo archive, Open-Meteo Marine/ERA5-Ocean, NOAA IBTrACS, GEBCO | Real public external data from 2023-08-01 through 2025-12-31 | Environmental hazard proxy classification in the trained region | Vessel casualty risk, local rescue risk, causal safety claims |
| Official sea condition | MDRRMO-entered `sea_conditions` | Human-authored operational input | Human authority and warning precedence | Automated verification of the official decision |
| Catch activity | Consented `catch_logs` | User-entered, sparse, recent, privacy-filtered | Coarse relative activity surface with at least three reporters | Catch prediction, fish abundance, enforcement, or causal livelihood conclusions |

## Feature-by-feature analysis

| Feature | What it is about | Data it utilizes | How it processes the data | How it outputs data | Is the data sufficient for the expected output? |
|---|---|---|---|---|---|
| Squall nowcasting | Detect a pressure pattern that may precede a localized squall and estimate lead time | Pressure readings per buoy, buoy coordinates, 90-minute lookback, 5-minute sampling; synthetic squall event labels for training and evaluation | Builds 21 pressure, derivative, anomaly, and spatial-propagation features; estimates onset order, bearing, speed, fit quality, and coverage; runs a `StandardScaler` plus logistic-regression classifier; applies a threshold and a hand-built window score; quality-gates stale, sparse, gappy, out-of-range, or degenerate arrays | `unknown`, `clear`, `watch`, or gated `return_now`; probability, confidence, affected polygon, per-buoy arrival estimates, lead time, features, calibration | **Demo: yes. Operational nowcast: no.** The model is trained on generator-created pressure drops that resemble the features it measures. The stored synthetic evaluation is weak: precision 0.286 and recall 0.133. There are no confirmed local squall labels, and the live alarm is correctly disabled until field validation. |
| Trip anomaly and overdue detection | Detect when a vessel is late or deviates from its own normal contact pattern | Vessel ID, trip ID, buoy sequence, timestamps, contact coordinates, and a weather snapshot | Builds a vessel profile from route frequency, departure hour, inter-contact intervals, trip duration, and maximum distance; uses fleet averages and marks profiles with fewer than three trips as low confidence; scores overdue time, route deviation, distance deviation, and weather severity with fixed weights; persists review cases rather than dispatching automatically | Expected next buoy and time window, score, `normal`/`watch`/`overdue`/`alert`, factor explanations, confidence flag, and responder-review case | **Established-vessel demo: yes. Real distress detection: not yet.** The synthetic fixture has 496 normal trips and 8 synthetic incidents. The measured median detection latency is 55 minutes, but the false-alarm rate is explicitly null because it was retracted after a flawed evaluation path. The default live scoring path also uses a synthetic weather fallback unless a weather provider is explicitly injected, so the weather factor is not currently real evidence. |
| Drift prediction | Estimate where a person, swamped banca, or intact hull may drift after last contact | Last-known latitude, longitude, and timestamp; responder-selected object class; wind forecast; buoy current observations; published-style leeway coefficients; uncertainty parameters | Propagates 2,000 particles in 10-minute steps; combines current, windage, crosswind, fixed current bias, and diffusion; interpolates fresh buoy currents by inverse-distance and time; calculates a density grid and convex-hull contours; production runs require at least two nearby fresh buoys, at least 50% observed-current coverage, and non-degraded wind | Density grid, centroid track, 50%/75%/95% contours, object class, wind source, degradation flag, input coverage, and immutable run metadata | **Synthetic search-map demo: yes. Real SAR probability: no.** The stored result is 100% containment across 8 synthetic incidents with observation fraction 1.0, but the true tracks and evaluation inputs come from the same synthetic assumptions. The production gate intentionally returns `insufficient_environmental_data` when real buoy coverage is absent. The current sensor is the critical missing data source. |
| Bayesian search re-tasking | Update the search posterior after a responder reports that a sector was searched without finding the target | Existing drift density grid, responder-drawn sector bounds, detection-method preset, and an idempotency key | Multiplies searched cells by `1 - detection_probability`, renormalizes the grid, recalculates contours, and identifies the highest remaining-mass cell | Updated posterior, new contours, next-area recommendation for responder review | **Mechanically: yes. Operationally: not yet.** The update needs an initial posterior, a trustworthy last-known position, and a defensible detection probability. The current detection probabilities are approved presets, not measured local search-performance data. It supports human review but must not be described as automatic asset dispatch. |
| Marine hazard or danger zone | Estimate environmental hazard level across monitored sectors | Live Open-Meteo weather and marine values; static GEBCO depth; month; optional degraded-buoy adjustment | Runs a browser-exported 90-tree gradient-boosted classifier; converts model probability to a score; then applies explicit live wind, wave, precipitation, and weather-code thresholds that can raise or cap the displayed level | Per-sector score, `lower risk`/`watch`/`danger`, reasons, model probability, source, timestamp, and model metadata | **Environmental proxy: yes. Vessel-safety prediction: no.** The artifact has 12,456 training rows, 8,760 test rows, and 1,114 positive labels, but labels are thresholds and cyclone proximity, not vessel outcomes. Gusts account for 78.3% of feature importance and depth contributes 0.0. The committed artifact contains three trained model sectors and 40 stored scan sectors, but the current predictor evaluates only those three plus five hard-coded coverage cells, not all 43 documented sectors. That is both a spatial-transfer limitation and a documentation/runtime mismatch. |
| Mobile risk score and fishing window | Give the fisher a transparent fallback when a server risk verdict is unavailable | Forecast wind, gusts, waves, precipitation, weather code, official sea condition, and squall status | Compares values with fixed thresholds, applies warning precedence, handles missing and stale data, and calculates the first deteriorating hourly interval | Device-derived safe, caution, danger, unknown, and window-availability states | **Guidance: yes. Official or calibrated safety verdict: no.** This is a rule engine, not AI. The backend forecast route is explicitly a transparent Open-Meteo proxy and has no server-side fusion model. The output is useful if labeled as forecast guidance and unknown data remains unknown. |
| Consent-based catch activity surface | Show recent relative activity without exposing exact vessel locations | Consented catch-log coordinates, vessel IDs, recent 30-day window, and per-cell observation counts | Bins coordinates into 0.02-degree cells, requires at least three independent reporters, caps repeated contributions per vessel, normalizes a relative score, and omits exact points and vessel IDs | Coarse cells, relative activity score, observation count, minimum reporter policy, and model/version metadata | **Aggregated activity surface: conditionally yes. Fish prediction: no.** The data supports a privacy-preserving recent-activity map only when enough independent consented reports exist. It is not a predictive model and must not be labeled as a guaranteed catch hotspot or abundance forecast. |

## What the current evaluation numbers actually prove

| Component | Current evidence | Correct interpretation |
|---|---|---|
| Squall | Synthetic precision 0.286, recall 0.133, mean lead 50 minutes | The implementation can score a generated dataset, but the generated dataset does not establish meteorological skill. |
| Trip anomaly | 8 synthetic incidents detected, 55-minute median latency, false-alarm rate retracted to null | The pipeline can detect the generator's abnormal trips; the most important operational error metric is still unmeasured. |
| Drift | 8 synthetic incidents, 100% containment, 1.40x area reduction, 100% observed-current fraction in evaluation | The simulator is internally consistent with its synthetic tracks; it does not establish real-world containment. |
| Danger zone | ROC AUC 0.9652, average precision 0.8794, precision 0.829, recall 0.8251, Brier 0.0216 | The classifier reproduces environmental proxy labels well on a time-separated external dataset; it does not predict casualties or rescue outcomes. |

## Data gaps ranked by impact

1. **Real buoy pressure and current histories.** Without these, AqOne cannot validate its differentiating sensing claim or prove that the live gates admit enough data for a useful output.
2. **Confirmed local squall and weather-event labels.** The squall classifier currently learns the generator's storm grammar, not observed local storm behaviour.
3. **Real vessel contact histories with known trip boundaries.** The anomaly model needs at least three completed trips per vessel for a vessel-specific baseline and enough normal trips to measure false alarms.
4. **Independent drift outcomes.** Each real search or controlled drifter deployment needs a recovered position/time so contour containment can be measured independently of the simulator.
5. **Observed search detection performance.** The Bayesian update needs field evidence for the `poor`, `moderate`, and `good` detection probabilities.
6. **Independent vessel-safety labels for the danger-zone model.** Environmental thresholds are useful proxies, but they cannot validate vessel risk without incidents, near misses, or an explicitly approved surrogate target.
7. **Danger-zone sector alignment.** The committed artifact stores 3 trained sectors and 40 scan sectors, while `web/js/dangerZonePredictor.js` evaluates only 3 model sectors plus 5 hard-coded cells. The documented 43-sector output is not the current runtime output.
8. **Artifact and provenance alignment.** `web/ml/train_danger_zone_model.py` exports version `2026.08.04-new-washington-grid-v2`, while the committed model card and browser artifact identify `2026.08.04-real-data-v1`; these should be reconciled before another release.

## Council deliberation

### 1. Grounding

**Observed facts:**

- No LLM or foundation model runs in the product.
- Only the browser danger-zone classifier is trained on real external historical data.
- Squall training, trip profiling, and drift evaluation rely on synthetic or simulator-generated data.
- Drift and squall have explicit source, freshness, and quality gates that prefer `unknown` or insufficiency over invented calm or a degraded operational result.
- Real production drift requires current observations from at least two nearby fresh buoys and at least 50% observed particle coverage.
- Live `RETURN NOW` requires a separate release flag and a field-validation record.

**Unverified assumptions:**

- The number, placement, calibration, clock quality, and uptime of future real buoys.
- The actual distribution of vessel routes, trip duration, contact gaps, and irregular behaviour.
- Whether local responders can sustain the false-alarm and workload levels implied by the current thresholds.
- Whether Open-Meteo forecast and marine values are accurate enough for the nearshore cells used by fishers.

### 2. Perspectives

**Devil's Advocate:**

- The synthetic models are partly evaluated against the same assumptions that created them, so high containment or detection numbers can be self-consistency rather than predictive validity.
- Danger-zone labels reuse weather thresholds that are also model features, so its strong metrics mainly prove that the classifier learned the threshold definition.
- A calm forecast cannot represent engine failure, collision, equipment loss, or a vessel outside the monitored coverage.

**Simplicity Champion:**

- The umbrella term “AI layer” is acceptable for the pitch only if every feature is labeled as classifier, statistical profile, physics simulation, Bayesian update, rule engine, or aggregation.
- No LLM, deep-learning stack, feature store, or new data platform is justified before the missing field data exists.
- `catch-density-v1` should be described as an aggregation policy rather than a predictive model.

**Security and Reliability Auditor:**

- The source separation between synthetic and live rows is a strong design choice for the current scope.
- The unknown states and drift insufficiency response are safer than silently substituting synthetic data into a live safety result.
- Every high-impact output needs source type, data age, coverage, model version, limitation, and human-authority wording to remain attached to it.

**Architect and DX Lead:**

- The current modular split is understandable and already matches the product sequence: before trip, during trip, after anomaly, and search.
- The next engineering investment should be a governed pilot data path and evaluation registry, not more model complexity.
- The danger-zone model artifact, training script, model card, and browser runtime need one release identity to stay reproducible.

### 3. Consensus and tension

**Where all seats agree:**

The current system is sufficient as a demonstrable, explainable decision-support prototype.

It is not sufficient to claim field-validated life-safety prediction.

**Core tension:**

The breadth of the AI story is valuable for the pitch, but the evidence is narrow.

Calling the whole umbrella “AI” is reasonable; calling every output a learned prediction is not.

### 4. Verdict

**Recommended path:**

Present AqOne as an AI-assisted safety decision-support layer whose sensing substrate is the buoy network.

Use the exact mechanism labels in the feature table.

Prioritize a field pilot that collects pressure, current, contact, search, and incident-outcome data before adding new models or claiming operational calibration.

Keep live outputs fail-closed to `unknown`, `watch`, responder review, or insufficient environmental data until the corresponding field evidence and named approval exist.

**Revisit when:**

Promote a capability only after a predeclared evaluation set contains independent local observations, outcome labels, coverage and freshness statistics, false-alert and miss rates, and a named human reviewer.

## Ponytail audit findings

`yagni:` Do not add an LLM or a second AI service layer; the existing classifiers, statistical code, physics simulator, and browser runtime already cover the requested outputs. [backend/app/ai, web/ml, web/js/dangerZonePredictor.js]

`yagni:` Do not build server-side forecast fusion yet; the current transparent Open-Meteo proxy is sufficient until real buoy data exists. [backend/app/api/public.py, docs/05_PUBLIC_API.md]

`shrink:` Treat `catch-density-v1` as a named aggregation policy, not a model, and remove predictive language from its documentation. [backend/app/api/hotspots.py]

`shrink:` Keep one release identity and one sector manifest across the training script, browser artifact, predictor, and model card; the current mismatch adds provenance and runtime complexity without adding capability. [web/ml/train_danger_zone_model.py, web/ml/model-card.json, web/js/dangerZoneModel.js, web/js/dangerZonePredictor.js]

Net: no production code or dependencies changed in this read-only audit.

## Evidence paths

- `backend/app/ai/squall.py`
- `backend/app/ai/trip_profile.py`
- `backend/app/ai/anomaly_service.py`
- `backend/app/ai/drift.py`
- `backend/app/ai/current_field.py`
- `backend/app/ai/search.py`
- `backend/app/ai/eval_store.py`
- `backend/app/simulation/generator.py`
- `backend/app/ai/models/eval_results.json`
- `web/ml/train_danger_zone_model.py`
- `web/ml/model-card.json`
- `web/js/dangerZonePredictor.js`
- `mobile/lib/services/safety_score.dart`
- `backend/app/api/hotspots.py`
- `docs/17_AI_EXPLAINED_SIMPLY.md`
- `docs/16_QA_DISCLOSURES.md`
- `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`
- `docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md`
- `docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md`
- `docs/42_DATA_STRATEGY_RESPONSIBLE_AI_IMPLEMENTATION_PLAN.md`
