# Needs-validation register

All entries below are independently source-verified candidates, not confirmed vulnerabilities.
No severity is assigned while a decisive local or deployment fact remains unresolved.
The complete records remain machine-readable in findings.json.

## backend.ai.anomaly.authenticated-whole-fleet-recompute — Authenticated anomaly evaluation can amplify work across fleet history

**Boundary and candidate:** A valid operator bearer token can invoke the anomaly evaluation write path without a narrower role check, request-rate bound, mutual exclusion, or source-visible work cap. Each invocation runs inline, reads all selected contact history and all trip states, rebuilds fleet and vessel profiles, and mutates the shared anomaly projection; whether bounded repeated calls materially delay live safety APIs depends on runtime data volume and deployment controls that were not observed.

**Verified source trace:**
1. **entrypoint** — backend/app/main.py:129 (anomaly router authentication boundary). The complete anomaly router is mounted with only Depends(require_user), so every valid user bearer token reaches its routes without an endpoint-specific role or capability check.
2. **propagation** — backend/app/api/anomaly.py:79 (POST /api/ai/anomaly/evaluate). The authenticated no-body endpoint has no additional dependency or admission control and awaits evaluate_and_persist inline.
3. **propagation** — backend/app/ai/anomaly_service.py:55 (_load_trip_rows). Evaluation fetches every live contact row, or every live and synthetic contact row in demo mode, ordered across all vessels and trips without a row, vessel, trip, or time bound.
4. **propagation** — backend/app/ai/anomaly_service.py:105 (_load_trip_states). Evaluation also fetches all vessel trip-state rows without a filter or limit.
5. **propagation** — backend/app/ai/trip_profile.py:225 (build_profiles_from_contacts). The complete in-memory contact list is filtered, grouped, flattened into a fleet profile, and processed again into per-vessel profiles.
6. **sink** — backend/app/ai/anomaly_service.py:182 (evaluate_and_persist projection rebuild). The run first deactivates the selected shared anomaly-score projection, then synchronously scores every eligible trip and performs per-vessel profile, score, and possible case upserts before returning.

**Supporting evidence:**
- backend/app/auth.py:103 — require_user validates a signed user-kind token but does not enforce a role or per-action capability.
- backend/app/api/anomaly.py:85 — The request acquires the application database pool and directly awaits the complete evaluation before responding.
- backend/app/db.py:6 — The backend exposes one module-global asyncpg pool used by API routes, so evaluation and live database-backed APIs share source-visible pool capacity.
- backend/app/ai/anomaly_service.py:173 — evaluate_and_persist performs both whole-source loads before building eligibility and profiles for the run.
- backend/app/ai/trip_profile.py:252 — Profile construction groups the filtered history, constructs a fleet-wide trip list, builds the fleet profile, and loops over every vessel group.
- backend/app/ai/anomaly_service.py:189 — The evaluator loops over every eligible vessel/trip and issues multiple awaited writes, including anomaly-case writes for non-normal scores.
- backend/tests/test_anomaly_active_readonly.py:114 — The request test identifies POST /evaluate as the explicit write path and expects a normal operator token to reach it, but it does not measure concurrency, data-scale, or availability effects.
- Dockerfile:15 — The checked-in default launches one Uvicorn command without a source-visible worker count, request limit, or timeout; provider-side overrides remain unknown.

**Decisive blockers:**
- No bounded runtime observation establishes the request duration, memory use, database-pool occupancy, event-loop delay, or concurrent safety-API latency at representative contact/trip volumes.
- This Windows workspace cannot enforce the required empty allowlisted environment, isolated no-network namespace, read-only target and toolchain, scratch-only process writes, explicit CPU/memory/process/file/disk limits, and race-safe artifact promotion, so target-controlled services and tests were not executed.
- Live worker count, proxy or application rate limiting, request timeouts, database-pool sizing, scheduled-run overlap, and representative production row counts are deployment facts not established by repository source.

**Safe resolution plan:**
**Bounded local validation:** Inside the approved OS-enforced sandbox, start the production Docker command against an isolated disposable PostgreSQL database containing synthetic fixtures at fixed scales (for example 1,000, 10,000, and 50,000 contact rows with bounded trip counts). With one mdrrmo token, issue one evaluation and then at most three concurrent evaluation requests while a separate dummy principal performs bounded GET /health/ready and one protected read. Record wall time, peak RSS, event-loop/read latency, database-pool wait time, and projection state before and after; enforce strict wall-clock and resource limits and destroy the database afterward.
**Owner-observed deployment validation:** Without sending audit traffic, have the service owner inspect and record the deployed worker count, endpoint/proxy rate-limit and timeout rules for POST /api/ai/anomaly/evaluate, asyncpg pool limits, scheduler cadence and overlap prevention, current buoy_contacts and vessel_trips row counts, and monitoring evidence for evaluation duration or correlated API/DB saturation.

## backend.ai.anomaly.zero-contact-poison-run — Zero-contact trip can interrupt anomaly recomputation after projection deactivation

**Boundary and candidate:** An anonymous caller can register an open trip for a newly created or existing vessel without any contact events. A later authenticated or scheduled anomaly evaluation includes that zero-contact trip, deactivates the current anomaly-score projection, and then follows a source-visible exception path while scoring or persisting it. Whether the prior projection remains cleared depends on the runtime database transaction behavior and therefore requires bounded PostgreSQL validation.

**Verified source trace:**
1. **entrypoint** — backend/app/api/trips.py:82 (create_or_register_trip). The router is mounted without the blanket operator dependency and accepts a caller-selected vessel_id and open trip without requiring any contact event.
2. **propagation** — backend/app/ai/anomaly_service.py:150 (eligible_latest_trips). Open, overdue, or unresolved trip-state rows not represented by contact rows are added to the evaluation set with an empty contacts list.
3. **propagation** — backend/app/ai/anomaly_service.py:183 (evaluate_and_persist). The evaluator deactivates every anomaly-score row in the selected live or demo scope before iterating and validating all eligible trips.
4. **sink** — backend/app/ai/anomaly_service.py:190 (evaluate_and_persist). A zero-contact trip for a fresh vessel has no profile entry and raises at profiles[vessel_id]; if the vessel has historical contact rows and therefore a profile, persistence later dereferences contacts[-1] at line 245 instead.

**Supporting evidence:**
- backend/app/main.py:97 — The trips router is included before the blanket require_user dependency that is applied to the anomaly router.
- backend/app/api/trips.py:94 — Registration creates a caller-selected vessel when absent and inserts the trip without requiring a corresponding contact.
- backend/app/ai/trip_profile.py:262 — Profile construction adds fallback profiles only for vessels present in contact rows, so a fresh zero-contact vessel is absent from the profiles mapping.
- backend/app/ai/anomaly_service.py:245 — Even when an existing vessel supplies a profile, score persistence requires contacts[-1].observed_at after the projection-deactivation statement has run.
- backend/app/api/anomaly.py:88 — The HTTP evaluator acquires a connection and calls evaluate_and_persist without an explicit transaction block.
- backend/app/ai/run_anomaly_evaluation.py:33 — The scheduled evaluator also uses a direct asyncpg connection and invokes evaluate_and_persist without an explicit transaction block.

**Decisive blockers:**
- The required OS-enforced sandbox is unavailable in this Windows workspace, so the audit could not run the target against an isolated disposable PostgreSQL database to observe the exception and determine whether asyncpg commits the projection-deactivation statement before the later failure.

**Safe resolution plan:**
**Bounded local validation:** Inside the required no-network, read-only-target, scratch-only sandbox, start a disposable local PostgreSQL instance; apply the migrations; seed one active live anomaly-score row; anonymously register an open trip for a fresh vessel with no buoy_contacts; invoke evaluate_and_persist through a bare asyncpg connection exactly as the HTTP and scheduled callers do; assert the raised exception; then query the seeded row from a fresh connection to determine whether is_active remained false. Repeat with an existing vessel that has historical contacts to exercise the later contacts[-1] path, and use an explicit transaction as a rollback control.

## backend.ai.squall.flag-authorizes-live-model-replacement — Training flag exposes the live squall artifact to every operator role

**Boundary and candidate:** The authenticated training route is protected only by the blanket user-token check and ALLOW_TRAINING. When that flag is truthy, an MDRRMO, LGU, or admin token can synchronously retrain from stored synthetic rows and write the result directly over the same joblib path loaded by live squall reads. Source defaults and the checked-in Render blueprint leave the flag disabled, so deployment reachability and an observed overwrite remain unresolved.

**Verified source trace:**
1. **entrypoint** — backend/app/api/squall.py:203 (POST /api/ai/squall/train). An authenticated dashboard user can invoke the training endpoint; the router receives only the blanket require_user dependency configured in app.main.
2. **propagation** — backend/app/api/squall.py:205 (train). The only route-local authorization gate is whether ALLOW_TRAINING has one of the accepted truthy strings.
3. **propagation** — backend/app/api/squall.py:214 (train). The async request handler synchronously trains a model from the stored synthetic readings, squall events, and buoy rows.
4. **propagation** — backend/app/api/squall.py:215 (train). The request immediately passes the newly trained bundle to save_bundle with no approval or staging argument.
5. **sink** — backend/app/ai/squall.py:777 (save_bundle). joblib.dump writes directly to the default active squall.pkl path rather than atomically promoting a separately validated artifact or retaining a rollback version.

**Supporting evidence:**
- backend/app/main.py:129 — The protected-router dependency is require_user, not a role-specific or release-approver dependency.
- backend/app/main.py:133 — The entire squall router, including /train, is registered with only that blanket dependency.
- backend/app/auth.py:114 — require_user validates the signed token and user kind but performs no role authorization for the training action.
- backend/app/ai/squall.py:19 — MODEL_PATH identifies backend/app/ai/models/squall.pkl as the default shared model artifact.
- backend/app/api/squall.py:120 — Live squall status loads a bundle from the default MODEL_PATH on each request, linking the training write to runtime reads.
- backend/.env.example:16 — The example configuration says ALLOW_TRAINING guards this route and should be left unset during a demo; the following value is empty.
- render.yaml:17 — The checked-in Render environment list includes database, JWT, setup-key, and expiry settings but does not enable ALLOW_TRAINING.
- docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md:404 — The operational handoff explicitly says not to run the training endpoint in deployment or replace the committed model artifact through telemetry plumbing.
- docs/42_DATA_STRATEGY_RESPONSIBLE_AI_IMPLEMENTATION_PLAN.md:234 — The current governance contract requires human-reviewed offline preparation with versioned inputs, approval, rollback, and an audit event for each release.

**Decisive blockers:**
- This workspace cannot provide the required OS-enforced empty-environment, no-network, read-only-target, scratch-only-write, resource-bounded sandbox, so the authenticated route and artifact replacement were not executed.
- The live value of ALLOW_TRAINING is a deployment fact not present in the repository. The example configuration is empty and render.yaml omits the key, which makes the source-defined/default deployment return 403 rather than expose the replacement path.
- No owner-observed evidence establishes whether an external release process, filesystem policy, immutable deployment, artifact backup, or rollback control contains the direct write in the actual environment.

**Safe resolution plan:**
**Bounded local validation:** Inside the approved full sandbox, start a disposable app instance with a temporary PostgreSQL fixture containing the minimum synthetic readings, events, buoys, and one account for each role. Redirect app.ai.squall.MODEL_PATH to a predeclared scratch file, set ALLOW_TRAINING=true, call POST /api/ai/squall/train with each role token, and record bounded hashes plus loadability of the scratch model before and after each call. Repeat with the flag unset to prove the 403 fail-closed path; interrupt one scratch-only write to determine whether the prior artifact remains loadable. Do not promote the model file as audit evidence unless trusted parent-side race-safe promotion is available.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner inspect the effective ALLOW_TRAINING value, route access logs, container filesystem policy, model release procedure, retained prior version, rollback control, and audit trail. If the flag is unset, record that the path is not reachable; if it is enabled, identify the roles that can invoke it and whether a direct write changes the artifact subsequently loaded by /api/ai/squall/current.

## backend.auth.login-timing-enumeration — Operator login may disclose account existence through bcrypt timing

**Boundary and candidate:** The anonymous login path has source-visible, account-dependent work: a nonexistent email bypasses password hashing, while a wrong password for an existing operator invokes bcrypt. This could let a remote caller infer valid operator email addresses from repeated response-time samples, but distinguishability and deployment-side request controls were not observed.

**Verified source trace:**
1. **entrypoint** — backend/app/api/auth.py:45 (POST /api/login). An anonymous caller submits an operator email and password to the login route.
2. **propagation** — backend/app/api/auth.py:50 (login account lookup). The route queries the users table by normalized email and receives either an account row or None.
3. **sink** — backend/app/api/auth.py:59 (login failure predicate). Python short-circuits the OR expression when the row is None, but calls verify_password for an existing row, creating account-dependent bcrypt work before the common 401 response.

**Supporting evidence:**
- backend/app/auth.py:58 — verify_password delegates to bcrypt.checkpw, an intentionally costly password verification operation.
- backend/app/api/auth.py:59 — The row-is-None term precedes verify_password in an OR expression, so only known accounts reach bcrypt verification.
- backend/tests/test_login_audit.py:148 — The unknown-email regression test checks the common 401 and audit-event shape but does not measure time or assert that password verification runs on both failure branches.

**Decisive blockers:**
- The required OS-enforced no-network, read-only-target, scratch-only execution sandbox is unavailable, so the target-controlled login fixture and timing measurements were not run.
- No bounded runtime samples establish whether the bcrypt-dependent latency difference remains statistically distinguishable through the database, application server, and network noise.
- Live proxy, WAF, rate-limit, lockout, and abuse-monitoring controls for /api/login are deployment facts not represented in repository source.

**Safe resolution plan:**
**Bounded local validation:** Inside the approved execution sandbox, use the existing FastAPI TestClient and fake database pattern with one bcrypt-hashed operator. After five warm-up requests, submit ten alternating unknown-email and known-email/wrong-password requests, wrap verify_password to record invocation counts, and record per-request monotonic elapsed time. Confirm both branches return the same 401 body and audit shape, then determine whether the two bounded timing distributions separate; stop after these twenty measured requests and retain only aggregate counts and timings.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner inspect the effective proxy/WAF and application configuration for per-IP and per-account throttling or lockout on POST /api/login, and review existing authentication telemetry for whether repeated failed-login timing samples would be detectable or blocked. Record the effective rule, threshold, and scope, or explicitly record that no such control exists.

## backend.catch.global-idempotency-cross-vessel-write — Catch-log retry keys are not scoped to the authenticated vessel

