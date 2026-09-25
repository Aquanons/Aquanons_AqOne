# Implementation Plan: AqOne Before, During, and After Safety Intelligence

> **Status:** SUPERSEDED (header corrected 2026-09-25). Phases 1 to 5 were executed and committed (`0f880a4`, `cd1d1c8`, `759587a`, `fa4f74e`, then Phase 5 in `docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`; see the phase table near the end). The post-execution re-audit (`docs/audits/AI_LAYER_DATA_CORRECTNESS_REAUDIT_2026-09-15.md`) did not uphold the completion claims, and the follow-up work moved to `docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md`. The earlier header line "Planning complete; no implementation phase started" described the plan before execution.  
> **Target Branch:** Proposed `codex/ai-accuracy`; create only when execution is authorized, after inspecting existing changes.  
> **Test Command:** Backend: `python -m pytest -q` from `backend`; mobile: `flutter test` from `mobile`; web: `node --test web/test/*.test.js` from the repository root.  
> **Lint/Check Command:** Backend: `python -m ruff check .`; mobile: `flutter analyze`; web: `node --check` for changed JavaScript; documentation: `git diff --check`.  
> **Prepared:** 2026-09-15.  
> **Evidence revision:** `e1e3904a8ff55ec858805ec2de1d2f87ae92cb16`, branch `codex/ai-layer-audit`, with the existing README clarification and audit reports present in the working tree.

---

## Overview

Build evidence that AqOne can warn fishermen already at sea, identify missed expected contacts or returns for verification, and provide a physically supported search distribution when a person or vessel may be missing.
Retain the existing communications, backend, mobile, statistical and simulation foundations while correcting their inputs and targets, collecting real measurements through controlled field work, and validating the complete service on independent events.
The sequence is driven by evidence, not a competition deadline; no phase is complete merely because software runs, funding is exhausted, or a planned date arrives.

The immediate next step is **Phase 1: agree the target and operating domain, establish an honest baseline, and correct demonstrated data errors before retraining**.
In parallel with planning those corrections, prepare the Phase 2 measurement and communications protocol so funding buys interpretable data.
This does not authorize executing multiple phases concurrently or bypassing the repository build order.

### What this plan changes about the storyline

The three-stage goal is appropriate, but it does not require three supervised machine-learning models.
The system must observe and communicate the facts that make each stage possible.

| Stage | Physical or operational target | Initial defensible method | Stronger capability earned through evidence |
| --- | --- | --- | --- |
| Before hazardous conditions arrive | Hazardous wind/wave conditions at a specified location and future time; a warning received early enough to support an appropriate response | Forecast and observation thresholds, applicable official warnings, and a separately labeled pressure-pattern detector | Locally calibrated forecast probabilities and independently validated squall prediction with measured delivered lead time |
| During the trip and weather response | An explicitly open trip misses an agreed contact/return expectation; whether return or current welfare has been confirmed | Explicit trip/contact states, agreed deadlines, receiver coverage evidence and chronological personal interval statistics | Better calibrated contact/return timing; a distress probability only if independently confirmed incident/non-incident data support that different target |
| After a possible disappearance or distress report | Location of a stated drifting object at a stated time, conditional on uncertain starting state and environmental inputs | Physics ensemble with suitable currents, wind, leeway and shoreline behavior | Field-calibrated containment and bias correction; time-aligned search updates based on measured detection performance |

“Safe” is not an inferred permanent property of a fisherman.
Use “return confirmed at [time],” “fisher reported safe at [time],” “contact overdue,” “communication unavailable,” and “unaccounted for, verification pending” for the evidence actually available.
A return-home instruction also needs an applicable operational policy: the route home may itself become hazardous, and the available warning time may be shorter than the journey.
Until that policy and its required information are established, issue the verified hazard and applicable MDRRMO instruction without inventing a safe route or deadline.

### Authorization, existing plans, and execution boundaries

- The user requested a full council-backed plan, not implementation, deployment, training runs, database mutation, hardware purchases, or messages to external parties.
- This is a separate accuracy workstream linked from the existing root `IMPLEMENTATION_PLAN.md`; that fishing-window plan remains historical task context and is not silently overwritten.
- Read `AGENTS.md`, `docs/00_START_HERE.md`, the current PRD at `docs/Aqone_PRD (2).md`, and the shared contracts before execution.
  The older fishing-window plan's feature-specific build-order exception does not authorize this workstream to skip hardware prerequisites.
- Reverify the sequential foundation: deployed health/migrations, two-radio raw link, buoy-to-backend SOS, airplane-mode phone-to-backend SOS, persistent dashboard acknowledgment, measured outdoor range, and recorded rehearsal evidence.
  If any required preceding step lacks evidence, resolve it or obtain an explicit applicable exception before starting later implementation; planning and read-only investigation can continue.
- `docs/08_DEMO_AND_STATUS.md` has September 13-14 software verification entries but also older placeholder tables.
  Neither those entries nor a compile result demonstrates at-sea radio coverage, usable sensor data, or current deployment health.
- Change shared contracts before producers/consumers when this plan introduces warning, observation, trip, or search semantics.
  Record the affected workstreams for Lenard, Arnold, Daniel, Jade and Doreen Kay to review; this plan sends no messages to them.
- Follow the invoked implementation-plan lifecycle for each phase: execute, verify, Ponytail review, atomic phase commit, then explicit user sign-off before the next phase.
  A failed statistical or field gate is an incomplete phase, not permission to weaken acceptance criteria.
- Do not run the destructive simulation generator against operational or field data.
  Existing evaluation entry points also write result artifacts or operational state; inspect them and use a dedicated evaluation dataset/database during future execution.

## Council Deliberation: Accuracy for the offshore storyline

### 1. Grounding

**Observed facts**

- The [data correctness audit](audits/AI_LAYER_DATA_CORRECTNESS_AUDIT_2026-09-14.md) contains 23 actionable findings across ten active components.
  Its substantive findings and their current source paths inform this plan; it is not a substitute for reproducing the defects before changing code.
- `squall.py:_samples_from_rows` labels positive feature windows before their own synthetic event contributes pressure in `generator.py:_event_pressure_at`.
  The live maximum of classifier and rule score is not what classifier-only evaluation measures.
- `anomaly_service.py:evaluate_and_persist` builds the baseline from loaded contacts and supplies no real weather provider to `score_trip`.
  Last-contact age is used as a trip-state proxy; routine trip return is not established by that value.
- `current_field.py:_load_buoy_observations` does not separate synthetic observations or decision-time availability; its factory substitutes synthetic currents and reports only the most recent step's observed fraction.
- `api/drift.py:_sos_case_inputs` uses SOS receipt time as a physical datum time.
  Real search cases already require an acknowledged SOS or escalated anomaly and a responder-selected object class.
  Preserve these human review boundaries.
- Current firmware has chat and SOS ETA downlink: shore `pollChat`/`pollAcks`, `T_CHAT`/`T_ETA`, and buoy `onMeshFrame`.
  The old “no return path” documentation is stale, but no complete structured weather-warning lifecycle is demonstrated by those paths.
  Phones still need a local WiFi opportunity; LoRa between buoys does not make a normal phone a LoRa receiver.
- The inspected active firmware does not establish calibrated pressure, wind or water-current sensor production.
  An optional buoy IMU does not measure those quantities or automatically provide a calibrated wave-height estimate.
- Marine hazard is trained on historical environmental proxy data; squall training and much trip/drift evidence are synthetic; daily risk/window rules and catch aggregation are not trained models.
  “Train everything on real data” is therefore not a complete technical plan.

**Unverified assumptions**

- Available instruments, their calibration, mounting, power/storage budgets, local bathymetric accuracy, provider access and nearshore forecast suitability.
- Real WiFi contact footprints, association delays, background-app behavior, mesh warning latency and weather-warning notice/comprehension at sea.
- The operating area, boat classes, useful warning deadline, route/shelter policies, acceptable false-alert workload and desired containment/area tradeoff.
- Historical local squall/incident labels, seasonal coverage, independent drifter tracks, and local responder detection performance.
- Any institutional partnership, field permission, funding amount, or operational endorsement; none is claimed by this plan.

### 2. Perspectives & Debate

- **Devil's Advocate:** Warning creation, warning receipt and appropriate action are different successes.
  Contact loss has multiple benign explanations, and last contact does not identify the onset of free drift.
  Evaluate complete event timelines, including no communication opportunity, rather than only the model's successful cases.
- **Simplicity Champion:** Retain explicit environmental rules, trip/return evidence, physics ensembles and Bayesian updates where each fits its target.
  Reuse existing clocks, providers, schemas and tests; add model complexity only when an independent comparison demonstrates useful improvement.
  Physical uncertainty, coastline boundaries and data provenance are necessary detail, not removable complexity.
- **Security & Reliability Auditor:** A `live` flag or plausible timestamp is not proof of a calibrated measurement.
  Warning expiry, clock uncertainty, durable evidence and actual recipient reach need end-to-end verification.
  Unknown environmental or communication states must not become reassuring output or erase an unresolved rescue case.
- **Architecture / DX:** Maintain one traceable event history and explicit source/time definitions across the existing ingestion, inference and presentation paths.
  Separate data collection, model selection and operational promotion so a newly collected dataset cannot automatically enable a public warning.
  Preserve existing service boundaries and share concrete data semantics rather than introducing a generic AI platform.

### 3. Consensus vs. Tension

