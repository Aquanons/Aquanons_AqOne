# Evidence: Backend track

Plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`; track file listed in its header table.
Each phase appends a dated section: red and green test runs, gate results, and any device or bench record.
Row counts and IDs only; never data, URLs or credentials.

## Phase B1 - Incident lifecycle

### Red run

- `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@localhost:55432/postgres python -m pytest -q -p no:cacheprovider tests/test_incident_lifecycle.py tests/test_incidents_is_pure.py tests/test_edge_lifecycle_pg.py`: collection failed because `app.incidents` does not exist.
- `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@localhost:55432/postgres python -m pytest -q -p no:cacheprovider tests/test_edge_lifecycle_pg.py`: 7 failed, 1 passed. Failing tests: `test_resolve_without_reason_stores_unspecified`, `test_resolve_with_reason_code_is_returned_in_vessel_feed`, `test_reopen_restores_active_and_downlink_and_audits`, `test_reopen_of_open_incident_is_no_change`, `test_ack_with_stale_version_conflicts`, `test_transport_merge_does_not_bump_version`, `test_still_in_danger_reopens_within_two_hours`.

### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 465 passed, 5 skipped, 1 xfailed.
- `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@localhost:55432/postgres python -m pytest -q -p no:cacheprovider tests/`: 465 passed, 5 skipped, 1 xfailed.
- `python -m pytest -q -p no:cacheprovider tests/test_edge_lifecycle_pg.py tests/test_incident_lifecycle.py tests/test_incidents_is_pure.py tests/test_responder_loop.py`: 29 passed.
- `python -m pytest -q -p no:cacheprovider tests/test_migrate.py`: 5 passed; migration 032 applied by fresh probe databases.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed, 0 errors.
- The three failures match Phase 6 deferred probes: two minimum hotspot cohort probes and the firmware shared LoRa key probe.
- Diff review: `backend/app/api/sos.py` is two lines shorter than its starting version, and incident policy modules contain no forbidden framework/database imports.

## Phase B2 - Incident nonce and safe text

### Red run

- `python -m pytest -q -p no:cacheprovider tests/test_sos_text.py`: collection failed because `app.incidents.text` does not exist.
- `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@localhost:55432/postgres python -m pytest -q -p no:cacheprovider tests/test_sos_ingest.py::test_sos_note_truncated_on_char_boundary tests/test_sos_ingest.py::test_sos_boat_truncated_to_32_bytes`: 2 failed because stored note and boat strings exceed their UTF-8 byte caps.
- `AQONE_PROBE_PG_ADMIN_URL=postgresql://postgres@localhost:55432/postgres python -m pytest -q -p no:cacheprovider tests/test_edge_nonce_pg.py`: 5 failed, 2 passed. Failing tests: `test_prepared_rows_cannot_capture_nonce_sos`, `test_same_second_different_nonce_two_rows`, `test_same_nonce_merges_across_transports`, `test_position_conflict_stores_alt_position`, `test_close_positions_do_not_conflict`.

### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 461 passed, 23 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 479 passed, 5 skipped, 1 xfailed.
- Focused text and nonce integration checks: 14 passed.
- `python -m pytest -q -p no:cacheprovider tests/test_migrate.py`: 5 passed; the fresh manual database applied migrations through 033.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed. Failures are unchanged Phase 6 deferred probes: two hotspot cohort probes and the firmware shared LoRa key probe.
- Manual local `curl` POST with a 70-byte UTF-8 note returned HTTP 200; PostgreSQL stored 64 bytes across 32 valid UTF-8 characters.
## Phase B3 - Downlink cap and gateway last-seen

### Red run

- `python -m pytest -q -p no:cacheprovider tests/test_downlink_policy.py`: collection failed because `app.incidents.downlink` does not exist.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/test_edge_downlink_pg.py --tb=short`: 3 failed. The feed returned 30 rows instead of 12; `gateway_status` did not exist; and `/api/ops/status` returned 404.
### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 466 passed, 26 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 487 passed, 5 skipped, 1 xfailed.
- B3 policy plus downlink regression tests: 15 passed; B3 PostgreSQL/API tests: 3 passed.
- `python -m pytest -q -p no:cacheprovider tests/test_migrate.py`: 5 passed; fresh PostgreSQL probes applied migration 034.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed. Failures remain the Phase 6 deferred hotspot cohort and shared LoRa key probes.
## Phase B4 - Dispatcher triage, flags and late calls

### Red run

- `python -m pytest -q -p no:cacheprovider tests/test_triage.py tests/test_plausibility.py`: collection failed because `app.incidents.triage` and `app.incidents.plausibility` do not exist.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/test_edge_active_pg.py --tb=short`: 5 failed. Failures covered missing totals/flood metadata, no limit support, no late-call metadata, no open-call count, and no delivery path.### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 476 passed, 31 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 502 passed, 5 skipped, 1 xfailed.
- B4 focused pure policy, plausibility, geography and trip-profile checks: 21 passed, 1 xfailed; B4 PostgreSQL/API tests: 5 passed.
- `python -m pytest -q -p no:cacheprovider tests/test_migrate.py`: 5 passed.
- Timing note: `/api/sos/active` against 10,000 unresolved rows returned 200 rows with `total=10000` in 267.7 ms on local PostgreSQL 18 (TestClient request round trip).
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed. The same Phase 6 deferred hotspot cohort and shared LoRa key probes remain.
## Phase B5 - Chat authority, identity and trust

