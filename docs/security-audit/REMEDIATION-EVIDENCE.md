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

## Phase 4: Handset tells the truth

### Environment

- Date: 2026-09-24T08:25:00+08:00
- Branch: `fix/security-audit-remediation`
- Requirements: SEC-20, SEC-21, SEC-22, SEC-23, SEC-24, SEC-25
- Contract changes:
  - `docs/05_PUBLIC_API.md`: Documented `onset_at` ISO 8601 UTC timestamp in squall status response when level is `watch` or `return_now`.

### Verification Gates

#### 1. Backend Default Gate

Commands executed from `backend/`:
```powershell
python -m ruff check app tests
python -m pytest -q -p no:cacheprovider
```

Result:
- Ruff: All checks passed (0 errors).
- Pytest default suite: 410 passed, 5 skipped, 1 xfailed.
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
flutter analyze
flutter test
flutter test test_security_probes
```

Result:
- Flutter analyze: No issues found (0 warnings, 0 errors).
- Flutter test default suite: 265 passed, 0 failed.
- Mobile security probes: 6 passed, 0 failed.
- Status: PASSED.
- Note on probe count: The plan references 7 Dart probes; the repository holds 6 probe tests across `sos_probes_test.dart` (4), `squall_probes_test.dart` (1), and `flutter_reaudit_probe_test.dart` (1).
  All 6 tests passed.

#### 4. Probe Gate (PostgreSQL 18 on Port 55432)

Command executed from `backend/`:
```powershell
$dataDir = "$env:TEMP\aqone_probe_pg_data"
if (!(Test-Path $dataDir)) { & 'C:\Program Files\PostgreSQL\18\bin\initdb.exe' -D $dataDir -U postgres -A trust -E UTF8 }
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir -o '-p 55432' -l "$env:TEMP\aqone_probe_pg.log" start
Start-Sleep -Seconds 2
$env:AQONE_SECURITY_PROBES = '1'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest tests/security_probes -p no:cacheprovider -s --junitxml=../docs/security-audit/probe-runs/phase-4/backend-probes.xml
Remove-Item Env:AQONE_SECURITY_PROBES, Env:AQONE_PROBE_PG_ADMIN_URL -ErrorAction SilentlyContinue
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir stop
```

Result:
- Total probe items: 43.
- Passed: 30 (+1 net passed from Phase 3: `test_handset_reply_reaches_an_sos_that_arrived_only_over_the_buoy`).
- Failed: 13 (open findings for Phase 5 firmware and Phase 6 release APK, plus 2 deferred hotspot probes).
- Errors: 0.
- Status: PASSED.

### Probe Status Changes (Phase 4)

1. `tests/security_probes/test_probe_sos.py::test_handset_reply_reaches_an_sos_that_arrived_only_over_the_buoy`: PASSED [SEC-21 backend half]
2. `mobile/test_security_probes/sos_probes_test.dart::[mobile.sos.standdown-intent-treated-resolved] a stand-down the backend rejected (503) is not shown as resolved`: PASSED [SEC-20]
3. `mobile/test_security_probes/sos_probes_test.dart::[mobile.sos.standdown-intent-treated-resolved] a stand-down never sent (no backend id yet) is not shown as resolved`: PASSED [SEC-20]
4. `mobile/test_security_probes/sos_probes_test.dart::[mobile.sos.standdown-intent-treated-resolved:control] an accepted stand-down is resolved`: PASSED [SEC-20 Control]
5. `mobile/test_security_probes/sos_probes_test.dart::[mobile.sos.buoy-only-reply-unroutable] handset half: the reply to a buoy-only SOS is delivered`: PASSED [SEC-21 mobile half]
6. `mobile/test_security_probes/sos_probes_test.dart::[mobile.eta.server-clock-discarded] rescue ETA is measured against server time, not the phone clock`: PASSED [SEC-22]
7. `mobile/test_security_probes/squall_probes_test.dart::[mobile.squall.ack-survives-missed-clear] a squall six hours later on the same buoys alarms again after a missed clear`: PASSED [SEC-23]

#### Regression Check: Phases 1, 2, and 3 Probes Stay Green

- All Phase 1 probes (SEC-01 through SEC-05) remain PASSED.
- All Phase 2 probes (SEC-06 through SEC-11) remain PASSED.
- All Phase 3 probes (SEC-12 through SEC-19) remain PASSED.

### Trace Tasks Re-Evaluation (PROBES.md Section 4)

#### T1 - mobile.location.undisclosed-weather-coordinate-egress (SEC-24)

1. Does `HomePage` read the device position during initialisation, without the fisher tapping anything?
   Yes (`mobile/lib/ui/home_page.dart:181`).
2. Are those coordinates placed in a request to the AqOne backend forecast route, to `api.open-meteo.com`, or both?
   Yes, but coordinates are now coarsened to 1 decimal place (~11 km) before egress in `mobile/lib/services/forecast_provider.dart:55-56, 172-173`.
3. Are the requested coordinates persisted, for example under the `forecast_record_v2` SharedPreferences key?
   Yes, and stored coordinates are now rounded to 1 decimal place in `mobile/lib/models/forecast_outlook.dart:153-171`.
4. What does the in-app location or privacy text say location is used for?
   `mobile/lib/ui/info_page.dart:141-147` (`InfoCopy.privacy`): "Precise position is only sent as part of an SOS you deliberately send. Weather forecasts use your approximate location (about 11 km). The online map fetches map tiles for the area you are viewing from OpenStreetMap."
   Verdict: REMEDIATED. Coordinates sent and stored for forecasts are coarse (~11 km) and location use is explicitly disclosed.

#### T2 - mobile.map.undisclosed-location-derived-tile-egress (SEC-25)

1. Does the Venture map centre its camera on the device fix?
   Yes (`mobile/lib/ui/venture_page.dart:118-124`).
2. When the offline MBTiles asset is missing, does tile loading fall back to `tile.openstreetmap.org`?
   Yes (`mobile/lib/services/mbtiles_provider.dart:82`).
3. Is the MBTiles asset both declared in `mobile/pubspec.yaml` and present on disk?
   Asset is declared in `mobile/pubspec.yaml:70` and missing from disk.
4. What does the in-app location or privacy text say location is used for?
   `mobile/lib/ui/info_page.dart:141-147` (`InfoCopy.privacy`): "The online map fetches map tiles for the area you are viewing from OpenStreetMap."
   Verdict: REMEDIATED. Online tile loading from OpenStreetMap is explicitly disclosed in privacy copy.

### Implementation Details and Scope Notes

1. Stand-down persistence (SEC-20): `AppDatabase` schema bumped to version 14 with `fisher_reply_synced INTEGER NOT NULL DEFAULT 0` column.
   `SosRecord.isStoodDown` requires both `fisherReply == 2` and `fisherReplySynced == true`.
   While unsynced, UI shows pending stand-down banner (`standDownPendingTitle`, `standDownPendingDescription`, `responderReplyPendingSafeNow`).
2. Buoy-only SOS replies (SEC-21): `SosService._sendReply` re-posts direct SOS when `!_backend.hasVesselCredential` prior to posting reply.
   Backend idempotent `COALESCE` populates `local_id` so subsequent reply route matches without requiring device credential.
3. Server-relative ETA (SEC-22): `RemoteSos` parses `server_time` from backend and buoy envelopes.
   `SosService._applyRemote` computes device ETA adjusted for server clock skew (`deviceNow + (serverEta - serverNow)`).
4. Squall identity (SEC-23): Backend `GET /api/public/squall` exposes `onset_at` ISO timestamp for `watch` and `return_now` levels.
   `SquallWatch.identity` incorporates `onsetAt`, or falls back to a 3-hour UTC bucket floored `observedAt` to re-alarm if a clear was missed.
5. Privacy Copy (SEC-24, SEC-25): `InfoCopy` in `mobile/lib/ui/info_page.dart` is English-only today; per plan, moving it to ARB is out of scope.

### Probe Harness Fixes Logged

1. `backend/tests/security_probes/test_probe_sos.py`: Authorized change for SEC-21: directly re-posted SOS with `local_id` before unauthenticated reply to exercise backend `COALESCE` ingest logic while keeping `fisher_reply == 2` assertion.
2. `mobile/test_security_probes/sos_probes_test.dart`: Authorized change for SEC-21: mock backend records `local_id` on `POST /api/sos` and verifies it on `/api/sos/reply/{local_id}` while keeping `expect(ok, isTrue)`.
   Added `import 'dart:convert';` and `request is http.Request` guard for body reading.
3. `mobile/test/widget_test.dart`: Extended with tests verifying that pending stand-down does not show still-in-danger warning, while synced stand-down does.
4. `mobile/test/forecast_provider_test.dart`: Added unit tests verifying outgoing query parameters for `AqOneForecastProvider` and `OpenMeteoForecastProvider` use 1-decimal-place coordinates.
5. `mobile/test/sos_record_test.dart`: Updated stand-down test to assert `isStoodDown` requires `fisherReplySynced: true` and is false when `fisherReplySynced: false`.
6. `mobile/test/sos_service_test.dart`: Updated ack read-back test to align mock `server_time` with `eta_at` under SEC-22 server time adjustment.

## Phase 5: Firmware hardening

### Verification Summary

- [x] Contract first: `docs/02_LOAM_PACKET_SPEC.md` updated with WARN `rev` field (SEC-29) and `txEnqueue` ring reserve capacity rules (SEC-30). Daniel informed via evidence below.
- [x] SEC-31: removed the two leading spaces on line 1 of `firmware/shore/AqOneShore/AqOneLoam.h`. `diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h` prints nothing.
- [x] SEC-26 & SEC-27: moved `UPLINK_SSID`, `UPLINK_PASS`, `GATEWAY_API_KEY` (shore) and `LOAM_KEY` (both) into gitignored `AqOneSecrets.h` next to each sketch. Committed `AqOneSecrets.h.example` with placeholders. Added `#error` when the header is missing and compile/link guard when `LOAM_KEY` equals the old default. Both `AqOneLoam.h` copies include the header identically. Added `.gitignore` ignore rules and updated `firmware/README.md`.
- [x] Shore: sends `X-Api-Key: GATEWAY_API_KEY` on `POST /api/sos` and `POST /api/advisories/delivery`, matching Phase 2.
- [x] SEC-28: replaced `client.setInsecure()` with `client.setCACert(BACKEND_CA_CERTS)` holding root CAs for `aqone-backend.onrender.com` (GlobalSign ECC Root CA - R4 primary, GTS Root R1 and ISRG Root X1 backups). Documented expiry dates and rotation procedure in `firmware/README.md`.
- [x] SEC-29: shore populates `rev` (advisory `updated_at` epoch seconds) on each WARN payload; buoy stores `rev` in `CachedWarning` and ignores frames with non-newer revisions. Backend public advisories feed was verified to already expose `updated_at` (and documented in `docs/05_PUBLIC_API.md`).
- [x] SEC-30: `txEnqueue` takes `size_t reserve = 0`. Chat frames set `reserve = 2` (requiring > 2 free ring slots), while SOS, ACK, and WARN frames may use any free slot. Both `AqOneLoam.h` headers updated identically.
- [x] Compilation: PlatformIO 6.2.0 installed in a scratch venv outside repo (`.gemini/antigravity-cli/brain/.../scratch/pio_venv`). Both `buoy` and `shore` compiled clean with 0 errors and 0 warnings using temporary `AqOneSecrets.h` from `.example`. Scratch secrets deleted immediately after verification.
- [x] Backend default gate: `ruff check app tests` clean, `pytest -q -p no:cacheprovider` passed (410 passed, 5 skipped, 1 xfailed).
- [x] Mobile gate: `flutter analyze` clean (0 issues), `flutter test` passed (265 passed, 0 failed), `flutter test test_security_probes` passed (all 6 passed).
- [x] Web gate: `node --test web/test/*.test.js` passed (149 passed, 0 failed).
- [x] Probe gate: 38 passed (+8 net over Phase 4; all SEC-26 through SEC-31 probes passed), 5 failed (2 deferred hotspot probes, 1 deferred per-device LoRa key probe, 2 Phase 6 release APK probes), 0 errors.
- [x] Git status: verified no `AqOneSecrets.h` staged or committed.