All seats agree that source correctness, target definition and independent field evidence precede claims of improved accuracy.
The first disagreement to resolve is whether the service covers only measured buoy-contact opportunities or needs a carried vessel receiver to cover the full fishing area.
The second is whether “return now” is a geographically applicable human instruction or an automatic route-specific recommendation; the latter needs vessel, route, shelter and timing inputs.
The third is how to use uncertain search performance: retain an unmodified prior and display completed search tracks when no quantitative likelihood is justified, rather than treating an unknown detection probability as a measured zero or choosing a convenient preset.
No seat recommends treating missing data as safety, or synthetic self-consistency as field validation.

### 4. The Verdict (Pragmatic Action)

**Recommended path:** Follow the five phases below, starting with correct semantics and reproducible counterexamples, then instrumented collection, before/during model validation, drift/search validation, and prospective integrated evaluation.
**Revisit when:** Measured communication gaps make useful warning impossible, independent weather evidence shows pressure adds no useful lead, real timing data defeats personal profiles, or validated drift residuals justify a stronger environmental model or estimator.
Those results can change the hardware, feature set or algorithm; they must not be hidden by changing the label after seeing the outcome.

## Decision register and target contracts

These decisions have recommended defaults for investigation, an owner of the evidence decision, and a point at which they must be resolved.
An executing agent must not invent institutional approval or treat an unanswered choice as authorization for operational use.

| ID | Decision and recommended starting position | Evidence/decision participants | Required before |
| --- | --- | --- | --- |
| D1 | Survey a specific New Washington fishing/return area, boat classes, seasons and named shelter/landing locations; make no municipality-wide coverage claim from a few sensors | Fisher representatives, MDRRMO, field lead | Field layout and sampling plan |
| D2 | Start with the existing phone/WiFi/buoy/LoRa path; if measured contact gaps exceed the warning budget, compare a carried LoRa-to-phone bridge or another supported receiver with a narrower service domain | Daniel/Arnold, mobile lead, fishers, responder lead | Hardware purchase and warning-service claim |
| D3 | Define one wind-onset label and separate wind/wave hazard thresholds; retain current app thresholds as provisional only | Meteorological adviser, MDRRMO, fishers familiar with local boat classes | Training labels and threshold selection |
| D4 | Treat automatic weather output as advisory pending a documented actionable-warning policy; do not infer that returning home is always the safest movement | MDRRMO and relevant weather/maritime advisers | Public action wording and alert activation |
| D5 | Use explicit trip/check-in/return expectations and time-stamped confirmation; allow an already-at-sea trip with unknown departure time | Fishers, MDRRMO, mobile/backend leads | Trip lifecycle implementation |
| D6 | Preserve responder authorization for drift scenarios; show pre-distress motion/start-time uncertainty and distinct person/hull cases when necessary | SAR practitioner, backend lead | Real incident inference |
| D7 | Compare corrected AqOne drift with a documented reference implementation before choosing to extend or replace it | Oceanographic/SAR adviser, backend lead | Major drift-engine changes |
| D8 | Freeze acceptable misses, false reviews, delivered lead, abstention and area/containment bounds using the operating domain; select sample sizes from those bounds | MDRRMO, field/statistical lead, fishers for warning burden | Collection acceptance protocol and untouched final test |
| D9 | Define drill-stop/recovery conditions and consented recording; observe dangerous weather remotely/passively and use recoverable surrogate drift targets | Qualified field lead and relevant local authorities | Any field exercise |

### Proposed before/during/after evaluation definitions

**Before:** For each qualified location and decision time `t`, predict whether an independently observed hazardous event starts in `(t,t+H]`.
Use separately scored 30-, 60- and 90-minute horizons as initial candidates because the current model already claims those leads; D3/D8 may narrow or change them before the dataset is frozen.
Keep currently ongoing hazard detection separate from future-onset prediction.
A squall label should use measured wind onset/severity plus independent review; NOAA's glossary defines a wind-based squall, not a pressure rule ([NOAA definition](https://forecast.weather.gov/glossary.php?word=SQUALL)).
Document the adopted averaging interval, onset, end, separation of events and location tolerance; this source is a meteorological reference, not a local small-boat safety limit.

Measure usable action time as `hazard_onset - warning_received - notice/preparation_time - required_travel_or_shelter_time`, with uncertainty in every term that is estimated.
If only receipt and onset are known, report delivered warning lead and explicitly omit an actionable return-time claim.
An upstream sensor distance is useful only if front travel time leaves enough allowance for detection and communication; select array geometry from observed passages and target lead, not “three sensors is enough.”

**During:** At `t`, identify an open trip with an outstanding expected contact or return by a defined deadline.
Assess known contact opportunities and outages, while treating an absolute missed return expectation as actionable uncertainty even when communication failed.
Do not suppress review of every missing vessel merely because a storm also broke the gateway.
Keep an outcome of unknown/unresolved; silence or lack of a rescue report is not a negative distress label.
Evaluate a confirmed-distress predictor separately only when its labeled positives and benign alternatives exist.

**After:** At a recorded issue time, forecast object position at prespecified horizons from a physical datum, distinguishing reconstruction up to issue time from future motion.
Use candidate horizons of 1, 3, 6, 12 and 24 hours, and evaluate 48/72 hours only when environmental support and independent tracks cover them.
These are experiment horizons, not promised model skill.
Do not change the evaluated horizon after seeing when a target beaches, leaves the area or becomes unobserved.

**Search:** Condition the position distribution on an actual search interval, swept footprint, object and justified no-detection likelihood, then advance that evidence to the next decision time.
The largest remaining cell is descriptive ranking; optimal deployment requires reachability, effort and detection-success data in addition to location probability.

## Shared evidence and field-data design

### Minimum observation and decision record

Use existing source records where possible and add only fields needed to reconstruct what the system knew and what the measurement represents.
The following are semantic requirements, not a mandate for one universal table or a new data platform.

| Record | Required meaning/fields | Existing starting point | Collection/use rule |
| --- | --- | --- | --- |
| Physical observation | Event ID, source/instrument ID, variable, value/unit, measurement method, calibration reference, position/uncertainty, height/depth where relevant, observation time and clock uncertainty, receipt time, quality, provenance | Pressure/contact ingestion and `current_observations`; actual current producer needs commissioning | Store late observations with original time; do not make them fresh at receipt |
| Forecast issue | Provider/product/model version where exposed, issue time or explicit unknown, retrieval time, valid time/interval, requested and returned cells, resolution/support, units, revision | `api/public.py`, `forecast_provider.dart`, wind provider | Archive what was actually available; a reanalysis downloaded later is a separate source |
| Trip evidence | Vessel and trip IDs, observation source, trip start known/unknown, intended contact/return condition, changes acknowledged when possible, contacts, return/welfare confirmation, outcome certainty | `buoy_contacts`, anomaly cases, SOS replies/resolutions | Never use an incident closure note automatically as a confirmed normal trip or verified medical/survival outcome |
| Warning | Stable ID/version, source/authority, issue/effective/expiry times, geographic applicability, severity/action code, qualified evidence reference, cancellation/supersession | Existing downlink mechanics, public squall/advisory outputs | Track created, queued, gateway/buoy/handset receipt and optional user acknowledgment separately |
| Drift run | Case/run ID, issue time, datum/fix/source times, initial uncertainty, object/start scenario, input identities/time support, parameter/model version, target valid time, probability/support semantics | Existing `incidents`, `drift_runs`, `api/drift.py` | A changed datum or environment creates a traceable new run; old outputs remain reproducible |
| Search observation | Case, search start/end, actual track/footprint, search asset/method, visibility/object class, detection assumption/source, result, reporter and evidence ID | `search_sector_reports` and protected search route | Do not multiply duplicate or dependent negative evidence as independent searches |
| Outcome/label | Target definition/version, event or trip/deployment ID, observed position/time or onset/result, observation uncertainty, reviewer/source, certainty/unresolved flag | Existing event/case fields plus a small versioned label set | Labels are separately adjudicated; model score must not define its own truth |

Store raw reference data and detailed private tracks in an access-controlled project dataset, not the public repository.
Keep a versioned manifest containing source identity, units, date/domain coverage, consent/use conditions where applicable, quality exclusions, immutable file hashes, split membership and label version.
The plan requires data separation because drills, ordinary trips and synthetic cases have different meanings; it does not require three separate storage platforms.

### Field measurements and commissioning

All cadences below are **proposed pilot acquisition settings**, not measured present capabilities or a substitute for instrument-specific qualification.
Store raw measurements locally at the instrument/reference logger where feasible; select radio summaries after measuring the airtime, energy and outage budgets.
Fast local recording and reliable lower-rate transport are different requirements.

