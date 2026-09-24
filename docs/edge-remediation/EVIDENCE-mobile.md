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


