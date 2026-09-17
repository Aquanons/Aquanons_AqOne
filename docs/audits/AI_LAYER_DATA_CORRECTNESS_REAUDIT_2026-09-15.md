# AqOne AI Layer Data Correctness and Fit Audit

**Post-Gemini re-audit**

- **Date:** 2026-09-15
- **Branch:** `codex/ai-accuracy`
- **Revision inspected:** `601288fa03111252c1a67dcb8c5faa3996385397`
- **Prior context:** `docs/audits/AI_LAYER_DATA_CORRECTNESS_AUDIT_2026-09-14.md`, `docs/AI_ACCURACY_IMPLEMENTATION_PLAN.md`, and the completed Gemini Ponytail simplification plan.
- **Scope:** post-Gemini input-output fit for the before/during/after disaster storyline: warning, contact/anomaly review, drift simulation, search re-tasking, environmental advisories, mobile risk/window guidance, and consented activity aggregation.
- **Method:** read-only inspection of current producers, callers, runtime paths, fallbacks, labels, evaluators, data protocols, firmware transport, and active consumers. No live database, field sensor, responder case, or operational outcome was available.
- **Validation observed:** web Node tests passed (141 tests). Backend Python checks could not run because `python` is not available on this host. Flutter validation was not independently re-run to completion in this audit. Automated tests are not field validation.
- **Repository changes:** only this report is created by this re-audit; no source, test, configuration, generated, database, or existing documentation file was changed.

**Files inspected:** `backend/app/ai/{squall,anomaly_service,trip_profile,drift,current_field,environment,search,drift_eval}.py`; `backend/app/api/{squall,drift,current_events,advisories}.py`; `backend/app/geo.py`; `web/js/dangerZonePredictor.js`; `web/ml/model-card.json`; `mobile/lib/{services/buoy_client,fishing_window,venture_feeds}.dart`; `mobile/lib/ui/app_shell.dart`; `firmware/{shore/AqOneShore/AqOneShore.ino,buoy/AqOneBuoy/AqOneBuoy.ino}`; `backend/app/api/{hotspots,sea_condition}.py`; `docs/08_DEMO_AND_STATUS.md`; `docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`; `docs/49_AI_ACCURACY_DATA_PROTOCOL.md`; `docs/50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md`; `docs/51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md`; and the prior audit.

## Executive verdict

Gemini materially improved provenance labels, explicit insufficiency states, trip lifecycle handling, forecast completeness checks, and the separation of synthetic evaluation from live paths. The repository now contains a credible software demonstration of several mechanisms, but it still does not contain enough measured data to support the stronger safety storyline claims.

The strongest remaining issue is transport fit for the first layer: the shore gateway can send and the buoy can cache a warning, but the active handset UI still polls the internet-backed squall endpoint. The offline-at-sea phone path does not call the buoy warning endpoint, so the warning that is visible in the protocol is not yet the warning the fisherman can actually receive.

The weakest physical inference remains drift/search. Real-case drift enables stranding but does not pass the shoreline polygon; current observations are not filtered for calibration status; the 111 km support radius is not a validated local field; support loss during the forecast does not fail the run; and responder searches still update a static final grid instead of time-aligned trajectories. A result may therefore be labelled `ok` while containing unsupported motion or mis-timed negative evidence.

The most misleading current claim is in `docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`, which says all 23 audit vulnerabilities were “resolved and verified” and describes shadow observation across New Washington. The same repository says the field-validation log is a template and that outdoor deployments and range measurements remain outstanding (`docs/08_DEMO_AND_STATUS.md:35,562-570`). The evidence supports unit and synthetic-fixture verification, not prospective field validation.

The single highest-value correction is to make the real decision path honest end to end: wire the buoy warning cache to the handset, and make real drift/search refuse unsupported or unqualified evidence rather than presenting a completed rescue field.

## Inventory validation

| Component | Current technology type | Re-audit result |
| --- | --- | --- |
| Squall nowcasting | Pattern classifier plus deterministic front/rule logic | Exists; synthetic-calibrated research signal |
| Trip anomaly and overdue detection | Statistical profile plus deterministic rules | Exists; verification support, not distress probability |
| Drift prediction | Physics-based Monte Carlo simulation | Exists; conditional simulation with unresolved support and geometry limits |
| Bayesian search re-tasking | Bayesian update plus deterministic ranking | Exists; production update is static-grid, not trajectory-time aligned |
| Marine hazard or danger zone | Supervised proxy classifier plus threshold rules | Exists; environmental advisory, not casualty prediction |
| Mobile risk score | Deterministic rule engine | Exists; environmental threshold summary |
| Fishing window | Deterministic horizon scanner | Exists; conditional forecast deterioration estimate |
| Consent-based catch-activity surface | Aggregation/privacy policy | Exists; relative reported activity only |
| Legacy current-weather advisory | Deterministic rule engine | Active user-visible output discovered in the prior audit |
| Buoy-current summary | Descriptive statistical aggregation | Active public telemetry summary discovered in the prior audit |

No additional production AI estimator was found. `ai/coverage.py` and `coverage_eval.py` remain evaluation-only with no production inference caller. Demo generators and evaluators are included only where they define runtime fallbacks, labels, or claimed evidence.

### 🏛️ Council Deliberation