**Boundary and candidate:** An authenticated vessel-device request must name its token-bound vessel, but a non-null local_id collision is resolved against the globally unique catch-log key. If vessel A submits a local_id already held by vessel B, the source-visible conflict branch targets B's row and can change optional catch metadata and hotspot consent without a vessel predicate. The concrete two-vessel database mutation was not executed, so this remains unconfirmed pending a bounded disposable-PostgreSQL check.

**Verified source trace:**
1. **entrypoint** — backend/app/api/catch.py:62 (ingest_catch_log). POST /api/catch-logs accepts a caller-controlled local_id from an authenticated vessel device.
2. **propagation** — backend/app/api/catch.py:73 (ingest_catch_log). The route derives owned_vessel_id from the device token and rejects a mismatched body vessel_id, but passes the independently caller-controlled local_id into the insert.
3. **sink** — backend/app/api/catch.py:96 (ingest_catch_log SQL upsert). ON CONFLICT selects any row with the same non-null local_id and updates species_name, method, notes, and share_for_hotspots without checking the existing row's vessel_id.

**Supporting evidence:**
- backend/app/auth.py:191 — Vessel-device authentication verifies that the token vessel matches the current device record, establishing a real vessel-owner boundary.
- backend/app/api/catch.py:74 — The normal insert path explicitly rejects a body vessel_id that differs from the authenticated device vessel.
- backend/migrations/011_catch_logs.sql:29 — The partial unique index is on local_id alone rather than on vessel_id and local_id.
- backend/app/api/catch.py:101 — The conflict branch updates existing optional metadata and unconditionally replaces share_for_hotspots, with no owner predicate.
- backend/app/api/catch.py:121 — The response returns the conflict-selected row id and reports it as a duplicate without verifying that the row belongs to the authenticated vessel.

**Decisive blockers:**
- The current Windows workspace cannot provide the required OS-enforced no-network namespace, empty allowlisted environment, read-only target and toolchain, scratch-only process writes, explicit resource limits, and race-safe artifact promotion, so the FastAPI/PostgreSQL path could not be executed to independently observe the two-vessel mutation.
- The repository does not contain an active handset catch-log producer, so source alone does not establish how a real victim local_id would be learned or predicted; the boundary effect requires an authenticated vessel device to submit a value equal to another vessel's existing non-null key.

**Safe resolution plan:**
**Bounded local validation:** Inside a disposable fully sandboxed PostgreSQL/FastAPI fixture, create dummy vessels A and B with separate valid device tokens. Insert B's catch log with local_id shared-key, null optional metadata, and share_for_hotspots false; then POST as A with vessel_id A, the same local_id, distinct metadata, and share_for_hotspots true. Stop after asserting that the API reports duplicate, returns B's row id, and B's stored row remains owned by B but has the conflict-assigned fields changed. Repeat after changing uniqueness and conflict handling to (vessel_id, local_id) and assert separate rows.
**Owner-observed deployment validation:** Without sending crafted requests, the owner can read the deployed pg_indexes definition for uq_catch_logs_local_id and compare the deployed application revision with this source ref; separately review trusted telemetry or client-generation code to determine whether catch local_id values can be exposed, reused, or predicted across vessels.

## backend.contacts.future-timestamp-anomaly-suppression — Future-dated contacts can postpone contact-delay anomaly scoring

**Boundary and candidate:** A holder of the gateway ingest credential can submit a live contact with an arbitrarily future observed_at. The evaluator orders and selects contacts by that timestamp, anchors the next-contact window to it, and clamps negative lateness to zero, so inter-contact delay scoring can remain normal until the future-derived window passes. This does not suppress an already-overdue explicit expected_return_at, which the scorer independently applies as a maximum overdue factor.

**Verified source trace:**
1. **entrypoint** — backend/app/api/contacts.py:61 (ContactEventIn.observed_at). The gateway-authenticated request accepts any parseable datetime without a maximum future-skew validator.
2. **propagation** — backend/app/api/contacts.py:107 (ingest_contact). The caller-supplied observed_at is written directly to buoy_contacts.
3. **propagation** — backend/app/ai/anomaly_service.py:85 (_group_latest_trips). The greatest stored contact timestamp selects the latest trip for each vessel.
4. **propagation** — backend/app/ai/trip_profile.py:353 (expected_next_contact). The final contact timestamp becomes the base for the expected next-contact window.
5. **sink** — backend/app/ai/trip_profile.py:502 (score_trip). Lateness is clamped to zero while the server-clock evaluation time remains before the future-derived window end, preventing an inter-contact overdue factor during that interval.

**Supporting evidence:**
- backend/app/api/contacts.py:61 — Unlike the pressure-ingest model, the contact model has no validator that rejects timestamps ahead of the server clock.
- backend/migrations/002_simulation.sql:17 — The contact occurrence time is stored as an unconstrained TIMESTAMPTZ column.
- backend/app/api/anomaly.py:86 — Evaluation uses the server clock as as_of, so a stored future contact remains ahead of the scoring clock rather than advancing evaluation time.
- backend/app/ai/trip_profile.py:364 — The expected-window end is computed by adding the learned interval and padding to last_contact_at.
- backend/app/ai/trip_profile.py:515 — An explicit expected_return_at is compared independently with the server clock and, when overdue, replaces the contact-delay factor via max at line 518; that is a containment boundary on the claim.

**Decisive blockers:**
- This audit environment cannot provide the required OS-enforced no-network, empty-environment, read-only-target, scratch-only-write, resource-limited sandbox, so the target-controlled Pydantic model and scoring code were not executed and the predicted accepted input and score transition were not independently observed.

**Safe resolution plan:**
**Bounded local validation:** Inside the required sandbox, instantiate ContactEventIn with a live contact whose observed_at is one day after a fixed as_of and verify model acceptance; then construct a minimal VesselProfile and matching ContactPoint, call score_trip at that fixed as_of, and compare its overdue factor/status with an otherwise identical realistically timed contact. Assert that the future-dated case has zero inter-contact overdue factor until its derived window passes, and separately assert that a past expected_return_at still produces the return-overdue factor so validation does not overstate the impact.

## backend.contacts.optional-position-crash — Optional contact coordinates can abort shared anomaly evaluation

**Boundary and candidate:** The gateway contact contract permits latitude and longitude to be omitted and persists those omissions as nullable database values. The shared anomaly evaluator loads every live contact and converts both coordinates with float(...) before trip eligibility or per-vessel isolation, so one contract-valid positionless row can potentially abort the whole operator-triggered or scheduled evaluation rather than only excluding that contact.

**Verified source trace:**
1. **entrypoint** — backend/app/api/contacts.py:67 (POST /api/v1/contacts). A holder of the gateway API key can submit a ContactEventIn object; its latitude and longitude fields default to None when omitted.
2. **propagation** — backend/app/api/contacts.py:94 (ingest_contact database insert). The route inserts payload.latitude and payload.longitude directly into buoy_contacts, including None values, and returns the request as accepted when the remaining constraints pass.
3. **propagation** — backend/app/ai/anomaly_service.py:55 (_load_trip_rows). The evaluator selects latitude and longitude for every in-scope live contact without requiring either column to be non-null.
4. **sink** — backend/app/ai/anomaly_service.py:78 (_group_latest_trips). Every loaded row is converted into a ContactPoint using float(row['latitude']) and float(row['longitude']) before freshness, trip-state, or per-vessel filtering; a null value therefore reaches an unguarded numeric conversion on the shared evaluation path.

**Supporting evidence:**
- backend/app/api/contacts.py:62 — ContactEventIn declares latitude and longitude as optional float fields with None defaults.
- docs/04_INGEST_API.md:150 — The published gateway contract explicitly marks latitude and longitude as optional when the buoy lacks a position.
- backend/migrations/002_simulation.sql:18 — The latitude and longitude columns are added without NOT NULL constraints, so the database does not reject an omitted position.
- backend/app/api/contacts.py:108 — The ingest insert binds payload.latitude and payload.longitude directly and has no paired-presence or required-position validation.
- backend/app/ai/anomaly_service.py:63 — Production evaluation selects all rows labelled live and supplies no coordinate non-null predicate.
- backend/app/ai/anomaly_service.py:136 — Trip eligibility begins by calling _group_latest_trips, so the coordinate conversion occurs before stale, completed, or cancelled contacts can be excluded.
- backend/app/api/anomaly.py:89 — The protected operator evaluation route calls the same evaluate_and_persist path without containing failures for one malformed contact or vessel.
- backend/app/ai/run_anomaly_evaluation.py:35 — The scheduled one-shot evaluator calls the same shared function and has no exception handling that would continue past a failed evaluation.

**Decisive blockers:**
- The required OS-enforced execution sandbox is unavailable in this Windows workspace: an empty allowlisted environment, isolated no-network namespace, read-only target and toolchain, scratch-only process writes, explicit CPU/memory/process/file/disk limits, and race-safe artifact promotion cannot all be enforced. Target-controlled Python, FastAPI, Pydantic, database fixtures, and tests were therefore not executed, so the exact exception, HTTP status, transaction behavior, and scheduled-job effect have not been independently observed.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved no-network sandbox, instantiate ContactEventIn from a valid live gateway payload that omits latitude and longitude and assert the parsed values are None; use a bounded fake async connection whose contact query returns that stored-shape row, invoke evaluate_and_persist once at a fixed UTC clock, and record whether conversion raises before any score/profile/case write. Then add the same row alongside a valid second vessel to determine whether the single row prevents the entire evaluation batch rather than only its own trip.
**Owner-observed deployment validation:** Without sending audit traffic, have the owner query for live buoy_contacts where latitude or longitude is null, inspect scheduler and application logs for failed anomaly evaluations at anomaly_service.py coordinate conversion, and compare the last successful evaluation timestamp with the first such row. Record only configuration/log/database observations and redact vessel identifiers and credentials.

## backend.current-ingest.unbound-calibration-claim — Gateway current ingest can self-assert production calibration status

**Boundary and candidate:** A holder of the gateway API key can submit current observations labelled as live and qualified without supplying or matching a server-known instrument or calibration record. Those labels are the qualification predicates used by the production current-field loader, so sufficiently fresh and spatially distributed claimed readings can contribute to a responder drift run and its persisted environmental status. The source path is concrete, but the actual trust delegated to gateways, any out-of-repository calibration binding, and a bounded observed result remain unresolved.

**Verified source trace:**
1. **entrypoint** — backend/app/api/current_events.py:48 (POST /api/v1/current-events). The current-event route admits requests authenticated by require_gateway_key; the realistic lower-trust principal is a process or gateway holding that bearer secret.
2. **propagation** — backend/app/api/contacts.py:29 (require_gateway_key). Authentication compares the request to one environment-provided GATEWAY_API_KEY and does not resolve a per-gateway identity, buoy scope, instrument, or calibration authority.
3. **propagation** — backend/app/api/current_events.py:37 (CurrentEventIn.calibration_status). The request body itself may select qualified, uncalibrated, or synthetic calibration status; source is likewise caller-selected on the preceding line.
4. **propagation** — backend/app/api/current_events.py:80 (ingest_current_event database insert). The endpoint stores payload.calibration_status directly alongside the caller-selected source, with no calibration-record or instrument binding in the insert path.
5. **propagation** — backend/app/ai/current_field.py:63 (_load_buoy_observations qualification predicate). The production loader accepts rows whose caller-stored calibration_status is 'qualified' (and legacy NULL), without selecting instrument_id or resolving a calibration record.
6. **propagation** — backend/app/api/drift.py:243 (_compute_and_persist_run production current-field construction). A real-case drift run builds its current field from the qualified live rows with synthetic fallback disabled.
7. **sink** — backend/app/api/drift.py:366 (_compute_and_persist_run drift_runs persistence). After geometry, coverage, and wind checks, the result is persisted with environmental_status='ok' when the assessment is sufficient, making accepted current rows part of an operator-facing safety decision artifact.

**Supporting evidence:**
- backend/app/api/current_events.py:36 — The request chooses source as live or synthetic, and only the synthetic branch receives the additional demo gate.
- backend/app/api/current_events.py:65 — The complete INSERT column list stores source and calibration_status but omits the existing instrument_id column and any calibration-record identifier.
- backend/app/ai/current_field.py:74 — Production selection accepts non-synthetic live rows (and legacy NULL source), then accepts the stored qualified label (and legacy NULL calibration) without reading instrument_id.
- backend/app/api/drift.py:234 — The production geometry gate counts nearby fresh buoys through the same qualified observation loader path.
- backend/migrations/025_drift_qualification_and_provenance.sql:5 — The schema adds instrument_id for observation provenance, but current ingest neither accepts nor resolves it.
- docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md:225 — The repository's D1 invariant explicitly says a caller-provided label alone cannot manufacture a calibration record.
- docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md:241 — The documented qualification contract requires instrument identity and a calibration record/version in addition to depth, timing, and uncertainty.
- docs/04_INGEST_API.md:22 — The contract describes per-gateway keys and revocation, while the implementation visible in require_gateway_key uses one shared environment secret without a server-side gateway record.
- docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md:31 — Physical in-water current instruments and buoy deployments are explicitly pending, so an actual operationally affected current-data path cannot be inferred from source alone.

**Decisive blockers:**
- The required OS-enforced execution sandbox is unavailable in this Windows workspace, so no target-controlled API/database/drift fixture was run to observe the minimum accepted-row-to-production-status result.
- The repository does not establish whether every holder of the deployed GATEWAY_API_KEY is intentionally delegated calibration authority or whether an external provisioning system binds each key, gateway, buoy, instrument, and current calibration record before data reaches this endpoint.
- The repository states that physical in-water buoys and current-reference instruments are still pending deployment, so the presence of real qualified current rows and the concrete operator/resource impact are deployment facts rather than source-visible facts.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved no-network, empty-environment, read-only-target sandbox with a disposable PostgreSQL fixture, register two dummy buoy rows at distinct coordinates with no instrument or calibration association. Using one dummy GATEWAY_API_KEY, submit two fresh POST /api/v1/current-events bodies with source='live' and calibration_status='qualified'; assert that the stored rows have instrument_id NULL yet are returned by _load_buoy_observations and counted by count_nearby_fresh_buoys. Invoke _compute_and_persist_run with a deterministic local predict_drift test double that calls the real current field once and returns a non-degraded result, then assert that one dummy drift_runs row receives environmental_status='ok'. Repeat the ingest, loader, and count checks with calibration_status='uncalibrated' and assert exclusion. Stop after these assertions and send no external traffic.
**Owner-observed deployment validation:** Without sending audit traffic, have the backend and hardware owners inspect the deployed gateway credential registry, provisioning records, and one redacted current-observation lineage record. Confirm whether keys are truly per gateway and revocable, which gateway may report which buoy, where instrument and calibration-record/version are bound, whether source/calibration labels are derived from authenticated device state rather than request text, and whether any physical current sensors have been commissioned for production drift decisions.

