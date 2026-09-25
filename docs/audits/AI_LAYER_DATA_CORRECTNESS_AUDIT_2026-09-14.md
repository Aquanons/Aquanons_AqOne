# AqOne AI Layer Data Correctness and Fit Audit

> **Note (2026-09-25): barometer dropped.** The buoy barometer is no longer part of the
> architecture; squall alerts now come from the PAGASA weather API (PRD §5.1).
> References below to barometers, pressure readings or the pressure-based squall model
> describe that retired design and the code it left behind (`backend/app/ai/squall.py`,
> `barometric_readings`, `/api/v1/pressure-events`), which stays until it is removed.

- Date: 2026-09-14.
- Inspected branch: `codex/ai-layer-audit`.
- Inspected revision: `e1e3904a8ff55ec858805ec2de1d2f87ae92cb16`, plus the pre-existing, untracked reference audit.
- Scope: input-output fit, physical interpretation, decision-time availability, provenance, labels, evaluation targets, geometry, and fallback semantics of active AI and AI-adjacent outputs.
- Method: static inspection of producers, callers, consumers, training routines, generators, and evaluators; limited primary-source checks of physical definitions and provider variable semantics.
- No live database, actual deployed service, field sensor, or recorded operational outcome was inspected.
- No model was retrained, evaluator executed against a database, or fixture regenerated.
- No files other than this report were changed by this audit.
  The reference audit was already untracked when inspection began and was preserved.

Files inspected, grouped by the evidence they supply:

- Project claims: `AGENTS.md`, `docs/00_START_HERE.md`, `docs/Aqone_PRD (2).md`, `docs/05_PUBLIC_API.md`, `docs/08_DEMO_AND_STATUS.md`, `docs/17_AI_EXPLAINED_SIMPLY.md`, `web/ml/README.md`, and `docs/audits/AI_LAYER_DATA_SUFFICIENCY_AUDIT_2026-09-14.md`.
- Computations and evaluation lineage: `backend/app/ai/squall.py`, `squall_eval.py`, `trip_profile.py`, `trip_profile_eval.py`, `anomaly_service.py`, `run_anomaly_evaluation.py`, `drift.py`, `drift_eval.py`, `current_field.py`, `environment.py`, `search.py`, `coverage.py`, `coverage_eval.py`, `eval_store.py`, and `models/eval_results.json` under that directory.
- Data producers and services: `backend/app/simulation/generator.py`, `backend/app/geo.py`, `backend/app/main.py`, and `backend/app/api/{squall,pressure_events,contacts,sos,drift,public,hotspots,catch,sea_condition,metrics}.py`.
- Data-time definitions: `backend/migrations/001_init.sql` and `backend/migrations/007_sos_ingest.sql`.
- Browser model and consumers: `web/ml/train_danger_zone_model.py`, `web/ml/model-card.json`, `web/js/dangerZoneModel.js`, `web/js/dangerZonePredictor.js`, and `web/js/dashboard/{dashboard-markers,dashboard-tools,dashboard-ai-ops,dashboard-sar,dashboard-hotspots}.js`.
- Handset producers and consumers: `mobile/lib/services/{safety_score,fishing_window,forecast_provider,venture_feeds,location_service,catch_service}.dart`, `mobile/lib/models/{daily_outlook,forecast_outlook,weather_snapshot,hotspot_cell,sea_condition}.dart`, `mobile/lib/data/{forecast_cache,demo_hotspots}.dart`, `mobile/lib/core/config.dart`, `mobile/lib/ui/{home_page,venture_page}.dart`, `mobile/lib/ui/widgets/{weather_card,sea_condition_banner}.dart`, and `mobile/lib/l10n/app_en.arb`.
- Repository searches covered `backend/app`, `mobile/lib`, `web/js`, `firmware`, and `gateway` to distinguish active consumers from unused modules and inspect evidence of sensor producers.
  Search matches are not evidence that field hardware exists or measures at the claimed accuracy.
  The opaque `squall.pkl` artifact was located but not deserialized; its fitted coefficients and embedded metadata were not independently inspected.

Citations below are repository-relative `path:line` references, or named functions where a whole transformation is relevant.
They refer to the inspected revision, not necessarily a future implementation.
“Not stated” means the repository does not establish the quantity; a provider's present documentation is not a record of the model/grid selected for a historical request.
Application polling, forecast valid-time spacing, provider model updates, and sensor sampling are separate clocks throughout this report.
“Available” describes a data path, not validation of its local suitability.

## Executive verdict

The layer contains physically relevant inputs, but several outputs exceed what those inputs identify.
Wind, current, pressure, contact time, and reported catch location are sensible measurements for some narrowly defined tasks.
Their presence does not establish squall forecast skill, distress detection, local vessel safety, calibrated search containment, or fish abundance.
There is no repository evidence sufficient to identify causal effects for any component.
Physical mechanisms below are engineering judgments, predictive usefulness is assessed against the actual target, and causal identification is explicitly withheld.

The strongest data fit is the consent-based catch surface **when defined strictly as relative reporting activity**.
Its inputs directly define that aggregation, although its time window and “independent observations” language need correction.
Among physical estimators, the drift equation has the clearest mechanism, but the environmental lineage and datum do not yet support its operational interpretation.

The weakest fit is squall nowcasting: the synthetic positive windows occur before their own event generates any pressure perturbation, and the live output takes the maximum of a classifier probability and an uncalibrated rule score.
This is more specific than the prior audit's lack-of-field-data finding.

The most misleading current claim is a real-case drift field described as using observed currents without synthetic fallback.
The executed loader does not filter synthetic rows, interpolation can use observations from both sides of simulation time, and reported coverage describes only the last particle step.
The same path actually substitutes the synthetic current equation for unsupported particles.
These are demonstrated lineage discrepancies, not merely missing validation.

The single highest-value correction is **DRIFT-01: make the current input's provenance and time support match the real-case claim**.
Until then, narrow the result to a conditional demonstration or return environmental insufficiency; adding more sensors alone will not fix the meaning of the current coverage field.

## Inventory validation

| Evaluated component | Technology type | Active output and trace |
| --- | --- | --- |
| Squall nowcasting | Supervised classifier plus deterministic detection/projection rules | `api/squall.py:76` → `ai/squall.py:768` → public/dashboard squall status; handset polling in `venture_feeds.dart:squall` |
| Trip anomaly and overdue detection | Statistical profile plus deterministic score | `anomaly_service.py:124` → `trip_profile.py:453` → persisted score/review case; dashboard AI operations |
| Drift prediction | Physics-based simulation | `api/drift.py:179` → `ai/drift.py:368` → grid and contours for a responder-opened case |
| Bayesian search re-tasking | Bayesian update plus deterministic cell ranking | `api/drift.py:711` → `ai/search.py:49,101` → updated grid, contours, next-area suggestion |
| Marine hazard or danger zone | Supervised classifier plus deterministic rules | `dangerZonePredictor.js:222` → exported GBDT and rule postprocessing → dashboard map |
| Mobile risk score | Deterministic rule engine | `forecast_provider.dart:75,176` → `SafetyScore.applyTo` → daily forecast strip |
| Fishing window | Deterministic rule engine | `weather_card.dart:78` → `FishingWindowCalculator.calculate` → hourly deterioration estimate |
| Consent-based catch-activity surface | Aggregation or privacy policy | `api/hotspots.py:73` → `aggregate_hotspots` → handset and dashboard cells |
| Legacy current-weather advisory, newly discovered | Deterministic rule engine | `WeatherSnapshot.looksUnsafe` → `weather_card.dart:219` and `venture_page.dart:536` |
| Buoy-current summary, newly discovered | Other: descriptive statistical aggregation | `api/sea_condition.py:_buoy_telemetry` → public sea condition → `sea_condition_banner.dart:98` |

The first eight requested components all exist, but the mobile score and fishing window are separate computations, not a server fusion model.
The two added components are included because their active outputs independently imply environmental conditions to users.

| Discovered but excluded item | Reason for exclusion |
| --- | --- |
| `ai/coverage.py`, `coverage_eval.py` | Evaluation-only geometric coverage estimator; no production inference caller found; committed evaluation artifact has no coverage result, and `dashboard-sar.js:sarRowsFromResults` does not render a coverage section despite the evaluator's comment claiming it does |
| `mobile/lib/data/demo_hotspots.dart` | Unused illustrative surface in the active map path inspected; `venture_page.dart:303` consumes the service surface without selecting `DemoHotspots.surface`; its comment claiming automatic fallback is stale |
| `trip_profile.py:get_weather_snapshot` | Not the provider used by live anomaly scoring; `anomaly_service.py:148` injects none, so the synthetic default wins; documented below as an existing but unused candidate source, not an operational input |
| `AqOneConfig.marineSampleLat`, `marineSampleLon` | Not used by the active forecast provider; actual wave requests use supplied `lat,lon`; no finding based on the stale “fixed offshore point” comment |
| Backend forecast fusion model | No such active model; `public.py:297-304` explicitly returns provider data without `risk`; consumer comments describe an intended future source |
| Multi-incident optimization and residual drift learning | Explicit roadmap items in `docs/Aqone_PRD (2).md:189,209`; no active learned correction or allocation module found |
| Public wave/capsize alert placeholder endpoints | Empty alert responses in `public.py`, not an active estimator with a training target; do not infer that a detector assessed the water and found no hazard |
| Human sea-condition declarations and authored advisories as independent AI components | Human decisions, not inferred physical quantities; their authority/status is evaluated as an input to the fishing window, without auditing the human decision process |
| Model evaluators, generators, and demo scenario modules as separate components | Not independent production estimators; included only where they define labels, fallback inputs, calibration, or claimed evaluation evidence |
| Raw weather display, static map decorations, and other dashboard counters | Not new AI estimators; weather-derived safety language is covered by the legacy advisory; no general dashboard or UI audit is attempted |

## Component findings

### Squall nowcasting

#### Claimed output

The PRD claims prediction of localized convective squall onset and an early `RETURN NOW` alert (`docs/Aqone_PRD (2).md:133-137`).
`docs/17_AI_EXPLAINED_SIMPLY.md:27-42` claims a learned distinction between pressure drops that become squalls and normal weather.
The active code instead recognizes a synthetic-trained pressure-array pattern, optionally projects pressure-onset timing, and returns `unknown`, `clear`, `watch`, or a flag-enabled `return_now` (`api/squall.py:76-168`).
The scored object is an array of fixed buoys, not a particular boat or a directly observed gust front at a boat.
Training positives are nominally 30, 45, 60, 75, or 90 minutes before a generator event's `started_at`; arrival output selects buoys within 90 minutes or substitutes a fallback selection (`squall.py:619-633,706-719`).
Those are three distinct targets: future meteorological squall, present pressure-pattern detection, and conditional front arrival at a buoy.