#### 1 Grounding

**Observed:** The current branch contains explicit live/synthetic flags, a real-case drift quality gate, a buoy warning transport protocol, trip state tables, and a documented field-measurement protocol. It also contains a live mobile squall polling path, a separate unused `BuoyClient.warnings()` method, synthetic squall calibration metadata, fixed search detection presets, a broad current interpolation radius, and no completed field-validation log.

**Unverified:** No field measurements, controlled drills, independent local squall labels, calibrated current instruments, communication-opportunity tracks, confirmed distress outcomes, search-method detection trials, or independent drift tracks were available. Causal effects cannot be identified from this repository.

#### 2 Perspectives and debate

- **Architecture seat:** The three-stage storyline is structurally present, but the warning path splits at the buoy: the protocol has a cached warning endpoint while the active handset consumer remains internet-backed.
- **Devil’s-advocate seat:** “Resolved and verified” is not supported by repository evidence when field logs are blank, calibration is synthetic, and no responder outcome labels exist.
- **Reliability/security seat:** A gateway acceptance event is not a buoy receipt, a phone receipt, or a user acknowledgement. Delivery events and warning ingestion also need source and time provenance before they can support an operational claim.
- **Simplicity/Ponytail seat:** Several helpers and metadata paths are unused in production. Keeping a trajectory-weighting helper while the API still uses a static update increases apparent completeness without improving the live result.
- **Physical-model perspective:** Drift has a credible mechanism, but its current support, valid-time semantics, land boundary, and object-specific leeway are not sufficient for a real rescue location claim.
- **Decision-science perspective:** Trip silence is evidence of missing communication, not distress. Search presets are responder policy choices, not measured probabilities. Hazard labels are environmental proxies, not incident outcomes.

#### 3 Consensus versus tension

The council agrees that the repository is appropriate as a staged demonstration and data-collection scaffold, but not as a validated autonomous safety system. The disagreement is about sequencing: one view favours collecting field data first; another favours first closing the obvious runtime wiring and unsupported-input gates. The combined recommendation is to close the truthfulness defects that can be fixed from existing data lineage before collecting more data, then run controlled drills that measure the remaining claims.

#### 4 Verdict

The architecture can support the intended before/during/after workflow only as human-reviewed, conditional guidance. It cannot yet honestly claim that an offshore fisherman will receive an AI warning without signal, that an anomaly score establishes safety or distress, or that a drift/search contour is a calibrated rescue probability. The next implementation plan should prioritize the offline warning consumer, source qualification/as-of semantics, time-aligned search updates, and independent field labels.

## Prior finding disposition

| Prior finding | Current disposition | Evidence after Gemini |
| --- | --- | --- |
| SQUALL-01 | Partially resolved | Feature cutoff and event-timing tests improved; calibration remains synthetic and no independent local labels exist. |
| SQUALL-02 | Still open | Runtime/evaluator probability semantics remain different; bundle declares `CALIBRATION='synthetic'` (`backend/app/ai/squall.py:20`, `api/squall.py:116-129`). |
| SQUALL-03 | Substantially improved | Arrival-origin invariants were added and tested; field arrival accuracy remains unverified. |
| TRIP-01 | Partially resolved | Trip states now exist, but candidates still originate only from `buoy_contacts`; no-contact registered trips are omitted. |
| TRIP-02 | Partially resolved | Candidate trips are excluded from profiles, but normal/incident history selection and explicit normal-return labels remain incomplete. |
| TRIP-03 | Partially resolved | Synthetic weather is separated from live evaluation, but live scoring does not inject weather. |
| DRIFT-01 | Still open | Synthetic fallback is disabled in the new real-case run, but calibration filtering, support-loss gating, radius, and legacy fallback remain. |
| DRIFT-02 | Partially resolved | `client_ts` is preferred, but stale timestamps are accepted without a lower-bound/delay policy. |
| DRIFT-03 | Still open | Wind valid-time and local shoreline support are not established; the production call omits `boundary_polygon`. |
| DRIFT-04 | Still open | Evaluation selects synthetic incidents only; no independent drift tracks establish containment. |
| SEARCH-01 | Still open | Production API calls `update_posterior()` without trajectory times or `searched_at`. |
| SEARCH-02 | Still open | `poor/moderate/good` map to fixed 0.3/0.6/0.9 values without field detection data. |
| HAZARD-01 | Partially resolved | Threshold overrides are explicit, but model probability remains an environmental proxy beside a different tier claim. |
| HAZARD-02 | Partially resolved | Buoy adjustment is zeroed, but static depth and communication-independent model inputs remain weak physical support. |
| HAZARD-03 | Still open | Global forecast/marine cells and static 600 m sectors do not establish fine coastal resolution. |
| MOBILE-01 | Mostly resolved | Missing present hourly evidence returns unknown/incomplete; wave absence can still leave a lower-risk environmental result with caveat. |
| MOBILE-02 | Partially resolved | Forecast provenance fields improved, but handset location is not a verified vessel position at decision time. |
| WINDOW-01 | Mostly resolved | Incomplete current/intervening hourly coverage suppresses a positive countdown. |
| WINDOW-02 | Still open | Daily aggregates and variable-specific onset approximations remain insufficient for “time remaining at sea.” |
| CATCH-01 | Partially resolved | Coarse location/activity and report counts are exposed, but effort, seasonality, and reporting bias are not normalized. |
| CATCH-02 | Partially resolved | A truncation flag exists; the recent population and cap semantics still need operational evidence. |
| WEATHER-01 | Mostly resolved | Trigger wording is more explicit; this remains a rule advisory, not sea safety. |
| CURRENT-01 | Partially resolved | Vector/scalar fields improved, but one newest timestamp still summarizes mixed-time and mixed-location samples. |