## backend.demo-weather.unbounded-coordinate-expansion — Demo weather coordinate cardinality is not application-bounded

**Boundary and candidate:** When DEMO_MODE is enabled and a scenario is active, an unauthenticated caller can supply arbitrarily many comma-separated coordinate cells at the application layer. The handlers synchronously parse and copy those cells and construct one JSON response object per pair in the demo FastAPI process. The repository proves the amplification path, but not that the largest request accepted by the real ingress can cause a concrete availability loss; the documented deployment also isolates the demo from production.

**Verified source trace:**
1. **entrypoint** — backend/app/api/demo.py:123 (weather_forecast route). Registers the demo forecast GET route without the require_demo_key dependency used by the control routes.
2. **propagation** — backend/app/api/demo.py:125 (weather_forecast parameters). Accepts latitude and longitude as unrestricted optional query strings; no max_length or coordinate-count constraint is declared.
3. **propagation** — backend/app/demo/weather.py:10 (_number_list). Splits every comma-delimited item and materializes a float list whose size follows caller-controlled input cardinality.
4. **propagation** — backend/app/demo/weather.py:20 (coordinates). Materializes a second list containing every paired latitude and longitude after checking only equal, non-zero lengths.
5. **sink** — backend/app/demo/weather.py:52 (forecast). Builds a response list with one nested response object for every caller-supplied coordinate pair.

**Supporting evidence:**
- backend/app/api/demo.py:128 — The forecast route passes parsed cells directly to the linear response builder after requiring only that a demo scenario is active.
- backend/app/api/demo.py:131 — The marine route repeats the same public, unconstrained input path.
- backend/app/demo/weather.py:66 — The marine response builder also emits one nested object for every supplied coordinate pair.
- backend/app/main.py:139 — The entire demo router is reachable only when DEMO_MODE has an explicitly truthy value.
- docs/29_DEMO_IMPLEMENTATION_PLAN_LUNA.md:101 — The documented design places the demo on a separate Railway service and database, so this path does not directly threaten the production service.
- docs/29_DEMO_IMPLEMENTATION_PLAN_LUNA.md:480 — The weather routes intentionally omit X-Demo-Key because browser code calls them without custom headers.
- render.yaml:17 — The checked-in production service environment list does not enable DEMO_MODE, so current public reachability of a separate demo deployment is not established by repository configuration.

**Decisive blockers:**
- Repository source does not establish whether a DEMO_MODE=true service is currently deployed, or the effective request-target, concurrency, rate, timeout, CPU, and memory limits applied by its Railway ingress and runtime.
- The required OS-enforced sandbox controls are unavailable in this Windows workspace, so the largest ingress-accepted request and its effect on concurrent demo control or health requests could not be measured safely; source alone does not demonstrate a service interruption or material latency increase.

**Safe resolution plan:**
**Bounded local validation:** In an approved no-network, isolated-loopback sandbox with an empty allowlisted environment, read-only target and toolchain, scratch-only writes, and strict CPU, memory, process, file-size, disk, and wall-clock limits, run a single disposable demo ASGI worker with dummy state. Send progressively larger but pre-bounded paired coordinate queries, stopping at the first parser rejection or predefined latency or memory ceiling; record the maximum accepted cardinality, response size, peak memory, request latency, and latency of one concurrent /healthz request. Confirm a vulnerability only if one accepted bounded request causes a repeatable owner-observable availability loss to another request.
**Owner-observed deployment validation:** Without sending audit traffic, have the owner verify whether the separate demo service currently has DEMO_MODE enabled and record its ingress request-target limit, worker count, concurrency and rate controls, request timeout, and memory/CPU quota. Review existing provider metrics and logs from legitimate demo use for request rejection, worker restart, memory exhaustion, or delayed health/control requests; the tracked Render production service should remain out of scope because its manifest does not enable DEMO_MODE.

## backend.hotspots.minimum-cohort-policy-drift — Public hotspot aggregation uses three reporters despite the canonical five-reporter privacy floor

**Boundary and candidate:** The anonymous catch-activity endpoint publishes coarse activity cells once three distinct vessel identifiers contributed consented records. The newer active canonical architecture requires a minimum anonymity cohort of five independent vessels, so the implementation can disclose the presence and relative activity of a smaller fishing group than the repository's stated privacy invariant permits. Exact vessel identifiers and source coordinates are not returned, which contains but does not eliminate the documented cohort-policy mismatch.

**Verified source trace:**
1. **entrypoint** — backend/app/api/hotspots.py:74 (GET /api/public/hotspots). An anonymous caller invokes the public hotspot route.
2. **propagation** — backend/app/api/hotspots.py:16 (MIN_REPORTERS). The implementation fixes the minimum distinct-vessel cohort at three.
3. **propagation** — backend/app/api/hotspots.py:41 (aggregate_hotspots eligibility filter). A cell becomes eligible when its distinct vessel-id count reaches the three-reporter constant.
4. **sink** — backend/app/api/hotspots.py:99 (public_hotspots response). Eligible cells are returned publicly with a coarse center, score, observation count, and reporter count.

**Supporting evidence:**
- docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md:13 — The active specification identifies itself as the canonical end-to-end architecture and data-flow model.
- docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md:227 — The canonical catch-activity flow publishes only after the reporter threshold k >= 5 is met.
- docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md:256 — The non-negotiable fisher-privacy rule names a minimum reporter threshold of k >= 5.
- docs/05_PUBLIC_API.md:743 — The older implemented API contract documents min_reporters as three, corroborating the source-visible policy drift rather than refuting it.
- backend/tests/test_hotspots.py:21 — The source test constructs exactly MIN_REPORTERS distinct vessels and expects the cell to be published, but it follows the implementation constant symbolically and therefore does not enforce the canonical value five.

**Decisive blockers:**
- The current Windows audit workspace cannot enforce the required empty-environment, no-network, read-only-target, scratch-only, resource-limited execution sandbox, so the three-vessel aggregation result was not independently executed.
- Repository source establishes a newer canonical k >= 5 rule and an older API contract at three, but no recorded owner acceptance reconciles that conflict or documents that the canonical privacy floor was intentionally reduced.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved isolated sandbox, call aggregate_hotspots with synthetic rows in one 0.02-degree cell: two, three, four, and five distinct vessel_id values. Record that two is withheld while three and four produce a public cell, then compare that bounded result with the canonical k >= 5 invariant; do not start a service or contact a deployment.
**Owner-observed deployment validation:** Have the architecture/privacy owner review the source-visible 3-versus-5 conflict and record the approved minimum cohort. Separately, have the deployment owner inspect the deployed revision or configuration and existing response metadata to state the live min_reporters value without generating catch records or sending audit traffic.

## backend.mesh.unbounded-public-storage — Anonymous mesh chat can accumulate rows without a source-visible retention control

**Boundary and candidate:** Every schema-valid request to the public mesh-chat write route reaches an unconditional database insert. Individual fields and history reads are bounded, but repository source shows no deduplication, aggregate quota, expiry, cleanup job, or application rate limit for stored chat rows; whether anonymous traffic can exhaust the deployed database or disrupt shared service remains dependent on external edge controls and database capacity.

**Verified source trace:**
1. **entrypoint** — backend/app/api/mesh.py:42 (POST /api/mesh/chat (ingest_chat)). An anonymous caller can submit any MeshChatIn payload that satisfies the per-field validation bounds.
2. **sink** — backend/app/api/mesh.py:47 (ingest_chat database write). The handler unconditionally executes INSERT INTO mesh_chat and returns the newly persisted row; no request identity, deduplication key, aggregate quota, or retention check occurs on this path.

**Supporting evidence:**
- backend/app/main.py:58 — The mesh router is deliberately registered without an authentication dependency because hubs and fishers have no accounts.
- backend/app/api/mesh.py:23 — Sender and message text have per-request length bounds (64 and 256 characters), which contain row size but do not limit the number of rows.
- backend/app/api/mesh.py:72 — History reads are capped at 200 rows, containing response size but not persistent table growth.
- backend/migrations/010_mesh_chat.sql:4 — The table stores each message with a generated identifier and creation timestamp; the schema has no expiry column or storage-quota constraint, and repository search found no mesh_chat deletion or cleanup path.
- render.yaml:1 — The source blueprint provisions the shared PostgreSQL service but exposes no chat-specific retention, quota handling, or edge throttling configuration; the live provider state is external.

**Decisive blockers:**
- The deployed request path's effective anonymous throttling, proxy or WAF controls, and the active database plan's storage quota, alerting, and quota-failure behavior are external to the repository; without those facts, meaningful availability impact cannot be established.
- The required OS-enforced execution sandbox is unavailable in this Windows workspace, so independent bounded observation of valid request-to-row growth against a disposable PostgreSQL instance was not permitted.

**Safe resolution plan:**
**Bounded local validation:** Inside the required no-network, read-only-target sandbox, provision a disposable PostgreSQL database in scratch, start the backend with only allowlisted dummy settings and strict resource/time limits, submit exactly 25 distinct schema-valid POST /api/mesh/chat requests through the native ASGI/HTTP interface, then compare mesh_chat row count and relation size before and after. Confirm whether all 25 rows persist and whether any cleanup or throttling activates, then destroy the scratch database.
**Owner-observed deployment validation:** Without sending audit traffic, have the service owner inspect the active ingress and database configuration and record: any enforced per-client or route-specific POST /api/mesh/chat rate limit, the current database storage quota and usage, retention or scheduled cleanup for mesh_chat, alert thresholds, and provider behavior when the quota is reached. Use those observed controls and capacity facts to decide whether sustained anonymous row creation can plausibly impair the shared database or backend.

## backend.operator-jwt.no-server-revocation — Operator bearer tokens have no server-side invalidation before expiry

**Boundary and candidate:** Source shows that dashboard logout only removes the browser's copy of an operator JWT, while protected requests continue to trust the signed role claims until the token expires. A copied bearer token could therefore continue authorizing shared safety mutations after that operator logs out; the required bounded runtime replay was not executed in this source-only audit.

**Verified source trace:**
1. **entrypoint** — backend/app/api/sea_condition.py:85 (POST /api/sea-condition). A caller presents an operator bearer token to a responder-role-protected route that changes shared operational safety state.
2. **propagation** — backend/app/auth.py:103 (require_user). The dependency accepts the bearer credential and reconstructs identity and role solely from JWT claims; its validation path performs no user, session, or revocation lookup.
3. **propagation** — backend/app/auth.py:138 (require_roles._dep). Authorization compares the role carried by the already-decoded token with the allowed roles, so a copied token retains its original authority until expiry.
4. **sink** — backend/app/api/sea_condition.py:102 (set_current database mutation). An accepted token reaches the database write that publishes the current sea condition to the shared safety system.

**Supporting evidence:**
- web/js/profile.js:279 — The logout handler only removes aqoneToken, aqoneUser, and the demo flag from sessionStorage before redirecting; it makes no backend logout or revocation request.
- backend/app/auth.py:94 — decode_token accepts a correctly signed, unexpired HS256 token and has no session or account-state input.
- backend/app/auth.py:69 — create_token embeds user identity, email, role, issue time, and expiry directly in the operator JWT without a revocable session identifier or token version.
- backend/migrations/005_auth.sql:7 — The operator users schema contains identity, password hash, role, creation time, and last-login time but no account-disable, session-version, or token-revocation state.
- docs/guides/07_SECURITY.md:20 — The project threat model explicitly identifies stolen-JWT impersonation and says it is only partly mitigated by short expiry and HTTPS.
- docs/guides/07_SECURITY.md:63 — The security guide describes operator bearer JWTs as having a 12-hour expiry.
- render.yaml:26 — The checked-in Render blueprint overrides JWT_EXPIRY_HOURS to 168 hours, extending the source-configured exposure window to seven days if that blueprint value is active.

**Decisive blockers:**
- This audit's Windows workspace cannot enforce the required no-network, empty-environment, read-only-target, scratch-only, resource-limited execution sandbox, so no target-controlled backend or browser session was run and no post-logout replay response was observed.
- The repository documents client-side logout and stolen-JWT residual risk but does not state whether operator logout is required to invalidate every copied token immediately; the owner's intended revocation policy and the deployment's effective JWT expiry or compensating session controls are not source-visible.

**Safe resolution plan:**
**Bounded local validation:** In an approved isolated sandbox with a disposable database and dummy operator, set a short nonzero JWT lifetime, obtain one token through POST /api/login, use it once against a disposable protected mutation, perform the dashboard's logout action, then replay the exact saved Authorization bearer value against a second disposable mutation before expiry. Record the HTTP status and whether the dummy row changes; do not use real accounts, incidents, or deployments.
**Owner-observed deployment validation:** Without sending audit traffic, have the owner inspect the effective JWT_EXPIRY_HOURS and any provider-side session or secret-rotation controls, and state whether logout, credential administration, role change, or account disablement is required to invalidate already-issued operator tokens. Compare those facts with any existing routine authentication logs rather than creating a live replay.

## backend.public-sea-condition.operator-identity-disclosure — Public sea-condition response may disclose operator account identifiers

**Boundary and candidate:** The unauthenticated sea-condition feed reuses the authenticated serializer and therefore includes both the operator user ID and a value populated from the operator account email. The public-route comment calls this a setter name, while mobile source says the public endpoint omits it, so the approved public attribution contract is unresolved.

**Verified source trace:**
1. **entrypoint** — backend/app/api/public.py:110 (public_sea_condition). An anonymous caller can invoke GET /api/public/sea-condition; the public router is mounted without an authentication dependency in backend/app/main.py:99-102.
2. **propagation** — backend/app/api/public.py:120 (public_sea_condition). The handler selects the complete latest sea_conditions row, including its setter fields.
3. **propagation** — backend/app/api/sea_condition.py:29 (_serialise). The shared serializer copies both set_by_user_id and set_by_name into the response object.
4. **sink** — backend/app/api/public.py:126 (public_sea_condition). The handler returns the unredacted serialized object to the anonymous caller.

**Supporting evidence:**
- backend/app/main.py:102 — The public router is included before the blanket authenticated routers and without a dependency, explicitly making its safety feeds unauthenticated.
- backend/app/api/sea_condition.py:111 — The declaration write path stores user.get('email') in set_by_name, so the public field is an account email rather than a separately approved public display label.
- backend/app/api/public.py:114 — The public handler says the handset should show a setter's name and timestamp, establishing intended attribution but not approval to publish the operator's account email or internal user ID.
- mobile/lib/models/sea_condition.dart:87 — The mobile model documents setByName as available only from the authenticated endpoint.
- mobile/lib/models/sea_condition.dart:171 — A second mobile comment expressly states that the public endpoint omits set_by_name, conflicting with the current backend serialization.
- backend/migrations/004_dashboard.sql:11 — The stored row has separate set_by_user_id and set_by_name columns, both of which the shared serializer exposes.