A meteorological squall is defined by abrupt, sustained wind increase, not by a pressure-drop threshold; a local wind time series provides a direct event definition ([NOAA glossary](https://forecast.weather.gov/glossary.php?word=SQUALL)).
Pressure evolution is physically plausible context for atmospheric disturbances, but pressure alone does not identify all local squalls or their wind severity.
The repository supplies synthetic predictive results, not demonstrated local forecast usefulness or causal identification.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `pressure_hpa`, `buoy_id`, `observed_at` | Training input; runtime input | `squall.py:74-77,219-236`; `pressure_events.py:58-75`; `api/squall.py:28-61` | Synthetic training; gateway-declared live telemetry at runtime | Received samples yes; full retrospective history is not automatically decision-time data | Fixed buoy point; sensor accuracy, height, exposure and field spacing not stated | Synthetic 5 min; live cadence not measured here; expected 5 min, max gap/age 10 min | Keep but transform | Preserve calibrated pressure, timestamp and quality; disturbances are relevant proxies, not direct wind-event labels |
| `lat`, `lon` of each buoy | Training/runtime input; static geometry | `squall.py:239-247,282-354` | Synthetic positions for training; stored positions for live; survey evidence not supplied | Yes if correct at sampling time | Point coordinates; non-collinearity test, no minimum useful aperture | Static; movement/survey update cadence not stated | Keep | Needed to infer pressure-pattern propagation; geometry must represent actual sensors |
| `pressure_tendency_30`, `pressure_tendency_60`, `second_derivative`, `deviation_from_mean` | Derived feature | `squall.py:477-511` from `pressure_hpa` at `as_of`, minus 30/60 min and simultaneous array mean | Derived | Yes from historical samples; carry-forward may conceal gaps | Per buoy; deviation relative to whichever buoys qualify | 30/60 min finite differences; 90 min lookback | Keep but transform | Pressure change is plausible; inter-sensor offsets and changing array membership can masquerade as gradients |
| `mean_tendency_30`, `min_tendency_30`, `std_tendency_30`, `mean_tendency_60`, `min_tendency_60`, `std_tendency_60`, `mean_second_derivative`, `min_second_derivative`, `std_second_derivative`, `min_deviation`, `std_deviation` | Derived training/runtime features | `squall.py:40-62,515-538`; aggregations of preceding row | Derived | Yes with adequate history | Whole qualifying array, not a forecast grid | Recomputed per detection from 5 min resampled history | Keep but transform | Retain physical units, array composition and sensor normalization; usefulness beyond direct pressure tendencies is unmeasured |
| `mean_deviation` | Derived training/runtime feature | `squall.py:468,485,526` | Derived | Yes | Array | Same instant | Drop | Mean of deviations from the same mean is zero apart from roundoff; it cannot represent a physical gradient |
| `array_drop_hpa`, `anomaly_energy` | Derived training/runtime features; rule input | `squall.py:490,529-530,602-606` | Derived from negative deviations from simultaneous array mean | Yes | Inter-buoy contrast | Instantaneous contrast, not total pressure fall over the lookback | Keep but transform | `array_drop_hpa` is max negative spatial deviation; rename its physical meaning; evaluator calls it a lookback drop incorrectly |
| `onset_time`, `propagation_speed_mps`, `propagation_bearing_sin`, `propagation_bearing_cos`, `propagation_r2`, `propagation_residual_minutes`, `onset_coverage`, `onset_span_minutes` | Derived training/runtime features | `squall.py:282-354,492-502,531-537`; pressure thresholds plus buoy geometry | Derived | Conditional on detected historical onsets | Plane-front fit through buoy points | Onsets quantized to 5 min; bearing scanned in 5° increments | Keep but transform | Represents a moving pressure pattern under constant front assumptions; not independently identified storm movement |
| `label`, `started_at`, `lead_minutes`, `group_id` | Training and evaluation label/target | `squall.py:695-719`; `squall_eval.py:86-119` | Synthetic event schedule | Labels are retrospective, appropriately not runtime features | One event/array label; no independent local arrival target | Leads 30-90 min before event start; negatives outside protected windows | Replace | Own-event pressure is exactly absent at every positive feature cutoff; see SQUALL-01 |
| `front_origin_lat`, `front_origin_lon`, `bearing_deg`, `speed_kph`, `pressure_drop_hpa`, `rise_minutes`, `hold_minutes`, `started_at`; `diurnal`, `semi_diurnal`, `slow_trend`, `noise` | Training data-generation inputs | `generator.py:480-614,617-643` | Synthetic | Available only to generator, not independent measurements | 10.5 km cross-front attenuation scale; 24-34 km path | Speed 20-40 km/h; 30-60 min rise; 45-120 min hold; synthetic cycles/noise | Replace | Useful simulation controls but not evidence for local storm physics or event prevalence |
| `_latest_before` value `1013.25`, or earliest reading before series begins | Fallback input | `squall.py:251-258`; training calls extraction without live gate | Synthetic constant or future-relative boundary value | Not a measurement at the requested earlier time | Buoy slot | Unlimited early-history substitution | Drop | Live gate normally excludes absent arrays; training/evaluation still need explicit causal history rather than invented prehistory |
| `DEFAULT_THRESHOLD=0.55`, `_window_score`, `probability`, `confidence` | Static decision parameters and derived decision score | `squall.py:23,602-637`; `api/squall.py:134-165` | Human-chosen rule mixed with fitted classifier | Yes | Array | Per detection; handset and dashboard poll ~60 s | Keep but transform | Valid as an explicit candidate rule score; max of two scores is not a calibrated probability |
| `QUALITY_MIN_BUOYS=3`, pressure range 850-1100, gap/age policy, `SQUALL_RETURN_NOW_ENABLED` | Static quality parameters; human authority decision | `squall.py:33-38,365-438`; `api/squall.py:64-73` | Policy | Yes | Qualifying array | Gate per request; flag update cadence not stated | Keep | Filters missing/unusable information; it does not supply event labels, calibration, or minimum upstream coverage |

`contact_radius_m` is loaded into `BuoyMeta` but does not enter the classifier or arrival equations; do not count it as meteorological spatial resolution.
The environment flag is the implemented runtime permission input; a field-validation record is discussed by documentation but is not read by `_return_now_enabled`.
This observation concerns what the output is conditioned on, not approval or release process.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Independently timed local squall onset/severity labels from wind measurements and event review (Add) | Necessary for real squall prediction | Defined gust event at a specified buoy/location within a stated lead horizon | Requires new field collection and labeling; no independent local series evidenced | Same intended target; replaces wrong synthetic target | Pressure is a predictor candidate, not an adequate definition of wind outcome |
| Sensor offsets, pressure reference/exposure, clock error, field sampling record (Add) | Necessary for array propagation | Pressure gradient and onset order that are atmospheric rather than instrument artifacts | Requires hardware characterization; ingest timestamp exists | Same target | Small inter-sensor differences trigger onsets |
| Downstream target location plus fitted front time intercept and timing uncertainty (Add) | Necessary for arrival claim | Conditional arrival at an actual buoy or explicitly named location | Geometry and fitted intercept exist during computation; intercept is discarded | Same arrival target | Origin time must correspond to the spatial origin |
| Upstream buoy density/aperture and observed front passages (Add) | Necessary for claimed early warning coverage | Lead time within observable propagation directions | Stored buoy coordinates exist; deployment/performance evidence requires collection | Same target or narrower monitored-array target | Three non-collinear sensors are not a guarantee of useful warning lead time |
| Local terrain and sea-breeze convergence / mesoscale boundary observations (Add later) | Helpful for initiation or rapidly changing fronts | Explain events that do not simply advect through the array | No verified connected local source; requires source assessment | Same meteorological target | A fixed moving plane cannot describe local initiation; not justified merely to predict synthetic labels |
| Radiosonde/sounding data (Add later) | Helpful environmental context, not necessary for pressure-pattern reporting | Instability/shear context for genuine convective forecast | Not connected in inspected path; availability/cadence not stated | Same meteorological target | Coarse sounding context alone does not locate imminent local onset |
| Satellite cloud-top temperature and lightning (Add later) | Helpful for active convection | Confirm/upstream-track convection independently of pressure | Not connected in inspected path; source access and latency unverified | Same meteorological target | Could discriminate convective systems, but incremental local skill must be measured |

#### Scale, geometry, leakage, and circularity findings

1. **The synthetic target precedes its own signal.** For any event and buoy, `_event_pressure_at` returns zero for negative along-track position, and for nonnegative position until `started_at + along/speed`.
   Training features stop at `started_at - lead` with strictly positive lead.
   Therefore the labeled event contributes zero pressure throughout its own positive window, even before considering noise.
   Other overlapping events or sampling artifacts can supply patterns, but cannot establish predictability of that independently sampled future event.
   The prior audit's description that training learns its generated precursor drops is materially incomplete.
2. **Target leakage versus circularity are different here.** The more direct failure is absent causal signal in the synthetic precursor target, not necessarily a future feature on every sample.
   Separately, the time-split evaluator passes full-history arrays to `assess_array_quality`, which uses `series[-1]` for freshness (`squall.py:398-401`), and `_latest_before` can substitute an earliest reading newer than an early feature time.
   Historical eligibility can therefore depend on data unavailable at that cutoff even though feature extraction generally uses past values.
3. **Evaluated and displayed scores differ.** `squall_eval.py:194-199` evaluates raw classifier probabilities; `detect_squall` raises them with `_window_score`.
   Training's stored holdout uses `pipeline.predict` rather than the deployed 0.55-plus-rule decision (`squall.py:737-746`).
   Neither the old committed metrics nor the newer evaluator establishes skill of the complete displayed decision.
4. **Arrival geometry loses a fitted parameter.** `estimate_propagation_vector` fits `offset = slope * along + intercept`, then retains the earliest onset time with the spatial centroid but discards `intercept`.
   `_arrival_projection` assumes the front was at that centroid at the earliest onset.
   The resulting ETA is early by the missing intercept under a perfect planar example; clipping negative delays to zero conceals the displacement.
   If no projection exists, three buoys receive artificial zero-minute arrivals.
5. **A hull of selected buoys is not a measured storm boundary.** It has no lateral storm-width estimate or island/terrain-dependent evolution.
   Five-minute onset sampling and a constant-speed plane may be appropriate for a conditional fit, but do not justify precise arrival of a changing convective storm.
6. **Missing information partly remains explicit.** Live quality failure returns `unknown`, not calm.
   `clear` means no candidate crossed this detector's threshold in a qualifying array, not absence of squalls outside the array or absence of every storm mechanism.

#### Highest-value correctness change

Replace the event-start label with a location-specific, independently defined onset target and decision cutoff.
This changes the existing synthetic target to the intended physical target; until that evidence exists, narrow the output to pressure-pattern candidates.

#### Input to drop or replace

Drop `mean_deviation`: it is identically zero up to floating-point error.
More consequentially, replace the pre-event synthetic labels before interpreting any fitted feature importance.

#### Minimum defensible input set

- Calibrated pressure histories with measurement times and surveyed geometry: **already present but unsuitable or incomplete**; measurement paths exist, field characterization does not.
- A defined array/location and causal history cutoff: **already present but unsuitable or incomplete**; fixes temporal interpretation on the same target.
- Independent wind-defined onset labels and non-events: **requires new collection**; enables the intended squall target and out-of-event predictive evaluation.
- Front origin time/intercept and uncertainty: **available from an existing source but not currently used**; preserves arrival geometry for conditional estimation.
- Pressure-pattern score instead of calibrated squall probability while evidence is synthetic: **requires a narrower or different target**; makes the claim honest without adding speculative features.

#### Beyond the prior audit

Adds the positive-window/own-event contradiction, decision-score/evaluator mismatch, spatial meaning of `array_drop_hpa`, zero-information `mean_deviation`, and lost propagation intercept.
Confirms synthetic training and insufficient field evidence without treating those alone as new findings.

#### Honest output after fixes

“A pressure-pattern candidate was detected in this monitored array; conditional pressure-front arrival estimates are shown only where geometry and timing support them.”
A real squall probability or guaranteed warning lead time requires independent local predictive evidence beyond these corrections.

#### Plan-ready findings

##### Finding SQUALL-01: Positive windows contain no signal from their own event

- Severity: High
- Type: target mismatch
- Evidence: `backend/app/ai/squall.py:706-719`; `backend/app/ai/squall_eval.py:103-119`; `backend/app/simulation/generator.py:584-614`.
- Problem: Labels precede the earliest possible pressure perturbation generated by the labeled event; synthetic skill cannot be interpreted as learning that event's precursor.
- Recommendation: Define onset at a specific location and lead cutoff using independent wind-event observations; use pressure-pattern reporting until such labels exist.
- Target effect: different target
- Expected benefit: Separates genuine anticipation of a physical event from recognition of unrelated synthetic patterns.
- Dependencies: New labeling and hardware collection.
- Verification evidence needed: One isolated generated event with its positive cutoffs demonstrates zero own-event pressure; then independently timestamped local event/non-event examples at declared horizons.
- Implementation planning note: Establish the physical event definition and whether the task is initiation prediction or downstream arrival before changing any features.

##### Finding SQUALL-02: Displayed probability and evaluation target are different quantities

- Severity: High
- Type: target mismatch
- Evidence: `backend/app/ai/squall.py:602-637,737-746`; `backend/app/ai/squall_eval.py:194-199`; `backend/app/ai/squall.py:398-401`.
- Problem: Runtime uses the maximum of a classifier probability and rule score, while evaluation measures the classifier; retrospective freshness can use later rows.
- Recommendation: Name the combined result a candidate score and evaluate that exact decision with all data and quality checks restricted to each decision cutoff.
- Target effect: narrower target
- Expected benefit: Prevents classifier metrics and future-informed eligibility from substantiating a different live alarm.
- Dependencies: Existing sources; new independent labeling for physical forecast claims.
- Verification evidence needed: A window where the rule overrides the classifier and a stale-at-cutoff window with later readings; compare deployed decisions and evaluator decisions.
- Implementation planning note: Do not treat `array_drop_hpa` as temporal fall or retain `mean_deviation` as a meaningful physical feature.

##### Finding SQUALL-03: Arrival estimates discard the front's fitted time origin

- Severity: High
- Type: geometry mismatch
- Evidence: `backend/app/ai/squall.py:293-317,343-353,575-599,619-633`.
- Problem: Earliest onset and spatial centroid do not define the same origin; fitted intercept is discarded, and absent propagation can become zero-minute arrivals.
- Recommendation: Preserve a spatially consistent fitted time origin; suppress unsupported arrival/polygon claims and describe supported projections as conditional pressure-front estimates.
- Target effect: same target
- Expected benefit: Removes systematic timing displacement and fabricated immediate arrival.
- Dependencies: Existing fitted data; field timing observations for validation.
- Verification evidence needed: A non-collinear array with known planar arrival times reproduces each known onset using the retained intercept, and missing propagation yields no ETA.
- Implementation planning note: Distinguish already-passed buoys, downstream buoys, and the intended vessel warning location before interpreting lead time.

### Trip anomaly and overdue detection

#### Claimed output

The intended claim is detecting a boat that failed to return before a family reports it missing (`docs/Aqone_PRD (2).md:153` and following trip-anomaly section).
The actual output is a weighted deviation score and expected next **buoy contact** window for the latest contact-bearing trip, with `normal/watch/overdue/alert` and a responder-review case (`trip_profile.py:308-337,453-539`; `anomaly_service.py:124-208`).
It is not a distress probability, proof of non-return, or prediction of mechanical failure.
The horizon is time since the modeled next contact; a trip is considered eligible only while its final contact is within 12 hours of evaluation time (`anomaly_service.py:105-120`).
The spatial object is a vessel's contact sequence, which is an intermittent communication record rather than a continuous vessel track.

Lost contact is plausibly a consequence of distress, but also normal fishing, return to port, changed routes, radio outage, or coverage gaps.
The physical ambiguity is not resolved by a stronger anomaly score.
Synthetic latency evidence shows response to deliberately truncated contact sequences; independent predictive usefulness for distress and causal identification are not established.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `vessel_id`, `trip_id`, `buoy_id`, `observed_at`, `source`, `is_synthetic` | Profile/training input; runtime input | `api/contacts.py:ContactEventIn,ingest_contact`; `anomaly_service.py:55-67` | Gateway-declared live; synthetic fixtures; mixture only when demo evaluation enabled | Received contacts yes; receipt/measurement distinction and future cutoff not enforced by profile loader | Contact event at a named buoy for a named vessel/trip | Irregular contacts; live sampling/check-in cadence not stated; synthetic passage times | Keep but transform | Correct identity/time substrate for contact-gap estimation; trip ID alone does not establish that a trip completed normally |
| `latitude`, `longitude` → `ContactPoint.latitude`, `longitude` | Profile/runtime input | `trip_profile.py:202-220`; `api/contacts.py:ContactEventIn`; `generator.py:783-784,839-840` | Supplied coordinates in live ingest; synthetic coordinates equal buoy position | If supplied; contract permits null, while profile conversion expects numbers | Vessel fix versus buoy-proxy identity is not carried into profile; accuracy not stated | At contact timestamp; location age not carried | Keep but transform | Useful position only with fix provenance/age; contact radius is not an exact vessel coordinate |
| `typical_sequence`, `interval_stats` including `leg_index`, `mean`, `std`, `p10`, `p90` | Derived profile features | `trip_profile.py:194-199,272-282,299-337` | Derived from all loaded trips | Includes current trip; retrospective evaluator also includes future trips | Most common compressed buoy sequence; intervals from raw adjacent contacts | Irregular per-leg durations; rebuilt each evaluation | Keep but transform | Habitual contact patterns are relevant, but route-leg indexing must match the underlying intervals |
| `typical_trip_duration_minutes`, `typical_max_distance_km` with `mean/std/p10/p90` | Derived profile features | `trip_profile.py:262-271,293-294` | Derived | Same history caveat | First-to-last contact span; radial distance from a fixed point | Per recorded trip, not necessarily departure-to-return duration | Keep but transform | Neither first/last contact nor a fixed inland origin is a direct return/shore-distance measure |
| Fleet profile for `<3` trips, `low_confidence`, 0.9 score multiplier | Fallback input; static policy | `trip_profile.py:223-237,525-526` | Derived mixture of fleet routes and human policy | Yes | Different vessels and routes pooled | All loaded history; threshold 3 trips | Replace | A fleet's modal route need not be traversable or habitual for this vessel; a confidence flag does not repair mismatched expectations |
| `as_of`, `last_contact_at`, `expected_at`, `window_start`, `window_end`, `overdue_minutes`, `overdue_scale`, `overdue_factor` | Runtime input and derived feature | `trip_profile.py:308-337,479-481`; `anomaly_service.py:124-148` | Server clock plus inferred profile timing | Yes, subject to clock and available-history constraints | Vessel contact process | Current evaluation; 15 min padding; 0.75 sigma; minimum scale 10 min | Keep but transform | Appropriate for a conditional contact deadline, not a learned distress likelihood |
| `route`, `sequence_factor`; `current_distance`, `typical_distance`, `distance_factor` | Derived runtime features | `trip_profile.py:438-450,477-492` | Derived from contacts and profile | Yes | Route prefix and maximum radial distance over observed contacts | Accumulates over trip | Keep but transform | An incomplete normal prefix is penalized against a full route; distance is not current distance offshore |
| `CENTER_LAT=11.6892`, `CENTER_LON=122.3667` | Static parameter | `trip_profile.py:28-29,483` | Hard-coded reference point | Yes | Single point, not shoreline; differs from `geo.py` municipal center | Static | Replace | Can be retained only as explicitly named distance from a reference point; unsuitable for “offshore distance” |
| `wind_speed_mps`, `weather_code` → `weather_factor`; synthetic `wind_direction_deg` | Runtime fallback and derived feature | `trip_profile.py:411-435,493-496`; `anomaly_service.py:148` | Deterministic synthetic weather by location/time | Computable, not an observed environmental fact | Last contact location, not current unknown vessel location | At last contact time; synthetic daily/seasonal cycles | Drop | Default live scoring injects no real provider; synthetic weather changes a live case's score without representing actual weather; direction does not enter severity |
| `weights={overdue:.85,sequence:.10,distance:.03,weather:.02}`, thresholds `.35/.55/.65`, `OPEN_TRIP_FRESHNESS_WINDOW=12h` | Static parameters | `trip_profile.py:33-39,351-359`; `anomaly_service.py:38` | Human policy, with freshness rationale drawn from synthetic trip durations | Yes | All vessels | Per score; eligibility expires at 12 h | Keep but transform | Policy priorities, not calibration; contact age is not evidence of completion |
| Synthetic incident index `(vessel_id,last_contact_at)`, `abnormal_reason`, normal/incident trip membership | Evaluation target | `trip_profile_eval.py:75-110`; `generator.py:470-477,749-812` | Synthetic incidents generated by route truncation, including `loss_of_signal` | Retrospective label only | Vessel/trip | 5 min sweep over 12 h after final contact | Replace | Contact loss is baked into the target; distress and benign loss of signal are not independently resolved |

`typical_departure_hour` and `departure_hour_std` are computed and returned in the profile (`trip_profile.py:256-260,289-290`) but do not drive the score or next-contact time.
They are descriptive first-contact-time statistics, not a demonstrated departure predictor.
Their input-fit verdict is **Keep but transform** if displayed as first-contact summaries; they do not justify adding further departure features to this scorer.
The unused `get_weather_snapshot` requests hourly Open-Meteo data with a 20-minute application cache, but also falls back to synthetic weather (`trip_profile.py:365-408`).
It is **available from an existing source but not currently used**, and is not automatically a suitable fix without location, time, and source handling.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Explicit return/closed-trip evidence and outstanding-trip state (Add) | Necessary for “did not return” | Separate completed trips from vessels still at sea | Not present in this scoring contract; requires voluntary trip/check-in or responder evidence | Changes contact-gap proxy to non-return target | Age of last contact cannot establish return |
| Communication opportunity/coverage and buoy uptime at the expected contact (Add) | Necessary for interpreting silence | Conditional missed contact despite an expected opportunity | Buoy identity/health paths exist; measured coverage and route-specific opportunity require collection | Same contact-gap target; prevents distress overinterpretation | A registered buoy is not proof that a boat should have been heard |
| Voluntary check-in interval or route/mechanical expected contact interval (Add) | Necessary for a cold-start deadline | A meaningful deadline before vessel history exists | Requires human entry or verified historical intervals | Same narrower missed-contact target | Better than borrowing another vessel's modal route |
| Real completed normal-trip history and confirmed distress/non-distress outcomes (Add) | Necessary for distress predictive usefulness | False-alarm and missed-event estimates on real trips | New collection and labeling; live ingest path alone is insufficient | Same intended distress target | Include return, outage and route-change non-events, not only successful contact moments |
| Weather at plausible vessel location/time with uncertainty (Add later) | Helpful for distress interpretation | Environmental context near the unknown vessel | Existing unused provider, but neither current vessel location nor local validation is established | Same intended distress target | Last-contact weather is historical context; does not describe current exposure |
| Vessel type/size and route-specific operating pattern (Add later) | Helpful | Stratified expectations if fleet pooling is retained | Not read by scorer; adequate real attributes/history not evidenced | Same target | Type/route may explain normal timing; must show incremental predictive value |
| Persons aboard and fuel state (Add later) | Helpful for response consequence or mechanical-risk target; not necessary for contact-gap detection | Severity prioritization or explicitly different failure assessment | Requires verified human input; not consumed here | Different target if used as severity/fuel-failure prediction | Do not add rescue priority variables merely to reproduce a silence label |

#### Scale, geometry, leakage, and circularity findings

- Live profiles are built from all loaded contact rows, including the latest candidate trip, without requiring completion or `observed_at <= as_of` (`anomaly_service.py:55-67,134-148`).
  This lets the candidate influence its own baseline; it is circular normalization, not necessarily future leakage in normal wall-clock use.
  The evaluator builds profiles from the complete dataset before replaying historical trips (`trip_profile_eval.py:75`), which additionally permits future-trip information unavailable at replay time.
- Route identity is compressed, but duration samples are indexed through **uncompressed** contacts (`trip_profile.py:272-278`).
  With repeated contacts at one buoy, a dwell/heartbeat interval can occupy the index used for a transit leg.
  Both histories are relevant, but they represent different physical intervals.
- A completed typical route still receives an expected time with `next_buoy=None` and a reused interval (`trip_profile.py:321-337`).
  It can become overdue after return; conversely a genuinely missing vessel ages out of active-score eligibility at 12 hours.
  Persistent review cases are not automatically erased, so this is specifically an eligibility/score interpretation issue, not a claim that all responder evidence disappears.
- A correct unfinished prefix still incurs sequence deviation because the denominator is the full route length (`trip_profile.py:438-450`).
  Route progress is not itself abnormality.
- Default weather is synthetic, and the “current offshore distance” explanation uses maximum distance from a hard-coded reference over the trip, not shortest distance to shore (`trip_profile.py:483,514-520`).
- The fixed 12-hour rule and approximately normal per-leg timing assumptions are not grounded in actual route/season/communication distributions here.
  The current evaluator's normal-trip sweep is better than testing only contact instants, but still cannot identify safe return without a return label.
  The committed false-alarm metric remains null; this audit does not replace it with an inferred number.

#### Highest-value correctness change

Condition overdue status on an explicit outstanding contact/return expectation and distinguish missing communication opportunity.
This narrows the immediate claim to missed expected contact; a real non-return target requires return-state data.

#### Input to drop or replace

Drop synthetic `weather_factor` from live interpretation.
It is not a degraded measurement of real weather, and the existing `source` field on the snapshot does not reach the factor explanation.

#### Minimum defensible input set

- Identified, timestamped received contacts: **already present but unsuitable or incomplete**, because location provenance, nullable coordinates and cutoff semantics remain unresolved.
- Completed pre-decision normal history with matching route-leg intervals: **already present but unsuitable or incomplete**; improves the same contact-gap target.
- Explicit next contact/check-in expectation and trip closure: **requires new collection**; makes non-return distinguishable from normal completion.
- Expected communication opportunity and receiver availability: **requires new collection**, partly supported by existing buoy metadata; improves interpretation of the same target.
- Independent distress/non-distress outcomes: **requires new collection** for predictive usefulness, not a runtime feature.
- “Missed expected contact for review” instead of inferred distress: **requires a narrower or different target** while outcome evidence is absent.

#### Beyond the prior audit

Adds current-trip self-inclusion, future-history replay leakage, compressed-route/raw-interval mismatch, fixed-reference distance semantics, and the inability of the 12-hour eligibility rule to distinguish return from continuing disappearance.
The prior audit correctly identified synthetic weather; this audit specifies the actual caller and why even last-contact real weather would not describe the current vessel's exposure.

#### Honest output after fixes

“This vessel missed a stated or historically supported contact deadline under the recorded communication conditions; verify its status.”
This is a review cue, not a probability of distress or proof the vessel failed to return.

#### Plan-ready findings

##### Finding TRIP-01: Contact age is being used as trip state

- Severity: High
- Type: missing input
- Evidence: `backend/app/ai/anomaly_service.py:105-120,139-148`; `backend/app/ai/trip_profile.py:321-337`.
- Problem: A recent completed trip can be scored overdue, while an unresolved missing trip eventually falls outside active scoring solely due to age.
- Recommendation: Establish explicit outstanding-trip/contact expectation and closure evidence; treat absent coverage as missing observation opportunity and narrow output to missed expected contact.
- Target effect: narrower target
- Expected benefit: Distinguishes the operational states that silence alone cannot identify.
- Dependencies: Existing buoy metadata plus new trip/check-in and coverage collection.
- Verification evidence needed: Matched contact sequences for a returned vessel, a receiver outage, and an unresolved missing vessel across the 12-hour boundary.
- Implementation planning note: Identify available return/check-in evidence before changing thresholds; preserve the distinction between persisted cases and active score eligibility.

##### Finding TRIP-02: Baseline history and runtime leg semantics do not match

- Severity: High
- Type: leakage
- Evidence: `backend/app/ai/anomaly_service.py:134-148`; `backend/app/ai/trip_profile.py:272-278,315-337,438-450`; `backend/app/ai/trip_profile_eval.py:75-93`.
- Problem: Candidate and future replay trips enter the reference profile; compressed routes are paired with raw contact intervals; normal route progress contributes deviation.
- Recommendation: Use only completed, prior, normal trips at each decision cutoff and define consistent contact/transit-leg quantities for both baseline and candidate.
- Target effect: same target
- Expected benefit: Makes expected contact timing and anomaly comparison refer to the same physical process without future knowledge.
- Dependencies: Existing contact source plus completion/normal labels.
- Verification evidence needed: A history with duplicate same-buoy contacts, an incomplete matching prefix, and a future trip must leave the earlier decision's baseline well defined and unchanged by later data.
- Implementation planning note: Decide whether same-buoy residence time or inter-buoy travel time is the intended interval before rebuilding profiles.

##### Finding TRIP-03: Environmental explanations use invented weather and mislabeled distance

- Severity: Medium
- Type: wrong input
- Evidence: `backend/app/ai/trip_profile.py:28-29,411-435,483-520`; `backend/app/ai/anomaly_service.py:148`.
- Problem: Live cases receive synthetic weather and “offshore” distance from a fixed point; neither is the stated environmental measurement.
- Recommendation: Remove synthetic weather from live scoring and describe distance as distance from the named reference, or replace it with the actually intended shore/route quantity.
- Target effect: narrower target
- Expected benefit: Keeps factor explanations aligned with real evidence without requiring a new weather model.
- Dependencies: Existing sources; shoreline source only if true shore distance is retained.
- Verification evidence needed: A live-sourced case must not claim measured weather when no provider is used; two positions equally far from the reference but differently located relative to shore expose the distance distinction.
- Implementation planning note: Reassess factor meaning before connecting the unused weather provider; this is not a request to add vessel-risk features indiscriminately.

### Drift prediction

#### Claimed output

The intended quantity is the location distribution of a person in water, swamped banca, or intact drifting hull following a last-known position, to support a responder's search area (`docs/Aqone_PRD (2).md:171-189`).
The actual output is the **terminal distribution of simulated particles**, conditional on assumed currents, wind, object class and error parameters, plus hull contours nominally labeled 50/75/95% (`ai/drift.py:368-489`).
The default horizon is 24 hours **from `observed_at`**, with real-case requests accepting up to 72 hours (`api/drift.py:265-277`).
It is not necessarily a distribution “now,” and does not model survival or probability of rescue.
There is no training target in the classifier sense; uncertainty settings were adjusted against synthetic incidents (`drift.py:391-401`).

Advection by water velocity and object-specific wind-induced leeway is physically well founded.
That supports a conditional simulation, not the calibration of AqOne's chosen coefficients, local inputs, or contour probabilities.
The distinction matters because operational search planning also considers search performance and scenarios, not merely terminal particle density ([USCG SAROPS overview](https://www.dcms.uscg.mil/Our-Organization/Assistant-Commandant-for-Acquisitions-CG-9/International-Acquisition/SAROPS/)).
Predictive usefulness on independent local drifts and causal identification are not established.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `last_lat`, `last_lon`, `observed_at` from SOS `latitude`, `longitude`, `created_at` | Runtime input | `api/drift.py:280-296`; `api/sos.py:94,153-174`; `migrations/001_init.sql:22-29` | Human/device SOS location; database insertion time | Yes, but wrong time meaning for delayed SOS | Point fix; uncertainty and fix age absent from drift input | Insert time, not necessarily origin/fix time | Replace | Pair coordinates with actual location/datum time; mesh delay otherwise shortens elapsed drift artificially |
| `last_lat`, `last_lon`, `observed_at` from anomaly contact | Runtime input | `api/drift.py:299-325` | Latest non-null stored contact position/time | Yes after arrival; contact location provenance incomplete | Vessel fix or buoy proxy; not specified in drift input | Last contact event | Keep but transform | Last radio contact need not be the time free drift began; active travel may occur afterward |
| `object_class` / `ObjectClass` | Runtime input; human-entered decision | `api/drift.py:265-277`; `ai/drift.py:46-64` | Responder-selected; legacy synthetic reason mapping | Yes as a scenario choice, not necessarily confirmed object state | One target object | Fixed for whole run | Keep but transform | Directly relevant to windage; must reflect uncertainty in whether person, hull, or both are being searched |
| `observed_u_mps`, `observed_v_mps`, `observed_at`, buoy `lat`, `lon` | Runtime external/hardware input | `current_field.py:45-83`; `generator.py:682-712` | Database mixture; synthetic rows explicitly exist; loader selects neither source nor synthetic flag | Loaded at run time; may be after trajectory step time in a hindcast | Fixed buoy sensor point; measurement depth/accuracy not stated | Synthetic 15 min; real cadence not stated; all observations loaded once per run | Keep but transform | Relevant water velocity only if real, depth-representative, time-supported and water-connected to particles |
| `IDW_POWER=2`, `MAX_RADIUS_M=111000`, `MAX_AGE_SECONDS=3600`; interpolated `u_out`,`v_out` | Derived runtime field and static parameters | `current_field.py:28-30,145-210` | IDW in distance and linear temporal interpolation | Future observations relative to a forecast cutoff are not available; historical observations after a drift start may legitimately be available at rerun time | Up to 111 km, regardless of land/islands/channels | Nearest sample within 1 h; holds endpoint inside this interval; no current forecast beyond it | Keep but transform | Policy radius is not physical correlation length; observations are not a 24-72 h forecast |
| `_synthetic_current_vector`: `u`,`v` from tide/daily/weekly/spatial terms | Fallback input | `drift.py:124-147`; `current_field.py:204-207` | Synthetic equation | Computable, not observed or locally calibrated | Smooth field around hard-coded center | Continuous analytic cycles including 12.42 h | Drop | No empirical phase/amplitude fit; not an operational replacement for tidal/channel current |
| `wind_speed_10m`, `wind_direction_10m`, provider `time` → `WindSeries.u_mps`,`v_mps` | Runtime external input; derived feature | `drift.py:192-257` | External Open-Meteo forecast; units requested m/s; direction rotated from meteorological “from” to motion “to” | Available only over returned valid times; endpoint substitution may cover absent history | One request at initial location used for all particles; returned grid resolution not recorded | Hourly values, 3 forecast days; application cache 20 min; provider issue cadence not stated in repo | Keep but transform | Direction conversion is appropriate; attach timezone, valid coverage and actual grid/time provenance |
| `_synthetic_wind_series` | Fallback input | `drift.py:150-181,234-235`; `drift_eval.py:87-98` | Synthetic; production result gate rejects `degraded=True` | Only a generated scenario | Single starting location | Hourly synthetic series | Drop | Keep only for explicit demo/evaluation, not operational wind; live gate already rejects this wind fallback |
| `downwind`,`crosswind` = (.006,.002), (.012,.004), (.020,.007) | Static physical parameters | `drift.py:52-64`; generator `_leeway_spec` | “Literature-inspired” approximations, no exact local object calibration supplied | Yes | Broad object classes | Constant over drift | Keep but transform | Windage is directly relevant; vessel loading, immersion and capsize state can change it; do not call these fitted local coefficients |
| `initial_spread_m=250`, `current_bias_sigma_ms=.06`, `leeway_scale_sigma=.25`, `diffusivity_m2_s=.75`, `cross_sign`, `current_bias_u`,`current_bias_v`,`leeway_scale` | Static physical/error parameters; derived ensemble samples | `drift.py:382-425` | Assumed distributions; current sigma tuned against synthetic incidents | Yes as assumptions | Gaussian start uncertainty; persistent particle errors and left/right split | Bias/leeway held constant; isotropic diffusion each step | Replace | Need datum-specific and field-supported uncertainty; synthetic containment is not an observational calibration |
| `forecast_hours`, `step_minutes=10`, `particle_count=2000`, `grid_resolution_m=500`, RNG seed | Runtime control; static numerical parameters | `drift.py:368-408,457-480` | Human request/numerical policy | Yes | 500 m bins, not 500 m environmental resolution | Terminal horizon; 10 min integration, rounded up to whole steps | Keep but transform | Numerical detail must not imply resolved shoreline/current physics; declare exact terminal valid time |
| `nearby_buoy_count`, `observation_fraction` / `observed_coverage`, `wind_source`, `degraded`, thresholds 2 buoys/.5 coverage | Derived quality inputs; static policy | `current_field.py:86-110,209`; `environment.py:45-47,98-115`; `api/drift.py:192-207` | Computation/policy | Yes, but coverage is last-step fraction and “observed” is not source-verified | Count within 111 km of initial point; fraction of final-step particles | Freshness referenced to simulation times; cache age used as forecast-age proxy | Replace | Does not establish whole-trajectory real environmental support |
| `true_track`, `abnormal_reason`, `(len(track)-1)*.5`, 95% containment, area reduction | Calibration/evaluation target and derived metrics | `generator.py:888-937`; `drift_eval.py:85-111,144-166`; `drift.py:391-401` | Synthetic track with similar wind/current/leeway assumptions | Retrospective target, not operational observation | Terminal point; generated track stops at polygon exit | 30 min generated track; variable horizon on termination | Replace | Evaluator conditions on outcome-derived length and shares assumptions; not independent containment or real search-efficiency evidence |

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Datum/fix time, location uncertainty, and free-drift start or pre-distress motion (Add) | Necessary | A target distribution anchored to the real object's state | SOS `client_ts` exists; actual fix time/accuracy must be traced from device; motion may require responder evidence | Same target; uncertain onset requires conditional scenarios | Receipt time and last contact do not establish release into free drift |
| Shoreline/island/channel geometry, land mask and grounding behavior (Add) | Necessary for local nearshore claim | Water-connected trajectories and possible beaching | `geo.py` polygon exists but is acknowledged approximate and includes open-water limits; suitable geometry requires an external/local source | Same target | Particles cannot drift through Panay; an administrative/demo boundary is not shoreline |
| Bathymetry, tide/current phase and surface-current forecast through horizon (Add) | Necessary where depth/channel/tidal effects materially control flow | Nearshore current evolution rather than unsupported persistence | Static GEBCO samples exist only in hazard layer; no local tidal/current forecast wired; real suitability unverified | Same target | A 1 h freshness gate cannot extend current observations 24-72 h |
| Object-specific leeway and immersion/load state (Add) | Necessary for class-specific quantitative claim | Relevant windage distributions for banca/person/hull | Coefficients present but incomplete; independent measurements or suitable published object data required | Same target | Broad class differences do not establish the actual object's response |
| Independent drifter/recovery observations and bias estimates (Add) | Necessary for calibrated containment | Empirical errors at declared horizons, including shoreline encounters | Requires new collection; recovery labels absent from evaluator | Same target | Separates field prediction from synthetic self-consistency |
| Stokes drift / wave-induced transport (Add later) | Helpful, potentially necessary under material wave transport | Better same-object trajectory under waves | Wave heights exist elsewhere; height alone is insufficient transport vector; no appropriate source connected | Same target | Define what observed/model current already includes to avoid double-counting wave transport |
| Vertical current shear and measurement depth (Add later; depth metadata Add now) | Helpful; necessary if sensor and object's immersion differ materially | Object-representative current | Sensor depth/vertical profiles not stated | Same target | Surface person and partly submerged hull do not necessarily sample the same water layer |
| Freshwater outflow (Add later) | Helpful near affected estuaries | Better local flow during material discharge | No discharge input connected | Same target | Only justified where outflow changes local drift beyond existing measured-current information |
| Distance from shore as a scalar (Add later) | Helpful as domain/uncertainty diagnostic; irrelevant as a substitute for geometry | Identify when open-water approximation ceases to apply | Requires suitable shoreline geometry | Same target | Distance alone cannot prevent crossing an island or distinguish a channel |

#### Scale, geometry, leakage, and circularity findings

1. **Observed-column names do not establish real provenance.** `_load_buoy_observations` includes generated `observed_u_mps/observed_v_mps` rows, while the generator explicitly sets `is_synthetic=True`.
   `environment.py:3-8` and `api/drift.py:184-190` claim a real-case path without synthetic substitution, but the called field factory has no such source separation and uses synthetic fallback for unsupported particles.
   This qualifies the prior audit's claim of a fully protected live path.
2. **Coverage is not the reported whole-run quantity.** `observation_fraction` is overwritten each step (`current_field.py:209`).
   It can report high support at the last step even when earlier motion used invented currents.
   The two-buoy check tests the initial point only; individual particles can be supported by one buoy, across land, or mostly outside the array's informative footprint.
3. **Decision time differs from trajectory time.** Retrospective reconstruction may legitimately use observations acquired after the original datum but before the current run.
   It is leakage if those same observations substantiate a forecast purportedly issued at the original datum.
   The evaluator loads all observations, including the simulated future, without preserving issue-time availability (`drift_eval.py:60-98`).
   For a fresh 24-hour forecast, actual future buoy observations are unavailable; after about one hour the factory falls back and final-step coverage tends to fail.
   This is not solved by polling the historical observations more frequently.
4. **Datum time is wrong for delayed SOS.** `client_ts` exists, but `_sos_case_inputs` pairs SOS location with database `created_at`.
   With a two-hour mesh delay, a location recorded two hours earlier is treated as the start point at receipt.
   `client_ts` alone also needs checking against actual GPS-fix age before substitution is called correct.
5. **Wind time support is not guaranteed by a successful fetch.** The request fetches current forecast days, not an interval tied to an old `start_at`; `_interpolate_series` holds endpoints beyond the returned range.
   Times parsed from provider strings remain naive in `_fetch_wind_series`; `.timestamp()` then depends on host timezone, despite requesting Asia/Manila.
   Cache refresh measures retrieval age, not model issue age or whether the supplied wind is valid at the trajectory time.
6. **Geometry and object physics remain conditional.** A 111 km IDW radius, no barriers, one wind series for every particle, constant error biases, and broad fixed leeway coefficients cannot establish a 500 m-resolved nearshore search distribution.
   The generator beaches tracks at **any** `geo.point_in_water` boundary, including open-water outer limits, while the predictor has no land-mask handling (`generator.py:927-934`; `geo.py:62-85`).
   Do not reuse that polygon as verified coastline.
7. **Evaluation changes the horizon using outcome data.** A terminated generated track shortens the evaluated forecast through `(len(track)-1)*.5`.
   This can avoid testing post-grounding or post-domain-exit behavior at the requested 24-hour horizon.
   Further, the “naive maximum drift speed” baseline uses the model's terminal **centroid displacement**, not an independently specified maximum speed (`drift_eval.py:144-151`; `drift.py:493-500`; `dashboard-sar.js:sarRowsFromResults`).
   Area reduction is consequently not the claimed comparison.
8. **Contour mass is model mass, not field probability.** A convex hull of selected high-density cell centers can bridge low-density gaps and does not itself establish exact physical containment.
   The nominal 95% label is not evidence of 95% recovery-location coverage.

#### Highest-value correctness change

Require real, decision-time-supported current inputs and report support over the entire propagated trajectory.
This corrects the same conditional drift target; when the horizon is unsupported, narrow to a supported reconstruction/short-horizon scenario or return insufficiency.

#### Input to drop or replace

Drop `_synthetic_current_vector` as an operational fallback.
It does not become a tide model merely because it contains a 12.42-hour sine wave.

#### Minimum defensible input set

- Datum position, actual datum time, and uncertainty: **already present but unsuitable or incomplete**; `client_ts` is an existing candidate, not an automatically valid fix timestamp.
- Explicit object/free-drift scenario and relevant leeway distribution: **already present but unsuitable or incomplete**; changes an unconditional location claim into conditional estimation.
- Real, depth-representative currents and wind with spatial/valid-time support through the declared horizon: **already present but unsuitable or incomplete**; additional current forecast/field evidence requires collection or a suitable external source.
- Suitable shoreline/land mask and nearshore current boundary information: **requires new collection**, potentially through an appropriate external dataset; the demo polygon is unsuitable.
- Independent position/time tracks at prespecified horizons: **requires new collection** for containment calibration on the same target.
- “Conditional particle distribution under stated assumptions” rather than calibrated SAR probability: **requires a narrower or different target** until independent evidence supports stronger language.

#### Beyond the prior audit

Corrects the claimed source separation and interpretation of observed-current coverage.
Adds receipt-time datum error, forecast-versus-hindcast availability, wind timezone/validity gaps, absent shoreline handling, outcome-dependent evaluation horizons, and the incorrect area-reduction baseline quantity.
The shared synthetic physics limitation remains valid, but the generator and predictor are not identical: their geography, grounding, and timing differ.

#### Honest output after fixes

“Conditional drift distribution for the stated object and datum, valid at the stated time, using source-identified environmental data and explicit uncertainty assumptions; not an empirically calibrated containment probability.”
If environmental or boundary support is absent, the honest output is insufficiency rather than a substitute field.

#### Plan-ready findings

##### Finding DRIFT-01: Real-case current support includes synthetic and unsupported motion

- Severity: Critical
- Type: provenance issue
- Evidence: `backend/app/ai/current_field.py:45-83,174-209`; `backend/app/ai/environment.py:3-8,98-115`; `backend/app/api/drift.py:192-207`; `backend/app/simulation/generator.py:709-711`.
- Problem: Unfiltered synthetic rows count as observations; unsupported particles use synthetic current; last-step fraction is treated as run-wide coverage.
- Recommendation: Define real source and decision-time eligibility explicitly, prohibit invented current in a real-supported result, and assess environmental support across the full trajectory/horizon.
- Target effect: same target
- Expected benefit: Makes “observed-current-supported drift” a truthful data claim.
- Dependencies: Existing source flags/time data; suitable current forecast or shorter supported horizon.
- Verification evidence needed: Mixed live/synthetic rows, a mid-run data gap followed by fresh final observations, and a genuine forecast with no future observations must yield accurate provenance/support or insufficiency.
- Implementation planning note: Distinguish run issue time, datum time and each particle step time before deciding which observations may legitimately enter.

##### Finding DRIFT-02: SOS receipt time and assumed drift onset do not define the target datum

- Severity: High
- Type: wrong input
- Evidence: `backend/app/api/drift.py:280-325`; `backend/app/api/sos.py:94,153-174`; `backend/migrations/001_init.sql:29`; `backend/app/ai/drift.py:414-415`.
- Problem: Coordinates are paired with database insertion time; all last contacts are treated as immediate free-drift starts with the same 250 m initial spread.
- Recommendation: Use verified coordinate/fix time and source-specific uncertainty; represent uncertain free-drift onset or pre-distress motion as an explicit conditional scenario.
- Target effect: same target
- Expected benefit: Removes transport-delay displacement and falsely precise initialization.
- Dependencies: Existing `client_ts` plus device fix provenance and responder evidence where needed.
- Verification evidence needed: One delayed SOS with distinct fix, origin and receipt times; one overdue vessel that traveled after last contact.
- Implementation planning note: Confirm which timestamp actually belongs to the stored coordinates; do not substitute origin time blindly for fix time.

##### Finding DRIFT-03: Environmental time and nearshore geometry do not support the requested horizon

- Severity: High
- Type: scale mismatch
- Evidence: `backend/app/ai/drift.py:192-257,428-455`; `backend/app/ai/current_field.py:28-30,155-192`; `backend/app/api/drift.py:277`; `backend/app/geo.py:62-85`.
- Problem: Hour-old point currents do not forecast a day ahead; wind can be endpoint-held or timezone-shifted; spatial interpolation ignores land and channel boundaries.
- Recommendation: Match currents/wind to explicit issue and valid times, use water-connected spatial support and suitable shoreline geometry, and limit the claim/horizon to supported physics.
- Target effect: narrower target
- Expected benefit: Avoids presenting grid detail or fresh retrieval as evidence of resolved nearshore drift.
- Dependencies: Existing timestamps; external/local shoreline and horizon-covering environmental source.
- Verification evidence needed: Inputs spanning a tidal reversal, an island/channel, and a datum outside forecast valid times; document supported domain and horizon.
- Implementation planning note: Determine sensor depth/current definition, wind timezone and forecast coverage before considering optional wave/shear/outflow terms.

##### Finding DRIFT-04: Synthetic containment and the baseline do not establish the claimed search benefit

- Severity: High
- Type: circularity
- Evidence: `backend/app/ai/drift.py:391-401,493-500`; `backend/app/ai/drift_eval.py:85-111,144-151`; `backend/app/simulation/generator.py:888-937`; `web/js/dashboard/dashboard-sar.js:sarRowsFromResults`.
- Problem: Uncertainty is tuned on related generated physics; outcome-truncated horizons and model-centroid baseline undermine the stated 24-hour containment/maximum-speed comparison.
- Recommendation: Evaluate at prespecified horizons against independent object tracks and an independently defined baseline; retain synthetic results only as scenario self-consistency evidence.
- Target effect: same target
- Expected benefit: Establishes what evidence would actually support empirical containment and area savings.
- Dependencies: New drifter/recovery collection and suitable object/leeway evidence.
- Verification evidence needed: At least one independently observed track through the intended horizon, including a grounding/domain-exit case, with baseline definition fixed before inspecting outcome.
- Implementation planning note: Define whether beaching is an outcome to retain or censor; do not equate demo-polygon exit with shoreline grounding.

### Bayesian search re-tasking

#### Claimed output

The mathematical output is a normalized location distribution conditional on a reported unsuccessful search and an assumed probability of detection.
For cells inside a responder rectangle, the code multiplies prior mass by `1-detection_probability`, then normalizes (`search.py:49-81`).
The stronger operational output is `next_area`, the single cell with greatest remaining normalized mass, labeled a recommendation for responder review (`search.py:101-127`).
It is not an optimized search plan, expected rescue probability, or asset assignment.
Its time horizon is inherited from the original drift terminal grid; no search-time propagation occurs in `update_posterior`.

Negative search evidence is relevant to target location if the target could have been detected under the actual search conditions at that time.
The algebra is defensible under those assumptions; no field evidence demonstrates the preset likelihoods or calibrated initial prior.
A mathematically consistent Bayesian update neither validates its inputs nor establishes a causal effect of searching a sector on rescue success.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `posterior_grid` / `prior_grid`, `values`, `origin.lat/lon`, `x_edges_m`, `y_edges_m` | Runtime input | `api/drift.py:737-757`; `search.py:20-29` | Derived drift simulation, potentially already updated | Yes as stored; current validity not established | Usually 500 m cells of terminal drift field | Fixed terminal time inherited from drift; no grid-time variable in update | Keep but transform | Correct mathematical prior only for matching event/time and defensible initial uncertainty |
| `south`, `west`, `north`, `east` → `x_min_m`, `x_max_m`, `y_min_m`, `y_max_m` | Runtime human-entered input; derived geometry | `api/drift.py:54-78,636-646,785-800` | Responder rectangle | Yes as report, not verified track coverage | Rectangle; cells selected by center | Report submission; actual search start/end not requested | Keep but transform | Bounding rectangle can include unsearched water, shore, or gaps between tracks |
| `method` → `detection_probability` (`poor=.3`, `moderate=.6`, `good=.9`) | Runtime human choice; static likelihood | `api/drift.py:42-50,795` | Approved heuristic presets, not local measurements | Yes as an assumption | Uniform within rectangle, all object types | One fixed value per report | Replace | Search effectiveness depends on object, method, visibility, track spacing and time; preset approval is not calibration |
| Negative result / target not found | Runtime human-entered evidence, implicit in reporting action | `search.py:1-8`; `api/drift.py:711-721` | Responder assertion | Yes after search | Reported sector | Search time itself not supplied | Keep | This is the evidence being conditioned on; it needs spatial/temporal meaning, not a learned label |
| `run_number`, `idempotency_key`, `searched_at`, `run_id` | Runtime evidence identity/time metadata | `api/drift.py:63-70,737-800,808-814` | Stored/report identifiers; database report time | Yes | Case/run/report | `searched_at` stored, not used in Bayesian dynamics | Keep but transform | Prevents reapplying the same submission; does not identify correlated repeat searches or actual sweep time |
| `remaining_mass`, `np.argmax(values)` | Derived feature/decision | `search.py:112-127` | Deterministic rank after normalization | Yes | One grid cell | Same fixed grid time | Keep but transform | Ranks location mass, not expected detection success or travel feasibility |

There are no supervised training inputs or learned labels.
Synthetic sector updates and mathematical assertions can check arithmetic but are not measured detection-performance evidence.
`reported_by` and `notes` retain human context; neither supplies a likelihood or changes the update.
Their input-fit verdict is **Keep** as evidence metadata, with no claimed predictive role.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Search start/end time and time-aligned target distribution (Add) | Necessary for moving targets | Negative evidence about where the target was while searching | Report timestamp exists; actual sweep times and propagated prior are absent | Same posterior target | Searching a location at hour 2 does not directly exclude that location at hour 24 |
| Actual responder tracks and track spacing (Add) | Necessary for area-wide search likelihood; optional only for explicit hypothetical rectangle | Which water was effectively searched | Not in sector request; requires responder/hardware collection | Same target | Drawing a rectangle is not evidence of uniform coverage |
| Object/method/sensor/visibility-conditioned local detection probability (Add) | Necessary for calibrated posterior | Defensible likelihood of no detection given target present | Presets only; requires field measurements or suitable performance source | Same target | Measurement performance controls how much mass can be removed |
| Initial posterior calibration and drift bias correction (Add) | Necessary for empirical probability claim | Calibrated location probability after update | Dependent on DRIFT findings and new independent tracks | Same target | Bayes cannot create probability calibration from a biased or incomplete prior |
| Search-to-search dependence / repeated-track identity (Add) | Necessary when repeat reports share the same missed-target mechanism | Defensible combined evidence from repeats | Idempotency key exists but is not statistical dependence data | Same target | Independent keys do not make repeated searches conditionally independent |
| Asset position, reachability, time budget, expected detection efficiency (Add later) | Helpful for review; necessary for an optimal search recommendation | Best expected-success search area | Not used by current recommender | Different target | Highest location mass alone is not maximum expected search success |

#### Scale, geometry, leakage, and circularity findings

- A moving-target posterior is updated as a stationary grid: negative search evidence is applied to terminal cells without time alignment.
  Rerunning drift also constructs a new prior/posterior from the datum rather than time-transporting accumulated search evidence (`api/drift.py:179-210`); do not assume a new run retains the old likelihood information.
- Rectangle-center masking is discontinuous for narrow tracks and small rectangles relative to 500 m bins.
  An overlapping rectangle may contain no cell centers; a large one may assign high detection probability to water never traversed.
- Uniform detection presets do not reflect target visibility, search effort, sensor performance or local conditions.
  Two separate “good” reports can multiply a cell by `.1 * .1`, even if they repeat the same ineffective viewing conditions.
  Idempotency protects a repeated submission, not this dependence assumption.
- The highest remaining-mass cell is an appropriate descriptive ranking under the assumed prior/likelihoods.
  Calling it where responders “should” search requires detection efficiency and feasibility, and should not be inferred from Bayes' theorem alone.
- No evidence of independent empirical prior or likelihood calibration was found.
  This is a validation limitation distinct from the mathematical correctness of multiplying by a specified likelihood.

#### Highest-value correctness change

Attach the actual search interval and apply its evidence to a distribution valid during that search.
This improves the same posterior target; until time and likelihood support exist, narrow the output to a hypothetical static-grid update.

#### Input to drop or replace

Replace unqualified `good=.9` and other fixed method likelihoods with explicitly conditional, evidence-supported values or clearly labeled assumptions.
Do not replace them with zero detection: unknown detection probability is not evidence that nothing was searched.

#### Minimum defensible input set

- Source-identified prior with a physical datum and valid time: **already present but unsuitable or incomplete**.
- Negative result, report identity and rectangle: **already present but unsuitable or incomplete** for actual search footprint/time.
- Search interval, effective footprint, object/method-conditioned likelihood: **requires new collection** for the same target.
- Prior calibration/bias evidence: **requires new collection**, dependent on drift validation.
- “Largest remaining cell under stated static assumptions”: **requires a narrower or different target** if time propagation and search performance remain absent.
- Asset cost/reachability inputs: **requires new collection** only for a **different target**, optimal operational tasking; not required for honest descriptive ranking.

#### Beyond the prior audit

Adds moving-target versus stationary-grid mismatch, rectangle versus effective sweep geometry, and conditional dependence of repeat searches.
Qualifies the prior audit's correct preset-calibration concern by distinguishing posterior algebra from the recommendation's expected-success claim.

#### Honest output after fixes

“Given this time-aligned prior and the reported search's stated detection assumptions, these cells retain the most modeled location probability for responder review.”
This does not claim optimal tasking or measured rescue probability.

#### Plan-ready findings

##### Finding SEARCH-01: Negative search evidence is applied to the wrong time state

- Severity: High
- Type: target mismatch
- Evidence: `backend/app/ai/search.py:49-81`; `backend/app/api/drift.py:54-70,795-814,179-210`.
- Problem: The update has no search interval or moving-target state transition; a terminal drift grid is treated as stationary across reports.
- Recommendation: Define search time and the corresponding target distribution; retain only a static conditional-update claim until temporal alignment is supported.
- Target effect: narrower target
- Expected benefit: Avoids excluding future target locations because those locations were empty at another time.
- Dependencies: Existing drift time data plus responder search-time collection.
- Verification evidence needed: A target moving into a sector after an unsuccessful earlier search must not be excluded merely by that earlier rectangle report.
- Implementation planning note: Decide how negative evidence relates to a rerun's valid time and datum before treating reruns as refreshed posteriors.

##### Finding SEARCH-02: Search rectangle and method preset are not measured detection likelihoods

- Severity: High
- Type: missing input
- Evidence: `backend/app/api/drift.py:42-50,54-70`; `backend/app/ai/search.py:68-79,101-127`.
- Problem: Uniform likelihood and repeated-report independence are unsupported; highest mass is presented as a next-area recommendation without search performance.
- Recommendation: Record effective footprint/time and object/method-conditioned detection evidence; describe next area as highest modeled mass unless expected-success inputs are available.
- Target effect: narrower target
- Expected benefit: Prevents arbitrary probability removal and overinterpretation of a cell ranking.
- Dependencies: Responder tracks, sensor/method performance evidence and drift calibration.
- Verification evidence needed: Sparse sweep tracks inside a large rectangle and overlapping repeat searches; compare assumed coverage/detection with actually observed detection opportunities.
- Implementation planning note: Distinguish unique submissions from independent evidence; do not add asset optimization inputs unless that stronger target is requested.

### Marine hazard or danger zone

#### Claimed output

The documented model is an experimental environmental-proxy classifier, explicitly not verified casualty risk (`web/ml/README.md:5`).
The dashboard presents per-sector `Lower risk`, `Watch`, or `Danger`, a percentage-like score, reasons, and strongest percentage (`dangerZonePredictor.js:132-151,182-218,255`; `dashboard-markers.js:371-372`).
Actual runtime “Danger” is determined by **simultaneous** wave and wind thresholds; model probability without that conjunction is capped at Watch.
The trained target instead labels **any** qualifying wind, gust, wave, thunderstorm, or cyclone-proximity condition as positive.
The two quantities must be separated before evaluating input fit.

The spatial unit is a requested sector point drawn as a 600-800 m radius area, not a measured nearshore hazard polygon.
The runtime request uses provider `current` values with `forecast_hours=1`; this is a present environmental classification, not a demonstrated future incident forecast.
Wind and waves have direct physical relevance to vessel loading, while casualty outcomes also depend on vessel and operating state.
The stored model shows discrimination of its proxy labels on time-separated historical data; it does not establish independent local safety prediction or causal identification.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `wind_speed_10m`, `wind_gusts_10m` | Training input; runtime external input | `train_danger_zone_model.py:114-124,218-235`; `dangerZonePredictor.js:96-104,171-180` | Historical modeled weather; external current model forecast | Live values available when fetched; historical reanalysis is retrospective, not an archived issue-time forecast | Requested sea cells; actual selected grid and native resolution not retained | Training every third hourly row; runtime `current`; provider issue cadence not stated in repo | Keep | Direct environmental hazard variables; reproduction of their own threshold labels is not casualty skill |
| `precipitation`, `weather_code` | Training/runtime input | Same functions, `train_danger_zone_model.py:221-222`; `dangerZonePredictor.js:175,188-189` | External weather products | Same historical/live distinction | Weather grid cell, not vessel conditions | Training 3-hour sampling of hourly values; current runtime interval differs | Keep but transform | Rain is context, code is categorical weather interpretation; do not treat every numerical code increment as increasing physical danger |
| `wave_height`, `wave_period` | Training/runtime external input | `train_danger_zone_model.py:127-137,223-224`; `dangerZonePredictor.js:176-177` | ERA5-Ocean training; live provider-selected marine model | Available at valid times; no observed local truth established | Marine grid; selected grid and native resolution not recorded in artifact/runtime result | Hourly training source sampled every 3 h; current runtime values | Keep but transform | Significant wave height/period are relevant, but training and runtime models and sampling supports differ |
| `depth_m` | Training/runtime static parameter | `train_danger_zone_model.py:91-111`; `model-card.json:sectors`; `dangerZonePredictor.js:37-42,178` | GEBCO 2020 lookup; five added cells have hard-coded GEBCO-attributed values with no query provenance in this file | Yes | Single point per sector, not navigable channel bathymetry | Static dataset; field update cadence not applicable | Drop | Artifact reports zero importance and no depth split; remove from hazard explanation unless its actual physical role is defined and validated |
| `month_sin`, `month_cos` from `observed_at.month` / browser UTC month | Derived training/runtime features | `train_danger_zone_model.py:240-245`; `dangerZonePredictor.js:165-180` | Calendar-derived | Yes; runtime uses wall clock rather than provider valid time | Same across sectors | Monthly cycle | Keep but transform | Plausible seasonal context, not a physical storm measurement; use valid time and verify added predictive value independently |
| `ISO_TIME`, `LAT`, `LON`, `WMO_WIND`, `USA_WIND`, `TOKYO_WIND`, `JTWC_WIND` → `wind_kt`, `cyclone` | External label-construction inputs | `train_danger_zone_model.py:149-176,187-193` | NOAA best-track archive; maximum available agency wind value | Retrospective labels; best-track values and +3 h records not available as such at historical forecast issue time | Storm center within 350 km of sector; no wind-radius/asymmetry/local exposure representation | Best-track cadence not stated in repository; ±3 h window | Keep but transform | Appropriate only as explicitly retrospective cyclone-proximity context; mixed agency wind conventions and local exposure are not resolved |
| `observed_hazard`; `labels=int(cyclone or observed_hazard)` | Training/evaluation target | `train_danger_zone_model.py:229-248`; model-card `label_definition` | Policy thresholds on predictor values plus best-track proximity | Retrospective target | Sector-time proxy | Same sampled time or ±3 h cyclone | Replace | Define a single output target; these are not local observed incidents and differ from runtime “Danger” |
| Class-balancing `sample_weight`; fitted probability and historical metrics | Training weighting; evaluation output | `train_danger_zone_model.py:316-333`; `model-card.json:metadata` | Derived from training class balance | Training only | Three artifact training sectors | Before 2025 vs 2025 test split | Keep but transform | Useful classifier fitting; balanced weighting and proxy test Brier do not establish deployment-prevalence calibrated hazard probability |
| `buoy.status`, `buoy.signal` → `degradedCount`, `buoyAdjustment` | Runtime input; derived rule adjustment | `dangerZonePredictor.js:123-129,163-184` | API health/communication data; count over supplied fleet | If API returns it; not environmental measurement | Same global count added to every sector, no distance matching | At fetch; measurement age/units of signal not established here | Drop | Radio health is not direct evidence of waves/weather, and no target validation supports this addition |
| `measuredDanger`, `measuredWatch`, score cutoffs 40/65, adjustment cap .08 | Static policy and derived decision | `dangerZonePredictor.js:183-199` | Human rule | Yes | Sector point | Per current-data request | Keep but transform | Explicit environmental threshold tiers can be honest; they are neither measured casualty risk nor the classifier's label probability |
| `sector.lat/lng`, `radius`, `model.sectors`, `NEW_WASHINGTON_COVERAGE` | Runtime/static geometry | `dangerZonePredictor.js:37-51,205,222-224`; artifact `sectors` | Three trained points plus five added monitoring points | Yes | Requested locations; display radii capped at 800 m | Static | Keep but transform | Display footprint does not show physical resolution; unused 40 scan sectors do not confer coverage |
| `weather.time`, `marine.time`, browser `now`, `fetchedAt`, cached prior result | Runtime/fallback time inputs | `dangerZonePredictor.js:165,216,256`; `dashboard-markers.js:376-409` | Provider valid times and retrieval times; previous forecast result on failure | Yes, possibly stale | Previously selected cells | Initial load/manual refresh in inspected caller; source update cadence not measured | Keep but transform | Weather time or wall-clock fallback cannot stand in for marine validity or model issue time |
| Demo weather/marine endpoint override | Fallback/scenario input | `dangerZonePredictor.js:4-35,263` | Explicit synthetic demo endpoint | Yes as illustration | Same configured sectors | Demo-defined; not environmental cadence | Keep | Only as source-labeled demonstration; not evidence that those conditions exist |

The committed artifact and model card describe three trained sectors and 40 stored scan sectors; the current training script defines eight initial sectors and exports a different version.
Runtime evaluates three artifact sectors plus five hard-coded cells, not the documented 43 (`docs/17_AI_EXPLAINED_SIMPLY.md:128,150`).
This report does not infer that the current script exactly reproduces the committed model's rows merely because its label description matches.
The metadata is evidence of claimed artifact provenance, not independent verification of downloaded raw samples.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Explicit single target and hazard horizon (Add) | Necessary | Distinguish current threshold tier from casualty probability or future forecast | Existing code and label definitions can support a narrower claim | Narrower target | Current OR training target and AND danger tier are different |
| Actual provider cell coordinates, model identity, valid/issue time, joint weather/marine support (Add) | Necessary for locality/freshness claim | Regional forecast environmental tier at the right place/time | Some response coordinates/times exist but are discarded; issue metadata availability needs checking | Same environmental target | Requested 600 m circle is not model resolution; retrieval does not establish matched valid times |
| Nearshore sea state, tide and bathymetry at sufficient local scale (Add later) | Helpful for regional proxy; necessary for local navigational/boat safety claim | Channel/shoaling/current-wave interactions | Current wave source and coarse GEBCO exist; no suitable local validation/tidal input | Same environmental target if narrowed; otherwise stronger different target | Coarse bathymetry alone cannot resolve local loading |
| Vessel class/stability and load (Add later) | Necessary for vessel-specific safety probability | Failure susceptibility of the actual vessel | Not consumed; requires verified attributes and outcomes | Different target | Same waves do not imply same capsize likelihood for every vessel |
| Operator experience, daylight, distance/time to safe harbor (Add later) | Helpful for operational go/no-go advice | Context-specific operating recommendation | Not consumed; new human/route data; daylight can be sourced externally but is not wired | Different target | These concern exposure and ability to respond, not the current proxy label |
| Independent casualty, near-miss or explicitly defined local hazard observations (Add) | Necessary for empirical safety skill; local hazard observations sufficient for narrower claim | Validate chosen output rather than feature thresholds | Requires new labeling | Same target only if hazard proxy remains; different target for vessel outcomes | Labels must be independent of the rule being evaluated |
| Forecast-as-issued historical inputs (Add) | Necessary for predictive forecast claim | Skill at a specified positive lead time | Not in committed training evidence | Different target if current classification becomes prediction | Reanalysis label reproduction is not prospective forecast evaluation |

#### Scale, geometry, leakage, and circularity findings

- **Threshold-label circularity is specific, not a ban on these inputs.** Wind/wave values are the right data to evaluate those thresholds.
  A classifier learning those same thresholds mainly learns a deterministic environmental definition.
  Its AUC cannot establish that a vessel will capsize, and adding correlates of the same label does not repair that target mismatch.
- `measuredDanger` requires wave ≥2 m **and** gust ≥40 km/h or wind ≥30 km/h.
  Training labels use an **OR** across those conditions, plus thunderstorm/cyclone terms.
  Even a high classifier probability is capped below Danger if the conjunction fails.
  Therefore neither `score` nor `strongestProbability` is the model's probability of the trained event.
- `degradedCount` is global, contrary to the document's sector-specific buoy-health wording (`docs/17_AI_EXPLAINED_SIMPLY.md:167`).
  Missing/offline communication may alter confidence in observations; it does not establish more severe marine weather at all sectors.
- Reanalysis-to-current-product transfer and 3-hour sampling versus current intervals change the input distribution.
  A ±3-hour best-track target is a retrospective proximity label, not a direct live feature leak by itself; claiming positive-lead forecast skill would require issue-time data.
- Static GEBCO depth is used to produce “Shallow-water bathymetry” reasons even though the committed classifier does not use depth in any split.
  The explanation therefore suggests a contribution not established by the model or explicit hazard rule.
- Returning multiple nearby request coordinates does not prove multiple independent resolved weather cells.
  The provider can return grid centers displaced from requested locations; exact regional selected resolution is **not stated** in stored runtime/model evidence.
  Do not import the provider's best global headline resolution as local 600 m skill.
- Cached scans and `observedAt=weather.time || marine.time || now` collapse different kinds of time support.
  A fetch failure is disclosed; it still leaves an older result, and a successful fetch does not prove the atmospheric and marine values are contemporaneous.

#### Highest-value correctness change

Define the displayed result as an explicit current environmental threshold tier, separate from classifier probability and casualty risk.
This narrows the target and resolves the OR-label/AND-tier discrepancy before any feature expansion.

#### Input to drop or replace

Drop `buoyAdjustment` from the environmental hazard score.
Buoy health can describe data availability, but this count is neither a local sea-state observation nor a trained hazard predictor.
Depth is a second candidate to drop from the hazard explanation; no new bathymetric feature is justified solely to increase the current label's accuracy.

#### Minimum defensible input set

- Time-aligned forecast wind, gust and significant wave height for the actual represented cell: **already present but unsuitable or incomplete** in provenance/local resolution.
- Recognized weather condition and explicitly scaled precipitation if part of the rule: **already present and suitable** for their own environmental thresholds, subject to the same source/time caveats.
- One documented rule target with horizon and units: **requires a narrower or different target**; current inputs can support threshold guidance.
- Local environmental observations: **requires new collection** to validate the same narrowed target.
- Vessel-specific attributes and independent incident outcomes: **requires new collection** only for a **different target**, vessel safety probability.
- Learned seasonal/depth features are not a minimum requirement for a transparent threshold classification.

#### Beyond the prior audit

Adds the OR-training/AND-runtime mismatch, global non-environmental buoy adjustment, unsupported depth explanation, forecast-product transfer, and valid-time/provenance loss.
The prior audit's sector-count and version discrepancies are confirmed but used only to qualify spatial transfer and artifact lineage, not repeated as a release-management finding.

#### Honest output after fixes

“Current provider-forecast environmental conditions meet this stated threshold tier at the represented forecast cell; this is regional guidance, not vessel-specific safety or casualty probability.”

#### Plan-ready findings

##### Finding HAZARD-01: The trained event and displayed danger tier are different targets

- Severity: High
- Type: target mismatch
- Evidence: `web/ml/train_danger_zone_model.py:229-248`; `web/js/dangerZonePredictor.js:182-210,255`; `web/ml/model-card.json:metadata.label_definition`.
- Problem: OR-defined training positives become an AND-defined Danger tier, while score percentages imply a common probability.
- Recommendation: Define one explicit environmental threshold-tier claim and distinguish it from any classifier probability; use independent outcomes only if the target becomes vessel risk.
- Target effect: narrower target
- Expected benefit: Makes the output's event, horizon and numerical meaning unambiguous.
- Dependencies: Existing definitions; new labeling only for stronger predictive claims.
- Verification evidence needed: Wave-only, gust-only, thunderstorm-only, cyclone-only and combined wind/wave cases mapped separately to training label, classifier score and displayed tier.
- Implementation planning note: Decide the physical target first; do not improve AUC on the proxy and call that improved casualty prediction.

##### Finding HAZARD-02: Global buoy health and unused depth are presented as hazard evidence

- Severity: Medium
- Type: wrong input
- Evidence: `web/js/dangerZonePredictor.js:123-150,163-184`; `web/ml/model-card.json:metadata.feature_importance`; `docs/17_AI_EXPLAINED_SIMPLY.md:167`.
- Problem: Every sector gets the same untrained communication-health increment, and a zero-use depth variable generates a risk reason.
- Recommendation: Remove health adjustment from environmental severity and remove unsupported depth attribution; retain source health only as source-quality context.
- Target effect: same target
- Expected benefit: Prevents nonlocal communication faults and unused features from masquerading as physical marine hazard.
- Dependencies: Existing source data and artifact inspection.
- Verification evidence needed: Hold weather fixed and change an unrelated buoy's status; inspect depth split usage and verify explanations correspond to an actual decision input.
- Implementation planning note: Separate measurement availability from weather severity; no new hazard features are necessary to make this distinction.

##### Finding HAZARD-03: Fine sector display lacks matching spatial and temporal source support

- Severity: High
- Type: scale mismatch
- Evidence: `web/js/dangerZonePredictor.js:96-104,165-180,205-216,222-239`; `web/ml/train_danger_zone_model.py:114-137,213`; `web/ml/model-card.json:sectors`.
- Problem: Three historical sector sources transfer to eight displayed cells; actual grid/valid-time differences and historical-versus-live product differences are not represented by the displayed radii.
- Recommendation: Represent actual source cell/time support and restrict wording to its resolved domain; require forecast-as-issued/local evidence for any finer or positive-lead claim.
- Target effect: narrower target
- Expected benefit: Avoids implying neighborhood-scale hazard measurement from a regional forecast product.
- Dependencies: Existing provider response metadata; local observations for added accuracy claims.
- Verification evidence needed: Capture returned grid centers/model/valid times for all eight requested cells and compare duplicates, atmospheric/marine offsets and historical input definitions.
- Implementation planning note: Verify the committed artifact's actual training lineage; current training script and committed model version are not identical evidence.

### Mobile risk score

#### Claimed output

The actual output is a daily threshold classification, `safe`, `caution`, `danger`, or `unknown`, with reasons and an optional normalized severity score.
It applies to weather requested for one handset/default location for each forecast date, not to an identified vessel's probability of capsizing or returning safely.
`SafetyScore.assess` defines the computation (`mobile/lib/services/safety_score.dart:33-146`); `mobile/lib/l10n/app_en.arb:145-153` supplies the missing-sea-state disclaimer, guidance language and the visible “Safe” label.
The honest interpretation is “the available forecast variables cross these policy thresholds on this date.”
The stronger interpretation “this vessel can safely go fishing” needs a different target and vessel exposure evidence.

Comments describe a buoy-fused backend score outranking the handset rule, but the current backend forecast response explicitly supplies no risk score (`backend/app/api/public.py:297-304`; `forecast_provider.dart:21-22`; `safety_score.dart:24-28`).
Both the current backend-fed and direct-provider paths therefore use the handset heuristic.
The requested forecast is seven days, with three days designated confident by configuration; no empirical calibration of that confidence horizon was found (`mobile/lib/core/config.dart:133-141`).
There are no training examples, learned labels or model evaluation target for this rule.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `gustKph` from `wind_gusts_10m_max` / `gust_kph` | Runtime input | `forecast_provider.dart:91-99`; `daily_outlook.dart:223,279`; `safety_score.dart:46-54` | External forecast, parsed | Yes when provided; future realized gust is not known | Returned atmospheric grid; actual local grid resolution not stated | Daily maximum; application polls every 30 minutes; provider issuance cadence for selected model not stated | Keep | Gust loading is physically relevant to small craft; it remains a grid forecast maximum, not a measured gust at the hull |
| `windKph` from `wind_speed_10m_max` / `wind_kph`, substituted as `gust` | Fallback input | `daily_outlook.dart:222,278`; `safety_score.dart:46` | External forecast of a different wind statistic | Yes when provided | Same atmospheric grid | Daily maximum wind speed, not daily maximum gust | Replace | A mean-wind statistic cannot establish that gusts stayed below a gust threshold; retain its own meaning rather than relabeling it |
| `waveM` from hourly `wave_height` | Runtime input; derived feature | `daily_outlook.dart:291-317`; `backend/app/api/public.py:199-215`; `safety_score.dart:57-68` | External significant-wave forecast, maximum of available daily samples | Yes if marine response succeeds | Marine grid; resolution and nearshore representativeness not stated in the response lineage | Hourly samples reduced to a daily maximum; missing hours skipped; application polls every 30 minutes | Keep but transform | Relevant wave exposure proxy; maximum of incomplete samples is not necessarily the full day's maximum, and significant height is not the largest individual wave |
| `precipMm` from `precipitation_sum` / `precip_mm` | Runtime input | `daily_outlook.dart:224,280`; `safety_score.dart:71-82` | External forecast | Yes | Atmospheric grid | Daily total, not instantaneous rainfall rate | Keep but transform | Appropriate for a declared daily-rain threshold; too indirect to represent current visibility, convective gust severity or vessel safety by itself |
| `weatherCode`, `condition` | Runtime input; derived feature | `daily_outlook.dart:219,275,374`; `weather_snapshot.dart:WeatherCondition.tryFromCode/fromCode`; `safety_score.dart:85-105` | External weather category mapped to local enum | Yes if present; parser invents code `0` when absent | Atmospheric grid | Daily category; provider-defined daily summary, not a timed storm onset | Keep but transform | Thunderstorm/rain/fog categories are relevant; missing or unrecognized codes must remain unknown rather than become sunny/calm |
| `lat`, `lon`; cached `Fix.lat`, `Fix.lon`; default `aklanLat=11.6892`, `aklanLon=122.3667` | Runtime input; fallback input | `home_page.dart:236-241`; `location_service.dart:75-103`; `config.dart:87-88` | Device location or static fallback | Coordinates available, but cached fix age is not screened by this caller | Last-known handset point or municipal reference, not necessarily present vessel position | Location sample age/cadence not stated at this decision; default static | Keep but transform | A forecast is only location-specific if the location represents the decision object; preserve fix age/accuracy and distinguish a regional fallback |
| `latitude`, `longitude`, `marineSampleLat`, `marineSampleLon`, `fetchedAt`, forecast date | Runtime support inputs | `forecast_outlook.dart:95-106,376-387`; `forecast_provider.dart:63-70`; `forecast_cache.dart:ForecastCache`; `home_page.dart:224,254` | Provider metadata mixed with request coordinates and device retrieval time | Partly: actual marine grid center and model issue time are not retained by this path | Atmospheric returned point; marine fields supplied from requested point | Daily valid dates; retrieval time; cache maximum age 12 hours; provider model issue time not stated | Keep but transform | Requested marine coordinates do not prove the returned marine cell; retrieval time alone does not establish forecast issuance or location freshness |
| `cautionGustKph=30`, `dangerGustKph=50`, `cautionWaveM=1.5`, `dangerWaveM=2.5`, `cautionPrecipMm=20`, `dangerPrecipMm=50` | Static parameter; policy target definition | `config.dart:161-166`; `safety_score.dart:33-128` | Human-selected constants; local outcome calibration not stated | Yes | Same for every vessel/location | Fixed; daily use | Keep but transform | Keep as explicit policy thresholds; they are not demonstrated universal safety limits |
| `level`, `reasons`, `_score=max(gust/(50×1.4), wave/(2.5×1.4), precip/(50×1.4))`, clipped to `[0,1]` | Derived feature/output | `safety_score.dart:109-146` | Deterministic calculation from above | Yes | Same daily cell | Per assessment | Keep but transform | Severity index is not a probability; weather category can produce Danger while the numeric index is low because code is absent from the index |
| Existing `day.risk` with `source==backend` | Conditional runtime override | `safety_score.dart:25-30`; `public.py:297-304` | Intended server result; not currently produced by inspected endpoint | Not currently supplied by that endpoint | Not established | Not stated | Add later | No additional data-fit finding for an inactive fusion input; reassess its target if it is actually introduced |

Daily temperatures are downloaded/displayed but are not inputs to this risk rule; do not attribute risk prediction to them.
No synthetic weather fallback was found in this active daily rule; nulls, mean-wind substitution, regional coordinates and cached forecasts are its relevant degraded inputs.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Per-variable completeness, including full-day wave support and a genuinely known weather code | Necessary | “No checked forecast threshold exceeded” with an explicit checked-variable set | Existing responses and sample times; not fully carried through reduction | Same threshold target; narrows current “Safe” interpretation | Low rainfall alone cannot establish low wind or low waves; **Add** |
| Actual forecast grid centers/valid times and handset fix age/accuracy | Necessary for location-specific guidance | Forecast conditions for the stated location and period | Provider response and `Fix` contain parts; marine response metadata not retained here | Same target with honest spatial qualification | Prevents an old onshore fix or displaced marine cell being treated as the current vessel; **Add** |
| Vessel class/stability, load and route exposure linked to independent safety outcomes | Necessary only for a vessel-safety prediction | Probability of a defined unsafe vessel event | No linked labeled dataset demonstrated; requires collection | Different target | **Add later** only if retaining the stronger safety claim; unnecessary for an explicitly environmental threshold rule |

#### Scale, geometry, leakage, and circularity findings

Wind and waves have credible physical mechanisms through aerodynamic loading and vessel motions; daily rain is a coarser proxy whose physical effect depends on intensity and context.
No repository result quantifies predictive improvement for real vessel safety, and no causal effect is identified.
Threshold self-consistency would only establish that the rule implements its policy.

`assess` begins at Safe and returns Unknown only when gust, wave and precipitation are all absent unless an adverse code already raises the level (`safety_score.dart:34,109-126`).
Consequently a day with only zero precipitation can be Safe despite missing both wind and sea state.
The missing-wave disclaimer is useful but does not change that input-output classification.
Replacing an absent weather code with `0` and substituting wind for gust separately make missing information look favorable.

The forecast requested at `cachedFixIfPermitted` can refer to a previous location; the returned `Fix` includes age/accuracy information but the caller passes only latitude/longitude.
The direct marine call uses the supplied coordinates despite its stale fixed-offshore comment (`forecast_provider.dart:112-125`).
Provider guidance confirms that returned marine grid coordinates can differ from the request; a requested point is not proof of shoreline-scale support ([Open-Meteo marine documentation](https://open-meteo.com/en/docs/marine-weather-api)).
The rule itself takes no current time or forecast freshness argument; loading a cache checks age, but retaining an in-memory outlook after a failed refresh does not independently rescore daily validity (`home_page.dart:236-254`; `SafetyScore.assess`).
This is a provenance limitation, not evidence that every displayed forecast is stale.

#### Highest-value correctness change

Make the low-risk output conditional on explicitly sufficient inputs, preserving missing gust, wave and category information instead of favorable substitutions.
This narrows the claim to an environmental threshold assessment and improves correctness under missing data; it does not validate vessel safety prediction.

#### Input to drop or replace

Replace `day.windKph` as the fallback value of a variable called `gust`.
Wind speed can remain a separately named observation/forecast statistic.

#### Minimum defensible input set

- Daily gust forecast: **already present but unsuitable or incomplete** when substituted by wind speed; retain genuine gust identity for the same threshold target.
- Significant-wave forecast with valid-date sample support: **already present but unsuitable or incomplete** when gaps are hidden; same target.
- Known weather category and explicitly daily precipitation: **already present but unsuitable or incomplete** because absent code becomes fair weather; same target.
- Target coordinates, fix age/accuracy, actual atmospheric/marine cells and valid times: **available from an existing source but not currently used** in full; supports the same location-specific target.
- Named policy thresholds: **already present and suitable** for a rule, not validated safety limits.
- Claim “no checked threshold exceeded” instead of vessel safety: **requires a narrower or different target**; makes the current computation honest without collecting unrelated features.

#### Beyond the prior audit

The prior audit correctly identifies a handset heuristic rather than trained AI.
This analysis adds the mean-wind-as-gust substitution, favorable missing-code default, partial-wave daily maximum, and the specific partial-input path that still returns Safe.
It also qualifies the claim of a fixed offshore marine point by following the actual caller's coordinates.

#### Honest output after fixes

“For the stated forecast cell and date, the listed available forecast variables cross these policy thresholds; incomplete inputs cannot establish an all-clear, and this is not a vessel-safety probability.”

#### Plan-ready findings

##### Finding MOBILE-01: Missing hazard variables can still produce Safe

- Severity: High
- Type: wrong input
- Evidence: `mobile/lib/services/safety_score.dart:34,46,109-126`; `mobile/lib/models/daily_outlook.dart:219,275,291-317`; `backend/app/api/public.py:199-215`.
- Problem: Mean wind substitutes for gust, absent weather codes become fair weather, and a partial set of low values can classify a day Safe.
- Recommendation: Preserve each variable's identity and missingness; define the minimum checked-variable support for a favorable threshold classification and qualify incomplete daily maxima.
- Target effect: narrower target
- Expected benefit: Prevents absent or differently defined weather data from becoming evidence of safe conditions.
- Dependencies: Existing forecast fields and sample times.
- Verification evidence needed: Inspect classifications for rain-only zero, missing gust with low mean wind, absent/invalid code, and one available wave sample; compare complete-day behavior separately.
- Implementation planning note: Decide whether the intended low tier means no observed threshold crossing or adequate evidence of low environmental thresholds; do not claim vessel safety from either alone.

##### Finding MOBILE-02: Forecast location and age do not fully identify the decision object

- Severity: Medium
- Type: provenance issue
- Evidence: `mobile/lib/ui/home_page.dart:236-254`; `mobile/lib/services/location_service.dart:75-103`; `mobile/lib/services/forecast_provider.dart:63-70,112-125`; `mobile/lib/models/forecast_outlook.dart:376-382`.
- Problem: A cached fix or default point drives the forecast; requested marine coordinates stand in for returned marine-cell metadata, and retrieval time is not model issuance or fix time.
- Recommendation: Base the claim on the actual target location, location age and source valid-time/grid support; describe regional fallback forecasts as regional.
- Target effect: narrower target
- Expected benefit: Prevents a forecast for another point or period from being interpreted as conditions at the current vessel; also constrains fishing-window interpretation.
- Dependencies: Existing location and provider metadata; selected-model issuance metadata may require additional provider information.
- Verification evidence needed: Compare one stale handset fix, regional fallback and nearshore marine response against the recorded requested/returned coordinates and valid times.
- Implementation planning note: Determine which metadata the backend and direct paths actually preserve before deciding what additional source fields are necessary.

### Fishing window

#### Claimed output

The displayed “Fishing weather window” is an operational weather-guidance rule: current caution/danger, unknown/incomplete coverage, an approximate time to a forecast threshold crossing, or no worsening through a supported horizon.
It is computed by `FishingWindowCalculator.calculate` (`mobile/lib/services/fishing_window.dart:143-560`) and displayed by `weather_card.dart:78` using strings in `app_en.arb:575-665`.
The displayed disclaimer already says it excludes return/preparation/travel time.
Therefore the defensible object is the forecast time series at the requested location, not a vessel's remaining safe time at sea.
The horizon is up to `confidentDays=3`, further limited by contiguous available data.
No learned target or training/evaluation dataset exists for this component.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| Hourly `windKph`, `gustKph` from `wind_speed_10m`, `wind_gusts_10m` | Runtime input | `forecast_provider.dart:95-99`; `forecast_outlook.dart:parseOpenMeteo`; `fishing_window.dart:563-602` | External forecasts | Yes as forecasts, not future measurements | Atmospheric grid at shared mobile target | Hourly values; actual provider issuance cadence not stated; application polls 30 minutes | Keep but transform | Relevant wind exposure; instantaneous wind and preceding-hour gust maximum have different temporal support |
| Hourly `waveM` from `wave_height` | Runtime input | `forecast_provider.dart:122-127`; `fishing_window.dart:315-339,563-602` | External significant-wave forecast | Yes if supplied | Marine grid, possibly offset from atmosphere and handset | Hourly instantaneous samples; current selection accepts nearby past or future sample within one hour | Keep but transform | Physically relevant; a future sample is a forecast for that time, not a current measurement |
| Hourly `weatherCode`, `condition` | Runtime input; derived feature | `forecast_outlook.dart:parseOpenMeteo`; `fishing_window.dart:563-602` | External category; unknown can remain null in hourly assessment | Yes when supplied | Atmospheric grid | Hourly category | Keep but transform | Relevant category rule; onset support must match the actual variable rather than assuming every value covers the preceding hour |
| `days[].precipMm`, daily `risk.level`, daily weather category | Runtime input; fallback input | `fishing_window.dart:233-273,301-313,466-512,621-631` | External daily aggregate plus the mobile rule | Yes as a whole-day forecast | Same shared forecast location | Daily total/category; daily-only fallback intentionally has no hourly countdown | Keep but transform | Daily restriction is legitimate, but whole-day rain does not establish present rainfall or its start time; daily risk inherits MOBILE-01 |
| `seaCondition.status` including `notAdvised`, `caution`; `squall.returnNow`, `squall.level` | Human-entered decision input; upstream runtime input | `fishing_window.dart:153-181`; `models/sea_condition.dart`; `venture_feeds.dart:squall` | Human authority plus upstream squall output | If feeds are present; applicability/age are not checked in this calculator | Declaration/feed scope supplied upstream; no route-specific intersection here | Feed polling is application-driven; decision effective interval/source cadence not stated here | Keep but transform | An applicable official restriction is decision-relevant without being a physical measurement; squall limitations carry through, and age/scope must accompany authority |
| `forecast.fetchedAt`, `now`, `refreshMaxAge=30 min`, `cacheMaxAge=12 h`, future-skew tolerance | Runtime support input; static parameter | `fishing_window.dart:143-151,199-231`; `data/forecast_cache.dart:ForecastCache` | Device clock/retrieval time and policy constants | Yes | Whole retrieved forecast, not per source grid | Reassessed against current device time; not provider issue cadence | Keep but transform | Useful retrieval-age guard; cannot establish source issuance, source-valid-time coverage or warning applicability alone |
| Hourly `time`, sorted/deduplicated intervals, `intervalStart=time−1 h`, `lastEnd`, `hasGap`, `isIncomplete`, `durationUntilDeterioration` | Derived features | `fishing_window.dart:275-284,344-459,563-602` | Deterministic temporal transforms; duplicates merged conservatively | Yes | Same location assumed across sequence | Hourly with 15-minute gap tolerance; three-day horizon | Keep but transform | Completeness is essential to a countdown; current incomplete support is not propagated to the future gap state |
| `_calculateOnset`: `time` for wave-only, `time−1 h` otherwise | Derived feature | `fishing_window.dart:128-141` | Rule-defined timing | Yes | Same forecast cell | One-hour shift, not an estimated physical onset distribution | Replace | Mixed variable timestamps do not support a universal minus-one-hour atmospheric onset |
| Gust/wave thresholds, severe-weather categories, daily rain thresholds; `confidentDays` | Static parameter; policy target definition | `config.dart:137,161-166`; `fishing_window.dart:563-602` | Fixed policy choices | Yes | Uniform across vessels and routes | Fixed; hourly thresholds plus daily rain restrictions | Keep | Defines a useful limited guidance rule if described explicitly; no outcome-derived confidence calibration was found |
| Requested/returned coordinates, cached fix and regional fallback | Runtime/fallback support input | Same active forecast lineage as MOBILE-02 | Device/provider/static mixture | Partly | Cell at supplied point, not a vessel trajectory | Fix age and selected-grid update cadence not stated | Keep but transform | A fixed-location forecast cannot directly represent an offshore trip moving between cells |

Hourly temperature and precipitation are present in provider requests but are not active inputs to `_assessHour`; daily precipitation is the rain decision input.
No synthetic fallback is used here.
Cached and daily-only data are the substantive fallback sources.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Complete present-hour support carried into the entire countdown interval | Necessary | Time to next threshold crossing without an unassessed starting interval | Existing hourly fields and `isIncomplete` | Same target | **Add**; complete future data do not repair missing present wind or waves |
| Per-variable valid-time/aggregation semantics | Necessary | Correct timing of the forecast crossing | Existing provider documentation and returned timestamps | Same target | **Add**; one hourly timestamp can label an instantaneous value or a preceding-hour maximum |
| Restriction effective time/geographic applicability | Necessary for applying the restriction to this trip | Applicable official restriction or upstream alert | Feed contains portions; no complete effective-time policy demonstrated here | Same guidance target | **Add** where available; do not reinterpret an authority decision as measured weather |
| Route, return duration and preparation margin | Irrelevant to the explicitly disclaimed weather-threshold countdown; necessary for safe remaining fishing time | Trip-specific time available before return | No complete linked route-duration input in this computation | Different target | **Add later** only if the claim expands; retain the existing exclusion for the narrow output |

#### Scale, geometry, leakage, and circularity findings

The rule has plausible environmental inputs, but no field evidence demonstrates its accuracy in forecasting local threshold onset, and no causal conclusion follows.
Its forecast horizon is distinct from a trip's exposure horizon and from the source's actual useful skill horizon.
The source model's future values are available at decision time as forecasts; this is not leakage, provided they are not retrospectively replaced by realized/revised weather in evaluation.

There is a concrete missing-information failure: `_assessHour` can mark `currentHour` incomplete and set `currentIsIncomplete=true`, but the unknown branch also requires `currentHour==null` (`fishing_window.dart:362-389`).
In that path the two conditions cannot both hold.
The later scan initializes `hasGap=false`, so complete future hours can yield a positive countdown despite an incomplete current interval.
This is an input-support finding rather than a general code review: the countdown claims an assessed interval whose starting conditions were not established.

The provider distinguishes instantaneous wind from preceding-hour gust maxima and daily accumulated rain ([Open-Meteo forecast documentation](https://open-meteo.com/en/docs)).
The marine wave height is an instantaneous significant-wave quantity ([Open-Meteo marine documentation](https://open-meteo.com/en/docs/marine-weather-api)).
Treating all atmospheric samples as `[T−1h,T)` and subtracting an hour from every non-wave onset changes the physical meaning of instantaneous wind/category values.
Today's total rainfall also raises `currentRisk` irrespective of whether the rain is expected later or has already passed (`fishing_window.dart:301-313`).
A daily precaution can be valid policy, but its output should be a day-level restriction, not evidence of current adverse rain.
The future daily-rain branch already avoids inventing a midnight countdown, which is a useful existing pattern.

#### Highest-value correctness change

Carry incomplete current environmental support into the countdown's assessed interval.
This improves correctness for the same forecast-threshold target; it does not require a new prediction model or new weather variables.

#### Input to drop or replace

Replace the universal `time−1 hour` atmospheric onset transformation with the source variable's actual temporal meaning.
Do not drop the official restriction merely because it is human-entered; it is an independent decision input.

#### Minimum defensible input set

- Hourly genuine gust, significant wave height and known category for the current and intervening future support: **already present but unsuitable or incomplete** when missing current support is ignored; same target.
- Per-variable timestamp meaning and returned cell identity: **available from an existing source but not currently used** consistently; same target.
- Daily rain explicitly interpreted as a daily restriction: **already present but unsuitable or incomplete** when described as current; narrows timing language.
- Applicable human restrictions and upstream alert state with effective-time/scope support: **already present but unsuitable or incomplete**; conditional guidance, not a physical probability.
- Clock, retrieval age and a bounded supported horizon: **already present and suitable** as limited guards, without claiming provider freshness or three-day forecast skill.
- Route/return time: **requires a narrower or different target** if users are to receive remaining safe fishing time; not needed for the current disclaimed weather-only guidance.

#### Beyond the prior audit

The prior audit's rule-based characterization remains correct.
This analysis adds the current-interval completeness contradiction, variable-specific timestamp mismatch, and distinction between a daily-rain precaution and rain occurring now.
It retains the existing daily-only and return-time disclaimers rather than demanding a learned model for this guidance.

#### Honest output after fixes

“At this forecast location, the next specified environmental threshold is forecast around this time, conditional on complete intervening data and applicable warnings; this is not the time you can safely remain fishing or the time needed to return.”

#### Plan-ready findings

##### Finding WINDOW-01: A countdown can start from an unassessed current interval

- Severity: High
- Type: missing input
- Evidence: `mobile/lib/services/fishing_window.dart:362-389,427-459,563-602`.
- Problem: Current incompleteness is detected but cannot activate the corresponding unknown branch and is not carried into the future gap state.
- Recommendation: Require explicit current-and-intervening variable support for the countdown; preserve adverse evidence but withhold a favorable continuous-window claim across unknown conditions.
- Target effect: same target
- Expected benefit: Makes the reported interval match the interval actually supported by input data.
- Dependencies: Existing hourly data and completeness flags.
- Verification evidence needed: A present interval with missing gust or wave, followed by complete future intervals and a later threshold crossing, must not imply fully assessed time from now.
- Implementation planning note: Trace all favorable result states and the daily-only fallback against the same minimum-input definition before changing the calculation.

##### Finding WINDOW-02: Forecast aggregates are assigned unsupported onset times

- Severity: Medium
- Type: scale mismatch
- Evidence: `mobile/lib/services/fishing_window.dart:128-141,301-313,315-359,466-512`; `mobile/lib/services/forecast_provider.dart:95-99,124-127`; provider variable definitions cited above.
- Problem: Instantaneous atmospheric values inherit preceding-hour support, and full-day precipitation can be presented as current risk.
- Recommendation: Define threshold timing by each variable's temporal support and distinguish whole-day restrictions from an hourly onset.
- Target effect: narrower target
- Expected benefit: Prevents unsupported precision or current-condition claims from hourly/daily aggregate inputs.
- Dependencies: Existing provider timestamps and authoritative variable definitions.
- Verification evidence needed: Compare gust, instantaneous wind, wave-only, category-only and later-today rain cases against the source's actual valid intervals.
- Implementation planning note: Establish the provider semantics in both backend and direct responses; do not infer all variables' intervals from their shared timestamp column.

### Consent-based catch-activity surface

#### Claimed output

The active output is a retrospective, coarse relative reporting-activity surface, computed on request from consented catch-log rows (`backend/app/api/hotspots.py:21-96`).
It is neither a trained fish-distribution model nor a probability of catching fish.
The handset contract explicitly disclaims catch probability but calls the count “independent observations” (`mobile/lib/models/hotspot_cell.dart:29-36`).
The actual count is raw log rows, including repeated reports by the same vessel.
The score combines distinct vessel identifiers and capped repeated reports, normalized relative to eligible cells in the same query.
It supports inspection of where participating vessels have reported activity, subject to location and reporting biases.

The nominal horizon is the last 30 days and the object is a `0.02°×0.02°` cell with at least three distinct reporting vessel IDs.
The code's date filter, however, has no upper bound and includes the cutoff date; it is not precisely a bounded trailing 30-day interval.
Only the highest-ranked 40 cells are returned.
There is no learned target, training dataset, or evaluation label to invent for this aggregation.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `share_for_hotspots` | Runtime input; inclusion policy | `api/catch.py:46,92-116`; `api/hotspots.py:82` | Explicit human-entered consent flag | Yes for ingested rows | Individual report before aggregation | At logging/update; upload can be delayed offline | Keep | Correctly defines the consenting-report population; consent is not evidence that the sample represents all fishing |
| `vessel_id` | Runtime input | `hotspots.py:36,39-48`; `catch.py:CatchIn` | Report-linked vessel identifier | Yes | Vessel identity within each cell | Per submitted report | Keep | Supports distinct reporting-vessel counts, not independent trips, people, standardized effort or outcomes |
| `latitude`, `longitude` from `Fix.lat`, `Fix.lon` | Runtime input | `catch_service.dart:73-105`; `hotspots.py:28-36`; active callers `venture_page.dart:1240,2168` | Device GPS at logging, submitted as catch coordinates | Yes if fix succeeds; otherwise null and excluded | Point reduced to coarse cell; accuracy not retained by aggregation | Sample at logging; actual catch-event time/location relation not established | Keep but transform | Directly identifies a report location, but not necessarily where fish were caught if logging occurs later; accuracy can affect boundary assignment |
| Optional `fallbackLat`, `fallbackLon` | Potential fallback input, inactive in inspected callers | `catch_service.dart:79-80,104-105`; `venture_page.dart:1240,2168` | Caller-provided position if supplied | Not supplied by the two active catch UI callers | Would be last known position | Age not stated | Add later | Do not diagnose an active stale-position fallback that these callers do not use; reassess only if a caller begins supplying it |
| `catch_date`, `created_at`, `CURRENT_DATE` | Runtime selection inputs | `catch_service.dart:90-100`; `api/catch.py:41`; `hotspots.py:85-87` | Device UTC logging date in active mobile path, human/API-supplied date otherwise; server receipt time and database date | Yes for received rows; unuploaded reports absent | Whole query domain | Day precision; inclusive lower cutoff; no upper bound; receipt time breaks ordering ties | Keep but transform | Need a defined event-vs-log date and bounded reporting interval; future dates currently qualify and delayed arrivals change the surface |
| `lat_bin=floor(latitude/0.02)`, `lon_bin=floor(longitude/0.02)`, `center_lat`, `center_lon` | Derived feature | `hotspots.py:32-35,61-65` | Deterministic geographic binning | Yes | Fixed angular cell, roughly 2.2 km north-south; east-west size varies with latitude | Per aggregation | Keep | Appropriate coarse reporting unit; cell center is not an observed fishing point or a precise productive location |
| `reporters=len(counts)`, `observations=sum(counts)`, `capped_observations=sum(min(count,3))` | Derived feature | `hotspots.py:51-54` | Counts of eligible submitted rows/vessel IDs | Yes within selected rows | Per cell | Query's selected date range | Keep but transform | Name raw reports and distinct reporters separately; repeated logs are not independent evidence, even when score contribution is capped |
| `max_reporters`, `max_capped_observations`, `score=0.7×reporters/max_reporters + 0.3×capped_observations/max_capped_observations` | Derived feature | `hotspots.py:46-58` | Within-query normalization and policy weights | Yes | Relative to all eligible cells before top-40 selection | Recomputed per request; no fixed seasonal baseline | Keep but transform | Directly defines relative reporting intensity; score can change when another cell changes and is not comparable as absolute abundance or probability |
| `CELL_SIZE_DEGREES=.02`, `MIN_REPORTERS=3`, per-vessel cap `3`, weights `.7/.3`, `WINDOW_DAYS=30`, `MAX_CELLS=40`, row limit `20000` | Static parameter | `hotspots.py:14-17,48,54-58,70,88` | Aggregation/disclosure/selection policies | Yes | Coarse cells and global query cap | Fixed; nominal 30-day window | Keep but transform | Thresholds define what is shown; global row truncation before per-vessel capping can alter the geographic sample and distinct-reporter counts |
| `generated_at`, persisted hotspot snapshot | Runtime metadata; fallback input | `hotspots.py:93`; `venture_feeds.dart:51-75,132-141`; `venture_page.dart:303-312`; `config.dart:213` | Server computation timestamp; previously fetched response | Yes if cached; not necessarily current | Previously computed same surface | Hotspot poll 15 minutes; source reports event-driven; cached payload age preserved separately, maximum source-report freshness not stated | Keep but transform | Generation time is not latest catch-event time or complete data coverage; an old retained surface remains historical reporting evidence |

`species`, `quantity_estimated`, `quantity_confirmed`, `method` and `notes` are stored catch attributes but are not inputs to `aggregate_hotspots`.
In particular, neither catch weight nor confirmed quantity influences the displayed score.
There is no runtime synthetic surface substitution in the active feed; `DemoHotspots.surface` is excluded as unused.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Explicit catch-event versus logging location/date meaning, plus fix accuracy | Necessary if calling these catch locations rather than report locations | Honest spatial meaning of the reported activity | Logging fix/date exist; independent catch-event location/time not established | Narrows to report location unless event data collected | **Add** meaning/support, not a new fish model; otherwise shore-side logging can be interpreted as offshore catch geography |
| Bounded date support and indication of globally truncated source rows | Necessary | Activity for a stated complete or explicitly sampled interval | Existing `catch_date`, `created_at`, query population | Same aggregation target | **Add** support information; selected rows must match the advertised window |
| Effort, including zero-catch trips and duration/gear exposure | Necessary for catch-per-effort; irrelevant to counting submitted reports | Productivity or catch-per-unit-effort | No standardized denominator in this aggregation; requires collection | Different target | **Add later** only if advancing to productivity; raw positive catch logs cannot supply the denominator |
| Seasonal baseline | Helpful for comparing activity across seasons; irrelevant to a single relative report snapshot | Seasonal anomaly or comparable longitudinal activity | Existing logs may eventually span seasons; real representative seasonal history not demonstrated | Different target for seasonal anomaly | **Add later** after specifying that target |
| Reporting-propensity/coverage correction; gear and vessel differences | Necessary for extrapolation to total fishing or fish availability; otherwise helpful context | Population-level activity or productivity | Vessel/log attributes partly exist; nonreporters and effort data incomplete | Different target | **Add later**; normalizing by report counts does not correct selective adoption, consent, connectivity or gear |
| Independent evaluation of the proposed planning use | Necessary to claim a planning benefit, not to compute counts | Evidence that report maps improve a specified planning decision | No independent operational evaluation located | Same reporting output, new downstream utility claim | **Add later** with a defined decision; do not substitute agreement with the aggregation formula |

#### Scale, geometry, leakage, and circularity findings

This is definitional aggregation: report coordinates and counts directly determine reported activity.
It does not require a causal relation between report density and fish abundance to be useful as a reporting map.
No predictive skill or causal effect on catch success is established.
Missing/suppressed/unreturned cells mean insufficient, excluded or lower-ranked reporting evidence, not zero fish or zero fishing.

The selected population is consenting, geolocated, received positive-catch logs, further truncated to 20,000 rows before capping repeated vessel contributions.
A prolific reporting vessel can therefore consume source rows and exclude other vessels/cells even though its score contribution is later capped.
The lower-date-only filter admits future dates and up to 31 calendar dates including today for the nominal 30-day setting (`hotspots.py:85-88`).
A server computation timestamp cannot resolve this event-time mismatch.
These are sample-definition errors for the stated aggregation, independent of any privacy judgment.

One eligible cell has normalized score `1` regardless of whether its reporter count is three or much larger.
An unchanged cell's score can fall when another cell gains reports.
Calling raw log count “independent observations” is also stronger than the data identity supports.
GPS acquisition at logging is measured, but its equivalence to the actual catch position is not established by the code; that distinction must be retained before using this map for fishing-location planning.

#### Highest-value correctness change

Define and enforce the selected reporting interval/population, including event-versus-log date and global truncation, so the claimed recent surface describes the rows actually counted.
This improves correctness for the same reporting-activity target; moving to fish productivity requires a different denominator and target.

#### Input to drop or replace

Replace raw `observations` as evidence of **independent** support with the honest interpretation “submitted reports,” alongside distinct reporting-vessel support if needed.
Do not drop consent or add catch weight as a surrogate for effort.

#### Minimum defensible input set

- Consented geolocated report rows and vessel identifiers: **already present and suitable** for report counting, conditional on record identity.
- Explicit report/catch location and time semantics: **already present but unsuitable or incomplete** for a true catch-location claim; narrowing to logging/report location is immediately defensible.
- A bounded, stated date population with known truncation: **already present but unsuitable or incomplete**; same target.
- Coarse cell geometry, distinct reporter threshold and relative count formula: **already present and suitable** as declared aggregation policies.
- Raw report counts labeled as raw, and relative scores labeled relative to the selected population: **requires a narrower or different target** only where language currently implies independent observations or fish abundance.
- Effort, seasonal/gear effects and nonreporter information: **requires new collection** only for the different productivity/population target; not minimum inputs for this reporting map.

#### Beyond the prior audit

The prior audit correctly treats this as consented activity aggregation rather than a fish-prediction model.
Additional data-fit findings are the missing upper date bound, calendar-window interpretation, row cap before per-vessel capping, relative-score denominator, independence wording, and logging-location versus catch-event-location distinction.
No additional data-fit finding beyond the audit on the mere absence of a learned model.

#### Honest output after fixes

“Coarse cells with relatively more consented, geolocated catch reports in the stated selected reporting interval; repeated reports and omitted cells do not establish independent catch evidence, fishing effort, fish abundance or future catch probability.”

#### Plan-ready findings

##### Finding CATCH-01: Report identity and location are stronger claims than the counted data support

- Severity: Medium
- Type: target mismatch
- Evidence: `backend/app/api/hotspots.py:28-58`; `mobile/lib/models/hotspot_cell.dart:29-36`; `mobile/lib/services/catch_service.dart:90-105`; `mobile/lib/ui/venture_page.dart:1240,2168`.
- Problem: Raw repeated logs are described as independent observations, and a logging-time GPS fix is not necessarily a catch-event location; relative score is not an absolute activity level.
- Recommendation: Describe report counts, location provenance and within-query relative activity explicitly; collect catch-event position only if the stronger spatial claim is required.
- Target effect: narrower target
- Expected benefit: Makes the map's count, location and score interpretation match the submitted data without inventing a fish target.
- Dependencies: Existing report fields; new event-location collection only for a stronger target.
- Verification evidence needed: Trace repeated same-vessel logs, a log made after returning ashore and an unchanged cell whose normalization denominator changes.
- Implementation planning note: Confirm intended reporting workflow and planning use before adding effort or environmental predictors.

##### Finding CATCH-02: The selected sample is not necessarily the advertised recent window

- Severity: Medium
- Type: provenance issue
- Evidence: `backend/app/api/hotspots.py:79-96`; `backend/app/api/catch.py:41`; `mobile/lib/services/catch_service.dart:90-100`.
- Problem: Future dates qualify, the inclusive day cutoff has an ambiguous 30-day meaning, and a 20,000-row global cap precedes distinct-vessel/capped-count calculations.
- Recommendation: Define a bounded event/report interval and whether the population is complete or truncated; ensure output meaning follows that selected population.
- Target effect: same target
- Expected benefit: Makes “recent activity” describe the dates and reporters actually represented rather than an unstated query sample.
- Dependencies: Existing dates and received rows.
- Verification evidence needed: Enumerate cutoff-day, today, future-date, delayed-upload and row-cap cases, including one prolific vessel displacing other cells.
- Implementation planning note: Set event-date versus logging-date semantics first; no fish-label collection is needed to correct this aggregation.

### Legacy current-weather advisory

#### Claimed output

This separately active deterministic rule maps one Open-Meteo `current_weather` response to `looksUnsafe` (`mobile/lib/models/weather_snapshot.dart:64-74`).
It produces “Wind above threshold” or “Conditions look calm” in `venture_page.dart:536-585` and a wind-above-threshold explanation in `weather_card.dart:219-240`.
The actual predicate is **wind speed above 30 km/h OR thunderstorm/severe thunderstorm/heavy rain/rain**.
Therefore rain with low wind can yield an objectively false wind explanation; no response also selects the wind-warning headline although its body admits missing weather.
The “calm” alternative is a stronger sea-condition claim than this atmospheric subset supports.
This is an immediate point-forecast category rule, not a forecast of a defined incident or a full go/no-go determination.
There is no training target or evaluation dataset.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `current_weather.windspeed` → `windSpeed` | Runtime input | `venture_feeds.dart:85-102`; `weather_snapshot.dart:27-49,65` | External current-weather product, not a local anemometer | Yes when fetched | Requested point/provider grid; actual resolution not retained | Loaded on initial/retry/refresh or location actions; no periodic weather timer identified; provider valid time discarded, source update cadence not stated | Keep | Relevant to a named wind threshold; insufficient to establish calm sea conditions |
| `current_weather.weathercode` → `weatherCode` → `condition` | Runtime input; derived feature | `weather_snapshot.dart:35-50,53,68-74,WeatherCondition.fromCode` | External category mapped to enum | Yes if response parses | Same atmospheric cell | Source time discarded | Keep but transform | Rain/storm can independently trigger the rule; unrecognized codes should not become calm and reasons must identify the actual predicate |
| `current_weather.temperature` → `temperature` | Runtime display input; parse requirement | `weather_snapshot.dart:34-46`; `venture_page.dart:573-576` | External product | Yes if response parses | Same grid | Same discarded valid time | Keep | Appropriate for a temperature display; no evidence or code path makes it a predictor of this rule's unsafe flag |
| Requested `lat`, `lon`, including default Aklan coordinates | Runtime/fallback support input | `venture_feeds.dart:85-93`; `home_page.dart:195-198`; `venture_page.dart:352-374`; `config.dart:87-88` | Device location or static fallback | Coordinates yes; current vessel representativeness not established | Handset/default point; no wave/current location | Fix age/cadence not retained in `WeatherSnapshot` | Keep but transform | Same location limitation as MOBILE-02; label the point represented rather than imply conditions around the hull |
| `unsafeWindKph=30`; listed adverse categories | Static parameter; policy target definition | `config.dart:unsafeWindKph`; `weather_snapshot.dart:64-74` | Human-selected thresholds | Yes | Uniform | Fixed | Keep | Defines selected atmospheric criteria, not empirically calibrated vessel safety |
| `weather==null` → `unsafe=true` in Venture; retained previous weather after failed Home refresh | Fallback input/state | `venture_page.dart:272-282,536-538`; `home_page.dart:190-211` | Missing response in Venture or earlier Home response | Yes as an information state, not adverse measured wind | Unknown/previous point | Previous data age absent in `WeatherSnapshot` | Replace | Missing weather cannot truthfully assert a wind threshold was exceeded; a retained response needs its source time |

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Trigger identity and unknown state | Necessary | Correct atmospheric threshold explanation | Existing wind/code/missing-response state | Narrows output to actual predicate | **Add**; no new environmental feature is needed to stop attributing rain or no data to high wind |
| Source valid time and represented location | Necessary for “current here” wording | Time/place-qualified atmospheric advisory | Provider response contains metadata; current object discards it | Same target | **Add**; a fetch success is not proof that a local measurement was taken now |
| Gust, waves and vessel exposure | Necessary for stronger sea/vessel-safety claim; irrelevant to a named current-wind/category rule | Full environmental or vessel assessment | Gust/waves available in separate forecast component; vessel exposure incomplete | Different target | **Add later** only if keeping broad “calm/safe” language; narrowing avoids duplicating another estimator |

#### Scale, geometry, leakage, and circularity findings

Wind and storm category have credible physical relevance, but no incident-prediction performance or causal effect is established.
The threshold rule only proves a defined category/number condition was met.
Different predicates are collapsed into one wind assertion, and a negative on this short list is not evidence of calm seas.
Fog/showers do not trigger the legacy predicate, even though the separate daily rule treats them as caution; this demonstrates different policy targets rather than two independent estimates of the same learned risk.
Unknown-category fallback and discarded valid time weaken the favorable output's meaning under degraded data.

#### Highest-value correctness change

Limit the output to the actual triggered atmospheric criterion, with an explicit unavailable state and stated time/location.
This narrows the target and corrects false factual explanations without introducing a new model.

#### Input to drop or replace

Replace the `weather==null → wind warning` interpretation.
Missing information is a reason to withhold assessment, not a measurement of high wind.

#### Minimum defensible input set

- Wind speed and recognized weather category: **already present and suitable** for their own explicit thresholds; preserve unknown categories.
- Which criterion triggered: **available from an existing source but not currently used** in the explanation.
- Source time/location: **available from an existing source but not currently used** in the current snapshot object.
- Broad “calm conditions” wording: **requires a narrower or different target**; replace with a statement about the checked atmospheric criteria, not sea or vessel safety.

#### Beyond the prior audit

This distinct active path is included because its physical assertion differs from both the daily risk rule and fishing-window logic.
The additional finding is a direct mismatch between the data predicate and the stated wind fact, including the missing-response branch.
It is not a UI-quality finding: the asserted environmental quantity is wrong for the input that triggered it.

#### Honest output after fixes

“At the stated forecast point and time, this wind or weather-category threshold is met; otherwise no listed atmospheric threshold was detected in the available data, which does not establish calm seas or safe passage.”

#### Plan-ready findings

##### Finding WEATHER-01: Rain or missing weather is stated as high wind

- Severity: Medium
- Type: target mismatch
- Evidence: `mobile/lib/models/weather_snapshot.dart:64-74`; `mobile/lib/ui/venture_page.dart:536-585`; `mobile/lib/ui/widgets/weather_card.dart:219-240`; `mobile/lib/services/venture_feeds.dart:85-102`.
- Problem: An OR rule covering several weather categories and a no-data fallback produces a specific wind claim; its negative implies broader calm conditions.
- Recommendation: State the actual criterion or unavailability, retaining valid-time/location support and narrowing the negative to the criteria assessed.
- Target effect: narrower target
- Expected benefit: Removes a factual input-output mismatch without claiming new safety-prediction skill.
- Dependencies: Existing wind/category/response metadata.
- Verification evidence needed: Trace low-wind rain, unknown weather code, missing response and genuinely above-threshold wind through both consumers.
- Implementation planning note: Follow both `looksUnsafe` consumers; decide whether this limited advisory remains distinct from the daily rule rather than adding another risk model.

### Buoy-current summary

#### Claimed output

This active descriptive statistic is shown alongside the human sea-condition declaration as “Buoy check: … m/s current” with an age (`mobile/lib/ui/widgets/sea_condition_banner.dart:98-104`).
`backend/app/api/sea_condition.py:35-65` selects the latest nonsynthetic current row per buoy, averages their speed magnitudes, assigns direction from summed vector components, and reports the newest observation time.
It is neither a learned model nor the source of the human declaration.
The honest object is a set of buoy samples, not one coherent current vector at the handset or throughout the municipality.
The time horizon is descriptive/latest-record, with no guaranteed maximum sample age.
There are no training inputs, learned labels or evaluation targets.

#### Input inventory

| Input | Role | Source and citation | Provenance | Available at decision time? | Spatial scale | Temporal scale | Verdict | Why |
| ----- | ---- | ------------------- | ---------- | --------------------------- | ------------- | -------------- | ------- | --- |
| `co.buoy_id`, `co.is_synthetic=FALSE` | Runtime selection inputs | `sea_condition.py:38-42` | Stored identifier and provenance flag | Yes for stored rows | All represented buoys; no geographical filter | Latest row per buoy | Keep but transform | Excludes explicitly synthetic rows, unlike the drift loader; a false flag alone is not evidence of physical sensor calibration or representative coverage |
| `observed_u_mps`, `observed_v_mps` | Runtime input | `sea_condition.py:39,49-58` | Stored values designated observed; actual sensor/depth calibration lineage not established by this query | Yes after receipt | Distinct buoy points; positions/depth not selected | Latest per buoy regardless of age; measured sampling cadence not stated | Keep but transform | Physically meaningful vector components if measured consistently; different locations/times cannot automatically form one local flow vector |
| `observed_at` for each row | Runtime support input | `sea_condition.py:39-42,59` | Stored observation timestamp | Yes | Per buoy before reduction | No maximum age or time-alignment filter | Keep but transform | Necessary to know whether samples represent the same current state; retaining only the newest hides old members |
| `speed=mean(hypot(u,v))`; `direction=atan2(sum(u),sum(v))` | Derived feature | `sea_condition.py:49-58` | Descriptive mathematical aggregation | Yes | Network sample set | Mixed latest-record times | Keep but transform | Mean scalar speed and mean-vector bearing are different summaries; combining them implies a vector whose magnitude generally differs from the actual vector mean |
| `buoy_count=len(rows)`, `observed_at=max(times)`, `source='buoy'`, rounding to 2/1 decimals | Derived feature; metadata/static presentation precision | `sea_condition.py:59-65`; `models/sea_condition.dart:128-151` | Query count, newest timestamp and source assertion | Yes | Entire selected set | Single newest time; handset sea-condition polling 18 seconds in `config.dart:72` | Keep but transform | Count is not calibrated spatial coverage; newest time is not freshness of every sample, and decimal precision is not measurement accuracy |
| Cached sea-condition response | Fallback input | `venture_feeds.dart:_cachedJson,seaCondition`; `sea_condition_banner.dart:98-104` | Earlier response | Yes if retained | Previous selected set | Original payload observation time survives; aggregate sample-age span still absent | Keep but transform | Historical descriptive value can remain useful if identified as such; polling cannot freshen the underlying observations |

Human `status`, `reason` and author/time fields accompany this telemetry but do not enter its current computation.
No claim is made here about whether the human declaration was correct.

#### Missing decision-critical inputs

| Missing input | Necessary / helpful / irrelevant | Which claim it would enable | Available today? | Same target or target change? | Reason |
| ------------- | -------------------------------- | --------------------------- | ---------------- | ----------------------------- | ------ |
| Per-sample age/time range and locations | Necessary | A descriptive current summary with stated sampled support | Observation times exist; buoy coordinates exist elsewhere in repository | Same descriptive target | **Add**; newest-only age and all-buoy aggregation conceal stale/nonlocal contributions |
| Measurement depth, instrument/method and calibration meaning of `u,v` | Necessary for a measured physical-current assertion | Comparable current observations | No complete field lineage demonstrated by this path; hardware/operational source needed | Same quantity | **Add**; an “observed” column name cannot establish depth or accuracy |
| Intended scalar versus vector statistic and cancellation handling | Necessary | A mathematically coherent magnitude/direction description | Existing vector components | Same target if scalar summary retained; narrower local-flow claim | **Add** explicit statistic meaning; opposing currents make direction undefined while mean speed remains positive |
| Handset/object location | Irrelevant for a clearly labeled network sample summary; necessary for a local-current claim | Current near the specific vessel | Device location exists elsewhere | Different spatial target | **Add later** only if localization is intended; a network average cannot replace local flow estimation |

#### Scale, geometry, leakage, and circularity findings

This statistic directly measures properties of its selected rows if the rows truly are comparable observations.
No predictive usefulness or causal effect is established or needed for that descriptive target.
The repository does not establish that these rows are calibrated local surface-current observations from deployed hardware.

Spatially opposing or temporally offset flows can be averaged together without an explicit domain or synchronization rule.
For two samples `(u,v)=(1,0)` and `(-1,0)`, mean speed is `1 m/s` while the vector sum is zero; the formula still supplies a numerical north bearing from `atan2(0,0)`.
The public response thus cannot be interpreted as a physically coherent network-mean velocity with that speed and direction.
The handset currently displays speed and newest age, not direction, so the age/support ambiguity is the direct user-visible finding; vector incoherence also affects the API quantity a responder could consume.
One recently reporting buoy can make a summary containing arbitrarily older samples appear recent.

#### Highest-value correctness change

State and preserve the statistic's spatial/temporal sample support instead of presenting the newest timestamp as freshness of the complete aggregate.
This improves the same descriptive target and narrows any local-current interpretation.

#### Input to drop or replace

Replace `max(observed_at)` as the sole age of the aggregate.
No physical current component should be dropped merely because it is negative; cancellation is meaningful.

#### Minimum defensible input set

- Comparable `u,v` samples with verified measurement meaning: **already present but unsuitable or incomplete** because field provenance/depth/calibration is not demonstrated.
- Per-sample times and buoy locations: **available from an existing source but not currently used** fully in this summary.
- Explicit scalar-speed or vector-mean definition: **requires a narrower or different target** where the existing pair is read as one current vector.
- Full sample-age/support description: **already present but unsuitable or incomplete** after newest-only reduction.
- Local handset current: **requires a narrower or different target**; stay with a network sample summary unless a local estimation target is chosen.

#### Beyond the prior audit

This adds an active AI-adjacent statistic whose apparent currentness and spatial meaning can affect environmental interpretation.
The verified nonsynthetic filter qualifies the drift finding: this endpoint does filter synthetic rows, so the drift loader's provenance defect must not be generalized to every current consumer.
The new findings concern mixed sample times, scalar/vector meaning and newest-only age.

#### Honest output after fixes

“A descriptive summary of the stated, time-qualified buoy current samples over the stated area; it is not the current at your boat, and sample speed, vector direction and observation age have the explicitly identified meanings.”

#### Plan-ready findings

##### Finding CURRENT-01: One newest timestamp hides mixed-time, mixed-location currents

- Severity: Medium
- Type: scale mismatch
- Evidence: `backend/app/api/sea_condition.py:35-65`; `backend/app/api/public.py:public_sea_condition`; `mobile/lib/ui/widgets/sea_condition_banner.dart:98-104`.
- Problem: Latest samples of unrestricted age/location are summarized with the newest time; scalar mean speed and summed-vector bearing do not necessarily describe one velocity.
- Recommendation: Define the sampled domain/time support and scalar/vector statistic explicitly, preserving measurement provenance and undefined-direction cases.
- Target effect: narrower target
- Expected benefit: Prevents a descriptive network statistic from implying a fresh coherent local current.
- Dependencies: Existing times, buoy coordinates and components; hardware provenance/calibration for a stronger measured-current claim.
- Verification evidence needed: Inspect one new and one old sample plus equal/opposite vectors, and establish the instrument/depth meaning of one real row.
- Implementation planning note: Confirm whether consumers need a scalar network summary or local current; do not introduce a spatial prediction model for a descriptive-only requirement.

## Cross-component conclusion

| Component | Actual output type | Output claimed | Right inputs? yes / mostly / no | Top add | Top drop or replace | Target change required? | Honest claim after fixes |
| --------- | ------------------ | -------------- | ------------------------------- | ------- | ------------------- | ----------------------- | ------------------------ |
| Squall nowcasting | Classifier/rule pressure-pattern score and conditional front projection | Local squall early warning and arrival | no | Independent location/time-specific wind-onset labels | Pre-event synthetic target; zero `mean_deviation` | Yes: narrow now; independently define intended squall target for later prediction | Pressure-pattern candidate and conditional arrival fit; no established calibrated squall probability |
| Trip anomaly and overdue detection | Profile-based contact-gap score | Anomalous/non-returning vessel needing review | no | Confirmed trip state and expected communication opportunity | Synthetic weather and fleet route as personal expectation | Yes: narrow to missed expected contact unless distress outcomes are established | Vessel missed an explicit expected contact; cause and distress remain unconfirmed |
| Drift prediction | Conditional terminal particle simulation | Real-input search distribution and nominal containment | no | Correct datum and whole-horizon real environmental support | Synthetic current substitution in real-case field | Narrow until source, geometry and independent containment evidence support more | Conditional object-location simulation over stated supported times and assumptions |
| Bayesian search re-tasking | Likelihood reweighting and maximum-cell ranking | Updated target probability and recommended next search area | mostly | Search interval, effective footprint and supported detection likelihood | Unqualified uniform `.3/.6/.9` detection presets | Yes: static conditional ranking unless time alignment/performance supported | Remaining mass under stated prior and no-detection assumptions, not optimal rescue tasking |
| Marine hazard or danger zone | Proxy classifier with overriding threshold tiers | Local hazard tiers and percentage risk | no | One defined environmental target and actual source cell/time support | Global buoy-health severity adjustment | Yes: narrow to explicit environmental threshold tier | Regional forecast thresholds and context, not casualty probability or measured fine-scale danger |
| Mobile risk score | Daily deterministic threshold class/severity index | Safe/caution/danger forecast guidance | mostly | Per-variable completeness and valid location/time | Mean wind as gust; fair-weather defaults | Yes: narrow favorable tier to checked environmental evidence | Listed daily forecast thresholds, with missing evidence explicit; not vessel safety probability |
| Fishing window | Threshold-crossing time guidance | Time until fishing weather worsens | mostly | Complete current/intervening support and variable-specific timing | Universal one-hour atmospheric onset shift | Narrow timing/current language; retain weather-only target | Conditional forecast threshold timing; excludes return duration and safe time remaining at sea |
| Consent-based catch-activity surface | Relative selected-report aggregation | Recent coarse catch activity | mostly | Bounded date/population and report-location meaning | Raw reports as independent evidence | Clarify/narrow only; productivity would be a different target | Relative consenting report activity, not fish abundance, effort or catch probability |
| Legacy current-weather advisory | Current atmospheric OR rule | High wind or calm conditions | no | Actual trigger and source valid time | Missing/rain response interpreted as wind excess | Yes: narrow to actual atmospheric predicate | Specified atmospheric threshold met or unavailable; no sea-safety conclusion |
| Buoy-current summary | Mixed-sample descriptive statistic | Buoy current with a recent age | mostly | Sample age/location/depth support | Newest time as entire aggregate freshness | Yes: explicit scalar/network summary | Time-qualified current sample statistics, not a fresh local flow vector |

## Prioritized planning handoff

Priorities reflect the truthfulness and physical consequence of the current output claim, not implementation convenience.
Each row refers to the full finding above, including its dependencies and minimum evidence.
Within a component, define the target and source support before collecting optional predictors; an independent outcome dataset is necessary for a stronger empirical claim, not for every transparent rule or aggregation.
Optional additions in the missing-input tables are conditional investigations under the corresponding findings, not a mandate to build every listed data source.
No implementation or release decision is made by this report.

| Priority | Finding ID | Component | Short problem | Recommended change | Target effect | Evidence required before implementation |
| -------- | ---------- | --------- | ------------- | ------------------ | ------------- | --------------------------------------- |
| 1 | DRIFT-01 | Drift | Real-input claim includes synthetic/unsupported current | Establish source-separated, decision-time and whole-run support; restrict unsupported horizons | Same target, conditional restriction | One real/synthetic mixed-source lineage trace and per-step support accounting |
| 2 | DRIFT-02 | Drift | Receipt time and last contact are not the physical drift datum | Establish fix time/uncertainty and drift-start scenario | Same target | Trace delayed SOS origin, fix and receipt times and one anomaly-contact scenario |
| 3 | SQUALL-01 | Squall | Positive windows precede all pressure signal from their event | Define independent local wind onset/cutoff; narrow to pressure patterns until supported | Different training target; narrower interim claim | Symbolic or minimal event-timeline check plus a concrete field label definition |
| 4 | SEARCH-01 | Bayesian re-tasking | Search evidence and target distribution refer to different times | Establish search interval and matching distribution, or restrict to static hypothetical update | Same target; narrower interim claim | One moving-target search timeline with original grid time and rerun behavior |
| 5 | DRIFT-03 | Drift | Wind validity and nearshore geometry do not support full horizon | Establish source temporal support, time zone and water-connected domain | Same target; narrower supported domain | Old-datum forecast coverage and representative coast/channel crossing cases |
| 6 | MOBILE-01 | Mobile risk | Missing/differently defined values can produce Safe | Preserve unknowns and variable identity; define minimum favorable-tier inputs | Narrower target | Rain-only, absent-code, absent-gust and partial-wave examples |
| 7 | WINDOW-01 | Fishing window | Countdown can ignore missing present conditions | Require supported current and intervening conditions | Same target | Incomplete present interval followed by complete future threshold event |
| 8 | TRIP-01 | Trip anomaly | Silence is treated as non-return/open-trip state | Establish closed/open state and explicit communication expectations | Narrower target | Completed-return and genuine ongoing-trip timelines with coverage opportunity |
| 9 | SQUALL-03 | Squall | Arrival origin discards fitted timing | Preserve corresponding spatial/time origin and suppress invented arrivals | Same target | Perfect planar-front example including intercept and no-projection case |
| 10 | SQUALL-02 | Squall | Displayed score differs from evaluated probability | Define pressure-rule score and evaluate the actual target/decision path | Narrower target | Classifier, rule maximum and deployed cutoff compared on identical examples |
| 11 | HAZARD-01 | Danger zone | OR-trained event and AND danger tier are different | Select one explicit environmental output target; separate percentage meanings | Narrower target | Single-condition and combined-condition label/score/tier comparison |
| 12 | SEARCH-02 | Bayesian re-tasking | Rectangle/preset do not establish actual detection likelihood | Identify effective search footprint and conditional detection evidence; qualify ranking | Narrower target until likelihood supported | Track spacing, method/object visibility and dependent-repeat examples |
| 13 | DRIFT-04 | Drift | Synthetic containment and centroid baseline overstate evidence | Use prespecified horizons, truthful baseline and independent drift observations | Same target | Independent track protocol and calculation of existing baseline's actual quantity |
| 14 | TRIP-02 | Trip anomaly | Candidate/future history and mismatched leg semantics define baseline | Use prior normal histories and physically matched interval definitions | Same target | Repeated-buoy route and historical replay with only then-available trips |
| 15 | HAZARD-03 | Danger zone | Fine sector footprints lack equivalent data support | Retain actual cell/model/valid-time domain and qualify product transfer | Narrower target | Returned cells/times for eight requests and committed artifact lineage |
| 16 | MOBILE-02 | Mobile risk / fishing window | Cached point and retrieval age do not identify current vessel forecast | Preserve location age and returned grid/valid-time provenance | Narrower target | Stale-fix, default-point and nearshore marine response trace |
| 17 | WINDOW-02 | Fishing window | Instantaneous and daily inputs receive unsupported onset times | Match timing language to variable aggregation periods | Narrower target | Source definitions and wind/gust/wave/category/daily-rain timeline examples |
| 18 | WEATHER-01 | Legacy weather | Rain or no data is reported as wind excess | Explain actual predicate, unknown state and source time | Narrower target | Both consumers with low-wind rain, no response and actual high wind |
| 19 | CURRENT-01 | Buoy-current summary | Newest-only age conceals stale/nonlocal sample mixture | Define sample support and scalar/vector meaning | Narrower target | Mixed-age and opposing-current examples plus one field measurement lineage |
| 20 | TRIP-03 | Trip anomaly | Invented weather and reference distance imply real exposure | Remove synthetic operational weather; name distance and location uncertainty honestly | Narrower target | Actual scorer dependency and maximum-reference-distance calculation |
| 21 | HAZARD-02 | Danger zone | Communication health and unused depth imply physical hazard | Remove unsupported severity increment and attribution | Same target | Fixed-weather/unrelated-buoy counterexample and artifact depth split count |
| 22 | CATCH-02 | Catch activity | Date bounds/global truncation change advertised population | State and bound recent report population and truncation | Same target | Cutoff/future/delayed dates and pre-cap sample displacement |
| 23 | CATCH-01 | Catch activity | Logging positions and repeated counts overstate catch evidence | State report-location, raw-count and relative-score meaning | Narrower target | Logging workflow, repeated-vessel rows and changed normalization denominator |