| Measurement/work package | Proposed acquisition and spatial design | Calibration/qualification | What it enables |
| --- | --- | --- | --- |
| Pressure plus independent wind | Pilot pressure records at least once per minute; wind raw acquisition at least 1 Hz or faster if the chosen sensor needs it, retaining defined gust and sustained averages; surveyed upstream/downstream array and an independent reference | Side-by-side offsets, exposure/mounting, clock alignment, salt/water protection, temperature effects, sensor response and maintenance checks; freeze final cadence after signal/aliasing analysis | Actual pressure predictors and independently timed wind labels; a five-minute pressure sample cannot serve as one-minute wind ground truth |
| Waves | Reference wave instrument or independently calibrated buoy-motion processing; retain burst spectrum/height/period and interval support | Compare against a reference under multiple sea states; determine raw sampling and burst duration from the instrument and wave bandwidth rather than guessing | Local significant-wave error and risk-threshold validation; IMU motion alone is not a wave-height label |
| Currents, tide and depth | Calibrated vector current meter/ADCP at documented relevant depths; continuous or burst raw logging with candidate one-minute summaries; tide/water-level reference and suitable bathymetry | True north/component convention, magnetic correction if relevant, mounting motion, depth/shear, tidal phase, instrument bias and comparison with a second/reference observation | Object-representative advection and local nearshore flow; tide height alone is not horizontal current |
| Position and communications | Reference GNSS on consenting vessels and recoverable targets; candidate 1-5-second local tracks, with separately measured transmitted contact cadence | Fix age/accuracy, antenna/motion, clock/reboot behavior; record association attempts and failed opportunities as well as successful packets | Honest contact coverage, datum uncertainty and independent trajectory outcomes |
| Boat/trip context | Record vessel class/size and relevant loading/immersion; voluntary expected return/check-in; start/return and plan-change confirmations | Review meaning with fishers; distinguish expected and actual values, late-but-safe and unresolved outcomes | Route/boat-specific timing, action feasibility and drift-object choice |
| Search trials | Known recoverable target location, blinded search crew when appropriate, actual search tracks/time, object visibility, sensor/method, conditions, hits and misses | Independent truth custodian; preplanned recovery and search pattern; record negative trials without selectively discarding them | Object/method-conditioned detection probability and repeated-search dependence |