**Decisive blockers:**
- The required OS-enforced execution sandbox was unavailable, so the anonymous route could not be invoked against a bounded fake database row to observe the exact emitted payload.
- Repository intent conflicts: the backend public handler intends human attribution, while the mobile model says public responses omit the setter. An owner decision is required on whether anonymous clients may receive no actor, a non-identifying public display label, or operator account identifiers such as email and user ID.

**Safe resolution plan:**
**Bounded local validation:** In an approved no-network sandbox, use a fake pool returning one sea_conditions row with set_by_user_id='42' and set_by_name='operator.audit@example.invalid'; invoke public_sea_condition without Authorization and capture only whether current.set_by_user_id and current.set_by_name are present, then compare that shape with the approved public attribution contract.
**Owner-observed deployment validation:** Without generating audit traffic, have the deployment owner inspect an existing sanitized response or server-side response trace for GET /api/public/sea-condition and confirm whether real account email/user ID values are emitted; separately record the product/privacy owner's approved anonymous attribution fields.

## backend.public-squall.unbounded-history-load — Public squall feed loads all retained live pressure readings per request

**Boundary and candidate:** The unauthenticated handset squall route fetches every retained live barometric reading, converts and sorts the full result in process, and only then derives a 90-minute nowcast. The source-visible work grows with historical retention even though the response is bounded; whether anonymous request traffic can exhaust the deployed database or application process requires controlled measurement and deployment configuration evidence.

**Verified source trace:**
1. **entrypoint** — backend/app/api/public.py:419 (public_squall). Defines GET /api/public/squall on the intentionally unauthenticated public router.
2. **propagation** — backend/app/api/public.py:434 (public_squall). Each request calls _load_rows with live=True before building the bounded status response.
3. **propagation** — backend/app/api/squall.py:32 (_load_rows). Fetches live barometric readings ordered by time and buoy with no time predicate, LIMIT, or pagination.
4. **sink** — backend/app/ai/squall.py:233 (build_history). Converts the complete result into PressureReading objects, groups every row, and sorts each full per-buoy series in application memory.

**Supporting evidence:**
- backend/app/main.py:102 — Registers public_router without the bearer-token dependency used for protected routers.
- backend/app/api/squall.py:34 — The SELECT reads buoy_id, observed_at, and pressure_hpa from all rows matching only is_synthetic = live and orders the complete match set.
- backend/app/api/squall.py:93 — build_squall_status materializes history before the quality gate can discard stale or insufficient input.
- backend/app/ai/squall.py:410 — The 90-minute quality window is applied in Python by scanning already-loaded per-buoy series, not in the database query.
- backend/app/ai/squall.py:796 — When quality passes, current_detection builds another full in-memory history before extracting the bounded feature window.
- backend/migrations/002_simulation.sql:24 — barometric_readings is an appendable table with an observed_at column; the reviewed migrations define indexes but no row-count bound or retention constraint.

**Decisive blockers:**
- This workspace cannot provide the required OS-enforced no-network, empty-environment, read-only-target, scratch-only-write, low-resource sandbox, so the target ASGI/database path was not executed against controlled historical cardinalities.
- Repository source does not establish deployed live-row cardinality or age, request concurrency, reverse-proxy caching or throttling, database connection limits, or Render memory and request-time limits; those facts decide whether the source-visible amplification produces an availability failure.

**Safe resolution plan:**
**Bounded local validation:** Inside the approved isolated sandbox, seed a disposable PostgreSQL database with three buoys and the same fixed 90-minute recent window, then add bounded historical tiers (0, 10000, 50000, and 100000 older live rows). Invoke GET /api/public/squall through the native ASGI interface at concurrency 1 and 8 under explicit wall-clock, CPU, memory, process, and database-size caps; record fetched-row count, query duration, peak process RSS, connection occupancy, response status, and whether the cap terminates any tier. Compare against the identical fixture after removing the older rows.
**Owner-observed deployment validation:** Without sending audit traffic, have the owner inspect current barometric_readings live-row count and oldest observed_at, any retention/pruning job, edge-cache and anonymous throttling policy for /api/public/squall, application worker/concurrency settings, database pool limits, and provider memory/timeout metrics. Determine whether normal or observed anonymous request volume can overlap enough full-history loads to breach those limits.

## backend.sos.anonymous-incidents-crowd-dispatch-feed — Anonymous SOS rows can crowd genuine incidents out of the dispatcher feed

**Boundary and candidate:** When local_id is omitted or unique, the public SOS endpoint accepts caller-selected vessel and timestamp identities, persists each distinct pair as an unresolved incident, and can create related vessel and optional buoy rows. The protected dispatcher query returns only the newest 100 unresolved incidents, and the dashboard replaces its complete live list with that response, so more than 100 newer fabricated incidents could hide an older genuine SOS from the operator's current list and map.

**Verified source trace:**
1. **entrypoint** — backend/app/api/sos.py:123 (POST /api/sos). The SOS ingest route is mounted on the intentionally unauthenticated router and accepts a SosIn body without a credential dependency.
2. **propagation** — backend/app/api/sos.py:140 (ingest_sos vessel creation). Each previously unseen caller-selected vessel_id is inserted into vessels before the incident write; a supplied buoy_id similarly creates a buoy row at lines 154-162.
3. **propagation** — backend/app/api/sos.py:164 (ingest_sos incident persistence). The endpoint inserts an SOS row and resolves only an exact vessel_id/client_ts conflict through its upsert. A distinct pair inserts when the optional local_id is omitted or unique.
4. **propagation** — backend/app/api/sos.py:304 (GET /api/sos/active). The operator query includes unresolved rows, orders them newest-first, and caps the result at 100 at line 306.
5. **sink** — web/js/dashboard/dashboard-live-sos.js:241 (loadActiveSos). A successful poll clears the dashboard's liveAlerts collection and replaces it with only the bounded response; marker synchronization later removes events absent from that response.

**Supporting evidence:**
- backend/app/api/sos.py:80 — The model documentation explicitly states that this endpoint is deliberately unauthenticated.
- backend/app/api/sos.py:93 — vessel_id is caller supplied with only a 1-32 character length bound, client_ts at line 94 is an unrestricted integer used in the primary conflict identity, and local_id at line 103 is optional.
- backend/migrations/007_sos_ingest.sql:47 — The cross-transport uniqueness control covers the exact (vessel_id, client_ts) pair; the secondary partial unique index at lines 52-54 applies only when optional local_id is present, so omitting local_id permits each distinct pair to insert.
- backend/migrations/008_responder_loop.sql:32 — resolved_at is nullable with no expiry default; incidents remain unresolved until a later explicit resolution path updates them.
- backend/app/api/sos.py:305 — The active feed orders by server-side created_at descending and limits the unresolved result to 100, so newer accepted rows take precedence over older rows regardless of caller client_ts.
- web/js/dashboard/dashboard-live-sos.js:211 — Marker synchronization removes any previously displayed incident whose id is absent from the latest bounded feed.
- backend/app/main.py:65 — The application mounts the SOS ingest router outside the blanket authenticated router group; no application-level rate-limit middleware is visible in the dependency or application configuration.

**Decisive blockers:**
- The Windows audit workspace cannot enforce the required empty allowlisted environment, isolated no-network namespace, read-only target and toolchain, scratch-only writes, strict resource limits, and race-safe artifact promotion, so the FastAPI/PostgreSQL/dashboard path was not executed to independently observe the 101-row displacement result.
- Repository configuration does not establish whether the deployed ingress adds per-source throttling, bot filtering, request quotas, or other admission controls; those external controls are decisive for real-world exploit throughput and likelihood even though they do not change the source-visible feed cap.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved isolated sandbox, start a disposable PostgreSQL database and the application with synthetic credentials; seed one older unresolved genuine fixture, submit exactly 100 valid anonymous SOS fixtures with unique vessel_id/client_ts pairs and no local_id, then call GET /api/sos/active with a dummy operator token. Assert that the response contains 100 newer fixtures and omits the genuine fixture, pass that response through a bounded dashboard DOM harness, and assert that the genuine list row and marker are removed. Destroy the database and harness after the check.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner inspect and export the effective Render/CDN/WAF ingress policy for POST /api/sos, including per-IP or per-device throttles, burst limits, bot controls, bypass routes, alerts, and database/storage quotas, then record whether any control prevents one anonymous source or distributed sources from creating more than 100 unresolved incidents within the operator response window.

## backend.sos.untrusted-provenance-claims — Anonymous SOS can claim responder-confirmed and buoy provenance

**Boundary and candidate:** The intentionally unauthenticated SOS endpoint accepts the strongest responder trust label and caller-selected buoy transport metadata, writes those values into the incident, and returns them through the protected operator feed for the dashboard to present as trust tier and delivery path. Source review establishes the complete path but the required isolated FastAPI/PostgreSQL execution was unavailable, so persistence and read-back remain to be reproduced with disposable data.

**Verified source trace:**
1. **entrypoint** — backend/app/main.py:65 (application router registration). The SOS ingest router is mounted without an authentication dependency, making POST /api/sos reachable at the application boundary by an anonymous caller subject only to deployment ingress controls.
2. **propagation** — backend/app/api/sos.py:93 (SosIn request model). The anonymous request controls vessel identity and can supply trust_tier, buoy_id, src_id, seq, and source; source is limited to direct or buoy and the trust validator accepts every listed tier, including confirmed_by_responder.
3. **propagation** — backend/app/api/sos.py:164 (ingest_sos database upsert). The insert stores payload.trust_tier and caller-supplied buoy metadata, and derives delivered_via_buoy solely from payload.source == 'buoy'; an unknown buoy_id is created immediately beforehand rather than authenticated as a known gateway report.
4. **propagation** — backend/app/api/sos.py:294 (active_sos operator feed). The authenticated operator feed selects the stored trust_tier, delivered_via_buoy, and buoy_id and serializes them without a server-derived provenance qualifier.
5. **sink** — web/js/dashboard/dashboard-live-sos.js:168 (live SOS drawer rendering). The dashboard presents the stored fields to responders as a LoRa-mesh delivery path, named buoy, and trust tier.

**Supporting evidence:**
- backend/app/api/sos.py:60 — The source states the intended invariant that every identity remains self-declared until a responder confirms it, while line 70 includes confirmed_by_responder in the anonymous model's accepted set.
- backend/app/api/sos.py:115 — The trust-tier validator normalizes only unknown strings; it preserves the caller-selected confirmed_by_responder value.
- backend/app/api/sos.py:154 — Any supplied buoy_id is inserted into the buoys table if absent, so the foreign key is not an authenticity or registration control.
- backend/app/api/sos.py:193 — The database parameters include payload.trust_tier, buoy_id, src_id, and seq, and lines 198-199 set the delivery flags directly from the caller-selected source.
- docs/05_PUBLIC_API.md:232 — The public contract says an unauthenticated claim cannot confirm itself and that the SOS snapshot trust tier is what the dashboard shows.
- mobile/lib/models/sos_record.dart:225 — The legitimate handset payload forwards its locally stored trust tier, showing why the backend sees this field but not providing server-side authority for it.
- mobile/lib/data/identity_store.dart:286 — A client helper can apply and preserve confirmed_by_responder across profile edits, but no current call site invokes applyTrustTier; this latent client behavior is not required for the backend provenance claim.

**Decisive blockers:**
- This Windows workspace cannot enforce the audit workflow's required no-network, empty-environment, read-only-target, scratch-only-write, resource-limited sandbox, so the anonymous insert and authenticated operator read-back were not executed against a disposable PostgreSQL database.
- Source does not reveal whether a deployed reverse proxy or provider policy restricts POST /api/sos despite the application mounting it without authentication; no deployed endpoint was contacted.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved isolated no-network sandbox with a disposable PostgreSQL database, seed one dummy operator, start the application with only test configuration, then POST one bounded dummy SOS without credentials using trust_tier=confirmed_by_responder, source=buoy, buoy_id=UNTRUSTED-BUOY, src_id=4242, and seq=7. Authenticate only as the dummy operator, GET /api/sos/active, and record whether that same incident is returned with confirmed_by_responder, delivered_via_buoy=true, and UNTRUSTED-BUOY. Stop the app and delete the disposable database after this single read-back.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner inspect the effective ingress, reverse-proxy, and route policy for POST /api/sos and confirm whether anonymous Internet clients can reach it or whether an external gateway-authentication control exists; record the relevant policy/configuration and its scope.

## backend.trips.unbound-public-access — Public trip routes are not bound to a vessel or trusted reporter

**Boundary and candidate:** The trip router is mounted without an authentication dependency, and its create, patch, get, and list operations accept or select caller-chosen trip and vessel identifiers. If the mounted routes are externally reachable as shown, an anonymous caller can read another fisher's trip details or alter its expected-return, status, and welfare evidence; the same stored state is later consumed by anomaly evaluation. The source path is complete, but the bounded runtime result and effective deployment exposure were not observed under this audit's unavailable execution sandbox.

**Verified source trace:**
1. **entrypoint** — backend/app/main.py:97 (application router registration). Registers trips_router without the protected operator dependency or any other router-level authentication control.
2. **propagation** — backend/app/api/trips.py:143 (PATCH /api/v1/trips/{trip_id}). Accepts a caller-selected trip_id and optional status, welfare, expected-return, reporter, and amendment fields without a Depends-based principal.
3. **sink** — backend/app/api/trips.py:176 (update_trip database write). Updates vessel_trips by trip_id alone, with no vessel-ownership or trusted-reporter predicate.

**Supporting evidence:**
- backend/app/api/trips.py:82 — The public create handler accepts caller-selected trip_id, vessel_id, state, welfare, and reporter provenance and inserts those values without an authenticated principal.
- backend/app/api/trips.py:201 — The single-trip GET selects and serializes a complete trip solely by caller-supplied trip_id.
- backend/app/api/trips.py:212 — The list GET returns trip records globally or by caller-selected vessel/status filters without a principal scope.
- backend/app/ai/anomaly_service.py:174 — Anomaly evaluation loads vessel_trips state and uses it to select and score eligible trips.
- backend/app/ai/trip_profile.py:528 — The scorer treats stored welfare_status=safe as evidence that caps the overdue factor and distress as evidence that forces it to one.
- backend/app/api/catch.py:65 — A neighboring handset write path demonstrates the source-visible ownership pattern: validate a vessel-device credential and compare the body vessel_id with the token-bound vessel.