### Red run

- `python -m pytest -q -p no:cacheprovider tests/test_chat_policy.py tests/test_trust.py`: collection failed because `app.mesh.chat_policy` and `app.incidents.trust` do not exist.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/test_edge_identity_pg.py --tb=short`: 5 failed, 3 passed. Enrolled blank fills remained anonymous, profile provenance/shore-contact columns and confirmation were absent, and a 3-day-expired token was rejected.
- The six mesh API cases yielded 5 failed, 1 passed: reserved sender accepted, anonymous origin spoofed, operator origin ignored, seventh post accepted, and anonymous history read reached the database instead of returning 401.
### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 501 passed, 39 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 535 passed, 5 skipped, 1 xfailed.
- Focused B5 policy/API checks: 73 passed; identity/profile PostgreSQL checks: 13 passed.
- `python -m pytest -q -p no:cacheprovider tests/test_migrate.py`: 5 passed; PostgreSQL probes applied migration 035.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed, 0 errors. The same two Phase 6 hotspot cohort probes and firmware shared LoRa key probe remain deferred.

## Phase B6 - Scheduler, SMS escalation, ops status and operator refresh

### Red run

- `python -m pytest -q -p no:cacheprovider tests/test_escalation.py tests/test_notify.py`: collection failed because `app.incidents.escalation` and `app.notify` do not exist.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/test_edge_scheduler_pg.py`: collection failed because `app.scheduler` does not exist.
- With the same PostgreSQL probe URL, the two operator refresh cases failed: both returned HTTP 405 because `POST /api/token/refresh` is not registered.

### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 507 passed, 44 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 546 passed, 5 skipped, 1 xfailed.
- B6 focused policy, notify, scheduler, auth and migration checks: 27 passed.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed, 0 errors. The same two Phase 6 hotspot cohort probes and firmware shared LoRa key probe remain deferred.
- Manual local run with Semaphore credentials unset: POST `/api/sos` returned 200; after 155 seconds the scheduler set `escalated_at`, wrote audit outcome `not_configured`, and `/api/ops/status` showed `sms_configured=false` with the `sos-escalation` last run. The isolated PostgreSQL database was dropped after verification.

## Phase B7 - Honest anomaly detection and drift clock

### Red run

- `python -m pytest -q -p no:cacheprovider tests/test_anomaly_source.py tests/test_trip_profile.py tests/test_drift.py --tb=short`: 11 failed, 19 passed. Failures cover missing 72-hour silent-vessel eligibility, handset-only overdue suppression, unavailable monitoring metadata, contact_via validation, cold-start damping, check-needed status, welfare timestamp expiry, circular departure hour, home landing distance, and implausible client clock handling.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/test_edge_welfare_pg.py --tb=short`: 2 failed because `contact_via` and `welfare_updated_at` are absent.

### Green run

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 518 passed, 46 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 559 passed, 5 skipped, 1 xfailed.
- B7 focused profile, anomaly source, drift, contact and welfare checks: 37 passed, including 5 migration checks.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed, 0 errors. The same two Phase 6 hotspot cohort probes and firmware shared LoRa key probe remain deferred.
- The required evaluation ran with `python -m app.simulation.generator --days 14 --seed 42` followed by `python -m app.ai.trip_profile_eval` on an isolated PostgreSQL 18 database. It evaluated 496 normal synthetic trips, raised 496 candidates, and measured a 100% false-alarm rate; it detected 8 incidents at a 55-minute median latency. These are simulation-only results, not field accuracy. The prior false-alarm value was retracted/null; the generated result is in `backend/app/ai/models/eval_results.json`. The isolated database was dropped after evaluation.