## Component findings

### Squall nowcasting

**Actual output:** A pressure-pattern detector and plane-wave arrival estimate over qualifying buoy histories. It can produce `clear`, `watch`, or `return_now`; the live bundle is explicitly synthetic-calibrated. This is a research signal, not a calibrated probability of a local squall.

Pressure and buoy coordinates have a plausible mechanism for detecting a propagating pressure disturbance. The model still trains/evaluates from synthetic rows (`backend/app/api/squall.py:193-205`; `backend/app/ai/squall.py:20`). `extract_pressure_features()` substitutes nominal pressure `1013.25` for empty histories (`backend/app/ai/squall.py:252-260`). Runtime quality checks reduce but do not eliminate misuse. The public path can return `return_now` whenever `SQUALL_RETURN_NOW_ENABLED` is set (`backend/app/api/squall.py:64-73,116-161`), despite no independent local onset label set.

**Input verdict:** Keep measured pressure and buoy timing as research inputs; keep but transform synthetic labels into explicitly synthetic calibration; replace operational `return_now` with a field-gated state; add phone receipt only after the handset actually consumes the buoy cache.

**Honest output after fixes:** “A research pressure-pattern signal and, when the handset encounters a buoy, a cached advisory; no validated local squall probability or guaranteed delivered lead.”

##### Finding SQUALL-04: Offline warning output is disconnected from the handset

- Severity: Critical
- Type: wrong input / provenance issue
- Evidence: `firmware/shore/AqOneShore/AqOneShore.ino:554-601`; `firmware/buoy/AqOneBuoy/AqOneBuoy.ino:927-979`; `mobile/lib/services/buoy_client.dart:165-188`; `mobile/lib/ui/app_shell.dart:140-176`.
- Problem: The no-signal phone does not call the buoy warning cache, so the AI warning path does not reach the scenario’s decision-maker.
- Recommendation: Connect the active handset sync loop to `/v1/warnings`, record distinct buoy-received and phone-received events, and keep internet polling as a separate path.
- Target effect: Same warning target; corrects the delivery claim.
- Expected benefit: Establishes whether the before-layer warning can be observed at sea.
- Dependencies: Firmware/handset integration and a controlled radio drill.
- Verification evidence needed: A phone in airplane mode receives one signed warning from a buoy and records receipt time.
- Implementation planning note: Trace every warning consumer before adding another client; do not treat gateway acceptance as handset delivery.

##### Finding SQUALL-05: Synthetic calibration still permits an uncalibrated live return state

- Severity: High
- Type: target mismatch / provenance issue
- Evidence: `backend/app/ai/squall.py:20`; `backend/app/api/squall.py:64-73,116-161,193-205`; `docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md:120-151`.
- Problem: A deployment flag can expose `return_now` while the bundle is synthetic-calibrated and no independent local onset labels exist.
- Recommendation: Keep live detections in research/watch mode until a prespecified local label set and approval evidence exist.
- Target effect: Narrower target.
- Expected benefit: Prevents a synthetic score from being presented as an operational evacuation decision.
- Dependencies: Independent local squall labels and controlled drills.
- Verification evidence needed: A field-labelled event table with pre-decision features and onset times.
- Implementation planning note: Define the event and lead-time target before collecting more predictors.

##### Finding SQUALL-06: Delivery events are accepted without verified source or receipt semantics

- Severity: High
- Type: provenance issue
- Evidence: `backend/app/api/advisories.py:392-480`; `firmware/shore/AqOneShore/AqOneShore.ino:510-527,601`; `docs/51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md:119-127`.
- Problem: The delivery endpoint accepts caller-supplied state and time, while the shore node records `gateway_accepted` immediately after sending. The repository has no producer for verified buoy receipt, phone receipt, or user acknowledgement in the offline path.
- Recommendation: Treat gateway acceptance as transport telemetry only and add authenticated, state-specific receipt events from the buoy and handset.
- Target effect: Same delivery target; removes an unsupported delivery claim.
- Expected benefit: Separates “sent,” “cached,” “received,” and “seen” in the measured lead-time calculation.
- Dependencies: Signed protocol frames, handset sync, and controlled drills.
- Verification evidence needed: One end-to-end event chain with distinct timestamps and rejected forged transitions.
- Implementation planning note: Define event authority and availability time before adding more delivery states.

### Trip anomaly and overdue detection

**Actual output:** A vessel-specific contact-gap/profile score and review status. It does not identify distress or prove that a fisherman is safe.

Contact observations, trip state, expected return/check-in interval, and vessel identity are relevant. The candidate set is built from `buoy_contacts` only (`backend/app/ai/anomaly_service.py:70-87,119-147`), so an already-at-sea registered trip with no contact is invisible. Live scoring calls `score_trip()` without `weather_provider` (`anomaly_service.py:178-185`), so weather cannot explain the current vessel state. `_load_trip_states()` catches every exception and returns an empty state map (`anomaly_service.py:100-113`), silently reverting to the 12-hour legacy cutoff.