**Decisive blockers:**
- This Windows audit workspace cannot enforce the required empty allowlisted environment, isolated no-network namespace, read-only target and toolchain, scratch-only process writes, strict resource limits, and race-safe artifact promotion, so no target-controlled FastAPI/PostgreSQL fixture was executed to observe the unauthorized read or state change.
- Repository source does not establish whether an upstream deployment proxy or identity layer restricts /api/v1/trips despite the application mounting it without authentication.

**Safe resolution plan:**
**Bounded local validation:** Inside a compliant no-network sandbox with a disposable PostgreSQL database and dummy vessels only, mount the current FastAPI app, seed one trip owned by dummy vessel A, then issue unauthenticated GET /api/v1/trips, GET /api/v1/trips/{trip_id}, and PATCH /api/v1/trips/{trip_id} from dummy principal B. Stop after asserting whether the records are returned and whether welfare_status/expected_return_at persist for vessel A; optionally run one bounded anomaly evaluation to assert whether that persisted state changes the dummy trip score.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner inspect the effective proxy/identity and route policy for /api/v1/trips and confirm whether anonymous Internet clients can reach the application handlers or whether an upstream principal and vessel/resource scope is enforced.

## backend.vessel-profile.unbound-owner-write — Unauthenticated profile upsert can replace another vessel's responder identity

**Boundary and candidate:** An unauthenticated caller who obtains a vessel's identifier can submit that identifier as vessel_id and replace the stored skipper name, licence fields, phone number, and non-empty boat name. The protected active-SOS feed joins the current mutable vessel row and the dashboard renders those fields for responders, so a successful overwrite can substitute dispatcher-facing identity and contact information; the endpoint does not modify the incident's separate trust_tier.

**Verified source trace:**
1. **entrypoint** — backend/app/api/vessel_profile.py:33 (POST /api/vessel-profile). The route accepts a VesselProfileIn body without any authentication or vessel-device dependency.
2. **propagation** — backend/app/api/vessel_profile.py:49 (register_vessel_profile upsert). A conflict on the caller-selected vessel id updates boat_name, skipper_name, license_type, license_number, and phone on the existing row.
3. **propagation** — backend/app/api/sos.py:301 (active_sos). The protected active-SOS query joins the current vessel profile fields into every unresolved event for that vessel.
4. **sink** — web/js/dashboard/dashboard-incidents.js:69 (openSosDrawer). The responder drawer renders the joined owner identity, licence, and contact number as operational incident context.

**Supporting evidence:**
- backend/app/main.py:71 — The application includes the vessel-profile router outside the blanket authenticated router group and explicitly documents it as unauthenticated.
- backend/app/api/vessel_profile.py:25 — vessel_id is supplied by the request body rather than derived from a validated vessel-device principal.
- backend/app/api/vessel_profile.py:49 — ON CONFLICT updates the existing identity row selected by that vessel id, with no ownership predicate.
- backend/app/api/vessel_auth.py:46 — A separate operator-issued pairing-code and vessel-device credential design exists, but the profile route does not use it.
- backend/app/api/sos.py:301 — The dispatcher-only active feed returns the mutable skipper, licence, and phone fields from the vessel row.
- web/js/dashboard/dashboard-live-sos.js:157 — The live-SOS adapter places the joined skipper name, licence, and phone into responder drawer data.
- docs/05_PUBLIC_API.md:232 — The contract states that trust_tier is not accepted by this endpoint, containing the claimed write to profile identity fields rather than incident trust state.

**Decisive blockers:**
- The required OS-enforced execution sandbox was unavailable, so no isolated FastAPI/PostgreSQL request sequence demonstrated the cross-vessel overwrite and protected-feed readback at runtime.
- Live reverse-proxy, WAF, and provider route controls are not represented in repository source and were not owner-observed, so deployed unauthenticated reachability remains unknown.

**Safe resolution plan:**
**Bounded local validation:** In a disposable isolated PostgreSQL database and backend process with no external network, create two dummy vessels, attach one unresolved dummy SOS to vessel B, POST /api/vessel-profile without Authorization using vessel B's id and replacement identity fields, then authenticate only a dummy responder and GET /api/sos/active. Record whether the response and dashboard adapter expose the replacement fields; repeat after applying ownership binding and require the anonymous overwrite to fail while first registration follows the chosen pairing flow.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner inspect the active proxy/WAF/provider route configuration and application access logs to establish whether POST /api/vessel-profile is externally reachable without an upstream identity check, and document any control that binds the submitted vessel_id to the caller.

## backend.warning-delivery.unbound-state-authority — Warning delivery states are not bound to their documented authorities

**Boundary and candidate:** The backend mounts warning-delivery write and history routes without a route dependency or router-level authentication dependency. A caller can select an existing public advisory identifier, claim any lifecycle state and identifiers accepted by the schema, and request the resulting per-warning history; the source does not bind backend, gateway, buoy, handset, or fisherman authority to the state being recorded.

**Verified source trace:**
1. **entrypoint** — backend/app/api/advisories.py:421 (record_warning_delivery HTTP route). The POST route accepts WarningDeliveryIn directly and declares no responder, gateway, vessel-device, or other authentication dependency.
2. **propagation** — backend/app/api/advisories.py:414 (WarningDeliveryIn.validate_vessel_for_ack). Validation requires vessel_id only when the selected state is user_acknowledged; it does not establish that the caller controls that vessel or is the documented authority for the selected state.
3. **sink** — backend/app/api/advisories.py:457 (record_warning_delivery database insertion). Caller-selected warning, vessel, buoy, state, occurrence time, and details are inserted into warning_delivery_events after only advisory-existence and duplicate checks.

**Supporting evidence:**
- backend/app/main.py:113 — The application says advisories_router owns authentication per route and mounts it without the blanket protected dependency; therefore a route that omits its own dependency remains unguarded at application registration.
- backend/app/api/advisories.py:147 — A nearby operator advisory route explicitly receives require_responder_roles, showing the protection pattern that the delivery POST and GET omit.
- backend/app/api/advisories.py:432 — The only pre-insert state control after advisory existence is duplicate lookup on caller-supplied warning, state, vessel, and buoy values; no predecessor-state or principal-authority check is present.
- backend/app/api/advisories.py:484 — The delivery-history GET route also has no dependency and returns every event for a caller-selected advisory, including vessel_id, buoy_id, state, timestamps, and details.
- backend/app/api/advisories.py:156 — The intentional public advisory feed returns active published advisories, whose serialized representation includes the advisory id, so valid warning identifiers are not secret authorization capabilities.
- docs/06_DELIVERY_STATES.md:89 — The delivery contract assigns generated, gateway_accepted, buoy_received, phone_received, and user_acknowledged to distinct backend, gateway, buoy, handset, and fisherman authorities and requires deliberate interaction for user_acknowledged.
- firmware/shore/AqOneShore/AqOneShore.ino:510 — The real gateway consumer posts gateway_accepted with JSON content type but no authorization header, confirming that the current client contract relies on the route being unauthenticated rather than supplying a gateway identity.
- backend/tests/test_warning_transport.py:148 — The committed route test submits user_acknowledged without any authorization header, expects HTTP 200, then fetches the complete history without authorization; this audit did not execute the test.

**Decisive blockers:**
- This Windows audit workspace cannot enforce the required empty allowlisted environment, isolated no-network namespace, read-only target and toolchain, scratch-only process writes, explicit resource limits, and race-safe artifact promotion, so target-controlled FastAPI/TestClient code was not executed and the accepted unauthenticated mutation and disclosure were not independently observed.
- A deployment ingress policy could add a control not represented in the repository; the deployed route exposure was not probed, and the gateway source currently sends no authorization header.

**Safe resolution plan:**
**Bounded local validation:** Inside the required OS-enforced sandbox, use a bounded FastAPI TestClient fixture with a fake in-memory pool containing one dummy published advisory. Without an Authorization header, POST /api/advisories/delivery with {"warning_id":101,"delivery_state":"user_acknowledged","vessel_id":"dummy-victim","occurred_at":"2026-01-01T00:00:00Z","details":{"probe":true}}, then GET /api/advisories/101/deliveries without a header. Record whether both return 200, whether the dummy row is inserted, and whether the GET exposes the dummy vessel, state, times, and details; use no external network or real data.
**Owner-observed deployment validation:** Have the deployment owner inspect the effective ingress and application route policy for both warning-delivery paths and confirm whether any proxy or platform authentication is mandatory before requests reach FastAPI. Compare that policy with the gateway's headerless request implementation; do not send audit traffic to the live service.

## firmware.buoy.chat-starves-sos-tx-ring — Unauthenticated chat can contend with SOS for every LoRa transmit slot

**Boundary and candidate:** A nearby client on the intentionally open buoy access point can submit WebSocket chat messages that enter the same fixed, type-agnostic LoRa transmit ring used by distress frames. Source proves that a full ring defers an SOS enqueue while preserving the SOS for retry, but hardware execution is required to determine whether sustained chat can repeatedly win the scheduling window and quantify the resulting emergency-transmission delay.

**Verified source trace:**
1. **entrypoint** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:758 (onWsEvent). The phone-facing WebSocket handler accepts text events from clients on the open local access point without authenticating or rate-limiting the sender.
2. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:801 (onWsEvent msg branch). Each valid chat message calls meshSend(T_CHAT, ...) with a short delay, placing non-emergency work into the common outbound path.
3. **propagation** — firmware/buoy/AqOneBuoy/AqOneLoam.h:415 (txEnqueue). All frame types use a ten-slot first-free ring; enqueue has no type-aware priority, reservation, replacement, or eviction and returns false only when every slot is used.
4. **sink** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:412 (sosTransmit). When meshSend cannot enqueue the SOS because the transmit ring is full, the persisted SOS is not lost but its radio transmission is deferred for a later retry.

**Supporting evidence:**
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:77 — The buoy access point is intentionally configured without a password, so any nearby radio client can reach the phone-facing service.
- firmware/buoy/AqOneBuoy/AqOneLoam.h:388 — The shared outbound ring has exactly ten slots.
- firmware/buoy/AqOneBuoy/AqOneLoam.h:424 — A full ring drops the attempted frame from the in-memory transmit ring rather than reserving or reclaiming a slot for SOS.
- firmware/buoy/AqOneBuoy/AqOneLoam.h:538 — The radio service scans slots by array order and transmits the first due item, without inspecting frame type or preferring SOS.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:413 — The SOS path explicitly handles a full transmit ring as transient and schedules another attempt instead of losing the persistent SOS.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:1131 — Queued SOS retry service is invoked by a five-second sweep, creating a scheduling window in which chat can refill a newly freed slot before flushQueue runs.
- docs/02_LOAM_PACKET_SPEC.md:170 — The protocol contract requires SOS traffic to have absolute LoRa-channel priority and makes chat strictly subordinate.

**Decisive blockers:**
- Source inspection cannot establish whether the ESP32 WebSocketsServer event loop can accept and enqueue attacker chat at a rate that repeatedly refills the ring before the five-second SOS retry sweep on the actual SX1262 timing path.
- The required firmware execution environment and ESP32/SX1262 hardware were unavailable, and this Windows workspace could not enforce the audit's mandatory no-network, read-only-target, scratch-only, resource-limited execution sandbox, so no target-controlled timing test was run.
- The maximum added SOS latency and whether sustained chat can cause repeatable starvation rather than a bounded transient delay remain unobserved.

**Safe resolution plan:**
**Bounded local validation:** On an isolated bench with a lab buoy and dummy LoRa receiver disconnected from operational backends, submit one dummy SOS while one nearby test client sends bounded valid WebSocket chat for at most 15 seconds at a predeclared rate sufficient to fill the ten-slot ring. Capture serial enqueue/full-ring messages and receiver frame timestamps; compare SOS enqueue-to-first-radio-frame latency against an identical no-chat control, stop after the first dummy SOS frame or 15 seconds, and confirm the persistent SOS remains queued throughout any failed enqueue.

## firmware.buoy.sos-queue-untrusted-capacity — Nearby peers can consume every persistent buoy SOS queue slot

**Boundary and candidate:** The phone-facing buoy access point is intentionally open, and POST /v1/sos admits caller-selected vessel and timestamp pairs into a twelve-slot persistent store-and-forward queue without authenticating the sender, limiting admissions per peer, reserving capacity, or evicting lower-trust entries. A nearby peer that submits twelve distinct valid pairs may therefore make the next genuine offline handset receive HTTP 503 until a matching shore acknowledgement frees a slot; the handset's durable outbox and parallel direct-Internet attempt contain the effect to delayed buoy handoff when those alternatives eventually succeed.

**Verified source trace:**
1. **entrypoint** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:375 (setupWiFi). The buoy starts an open SoftAP with no password, so any nearby Wi-Fi peer can reach the phone-facing HTTP service subject only to radio range and the concurrent association limit.
2. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:449 (handlePostSos). The POST /v1/sos handler processes the request without a sender identity, authorization check, per-peer rate limit, or admission token.
3. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:463 (handlePostSos). Admission validation requires only a non-empty vessel_id and a nonzero client_ts before queue accounting.
4. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:473 (handlePostSos). Deduplication rejects allocation only when both vessel_id and client_ts exactly match an existing used slot, so distinct caller-selected pairs remain separately admissible.
5. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:505 (handlePostSos). A free slot is marked used and the entire queue is immediately saved to NVS, allowing admitted entries to survive reboot.
6. **sink** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:491 (handlePostSos). When all twelve slots are used, the next SOS request is rejected with HTTP 503 queue full rather than receiving reserved or priority capacity.

**Supporting evidence:**
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:128 — MAX_QUEUE fixes the persistent SOS queue at twelve entries.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:157 — queueSave serializes the complete queue buffer into NVS.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:170 — queueLoad restores a correctly sized queue buffer from NVS after restart.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:177 — queueFreeSlot returns only an unused slot and has no reservation, ownership, priority, expiry, or eviction logic.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:389 — The source states queued SOS records retry until shore acknowledgement and do not otherwise age out in this implementation.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:851 — Queue reclamation follows a positive acknowledgement for this node whose sequence matches one held by the queued item.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:864 — The matching acknowledgement clears used and persists the reclaimed queue state.
- mobile/lib/services/buoy_client.dart:118 — The handset maps the full-queue response to BuoyRejected(503, 'buoy queue full').
- mobile/lib/services/sos_service.dart:87 — The handset stores a genuine SOS in its durable local outbox before attempting transport, limiting immediate data loss.
- mobile/lib/services/sos_service.dart:155 — Buoy and direct backend transports are attempted in parallel, so working Internet can bypass a saturated buoy.
- mobile/lib/services/sos_service.dart:218 — When both paths fail, the SOS remains saved with a failure reason and periodic retry later reattempts pending records.