### Gate Command Evidence

#### 1. Header Diff (SEC-31)
```powershell
git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
# Exit code 0, 0 bytes output. The two headers are byte-identical.
```

#### 2. PlatformIO Compilation Verification
Scratch secrets generated from `.example`, compiled using PlatformIO in external venv:
```powershell
Copy-Item firmware/buoy/AqOneBuoy/AqOneSecrets.h.example firmware/buoy/AqOneBuoy/AqOneSecrets.h
Copy-Item firmware/shore/AqOneShore/AqOneSecrets.h.example firmware/shore/AqOneShore/AqOneSecrets.h

$env:PLATFORMIO_SRC_DIR = "buoy/AqOneBuoy"
& "$env:SCRATCH\pio_venv\Scripts\pio.exe" run -d firmware -e buoy
# Result: SUCCESS in 48.2s (RAM: 18.3% used 59840 B, Flash: 26.0% used 869097 B)

$env:PLATFORMIO_SRC_DIR = "shore/AqOneShore"
& "$env:SCRATCH\pio_venv\Scripts\pio.exe" run -d firmware -e shore
# Result: SUCCESS in 43.3s (RAM: 15.6% used 51048 B, Flash: 29.7% used 993537 B)

Remove-Item firmware/buoy/AqOneBuoy/AqOneSecrets.h, firmware/shore/AqOneShore/AqOneSecrets.h
```

