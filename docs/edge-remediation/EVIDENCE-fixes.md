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

Red run: `python -m pytest -q -p no:cacheprovider tests/test_edge_lifecycle_pg.py::test_safe_now_reply_stores_stood_down_by_fisher`

```text
FAILED tests/test_edge_lifecycle_pg.py::test_safe_now_reply_stores_stood_down_by_fisher
AssertionError: assert 'safe_confirmed' == 'stood_down_by_fisher'
1 failed in 3.52s
```

Implementation check: the named PostgreSQL test passes after parameterizing the stored resolution code.
Guard red run: `python -m pytest -q -p no:cacheprovider tests/test_responder_loop.py::test_safe_now_resolves_and_removes_the_event_from_the_active_feed`

```text
FAILED tests/test_responder_loop.py::test_safe_now_resolves_and_removes_the_event_from_the_active_feed
assert reply.status_code == 200
E assert 500 == 200
1 failed in 2.72s
```

The fake pool unpacks exactly four SQL parameters, while the fix supplies five. Revision 2 explicitly allows updating this fake branch.

Green runs: `python -m pytest -q -p no:cacheprovider tests/test_edge_lifecycle_pg.py::test_safe_now_reply_stores_stood_down_by_fisher tests/test_responder_loop.py`: 16 passed.

Gates: ruff clean; backend 569 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 baseline failures; mobile gen-l10n passed, analyze 0 issues, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F6 - `many_calls_same_vessel` fires at two open calls

Red run: `python -m pytest -q -p no:cacheprovider tests/test_plausibility.py::test_many_calls_flag_at_two_open_calls`

```text
FAILED tests/test_plausibility.py::test_many_calls_flag_at_two_open_calls
AssertionError: assert 'many_calls_same_vessel' in []
1 failed in 0.48s
```

Green run: `python -m pytest -q -p no:cacheprovider tests/test_plausibility.py`: 8 passed.

Gates: ruff clean; backend 570 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 baseline failures; mobile gen-l10n passed, analyze 0 issues, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F7 - Scheduler reports the contract's job names

Red run: `python -m pytest -q -p no:cacheprovider tests/test_edge_scheduler_pg.py::test_ops_status_scheduler_keys_match_contract tests/test_edge_scheduler_pg.py::test_scheduler_starts_the_contract_jobs`

```text
ERROR collecting tests/test_edge_scheduler_pg.py
ImportError: cannot import name 'ANOMALY_JOB' from 'app.scheduler'
1 error in 3.16s
```

Green run: the two named scheduler tests passed: 2 passed.

Gates: ruff clean; backend 572 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 baseline failures; mobile gen-l10n passed, analyze 0 issues, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical. An initial ruff check caught import ordering in the new test; imports were reordered before the full gates.

## F8 - A failed escalation SMS is retried

Red run: `python -m pytest -q -p no:cacheprovider tests/test_edge_scheduler_pg.py::test_failed_sms_is_retried_on_the_next_run tests/test_edge_scheduler_pg.py::test_unconfigured_sms_is_not_retried`

```text
FAILED tests/test_edge_scheduler_pg.py::test_failed_sms_is_retried_on_the_next_run
AssertionError: assert ['failed'] == ['failed', 'sent']
1 failed, 1 passed in 4.49s
```

Green run: `python -m pytest -q -p no:cacheprovider tests/test_edge_scheduler_pg.py`: 7 passed.

Gates: ruff clean; backend 574 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 baseline failures; mobile gen-l10n passed, analyze 0 issues, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

## F9 - Line endings and rationale comments in `sos.py` and `anomaly_service.py`

No behavior change; no red test applies.

Gates: ruff clean; backend 574 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 baseline failures; mobile gen-l10n passed, analyze 0 issues, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical.

`backend/app/api/sos.py` has 864 CRLF line endings and 0 bare LF line endings, verified from file bytes because the `file` utility is unavailable in PowerShell. Its `git diff master --ignore-cr-at-eol --stat` remained `374 insertions(+), 264 deletions(-)` across line-ending conversion. Restored the specified downlink docstring, SEC-06 comments, and `OPEN_TRIP_FRESHNESS_WINDOW` rationale.

## F10 - Over-engineering cuts

No behavior change; existing tests are the guards. Applied matching-helper consolidation, shared coordinate-conflict SQL, removal of the duplicate handset filter, SMS-number parsing helper and semaphore removal, lifecycle helper inlining, mobile byte-limit alias removal, and default closure-code branch removal.

The explicitly listed lifecycle unit tests for `can_reopen` and `resolution_code_from` were removed; their behavior remains covered by the lifecycle PostgreSQL tests.

Two cuts were reverted after existing guards failed, as required by Section 5:
- Removing the `utf8ByteLength` fallback failed `ack modal captures target and prevents background case switching` with `TypeError: utf8ByteLength is not a function`; the runtime harness does not provide the core namespace helper.
- Dropping `event.pod_id` failed `SOS display labels stay neutral and follow the event fields`: expected `Relayed by pod P-4 - sender not verified`, got `Relayed by pod unknown - sender not verified`.

Gates: ruff clean; backend 572 passed, 5 skipped, 1 xfailed; backend security probes 11 passed and the same 3 baseline failures; mobile gen-l10n passed, analyze 0 issues, 318 passed, security probes 6 passed; web 173 passed and JavaScript syntax checks clean; `AqOneLoam.h` copies identical. The backend test count is two lower because F10 explicitly removed the two helper-specific unit tests.

## Pending - Len

- `pio run -d firmware -e shore`, then flash the shore and confirm a dashboard chat line reaches a boat. PlatformIO is not installed in this environment.