**Decisive blockers:**
- The audit environment cannot enforce the required isolated no-network namespace, empty allowlisted environment, read-only target/toolchain, scratch-only process writes, explicit resource limits, and race-safe artifact promotion, so the Arduino firmware or a source-faithful target-controlled harness was not executed.
- Repository source determines the admission and reclamation logic, but no isolated ESP32 bench observation establishes that twelve sequential valid HTTP requests persist as twelve occupied NVS slots and that a thirteenth genuine-shaped request receives 503 under the shipped Arduino/WebServer and Preferences libraries.

**Safe resolution plan:**
**Bounded local validation:** Inside a compliant no-network sandbox, build a minimal source-faithful harness with dummy WebServer and Preferences adapters around the unchanged queue and handlePostSos logic. Starting from an empty fake NVS image, submit twelve valid requests with distinct dummy vessel_id/client_ts pairs, assert twelve accepted responses and depth 12, submit one separate genuine-shaped dummy request and assert HTTP 503 with no overwrite, restart from the fake NVS image and assert depth remains 12, then inject one valid matching dummy mesh ACK and assert exactly one slot becomes available.
**Owner-observed deployment validation:** On an isolated non-operational bench buoy with no production gateway, identities, or radio traffic, clear test NVS; from one test handset submit twelve distinct dummy SOS pairs and record only response codes and /v1/status queue_depth, power-cycle and observe retained depth, submit a thirteenth dummy fisher request and observe whether it receives 503, then use the approved test shore fixture to send one correctly signed matching ACK and verify one slot is reclaimed. Stop after this minimum effect and erase the dummy queue before field use.

## firmware.loam.shared-default-key — Firmware source authenticates every LoRa source identity with one repository-known key

**Boundary and candidate:** At the audited commit, the buoy and shore firmware both compile the same development HMAC key and the decoder does not select a key by SRC_ID. A holder of that mesh-wide key could choose another device's SRC_ID, sign a syntactically valid frame, and have the shore path treat it as that origin, including forwarding a forged SOS to the backend. Whether deployed devices run this source/default and the bounded decoder result remain unobserved.

**Verified source trace:**
1. **entrypoint** — firmware/shore/AqOneShore/AqOneLoam.h:521 (radioService). The shore radio accepts packet bytes from a nearby radio peer and passes them to loamDecode.
2. **propagation** — firmware/shore/AqOneShore/AqOneLoam.h:300 (loamDecode). The decoder validates framing and recomputes one expected HMAC for every frame; it has no SRC_ID-to-key lookup or role-specific key selection.
3. **propagation** — firmware/shore/AqOneShore/AqOneLoam.h:257 (loamSign). HMAC-SHA256 is initialized with the single global LOAM_KEY while the signed bytes include attacker-selected type, SRC_ID, sequence, timestamp, and payload fields.
4. **propagation** — firmware/shore/AqOneShore/AqOneLoam.h:315 (loamDecode). After the shared-key comparison succeeds, the decoder exposes the packet-supplied SRC_ID as the authenticated frame origin.
5. **sink** — firmware/shore/AqOneShore/AqOneShore.ino:652 (onMeshFrame T_SOS branch). A decoded T_SOS from any source other than the shore node is parsed and passed to postSos, which forwards the supplied vessel data and decoded SRC_ID to the backend.

**Supporting evidence:**
- firmware/buoy/AqOneBuoy/AqOneLoam.h:86 — The buoy codec defines the repository-known development value as a global LOAM_KEY.
- firmware/shore/AqOneShore/AqOneLoam.h:86 — The shore codec defines the same repository-known development value as its global LOAM_KEY.
- firmware/shore/AqOneShore/AqOneLoam.h:310 — Verification calls loamSign before reading SRC_ID into the decoded frame and supplies no per-source key argument.
- firmware/platformio.ini:16 — The only buoy build flag configures WebSocket capacity; neither PlatformIO environment provides a key-provisioning or per-device key-selection mechanism.
- docs/02_LOAM_PACKET_SPEC.md:179 — The protocol contract requires the origin endpoint's key to be looked up by SRC_ID and states that production uses per-device keys.
- firmware/README.md:393 — The firmware documentation explicitly records that the HMAC key is shared and checked into git and that repository holders can inject mesh distress traffic until it is changed.

**Decisive blockers:**
- This Windows audit workspace cannot enforce the required no-network, empty-environment, read-only-target, scratch-only, resource-limited execution sandbox, so a compiled one-frame forge-and-decode fixture was not run and no accepted forged SRC_ID was observed locally.
- Repository source does not establish the provenance or effective key provisioning of firmware actually flashed to field devices; deployed images may differ from the audited development source.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved no-network sandbox, build the buoy and shore PlatformIO environments from this commit, then run a bounded decoder harness that signs one minimal T_SOS frame with the audited key while selecting a different dummy SRC_ID, feeds it to the shore decode path with postSos replaced by a local recording stub, and asserts that the stub receives that forged SRC_ID; repeat once with a different key and assert rejection. Retain only a predeclared small JSON result, never key material.
**Owner-observed deployment validation:** Without transmitting any radio traffic or disclosing keys, have the device owner attest the source commit and hashes of flashed buoy/shore images, the key-injection mechanism, distinct per-device key identifiers, and evidence that the shore selects a registered key by SRC_ID. If deployed images retain one global key or lack SRC_ID-based selection, treat cross-device origin forgery as exposed and rotate/provision before field use.

## firmware.shore.committed-uplink-credential — Concrete shore-uplink credential is committed in tracked firmware

**Boundary and candidate:** The tracked shore-gateway sketch contains a concrete Wi-Fi password literal and supplies it to the station connection API. Source proves repository disclosure and a live code path, but not whether the credential is still valid, reused, or present on a deployed gateway.

**Verified source trace:**
1. **entrypoint** — firmware/shore/AqOneShore/AqOneShore.ino:70 (UPLINK_PASS configuration). The tracked sketch defines a concrete credential literal in the gateway's configure-me section.
2. **sink** — firmware/shore/AqOneShore/AqOneShore.ino:105 (setupWiFi). The gateway passes the committed uplink SSID and password to WiFi.begin when joining its Internet uplink.

**Supporting evidence:**
- firmware/shore/AqOneShore/AqOneShore.ino:67 — Nearby comments describe these fields as the board's Internet connection for a real mast site or a demo hotspot; they do not label the concrete values as examples or inert placeholders.
- firmware/README.md:87 — Firmware setup documentation identifies UPLINK_SSID and UPLINK_PASS as shore-only configuration that operators must set.

**Decisive blockers:**
- Repository source cannot establish whether the committed credential is currently valid, belongs to a real network, is reused elsewhere, or was flashed to any deployed gateway; those facts require owner-side inventory rather than audit traffic.

**Safe resolution plan:**
**Owner-observed deployment validation:** Without attempting to authenticate or connect, have the network and gateway owner compare the redacted committed value against the current uplink or hotspot configuration, device provisioning records, and flashed firmware inventory; record whether it is valid or reused, then rotate it and remove it from tracked history if any match exists.

## firmware.shore.tls-peer-verification-disabled — Shore gateway disables backend TLS peer verification

**Boundary and candidate:** The current shore-gateway sketch routes every backend HTTPS request through one helper that explicitly disables certificate verification. If this sketch is flashed and an attacker can intercept or redirect the gateway's uplink, the attacker could impersonate the backend, receive dummy-equivalent operator login credentials or bearer authorization, and forge safety-traffic responses; source alone does not establish that this firmware is running on hardware or demonstrate the on-device result.

**Verified source trace:**
1. **entrypoint** — firmware/shore/AqOneShore/AqOneShore.ino:135 (httpsBegin). A TLS connection presented by an on-path or redirected network peer is accepted with certificate verification disabled.
2. **propagation** — firmware/shore/AqOneShore/AqOneShore.ino:227 (opsLogin). The operator-login request uses the same insecure helper for the configured HTTPS backend URL.
3. **sink** — firmware/shore/AqOneShore/AqOneShore.ino:237 (opsLogin). The gateway posts the serialized operator email and password to the unauthenticated TLS peer.

**Supporting evidence:**
- firmware/shore/AqOneShore/AqOneShore.ino:72 — BACKEND_HOST uses an HTTPS URL, so the defect is missing peer authentication rather than a cleartext scheme.
- firmware/shore/AqOneShore/AqOneShore.ino:131 — The source comment explicitly states that TLS certificates are not verified and that production should pin a CA.
- firmware/shore/AqOneShore/AqOneShore.ino:135 — The only shared HTTPS initializer calls client.setInsecure(); repository search finds no CA certificate or fingerprint configuration in the shore firmware.
- firmware/shore/AqOneShore/AqOneShore.ino:160 — SOS incident submission uses httpsBegin before posting incident data and treats HTTP 200 as backend receipt.
- firmware/shore/AqOneShore/AqOneShore.ino:388 — Acknowledgement polling uses httpsBegin and then sends the operator bearer token in the Authorization header.
- firmware/shore/AqOneShore/AqOneShore.ino:515 — Warning-delivery reporting also uses httpsBegin before posting gateway-accepted state.
- firmware/shore/AqOneShore/AqOneShore.ino:560 — Warning polling uses httpsBegin, checks only HTTP/JSON application behavior, and therefore has no independent server-identity control.
- README.md:26 — The repository status says neither shore nor pod sketch has run on hardware, leaving the actually flashed and deployed firmware state unresolved.

**Decisive blockers:**
- Repository source does not establish that a shore gateway has been flashed or deployed with this exact sketch; the project status states that neither firmware sketch has run on hardware.
- The audit environment lacks the required isolated execution sandbox and disposable ESP32/network harness needed to observe whether the compiled WiFiClientSecure client accepts an untrusted certificate and transmits only dummy credentials or safety payloads to that peer.

**Safe resolution plan:**
**Bounded local validation:** In an isolated lab with no route to production, flash a disposable ESP32 with the current shore sketch configured only with a mock backend and dummy operator credentials. Redirect its test Wi-Fi path to a bounded mock HTTPS server presenting a locally generated untrusted certificate; confirm whether login, bearer polling, one dummy SOS, and one dummy warning request reach the mock peer, then repeat after configuring a test CA to confirm fail-closed behavior for the untrusted certificate.
**Owner-observed deployment validation:** Without sending audit traffic, the device owner should inventory each shore gateway's flashed binary or reproducible source commit and configuration, confirm whether any gateway is active, and inspect whether its TLS client has a CA/fingerprint trust anchor or still uses setInsecure; record only firmware identity, trust-anchor mode, and uplink-network exposure.

## firmware.warning.missing-revision-tombstone — Buoy warning cache can accept stale signed warning state

**Boundary and candidate:** The shipped shore firmware emits changed advisories as new signed WARN frames but does not carry the contract-defined revision or cancellation state. A buoy authenticates each frame, then relies on a 64-entry RAM-only (source, sequence, type) seen set and unconditionally overwrites the cache slot for the same warning ID. A nearby peer with a captured older, still-unexpired authentic frame could replay it after its tuple is evicted; because the cache update has no revision or issue-order comparison, that replay may replace newer same-ID content. The production WARN path carries no cancellation or tombstone representation, and the seen set is cleared on reboot. The cache is exposed to offline handsets and pushed over WebSocket. Source establishes the path, but the compiled firmware and physical replay result were not independently exercised under the required sandbox.

**Verified source trace:**
1. **entrypoint** — firmware/buoy/AqOneBuoy/AqOneLoam.h:519 (radioService). The buoy reads an attacker-retransmittable LoRa frame from the radio, passes a frame with a valid existing HMAC through loamDecode, and dispatches it to onMeshFrame.
2. **propagation** — firmware/buoy/AqOneBuoy/AqOneLoam.h:343 (seenBefore and seenRemember). Replay detection checks only the bounded in-memory source, sequence, and type ring; entries are overwritten cyclically and are not durable.
3. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:927 (onMeshFrame T_WARN branch). An accepted WARN is keyed only by warning ID and the matching or first free cache slot is overwritten without any revision, cancellation, or issue-order comparison.
4. **sink** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:645 (handleGetWarnings). The resulting cached warning is serialized to the phone-facing /v1/warnings response; the same cache update is also broadcast to connected phones by the WARN handler.

**Supporting evidence:**
- firmware/shore/AqOneShore/AqOneShore.ino:530 — buildWarnPayload serializes ID, source, priority, area, timestamps, title, and text, but no revision or cancellation field.
- firmware/shore/AqOneShore/AqOneShore.ino:577 — pollWarnings notices content changes using an FNV signature and sends another WARN frame for the same ID, but that local signature is not transmitted as an ordering value.
- firmware/buoy/AqOneBuoy/AqOneLoam.h:300 — loamDecode validates framing and HMAC but does not reject an authentically signed frame based on age or a persisted message revision.
- firmware/buoy/AqOneBuoy/AqOneLoam.h:339 — The duplicate ring holds only 64 tuples, and seenRemember cyclically overwrites them at line 351.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:346 — CachedWarning stores no revision or cancellation/tombstone state.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:948 — The WARN handler overwrites the selected same-ID slot directly and marks it used; no monotonic comparison precedes the write.
- firmware/buoy/AqOneBuoy/AqOneBuoy.ino:1070 — Buoy setup clears the seen ring on every boot, so duplicate suppression is explicitly volatile.
- docs/02_LOAM_PACKET_SPEC.md:158 — The protocol contract defines revision ordering and states that an older revision must not resurrect a cancelled warning.
- backend/app/mesh/loam.py:239 — The repository's reference WarningCache enforces revision ordering and cancellation tombstones, demonstrating the intended control that the production firmware path lacks.

**Decisive blockers:**
- This audit workspace cannot provide the required OS-enforced empty-environment, no-network, read-only-target/toolchain, scratch-only-write, resource-limited firmware execution sandbox, so the compiled producer/decoder/cache/HTTP behavior was not independently reproduced.
- Repository source does not establish which firmware revision is flashed on field devices, whether a nearby peer can reliably capture and retransmit a complete signed WARN frame within radio range, or the resulting handset-visible behavior on the deployed hardware.