**Input verdict:** Keep observed contact timing and explicit trip state. Add registered-trip records and communication-opportunity context. Replace broad database-error fallback with an explicit unknown/needs-review state. Do not label the score as safety or distress probability.

**Honest output after fixes:** “This vessel has missed an expected contact or return condition; communication loss and distress remain unresolved.”

##### Finding TRIP-04: No-contact trips are absent from the candidate population

- Severity: High
- Type: missing input / target mismatch
- Evidence: `backend/app/ai/anomaly_service.py:70-87,119-147`; `backend/app/ai/trip_profile.py:494-510`.
- Problem: A trip registered before departure but never observed by a buoy cannot be scored; the empty-contact path is treated as normal.
- Recommendation: Include open trips with no contacts as an explicit “no opportunity yet/overdue” state, conditioned on the agreed check-in or return expectation.
- Target effect: Same missed-contact target; narrower interpretation than distress.
- Expected benefit: Covers the already-at-sea scenario without turning silence into a casualty label.
- Dependencies: Trip registration and expected-contact data.
- Verification evidence needed: Drill with an open trip, no contact, a known deadline, and a separate benign network-outage branch.
- Implementation planning note: Define whether “no contact yet” is unknown, overdue, or unaccounted before scoring it.

##### Finding TRIP-05: Live anomaly scoring has no weather-at-vessel input

- Severity: High
- Type: missing input
- Evidence: `backend/app/ai/anomaly_service.py:178-185`; `backend/app/ai/trip_profile.py:559-576`.
- Problem: Weather explanations are absent from live scores even when weather is materially relevant to a missed return.
- Recommendation: Add a decision-time, location-matched weather provider only as an explanatory factor; do not infer distress from weather alone.
- Target effect: Same missed-contact target.
- Expected benefit: Separates communication failure from weather exposure in responder review.
- Dependencies: Valid last position, forecast valid time, and provider availability.
- Verification evidence needed: Same trip timeline scored with weather at the vessel location and with unrelated weather.
- Implementation planning note: Preserve location/time provenance and a missing-weather state.

##### Finding TRIP-06: State-source failure silently becomes a legacy heuristic

- Severity: High
- Type: provenance issue
- Evidence: `backend/app/ai/anomaly_service.py:100-113,133-147`.
- Problem: A schema/database failure is indistinguishable from “no trip states,” so the score may use a 12-hour cutoff without telling responders.
- Recommendation: Return an explicit unavailable state when trip-state retrieval fails; use the legacy cutoff only for rows known to be legacy.
- Target effect: Narrower target.
- Expected benefit: Prevents a data outage from changing the meaning of the score.
- Dependencies: Database health signal and UI status wording.
- Verification evidence needed: Inject a state-table failure and confirm no normal/overdue classification is silently emitted.
- Implementation planning note: Handle the failure at the shared loader boundary.

### Drift prediction

**Actual output:** A conditional Monte Carlo distribution of an object’s future positions, using a last position/time, object class, wind, and current forcing. It is not a validated probability that a real fisherman will be inside the contour.

The physical mechanism is credible. The real-case path excludes synthetic current fallback in `_compute_and_persist_run`, but it does not filter `calibration_status='uncalibrated'` (`backend/app/api/current_events.py:36-37`; `backend/app/ai/current_field.py:57-64`). Its historical `as_of` filter uses `observed_at` but not receipt/availability time (`backend/app/ai/current_field.py:45-84`), so a late-arriving observation can leak into replay. `MAX_RADIUS_M=111000` and two buoys are treated as sufficient (`current_field.py:28-30`; `backend/app/api/drift.py:193-212`) without local spatial validation. `support_lost_at` is recorded but not used by `environment.assess_result` to reject a later unsupported trajectory (`current_field.py:254-255`; `environment.py:101-119`). Production enables stranding but omits `boundary_polygon` (`api/drift.py:201-210`), while `geo.WATER_POLYGON` is itself described as approximate. Wind timestamps are parsed as naive Manila-local values and converted through `.timestamp()` without an explicit valid-time contract (`backend/app/ai/drift.py:241-284`). The legacy GET branch can still call `create_current_field_factory(pool)` with synthetic fallback when no run exists (`backend/app/api/drift.py:684-706`).

**Input verdict:** Keep the drift equation as conditional simulation. Replace unqualified current observations, stale/naive wind forcing, approximate boundary assumptions, and unsupported legacy fallback. Add object-specific leeway, land/shore geometry, and independent drift tracks only when those inputs are measured and time-aligned.

**Honest output after fixes:** “Conditional drift distribution for the stated object class and supported observation window; insufficient environmental data suppresses a rescue contour.”

##### Finding DRIFT-05: Real runs use uncalibrated current observations

