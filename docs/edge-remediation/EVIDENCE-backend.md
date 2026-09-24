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