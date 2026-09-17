# Gemini AI Safety Remediation Review and Audit

Date: 2026-09-16.
Branch: codex/ai-safety-remediation.
Revision inspected: 593a193e9c990a0f63a943b1ac9c9b840e6db192.
Implementation comparison: 601288f through 570ad41, checked against the current revision.
The implementation commits are 0efc64a (warnings), d2bae9e (drift), 59ced0d (search), 89d1684 (calibration/replay), and 570ad41 (field handoff).
The subsequent 593a193 documentation commit is included where it describes these changes.

Scope: review Gemini's implementation against [the remediation plan](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md:139>) and the supplied completion report.
This covers offline warning delivery, trip continuity, drift support, time-aligned search, calibration/replay, and field evidence.
The Ponytail review examines the diff for unnecessary complexity; the Ponytail audit follows its callers across the repository.
Unrelated existing features and deadline edits are outside this review.
No fixes were implemented.
The working tree was clean before this review; the only repository file created by this review is this report.

## Verdict

**Changes required: the assertion that all five phases and all software/bench gates are complete is not supported by the implementation.**
There are useful improvements, but important fixes exist only in a Python representation of the firmware or are bypassed by the real caller.
New defects also affect no-contact trip evaluation, wind timing, and search assimilation.

For the intended storyline, the current software cannot yet demonstrate the complete chain of an offline warning actually reaching a fisherman, an unresolved no-contact trip remaining visible, and a responder receiving a geographically and temporally supported search estimate.
An overdue obligation is evidence for human verification, not proof that a person is unsafe.
A conditional drift simulation does not establish the person's actual location.

The highest-value next step is to repair and test the real producer-to-consumer paths described below before expanding the model or collecting a large training dataset.
Field collection preparation is useful; it is not field validation.

## What improved

- The application's advisory feed now attempts the buoy client after backend failure, and the application wiring supplies that client.
  This connects previously separated pieces of the offline path: [VentureFeeds.advisories](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/mobile/lib/services/venture_feeds.dart:210>).
- Both actual firmware headers change authentication handling for relay-mutated fields.
  This is a real firmware change, although a compiled cross-node verification was not available in this review: [buoy header](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/firmware/buoy/AqOneBuoy/AqOneLoam.h:1>), [shore header](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/firmware/shore/AqOneShore/AqOneLoam.h:1>).
- Live squall results from the current explicitly synthetic bundle are capped at watch, even when the return-now switch is enabled.
  Classifier probability and rule score are exposed separately, and the evaluator now scores their composed maximum: [status gate](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/squall.py:140>), [evaluation](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/squall_eval.py:199>).
  This does not establish field calibration.
- The current loader adds receipt/observation cutoff and qualification/depth filters.
  Trajectories and weights are now stored, and sector updates use that trajectory state instead of only attenuating the final grid: [current loader](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/current_field.py:45>), [search persistence](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:1085>).
- Real incidents without a stored run are prevented from silently entering the synthetic GET path.
  Trip-state query failures are no longer swallowed.
- The field handoff explicitly acknowledges that physical collection is pending.
  Its useful preparation must be retained while correcting the unsupported claims and thresholds described below.

## Verification performed and limits