- Severity: High
- Type: provenance issue
- Evidence: `backend/app/api/current_events.py:36-37`; `backend/app/ai/current_field.py:57-64,195-238`; `docs/50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md:70-77`.
- Problem: Any non-synthetic live row can drive the field, including rows explicitly marked uncalibrated.
- Recommendation: Require the protocol’s qualified/calibrated status before a row contributes to a real run; otherwise report insufficiency.
- Target effect: Same conditional simulation target.
- Expected benefit: Makes “observed-current-driven” mean qualified observation-driven.
- Dependencies: Instrument calibration records and ingestion validation.
- Verification evidence needed: One calibrated and one uncalibrated row with identical geometry; only the qualified row may affect the run.
- Implementation planning note: Filter at the shared loader, not at individual callers.

##### Finding DRIFT-06: Current support radius is not a validated local field

- Severity: High
- Type: scale mismatch / geometry mismatch
- Evidence: `backend/app/ai/current_field.py:28-30,195-238`; `backend/app/api/drift.py:193-212`; `docs/49_AI_ACCURACY_DATA_PROTOCOL.md:104-116`.
- Problem: An 111 km IDW radius can make two one-sided or co-located buoys appear to represent a spatial field over the rescue domain.
- Recommendation: Set support from measured buoy spacing and domain geometry, or suppress spatial interpolation outside a qualified local array.
- Target effect: Narrower supported domain.
- Expected benefit: Prevents broad extrapolation from sparse measurements.
- Dependencies: Buoy survey geometry and independent current observations.
- Verification evidence needed: Cross-validation by leaving out each buoy across representative New Washington locations.
- Implementation planning note: Do not choose a smaller radius by intuition; derive it from measurement spacing.

##### Finding DRIFT-07: Mid-forecast support loss does not fail an otherwise passing run

- Severity: High
- Type: missing input / scale mismatch
- Evidence: `backend/app/ai/current_field.py:254-255`; `backend/app/ai/environment.py:101-119`.
- Problem: Aggregate coverage can exceed 0.5 even when later particles have left observed support; the run remains `ok`.
- Recommendation: Make support loss over the claimed horizon an explicit insufficiency or narrow the forecast horizon to supported steps.
- Target effect: Narrower target.
- Expected benefit: Stops unsupported terminal contours from being presented as fully supported.
- Dependencies: Per-step support accounting and horizon policy.
- Verification evidence needed: A fixture where the ensemble leaves the array halfway through the horizon.
- Implementation planning note: Preserve the first support-loss time in the run’s acceptance decision.

##### Finding DRIFT-08: Production stranding is not using the shoreline boundary

- Severity: High
- Type: geometry mismatch
- Evidence: `backend/app/api/drift.py:201-210`; `backend/app/ai/drift.py:496-497`; `backend/app/geo.py:20-33,55-76`.
- Problem: `enable_stranding=True` has no polygon argument in the production call, so land checks do not run; the available polygon is also documented as approximate.
- Recommendation: Pass an authoritative water/shore geometry only after validating it for the operating area; otherwise narrow the output to unconstrained simulation.
- Target effect: Same target with honest geographic boundary, or narrower target.
- Expected benefit: Prevents particles from crossing land and being grounded correctly.
- Dependencies: Authoritative shoreline, island, channel, and bathymetry data.
- Verification evidence needed: Coastline crossing cases against a surveyed polygon.
- Implementation planning note: Confirm the runtime call graph before claiming the boundary is integrated.

##### Finding DRIFT-09: Legacy no-run GET can return synthetic-backed drift

- Severity: Medium
- Type: wrong input / provenance issue
- Evidence: `backend/app/api/drift.py:684-706`.
- Problem: A real incident without a persisted run can fall through to a factory whose default allows synthetic current, despite the new real-case gate.
- Recommendation: Require a real-case run or return `insufficient_environmental_data`; reserve the legacy branch for explicitly synthetic incidents.
- Target effect: Narrower target.
- Expected benefit: Removes a hidden fallback that changes real output meaning.
- Dependencies: Incident provenance and run lifecycle.
- Verification evidence needed: Real incident with missing run returns insufficiency, not a contour.
- Implementation planning note: Put the provenance guard at the endpoint branch.

##### Finding DRIFT-10: Client fix timestamps accept arbitrarily old datums

- Severity: Medium
- Type: provenance issue
- Evidence: `backend/app/api/drift.py:344-357`; `docs/49_AI_ACCURACY_DATA_PROTOCOL.md:102-107`.
- Problem: Any positive client timestamp not more than five minutes in the future is accepted, even if it is hours or days old.
- Recommendation: Record age and enlarge uncertainty or suppress the claim past a defined datum-age threshold.
- Target effect: Narrower target.
- Expected benefit: Prevents stale SOS metadata from being treated as a precise starting point.
- Dependencies: Device fix quality and explicit age policy.
- Verification evidence needed: Old-fix and fresh-fix cases with the same receipt time.
- Implementation planning note: Preserve physical fix time separately from receipt time.

##### Finding DRIFT-11: Historical current replay is filtered by occurrence time only

- Severity: High
- Type: leakage / provenance issue
- Evidence: `backend/app/ai/current_field.py:45-84`; `docs/49_AI_ACCURACY_DATA_PROTOCOL.md:42-55`.
- Problem: A row whose physical `observed_at` is before `as_of` but whose database receipt is after `as_of` is still loaded, exposing information unavailable at the decision time.
- Recommendation: Store and filter observation availability/receipt time, or state that the source cannot support historical replay.
- Target effect: Same conditional target after leakage control.
- Expected benefit: Makes replay inputs available at the stated decision time.
- Dependencies: Receipt timestamp in the observation source.
- Verification evidence needed: One delayed observation replayed before and after receipt.
- Implementation planning note: Keep occurrence time and availability time as separate fields.