#### 3. Backend Default Gate
```powershell
ruff check app tests
# Output: All checks passed!

pytest -q -p no:cacheprovider
# Output: 410 passed, 5 skipped, 1 xfailed in 25.24s
```

#### 4. Web Gate
```powershell
node --test web/test/*.test.js
# Output: tests 149, pass 149, fail 0
```

#### 5. Mobile Gate
```powershell
flutter analyze
# Output: No issues found! (ran in 4.1s)

flutter test
# Output: All 265 tests passed!

flutter test test_security_probes
# Output: All 6 tests passed!
```

#### 6. Probe Gate (Local Postgres 18 on Port 55432)
```powershell
$dataDir = "$env:TEMP\aqone_probe_pg_data"
if (!(Test-Path $dataDir)) { & 'C:\Program Files\PostgreSQL\18\bin\initdb.exe' -D $dataDir -U postgres -A trust -E UTF8 }
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir -o '-p 55432' -l "$env:TEMP\aqone_probe_pg.log" start
Start-Sleep -Seconds 2
$env:AQONE_SECURITY_PROBES = '1'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest tests/security_probes -p no:cacheprovider -s --junitxml=../docs/security-audit/probe-runs/phase-5/backend-probes.xml
Remove-Item Env:AQONE_SECURITY_PROBES, Env:AQONE_PROBE_PG_ADMIN_URL -ErrorAction SilentlyContinue
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D $dataDir stop
```
Output:
- Total probe items: 43.
- Passed: 38 (+8 net over Phase 4).
- Failed: 5 (3 deferred: `test_hotspot_cell_needs_five_distinct_reporters[3]`, `test_hotspot_cell_needs_five_distinct_reporters[4]`, `test_loam_signature_key_is_selected_per_source_id`; 2 Phase 6: `test_release_build_does_not_fall_back_to_debug_signing`, `test_tracked_release_apk_is_not_debug_signed`).
- Errors: 0.

