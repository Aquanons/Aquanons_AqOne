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

Not started.

## F3 - Anomaly monitoring is fleet-wide and top level

Not started.

## F4 - A fisher reply marks a call reopened only when it really reopens

Not started.

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