### Bayesian search re-tasking

**Actual output:** A posterior-like grid update and ranked next area under a supplied prior and responder-entered search rectangle. It is not an optimal search plan or calibrated rescue probability.

`update_trajectory_weights()` correctly accepts trajectory arrays, step times, and `searched_at` (`backend/app/ai/search.py:50-99`), but production imports and calls `update_posterior()` only (`backend/app/api/drift.py:15,215-233,775-778,884-891`). Search rectangles are therefore applied to the final static grid. Method labels map to fixed 0.3/0.6/0.9 probabilities (`api/drift.py:37-50,885`), which are policy presets rather than measured conditional detection probabilities.

**Input verdict:** Keep the Bayesian arithmetic as a transparent conditional update. Replace static updates with time-aligned trajectory evidence, and keep method presets as qualitative labels until detection trials establish conditional probabilities.

**Honest output after fixes:** “Remaining mass under the stated prior and reported search assumptions; responder review required.”

##### Finding SEARCH-03: Time-aware trajectory evidence is not wired into production

- Severity: High
- Type: leakage / scale mismatch
- Evidence: `backend/app/ai/search.py:50-99`; `backend/app/api/drift.py:15,215-233,875-890`.
- Problem: A search performed earlier is applied to final-horizon cells, even when the target could have moved elsewhere at the search time.
- Recommendation: Persist trajectory/time state with each run and apply negative evidence at `searched_at`; otherwise label the update as static hypothetical evidence.
- Target effect: Same target after time alignment; narrower interim claim.
- Expected benefit: Makes search re-tasking correspond to where the object could have been when searched.
- Dependencies: Stored particle trajectories, search timestamps, and rerun semantics.
- Verification evidence needed: A moving-target drill with a search at an intermediate time.
- Implementation planning note: Use the existing helper only after tracing all production callers; remove it if the product remains static.

##### Finding SEARCH-04: Fixed detection presets are not measured probabilities

- Severity: High
- Type: wrong input / target mismatch
- Evidence: `backend/app/api/drift.py:37-50,885`; `backend/app/ai/search.py:122-141`.
- Problem: Qualitative responder selections are treated as quantitative likelihoods and renormalized into a posterior.
- Recommendation: Keep them as qualitative conditional assumptions or replace them with method/object/visibility-specific detection estimates from controlled trials.
- Target effect: Narrower target until measured; same target after calibration.
- Expected benefit: Prevents false precision in the next-area ranking.
- Dependencies: Search tracks, sensor method, object visibility, spacing, and independent detections.
- Verification evidence needed: Detection-rate table stratified by method, weather, daylight, and object class.
- Implementation planning note: Do not claim calibration from mathematical normalization.

### Marine hazard or danger zone

**Actual output:** Browser-side per-sector environmental threshold advisory, with a model probability derived from historical environmental proxy labels and deterministic danger/watch floors. The displayed score is not a casualty probability.

Live Open-Meteo weather/marine variables and static GEBCO depth have plausible environmental relevance. The model card explicitly says labels are environmental proxies and global grids are unsuitable for coastal navigation (`web/ml/model-card.json`). Static sectors and 600 m display radii do not establish matching nearshore spatial resolution. `degradedBuoyCount` remains unused (`web/js/dangerZonePredictor.js:123`).

##### Finding HAZARD-04: Model probability and displayed danger tier remain different targets

- Severity: High
- Type: target mismatch
- Evidence: `web/js/dangerZonePredictor.js:160-208`; `web/ml/model-card.json`.
- Problem: The model predicts a broad environmental proxy while deterministic OR thresholds set the displayed tier; the percentage beside the tier can be read as vessel danger probability.
- Recommendation: Rename the percentage as an environmental exceedance score or remove it from the safety tier until one target is defined and independently evaluated.
- Target effect: Narrower target.
- Expected benefit: Aligns wording with the actual label.
- Dependencies: Explicit target definition and local environmental labels.
- Verification evidence needed: Single-condition and combined-condition examples compared with the model label.
- Implementation planning note: Do not add vessel features before deciding whether the target is environment exceedance or casualty risk.

##### Finding HAZARD-05: Fine coastal sectors lack matching data support

- Severity: Medium
- Type: scale mismatch / geometry mismatch
- Evidence: `web/js/dangerZonePredictor.js:30-39,145-151`; `web/ml/model-card.json` limitations.
- Problem: Static 600 m sector circles are displayed from coarse/global forecast inputs and static depth; the result is not a measured nearshore hazard field.
- Recommendation: Preserve the provider cell and valid time in the output or narrow the display to the supported forecast-cell scale.
- Target effect: Narrower target.
- Expected benefit: Prevents false local precision.
- Dependencies: Coastal observations, bathymetry, tide, and vessel context.
- Verification evidence needed: Returned provider grid cells and local measurement comparison.
- Implementation planning note: Derive map geometry from source support, not presentation preference.

### Mobile risk score

