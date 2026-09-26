# Evidence: Mobile track

Plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`; track file listed in its header table.
Each phase appends a dated section: red and green test runs, gate results, and any device or bench record.
Row counts and IDs only; never data, URLs or credentials.

## Phase M1: Delivery policy - relayed is not terminal (2026-09-24)

### Red run
- Command: `flutter test test/delivery_policy_test.dart test/sos_service_test.dart`
- Output:
  - `test/delivery_policy_test.dart`: failed to compile (missing `lib/models/delivery_policy.dart`, `lastAttemptAt` on `SosRecord`, `routesDue`, `isStale`).
  - `test/sos_service_test.dart`: failed to compile (missing `delivery_policy.dart`, `recordAttempt` on `OutboxStore`).

### Green run
- Command: `flutter test test/delivery_policy_test.dart test/sos_service_test.dart test/widget_test.dart`
- Output: All tests passed (34 passed).

### Gate results
- `flutter gen-l10n`: passed (0 errors)
- `flutter analyze`: passed (0 issues found)
- `flutter test`: passed (278 passed)
- `flutter test test_security_probes`: passed (6 passed)

### Manual / Device checks
- `Pending - Len: Manual (emulator): point the buoy client at a stub that accepts and never delivers, with the backend reachable. The record goes saved, then relayed, then delivered within 60 s.`
  Done 2026-09-25 (plan 66 C3): see `EVIDENCE-critical.md`.

## Phase M2: Foreground service while an SOS is pending (2026-09-24)

### Spike findings
- Plugin: `flutter_foreground_task: ^11.0.3` pinned.
- Isolate execution: `TaskHandler` runs in a separate background isolate, not the main isolate.
- Single writer to SQLite: While the UI isolate is active, the UI isolate's `SosService` timers run and handle `retryPending()`.
  The UI isolate periodically sends a ping to the foreground task.
  Only when the UI isolate is detached (no ping received from the UI isolate within the ping window) does the background task handler initialize its own database connection and `SosService` to call `retryPending()`.
  This keeps one writer at a time to sqflite.
- Android 14 and 15 rules:
  - Android 14 (API 34+) requires `android:foregroundServiceType` to be declared in `AndroidManifest.xml` on `<service>`, along with matching permission(s).
  - For our use case, `location` is used (justified by late GPS fill in M3), requiring `FOREGROUND_SERVICE` and `FOREGROUND_SERVICE_LOCATION`.
  - Android 15 (API 35+) introduces 6-hour runtime timeouts for `dataSync` type, but `location` does not have this 6-hour limit.
  - Android 15 also restricts `BOOT_COMPLETED` receivers from launching certain types, and strengthens runtime checks when starting foreground services from the background.
  - Requesting battery optimization exemption (`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`) via `FlutterForegroundTask.requestIgnoreBatteryOptimization()` prevents Android Doze from cutting network/alarms while an emergency SOS is pending.

### Red run
- Command: `flutter test test/foreground_policy_test.dart`
- Output: failed to compile (missing `lib/models/foreground_policy.dart`, `shouldRunForeground`).

### Green run
- Command: `flutter test test/foreground_policy_test.dart test/sos_foreground_test.dart`
- Output: All tests passed (6 passed).

### Gate results
- `flutter gen-l10n`: passed (0 errors)
- `flutter analyze`: passed (0 issues found)
- `flutter test`: passed (284 passed)
- `flutter test test_security_probes`: passed (6 passed)

### Manual / Device checks
- `Pending - Len: release build on target phone, SOS pressed with pod and internet off, screen off for 30 min, then internet turned on. The SOS lands without opening the app.`

## Phase M3: Incident nonce, byte-safe text and late GPS fill (2026-09-24)

### Red run
- Command: `flutter test test/text_clamp_test.dart test/buoy_client_test.dart test/sos_service_test.dart`
- Output: failed to compile (missing `lib/models/text_clamp.dart`, `lateFixPollInterval` / late fix support in `SosService`).

### Green run
- Command: `flutter test test/text_clamp_test.dart test/buoy_client_test.dart test/sos_service_test.dart`
- Output: All tests passed (38 passed).

### Gate results
- `flutter gen-l10n`: passed (0 errors)
- `flutter analyze`: passed (0 issues found)
- `flutter test`: passed (294 passed)
- `flutter test test_security_probes`: passed (6 passed)

### Manual / Device checks
- `Pending - Len: After B2 merges: an emulator SOS appears once in /active with its nonce, and a second press in the same second creates a second row.`

## Phase M4: Stand-down safety, closure text and reopen (2026-09-24)

### Red run
- Command: `flutter test test/closure_text_test.dart test/widget_test.dart test/sos_service_test.dart`
- Output:
  - `test/closure_text_test.dart`: passed.
  - `test/widget_test.dart`: failed (stand-down needs confirmation, no ETA copy when acknowledged without eta, reopened incident clears resolved card, undo within 2 minutes sends still-in-danger).
  - `test/sos_service_test.dart`: failed (`closed record keeps reconciling for 2 hours to catch a reopen`).

### Green run
- Command: `flutter test test/closure_text_test.dart test/widget_test.dart test/sos_service_test.dart`
- Output: All tests passed (41 passed).

### Gate results
- `flutter gen-l10n`: passed (0 errors)
- `flutter analyze`: passed (0 issues found)
- `flutter test`: passed (302 passed)
- `flutter test test_security_probes`: passed (6 passed)

## Phase M5: Identity - enrolment, SOS before setup, and recoverable vessel identity (2026-09-25)

### Red run
- Command: `flutter test test/enrolment_page_test.dart test/backend_client_vessel_auth_test.dart test/backup_rules_test.dart test/sos_service_test.dart`
- Output: failed to compile and tests failed (missing `lib/ui/enrolment_page.dart`, `VesselAuthException`, `backup_rules.xml`, `vessel id exists from first launch`, `SOS without boat name is raised with vessel id only`).

### Green run
- Command: `flutter test test/enrolment_page_test.dart test/backend_client_vessel_auth_test.dart test/backup_rules_test.dart test/sos_service_test.dart test/widget_test.dart`
- Output: All tests passed (46 passed).

### Gate results
- `flutter gen-l10n`: passed (0 errors)
- `flutter analyze`: passed (0 issues found)
- `flutter test`: passed (311 passed)
- `flutter test test_security_probes`: passed (6 passed)

### Manual / Device checks
- `Pending - Len: install, note the vessel ID, uninstall with backup on, reinstall. The same vessel ID comes back.`

## Phase M6: Silent SOS, alarm stream siren, and localised SOS flow (2026-09-25)

### Red run
- Command: `flutter test test/sos_alarm_test.dart test/localization_test.dart test/widget_test.dart`
- Output:
  - `test/sos_alarm_test.dart`: failed to compile (missing `audioContext` getter on `SosAlarm`, missing `player` parameter).
  - `test/localization_test.dart`: failed (missing keys `settingsSilentSos`, `settingsSilentSosDescription`, `sosStoodDown`, `sosNoneSentYet` across ARB files; bare `Text('` literals found in `home_page.dart` and `venture_page.dart`).
  - `test/widget_test.dart`: failed to compile (missing `sosAlarm` parameter on `HomePage`).

### Green run
- Command: `flutter test test/sos_alarm_test.dart test/localization_test.dart test/widget_test.dart`
- Output: All tests passed (32 passed).

### Gate results
- `flutter gen-l10n`: passed (0 errors)
- `flutter analyze`: passed (0 issues found)
- `flutter test`: passed (316 passed)
- `flutter test test_security_probes`: passed (6 passed)

### Manual / Device checks
- `Pending - Len: on device, toggle silent SOS on in settings, trigger SOS; alarm siren stays silent while countdown and dispatch proceed.`
- ~~`Pending - Len: on device, with silent SOS off, hold SOS button for 3 seconds; countdown and dispatch proceed silently without siren.`~~ Superseded 2026-09-26: plan 65 Phase 1 (`7826488`) removed the hold gesture; a long press now behaves like a tap; the quick silent path becomes a "Silence" button on the countdown (docs/64 D8 and FFR-15, plan 65 Phase 4).



