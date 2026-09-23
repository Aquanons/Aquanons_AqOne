# Security Audit Remediation Evidence

This document tracks gate runs, test counts, and probe statuses across remediation phases.
The probes defined in `backend/tests/security_probes/` and `mobile/test_security_probes/` serve as the acceptance criteria.

## Phase 0: Branch and baseline

### Environment

- Date: 2026-09-23T13:37:00+08:00
- Branch: `fix/security-audit-remediation`
- Base commit: `35a7822`
- OS: Windows 10
- Python: 3.11.9
- Flutter: 3.29.0 (Dart 3.7.0)
- PostgreSQL: 18.4 (throwaway cluster on localhost:55432)

### Verification Gates

#### 1. Backend Default Gate

Commands executed from `backend/`:
```powershell
Remove-Item Env:DATABASE_URL, Env:AQONE_SECURITY_PROBES -ErrorAction SilentlyContinue
python -m ruff check .
python -m pytest -q -p no:cacheprovider
```

Result:
- Ruff: All checks passed.
- Pytest default suite: 387 passed, 5 skipped, 1 xfailed in 27.02s.
- Status: PASSED.

#### 2. Mobile Gate

Commands executed from `mobile/`:
```powershell
flutter gen-l10n
flutter analyze
flutter test
flutter test test_security_probes
```

Result:
- `flutter gen-l10n`: Generated localization files successfully.
- `flutter analyze`: No issues found.
- `flutter test`: 259 passed, 0 failed.
- `flutter test test_security_probes`: 1 passed (control), 5 failed (expected red probes).
- Status: PASSED.

#### 3. Web Gate