| Check | Observed result | What it establishes |
| --- | --- | --- |
| Current diff, callers, firmware consumers, migrations, tests and relevant contracts | Reviewed | Static evidence of actual wiring and unmet requirements |
| node --test web/test/*.test.js | 141 passed, 0 failed | Existing dashboard regression tests pass; not backend, hardware, or integrated scenario correctness |
| Syntax parsing of changed Python files | All 20 parsed | Syntax only |
| Isolated execution of unchanged production function bodies | Five defect demonstrations below | Deterministic local behavior; not full application/database verification |
| Backend pytest and ruff | Not run | Available bundled Python lacks pytest, ruff, FastAPI and asyncpg; no configured backend environment was found during inspection |
| Targeted Flutter offline-warning test | Attempted; no output or completion observed, then stopped | No Flutter pass is claimed |
| Firmware compile, real database restart, physical radio/phone drill | Not performed | These gates remain unverified in this review |

The isolated checks compiled the selected functions directly from the inspected files in memory.
They did not modify production code or add repository test files.
The anomaly check substituted an empty database/history and no-op persistence boundary; it is a control-flow reproduction, not a database integration test.

| Reproduction | Input | Actual result | Correct comparison |
| --- | --- | --- | --- |
| Wind time interpretation | Provider-style local 08:00/09:00 samples with eastward values 8/9; query 00:30 UTC on the same day | 8.0 | 8.5 when those samples mean Philippine local time |
| Instantaneous search | Particle moves from latitude 0 to 1 in ten minutes; a narrow sector covers latitude 0.60 at minute six; second particle stays outside; POD 0.8 | Weights 0.5, 0.5 | Interpolated encounter gives 1/6, 5/6 |
| Interval search | Same trajectory; search is minutes one to two, sector is latitude 0.9 to 1.1 | Weights 1/6, 5/6 | Neither particle visited the sector during the interval, so 0.5, 0.5 |
| Manifest integrity | Three records with invented valid-length hashes, no raw files, no event IDs, arbitrary provenance strings | Accepted | Cannot be accepted as verified field evidence |
| No-contact persistence | Open trip for vessel1, no historical contact rows | KeyError 'vessel1' | Retain an explicit unknown/overdue review state without crashing |

## Correctness findings

P1 means a high-priority correctness or evidence-integrity issue affecting the requested scenario.
P2 means a material but more bounded defect.
“Unmet remediation” identifies a pre-existing gap Gemini claimed to close; it is not necessarily a newly introduced regression.

### GSR-01 [P1]: Warning retry, cancellation, and priority fixes are not in the running firmware

**Classification:** Unmet remediation; duplicate implementation used as acceptance evidence.
**Affected plan checks:** W2-W7, W9.

The new [Python warning model](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/mesh/loam.py:1>) is imported by warning tests, with no production caller found across backend, gateway, firmware, or mobile.
Actual warning sketches are unchanged in this remediation.
The real gateway remembers a warning after meshSend accepts it and skips unchanged warnings thereafter: [polling loop](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/firmware/shore/AqOneShore/AqOneShore.ino:584>).
A lost first transmission or a buoy booting later therefore still lacks the promised bounded rebroadcast.
The real buoy cache has no revision comparison or cancellation tombstone: [WARN handler](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/firmware/buoy/AqOneBuoy/AqOneBuoy.ino:927>).
An older warning can overwrite the same ID.
The Python priority scheduler does not control either radio.
The real gateway polls only authored public advisories; no producer connects the squall research output to that downlink.
See [pollWarnings](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/firmware/shore/AqOneShore/AqOneShore.ino:554>) and [the separate live squall route](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/squall.py:177>).
Therefore, a new research watch does not automatically become an offline warning merely because handset advisory fallback is connected.

The tests [beginning at the codec test](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/tests/test_warning_transport.py:222>) exercise Python encoding, relay, cache, and scheduling.
They do not execute the C++ warning producers/cache or demonstrate radio SOS priority.
Their integer publication/expiry fixture also avoids the actual date-string producer boundary.

**Smallest correction:** Apply the required behavior to the existing gateway/buoy implementation and verify those actual functions.
Do not maintain a second firmware implementation as proof of the first.
Preserve the useful HMAC header fix.

**Test required first:** Compile the real codec/cache/scheduler behavior into a host harness or execute it on the nodes.
Lose the first WARN, reboot a receiving buoy, deliver cancellation followed by an older revision, saturate warnings while sending SOS, and assert actual cache/output/acknowledgement behavior.
Run a real serialized advisory through the gateway date conversion.
Phone display and acknowledgement receipts must be generated by the actual clients and survive disconnection; the new backend duplicate lookup alone does not prove that.
Its identity tuple also lacks warning revision, so reusing an advisory ID for an update can conflate receipts: [delivery lookup](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/advisories.py:431>).

### GSR-02 [P1]: A registered trip with no contacts can crash the evaluation service

**Classification:** Introduced integration defect.
**Affected plan check:** C5.

[eligible_latest_trips](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/anomaly_service.py:150>) now adds open trips with an empty contact list.
However, [evaluate_and_persist](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/anomaly_service.py:177>) builds profiles from contact rows, then indexes profiles[vessel_id] at line 190.
With no history for that vessel, this raises KeyError.
With older history supplying a profile, [persistence](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/anomaly_service.py:245>) still indexes contacts[-1], producing IndexError.
The default synthetic flag at line 200 also classifies a no-contact trip as synthetic because its provenance is inferred solely from contacts.

The new C5 test calls eligibility and score_trip with a manually supplied profile rather than the persistence service.
It therefore misses the failure the real evaluation path encounters.
Older open trips excluded by the “latest” grouping can also be appended with empty contacts despite having historical observations.

**Smallest correction:** Carry declared-trip identity, provenance, and last-known/unknown contact state through the existing service.
Provide the existing low-confidence baseline behavior where appropriate and permit an explicitly absent last contact.
Never substitute an invented contact or label lack of contact as confirmed safety.

**Test required first:** Evaluate and persist a real declared trip with no contacts, both with and without older history.
Read the resulting active case from the actual API.
Also include another vessel in the same evaluation so one missing history cannot break the batch.
Verify missed return obligations, unknown welfare, and correct provenance.

### GSR-03 [P1]: Wind samples requested in Philippine time are interpreted as UTC

**Classification:** Introduced deterministic timing defect.
**Affected plan check:** D6.

[_fetch_wind_series](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/drift.py:227>) requests timezone Asia/Manila and parses the returned local ISO strings without attaching their timezone.
The changed [_interpolate_series](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/drift.py:278>) attaches UTC to every naive sample.
This shifts those samples by eight hours.
Open-Meteo documents that setting timezone returns local-time timestamps: [provider documentation](https://open-meteo.com/en/docs).
The isolated reproduction above demonstrates the resulting wrong interpolation.

The new test supplies already-aware UTC and Philippine timestamps.
That proves equivalence of correctly tagged timestamps, not correctness of the provider parser.
The function also continues clamping before/after the supplied series, so a fresh HTTP fetch does not establish wind support for an old datum or an unsupported future horizon.

**Smallest correction:** Normalize the provider's actual timestamp representation at ingestion.
Require valid-time coverage and retain forecast issue/retrieval provenance separately.
Do not treat a clamped endpoint as an observed or forecast-supported missing interval.

**Test required first:** Feed a real-shaped local-time provider response through fetch/parsing/interpolation, including midnight, a historical datum, series gaps, and a horizon beyond the last sample.
Verify the same physical instant gives the same vector independently of host timezone.

### GSR-04 [P1]: Drift support diagnostics do not constrain the published field

**Classification:** Unmet remediation and incomplete caller wiring.
**Affected plan checks:** D1, D2, D4, D5.

[Production geometry checking](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:233>) leaves min_separation_m at its zero default.
The colocation test passes 500 explicitly, so it does not test the production choice.
The [current loader](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/current_field.py:62>) accepts NULL source, calibration status, and depth.
[Current ingest](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/current_events.py:35>) still defaults depth to one metre and accepts a submitted qualification label without a linked calibration record.
A label is not independent measurement qualification.

[Spatial influence](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/current_field.py:254>) remains a 111 km distance rule without water connectivity.
Missing support still becomes zero current inside the numerical field.
[assess_result](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/environment.py:108>) accepts an aggregate observed fraction of at least 0.5 and non-degraded wind; support_lost_at does not make the result insufficient.
Thus unsupported particle-time segments can coexist with environmental_status “ok.”
The new support columns are not selected in [_RUN_COLUMNS](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:36>) or exposed by the normal response, so a responder does not receive the promised support boundary.

The geometry loader uses last_at as its receipt cutoff while the simulation loader uses decision_cutoff_at.
A delayed reading available when the decision is made can be excluded from geometry yet included in the field.

**Smallest correction:** Make qualification and support rules apply through the real caller and persisted response.
Use the decision cutoff for availability, and datum/integration time for physical validity.
Reject unsupported operational contours or explicitly return a bounded conditional estimate with its unsupported mass/time; zero numerical fill must not mean measured still water.

**Test required first:** Through the production API and a disposable database, compare colocated versus separated sensors, unknown qualification/depth, a sensor across land, delayed receipt, and a field that loses support partway through.
Assert the resulting status, supported horizon, and response metadata, not merely helper attributes.

### GSR-05 [P1]: Production drift does not enable coastline collision, and mass counts are invented

**Classification:** Unmet remediation.
**Affected plan check:** D7.

The production [predict_drift call](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:246>) passes enable_stranding=True but no boundary_polygon.
[The integrator](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/drift.py:510>) runs collision checking only when both are supplied.
The test supplies geo.WATER_POLYGON explicitly; the real path does not.

[geo.py](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/geo.py:19>) describes approximate demo geometry and also distinguishes open offshore edges from coastline.
It is not evidence of the high-resolution shoreline claimed in the new handoff.
Even when passed directly, endpoint-inside-water checking does not establish that a trajectory segment cannot cross a thin island and emerge in water.
[Run metadata](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:336>) calculates afloat_count from the literal 2000 and writes outside_domain_count=0.
The test's “mass accounting” assertion subtracts stranded from the test particle count and adds it back, without checking an outside-domain state: [D7 test](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/tests/test_drift_qualification.py:438>).

**Smallest correction:** Supply suitable coastline and separate open-domain boundaries through the real path, or explicitly withhold coastline-aware claims.
Derive particle states/counts from the simulation, not constants.
Do not classify exiting the modeled sea area as grounding.

**Test required first:** Run the production path for a thin island crossing, a shoreline hit, and an open-domain exit, with a non-default particle count.
Verify positions, separate terminal states, supported mass, persistence, and responder output.

### GSR-06 [P1]: GNSS fix metadata has a consumer but no actual producer

**Classification:** Unmet end-to-end remediation.
**Affected plan check:** D3.

[The SOS drift reader](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:433>) now prefers fix_acquired_at and reads fix_accuracy_m.
Repository-wide caller inspection finds those fields in this reader and the migration, but no mobile, mesh, gateway, or SOS ingest producer.
The existing handset transmission clock remains distinct from when the displayed position was acquired.
Renaming the fallback datum_source to client_send is useful honesty, but it does not fix a stale cached position being propagated from the wrong time.

**Smallest correction:** Preserve actual fix time and accuracy through the existing location and SOS path, including delayed/offline delivery.
For unknown legacy metadata, retain unknown provenance and require a justified datum/uncertainty choice or a narrower claim.

**Test required first:** Acquire a position, delay transmission, deliver via the real SOS serializer/ingest route, open a case, and verify the stored and returned datum.
Repeat with a cached fix, missing accuracy, and responder override.
Directly populating the new database columns in a mock is insufficient.

### GSR-07 [P1]: The actual search workflow invents missing time and detection probability

**Classification:** Unmet remediation in the user path.
**Affected plan checks:** S2, S5.

[The dashboard submission](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/web/js/dashboard/dashboard-ai-ops.js:550>) sends rectangle, method, and idempotency key, but no occurrence time or measured detection probability.
[The backend](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:1036>) substitutes submission time and the old 0.3/0.6/0.9 presets.
It records is_unassimilated=False regardless of this missing evidence.
Delayed reporting is therefore treated as a search at the wrong time.
The [likelihood helper](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/search.py:91>) additionally multiplies POD by 0.25 for “dependent,” an uncalibrated repeat-search assumption.
Repeated dependent reports still compound reductions.

**Smallest correction:** Capture the actual occurrence interval through the responder workflow.
Preserve unknown POD and unsupported timing as unassimilated evidence or explicit conditional assumptions, without silently changing the operational posterior.
Keep unmeasured method presets distinct from measured local detection performance.

**Test required first:** Submit through the actual dashboard/API with delayed, absent, partial, and out-of-support timing, unknown POD, and dependent repeats.
Assert evidence remains readable with its reason when not assimilated.
Verify that method selection alone cannot masquerade as calibrated negative evidence.

### GSR-08 [P1]: Search weighting uses the wrong trajectory positions

**Classification:** Introduced numerical defect.
**Affected plan checks:** S1, S2.

[Instantaneous searches](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/search.py:111>) use the nearest stored step rather than an interpolated location.
[Interval searches](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/search.py:105>) include a step after the end of the search whenever the preceding segment overlaps it.
The two numerical reproductions above show both a missed real encounter and attenuation for a location reached only after the search.
Partially out-of-range intervals are accepted rather than explicitly bounded/rejected.

**Smallest correction:** Evaluate location/footprint intersection at the actual supported occurrence time or over the actual supported interval.
Use a documented temporal approximation only if its error is acceptable for the spatial footprint and exposed as such.

**Test required first:** Add the two counterexamples above, a mid-segment crossing whose endpoints are outside the sector, and partially unsupported intervals.
Verify final particle weights and the persisted posterior through the search API.

### GSR-09 [P1]: One invalid old search report can silently erase all prior search evidence on rerun

**Classification:** Introduced persistence/replay defect.
**Affected plan checks:** S4, S6, S7.

[The rerun loop](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/api/drift.py:289>) replays all sectors inside one broad exception handler.
On any failure it publishes the original drift grid without an error or an unassimilated reason.
Legacy sectors receive south/north keys containing None; the helper tests key existence, then compares arrays with None.
A legacy sector can therefore trigger this fallback.
Out-of-range timing and contradictory zero-mass evidence can do the same.

This is not merely a failed request: the resulting run can look like a successful fresh prediction while ignoring previous searches.
The new S6 test only round-trips JSON; S7 filters a local list instead of calling the real query/rerun: [tests](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/tests/test_search_assimilation.py:294>).

**Smallest correction:** Preserve each report and its assimilation outcome.
Do not publish a successful posterior that silently discards prior evidence.
Handle unsupported legacy evidence explicitly and distinguish an assimilation failure from a prior-only conditional run.

**Test required first:** Store one valid and one legacy/invalid sector, rerun, restart, fetch, and update again using a disposable database.
Assert the valid evidence is retained, the invalid evidence has a visible reason, and an unexpected failure cannot silently reset weights.

### GSR-10 [P1]: Historical trip decisions still use future contacts and later trip amendments

**Classification:** Unmet replay requirement.
**Affected plan checks:** C3, C6.

[_load_trip_rows](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/anomaly_service.py:55>) loads all contacts with no occurrence/receipt cutoff.
The candidate grouping and scorer use those rows.
[_load_trip_states](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/anomaly_service.py:105>) reads current state and amendments without reconstructing what was known at as_of.
The new [profile filter](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/trip_profile.py:243>) filters observation time for baseline rows but does not reconstruct receipt-time knowledge or prior trip state.
It defaults absent state to completed, which is not confirmation of a normal completed trip.

Consequently, appending a future contact or extending a deadline after an old decision can alter replay of that decision.
C6 now verifies query failure propagation, but not amendment replay or baseline independence.

**Smallest correction:** Apply occurrence and receipt cutoffs before candidate selection and baseline construction.
Reconstruct deadline/status knowledge at the decision time.
Exclude unknown/abnormal histories from a confirmed-normal baseline or label the baseline's weaker meaning.

**Test required first:** Persist a historical decision, append a late contact, future contact, and later deadline/return amendment, then replay through the actual service.
The original prospective result must remain unchanged; a retrospective reconstruction must be separately identified.

### GSR-11 [P1]: “Verified field manifest” means syntactic acceptance, not verified evidence

**Classification:** Introduced evidence-integrity gap.
**Affected plan checks:** C3, C4, F8.

[validate_manifest](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/manifest.py:66>) checks hash shape and a short blacklist but never opens raw evidence or computes its checksum.
Event identity is optional, track_id is not included in grouping, provenance values are unrestricted, and an absent test split can pass.
Diversity is counted across arbitrary outcome strings rather than the defined target.
No training/evaluation entry point calls this validator; its callers are tests.

[The canonical manifest](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/manifests/field_eval_manifest_v1.json:1>) contains specific vessel/event outcomes and no raw evidence locations.
One “raw evidence” hash is exactly SHA-256 of the two bytes [].
That was independently computed during this review.
This does not prove any field record exists or establish that the other hashes identify measurements.
[The handoff](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md:92>) calls the fixture illustrative and verified, conflating schema illustration with raw-data verification.

**Smallest correction:** Explicitly mark these records as examples and exclude them from field evidence.
Verify referenced raw bytes, valid provenance, required event/track identities, and target-specific partition sufficiency at the actual dataset/evaluation boundary.
A standard-library implementation remains sufficient.
Do not claim physical-data verification from a plausible checksum string.

**Test required first:** Missing/raw-file mismatch, same track under different window IDs, unknown provenance, no held-out data, and drill/natural-label mixing must fail or return insufficient evidence through the evaluator itself.
A changed raw file must invalidate its previously accepted evidence.

### GSR-12 [P2]: The new drift evaluator can score the wrong horizon and wrong miss distance

**Classification:** Introduced evaluation defect; currently test-only caller.
**Affected plan check:** C8.

[evaluate_drift_track](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/drift_eval.py:193>) uses horizon_hours to check support and compute baseline area, but always selects true_track[-1] and contours[-1].
It does not align an observation with the requested horizon.
For a miss, it measures distance to polygon vertices, not to the nearest boundary segment.
For example, a point just outside the middle of a long edge can have a much larger reported miss than its actual distance to that edge.
Direction error and target-time matching required by C8 are not produced.
The normal evaluation entry point does not invoke this function.

**Smallest correction:** Define the metric and horizon explicitly, select/interpolate timestamped truth accordingly, calculate the specified separation/boundary distance, and run it in the real evaluation workflow.
Treat missing horizon truth/support as unavailable rather than choosing the terminal track point.

**Test required first:** One track spanning multiple requested horizons, an edge-midpoint miss with known distance, and a missing/unsupported truth interval.
Verify denominators and outputs from the actual evaluation entry point, not only helper fixtures.

### GSR-13 [P2]: Warning freshness still extends exact-midnight expiry and permits immortal missing-date notices

**Classification:** Incomplete new freshness logic.
**Affected plan checks:** W2, W5, W8, W10.

[Advisory.isActive](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/mobile/lib/models/advisory.dart:94>) infers “calendar date” from zero hour/minute/second.
An exact midnight instant is therefore extended to the end of that day.
The parser has discarded the distinction between a date-only value and a timestamp.
An official warning lacking both publish and expiry dates gets publishDate ?? now on every check, continually renewing its 48-hour retention.
Non-official missing-expiry notices return true indefinitely.
Thus the new “bounded retention” comment does not hold for degraded data.
Separately, [Advisory.parseList](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/mobile/lib/models/advisory.dart:184>) still maps a decoded object with no advisories list to an empty list.
A syntactically valid malformed response such as {} can therefore appear as no active warnings rather than unavailable information.
Missing source also defaults to an official notice, contrary to W10's requirement to preserve unknown identity/source.

**Smallest correction:** Preserve whether the input represents a calendar day or an exact instant.
Apply the agreed Philippine calendar policy only to calendar dates.
Use a fixed persisted receipt/issue time for approved retention and expose missing/invalid freshness rather than renewing it.

**Test required first:** An exact midnight timestamp, a date-only expiry, a non-Philippine host timezone, missing issue and expiry, a research warning without expiry, and restart with cached data.
Exercise the feed/screen path with a controlled clock.

### GSR-14 [P1]: Field preparation introduces unsupported labels and operational thresholds

**Classification:** Introduced documentation/data-target mismatch.
**Affected plan checks:** F1-F8.

[The new field handoff](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md:52>) defines a natural squall label using wind thresholds plus a barometric drop.
Requiring the detector's pressure signal in the reference event excludes relevant wind events without that signature and undermines an independent comparison against a pressure baseline.
It also treats a shore/station measurement as local offshore truth without establishing spatial representativeness.

[Its acceptance table](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md:69>) gives fixed 80% containment and twofold area reduction without specifying which nominal contour, supported horizon, sample denominator, or uncertainty criterion makes those numbers meaningful.
F6 says negative POD leaves the prior unchanged while the implemented API rejects it.
[The lead-time rule](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md:85>) asserts 20 minutes is enough for a motorized banca to reach shelter without route, starting position, vessel performance, or measured safe transit evidence.
These can be proposed hypotheses; the repository does not establish them as physical facts or qualified operational criteria.

The same document asserts high-resolution coastline handling and “causal, uncorrupted” profiling despite GSR-05/GSR-10.
Static code inspection does not establish causal identification.
Its “software/evaluation gate passed” status is inconsistent with the missing actual-path evidence identified here.

**Smallest correction:** Label candidate thresholds as proposed until their physical/operational basis is established.
Define independent event truth for the intended weather target, local representativeness, nominal coverage and denominators, and uncertainty before holdout inspection.
Use measured route-specific delivered lead for operational usefulness.
Keep physical field validation explicitly incomplete and correct the completion ledger rather than changing the definition of success.

**Test/evidence required first:** A target-definition review using weather events with and without a pressure-drop signature; a fully specified metric calculation on small known tracks; and actual commissioning, delivery, drifter, normal-trip, and blinded-search logs.
Drill outcomes must remain distinct from natural distress labels.
Do not fabricate records to make a manifest nonempty.

## Acceptance-gate reconciliation

“Partial” means some code exists or some narrower behavior is tested; it does not mean the full plan check passed.

| Plan checks | Audit disposition | Why |
| --- | --- | --- |
| W1 | Partial | Buoy fallback is wired; active-shell/background behavior and a physical receipt are not established here |
| W2 | Open | Real gateway date producer is not exercised by the Python integer fixture; mobile freshness gaps remain |
| W3 | Partial | Actual HMAC headers changed, but Python self-consistency is not a compiled cross-node test |
| W4-W5 | Open | Retry/revision/cancellation behavior is in the Python model, not the real sketches |
| W6-W7 | Open | Backend receipt checks and simulated scheduling do not establish offline receipt recovery, revision identity, or actual SOS priority |
| W8 | Not closed | Cache/time issues remain; actual disconnected/reconnection delivery is not established here |
| W9 | Open | Actual gateway only polls authored advisories; no squall research-to-downlink producer is connected |
| W10 | Open | Midnight/missing-date freshness and malformed-object/unknown-source parsing remain incorrect |
| D1-D2 | Partial | Filters added, but qualification/caller cutoff inconsistencies remain |
| D3 | Open | New columns/read path lack a real fix-data producer |
| D4-D5 | Open | Test-only separation setting, no connected-water support, and incomplete support enforcement/response |
| D6 | Open | Provider-to-interpolator timezone defect; unsupported series clamping remains |
| D7 | Open | No production boundary supplied; arithmetic identity does not prove state accounting |
| D8 | Partial | Real GET no-run fallback improved; no independent full database/read-idempotence verification here |
| S1-S2 | Open | Wrong sample selection and real workflow time substitution |
| S3 | Open | Interval handling and arbitrary repeat-dependence adjustment do not establish correct sweep exposure |
| S4 | Partial | Idempotency/run checks and geographic storage exist, but rerun evidence loss and actual database atomicity need closure |
| S5 | Partial | Invalid/zero-mass rejection exists; the actual API still substitutes presets for unknown POD |
| S6-S7 | Partial | State storage/query code exists; JSON/list tests do not establish restart or prospective rerun behavior |
| C1-C2 | Partial, useful | Current explicitly synthetic watch cap and composed-score evaluation improved; independent calibration and metadata-based promotion remain unestablished |
| C3-C4 | Open | Manifest acceptance is not evidence verification or enforcement at the training/evaluation boundary |
| C5-C6 | Open | No-contact persistence crash and historical knowledge leakage |
| C7 | Partial | Actual request failure injection is an improvement; fake pool is not the required persisted-case/restart proof |
| C8 | Open | Horizon and distance metric defects; helper is not integrated into the evaluator |
| F1-F8 | Physical validation pending | Preparation documents exist; neither simulated checks nor sample manifests close field gates |

The plan requires test-first implementation and actual-path acceptance checks.
The available commits and supplied report do not contain independently replayable RED-then-GREEN evidence for every task.
Tests and implementation arriving in the same commit cannot prove which was written first.
This review does not infer that Gemini definitely wrote tests afterwards; it finds that the required evidence and coverage are insufficient.
In particular, a passing test with the right W/D/S/C label is not evidence that the stated acceptance scenario ran.

## Ponytail review and audit

These are complexity findings, separate from the correctness findings above.
Repository-wide caller searches found no production consumer for the new Python radio model or ManifestSummary, and no runtime dependency files changed.

- [backend/app/mesh/loam.py:1](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/mesh/loam.py:1>): yagni: 342-line second firmware implementation used only by tests; replace the test subject with the existing real firmware harness, then remove the mirror.
- [backend/app/ai/manifest.py:31](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/backend/app/ai/manifest.py:31>): delete: unused ManifestSummary and its dataclass import; replacement: nothing, 10 lines removable.
- [mobile/lib/models/advisory.dart:150](<C:/Users/User/Desktop/PersonalProjects/00-HACKATHONS-COMPETITIONS/00-HACKATHONS/00-2026-FIRST-YEAR/2026-Aquanons/AIHackathon2026_Aquanons_AqOne/mobile/lib/models/advisory.dart:150>): shrink: _id duplicates _int exactly; use the existing _int parser, 6 lines removable.

Do not delete the warning tests without replacing their subject with actual firmware behavior.
The replacement harness size is unknown, so the 342-line mirror is excluded from the net estimate.
No deletion of a minimum smoke test or necessary safety validation is recommended.

Ponytail diff review net: -16 lines possible.
Ponytail repository audit net: -16 lines, -0 deps possible.

## Recommended correction order

This is a review handoff, not an authorization to implement fixes in this review.
For each row, first reproduce the failure at the stated real boundary, then make the smallest correction and rerun that check.
Do not expand into a new model architecture to solve wiring or timestamp defects.

| Order | Findings | First evidence to obtain |
| --- | --- | --- |
| 1 | GSR-01, GSR-02 | Actual firmware lost-warning/SOS-priority scenario and no-contact trip persistence/API test |
| 2 | GSR-03, GSR-04, GSR-05, GSR-06 | Provider parser, qualified supported field, real coastline/domain states, and delayed-fix SOS end-to-end tests |
| 3 | GSR-07, GSR-08, GSR-09 | Actual timed search submission, analytic trajectory counterexamples, and database rerun/restart retaining evidence |
| 4 | GSR-10, GSR-11, GSR-12 | Receipt-aware trip replay and raw-evidence-backed, horizon-aligned evaluation at its actual entry point |
| 5 | GSR-13 | Controlled-clock warning expiry and cache restart tests |
| 6 | GSR-14 | Correct independent field targets and explicit proposed criteria before collection or holdout evaluation |
| 7 | Field gates F1-F8 | Commissioned measurements and controlled, independently logged drills after software prerequisites demonstrate the intended behavior |

Correct the completion claims alongside the corresponding evidence; do not mark the full plan complete after fixing only these software defects.
Preserve the distinction between physical plausibility, predictive skill on independent observations, and causal identification.

## Evidence index and review boundaries

Primary inspected implementation areas:
backend/app/ai/anomaly_service.py, current_field.py, drift.py, drift_eval.py, manifest.py, search.py, squall.py, squall_eval.py, trip_profile.py, and environment.py;
backend/app/api/advisories.py, drift.py, squall.py, and the SOS/current-data producers;
backend/app/geo.py and backend/app/mesh/loam.py;
migrations 025 and 026;
both firmware AqOneLoam.h headers and the buoy/shore AqOne sketches;
mobile main/advisory/feed/buoy-client paths;
web/js/dashboard/dashboard-ai-ops.js;
the changed backend/mobile tests;
the remediation plan, relevant warning/data contracts, docs/52, docs/54, the canonical manifest, and the supplied completion report.

The attachment's references to firmware/buoy/loam_codec.py, backend/tests/test_offline_warnings.py, and mobile/test/offline_warnings_test.dart do not match files in the inspected tree.
The actual new mirror is backend/app/mesh/loam.py, the backend warning test is test_warning_transport.py, and the new mobile test is offline_warning_delivery_test.dart.
This supports treating the completion narrative as a claim to verify, rather than execution evidence.

No deployed system, private field archive, real municipal measurement, or prior physical test was observed during this review.
Absence of those observations is recorded as unverified evidence, not a claim that no such work exists outside the repository.
Only this report was added; no other repository files were changed.
