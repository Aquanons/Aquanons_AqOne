# Web remediation re-audit - 2026-09-14

**Verdict: improvements landed, but the remediation is not complete.**
Two high-priority defects and three medium-priority defects remain or were introduced.
The blanket closure of F01-F14 is not supported by the current behavior.

## Scope and evidence

Reviewed Gemini's five commits from `56868b4` through `68da372`, their affected dashboard consumers, backend contract changes, tests, and completion documentation.
The working tree was clean when the audit started.
This report is the only repository change made by this audit.
The correctness review below is separate from the complexity-only Ponytail audit.

| Check | Result |
|---|---|
| `node --test web/test/*.test.js` | 114 passed, 0 failed |
| JavaScript syntax checks across `web/js` | Passed |
| Syntax parsing of the three changed Python files | Passed |
| Local browser, assembled dashboard | Reproduced Advisory and Buoy panel exceptions, and Emergency dialog Escape failure |
| Actual weather renderer with raw null fields | Reproduced zero readings and lower-risk verdict |
| Actual weather renderer with old source timestamp | Reproduced LIVE MODEL and lower-risk verdict |
| Focused SOS builder and alert activation probe | Synthetic and missing-provenance rows failed to open the incident drawer |
| Actual audit module with successful A then failed B search | Reproduced A displayed while export requests B |
| Actual trip-check module with success then failed poll | Retained prior rows without a stale indicator |
| Full backend pytest and Ruff | Not rerun: the available Python runtime has neither installed |
| Deployed backend, database persistence, hardware path | Not exercised |

Browser verification used a temporary static server for `web/` on localhost.
Backend API 404s in that environment are expected and are not counted as application defects.
The missing-function exceptions are independent of those 404s.
Weather and audit probes reused the existing test DOM helper while executing the application modules.
The SOS probe executed the actual builder and row-activation function bodies with controlled records.
These focused probes are not a replacement for an authenticated browser flow against the backend.

## Correctness findings

### R1 - P1: Raw null weather still becomes a lower-risk verdict

**Location:** `web/js/dashboard/dashboard-shortcuts-weather.js:223-234`.
**Status:** Original F02 remains open.

The renderer calls `Number(value)` before deciding whether wind, gust, and wave readings are present.
`Number(null)` is zero, so `classifySafety` receives valid-looking zeros instead of missing observations.
The same conversion also accepts empty strings and booleans.

**Reproduction:** Pass `wind_speed_10m: null`, `wind_gusts_10m: null`, `weather_code: 0`, `wave_height: null`, and `wave_period: null` to the actual renderer with `stale: false`.
It renders `MODEL: LOWER RISK`, `LIVE MODEL`, `Wind 0.0 / 0.0 km/h`, and `Waves 0.00 m / 0.0 s`.
This can reassure an operator when the observations are unavailable.

**Smallest fix:** Validate raw numeric types and finite values before conversion or formatting.
Require the policy's necessary observations for a lower-risk verdict and preserve known adverse evidence.
Use placeholders for missing measurements.

**Required check:** Assert the actual rendered verdict and individual measurement cells for null, missing, empty-string, boolean, negative, and valid-zero inputs.
The existing test at `web/test/dashboard-runtime.test.js:885` tests nulls directly against `classifySafety`, bypassing the renderer's coercion.
Its wave-period assertion searches the entire card for a placeholder, so an unrelated missing field lets the test pass even when the period is displayed as zero.

### R2 - P1: Provenance changes make backend SOS rows inaccessible through Alerts

**Locations:** `web/js/dashboard/dashboard-live-sos.js:118-138`; `web/js/dashboard/dashboard-vessels-alerts.js:172-225`.
**Status:** Regression introduced while addressing original F08.

`isLive` now means `is_synthetic === false`, but the alert-row handler still uses `isLive` to decide whether it can open a backend incident drawer.
Backend synthetic rows therefore lose this interaction despite retaining a real `sosEventId`.
An older or incomplete server response without `is_synthetic` is also titled as a simulated distress call instead of showing unknown provenance.
Those rows also fall into the confidence renderer and can show `null% conf`.