Commands executed from repository root:
```powershell
node --test web/test/*.test.js
Get-ChildItem web/js, web/test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

Result:
- Node test runner: 149 passed, 0 failed in 1593ms.
- Syntax verification: All JavaScript files pass syntax check.
- Status: PASSED.

#### 4. Security Probe Gate (Baseline)

Database instance:
- Local throwaway PostgreSQL 18 cluster initialized on port 55432 with trust authentication.

Command executed from `backend/`:
```powershell
$env:AQONE_SECURITY_PROBES = '1'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
python -m pytest tests/security_probes -p no:cacheprovider -q
Remove-Item Env:AQONE_SECURITY_PROBES, Env:AQONE_PROBE_PG_ADMIN_URL
```

Result:
- Total test items: 43.
- Passed: 3 (all 3 control tests).
- Failed / Error: 40 (all 40 security probes reflecting open audit findings).
- Status: PASSED (baseline confirmed).

### Probe Status List (Baseline)

#### Backend Probes - Green / Controls (3 passed)

1. `tests/security_probes/test_probe_auth.py::test_squall_control_admin_reaches_the_model_write` (Control)
2. `tests/security_probes/test_probe_ingest_trust.py::test_contact_control_present_timestamp_is_accepted` (Control)
3. `tests/security_probes/test_probe_public_disclosure.py::test_hotspot_control_five_reporters_publish` (Control)

#### Backend Probes - Red / Open Findings (40 failed/error)

1. `tests/security_probes/test_probe_anomaly.py::test_contact_without_coordinates_does_not_abort_fleet_evaluation` (FAILED)
2. `tests/security_probes/test_probe_anomaly.py::test_zero_contact_trip_for_a_fresh_vessel_does_not_abort_evaluation` (FAILED)
3. `tests/security_probes/test_probe_anomaly.py::test_zero_contact_trip_for_a_known_vessel_does_not_abort_evaluation` (FAILED)
4. `tests/security_probes/test_probe_anomaly.py::test_failed_evaluation_does_not_commit_score_deactivation` (ERROR)
5. `tests/security_probes/test_probe_anomaly.py::test_one_ordinary_live_trip_evaluates_on_real_postgres` (ERROR)
6. `tests/security_probes/test_probe_anomaly.py::test_measure_whole_fleet_evaluation_cost` (ERROR)
7. `tests/security_probes/test_probe_auth.py::test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password` (FAILED)
8. `tests/security_probes/test_probe_auth.py::test_token_for_an_account_that_no_longer_exists_is_rejected` (FAILED)
9. `tests/security_probes/test_probe_auth.py::test_non_admin_operator_cannot_replace_the_live_squall_model[mdrrmo]` (FAILED)
10. `tests/security_probes/test_probe_auth.py::test_non_admin_operator_cannot_replace_the_live_squall_model[lgu]` (FAILED)
11. `tests/security_probes/test_probe_catch.py::test_one_vessel_cannot_rewrite_another_vessels_catch_log` (ERROR)
12. `tests/security_probes/test_probe_ingest_trust.py::test_request_text_cannot_mark_a_current_reading_qualified` (FAILED)
13. `tests/security_probes/test_probe_ingest_trust.py::test_contact_ingest_rejects_a_day_ahead_timestamp` (FAILED)
14. `tests/security_probes/test_probe_public_disclosure.py::test_public_sea_condition_does_not_expose_operator_account` (FAILED)
15. `tests/security_probes/test_probe_public_disclosure.py::test_hotspot_cell_needs_five_distinct_reporters[3]` (FAILED)
16. `tests/security_probes/test_probe_public_disclosure.py::test_hotspot_cell_needs_five_distinct_reporters[4]` (FAILED)
17. `tests/security_probes/test_probe_repo_static.py::test_shore_sketch_holds_no_concrete_credential[UPLINK_SSID]` (FAILED)
18. `tests/security_probes/test_probe_repo_static.py::test_shore_sketch_holds_no_concrete_credential[UPLINK_PASS]` (FAILED)
19. `tests/security_probes/test_probe_repo_static.py::test_shore_sketch_holds_no_concrete_credential[GATEWAY_API_KEY]` (FAILED)
20. `tests/security_probes/test_probe_repo_static.py::test_loam_key_is_not_the_repository_default` (FAILED)
21. `tests/security_probes/test_probe_repo_static.py::test_loam_signature_key_is_selected_per_source_id` (FAILED)
22. `tests/security_probes/test_probe_repo_static.py::test_loam_control_headers_are_byte_identical` (FAILED)
23. `tests/security_probes/test_probe_repo_static.py::test_shore_verifies_the_backend_certificate` (FAILED)
24. `tests/security_probes/test_probe_repo_static.py::test_buoy_warning_cache_orders_updates_by_revision` (FAILED)
25. `tests/security_probes/test_probe_repo_static.py::test_tx_ring_keeps_capacity_for_distress_frames` (FAILED)
26. `tests/security_probes/test_probe_repo_static.py::test_release_build_does_not_fall_back_to_debug_signing` (FAILED)
27. `tests/security_probes/test_probe_repo_static.py::test_tracked_release_apk_is_not_debug_signed` (FAILED)
28. `tests/security_probes/test_probe_resource_bounds.py::test_demo_weather_rejects_ten_thousand_coordinate_cells` (FAILED)
29. `tests/security_probes/test_probe_resource_bounds.py::test_mesh_chat_has_a_retention_or_admission_control` (FAILED)
30. `tests/security_probes/test_probe_resource_bounds.py::test_public_squall_does_not_load_week_old_readings` (ERROR)
31. `tests/security_probes/test_probe_sos.py::test_anonymous_sos_cannot_self_assert_responder_confirmation` (FAILED)
32. `tests/security_probes/test_probe_sos.py::test_anonymous_sos_cannot_claim_buoy_delivery_without_gateway_key` (FAILED)
33. `tests/security_probes/test_probe_sos.py::test_genuine_sos_survives_a_burst_of_anonymous_sos` (ERROR)
34. `tests/security_probes/test_probe_sos.py::test_handset_reply_reaches_an_sos_that_arrived_only_over_the_buoy` (ERROR)
35. `tests/security_probes/test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal[GET-/api/v1/trips-None]` (FAILED)
36. `tests/security_probes/test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal[GET-/api/v1/trips/PROBE-TRIP-None]` (FAILED)
37. `tests/security_probes/test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal[PATCH-/api/v1/trips/PROBE-TRIP-body2]` (FAILED)
38. `tests/security_probes/test_probe_unauth_routes.py::test_warning_delivery_route_requires_an_authority[POST-/api/advisories/delivery-body0]` (FAILED)
39. `tests/security_probes/test_probe_unauth_routes.py::test_warning_delivery_route_requires_an_authority[GET-/api/advisories/101/deliveries-None]` (FAILED)
40. `tests/security_probes/test_probe_unauth_routes.py::test_anonymous_caller_cannot_replace_an_existing_vessel_identity` (ERROR)

#### Mobile Probes - Green / Controls (1 passed)

1. `mobile/test_security_probes/sos_probes_test.dart: [mobile.sos.standdown-intent-treated-resolved:control] an accepted stand-down is resolved` (PASSED)

#### Mobile Probes - Red / Open Findings (5 failed)

1. `mobile/test_security_probes/sos_probes_test.dart: [mobile.sos.standdown-intent-treated-resolved] a stand-down the backend rejected (503) is not shown as resolved` (FAILED)
2. `mobile/test_security_probes/sos_probes_test.dart: [mobile.sos.standdown-intent-treated-resolved] a stand-down never sent (no backend id yet) is not shown as resolved` (FAILED)
3. `mobile/test_security_probes/sos_probes_test.dart: [mobile.sos.buoy-only-reply-unroutable] handset half: the reply to a buoy-only SOS is delivered` (FAILED)
4. `mobile/test_security_probes/sos_probes_test.dart: [mobile.eta.server-clock-discarded] rescue ETA is measured against server time, not the phone clock` (FAILED)
5. `mobile/test_security_probes/squall_probes_test.dart: [mobile.squall.ack-survives-missed-clear] a squall six hours later on the same buoys alarms again after a missed clear` (FAILED)

### Credential Leak Verification

- Scanned all files under `docs/security-audit/probe-runs/` for occurrences of sensitive literals (`UPLINK_SSID`, `UPLINK_PASS`, `GATEWAY_API_KEY`) using both UTF-8 and UTF-16LE byte patterns.
- Verified that zero plaintext secrets are present.

## Phase 1: Anomaly evaluation works on real Postgres

### Environment

- Date: 2026-09-23T18:55:00+08:00
- Branch: `fix/security-audit-remediation`
- Requirements: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05
- Contract changes: `docs/04_INGEST_API.md` updated with 5-minute future clock skew rejection for contact events (owned by Arnold).

### Verification Gates

#### 1. Backend Default Gate

Commands executed from `backend/`:
```powershell
ruff check app tests
pytest -q -p no:cacheprovider
```

Result:
- Ruff: All checks passed.
- Pytest default suite: 390 passed, 5 skipped, 1 xfailed in 28.45s.
- Status: PASSED.

#### 2. Mobile Gate

Commands executed from `mobile/`:
```powershell
flutter analyze
flutter test
```

Result:
- Flutter analyze: No issues found (0 warnings, 0 errors).
- Flutter test: 259 passed, 0 failed.
- Status: PASSED.

#### 3. Web Gate

Commands executed from repository root:
```powershell
node --test web/test/*.test.js
```

Result:
- Node test runner: 149 passed, 0 failed.
- Status: PASSED.

#### 4. Security Probe Gate (Throwaway PostgreSQL 18 on Port 55432)

Command executed from `backend/`:
```powershell
$dataDir = "$env:TEMP\aqone_probe_pg_data"
if (!(Test-Path $dataDir)) { & 'C:\Program Files\PostgreSQL\18\bin\initdb.exe' -D $dataDir -U postgres -A trust -E UTF8 }
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir -o '-p 55432' -l "$env:TEMP\aqone_probe_pg.log" start
Start-Sleep -Seconds 2
$env:AQONE_SECURITY_PROBES = '1'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
python -m pytest tests/security_probes -p no:cacheprovider -s
Remove-Item Env:AQONE_SECURITY_PROBES, Env:AQONE_PROBE_PG_ADMIN_URL
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir stop
```

Result:
- Total probe items: 43.
- Passed: 10 (was 3 in baseline; +7 net passed).
- Failed: 33 (was 40 in baseline; remaining open findings for Phase 2-5).
- Status: PASSED.

### SEC-05 Measurement Probe

Probe `test_measure_whole_fleet_evaluation_cost` executed against real Postgres:
- Output: `MEASURE {"contacts": 10000, "vessels": 200, "scored_trips": 200, "elapsed_seconds": 0.702}`
- Scored 200 trips across 10,000 contact events in 0.702 seconds.

### Probe Status Changes (Phase 1)

#### Anomaly Probes (SEC-01, SEC-02, SEC-03, SEC-05): All Green

1. `tests/security_probes/test_probe_anomaly.py::test_one_ordinary_live_trip_evaluates_on_real_postgres`: PASSED (was ERROR) [SEC-01]
2. `tests/security_probes/test_probe_anomaly.py::test_zero_contact_trip_for_a_fresh_vessel_does_not_abort_evaluation`: PASSED (was FAILED) [SEC-02]
3. `tests/security_probes/test_probe_anomaly.py::test_zero_contact_trip_for_a_known_vessel_does_not_abort_evaluation`: PASSED (was FAILED) [SEC-02]
4. `tests/security_probes/test_probe_anomaly.py::test_failed_evaluation_does_not_commit_score_deactivation`: PASSED (was ERROR) [SEC-02]
5. `tests/security_probes/test_probe_anomaly.py::test_contact_without_coordinates_does_not_abort_fleet_evaluation`: PASSED (was FAILED) [SEC-03]
6. `tests/security_probes/test_probe_anomaly.py::test_measure_whole_fleet_evaluation_cost`: PASSED (was ERROR) [SEC-05]

#### Ingest Trust Probes (SEC-04): Green

1. `tests/security_probes/test_probe_ingest_trust.py::test_contact_ingest_rejects_a_day_ahead_timestamp`: PASSED (was FAILED) [SEC-04]
2. `tests/security_probes/test_probe_ingest_trust.py::test_contact_control_present_timestamp_is_accepted`: PASSED (Control)

## Phase 2: Distress path integrity

### Environment

- Date: 2026-09-23T20:40:00+08:00
- Branch: `fix/security-audit-remediation`
- Requirements: SEC-06, SEC-07, SEC-08, SEC-09, SEC-10, SEC-11
- Contract changes:
  - `docs/04_INGEST_API.md`: Documented gateway key requirement for buoy provenance claims on SOS ingest and warning delivery.
  - `docs/05_PUBLIC_API.md`: Documented untruncated `/api/sos/active` feed, vessel profile overwrite 409 conflict rules, `GET /api/advisories/{id}/deliveries` operator access, and `Vessel trips (/api/v1/trips)` authorization rules.

### Verification Gates

#### 1. Backend Default Gate

Commands executed from `backend/`:
```powershell
ruff check app tests
pytest -q -p no:cacheprovider
```

Result:
- Ruff: All checks passed.
- Pytest default suite: 398 passed, 5 skipped, 1 xfailed in 15.83s.
- Status: PASSED.

#### 2. Mobile Gate

Commands executed from `mobile/`:
```powershell
flutter gen-l10n
flutter analyze
flutter test
```

Result:
- Flutter analyze: No issues found (ran in 50.6s).
- Flutter test: 259 passed, 0 failed.
- Status: PASSED.

#### 3. Web Gate

Commands executed from repository root:
```powershell
node --test web/test/*.test.js
```

Result:
- Node test runner: 149 passed, 0 failed.
- Status: PASSED.

#### 4. Security Probe Gate (Throwaway PostgreSQL 18 on Port 55432)

Command executed from `backend/`:
```powershell
$dataDir = "$env:TEMP\aqone_probe_pg_data"
if (!(Test-Path $dataDir)) { & 'C:\Program Files\PostgreSQL\18\bin\initdb.exe' -D $dataDir -U postgres -A trust -E UTF8 }
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir -o '-p 55432' -l "$env:TEMP\aqone_probe_pg.log" start
Start-Sleep -Seconds 2
$env:AQONE_SECURITY_PROBES = '1'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
python -m pytest tests/security_probes -v -p no:cacheprovider
Remove-Item Env:AQONE_SECURITY_PROBES, Env:AQONE_PROBE_PG_ADMIN_URL
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir stop
```

Result:
- Total probe items: 43.
- Passed: 20 (was 10 in Phase 1; +10 net passed).
- Failed: 23 (was 33 in Phase 1; remaining open findings for Phase 3-5).
- Migration 029 (`029_catch_logs_vessel_scoped_local_id.sql`) applied cleanly on fresh probe database.
- Status: PASSED.

### Probe Status Changes (Phase 2)

#### Distress & Provenance Probes (SEC-06, SEC-07): All Green

1. `tests/security_probes/test_probe_sos.py::test_anonymous_sos_cannot_self_assert_responder_confirmation`: PASSED (was FAILED) [SEC-06]
2. `tests/security_probes/test_probe_sos.py::test_anonymous_sos_cannot_claim_buoy_delivery_without_gateway_key`: PASSED (was FAILED) [SEC-06]
3. `tests/security_probes/test_probe_sos.py::test_genuine_sos_survives_a_burst_of_anonymous_sos`: PASSED (was FAILED) [SEC-07]

#### Vessel Profile Identity Probes (SEC-08): Green

1. `tests/security_probes/test_probe_unauth_routes.py::test_anonymous_caller_cannot_replace_an_existing_vessel_identity`: PASSED (was FAILED) [SEC-08]

#### Trips & Welfare Monitoring Probes (SEC-09): All Green

1. `tests/security_probes/test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal[GET-/api/v1/trips-None]`: PASSED (was FAILED) [SEC-09]
2. `tests/security_probes/test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal[GET-/api/v1/trips/PROBE-TRIP-None]`: PASSED (was FAILED) [SEC-09]
3. `tests/security_probes/test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal[PATCH-/api/v1/trips/PROBE-TRIP-body2]`: PASSED (was FAILED) [SEC-09]

#### Warning Delivery Authority Probes (SEC-10): All Green

1. `tests/security_probes/test_probe_unauth_routes.py::test_warning_delivery_route_requires_an_authority[POST-/api/advisories/delivery-body0]`: PASSED (was FAILED) [SEC-10]
2. `tests/security_probes/test_probe_unauth_routes.py::test_warning_delivery_route_requires_an_authority[GET-/api/advisories/101/deliveries-None]`: PASSED (was FAILED) [SEC-10]

#### Catch Logs Vessel Scoping Probes (SEC-11): Green

1. `tests/security_probes/test_probe_catch.py::test_one_vessel_cannot_rewrite_another_vessels_catch_log`: PASSED (was FAILED) [SEC-11]

#### Phase 1 Regression Check: Probes Stay Green

1. `tests/security_probes/test_probe_anomaly.py::test_one_ordinary_live_trip_evaluates_on_real_postgres`: PASSED [SEC-01]
2. `tests/security_probes/test_probe_anomaly.py::test_zero_contact_trip_for_a_fresh_vessel_does_not_abort_evaluation`: PASSED [SEC-02]
3. `tests/security_probes/test_probe_anomaly.py::test_zero_contact_trip_for_a_known_vessel_does_not_abort_evaluation`: PASSED [SEC-02]
4. `tests/security_probes/test_probe_anomaly.py::test_failed_evaluation_does_not_commit_score_deactivation`: PASSED [SEC-02]
5. `tests/security_probes/test_probe_anomaly.py::test_contact_without_coordinates_does_not_abort_fleet_evaluation`: PASSED [SEC-03]
6. `tests/security_probes/test_probe_anomaly.py::test_measure_whole_fleet_evaluation_cost`: PASSED [SEC-05]
7. `tests/security_probes/test_probe_ingest_trust.py::test_contact_ingest_rejects_a_day_ahead_timestamp`: PASSED [SEC-04]
8. Controls (3): PASSED.

## Phase 3 Verification Evidence: Operator Sessions and Public Disclosure

Date: 2026-09-23
Requirements: SEC-12, SEC-13, SEC-14, SEC-15, SEC-16, SEC-17, SEC-18, SEC-19
Status: PASSED (All 8 requirements verified, all gates passed)

### Changes Summary

- Contract documentation updated in `docs/05_PUBLIC_API.md` (logout route, session token version validation, squall model admin-only, public sea condition `set_by_label`) and `docs/04_INGEST_API.md` (current events `uncalibrated` demotion).
- Migration 030 (`backend/migrations/030_user_token_version.sql`): added `token_version INTEGER NOT NULL DEFAULT 0` to `users`.
- Migration 031 (`backend/migrations/031_mesh_chat_created_at_index.sql`): added index on `mesh_chat (created_at)`.
- SEC-12: `create_token` includes `ver` claim with user's `token_version`.
  `require_user` verifies `sub` against database, checking that `token_version` matches and role matches.
  Added `POST /api/logout` endpoint that increments `token_version` on the user record.
  Updated `web/js/profile.js` to call `POST /api/logout` before clearing local storage.
- SEC-13: `login` in `backend/app/api/auth.py` evaluates `_DUMMY_HASH` with `verify_password` when email is unknown to eliminate timing discrepancy.
- SEC-14: `POST /api/ai/squall/train` now requires `require_admin_role`.
- SEC-15: Added `_serialise_public_sea_condition` returning `set_by_label` and omitting operator identity fields (`set_by_user_id`, `set_by_name`, email).
  Updated `mobile/lib/models/sea_condition.dart` to read `set_by_label` falling back to `set_by_name`.
- SEC-16: `ingest_current_event` in `backend/app/api/current_events.py` demotes `qualified` to `uncalibrated`.
- SEC-17: `coordinates()` in `backend/app/demo/weather.py` caps grid requests at `MAX_COORDINATE_CELLS = 64`.
- SEC-18: `_load_rows` in `backend/app/api/squall.py` accepts optional `since` parameter, defaulting `public_squall` to past 24 hours while keeping training unbounded.
- SEC-19: `ingest_chat` in `backend/app/api/mesh.py` enforces 30-day retention cleanup on `mesh_chat`.

### Verification Gates

#### 1. Backend Gate

Commands executed from `backend/`:
```powershell
ruff check app tests
pytest -q -p no:cacheprovider
```

Result:
- Ruff: All checks passed (0 errors).
- Pytest default suite: 409 passed, 5 skipped, 1 xfailed.
- Status: PASSED.

#### 2. Web Gate

Command executed from repository root:
```powershell
node --test web/test/*.test.js
```

Result:
- Node test runner: 149 passed, 0 failed.
- Status: PASSED.

#### 3. Mobile Gate

Commands executed from `mobile/`:
```powershell
flutter gen-l10n
flutter analyze
flutter test
```

Result:
- Flutter analyze: No issues found (ran in 19.7s).
- Flutter test: 261 passed, 0 failed.
- Status: PASSED.

#### 4. Probe Gate (PostgreSQL 18 on Port 55432)

Command executed from `backend/`:
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\User\.gemini\antigravity-cli\brain\5f1ba94e-af06-4466-b19e-6d81fc6cb5c0\scratch\run_probe_gate.ps1
```

Result:
- Total probe items: 43.
- Passed: 29 (+9 passed from Phase 2).
- Failed: 14 (open findings scheduled for Phase 4 through Phase 7).
- Errors: 0.
- Migrations 030 and 031 applied cleanly on fresh throwaway databases.
- Status: PASSED.

### Probe Status Changes (Phase 3)

1. `tests/security_probes/test_probe_auth.py::test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password`: PASSED [SEC-13]
2. `tests/security_probes/test_probe_auth.py::test_token_for_an_account_that_no_longer_exists_is_rejected`: PASSED [SEC-12]
3. `tests/security_probes/test_probe_auth.py::test_non_admin_operator_cannot_replace_the_live_squall_model[mdrrmo]`: PASSED [SEC-14]
4. `tests/security_probes/test_probe_auth.py::test_non_admin_operator_cannot_replace_the_live_squall_model[lgu]`: PASSED [SEC-14]
5. `tests/security_probes/test_probe_auth.py::test_squall_control_admin_reaches_the_model_write`: PASSED [SEC-14 control]
6. `tests/security_probes/test_probe_public_disclosure.py::test_public_sea_condition_does_not_expose_operator_account`: PASSED [SEC-15]
7. `tests/security_probes/test_probe_ingest_trust.py::test_request_text_cannot_mark_a_current_reading_qualified`: PASSED [SEC-16]
8. `tests/security_probes/test_probe_resource_bounds.py::test_demo_weather_rejects_ten_thousand_coordinate_cells`: PASSED [SEC-17]
9. `tests/security_probes/test_probe_resource_bounds.py::test_public_squall_does_not_load_week_old_readings`: PASSED [SEC-18]
10. `tests/security_probes/test_probe_resource_bounds.py::test_mesh_chat_has_a_retention_or_admission_control`: PASSED [SEC-19]

#### Regression Check: Phases 1 and 2 Probes Stay Green

- All Phase 1 probes (SEC-01 through SEC-05, including anomaly evaluation and whole fleet cost measurement) stay PASSED.
- All Phase 2 probes (SEC-06 through SEC-11, including SOS provenance, active feed, vessel profile auth, trips auth, advisory auth, catch log scoping) stay PASSED.

### Manual Replay Check

Executed on migrated local Postgres database:
1. Seeded user `op@example.com` with role `mdrrmo`.
2. Called `POST /api/login` -> HTTP 200, received bearer token.
3. Called `GET /api/me` with bearer token -> HTTP 200, returned `op@example.com`.
4. Called `POST /api/logout` with bearer token -> HTTP 200, returned `{'message': 'Logged out.'}` (incremented `token_version` to 1).
5. Replayed previous bearer token against `GET /api/me` -> HTTP 401 `{'detail': 'session revoked'}`.

### Probe Harness Fixes Logged

1. `backend/tests/security_probes/conftest.py`: Added `import migrate` to fixture setup so throwaway databases run schema migrations.
   Added operator user seeding in `probe_db` fixture so authenticated routes have user 1 on migrated test databases.
2. `backend/tests/security_probes/test_probe_auth.py`: Updated `_stub_training` harness to inspect caller role and supply matching operator user for `users` queries so train endpoint can reach role check.