**Actual output:** A deterministic environmental risk class for forecast values available to the handset. It is not a probability of vessel safety. Missing values now produce more explicit unknown/caveat behavior, but forecast location and age still describe a provider response rather than a verified vessel position. Keep the rule inputs and transform them only to preserve variable identity and completeness. Honest claim: “listed forecast thresholds at the returned location/time, with missing evidence shown.”

### Fishing window

**Actual output:** A deterministic estimate of when the available forecast first crosses a caution/danger condition. It is not safe time remaining after accounting for travel, fuel, vessel capability, or communication opportunity. The calculator now rejects an unassessed current interval and identifies gaps (`mobile/lib/services/fishing_window.dart:300-470`). Daily rainfall remains date-level evidence, and the one-hour onset adjustment is a convention rather than a measured physical onset for every variable.

##### Finding WINDOW-03: Forecast timing conventions are stronger than the source cadence

- Severity: Medium
- Type: target mismatch / scale mismatch
- Evidence: `mobile/lib/services/fishing_window.dart:137-151,300-470`.
- Problem: Daily aggregates and variable-specific onset adjustments can be rendered as a time countdown even though their physical valid interval is broader or not stated.
- Recommendation: Keep daily evidence date-level and state “first forecast interval/date,” not an exact event time; require source cadence/valid interval before minute-level wording.
- Target effect: Narrower target.
- Expected benefit: Prevents a forecast aggregate from being mistaken for a measured onset.
- Dependencies: Provider valid intervals and local verification.
- Verification evidence needed: A timeline with daily rain, hourly wind, gust, wave, and missing intervals.
- Implementation planning note: Use the coarsest time resolution supported by the input.

### Consent-based catch-activity surface

**Actual output:** Coarse, consented spatial aggregation of reported catch activity. It is not abundance, biomass, effort-normalized productivity, or a prediction that fish are present. The service exposes coarse location/activity metadata and report counts (`backend/app/api/hotspots.py:73-98`). Keep the aggregation and privacy cap; narrow every planning claim to relative reported activity.

##### Finding CATCH-03: Report activity is not effort-normalized planning evidence

- Severity: Medium
- Type: target mismatch / provenance issue
- Evidence: `backend/app/api/hotspots.py:73-98`; catch schema and service callers.
- Problem: Repeated or unevenly reported trips can look like productive areas without exposure or effort denominators.
- Recommendation: State relative reported activity and add effort/season/gear normalization only if the planning target is changed to catch rate.
- Target effect: Narrower current target, or different target for catch rate.
- Expected benefit: Prevents the surface from being interpreted as fish abundance.
- Dependencies: Consent-preserving effort and independent validation.
- Verification evidence needed: Same area with unequal reporting effort and repeated contributors.
- Implementation planning note: Do not add correlated environmental features until the planning target is explicit.

### Legacy current-weather advisory

**Actual output:** A deterministic atmospheric predicate consumed by older weather UI paths. It can identify stated wind/rain/condition thresholds but cannot establish overall sea safety. Keep only the named predicates and explicit unknown state. No new learned target is justified.

### Buoy-current summary

**Actual output:** Descriptive scalar/vector statistics over buoy observations. It is not a fresh local flow vector unless the sample set has a declared spatial, temporal, depth, and calibration support. Current code reports scalar and vector information, but a newest timestamp can still mask mixed-age and mixed-location samples (`backend/app/api/sea_condition.py:31-76,133-150`). Keep raw support metadata and narrow wording to “time-qualified buoy telemetry summary.”

## Cross-component conclusion

| Component | Actual output type | Output claimed | Right inputs? yes / mostly / no | Top add | Top drop or replace | Target change required? | Honest claim after fixes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Squall nowcasting | Synthetic-calibrated pressure-pattern signal | Offshore early warning/return-now | no | Independent local onset labels and offline phone receipt | Un-gated live `return_now` | Yes, narrow to research/watch until validated | Research pressure-pattern signal delivered when a phone reaches a buoy |
| Trip anomaly | Profile/rule contact review | Safe or missing fisherman determination | no | Open-trip/no-contact state and communication opportunity | Distress/safety wording | Yes, missed-contact review | Missed expected contact; cause unresolved |
| Drift prediction | Conditional particle simulation | Rescue drift location | no | Qualified current/wind, datum age, shoreline, leeway, independent tracks | Synthetic/unsupported legacy fallback | Yes, conditional/narrowed | Conditional drift distribution under supported inputs |
| Bayesian re-tasking | Grid likelihood update/ranking | Search target posterior and next area | no | Time-aligned trajectories and measured POD | Fixed quantitative presets | Yes, advisory conditional ranking | Remaining mass under stated assumptions |
| Danger zone | Environmental proxy plus thresholds | Vessel danger probability | no | Exact local environmental target and source support | Casualty/probability wording | Yes, environmental advisory | Named forecast threshold advisory |
| Mobile risk score | Deterministic environmental class | Fisher safety | mostly | Verified vessel location and complete variables | Safe implication from missing evidence | Yes, environmental-only | Forecast threshold status with unknowns explicit |
| Fishing window | Forecast threshold crossing | Time left to fish/return | mostly | Source valid intervals and travel context | Exact onset from daily aggregate | Yes, forecast deterioration timing | Approximate first deterioration interval/date |
| Catch activity | Consent-preserving aggregation | Fishing hotspot/fish presence | mostly | Effort and reporting-bias context | Abundance/productivity wording | Yes, relative activity only | Relative reported catch activity |
| Legacy weather advisory | Rule predicate | Sea safety | mostly | Explicit trigger/time/source | General safety wording | Yes, atmosphere-only | Named atmospheric predicate or unavailable |
| Buoy-current summary | Descriptive statistic | Local current | mostly | Calibration, sample support, oldest/newest times | Newest-only freshness implication | Yes, telemetry summary | Time-qualified buoy telemetry statistics |