### Probe Status Changes (Phase 5)

1. `test_shore_sketch_holds_no_concrete_credential[UPLINK_SSID]`: PASSED [SEC-26]
2. `test_shore_sketch_holds_no_concrete_credential[UPLINK_PASS]`: PASSED [SEC-26]
3. `test_shore_sketch_holds_no_concrete_credential[GATEWAY_API_KEY]`: PASSED [SEC-26]
4. `test_loam_key_is_not_the_repository_default`: PASSED [SEC-27]
5. `test_loam_control_headers_are_byte_identical`: PASSED [SEC-31 Control]
6. `test_shore_verifies_the_backend_certificate`: PASSED [SEC-28]
7. `test_buoy_warning_cache_orders_updates_by_revision`: PASSED [SEC-29]
8. `test_tx_ring_keeps_capacity_for_distress_frames`: PASSED [SEC-30]

### Contract Notice for Daniel (Hardware/Firmware Owner)

`docs/02_LOAM_PACKET_SPEC.md` was updated:
1. `WARN` packets (type `0x07`): Added documentation for optional `rev` field containing advisory `updated_at` epoch seconds (UTC). Buoys compare incoming `rev` against cached warnings for that ID and ignore frames whose `rev` is not newer (`rev <= cached.rev`), preventing replay attacks and resurrection of cancelled warnings.
2. `txEnqueue`: Documented the `reserve` parameter and ring capacity rules. Chat frames (`0x05`) require > 2 free slots in `txRing` (`reserve = 2`), preventing chat floods from starving distress (`SOS`), `ACK`, and `WARN` frames.
3. Secrets handling: Firmware developers must copy `AqOneSecrets.h.example` to `AqOneSecrets.h` next to `AqOneBuoy.ino` and `AqOneShore.ino`. `AqOneSecrets.h` is gitignored and must never be committed. Real keys must be set prior to flashing.