**Safe resolution plan:**
**Bounded local validation:** In an OS-enforced offline sandbox, compile a bounded harness around the current production LoAM decoder, seen-ring functions, WARN cache branch, and warning serializer. Generate two valid shore-shaped signed WARN frames with the same dummy ID, distinct sequences, and different titles; deliver old then new, evict the old tuple with exactly 64 benign unique tuples, replay the old frame, and serialize /v1/warnings. Stop after checking whether the old title replaced the new one. Repeat from a simulated reboot. Separately assert from the producer and frame shape that no revision or cancellation/tombstone field is emitted; do not invent a cancellation frame that the production path cannot generate.
**Owner-observed deployment validation:** On an isolated spare gateway, buoy, and dummy backend fixture with no production credentials or real alerts, emit an old and then updated advisory under one dummy ID, retain the old radio frame, clear only the spare buoy's duplicate state by controlled reboot or bounded ring turnover, retransmit the old frame, and read the spare buoy's local /v1/warnings response. Review the emitted test frame for revision/cancellation fields rather than sending a synthetic cancellation frame. Do not transmit on a live mesh or use a real warning ID.

## mobile.eta.server-clock-discarded — Handset discards authoritative server time when rendering rescue ETA

**Boundary and candidate:** The backend supplies server_time specifically so the handset can correct clock drift before rendering the server-authoritative eta_at, but each mobile read-back parser discards that envelope field. The app persists only eta_at and derives its notification, countdown, and overdue state from the handset wall clock. On an offline, manually mis-set, or materially drifted handset, the same rescue ETA can therefore appear already delayed when it is still in the future, or still in the future after it is overdue, affecting the fisher's emergency decisions. The field protocol assumes network-synchronized handsets, but the inspected application path neither enforces nor verifies that assumption.

**Verified source trace:**
1. **entrypoint** — backend/app/api/sos.py:485 (vessel_sos response envelope). The backend begins the handset read-back path by returning its authoritative server_time alongside event eta_at values; the adjacent source comment states that the handset should use it for clock-drift correction.
2. **propagation** — mobile/lib/services/backend_client.dart:377 (BackendClient.vesselSos). The client decodes the response envelope but reads only decoded['events']; server_time is neither parsed nor returned.
3. **propagation** — mobile/lib/services/sos_service.dart:474 (SosService._applyRemote). Reconciliation persists etaAt and responder fields without any server observation time or derived clock offset.
4. **propagation** — mobile/lib/models/sos_record.dart:86 (SosRecord.etaTime and etaOverdue). The stored absolute ETA is converted to local time with no server-clock correction; etaOverdue then compares it with the handset's DateTime.now().
5. **sink** — mobile/lib/ui/widgets/responder_eta_dialog.dart:57 (_ResponderEtaDialogState._countdown). The safety-critical responder dialog renders remaining time or delayed state by subtracting uncorrected handset DateTime.now() from eta_at.

**Supporting evidence:**
- backend/app/api/sos.py:487 — The backend explicitly documents server_time as the value the handset should use to correct clock drift before rendering eta_at.
- backend/app/api/sos.py:255 — The un-enrolled handset's single-event acknowledgement envelope also includes server_time, so the corrective value exists on both backend read-back routes.
- mobile/lib/services/backend_client.dart:381 — The credentialed vessel-feed parser selects only the events list from the decoded envelope.
- mobile/lib/services/backend_client.dart:415 — The un-enrolled acknowledgement parser selects only the event object from the decoded envelope and likewise drops server_time.
- mobile/lib/services/buoy_client.dart:206 — The buoy-proxied offline response parser selects only decoded['events'], so it also discards the verbatim backend server_time.
- mobile/lib/services/backend_client.dart:64 — RemoteSos parses eta_at but exposes no server time, observation time, or clock-offset field.
- mobile/lib/ui/app_shell.dart:260 — The system notification's rescue minutes and delayed/soon choice are computed against DateTime.now().
- mobile/lib/ui/widgets/delivery_state_tile.dart:232 — The persistent delivery-state tile independently computes its countdown against DateTime.now(), confirming the issue is not confined to one dialog.
- docs/50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md:58 — The field protocol assumes handsets are synchronized to network time, but this is an operational assumption rather than an application-enforced control visible in the inspected source.

**Decisive blockers:**
- This Windows workspace cannot enforce the audit's required no-network namespace, empty allowlisted environment, read-only target and toolchain, scratch-only process writes, explicit resource limits, and race-safe artifact promotion, so the Flutter parsers and widgets were not executed to obtain a bounded observed render result.
- Repository source does not establish whether deployed handsets enforce automatic network time, what clock error persists while they are offline, or whether device policy prevents manual clock changes; those runtime conditions determine real-world reachability and magnitude.

**Safe resolution plan:**
**Bounded local validation:** In an approved isolated Flutter test environment, feed BackendClient and BuoyClient dummy acknowledgement envelopes whose server_time is T and eta_at is T plus 20 minutes while the test process wall clock represents T plus 60 minutes, then T minus 60 minutes. Reconcile the dummy SosRecord and assert the current notification, ResponderEtaDialog, and DeliveryStateTile show delayed or about 80 minutes instead of the server-relative 20 minutes. Use only mocked HTTP responses and a temporary test database, with no external network.
**Owner-observed deployment validation:** On a dedicated non-production handset and an isolated local test backend or pod, create a dummy SOS acknowledgement with a known server_time and eta_at, place the handset in airplane mode, offset its clock forward and backward, and have the owner observe the rendered countdown and delayed state against the backend timestamps. Also record whether automatic network time is mandatory on intended field devices and the measured clock drift during the longest supported offline interval; do not use a live emergency or deployed endpoint.

## mobile.location.undisclosed-weather-coordinate-egress — Previously granted GPS is silently repurposed for weather-coordinate egress

**Boundary and candidate:** Opening Home automatically reuses a previously granted location fix and supplies its full latitude and longitude to AqOne's public forecast path and direct Open-Meteo weather paths. Successful forecast data can persist the requested and returned coordinates in SharedPreferences, while the in-app privacy policy says position is sent only as part of a deliberately submitted SOS.

**Verified source trace:**
1. **entrypoint** — mobile/lib/services/location_service.dart:75 (LocationService.cachedFixIfPermitted). A prior while-in-use or always grant authorizes this method to return the platform's last-known latitude and longitude, with no age or accuracy rejection, and to obtain a live fix if no cached position exists.
2. **propagation** — mobile/lib/ui/home_page.dart:102 (_HomePageState.initState). Home starts both current-weather and forecast loading automatically during initialization, without a weather-location consent action.
3. **propagation** — mobile/lib/ui/home_page.dart:182 (_HomePageState._loadWeather). The current-weather path passes the unrounded permitted fix directly to VentureFeeds.weather instead of the fixed municipal fallback.
4. **propagation** — mobile/lib/ui/home_page.dart:225 (_HomePageState._loadForecast). The periodic forecast path independently obtains the same permitted fix and passes its full coordinates into the forecast provider.
5. **sink** — mobile/lib/services/forecast_provider.dart:169 (AqOneForecastProvider.outlook). The device coordinates are interpolated into AqOne's public forecast query; the provider falls back to direct atmospheric and marine Open-Meteo requests carrying the same latitude and longitude.

**Supporting evidence:**
- mobile/lib/services/location_service.dart:80 — The helper checks only whether platform permission is already while-in-use or always; it performs no purpose-specific consent check.
- mobile/lib/services/location_service.dart:87 — The helper prefers getLastKnownPosition and returns its coordinates, accuracy, and timestamp without rejecting stale or inaccurate fixes.
- mobile/lib/services/venture_feeds.dart:91 — Current weather constructs a direct Open-Meteo URL containing the caller-supplied latitude and longitude and issues a GET request.
- mobile/lib/services/forecast_provider.dart:86 — The atmospheric fallback sends the latitude and longitude as query parameters to the configured Open-Meteo host.
- mobile/lib/services/forecast_provider.dart:117 — The marine fallback also sends the same latitude and longitude to the separate Open-Meteo marine host.
- mobile/lib/ui/home_page.dart:243 — A successful forecast is saved asynchronously to the persistent ForecastCache.
- mobile/lib/models/forecast_outlook.dart:153 — ForecastOutlook.toCacheJson serializes response latitude/longitude and requested_latitude/requested_longitude into the cached record.
- mobile/lib/data/forecast_cache.dart:28 — ForecastCache writes the serialized outlook to the forecast_record_v2 SharedPreferences key.
- mobile/lib/ui/info_page.dart:102 — The user-facing privacy copy states that position is only sent as part of a deliberately submitted SOS and is not otherwise transmitted.
- docs/25_MOBILE_SECURITY_IMPLEMENTATION_PLAN.md:248 — The internal data-flow inventory acknowledges that Open-Meteo receives query-string latitude/longitude and sees the trip area, but this disclosure is absent from the in-app privacy copy.

**Decisive blockers:**
- This run could not execute target-controlled Flutter code with the required no-network, empty-environment, read-only-target, scratch-only-write, resource-limited sandbox, so the constructed outbound request URIs and SharedPreferences record were not independently observed with dummy coordinates.

**Safe resolution plan:**
**Bounded local validation:** Inside the approved execution sandbox, use Geolocator method-channel mocks to return an already-granted while-in-use permission and a distinctive last-known dummy fix such as 11.123456,122.654321. Pump HomePage with recording HTTP/backend clients and an empty SharedPreferences mock, without tapping a consent control. Assert that initialization constructs the AqOne forecast and direct Open-Meteo requests with those exact coordinates, that a successful forecast writes requested_latitude/requested_longitude to forecast_record_v2, and that fixed municipal coordinates are used when permission is denied.

## mobile.map.undisclosed-location-derived-tile-egress — Venture may disclose a location-derived viewport to OpenStreetMap without matching notice

**Boundary and candidate:** Opening Venture initiates a high-accuracy location request, moves the map to the resulting fix at zoom 14.5, and configures OpenStreetMap as the network fallback when a bundled or cached tile is unavailable. This can cause tile coordinates derived from the user's location to cross a third-party boundary even though the in-app privacy notice says position is sent only with a deliberately submitted SOS. The exact tile set and effective geographic precision remain unobserved because target-controlled Flutter execution was not permitted without the required sandbox.

**Verified source trace:**
1. **entrypoint** — mobile/lib/ui/app_shell.dart:355 (_AppShellState._select). A user selecting the Venture destination marks that screen for construction; the screen is not built before this deliberate navigation action.
2. **propagation** — mobile/lib/ui/venture_page.dart:175 (_VenturePageState.initState post-frame callback). On its first frame, Venture automatically calls _locate(initial: true) without requiring an SOS action.
3. **propagation** — mobile/lib/services/location_service.dart:123 (LocationService._locateInternal). The location path checks and, when needed, requests runtime location permission before acquiring a fix.
4. **propagation** — mobile/lib/services/location_service.dart:134 (LocationService._locateInternal). After permission, the service asks Geolocator for the current position with high accuracy.
5. **propagation** — mobile/lib/ui/venture_page.dart:294 (_VenturePageState._locate). The returned latitude and longitude become the map point and the controller moves the camera to that point at AqOneConfig.locatedMapZoom.
6. **propagation** — mobile/lib/ui/venture_page.dart:688 (_VenturePageState._buildMap). The visible Flutter map uses the OpenStreetMap URL template and the constructed tile provider, falling back immediately to a cached-network provider while initialization is pending.
7. **propagation** — mobile/lib/services/mbtiles_provider.dart:223 (buildTileProvider). The provider chain returns CachedNetworkTileProvider when the MBTiles asset cannot be opened and otherwise uses the same network provider for pack misses.
8. **propagation** — mobile/lib/services/tile_cache.dart:229 (_CachedTileImage._load). A rendered tile first checks the on-disk cache and calls the network fetch path when no cached bytes exist.
9. **sink** — mobile/lib/services/tile_cache.dart:149 (TileCache.fetch). The fallback performs an HTTPS GET to the URL generated from the map tile coordinates, crossing the handset-to-OpenStreetMap boundary.

**Supporting evidence:**
- mobile/lib/core/config.dart:80 — The map camera uses zoom 14.5 after a successful device fix.
- mobile/lib/core/config.dart:86 — The configured basemap URL sends z/x/y tile requests to tile.openstreetmap.org.
- mobile/pubspec.yaml:119 — The declared Flutter asset list contains images, the SOS alarm, and a team photo, but does not declare the configured MBTiles asset.
- mobile/lib/ui/info_page.dart:102 — The privacy notice states that position is only sent as part of an SOS the user deliberately sends and that location is not otherwise transmitted in the background.
- mobile/lib/ui/onboarding_page.dart:507 — Onboarding exposes that privacy notice through the Privacy Policy link, making it the visible disclosure users are asked to accept.
- mobile/lib/services/tile_cache.dart:154 — Every network tile fetch carries a stable AqOne User-Agent, confirming that the request is intentionally addressed to the external tile service rather than an opaque local renderer.

**Decisive blockers:**
- The required OS-enforced execution sandbox was unavailable, so the Flutter map could not be opened with a dummy fix and an empty cache to observe the exact outgoing tile URLs without permitting external network access.
- Source establishes the location-centered camera and network fallback, but the runtime tile-selection behavior of flutter_map, including the requested zoom levels, buffer tiles, timing, and effective geographic precision visible to the tile provider, remains decisive and unmeasured.

**Safe resolution plan:**
**Bounded local validation:** Inside the approved no-external-network sandbox, run a bounded Flutter widget/integration harness with a fake Geolocator platform returning a documented dummy fix, a temporary empty tile cache, the repository's declared asset bundle, and a recording local HTTP/HttpClient substitute. Open Venture once, wait only for the initial settled map frame, record the attempted tile.openstreetmap.org URLs without sending them, decode each z/x/y tile to geographic bounds, and compare those bounds with the dummy fix. Also record whether any tile request occurs before Venture is selected and whether the missing MBTiles asset forces the network provider. Confirm the candidate only if the captured tile set encloses or materially localizes the dummy fix while the displayed privacy text remains the SOS-only notice; otherwise reject or narrow it to the observed behavior.

## mobile.release.debug-signing-fallback — Android release builds fall back to a developer debug signing identity

**Boundary and candidate:** The documented release commands can produce a release-variant APK when the production keystore configuration is absent, and the Gradle configuration then selects the local Android debug signing configuration. A tracked release-named APK exists, but its signer and any installation or distribution are not established by source. If a debug-signed artifact was installed or distributed, update authority is tied to that specific developer debug key and migration to the intended production identity can require uninstalling the app and losing its private data; possession of that same debug key would also permit accepted replacement APKs.

**Verified source trace:**
1. **entrypoint** — mobile/README.md:46 (Run / release build instructions). A teammate or release operator is instructed to create demo and pitch artifacts with flutter build apk --release, without an adjacent mandatory signing check.
2. **propagation** — mobile/android/app/build.gradle.kts:20 (keystoreProperties initialization). The build loads android/key.properties only when the local untracked file exists, otherwise leaving the signing properties empty.
3. **propagation** — mobile/android/app/build.gradle.kts:26 (hasReleaseKeystore). The release-signing branch is selected solely from whether storeFile is present in the optional properties.
4. **sink** — mobile/android/app/build.gradle.kts:84 (android.buildTypes.release.signingConfig). When hasReleaseKeystore is false, the release variant selects signingConfigs.debug instead of stopping the build.