**Reproduction:** Build a backend event with an ID and no GPS fix, then activate its alert row.
With `is_synthetic: false`, the drawer opens.
With `is_synthetic: true` or the field missing, it does not.
Without coordinates there is no map-marker route to the drawer either, preventing acknowledgment and resolution through this view.

**Smallest fix:** Base backend incident actions on the record ID and drawer data.
Represent provenance separately as real, synthetic, or unknown.
Suppress model-confidence presentation for human-triggered SOS records regardless of provenance.
Keep synthetic backend records on the real acknowledge/resolve API path, as plan Task 3.7 requires.

**Required check:** Click and keyboard-activate real, synthetic, and unknown-provenance rows without GPS, then verify the correct incident ID reaches the existing action workflow.

### R3 - P2: Cleanup deleted exports that active modules still consume

**Locations:** `web/js/dashboard/dashboard-emergency-advisory.js:394`; `web/js/dashboard/dashboard-tools.js:398-399`; `web/js/dashboard/dashboard-shortcuts-weather.js:37-49,75-78`.
**Status:** New regression from the final cleanup; original F12/F14 cannot be closed.

The emergency/advisory module no longer exports `renderAdvisoryList`, dialog overlays, or their close functions.
The Buoy sync function and export were also removed, while the panel opener still calls it.

**Browser reproduction:** Open the local dashboard and click ADVISORIES, then BUOYS.
The browser records `TypeError: ns.renderAdvisoryList is not a function` and `TypeError: ns.updateBuoySync is not a function` from `openPanel`.
Panels can become visible before the exception, but advisory refresh and the remainder of panel-opening logic are interrupted.
Open Emergency Contacts and press Escape: its overlay remains `active`, while the shortcut handler can close the underlying panel instead.

**Smallest fix:** Restore exports with real cross-module consumers.
Remove the obsolete Buoy sync call if its new static sample label replaces the old behavior.
Check consumers before deleting any further namespace members.

**Required check:** Load the actual script order, open every panel, and exercise Escape on Emergency, Advisory, Delete, and Acknowledge dialogs.
Assert both the visible result and absence of application exceptions.
The current isolated-module tests cannot verify that the assembled namespace supplies these dependencies.

### R4 - P2: Independent safety feeds still do not age into stale/unavailable states

**Locations:** `web/js/dashboard/dashboard-trip-checks.js:28-45`; `web/js/dashboard/dashboard-ai-ops.js:924-934`; `web/js/dashboard/dashboard-shortcuts-weather.js:234` and `fetchWeatherData`.
**Status:** Original F09 and plan Task 3.3 remain incomplete.

Trip checks distinguish failure before the first successful load, but subsequent failures only log a warning.
Risk and squall polling likewise retain the previous display without adding a failure state or advancing its visible age.
Keeping known warnings is correct; keeping their apparent freshness is not.
The SOS header can remain LIVE while these independent feeds are unavailable.

The weather renderer trusts the caller's `stale` flag instead of checking observation age.
A successful response containing a January observation still renders `LIVE MODEL` and lower risk in September.
The cache contains `fetchedAt`, but there is no implemented per-feed expiry policy matching the checked-off task.

**Smallest fix:** Record each feed's last accepted success and validate source observation age where relevant.
Reuse the existing freshness helper with documented feed-specific thresholds.
Retain last-known warnings while labeling their age and failure state; expired calm data must not read as current lower-risk guidance.

**Required check:** Keep SOS polling healthy, fail each other feed after a successful load, and advance time past its freshness threshold.
Verify only the affected feed changes state, including initially empty feeds and old-but-successful weather responses.

### R5 - P2: Failed audit searches leave displayed results and exports inconsistent

**Location:** `web/js/dashboard/dashboard-operations-audit.js:179-183,207-210`.
**Status:** Original F13 is only partially addressed.

`renderAuditPanel` changes `appliedAuditFilters` before the new request succeeds, but does not clear or relabel the existing rendered results.
If the new request fails, the prior results and applied-filter label remain while Export uses the new filters.