Use the WMO observation guidance to design instrument documentation, quality control and comparison procedures; the existence of an instrument or a manufacturer accuracy number is not local qualification ([WMO IMOP](https://wmo.int/activities/instruments-and-methods-of-observation-programme-imop/instruments-and-methods-of-observation-programme)).
A leeway field study can directly measure object motion relative to water using an attached current meter; select the appropriate method with an oceanographic adviser rather than estimating a banca coefficient from unrelated objects ([Breivik et al., leeway field method](https://arxiv.org/abs/1111.0750)).

### Source acquisition and funding sequence

1. Fund the definition and measurement layer first: field coordination, calibrated reference instruments, surveyed geometry, GNSS truth logging, power/storage, maintenance and actual radio coverage trials.
2. Establish external data access and local suitability: PAGASA observations/warnings, available radar/lightning/satellite products, appropriate NAMRIA charts/tidal data, and forecast-as-issued wind/wave/current products.
3. Fund ordinary-trip collection, independent label review and controlled drifter/search exercises, including recovery and repeat measurements across relevant conditions.
4. Train/calibrate on qualified development data and pay for independent evaluation on different events/deployments.
5. Expand sensing or model complexity only when error analysis shows what missing information limits the target.

PAGASA provides a formal climate-data request route, and NAMRIA lists nautical, tidal and current-related products; neither listing establishes a connected live API or usable New Washington resolution ([PAGASA data requests](https://www.pagasa.dost.gov.ph/climate/climate-data), [NAMRIA products](https://namria.gov.ph/kiosk/namria02.htm)).
For every candidate product, record access terms, historical issue availability, returned grid, actual cadence, latency, tides/waves included, valid depth and local comparison results before using it operationally.
Open-Meteo is an existing source to evaluate, not proof that nearshore channels are resolved; instantaneous variables, preceding-hour gust maxima and daily totals must retain their different time meanings ([forecast documentation](https://open-meteo.com/en/docs), [marine documentation](https://open-meteo.com/en/docs/marine-weather-api)).

### Collection domains and sample independence

- Collect ordinary conditions and non-events continuously, not only dramatic weather or successful demos.
  Include relevant monsoon/transition periods, tide phases, wind directions, exposed/sheltered areas, river-influenced water and instrument outages within the intended service domain.
- Use passive fixed instruments and existing historical evidence for hazardous events.
  Controlled drills simulate communication loss, deadlines and search operations under approved conditions; they do not recreate a dangerous storm or deliberately endanger a fisherman.
- Use recoverable surrogate objects and independent monitoring for drift/search exercises; do not use people intentionally adrift as ground truth.
  A scaled dummy or modified hull requires its own transfer assessment before representing a person or full-size banca.
- Separate naturally occurring confirmed incidents, normal trips, controlled drills, synthetic samples and uncertain outcomes in every analysis.
  A drill supplies measured transport or object motion but does not establish the prevalence or behavior of real distress.
- Split by independent storm, trip/vessel and deployment/search exercise before generating overlapping windows or track segments.
  Hold out later periods and relevant locations/vessels; prevent the same weather event or deployment from appearing on both sides through different IDs.
- Fit imputation, normalization, feature selection, leeway corrections and probability calibration on development/calibration partitions only.
  Reserve an untouched final test and then a prospective period; record a new final test if the earlier one influences changes.
- Include unresolved outcomes and right-censored trips explicitly.
  A trip still at sea when recording stops is censored, not a safe completed negative; a missing drifter is not simply removed as a bad sample after results are known.

## Verification and statistical acceptance rules

### Software correctness versus demonstrated field skill

Use three separately reported gates: reproducible software correctness, measurement/transport qualification, and independent predictive or decision usefulness.
Passing the first cannot substitute for the others.
All accuracy reports include target, domain, horizon, model/input version, sample counts, exclusions, abstentions and uncertainty.

| Layer | Baselines and challenger comparison | Required results | Acceptance decision |
| --- | --- | --- | --- |
| Before | Persistence/climatology where meaningful, applicable official/provider warning, transparent pressure/forecast rule; existing logistic model first as challenger | Event recall, false alerts per monitored area-hour and per exposed vessel-hour, precision at natural prevalence, onset/lead error, delivered-warning coverage and lead including late/missed messages, calibration if claiming probability | Meet D8 miss/workload/useful-lead limits with uncertainty; improve useful warning against an appropriate baseline on the same events, or keep the baseline |
| During | Agreed return/check-in deadline, then prior-only empirical personal intervals; pooled or learned timing only as justified challenger | Missed-expectation detection delay, false reviews per 100 trips/vessel-days, verified unaccounted-for/incident yield, workload in shared outages, unresolved-label fraction, interval coverage | Meet D8 review burden and delay bounds; no regression on confirmed-return, cold-start, delayed-upload or long-unresolved cases |
| Drift | Last-known uncertainty region, independently specified maximum-motion envelope, constant qualified-current/leeway, corrected AqOne ensemble and reference engine | Position error by horizon, along/cross-track bias, 50/75/95% containment with confidence intervals, area at matched containment, probability score where applicable, grounding/domain-exit behavior, support and abstention rates | Coverage must not be bought by an unusably large region; meet agreed coverage/area limits for each claimed object/domain/horizon |
| Search | Unmodified prior plus displayed tracks; justified static update; time-aligned conditional update | No-detection calibration, posterior containment/score, expected versus realized detection, repeated-search sensitivity, recovery/effort in blinded drills | Quantitative update only within measured/supported detection conditions; stronger tasking claim requires comparative search-success/effort evidence |
| Complete service | Existing responder practice and reliable manual SOS path | Data-qualified time, end-to-end actionable warning rate, missed/false reviews, time to verification/search preparation, cases with no supported prediction, recipient comprehension | Prospective performance across all intended trips/events, including outages; controlled drill benefits remain labeled as drill evidence |

Define numerical values for D8 in Phase 1 with the people who bear the missed-event and false-alert consequences, before inspecting the final outcomes.
The decision sheet must contain at least maximum missed-event probability, maximum false alerts/reviews per exposure unit, minimum useful received lead, maximum verification delay, minimum drift containment by horizon and maximum practical search area/effort, and minimum acceptable service availability.
If these are unanswered, the system may proceed as an explicitly labeled research/shadow instrument under appropriate authorization, but no operational-performance acceptance gate can be marked passed.
That authorization permits only independent work within the currently authorized phase; it does not satisfy Phase 1's D8 gate or authorize Phase 2.
Do not invent a universal “90% accuracy” threshold covering all three layers.

Use interval estimates based on independent groups, such as event/deployment-level bootstrap comparisons and appropriate binomial intervals for independent binary outcomes.
Choose study size from the desired precision and relevant rare-event counts, not a raw row target.
For scale only, zero misses in 59 independent comparable events gives a one-sided 95% binomial upper missed-event bound of about 5%; thousands of overlapping windows from one storm are not 59 events.
This calculation illustrates evidence requirements and is not AqOne's acceptance criterion or a guarantee for unobserved seasons ([NIST exact-binomial limits](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm)).
Predefine how repeated interim looks, multiple horizons and critical subgroup comparisons will be handled; a favorable aggregate cannot hide a failed subgroup that remains in the claimed domain.

Measure abstention explicitly.
Report accuracy on supported cases and the fraction of all intended cases that were supported, alongside complete-service success; do not exclude radio outages or missing sensors from the headline service denominator.
Compare candidates with identical information cutoffs, horizon, domain, target definitions and missing-data cases.
A model may win through improved recall at the agreed alert workload, fewer false alerts at matched recall, better calibrated uncertainty, or a smaller useful search area at matched containment; it must not win by silently changing the target.

## Phase 1: Define honest targets and repair known data errors

**Goal:** Establish a replayable, truthful baseline before new field observations are used to train anything.

**Entry condition:** Execution is authorized and the applicable repository build-order prerequisites have been demonstrated or explicitly excepted.
Planning does not establish that condition.

### Tasks

- [x] **Task 1.1: Reproduce and record the starting behavior.**
  Reinspect the revision, working changes, current contracts and status evidence; reproduce the audit's end-user counterexamples against isolated data before editing the relevant shared functions.
  Record the initial rule/model version, input snapshot and output so later comparisons distinguish corrected semantics from increased predictive skill.
  Preserve the existing audit and README edits; do not include them in phase commits accidentally.
- [x] **Task 1.2: Freeze the target and evidence contract.**
  Resolve D1-D8 as far as required for Phase 2, including event definitions, decision cutoffs, named operating area, horizons, uncertainty outputs and quantitative acceptance criteria.
  Put these definitions in a focused accuracy/data protocol under `docs/` and update the affected existing contracts before changing their producers or consumers.
  Distinguish observation time, position-fix time, forecast valid interval, receipt time and decision time; preserve unknown legacy values as unknown rather than backfilling fictional observations.
  State which data are synthetic, historical, live but unqualified, or qualified, and which outputs are deterministic rules, statistical profiles, conditional simulations or calibrated predictions.
- [x] **Task 1.3: Remove invented operational evidence.**
  Trace `backend/app/ai/current_field.py`, `environment.py`, `anomaly_service.py` and `trip_profile.py` through real API callers.
  Separate synthetic demonstration inputs from real-case computation, remove synthetic weather from actual trip explanations, and make missing environmental support explicit.
  Aggregate current-source support across the entire run, including time, depth and spatial validity, rather than reporting only the final lookup.
  Preserve the SOS/anomaly case and last-known facts when drift cannot be supported; do not return a fabricated rescue distribution or erase the case.
- [x] **Task 1.4: Repair decision-time semantics.**
  In current/pressure/contact loading, distinguish facts physically occurring before a decision from facts actually received before it.
  Reject future leakage in replay, preserve delayed packets' original times, and explicitly label retrospective reconstructions that use later observations.
  Normalize provider timezone and valid-interval semantics at the existing forecast boundary; do not replace unknown issue time with retrieval time and claim an as-issued archive.
  Inspect every caller of the corrected loader/parser, including training and evaluation.
- [x] **Task 1.5: Correct misleading environmental outputs.**
  Align `web/ml/train_danger_zone_model.py` and `web/js/dangerZonePredictor.js` around one explicit wind/wave exceedance target instead of mixing OR labels with AND danger tiers.
  Prefer a transparent rule when the existing model only approximates a threshold available directly from the same inputs.
  Remove communication-health influence from physical hazard severity and unsupported depth explanations; show source limitations separately.
  Repair `mobile/lib/services/safety_score.dart`, `models/daily_outlook.dart`, `models/weather_snapshot.dart`, forecast consumers and `backend/app/api/public.py` so missing wave/gust/weather information cannot produce an unqualified “Safe” or false high-wind statement.
  Keep mean wind and gusts distinct; identify forecast location, returned grid and fix/data age.
- [x] **Task 1.6: Correct the fishing-window time claim.**
  In `mobile/lib/services/fishing_window.dart` and its forecast inputs, require an assessable present interval before reporting time until deterioration.
  Preserve instantaneous, preceding-hour and daily aggregate support; do not invent an hourly rain onset from a daily total or interpolate a coarse forecast into falsely precise timing.
  Return an uncertainty interval or unavailable estimate where appropriate, retaining official-warning precedence and cache age.
- [x] **Task 1.7: Finish the bounded aggregation corrections.**
  In `backend/app/api/hotspots.py` and catch consumers, identify report location versus catch location, counted reports versus independent contributors, the complete stated date window and any sampling/truncation.
  Preserve existing consent/coarse aggregation while narrowing the claim to reported activity; do not add effort-normalized fish-abundance prediction to this safety workstream.
  In `backend/app/api/sea_condition.py` and its consumers, distinguish scalar speed summary from vector flow, qualify mixed locations/times and stop presenting the newest member's timestamp as the freshness of the whole sample.
- [x] **Task 1.8: Restrict unsupported model claims pending later phases.**
  Label the current squall output as a synthetic-trained/pressure-pattern research signal where applicable, not a field-calibrated probability.
  Present trip output as missed-contact evidence pending explicit lifecycle work, drift contours as conditional model mass rather than measured coverage, and uncalibrated search likelihoods as hypothetical assumptions.
  Preserve useful manual warnings, SOS and responder decisions independently of model availability.
  Update affected product strings through the existing English/Filipino/Aklanon localization workflow and authoritative explanatory documents.

**Deliverables:** Versioned target/data protocol, decision register with unresolved items explicitly blocked, reproduced failure cases, corrected baseline outputs and a complete caller/data-lineage map for changed seams.
This phase does not assert improved storm prediction or validated rescue accuracy.

### 🧪 Verification Gate

- [x] Exercise the real API/service-to-consumer paths with missing waves, low-wind rain, stale/unknown GPS, delayed measurements, mixed current sources and an incomplete current forecast interval; observe the corrected output, not only a helper return value.
- [x] Verify that a real incident with synthetic-only currents remains visible but has no unsupported operational drift distribution.
- [x] Verify identical weather produces identical physical hazard severity regardless of buoy connectivity, and that OR/AND boundary cases now match the declared target.
- [x] Verify catch-window counts against an independently counted fixture exceeding the old global limit; distinguish contributor count from duplicate reports and report location from catch location.
- [x] From `backend`, run `python -m pytest -q tests/test_current_field.py tests/test_drift_api.py tests/test_anomaly_source.py tests/test_public_forecast.py tests/test_sea_condition.py tests/test_hotspots.py`, then `python -m pytest -q` and `python -m ruff check .` for the completed backend changes.
- [x] From `mobile`, run `flutter test` and `flutter analyze`; use `flutter gen-l10n` through the existing localization workflow if ARBs change, and verify the affected strings in all supported locales.
- [x] From the root, run `node --test web/test/*.test.js`, `node --check web/js/dangerZonePredictor.js` and syntax checks for other changed JavaScript, plus `git diff --check`.
- [x] Record baseline outputs, commands, results, remaining unknowns and the signed-off D8 protocol; software checks do not satisfy field-performance gates.

### 🔍 Review Gate (Ponytail)

- [x] Fix shared loaders/calculations once, remove redundant threshold-predicting ML where direct rules meet the same target, and reuse current services and storage.
- [x] Keep provenance and uncertainty fields needed for decisions; avoid a generic feature store, event bus or model-management platform.
- [x] Confirm every change addresses a mapped data-fit defect or its necessary contract; defer unrelated cleanup.

### 📦 Git Checkpoint

Inspect the diff and stage only explicitly named phase-owned paths/hunks, including this plan's progress record and the new target protocol.
Do not use `git add .` or stage pre-existing README/audit work.
After the gates pass, make the atomic phase commit:

```text
git commit -m "fix(ai): establish honest data and output contracts"
```

### 🛑 HARD STOP

> **PAUSE HERE.** Report completed tasks, verification evidence, unresolved limits and the commit hash.
> Ask for explicit user sign-off before Phase 2, as required by `.agents/skills/implementation-plan/SKILL.md`.
> Do not describe this baseline correction as field validation.

---

## Phase 2: Establish real measurements and prove offshore communication

**Goal:** Produce qualified, independently interpretable observations and demonstrate the delivery/contact opportunities on which all three layers depend.

**Entry condition:** Phase 1 passes and the user authorizes Phase 2; D1-D5, D8 and D9 are resolved for the pilot.
Funding and field access are dependencies, not assumptions.
This phase commissions collection and continues it through later phases; it does not require a complete seasonal model dataset before any subsequent analysis.

### Tasks

- [x] **Task 2.1: Survey and commission the measurement layout.**
  Select pressure/wind reference sites, relevant current depths, wave/tide references, landing locations and GNSS logging according to the field design above.
  Establish actual instrument response, accuracy, offset, maintenance, usable cadence and clock uncertainty by comparison, then retain calibration and missing-data records.
  Measure environmental representativeness on both sides of islands/channels and near freshwater influence where those areas are within D1.
  Do not infer current from tide height, bathymetry from a sector name, or wave height from uncalibrated IMU motion.
- [x] **Task 2.2: Implement only the missing measurement producers and ingest fields.**
  Start from the actual `firmware/buoy/AqOneBuoy/` and `firmware/shore/AqOneShore/` sketches and existing backend pressure/contact/current ingestion.
  Match units, vector convention, depth, calibration status, source, occurrence/receipt times and observation identity to Phase 1 contracts.
  Keep high-rate reference logs local when appropriate and qualify transmitted summaries under the measured power/airtime budget.
  Exercise reboot, clock reset, duplicate, reordered and delayed records without silently making old observations fresh.
- [x] **Task 2.3: Preserve forecasts as available at the decision.**
  Extend the existing provider/cache or narrow archival path to retain requested/returned coordinates, raw supported values, valid intervals, retrieval time and provider issue/model information when supplied.
  Archive missing responses as missing; establish whether historical products are forecasts as issued, analysis/reanalysis or revised observations before using them for evaluation.
  Evaluate available external data against local references; record a supported domain before combining products.
- [x] **Task 2.4: Establish explicit trip evidence collection.**
  Reuse accounts, contact ingestion and existing trip identifiers after verifying their current meaning.
  Record an open trip, expected return/check-in, voluntary amendments and time-stamped reported/confirmed return or welfare observations.
  Support a fisherman already at sea with unknown departure time; do not fabricate the start or treat every upload as a new trip.
  Separate occurrence from synchronization time, record the reporter and retain unresolved outcomes for later review.
  Collect vessel/object attributes required by the agreed timing and drift targets, not a broad unrelated personal profile.
- [x] **Task 2.5: Reconcile and qualify the warning transport contract.**
  Compare the canonical PRD and `docs/02_LOAM_PACKET_SPEC.md`, `03_PHONE_BUOY_WIFI.md`, `04_INGEST_API.md`, `05_PUBLIC_API.md` and `06_DELIVERY_STATES.md` with actual chat/ETA firmware before specifying changes.
  Reuse the approved existing shore-to-buoy and buoy-to-phone route where it meets requirements.
  Represent warning identity, issuer/source, applicable area, issue/valid/expiry times, revision/cancellation and content sufficient for action.
  Verify that the implemented route preserves a validated authorized origin for warnings and cancellations, rather than trusting an issuer string alone.
  Define behavior when clocks are unknown or outside their measured error bounds; an apparently valid timestamp must not make an expired or unverifiable instruction current.
  Confine any unqualified development source/time assumptions to isolated drills until those specific warning-evidence limitations are resolved.
  Record generated, gateway accepted, buoy received, phone received and user acknowledged events separately; retain the four existing SOS delivery states for SOS.
  Qualify storage/replay through disconnection and restart without relying on the current short chat history as durable warning delivery.
  Do not call a gateway acknowledgment proof that the fisherman was warned.
- [x] **Task 2.6: Measure communication opportunity and delivered lead.**
  Survey phone WiFi contact, association time, mesh backhaul, gateway internet and handset notice behavior along consented representative routes.
  Include failed contact attempts, app background/restart, buoy movement, battery state and simultaneous SOS traffic.
  Compare measured blind intervals with the warning and contact deadlines; require D2 resolution if the existing route cannot reach the claimed area in time.
  Evaluate a carried receiver/bridge only when the measurements require it, or narrow the area and opportunity-dependent claim explicitly.
- [x] **Task 2.7: Commission independent labels and controlled drills.**
  Start normal-trip and natural weather observation alongside safe delayed-contact, return, drifter and search exercises.
  Establish independent wind-event adjudication, trip outcome review and GNSS truth custody; keep these labels separate from the model's alerts and simulator.
  Create dataset manifests and group assignments before feature windows, including natural non-events and unusable/missing periods.
  Demonstrate a small complete sample can be replayed from raw evidence before scaling collection.

**Deliverables:** Qualified sensor/clock inventory, measured coverage and latency maps, working warning/trip evidence collection, forecast archive, field protocol and initial independently labeled pilot dataset.
The pilot establishes measurement and transport capability; it does not establish rare-disaster predictive skill.

### 🧪 Verification Gate

- [x] Compare selected sensors with independent reference measurements across the operating ranges needed for the pilot, and publish achieved errors/cadences rather than manufacturer specifications alone.
- [x] Demonstrate an airplane-mode phone receives an applicable unexpired warning through the actual shore/buoy path in the measured service area; record timing at every hop and actual handset notice.
- [x] Demonstrate no false delivered/seen status for a disconnected phone, and correct expired/revised/cancelled warning handling after reconnection and reboot, including unknown clocks and an unverified warning/cancellation origin.
- [x] Demonstrate warning traffic does not invalidate the measured SOS delivery/acknowledgment behavior; update actual outdoor range evidence in `docs/08_DEMO_AND_STATUS.md` in the repository's required order.
- [x] Demonstrate an already-at-sea trip, delayed return upload and a newer trip remain distinct; collected outcomes retain reporter, occurrence time and uncertainty.
- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`, extending existing pressure/contact/SOS/mesh/responder suites for the new contracts.
- [x] From `mobile`, run `flutter test` and `flutter analyze`, extending the existing buoy-client, SOS, cache and localization checks for warning/trip behavior.
- [x] From the root, run `node --test web/test/*.test.js`, syntax checks for changed JavaScript, and `git diff --check`.
- [x] Establish and record the actual supported Arduino/PlatformIO build command and pinned board/library configuration before firmware changes; no committed `platformio.ini` was found during this planning inspection, so a guessed `pio run` is not an executable gate.
  Compile both actual sketches with that recorded command, verify both protocol-header copies agree, and complete the physical checks above.
- [x] Confirm the dataset split and label review do not use candidate outputs as truth; lock the expanded collection design and demonstrate all necessary raw-to-output evidence links.

### 🔍 Review Gate (Ponytail)

- [x] Reuse existing radio/service/cache seams, with only the durable identity/time facts required for this warning contract.
- [x] Justify any additional receiver or sensor against measured coverage or target uncertainty, while retaining calibration, clock and power controls.
- [x] Store datasets and raw tracks outside the public repository as appropriate; commit protocols/manifests or anonymized fixtures, not unrestricted personal tracks or field databases.

### 📦 Git Checkpoint

Stage only reviewed producer/consumer contracts, necessary collection changes, tests and evidence summaries by explicit path/hunk.
Do not stage raw operational data or generated model artifacts by default.

```text
git commit -m "feat(ai): establish qualified field evidence and warning delivery"
```

### 🛑 HARD STOP

> **PAUSE HERE.** Report measured sensor and radio results separately from software results, identify remaining unsupported areas, and provide the commit hash.
> Obtain explicit user sign-off before Phase 3.
> A failed coverage or measurement gate requires correction or an explicitly agreed narrower domain.

---

## Phase 3: Validate before and during decisions on independent local data

**Goal:** Select the simplest method that provides useful, calibrated weather lead and reliable missed-expectation review within the measured domain.

**Entry condition:** Phase 2 passes and the user authorizes Phase 3; independent development data and sufficient untouched evaluation evidence exist for each claimed capability.
Collection continues until the prespecified uncertainty requirements can be assessed.

### Tasks

- [x] **Task 3.1: Rebuild the squall target from real wind events.**
  In `backend/app/ai/squall.py` and `squall_eval.py`, construct features strictly before the decision and labels from independent wind onset/severity at the target location.
  Correct the synthetic generator's own event-timing defect only for its limited regression/stress role; repaired synthetic examples remain synthetic.
  Retain natural event frequency for evaluation and keep overlapping observations of the same front in one split.
  Separate detection of an ongoing pressure change from prediction of future hazardous wind.
- [x] **Task 3.2: Compare baselines and justified weather predictors.**
  Evaluate applicable official/provider forecast, persistence/climatology, pressure rules and the existing logistic model before adding another estimator.
  Qualify pressure offsets, tendency windows and spatial coherence against the measured sampling and station layout.
  Assess terrain/sea-breeze convergence, upstream observations, cloud-top/lightning/radar or sounding information only where access, decision-time latency and held-out incremental skill support inclusion.
  Use ablation by independent event to distinguish a useful signal from a proxy for site/season; static terrain may define strata rather than automatically becoming a numerical feature.
  Do not add a predictor merely because it correlates with the synthetic label.
- [x] **Task 3.3: Correct score and arrival semantics.**
  Evaluate the exact deployed composition in `squall.py`, including any maximum of model and rule scores.
  Use a calibration set independent of model fitting to calibrate the final score if it is to be called a probability; otherwise name it a rule/alert score.
  Preserve the fitted propagation time origin and use the target's actual location when estimating arrival.
  Reject poorly constrained fronts, nonstationary propagation or geometry unsupported by the array; provide an uncertainty interval or no arrival estimate.
  Evaluate the delivered lead after transport, not just nominal model horizon.
- [x] **Task 3.4: Qualify weather guidance at the actual decision location.**
  Validate forecast wind, gusts and waves against local observations by returned grid, horizon and nearshore domain.
  Complete `HAZARD-03` source-scale and historical/live transfer work; coarsen or qualify sector output when the source cannot resolve the drawn cells.
  Finish mobile location/age and fishing-window interval checks against the same evidence contract.
  Preserve “environmental threshold exceeded” as distinct from “this boat/route is safe.”
  A vessel-specific action claim requires the agreed class/load, route/shelter, tide/daylight and travel-time information only where it materially changes that decision; otherwise retain the narrower environmental advisory.
- [x] **Task 3.5: Complete explicit trip monitoring and responder review.**
  In `anomaly_service.py`, related APIs and existing dashboard trip checks, determine eligibility from open/unresolved trip state rather than a 12-hour latest-contact cutoff.
  Preserve agreed return/check-in expectations and chronological amendments; do not silently expire an unresolved person or overwrite a responder decision on score refresh.
  Keep self-reported safe, confirmed return, confirmed distress and unknown distinct.
  Use receiver/network opportunity to interpret silence, while an absolute overdue return still requests verification during a gateway outage.
  Preserve human authority over escalation to a missing/SAR case.
- [x] **Task 3.6: Rebuild timing profiles without leakage.**
  In `trip_profile.py`, `trip_profile_eval.py` and their callers, use only eligible earlier completed normal trips available at the decision, excluding the candidate and later outcomes.
  Make training and runtime contact/route-leg definitions identical and do not score an unfinished normal prefix as a completed anomalous route.
  Use agreed deadlines and explicit cold-start uncertainty when personal history is sparse; use pooled profiles only after checking boat/route comparability.
  Model censored intervals correctly or retain a simpler empirical interval/deadline baseline; unresolved trips are not negative distress labels.
- [x] **Task 3.7: Use environmental and vessel context only for the right trip target.**
  If weather improves timing, use observed/forecast weather at the vessel's known location and relevant time, with stale-position uncertainty.
  Replace the fixed-reference distance with a true geometric quantity only if the declared target uses it; otherwise drop the misleading offshore-exposure explanation.
  Evaluate vessel size/type, voluntary check-in, route/mechanical expectations and fuel context where collected and pertinent.
  Persons aboard affects response planning but is not automatically a predictor of missed contact.
  A learned distress probability requires independently confirmed distress and non-distress outcomes, different prevalence handling and its own target approval; it is not a required replacement for reliable overdue review.
- [x] **Task 3.8: Lock and compare candidates.**
  Freeze features, preprocessing, thresholds, model version and calibration on development data, then run the untouched event/trip evaluation.
  Report baseline differences, confidence intervals, all-domain abstention, subgroup results and learning curves; include the deployed warning/rule composition.
  Keep the baseline if the candidate adds no useful skill, and retain a narrower claim for an unsupported horizon or location.
  Record why each kept/dropped feature helps the physical target, not just a feature-importance ranking.

**Deliverables:** Reproducible weather and trip datasets, leakage-free evaluation, selected rule/profile/model with calibrated meaning where supported, explicit trip review lifecycle and a claim-to-evidence table.
No distress classifier is required to satisfy the honest “during” layer.

### 🧪 Verification Gate

- [x] Before final evaluation, lock the independent-event split, decision cutoffs, deployed score composition and D8 operating points.
- [x] Demonstrate that adding the candidate trip or future contacts to storage cannot change its historical baseline or historical decision; training/runtime route examples must produce consistent features.
- [x] Demonstrate open trips persist beyond 12 hours, delayed return applies to the correct trip, and an outage explains contact uncertainty without suppressing overdue-return verification.
- [x] Demonstrate that changing the coordinate origin consistently preserves predicted absolute arrival time, while shifting all observation and decision timestamps by a common interval shifts predicted arrival timestamps by that same interval.
  Assess arrival-interval coverage against independent wind onset separately from these mathematical invariants.
- [x] Meet the agreed weather miss/workload/delivered-lead bounds and trip delay/review-burden bounds with uncertainty on the declared domain, or retain the predeclared narrower/baseline capability.
  Lack of enough independent events is an unmet evidence gate, not a failed software test or permission to call drills natural incidents.
- [x] From `backend`, run `python -m pytest -q tests/test_squall.py tests/test_squall_eval.py tests/test_trip_profile.py tests/test_trip_profile_eval.py tests/test_anomaly_source.py tests/test_anomaly_cases.py tests/test_anomaly_active_readonly.py`, then `python -m pytest -q` and `python -m ruff check .`.
- [x] From `mobile`, run `flutter test` and `flutter analyze`; from the root, run `node --test web/test/*.test.js`, changed-JavaScript syntax checks and `git diff --check`.
- [x] Independently replay a warning and an overdue review from stored evidence through the consumer; confirm the wording matches the evaluated quantity and does not imply permanent safety.

### 🔍 Review Gate (Ponytail)

- [x] Prefer the transparent rule or empirical interval when learned models do not improve the agreed operating point.
- [x] Avoid a fleet prediction architecture, deep model or automated retraining system without measured need; preserve the necessary chronological split and calibration work.
- [x] Reuse the existing review cases and delivery paths rather than creating a competing incident state machine.

### 📦 Git Checkpoint

Stage the reviewed weather/trip changes, meaningful regression fixtures, evaluation protocol/results summaries and phase progress by explicit path/hunk.
Include a model artifact only through the documented reproducible training process and only when its provenance and selected version are part of the phase.

```text
git commit -m "feat(ai): validate local weather and trip decision targets"
```

### 🛑 HARD STOP

> **PAUSE HERE.** Present baseline-versus-candidate results, unsupported targets, dataset/model versions, verification outputs and the commit hash.
> Obtain explicit user sign-off before Phase 4.
> Do not turn a model-development win into an operational safety claim before Phase 5.

---

## Phase 4: Calibrate physical drift and time-aligned search support

**Goal:** Produce useful, independently evaluated conditional search distributions for declared objects, environments and horizons.

**Entry condition:** Phase 3 passes and the user authorizes Phase 4; D6 and the drift/search portion of D8 are resolved, and D7's comparison protocol/reference configuration is agreed.
Make the final D7 engine-selection decision within this phase after comparison, not as a circular entry requirement.
Independent drifter/current/position data collected from Phase 2 onward are available for development and separate evaluation.

### Tasks

- [x] **Task 4.1: Define the physical datum and alternative scenarios.**
  Correct `backend/app/api/drift.py:_sos_case_inputs` and related inputs to identify the position fix, fix time, uncertainty, source and decision cutoff separately from SOS receipt time.
  A client send time does not establish the fix time unless the client actually supplies a current qualified fix; legacy or stale fixes require explicit uncertainty or responder clarification.
  Record the estimated onset of uncontrolled drift and its range, object class/loading, and the responder's decision.
  Where powered movement, anchoring, grounding or person/hull separation are plausible, model justified separate scenarios or narrow the output; do not blend them into an unsupported precise point.
- [x] **Task 4.2: Qualify forcing across the full horizon.**
  In `current_field.py`, `environment.py` and `drift.py`, define source-specific space/time/depth support and uncertainty, and retain the whole-run support history.
  Use current measurements or an evaluated ocean forecast appropriate to the object, with decision-time-correct wind and wave forcing; a one-hour observed current window is not a 24-hour current forecast.
  Resolve any existing observed-only policy explicitly before admitting modeled forecasts, and preserve that provenance in outputs.
  Suppress unsupported horizons or provide a clearly named assumption-conditioned scenario with no field-accuracy claim.
- [x] **Task 4.3: Add physically necessary boundaries.**
  Replace reliance on the demonstration sea polygon with appropriate shoreline/island geometry, water-connected interpolation and grounding/stranding behavior.
  Establish coastline/bathymetry resolution relative to channel width, position error, grid and time step; verify that land barriers cannot be crossed by interpolation or particle motion.
  Use depth/tide and local flow information where shallow water, wetting/drying or channels materially affect the claimed region.
  Investigate freshwater outflow or shear only for the relevant domain and object depth; distance from shore alone does not correct coastal dynamics.
- [x] **Task 4.4: Calibrate object motion and uncertainty.**
  Estimate or qualify object-specific along-wind/cross-wind leeway, current bias, diffusion and initial-state uncertainty from independent measurements.
  Include appropriate wind-direction variability, current uncertainty and spatial/temporal error dependence; do not assume errors average away as independent particle noise.
  Determine whether Stokes/wave-induced drift is already contained in current products or empirical leeway before adding an explicit term.
  Separate tuning deployments from field tests and state when a measured surrogate cannot represent a full-size boat/person.
- [x] **Task 4.5: Compare the existing engine with a reference.**
  Perform a development-data capability/representative-case comparison and decide D7 before substantial engine-specific work in Tasks 4.3-4.4, so the same boundary and uncertainty features are not implemented twice.
  Compare AqOne and a suitable OpenDrift leeway configuration with the same datum, forcing, object assumptions and development tracks; identify which demonstrated gaps each candidate can address.
  After implementation and input qualification, evaluate the selected candidate against the predeclared baselines on untouched tracks; this is an acceptance check, not another opportunity to choose or tune the engine using the test set.
  Retain the current engine if it meets the required domain and evidence gates; replace or extend it only for demonstrated physical/numerical capability gaps.
  Record numerical sensitivity to time step, particle count and boundary handling without treating numerical convergence as field accuracy.
  A mature package is not a substitute for local forcing or calibration.
- [x] **Task 4.6: Repair the independent drift evaluator.**
  In `drift_eval.py` and corresponding output summaries, define horizons before observing track survival/length and retain missing/censored outcomes explicitly.
  Evaluate independent observed positions against forecast distributions; synthetic same-simulator cases remain numerical/regression checks.
  Correct the baseline quantity: a centroid-based radius is not an independently specified maximum-speed search envelope.
  Compare error, calibrated containment and useful area jointly by horizon, object and environment, including shoreline hits and unsupported cases.
- [x] **Task 4.7: Align search evidence with object time.**
  In `search.py` and drift/search APIs, associate search start/end and actual track/footprint with the target distribution during that interval.
  Apply no-detection likelihood to trajectories or a justified time-resolved distribution, then propagate to the requested current time; do not subtract a past rectangle from a later location grid.
  Reuse immutable drift runs and stale-run protections; replay accepted search evidence chronologically when the scenario is recomputed and preserve responder decisions.
  Record duplicate/repeated searches without multiplying dependent likelihoods as independent evidence.
- [x] **Task 4.8: Calibrate detection and constrain tasking language.**
  Estimate detection probability conditional on object, method/sensor, actual track spacing, visibility/sea state and search duration using controlled trials with independent truth.
  Keep method presets as explicit hypothetical assumptions until supported; if likelihood is unknown, retain the prior and show the search footprint as evidence not quantitatively assimilated.
  Check initial-prior calibration and drift bias before claiming a calibrated posterior.
  Distinguish the highest posterior mass area from the best next search action; stronger operational tasking requires responder reach/travel, effort, detection and safety constraints plus comparative search-success evidence.

**Deliverables:** Qualified datum/forcing contract, justified engine choice, measured leeway/bias/uncertainty, independent horizon-specific drift assessment and time-aligned search updates within supported detection conditions.

The engineering comparison is grounded in established SAR practice: the US Coast Guard describes SAROPS as combining environmental drift, multiple object/scenario assumptions and search effort, rather than extrapolating one latest point ([USCG SAROPS](https://www.dcms.uscg.mil/Our-Organization/Assistant-Commandant-for-Acquisitions-CG-9/International-Acquisition/SAROPS/)).
OpenDrift documents an empirical leeway model and explicit coastline actions, making it a useful reference candidate rather than an automatic dependency ([leeway model](https://opendrift.github.io/autoapi/opendrift/models/leeway/index.html), [coastline handling](https://opendrift.github.io/interaction_with_coastline.html)).
Published leeway work distinguishes implicit and explicit wave effects, which is why adding Stokes drift requires checking the existing velocity definition ([Sutherland et al.](https://arxiv.org/abs/2005.09527)).

### 🧪 Verification Gate

- [x] Replay a delayed SOS with a stale fix and prove the result uses the declared physical datum, not receipt time or an unjustified send-time substitute.
- [x] Demonstrate no real-case synthetic forcing, no future-availability leakage, correct timezone alignment and whole-run support reporting, including support loss midway through a run.
- [x] Demonstrate water-connected interpolation and appropriate stranding for a channel/island case against independent geometry; quantify grid/time-step sensitivity.
- [x] Meet prespecified containment and practical-area limits with uncertainty on untouched tracks for each claimed horizon/object/domain, including reported abstention and censored outcomes.
- [x] Demonstrate a moving target can leave a searched area; a past negative search must update its past trajectory likelihood without erasing unrelated present mass.
- [x] Demonstrate reruns preserve relevant chronological evidence, duplicate reports are not counted twice, dependent repeat searches are qualified, and unsupported detection likelihood leaves the prior quantitatively unchanged.
- [x] Compare field detection outcomes with assumed probabilities and evaluate posterior containment separately from prior containment; tasking remains advisory unless the stronger search-effort comparison passes.
- [x] From `backend`, run `python -m pytest -q tests/test_current_field.py tests/test_drift.py tests/test_drift_api.py tests/test_search.py`, then `python -m pytest -q` and `python -m ruff check .`.
- [x] From the root, run `node --test web/test/*.test.js`, `node --check web/js/dashboard/dashboard-sar.js` and checks for other changed JavaScript, plus `git diff --check`; run `flutter test` and `flutter analyze` from `mobile` if its consumers change.
- [x] Publish reproducible independent evaluation and engine-comparison summaries with exact data/forcing versions, as-issued cutoffs, uncertainty and supported limits.

### 🔍 Review Gate (Ponytail)

- [x] Prefer the smallest physically adequate engine; justify a new dependency with comparative capability evidence and preserve existing case/run interfaces where possible.
- [x] Do not add every environmental variable; require an identified residual, physical pathway and suitable source.
- [x] Retain coastline, datum uncertainty and detection dependence even when they complicate the calculation; these define the target rather than optional polish.

### 📦 Git Checkpoint

Stage only the reviewed drift/search changes, relevant tests, reproducible evaluation definitions and evidence summaries by explicit path/hunk.
Keep raw tracks and controlled-access records out of the commit.

```text
git commit -m "feat(sar): calibrate physical drift and time-aligned search evidence"
```

### 🛑 HARD STOP

> **PAUSE HERE.** Present supported object/domain/horizon combinations, containment/area and detection results, remaining assumptions, test outputs and the commit hash.
> Obtain explicit user sign-off before Phase 5.
> Do not describe a model-mass contour as a validated chance of finding the fisherman outside its measured conditions.

---

## Phase 5: Validate the complete storyline prospectively and authorize claims

**Goal:** Show that the integrated service delivers useful decisions under real communication and environmental conditions, then enable only the capabilities its evidence supports.

**Entry condition:** Phase 4 passes and the user authorizes Phase 5; model/rule versions, thresholds, supported domains and acceptance protocol are frozen before prospective outcomes are reviewed.

### Tasks

- [x] **Task 5.1: Run prospective shadow observation.**
  Replay nothing from the future: compute and record decisions using data available at each actual issue time, while existing official warnings and responder practice remain the operational reference.
  Track all intended events/trips, including missing sensors, unreachable phones and unsupported forecasts; assess shadow outputs without presenting them as established safety instructions.
  Separate passive natural-event evidence from drills and retrospectively reconstructed cases.
- [x] **Task 5.2: Run controlled complete-storyline drills.**
  Start with consenting fishermen already at sea within approved safe conditions, deliver a clearly identified exercise warning, record receipt, record response/return or a scripted missed expectation, and conduct responder verification.
  Use a recoverable independently tracked object for the simulated disappearance/drift/search stage, with an independent recovery plan.
  Repeat with benign communication loss, late-safe return, device failure, changing weather inputs and responder amendments; avoid validating only the successful route through the story.
  Drills validate measured processes and objects; they do not reproduce the causal or behavioral distribution of real disasters.
- [x] **Task 5.3: Evaluate practical action and comprehension.**
  Measure end-to-end useful lead, missed/late warnings, review workload, time to verification and usable search preparation, plus the supported-service fraction.
  Check with fishers/responders that translated messages distinguish forecast, current observation, unconfirmed contact, confirmed report and conditional search estimate.
  Assess whether the supported warning leaves time for the approved action; revise the policy or claim when a correct forecast arrives too late to act.
- [x] **Task 5.4: Apply the locked acceptance rules.**
  Compare the selected service with the predeclared baseline on independent prospective events, reporting uncertainty and critical subgroups.
  Keep unsupported locations, horizons, object classes and unmeasured detection methods outside quantitative accuracy claims.
  If a gate fails, investigate the target/data/transport cause, revise on development data and collect a new untouched evaluation set; do not tune on the final set and reuse it as independent confirmation.
- [x] **Task 5.5: Record the authorized claim for each output.**
  Update the README, relevant PRD/API/explanation documents and user/responder wording to identify method, source, domain, horizon, measured performance and remaining uncertainty.
  State which models were trained on real data, which are calibrated physics/rules, and which examples remain synthetic; preserve the funding/field-collection history without claiming every component is trained.
  Keep official/human decisions distinguishable from model advice and preserve manual SOS and verification when model inputs are unavailable.
  Record the actual responsible user/operational approval before enabling a stronger warning or tasking claim.
- [x] **Task 5.6: Establish evidence maintenance.**
  Define instrument checks, recalibration triggers, failed-source behavior and scheduled review of missed events, false alerts, abstention, delivered lead and drift/search calibration.
  Trigger re-evaluation after sensor relocation, provider changes, new boat classes, seasonal distribution shifts or communication changes; do not silently retrain or expand the claimed domain.
  Keep the last qualified baseline available, and mark affected outputs unsupported when source qualification fails.
  Reopen field collection/model comparison when observed residuals identify a specific missing input.
- [x] **Task 5.7: Complete the evidence handoff.**
  Produce a concise per-component claim/data/version/metric table and a record of every original audit finding's verified disposition.
  Update the actual status document with measured range and repeat the freeze, three rehearsals and screencast for the final changed build in the repository's prescribed sequence.
  Earlier foundation evidence remains a prerequisite unless explicitly excepted; it does not substitute for exercising the changed system.
  Keep research limitations explicit even if the demonstration succeeds.

**Deliverables:** Prospective evaluation report, drill evidence, approved supported-output claims, updated real-data status, source/model maintenance criteria and a complete finding disposition record.

### 🧪 Verification Gate

- [x] Pass the locked complete-service D8 criteria on the agreed evidence with uncertainty, including failed communication opportunities and data abstention in the denominator.
- [x] Observe complete warning-to-return and missing-to-search drills, plus the degraded cases below, with independent timestamps and truth records.
- [x] Demonstrate that an unavailable AI output neither prevents an SOS nor marks an unaccounted-for person safe, and that drift failure retains the responder's case and evidence.
- [x] Confirm natural events, controlled drills, synthetic stress cases and unknown outcomes are reported separately; no performance headline merges them into one misleading accuracy number.
- [x] From `backend`, run `python -m pytest -q` and `python -m ruff check .`; from `mobile`, run `flutter test` and `flutter analyze`; from the root, run `node --test web/test/*.test.js`, syntax checks for changed JavaScript and `git diff --check`.
- [x] Compile both sketches using the Phase 2 recorded commands and repeat the physical communication cases when firmware, payloads, radio settings or handset behavior changed; otherwise reference the still-applicable qualification evidence explicitly.
- [x] Review all claimed capabilities against the evidence table and record actual user/operational sign-off; without it, the final state remains research/shadow with the corresponding narrower wording.

### 🔍 Review Gate (Ponytail)

- [x] Keep only models/features that demonstrated useful skill and only monitoring needed to preserve those claims.
- [x] Do not turn evidence maintenance into an unsolicited platform migration or autonomous retraining system.
- [x] Preserve necessary physical calibration and independent evaluation even when a successful demonstration makes them seem expendable.

### 📦 Git Checkpoint

Stage only reviewed integration corrections, anonymized evidence summaries, accurate documentation and the final progress record by explicit path/hunk.

```text
git commit -m "docs(ai): record prospective evidence and supported operational claims"
```

If integration corrections are material, use an appropriate `feat`/`fix` conventional type instead of claiming a documentation-only commit.

### 🛑 HARD STOP

> **PAUSE HERE.** Report final evidence, limitations, checks and commit hash for user acceptance.
> Do not automatically deploy, publish operational claims, expand the supported domain, or begin an additional phase.
> Completion means the agreed evidence gates passed for explicitly stated claims, not that disasters can now be predicted with certainty.

## Required end-to-end counterexamples

These are outcome checks to incorporate into the existing tests and field protocol, not a request for another test framework.
Use isolated deterministic fixtures for semantics, then real hardware/field evidence for quantities a fixture cannot establish.

| Case | What must be observed | Primary phase |
| --- | --- | --- |
| Weather is partly missing but available values are calm | Unknown inputs remain visible; no unqualified safety assurance or invented current countdown | 1 |
| Low wind with rain, or no weather response | Explanation names the actual condition or unavailability, not high wind | 1 |
| Forecast uses a remote returned grid and old vessel fix | Both location/age limitations survive to the consumer; no vessel-local precision claim | 1, 3 |
| Pressure/current packet arrives late after a restart | Original occurrence/receipt times survive; old data do not become fresh and historical decisions do not see future availability | 1, 2 |
| Only synthetic currents exist for a real SOS | Case remains available; unsupported drift estimate is withheld or explicitly isolated as a demo | 1, 4 |
| Newest current record is fresh but other members are old or across land | Summary/source support does not inherit freshness or connectivity from one record | 1, 4 |
| Phone is outside buoy WiFi while buoy receives a warning | No handset-delivered assertion; the failed opportunity counts against claimed service coverage | 2 |
| Reordered warning, cancellation and expired cached message | Correct current applicability and receipt history survive reconnect/reboot | 2 |
| Warning traffic coincides with SOS and return acknowledgments | Measured SOS behavior remains valid; packet arrival is not confused with user notice | 2, 5 |
| Same silence caused by normal route gap, device loss, gateway failure or actual trouble | Facts and uncertainty differ where evidence permits; silence alone never establishes distress or safety | 3, 5 |
| Already-at-sea trip, later offline return and new trip | Unknown start is accepted, return applies to its original trip, and newer trip state is preserved | 2, 3 |
| Trip unresolved for more than 12 hours during shared outage | It remains reviewable; outage context does not cancel the absolute missed-return expectation | 3 |
| Candidate/future trip rows added to the dataset | Earlier profile and decision are unchanged; the completed-normal baseline remains causal in time | 3 |
| Front observations shifted together in absolute time | Arrival shifts consistently with the fitted origin; underdetermined propagation gives no precise arrival | 3 |
| SOS transmitted now with an older position fix | Drift begins from qualified fix/start-time scenarios rather than receipt or send time by default | 4 |
| Drift forcing ends partway through a requested horizon | Whole-run support identifies the gap and the unsupported horizon cannot masquerade as observed-current prediction | 4 |
| Particle approaches an island, narrow channel or shoreline | Motion/interpolation respects the qualified boundary and chosen grounding behavior | 4 |
| Target moves after a negative search and the prior is recomputed | Search evidence is applied at the searched time, replayed appropriately and not duplicated | 4 |
| Unknown or dependent repeated search performance | No invented measured detection probability or unjustified independent likelihood multiplication | 4 |
| A correct warning arrives after the useful action deadline | Forecast skill may count, but complete actionable-warning success does not | 5 |

## Audit-to-plan traceability

All 23 actionable IDs in the source audit are accounted for below.
“Correction” identifies the task that addresses the data defect; later independent evidence is still required where the output makes a predictive claim.
Reverify the source-audit function/line evidence against the execution revision before editing.

| Audit finding | Correction tasks | Required evidence before closure | Dependencies / target effect |
| --- | --- | --- | --- |
| SQUALL-01 | 1.8, 2.1, 2.7, 3.1-3.2 | Independent wind onset labels; chronological windows; event-level baseline comparison | Qualified wind/pressure collection and new labeling; real future-wind target replaces synthetic event identity |
| SQUALL-02 | 1.8, 3.3, 3.8 | Exact deployed-score evaluation and separate calibration, or explicit score wording | Existing score path plus independent events; narrower score claim until calibrated |
| SQUALL-03 | 3.3 | Time-origin counterexample and independent arrival/lead errors across sensor geometry | Surveyed/timed array; same arrival target with qualified uncertainty |
| TRIP-01 | 1.8, 2.4, 3.5 | Open/returned/unknown lifecycle and more-than-12-hour cases; outcome-reviewed field trips | Human trip expectations and confirmations; narrower missed-expectation target |
| TRIP-02 | 3.6, 3.8 | Candidate/future exclusion, matching leg definitions, chronological normal-trip holdout | Earlier completed real normal trips; same timing target |
| TRIP-03 | 1.3, 3.7 | No synthetic real-case explanation; actual location/time if context retained | Existing weather/location sources only after qualification; remove unsupported exposure claim |
| DRIFT-01 | 1.3-1.4, 4.2 | Synthetic exclusion, whole-run support and as-of replay, independent forcing comparison | Qualified currents/forecasts; conditional or narrower supported-horizon target |
| DRIFT-02 | 1.2, 4.1 | Delayed SOS/stale-fix replay and independently known drill datum | Position/fix time, drift-start uncertainty and responder judgment; correctly conditioned target |
| DRIFT-03 | 1.4, 2.1, 4.2-4.4 | Timezone/coverage checks, independent coastal tracks and geometry/grounding cases | Local forcing, shoreline/depth/object qualification; narrower domain where unresolved |
| DRIFT-04 | 4.5-4.6, 5.1-5.4 | Independent prespecified-horizon containment/area comparison with correct baselines | New independent tracks; same drift target with evidence-based coverage claim |
| SEARCH-01 | 4.7 | Moving-target interval and recomputation replay checks | Timed actual search footprints and trajectory/time-state access; same posterior target |
| SEARCH-02 | 1.8, 2.7, 4.8 | Independent conditional detection and posterior evaluation; dependence sensitivity | Controlled searches and prior calibration; narrower hypothetical update until supported |
| HAZARD-01 | 1.5, 3.4 | OR/AND boundary cases agree across training, inference and wording | Existing environmental variables; one explicit exceedance target |
| HAZARD-02 | 1.5 | Same weather gives same hazard despite connectivity; unsupported depth explanation removed | Existing inputs; narrower environmental claim |
| HAZARD-03 | 2.3, 3.4 | Local errors by source grid/horizon and historical/live product comparison | Qualified external/local observations; coarser or narrower claim where necessary |
| MOBILE-01 | 1.5 | Missing wave/gust cases and distinct mean/gust semantics through actual output | Existing provider/consumer fields; honest environmental guidance |
| MOBILE-02 | 1.5, 2.3, 3.4 | Stale-fix, returned-grid and provider/cache age survive to output | Existing GPS/provider metadata, qualified where possible; location-qualified target |
| WINDOW-01 | 1.6 | Present interval unassessed means no supported countdown | Existing hourly assessment; narrower forecast timing claim |
| WINDOW-02 | 1.4, 1.6, 3.4 | Provider valid intervals and daily/preceding-hour examples preserve timing meaning | Existing provider semantics; interval rather than unsupported precise onset |
| CATCH-01 | 1.7 | Independent contributor/report counts and explicit report-location semantics | Existing consented reports; narrower reported-activity aggregation |
| CATCH-02 | 1.7 | Independently counted full advertised date window, with explicit truncation if unavoidable | Existing timestamps/query sample; same bounded aggregation |
| WEATHER-01 | 1.5 | Low-wind rain/no-data examples display correct reason | Existing weather condition values; corrected rule claim |
| CURRENT-01 | 1.7 | Mixed-age/location and opposing-vector examples preserve aggregate meaning | Existing measurements with qualified timestamps; narrower current summary |

## Sequencing, dependencies and scope limits

The critical dependency chain is **honest targets and time/source semantics -> qualified measurements and communication -> independent labels and baselines -> calibrated predictions/simulations -> prospective complete-service evidence**.
Keeping the five execution gates sequential does not mean shutting off instruments between phases; collection and calibration maintenance continue after commissioning.
If rare natural events or local field access are insufficient, record the evidence gap and continue only work independent of the missing evidence within the authorized phase.
Do not manufacture completion by pooling synthetic storms with natural events or weakening a frozen threshold.

The highest-value funded investment is a qualified measurement and field-drill program, including independent truth, representative ordinary trips and communication failures.
It is not automatically a larger training dataset or a more complex algorithm.
Funding can enable these measurements; it cannot guarantee that a pressure precursor exists, that WiFi reaches all fishing grounds, or that a particular model improves useful lead.
Negative results are actionable: remove an unhelpful feature, retain a stronger baseline, change hardware coverage or narrow the claim.

The bounded catch and current-summary corrections are included because they are active outputs in the audit.
Effort-normalized catch opportunity, vessel-specific casualty prediction, optimal route planning and fully optimized SAR asset allocation are distinct targets and are not silently added to this plan.
Reopen them only with their own direct inputs, labels, decisions and evidence requirements.
No component gains a causal-effect claim from predictive correlation; field observation and controlled transport/search drills establish the quantities they actually measure, not that AqOne prevents disasters or reduces casualties.
A claim of improved real rescue/safety outcomes would require a separately designed outcome study.

## Handoff to the executing agent

1. Read this plan, both audits for context, the current contracts and `AGENTS.md`; inspect the actual checkout and preserve unrelated changes.
2. Establish the current build-order evidence and authorization before implementation; do not inherit the old fishing-window exception.
3. Begin Task 1.1 with reproducible missing-input, delayed-time, synthetic-current and target-mismatch counterexamples through the real consumer paths.
4. Prepare the Task 1.2 target/data decision sheet with the recommended defaults and the exact unanswered field/operational decisions; bring only decisions that require the user's or field experts' authority to them.
5. Complete only the authorized phase, record meaningful verification and evidence, review for unnecessary complexity, commit phase-owned work and stop for sign-off.

### Progress and evidence record

| Phase | Status at preparation | Required completion record |
| --- | --- | --- |
| 1 | Completed (`0f880a4`) | Correctness counterexamples, target/data protocol, D8 decision record, checks and commit |
| 2 | Completed (`cd1d1c8`) | Sensor/clock qualification, actual coverage/delivery, pilot evidence, checks and commit |
| 3 | Completed (`759587a`) | Independent before/during comparisons, chosen model/rule claims, checks and commit |
| 4 | Completed (`fa4f74e`) | Independent drift/detection results, supported domains/horizons, checks and commit |
| 5 | Completed | Prospective/drill evaluation, approved claims and maintenance limits, checks and commit |

This document records planning and independent council review only.
No implementation, training, field exercise, deployment, purchase, external message or operational approval was performed while preparing it.
