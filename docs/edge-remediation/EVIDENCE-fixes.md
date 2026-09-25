# Edge review fixes evidence

## Step 0 - Baseline

- Backend `python -m ruff check app tests`: passed.
- Backend main suite: 559 passed, 5 skipped, 1 xfailed.
- Backend security probes: 11 passed, 3 failed. The failures are exactly `test_hotspot_cell_needs_five_distinct_reporters[3]`, `test_hotspot_cell_needs_five_distinct_reporters[4]`, and `test_loam_signature_key_is_selected_per_source_id`, matching the documented deferred baseline.
- Mobile `flutter gen-l10n`: passed.
- Mobile `flutter analyze`: passed with no issues.
- Mobile `flutter test`: 316 passed.
- Mobile `flutter test test_security_probes`: 6 passed.
- Web: 171 passed.
- Web JavaScript syntax checks: passed.
- Firmware `AqOneLoam.h` copies: identical; `git diff --no-index` printed nothing.
- Baseline matches the plan after the working-tree ReadOnly attribute was cleared.

## F1 - Shore gateway sends its key on chat calls

Red run: `python -m pytest -q -p no:cacheprovider tests/test_firmware_security.py::test_shore_chat_calls_send_gateway_key`

```text
FAILED tests/test_firmware_security.py::test_shore_chat_calls_send_gateway_key
AssertionError: bool postChat( must authenticate its /api/mesh/chat request with GATEWAY_API_KEY
1 failed in 0.39s
```

The first request failed because pytest was invoked from the repository root; rerunning from `backend/` produced the failing assertion above.

Green run: `python -m pytest -q -p no:cacheprovider tests/test_firmware_security.py::test_shore_chat_calls_send_gateway_key` - 1 passed.

Gates: ruff clean; backend 560 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 deferred failures; mobile analyze clean, 316 passed, security probes 6 passed; web 171 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F2 - Version conflicts return `current`

Red run: `python -m pytest -q -p no:cacheprovider tests/test_edge_lifecycle_pg.py::test_version_conflict_body_carries_current_for_acknowledge tests/test_edge_lifecycle_pg.py::test_version_conflict_body_carries_current_for_resolve tests/test_edge_lifecycle_pg.py::test_version_conflict_body_carries_current_for_reopen`

```text
FAILED tests/test_edge_lifecycle_pg.py::test_version_conflict_body_carries_current_for_acknowledge
FAILED tests/test_edge_lifecycle_pg.py::test_version_conflict_body_carries_current_for_resolve
FAILED tests/test_edge_lifecycle_pg.py::test_version_conflict_body_carries_current_for_reopen
AssertionError: 409 body must expose the event under current
3 failed in 19.57s
```

Green run: all three named tests and `test_ack_with_stale_version_conflicts` passed (4 passed).

Guard: `web/test/dashboard-incidents.test.js` test `409 displays the current answer and waits for another confirmation` passed in the full web suite.

Gates: ruff clean; backend 563 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 deferred failures; mobile analyze clean, 316 passed, security probes 6 passed; web 171 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F3 - Anomaly monitoring is fleet-wide and top level

Backend red run: `python -m pytest -q -p no:cacheprovider tests/test_edge_monitoring_pg.py tests/test_anomaly_active_readonly.py::test_active_never_writes`

```text
FAILED tests/test_edge_monitoring_pg.py::test_active_is_unavailable_without_live_contacts
FAILED tests/test_edge_monitoring_pg.py::test_active_is_available_with_a_recent_buoy_contact
FAILED tests/test_edge_monitoring_pg.py::test_handset_contacts_alone_leave_monitoring_unavailable
FAILED tests/test_edge_monitoring_pg.py::test_stale_contacts_leave_monitoring_unavailable
FAILED tests/test_anomaly_active_readonly.py::test_active_never_writes
AssertionError: active anomaly response must include top-level monitoring metadata
5 failed in 6.95s
```

Web red run: `node --test web/test/dashboard-runtime.test.js`

```text
anomaly feed renders Not monitoring for an empty unavailable payload: passed
anomaly feed ignores a bare list: failed
AssertionError: assert.ok(riskList.innerHTML.includes('ai-unavailable-state'))
```

Existing tests updated: removed `test_monitoring_unavailable_without_contacts`, whose assertion encoded the per-row rule; `test_active_never_writes` now reads `response.json()['rows']` and keeps its read-only assertion.

Green runs: backend monitoring and active-readonly tests: 7 passed; web runtime tests: 40 passed, including both anomaly feed cases.

Gates: ruff clean; backend 566 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 deferred failures; mobile analyze clean, 316 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F4 - A fisher reply marks a call reopened only when it really reopens

Backend red run: `python -m pytest -q -p no:cacheprovider tests/test_edge_lifecycle_pg.py::test_still_in_danger_on_open_incident_does_not_mark_reopened tests/test_edge_lifecycle_pg.py::test_still_in_danger_reopen_is_audited`

```text
FAILED tests/test_edge_lifecycle_pg.py::test_still_in_danger_on_open_incident_does_not_mark_reopened
AssertionError: expected reopened_at IS NULL; the open incident received a reopened_at timestamp
FAILED tests/test_edge_lifecycle_pg.py::test_still_in_danger_reopen_is_audited
AssertionError: expected an operations_audit_events row; no audit row was found
2 failed in 4.38s
```

Mobile red run: `flutter test test/sos_service_test.dart`

```text
fisher reply survives reconcile when the incident was never closed: Expected <1>, Actual <null>
a reopen clears a closed record once, not on every reconcile: Expected <1>, Actual <null>
Both named tests failed; the other 20 tests in sos_service_test.dart passed.
```

Green runs: the two new backend tests plus the existing reopen-window guards: 4 passed; `flutter test test/sos_service_test.dart`: 22 passed.

Gates: ruff clean; backend 568 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 deferred failures; mobile analyze clean, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F5 - A fisher's SAFE_NOW closes the call as `stood_down_by_fisher`

Not started.

## F6 - `many_calls_same_vessel` fires at two open calls

Not started.

## F7 - Scheduler reports the contract's job names

Not started.

## F8 - A failed escalation SMS is retried

Not started.

## F9 - Line endings and rationale comments in `sos.py` and `anomaly_service.py`

Not started.

## F10 - Over-engineering cuts

Not started.

## Pending - Len

- `pio run -d firmware -e shore`, then flash the shore and confirm a dashboard chat line reaches a boat. PlatformIO is not installed in this environment.