**Reproduction:** Search `a@example.com` successfully, submit `b@example.com` with a failed request, then click Export.
The actual module retains row A and `Applied filters ... actor: a@example.com`, but requests `/api/ops/audit/export?actor_email=b%40example.com&format=csv`.
The same mismatch exists while the second request is still pending.

**Smallest fix:** Keep requested filters separate from the accepted result snapshot and promote filters with the successful response.
Alternatively, clear the old result view and disable export until the new view is accepted.
Retain the existing response-order guard.

**Required check:** Successful A, pending B, failed B, and successful B must each leave the visible labels, rows, pagination, and export on one consistent snapshot.

## Completion records need correction

`docs/audits/WEB_AUDIT_2026-09-13.md:310` says every finding is remediated, despite R1-R5 above.
Its closure table also relabels F11 as secondary UI wiring, although the original F11 is login/password handling.
`docs/archive/plans/WEB_REMEDIATION_IMPLEMENTATION_PLAN.md:3` still says no implementation started, while every phase and acceptance gate is checked off.
Its Phase 3 and Phase 5 ledger hashes refer to different existing commits from the ones on the reviewed HEAD history; update them to the actual reviewed checkpoints.

The plan checks off the full backend suite and full-repository Ruff gate, but the status entry records only 24 selected backend tests and lint on three files.
That subset does not establish the full gates.
This audit could not rerun those gates with the available Python environment and does not infer that Gemini never ran them.
Record the exact commands and results, and leave unsupported gates pending.

Reopen F02, F08, F09, F12, F13, and F14 with the evidence above.
F07 has targeted ordering/target-capture improvements, but full authenticated persistence and delayed-network acceptance remain outside this re-audit's verified scope.

## Improvements worth keeping

- Shared escaping at the originally identified HTML sinks and disabled unsupported broadcast/check-in actions.
- The standalone advisory redirect, honest profile controls, and preserved login password bytes.
- SOS response-order guards, malformed-envelope rejection, drawer retirement, and captured acknowledgment targets.
- Corrected squall/drift layer wiring, overdue-vessel sorting, and removal of the duplicate map export handler.
- Removal of the legacy profile files and unused fullscreen add-on; the repaired coordinate scan targets the current module directory.
- The existing Node runner and useful behavior tests; add the missing scenarios without introducing a new framework.

## Recommended fix order

1. Correct raw weather validation and decouple backend SOS actions from provenance badges: R1 and R2.
2. Repair consumed exports and cover assembled panel/dialog behavior: R3.
3. Finish per-feed freshness and accepted audit snapshots: R4 and R5.
4. Run the focused regressions, the full available backend gates, and an authenticated browser flow with persistence checks.
5. Correct completion records from that evidence, then make the optional simplifications below.

## Ponytail audit: optional complexity cuts

Estimates below exclude required correctness fixes and the tests needed to verify them.
Do not remove the actual internal state, required cross-module exports, or useful behavioral tests.

1. `delete:` Remove approximately 20 lines of unused counter getters and externally writable test-only state exposure; drive tests through poll, drawer, and rendered-state behavior. [`dashboard-live-sos.js:279`](../../web/js/dashboard/dashboard-live-sos.js), [`dashboard-incidents.js:502`](../../web/js/dashboard/dashboard-incidents.js), [`dashboard-operations-audit.js:248`](../../web/js/dashboard/dashboard-operations-audit.js).
2. `shrink:` Remove approximately 15 lines of duplicate escaping and confidence fallback implementations; bind the helpers already supplied by the loaded core/vessels modules. [`dashboard-tools.js:6`](../../web/js/dashboard/dashboard-tools.js), [`dashboard-ai-ops.js:8`](../../web/js/dashboard/dashboard-ai-ops.js), [`dashboard-incidents.js:16`](../../web/js/dashboard/dashboard-incidents.js).
3. `native:` Remove approximately 13 lines of retained haversine fallback; the distance tool already has a Leaflet map, so use `map.distance(a, b) / 1000` and provide that operation in its test stub. [`dashboard-tools.js:139`](../../web/js/dashboard/dashboard-tools.js).

net: -48 lines, -0 deps possible.
