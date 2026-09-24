# Evidence: Web track

Plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`; track file listed in its header table.
Each phase appends a dated section: red and green test runs, gate results, and any device or bench record.
Row counts and IDs only; never data, URLs or credentials.

## W1 - alarm and honest coordinates (2026-09-24)

- Red run: focused `dashboard-alarm` and `dashboard-utils` tests failed on the missing persistent audio banner text, notification method, and `formatLatLon` helper.
- Green run: focused `dashboard-alarm`, `dashboard-utils`, and `dashboard-reaudit` suites - 119 passed, 0 failed.
- Gate: JavaScript syntax checks for the changed modules and tests passed.
- Browser check and screenshots: pending; no browser tab was available during this check.

## W2 - resolve and acknowledge dialogs (2026-09-24)

- Automated checks: `dashboard-incidents.test.js` covers reasoned resolve, expected versions, undo, no-ETA default, UTF-8 note limits and 409 handling; `dashboard-runtime.test.js` covers the target snapshot.
- Green gate: `node --test web/test/*.test.js` - 171 passed, 0 failed.
- Syntax gate: all JavaScript files under `web/js` and `web/test` passed `node --check`.
- Red run before implementation: not captured.
- Browser check against B1: pending; browser surface unavailable.

## W3 - triage feed and flood handling (2026-09-24)

- Automated check: `dashboard-live-sos.test.js` verifies server order, the `limit=200` endpoint, flood state, total count, late/flag/delivery labels and alternate position marker.
- Green gate: `node --test web/test/*.test.js` - 171 passed, 0 failed.
- Syntax gate: all JavaScript files under `web/js` and `web/test` passed `node --check`.
- Red run before implementation: not captured.
- Browser/performance check against B4: pending; browser surface and B4 backend are unavailable.

## W4 - trust, ops status, sessions and AI states (2026-09-24)

- Automated checks: `dashboard-ops-status.test.js`, `dashboard-runtime.test.js` and `dashboard-live-sos.test.js` cover contract-facing labels and behavior with stubs.
- Green gate: `node --test web/test/*.test.js` - 171 passed, 0 failed.
- Syntax gate: all JavaScript files under `web/js` and `web/test` passed `node --check`.
- Red run before implementation: not captured.
- Browser check against B3-B7: pending; browser surface and backend implementation are unavailable.
- Visual checks at 1280 px and 1920 px, in light and dark themes: pending.