## Prioritized planning handoff

| Priority | Finding ID | Component | Short problem | Recommended change | Target effect | Evidence required before implementation |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | SQUALL-04 | Squall / warning transport | Offline handset never consumes buoy warning cache | Wire handset sync to `/v1/warnings` and record receipt states | Same warning target; correct delivery claim | Airplane-mode phone, buoy, gateway controlled drill |
| 2 | SQUALL-06 | Warning transport | Gateway events are not verified handset delivery | Add authenticated buoy/phone receipt events | Same delivery target | End-to-end event-chain drill |
| 3 | DRIFT-05 | Drift | Uncalibrated live currents can drive real runs | Filter for qualified calibration status at ingestion/loader | Same conditional target | Qualified versus unqualified row lineage test |
| 4 | DRIFT-08 | Drift | Production stranding boundary is not passed and polygon is approximate | Validate and wire authoritative shoreline geometry, or narrow claim | Same target or narrower | Surveyed shoreline crossing cases |
| 5 | DRIFT-07 | Drift | Later unsupported particles can remain in an `ok` run | Fail or shorten the run at support loss | Narrower target | Mid-horizon support-loss replay |
| 6 | SEARCH-03 | Bayesian search | Negative evidence is applied to the wrong time state | Use trajectory/time-aware update or label static update | Same target after alignment; narrower interim | Moving-target search drill |
| 7 | SEARCH-04 | Bayesian search | Fixed presets are presented as likelihoods | Measure conditional detection or keep qualitative | Narrower interim; same after trials | Method/visibility/daylight detection table |
| 8 | TRIP-04 | Trip anomaly | No-contact open trips are invisible | Include explicit registered-trip state | Same missed-contact target | No-contact and benign outage drills |
| 9 | TRIP-06 | Trip anomaly | Database state failure silently changes semantics | Emit unavailable state instead of legacy fallback | Narrower target | Forced loader failure test |
| 10 | SQUALL-05 | Squall | Synthetic calibration can be promoted by environment flag | Keep live output in research/watch mode until field gate | Narrower target | Independent local event labels |
| 11 | DRIFT-06 | Drift | 111 km current support is not locally validated | Derive support from buoy geometry and cross-validation | Narrower domain | Buoy array spatial validation |
| 12 | DRIFT-09 | Drift | Legacy endpoint can synthesize a real case | Require persisted qualified run for real incidents | Narrower target | Missing-run real incident test |
| 13 | TRIP-05 | Trip anomaly | Live score lacks weather-at-vessel context | Add time/location-matched weather explanation | Same target | Weather-linked trip replay |
| 14 | HAZARD-04 | Danger zone | Model score and danger tier describe different targets | Rename/remove score or define one target | Narrower target | Proxy-label/tier comparison |
| 15 | WINDOW-03 | Fishing window | Forecast cadence does not support exact onset wording | Use interval/date wording for aggregates | Narrower target | Mixed-cadence forecast timeline |
| 16 | CATCH-03 | Catch activity | Reports lack effort and bias denominators | Keep relative activity wording or change target to catch rate | Narrower or different target | Effort-normalized validation sample |
| 17 | DRIFT-10 | Drift | Stale client datum accepted as precise | Add age uncertainty/suppression policy | Narrower target | Old versus fresh fix replay |
| 18 | DRIFT-11 | Drift | Late-arriving observations can leak into historical replay | Filter by availability/receipt time as well as occurrence time | Same target after leakage control | Delayed-observation replay |

## Ponytail audit

`delete:` `degradedBuoyCount` is assigned but never read; remove it rather than carrying a fake buoy-health feature into a physical hazard score. [web/js/dangerZonePredictor.js:123]

`delete:` `EVAL_HORIZONS` is declared but unused; remove it until an evaluator consumes it. [backend/app/ai/drift_eval.py:143]

`delete-or-wire:` `update_trajectory_weights()` and `record_trajectories` form a second trajectory path that production does not call; either wire the existing path for SEARCH-03 or delete the speculative path. [backend/app/ai/search.py:50-99; backend/app/ai/drift.py:433-459]

`shrink:` The synthetic and zero-current empty factories duplicate the same metadata setup; one small factory with an explicit mode would reduce repeated closure code without changing behavior. [backend/app/ai/current_field.py:151-176]

`stdlib:` Replace the literal `3.141592653589793` with `math.pi`; same behavior, less noise. [backend/app/ai/drift_eval.py:149]

`net: -40 lines, -0 dependencies possible.`

## Scope boundaries

This re-audit does not evaluate code quality, architecture, API design, governance, ownership, deployment, release readiness, UI quality, or general responsible-AI policy. Tests are considered only when they define a label, target, data-generation process, or the evidence boundary. Synthetic self-consistency is not treated as real-world validation. External provider availability is not treated as local suitability. No causal conclusion is established by this repository.