**Supporting evidence:**
- mobile/android/key.properties.example:18 — The repository explicitly documents that a missing key.properties causes a release build to use debug signing and warns that such a build must not be distributed.
- docs/25_MOBILE_SECURITY_IMPLEMENTATION_PLAN.md:1163 — A historical repository test record labels a generated release artifact debug-signed and records signingReport output with Variant: release and Config: debug; this is supporting history, not an independently reproduced result for the current tracked APK.
- docs/25_MOBILE_SECURITY_IMPLEMENTATION_PLAN.md:1247 — The release-hardening phase remains incomplete until a non-debug signer is demonstrated and release scenarios are recorded.
- mobile/releases/SHA256SUMS.txt:1 — The repository identifies a current tracked artifact named aqone-release.apk by SHA-256 but provides no signer certificate identity.
- docs/archive/plans/57_REPOSITORY_STRUCTURE_CLEANUP_IMPLEMENTATION_PLAN.md:208 — Repository history records that no externally hosted copy was verified and the tracked APK was retained; this does not establish whether it was sideloaded or otherwise distributed.

**Decisive blockers:**
- The current tracked APK's signing certificate was not inspected and a clean release build/signingReport was not reproduced because this audit environment cannot enforce the required no-network, empty-environment, read-only-target, resource-limited execution sandbox or race-safe artifact promotion.
- Repository source does not establish whether mobile/releases/aqone-release.apk, or another artifact produced through the fallback branch, was installed on a handset or distributed to evaluators, teammates, or pilot users.
- The repository's statement that the Android debug key is public and identical on every machine is not sufficient evidence of universal update authority; accepted replacement requires the same signing certificate as the installed APK. The actual signer and custody of that specific key remain decisive.

**Safe resolution plan:**
**Bounded local validation:** In an approved isolated build environment, first inspect mobile/releases/aqone-release.apk offline with apksigner verify --print-certs and record its signer certificate SHA-256. Then, in a harmless clean clone with no key.properties and no production credentials, run the release build and :app:signingReport under strict limits to confirm whether the fallback artifact uses the local debug certificate; do not install or publish either artifact.
**Owner-observed deployment validation:** Ask the release owner to compare the signer certificate SHA-256 of every APK actually shared or installed with the intended production certificate and the tracked APK, and to review the private release channel/device inventory for distribution. If any installed artifact is debug-signed, record the exact certificate owner/custody and the data-preserving migration constraints; do not send audit traffic or publish a replacement.

## mobile.sos.buoy-only-reply-unroutable — Buoy-only SOS replies are routed with an identifier the backend never received

**Boundary and candidate:** An uncredentialed handset can reconcile a buoy-relayed SOS by its LoRa sequence number and learn the backend event id, but its STILL_IN_DANGER or SAFE_NOW reply is sent through the unauthenticated local_id endpoint. The LoRa and shore paths never carry local_id, so the buoy-created backend row cannot match that request; the reply remains only in the handset outbox and the responder incident may remain unchanged.

**Verified source trace:**
1. **entrypoint** — mobile/lib/services/sos_service.dart:240 (SosService.replyToSos). The uncredentialed handset accepts reply 1 or 2 for its local SOS, persists the reply, and queues it until a remote incident id is known.
2. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:196 (buildSosPayload). The LoRa SOS payload carries vessel id, client timestamp, buoy id, and optional context but no handset local_id.
3. **propagation** — firmware/shore/AqOneShore/AqOneShore.ino:164 (postSos). The shore gateway creates a source=buoy ingest body with src_id and seq but no local_id, leaving the backend event without the handset correlation value.
4. **propagation** — firmware/buoy/AqOneBuoy/AqOneBuoy.ino:545 (handleGetSosStatus). The buoy status response returns the backend event id and sequence while explicitly returning local_id as null.
5. **propagation** — mobile/lib/services/sos_service.dart:455 (SosService._applyRemote). The handset matches the buoy event by seq, stores match.id as remoteId, and retries its persisted reply with both that event id and its unrelated local_id.
6. **propagation** — mobile/lib/services/backend_client.dart:436 (BackendClient.replyToSos). When no vessel credential is present, route selection ignores eventId and posts to /api/sos/reply/{local_id}.
7. **sink** — backend/app/api/sos.py:558 (fisher_reply_by_local_id). The unauthenticated endpoint updates only WHERE local_id equals the path value and returns 404 when no row matches, which is the expected state for a buoy-only ingest.

**Supporting evidence:**
- backend/app/api/sos.py:172 — SOS deduplication can later fill local_id from a direct delivery, but an exclusively buoy-delivered event retains the NULL local_id supplied by that path.
- mobile/lib/data/outbox_store.dart:42 — Automatic relay retries select only records still in saved state; a successful buoy handoff advances the record to relayed, so a later direct retry does not automatically backfill local_id.
- mobile/lib/services/sos_service.dart:486 — Reconciliation repeatedly retries a persisted reply after learning match.id, but marks it synchronized only when BackendClient returns success.
- docs/25_MOBILE_SECURITY_IMPLEMENTATION_PLAN.md:1017 — The repository records that no enrollment UI calls enrollVesselDevice, so the credentialed event-id reply path is not reachable for a normally installed handset.
- backend/app/api/sos.py:517 — The alternative event-id reply endpoint requires a vessel-device credential and binds the event to that credential's vessel.

**Decisive blockers:**
- The source path is complete, but the audit environment cannot provide every required execution control for target code: an isolated no-external-network namespace, an empty allowlisted environment, read-only target and toolchain, scratch-only process writes, explicit low resource limits, and race-safe artifact promotion. Therefore the exact HTTP 404, unchanged dummy incident, and persisted retry behavior were not observed in a local backend/mobile integration run.

**Safe resolution plan:**
**Bounded local validation:** In an approved isolated loopback sandbox, start a disposable PostgreSQL-backed FastAPI instance with dummy data and a Flutter service harness using a temporary outbox plus mocked buoy client. Ingest one SOS with source=buoy, src_id, and seq but no local_id; return that event id and seq from the mock buoy to an uncredentialed handset; invoke reply 1 and reply 2 separately. Assert that the handset posts /api/sos/reply/{local_id}, receives 404, the dummy row's fisher_reply and resolved_at remain NULL, and the reply remains pending after an outbox reload and reconciliation tick. Stop after those assertions and send no traffic to any deployed service.

## mobile.sos.standdown-intent-treated-resolved — Local stand-down intent is presented as remotely completed

**Boundary and candidate:** The post-dispatch stand-down path records SAFE_NOW locally before the backend accepts it. A missing backend event id returns without sending, and a failed backend reply returns false but that result is discarded. The locally stored reply immediately makes the SOS resolved, suppresses acknowledgement UI, and tells the fisher that MDRRMO was told even though the remote incident can remain active until a later reconciliation retry succeeds.

**Verified source trace:**
1. **entrypoint** — mobile/lib/ui/venture_page.dart:1524 (_SosFollowUpSheet stand-down control). The fisher can invoke the post-dispatch 'Slide to stand down' action.
2. **propagation** — mobile/lib/services/sos_service.dart:315 (SosService.standDown). The service saves reply 2 locally before checking remoteId, returns immediately when the id is absent, and awaits replyToSos without inspecting its boolean success result when the id is present.
3. **propagation** — mobile/lib/data/outbox_store.dart:233 (OutboxStore.saveFisherReply). The local outbox persists fisher_reply=2 independently of whether the backend accepted the stand-down.
4. **propagation** — mobile/lib/models/sos_record.dart:108 (SosRecord.isStoodDown and isResolved). Any locally stored reply 2 makes isStoodDown true and therefore makes isResolved true even while resolvedAt from backend read-back is null.
5. **sink** — mobile/lib/ui/venture_page.dart:891 (_buildSosStatus). The UI renders 'Stood down' and states that MDRRMO has been told to disregard based only on local fisherReply state.

**Supporting evidence:**
- mobile/lib/services/backend_client.dart:436 — BackendClient.replyToSos returns false for missing routing, authorization failures, non-200 responses, and caught transport errors; standDown does not consume this result.
- mobile/lib/services/sos_service.dart:321 — When remoteId is absent, standDown returns after only the local write and relies on a later reconcile to flush the intent.
- mobile/lib/services/sos_service.dart:486 — Reconciliation can later retry a locally saved fisherReply, showing the mismatch is a potentially temporary but real interval rather than proof of permanent loss.
- mobile/lib/ui/app_shell.dart:242 — Acknowledgement/ETA presentation is gated by !record.isResolved, so local reply 2 suppresses that safety UI before backend resolution is observed.
- mobile/lib/ui/venture_page.dart:389 — The post-dispatch callback always shows 'SOS stood down.' after standDown completes and has no success-versus-queued result to distinguish.
- mobile/lib/ui/widgets/responder_eta_dialog.dart:87 — The acknowledgement-dialog reply path is a source-visible control baseline: it consumes replyToSos's boolean and sets a queued indicator when the backend was not reached, unlike standDown.
- mobile/lib/l10n/app_en.arb:531 — The existing safety-critical queued copy explicitly says a reply was not sent yet and must not imply it reached MDRRMO, but the post-dispatch stand-down surface does not use it.

**Decisive blockers:**
- The required OS-enforced target-execution sandbox is unavailable in this Windows workspace, so the deterministic Flutter/SQLite state transition and rendered widget result were not independently observed with a dummy record. Confirmed status requires that target-native bounded execution evidence rather than source inspection alone.

**Safe resolution plan:**
**Bounded local validation:** Inside the required no-network, empty-allowlist, read-only-target, scratch-only sandbox, run a bounded Flutter test with a temporary SQLite outbox and mock BackendClient. For one acknowledged dummy SOS, exercise standDown once with remoteId absent and once with replyToSos returning HTTP 503; assert that the backend fixture remains unresolved while the current code persists fisher_reply=2, makes isResolved true, suppresses the responder acknowledgement path, and renders the MDRRMO-was-told stand-down text. Then repeat with a 200 response to establish the accepted control case.

## mobile.squall.ack-survives-missed-clear — A missed clear can carry a squall acknowledgement into a later event

**Boundary and candidate:** While one AppShell instance remains alive, two operational RETURN NOW responses with the same triggered-buoy set receive the same client identity. If the handset sees only unavailable/unknown polls between those distinct events, its acknowledgement of the first event is neither cleared nor distinguished from the second, so the later event can be shown as already acknowledged without restarting the alarm or full-screen alert. An app process restart resets this in-memory state, and the audited source currently caps its bundled synthetic live model at watch; current deployment reachability therefore remains unverified.

**Verified source trace:**
1. **entrypoint** — mobile/lib/services/venture_feeds.dart:202 (VentureFeeds.squall). The handset polls the public backend squall response and converts a failed or invalid response to SquallWatch.unavailable (unknown), rather than a definite clear.
2. **propagation** — mobile/lib/models/squall_watch.dart:153 (SquallWatch.identity). Event identity is only the sorted triggered-buoy list (or the constant 'squall' when empty); observed_at, generated_at, and any event epoch are excluded.
3. **propagation** — mobile/lib/ui/app_shell.dart:161 (_AppShellState._loadSquall). RETURN NOW starts the alarm for that identity, but an unknown/unavailable poll deliberately does not call clear; only a definite non-unknown non-alarm response resets acknowledgement state.
4. **propagation** — mobile/lib/services/squall_alarm.dart:38 (SquallAlarm.start). start returns immediately when the incoming identity equals the previously acknowledged identity, leaving sound and vibration stopped.
5. **sink** — mobile/lib/ui/app_shell.dart:174 (_AppShellState._loadSquall). The same retained acknowledgement suppresses the full-screen SquallAlertPage for a later RETURN NOW response with the same buoy-derived identity.

**Supporting evidence:**
- mobile/lib/models/squall_watch.dart:159 — identity sorts and joins triggeredBuoys and does not include either server timestamp or a server-issued event identifier.
- mobile/lib/services/squall_alarm.dart:48 — acknowledge copies _activeIdentity to _acknowledgedIdentity and stops the underlying alarm.
- mobile/lib/services/squall_alarm.dart:55 — clear is the sole source-visible reset for both _activeIdentity and _acknowledgedIdentity; the values are process-memory fields and therefore do not survive AppShell/process recreation.
- mobile/lib/ui/app_shell.dart:148 — The documented and implemented unavailable behavior intentionally leaves an existing alarm state alone because loss of signal is not treated as evidence that a squall passed.
- backend/app/api/squall.py:140 — The current live backend caps a synthetic-calibration model at watch even when return-now is otherwise allowed, so the audited tracked model does not establish current operational reachability of this client lifecycle flaw.
- docs/05_PUBLIC_API.md:547 — The contract reserves return_now for an operational, field-validated deployment and documents the deployment flag required before a live handset can receive it.

**Decisive blockers:**
- The workspace cannot execute Flutter/Dart target code under the audit's required no-network, empty-environment, read-only-target, scratch-only, resource-limited OS sandbox, so the two-event state sequence has not been independently observed.
- Current source trains and ships a synthetic-calibration squall bundle that the live backend caps at watch; whether any deployed environment instead has an operational non-synthetic bundle together with SQUALL_RETURN_NOW_ENABLED is an external configuration and artifact fact decisive to present reachability.

**Safe resolution plan:**
**Bounded local validation:** Inside an approved bounded sandbox, add a focused Dart test using a SosAlarm test double. Construct two SquallWatch values with different observed_at values but the same triggeredBuoys and assert their identities are equal; call SquallAlarm.start(first.identity), acknowledge(), deliberately omit clear() to model intervening unknown polls, then call start(second.identity) and assert the fake alarm start count does not increase and isAcknowledged(second.identity) remains true. Add a companion AppShell/VentureFeeds fixture returning RETURN NOW, unavailable, then same-buoy RETURN NOW and assert that the second full-screen alert is absent. Bound the fixture to those three responses and one widget lifecycle.
**Owner-observed deployment validation:** Without sending audit traffic, have the deployment owner read the running release metadata and environment to record the loaded squall bundle's calibration and the value of SQUALL_RETURN_NOW_ENABLED, plus the mobile build version in use. If the bundle is still synthetic or the flag is disabled, record the path as presently dormant; if both permit operational RETURN NOW, treat the bounded local lifecycle reproduction as release-blocking before rollout.

