# 08 — DEMO, CONTINGENCY & STATUS

> **This file contains historical entries** from the original Day 1–3
> hackathon push. Do not rewrite those entries as if they were current evidence.
> The current transport decision and current demo path are recorded in the
> newest entry below and in [`55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`](55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md).

## 2026-09-17 — Hybrid transport architecture decision

The primary field node is now a **shared strap-on boat safety pod**: local WiFi
to the phone, physical SOS button, flash-backed queue, GPS, and LoRa direct to a
tall shoreline gateway. Stationary navigational buoys remain in scope for fixed
barometer/current observations and optional LoRa relay coverage, not as the
default way to surround every boat with WiFi.

This is an architecture decision, not a claim of field validation. The next
hardware gates are: prove two Heltecs exchange a direct pod-to-shore packet,
test pod enclosure/strap and antenna placement, verify a pod power cycle does
not lose a queued SOS, then add one stationary relay buoy only if the direct
range test exposes a gap. Record measured distances and packet outcomes here.

## 2026-09-16 — AI Safety Remediation Phase 5: Field Readiness, Measurement Protocols & Collection Handoff

Recorded per `docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md` and `docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md`.
Environment: Windows 11, Python 3.11.9, pytest-9.1.1, Node.js v22.22.3, Ruff 0.15.5.

**Field Readiness, Measurement Protocols & Collection Handoff (Tasks 5.1–5.9, F1–F8):**
- **Instrument Inventory (Task 5.1):** Separated software-verified codebase assets (manifest validator, causal trip profiler, shoreline-bounded particle drift simulator, gated squall detector) from proposed physical assets (anchored marine buoys, seabed ADCP, directional wave buoy, shore tower ultrasonic anemometer) that remain pending in-water deployment.
- **Operating Domain & Independent Events (Task 5.2):** Formally defined the New Washington and Batan Bay geographic domain ($11.60^\circ\text{--}11.75^\circ\text{N}$, $122.40^\circ\text{--}122.55^\circ\text{E}$), artisanal vessel classes (Class A non-motorized, Class B motorized pumpboat), and independent event adjudication standards.
- **Pre-Registered Acceptance Protocols (F1–F8):** Established frozen decision rules, baselines, and denominators for collocated sensor commissioning (F1), handset WiFi contact logging (F2), prospective weather onset (F3), delayed return drills (F4), drifter containment (F5), blinded search trials (F6), integrated before/during/after storyline (F7), and frozen model evaluation (F8).
- **Delivered Lead Accounting Standard (Task 5.8):** Formulated delivered lead as $T_{\text{hazard\_onset}} - T_{\text{handset\_display}}$; unreceived or undelivered alerts are strictly accounted as missed lead in denominators, never excluded from statistics.
- **Canonical Manifest Fixture (Tasks 5.5, 5.9):** Created and verified [`manifests/field_eval_manifest_v1.json`](../manifests/field_eval_manifest_v1.json) with SHA-256 evidence checksums, disjoint event splits, and diverse evaluation outcomes, verified by `test_canonical_field_eval_manifest_validates_cleanly`.
- **Concrete Blockers & Handoff:** Documented prerequisites (LGU/Coast Guard permits, mooring installation, surrogate target construction, safety escort vessels) and defined collection handoff for hardware (Daniel), gateway (Arnold), and backend (Lenard).
- **Honest Status:** In accordance with Phase 5 rules, Phase 5 remains **Preparation & Protocol Complete; Physical In-Water Collection Pending Handoff**. Software gates pass completely; physical in-water claims remain unmeasured until real maritime collection is executed.

**Verification Results:**
- Backend: **362 passed, 5 skipped, 1 xfailed** (`python -m pytest -q`); Ruff check clean (`All checks passed!`).
- Manifest & Replay suite (`tests/test_calibration_and_replay.py`): **9/9 passed**.
- Web: **141 passed, 0 failed** (`node --test web/test/*.test.js`).

## 2026-09-15 — AI Safety Remediation Phase 4: Calibration Lineage, Historical Replay & Claim Boundaries

Recorded per `docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md`.
Environment: Windows 11, Python 3.11.9, pytest-9.1.1, Node.js v22.22.3, Ruff 0.15.5.

**Calibration Lineage, Historical Replay & Behavioral Scenarios (C1–C8):**
- **C1 (Gated Squall Promotion):** `build_squall_status` checks model calibration; unvalidated or synthetic calibration bundles (`calibration == 'synthetic'`) are strictly capped at `watch` with explicit reason (`unvalidated_synthetic_calibration`), preventing automated promotion to operational `return_now` during live operations.
- **C2 (Composed Decision & Distinct Probabilities):** Squall detector exposes `classifier_probability` and `pattern_score` as separate fields rather than conflating them into a single score; threshold selection and offline evaluation scripts evaluate the composed decision rule `max(p, rule_score)`.
- **C3 & C4 (Event-Level Dataset Manifest Validation):** Implemented `validate_manifest` (`app/ai/manifest.py`) enforcing disjoint event partitions across development/test splits (preventing leaking time windows from the same storm), rejecting empty datasets, placeholder SHA-256 hashes, and single-class target sets.
- **C5 (Overdue Open Trips Under Outage):** Open vessel trips with zero buoy contacts during gateway outages remain fully visible and reviewable as overdue when `expected_return_at < as_of`, preserving expected return obligations with `low_confidence = True`.
- **C6 (Robust Trip Loading & Historical Baselines):** Removed silent error swallowing in `_load_trip_states`; historical normal baselines filter strictly for completed, normal trips (`status == 'completed'`), preventing unfinished or abnormal trips from contaminating normal vessel duration profiles.
- **C7 (Database & Manual SOS Survival Under Model Outage):** Model crashes or numerical explosions in particle integration during drift case creation leave underlying incident records and manual SOS intake (`POST /api/sos`) 100% operational.
- **C8 (Controlled Drift Evaluation with Supported Horizons):** Implemented `evaluate_drift_track` (`app/ai/drift_eval.py`) computing exact polygon containment, area, reduction factor, and miss distance; horizons exceeding the model's supported horizon are reported as unsupported (`is_supported = False`) and not counted as containment successes.

**Verification Results:**
- Backend: **361 passed, 5 skipped, 1 xfailed** (`python -m pytest -q`); Ruff check clean (`All checks passed!`).
- Dedicated calibration and replay suite (`tests/test_calibration_and_replay.py`): **8/8 passed**.
- Web: **141 passed, 0 failed** (`node --test web/test/*.test.js`).

## 2026-09-15 — AI Safety Remediation Phase 1: Offline Warning Delivery & Verification

Recorded per `docs/AI_SAFETY_REMEDIATION_IMPLEMENTATION_PLAN_GEMINI_3_8.md`.
Environment: Windows 11, Python 3.11.9, pytest-9.1.1, Flutter 3.44.7, Node.js v22.22.3.

**Offline Warning Delivery & Mesh Codec Verification (W1–W10):**
- **W1 (Offline Warning Feed):** Mobile `VentureFeeds.advisories()` connected to `BuoyClient.warnings()` so handset in airplane mode fetches and renders active advisories over buoy WiFi SoftAP when backend cellular HTTP is unreachable.
- **W2 (Calendar & Expiry Policy):** Publication dates and active queries adhere strictly to Philippine Standard Time (PHT, UTC+8); advisories missing explicit expiration dates are bounded by 48-hour retention from publication rather than remaining silently immortal.
- **W3 (LoAM Codec & HMAC Tamper Rejection):** Implemented reference Python LoAM binary frame codec and verified round-trip serialization; HMAC-SHA256 neutralizes relay-mutable bytes (`RELAY_ID` at offsets 8..11, and `TTL`/`HOPS` at offsets 18..19); tampered bytes, invalid HMAC keys, or excessive hops (> 15) are strictly dropped.
- **W4 (Bounded Retries & Backoff):** Gateway rebroadcast retry queue enforces exponential backoff (30s, 60s, 120s) and terminates at 3 maximum attempts, preventing permanent channel saturation.
- **W5 (Revision Superseding & Cancellation Tombstones):** Warning cache enforces 6 maximum slots, expiration pruning, and revision ordering; cancelled warnings store tombstones that prevent resurrected display by older delayed frames.
- **W6 (Delivery State Deduplication):** `POST /api/advisories/delivery` enforces deduplication on `(warning_id, delivery_state, vessel_id, buoy_id)` returning `deduped: true` on replay, and requires `vessel_id` for `user_acknowledged`.
- **W7 (SOS Radio Priority):** Emergency distress SOS packets (`0x01`) take absolute priority over warning frames (`0x07`); warning rebroadcasts yield immediately when SOS traffic arrives.
- **W8 (Disconnected Handset Honesty):** Handset preserves last-known status while out of range; cache age remains honest without claiming false delivery while offline.
- **W9 (Explicit Downlink & Attribution):** Research alerts retain explicit `sig_type: "research"` and uncalibrated status, preventing automated return commands or confusion with official human-authored LGU directives.
- **W10 (Strict Parser Validation):** Mobile `Advisory.parseList` rejects malformed strings with `FormatException` rather than silently presenting a clear list; honors exact second-precision expiration for instants and 23:59:59 PHT for date-only calendar days.

**Verification Results:**
- Backend: 338 passed, 5 skipped, 1 xfailed (`python -m pytest -q`); Ruff check clean.
- Mobile: 256 passed, 0 failed (`flutter test`); `flutter analyze` clean (0 issues).
- Web: 141 passed, 0 failed (`node --test web/test/*.test.js`).

## 2026-09-15 — AI Layer Calibration, Physical Drift Boundaries & Prospective Verification (Phases 1–5)

Recorded per `docs/AI_ACCURACY_IMPLEMENTATION_PLAN.md` and `docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`.
Environment: Windows 11, Python 3.11.9, pytest-9.1.1, Flutter 3.44.7, Node.js v22.22.3.

**Remediation, Physical Calibration, and Prospective Validation:**
- **Phase 1 (Counterexamples & Semantic Isolation):** Eliminated fabricated data baselines; isolated synthetic demo inputs from live production pipelines (`allow_synthetic=False`); aligned timezones to Asia/Manila calendar day boundaries; separated unique vessel contributors from report counts in catch aggregation.
- **Phase 2 (Sensor Qualification & Warning Transport):** Enforced array telemetry quality gates (`ArrayQuality`, min 3 buoys, 5-min cadence); surfaced source grid resolution ($0.1^\circ \approx 11\text{ km}$) and data age in provenance headers; validated non-negative physical readings; preserved manual SOS integrity regardless of warning traffic.
- **Phase 3 (Nowcasting & Causal Trip Profiling):** Repaired squall front propagation invariants (shifting origin coordinates preserves absolute arrival time); eliminated future/candidate leakage in trip profiling ($T \le T_{\text{decision}}$); retained open trips beyond 12 hours for human dispatcher review; preserved human authority over SAR escalation.
- **Phase 4 (Physical Drift & Time-Aligned Search Evidence):** Separated physical datum ($T_{\text{fix}}$) from server ingest time; integrated high-resolution shoreline boundary polygon with particle grounding/stranding preventing mountain crossings; bounded search retasking by independent physical maximum-speed envelope ($A = \pi (V_{\max} \cdot t)^2$); applied time-aligned $(1 - p_d)$ search likelihood to particle trajectories at the time of search; labeled retasking as strictly advisory.
- **Phase 5 (Prospective Shadow Drills & Operational Claims):** Established prospective shadow observation protocol with zero future leakage; designed complete-storyline drills covering nominal and degraded branches (comms loss, delayed safe return, drift simulation fallback); evaluated delivered lead against the 20-minute small-craft safe transit threshold; published comprehensive component capability matrix and full resolution disposition for all 23 audit findings (`docs/45_AI_PROSPECTIVE_EVALUATION_AND_CLAIMS.md`).

**Build and Verification Evidence:**
- **Automated Verification Gate:**
  - `python -m pytest -q` (full backend suite): **334 passed, 5 skipped, 1 xfailed** (including all Phase 1–5 validation suites: `test_phase1_counterexamples.py`, `test_phase2_validation.py`, `test_phase3_validation.py`, `test_phase4_validation.py`, `test_phase5_validation.py`).
  - `python -m ruff check backend/`: **Clean, 0 errors**.
  - `flutter test` (mobile suite): **250 passed, 0 failed**.
  - `flutter analyze` (mobile analysis): **Clean, 0 issues**.
  - `node --test web/test/*.test.js`: **141 passed, 0 failed**.
  - `node --check web/js/dashboard/dashboard-sar.js`: **Clean, exit code 0**.
  - `git diff --check`: **Clean, 0 whitespace issues**.
- **Direct Observations & Honest Caveats:**
  - **Manual SOS Independence:** Distress call signaling, buoy relay, and responder acknowledgment operate completely autonomously from all AI services. An AI service crash does not impede emergency dispatch.
  - **Field Collection & Outdoor LoRa Range:** Physical buoy deployments and open-water radio range measurements in New Washington remain to be executed outdoors; local verification proves software correctness, numerical stability, physical boundary constraints, and protocol alignment.

## 2026-09-14 — Operations Console Audit Remediation: Complete Implementation & Verification

Recorded per `docs/archive/plans/WEB_REMEDIATION_IMPLEMENTATION_PLAN.md` and `docs/audits/WEB_AUDIT_2026-09-13.md`.
Environment: Windows 11, Node.js (native test runner), Python 3.11.9, pytest-9.1.1.

**Remediation and Corrective Changes:**
- **Phase 1 (Security & Honest Actions):** Sanitized DOM injection sinks in incident feeds, pin popups, sea condition, and AI cards via `escapeHtml`; removed misleading broadcast/check-in success messages; redirected standalone advisory to the integrated dashboard workflow; isolated authenticated operator profiles without cross-account cache leaks.
- **Phase 2 (Module Wiring & Session State):** Fixed confidence score ReferenceError in `openIncidentDrawer`; mapped squall/drift layer toggles to rendered AI groups; unified single map export handler; sorted overdue vessels (priority 0) ahead of normal vessels; sanitized password whitespace and cleared demo bypass state on valid login.
- **Phase 3 (Data Freshness, Validation, & Demo Provenance):** Demoted stale/missing weather data and validated non-negative physical readings; isolated danger-zone overrides to the current session; badged synthetic demo rows distinctly from live SOS records; displayed honest offline/stale indicators when services are unreachable.
- **Phase 4 (Asynchronous Ordering & Keyboard Stabilization):** Added request generation counters (`activeSosReqSeq`, `lastAcceptedSosSeq`) to enforce poll response ordering; retired SOS drawers when incidents leave authoritative active feeds; locked acknowledgment modal targets to prevent background case swapping; suppressed single-key shortcuts while typing in editable elements; enforced Escape key hierarchy; snapshotted audit search filters for pagination and export consistency.
- **Phase 5 (Dead Code Removal & Geographic Test Gate):** Removed unused `web/js/jss.js` (171 lines), `web/css/profile.css` (673 lines), and vendored Leaflet fullscreen add-on (192 lines + 2 HTML tags + 2 image assets); trimmed dead assignment-only namespace exports; repaired `backend/tests/test_dashboard_coords.py` to scan all `web/js/dashboard/*.js` files (26/26 coordinates verified within water polygon or shore stations); documented web verification and browser smoke workflows in `README.md`.

**Build and Verification Evidence:**
- **Automated Verification Gate:**
  - `node --test web/test/*.test.js`: **114/114 tests passed** (including helper tests and all runtime regression tests for Phases 1–5).
  - JavaScript syntax checks across all `web/js/` and `web/test/` files: **Clean (exit code 0)**.
  - Python tests: `python -m pytest backend/tests/test_dashboard_coords.py backend/tests/test_sos_ingest.py backend/tests/test_responder_loop.py` — **24 passed, 0 failed**.
  - Python lint: `python -m ruff check backend/tests/test_dashboard_coords.py backend/app/api/sos.py backend/tests/test_sos_ingest.py` — **Clean, 0 errors**.
  - `git diff --check`: **Clean, 0 whitespace issues**.
- **Browser & UI Acceptance Flow:**
  - **Auth & Session:** Verified login, session clear on logout, and profile page rendering authenticated credentials.
  - **Live Incident Handling:** Verified SOS drawer open, target lock during acknowledgment modal, focus containment and return, and automatic drawer retirement upon resolution.
  - **Audit Logging:** Verified search query snapshotting ensures pagination and CSV/JSON export adhere strictly to submitted filters rather than active form input state.
  - **Accessibility:** Verified single-letter hotkeys are ignored when typing in inputs; verified Escape key dismisses modals first, drawers second, panels third.
- **Direct Observations & Honest Caveats:**
  - **Hardware / Handset Verification:** Physical buoy hardware and field handset verification remain separate critical-path work. Local web verification confirms dashboard software correctness, security, and protocol contract alignment, but does not substitute for outdoor LoRa range tests.
  - **Deployment Limit:** Hosted Railway deployment remains inactive; all tests were verified in local developer runtime environments.

## 2026-09-13 — Phase 4: Localized Fishing Weather Window & Audit Corrections Verification

Recorded per `IMPLEMENTATION_PLAN.md` and `docs/audits/GEMINI_FISHING_WINDOW_AUDIT.md`.
Environment: Windows 11, Flutter 3.44.7 (channel stable), Python 3.11.9.

**Audit Resolution and Corrective Changes:**
- **Finding 1 (Precedence):** Restrictive warnings evaluate independently of forecast availability; danger warnings return immediately as high risk; caution warnings set a minimum floor of caution without downgrading higher forecast danger. `WeatherCard` evaluates the window whenever a forecast or active warning is present.
- **Finding 2 (Wave Semantics):** Instantaneous wave heights at `now` (and nearest past/covering interval) are evaluated for current risk. Future wave threshold onset is `h.time` (instantaneous), while atmospheric onset is `intervalStart` (`h.time - 1h`).
- **Finding 3 (Daily Rain):** Removed fabricated midnight countdowns from future daily rain totals; exposes date-level advisory (`firstAdverseDay = day.date`, `availability = missingHourly`) without positive duration.
- **Finding 4 (Validation & Completeness):** Input validation via `_nonnegativeDouble` rejects negative speeds and heights across `ForecastOutlook`, `DailyOutlook`, cache, and fallback parsers. `_assessHour` requires gust completeness for green certification (no replacement with mean wind).
- **Finding 5 (Duplicate Timestamps):** Implemented conservative duplicate timestamp merging (most severe weather code, maximum numeric hazards) across backend, fallback, cache, and calculator.
- **Finding 6 (Location Consistency):** Mobile fallback wave queries match requested coordinates (`$lat`, `$lon`); forecast location coordinates are displayed in the UI footer (`_footerProvenance`).
- **Finding 7 (Timezone Metadata):** Offset-free timestamps are converted to UTC using declared `utcOffsetSeconds` (`parseForecastTime`); replaced wall-clock `day.isToday` with injected `now`.
- **Finding 8 (Upcoming Risk Tier):** Rendered upcoming risk icon, color, and localized label (`result.upcomingRisk!.label(t)`) in `WeatherCard`'s subtitle alongside onset.
- **Ponytail Complexity Reductions:** Deleted dead `CommunitySpot`/`spots()`, removed unused daily provider adapters, dropped duplicate provenance fields from `FishingWindowResult` (reads from `ForecastOutlook`), and simplified `ForecastCache` to v2 single-record persistence (-255 lines net).

**Build and Verification Evidence:**
- **Automated Verification Gate:**
  - `flutter gen-l10n`: Succeeded cleanly; generated `mobile/lib/l10n/app_localizations*.dart` with ICU plural rules and localizations for English, Tagalog (`fil`), and Aklanon (`akl`).
  - `flutter analyze`: 0 issues found across all mobile files.
  - `flutter test`: 235/235 tests passed (including all 18 unit/widget tests in `mobile/test/weather_card_test.dart` and 24 tests in `mobile/test/fishing_window_test.dart`).
  - `flutter test --dart-define=PITCH_MODE=true test/pitch_mode_test.dart`: 3/3 passed (verifying manual SOS button present, catch/hotspot/squall controls absent, and clean rendering across 360x640 and 390x844 viewports without RenderFlex overflow).
  - `flutter build web`: Succeeded cleanly (`Built build\web` in 45.4s).
  - Backend tests: `cd backend && python -m pytest -q tests/test_public_forecast.py && python -m ruff check app/api/public.py tests/test_public_forecast.py` — 13 passed in 3.03s, 0 ruff errors.
- **UI & Layout Verification:**
  - `_FishingWindowSummary` tested in narrow 360x640 layout with 1.5x large text scaling and dark theme without any RenderFlex overflow (header text in `Expanded`, badge container in `Flexible` with `TextOverflow.ellipsis`, upcoming risk tier in subtitle `Row` with `Expanded`).
  - Evaluated under both light and dark themes; caution/warning states use high-contrast dark text on amber badges (`#000000` text on `#FDE68A`) to satisfy WCAG AA readability.
  - Verified localization fallback: Tagalog and Aklanon build cleanly falling back to reviewed English strings where translations are not yet reviewed by native speakers per `mobile/lib/l10n/README.md`.
  - HomePage lifecycle and foreground 1-minute timer re-renders window countdowns without firing unneeded network calls.
- **Direct Observations & Honest Caveats:**
  - **Hardware / Handset Status:** Physical buoy hardware and field handset tests remain to be scheduled outdoors; this verification is conducted in local automated test, widget harness, and web compilation environments.
  - **No Live Overwrite:** Did not run destructive or live weather override; all automated tests run against deterministic synthetic fixtures.

## 2026-09-05 — Phase 1 Pitch Mode Mobile Build & Verification

Recorded per `docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md` Phase 4.
Environment: Windows 11, Flutter 3.44.7 (channel stable), Android SDK 37.0.0.

**Build and Verification Evidence:**
- **Build Mode:** Opt-in pitch build compiled with `--dart-define=PITCH_MODE=true` and `--dart-define=BACKEND_BASE_URL=https://aihackathon2026aquanonsaqone-production.up.railway.app`.
- **Release APK:** `mobile/build/app/outputs/flutter-apk/app-release.apk`
  - SHA-256: `7A5F5B0F0DEA4BF17D0BB02D145C0B2CD9546D85D35F9CEDB10EBFA9C93EC771`
  - Size: 65,351,651 bytes (62.3 MB)
  - Built at: 2026-09-05 10:31:50 UTC+8
  - Git Commit: `8410cb4` (checkpoint `test(mobile): verify pitch SOS flow`)
- **Automated Verification Gate:**
  - `flutter analyze`: 0 issues found across all mobile files.
  - `flutter test`: 184/184 tests passed.
  - `flutter test --dart-define=PITCH_MODE=true test/pitch_mode_test.dart`: 3/3 passed (verifying manual SOS button present, catch/hotspot/squall controls absent, and clean rendering across 360x640 and 390x844 viewports without RenderFlex overflow).
  - Normal test run confirms deferred features (catch logging, catch history, hotspot circles, squall watch) remain fully functional when `PITCH_MODE=false`.
- **Direct Observations & Honest Caveats:**
  - **Backend Deployment:** Public Railway URL (`https://aihackathon2026aquanonsaqone-production.up.railway.app/healthz`) returned HTTP 404 (`{"status":"error","code":404,"message":"Application not found"}`). The remote deployment is currently inactive or deleted on Railway. Direct-to-cloud SOS transport cannot reach the backend until the service is redeployed.
  - **Hardware / Handset Status:** No physical handset or buoy hardware connected during this local build session. End-to-end rehearsal on live buoy Wi-Fi / LoRa and physical handset install remains to be conducted on the bench setup.
  - **APK Preservation:** Existing `mobile/AqOne.apk` preserved intact; newly built release APK is located at `mobile/build/app/outputs/flutter-apk/app-release.apk`.

## 2026-08-31 — operations console auditability Phase 5: local proof passed, policy and deployment blocked

Recorded per
`docs/41_OPERATIONS_CONSOLE_AUDITABILITY_IMPLEMENTATION_PLAN.md` Phase 5.
Environment: Windows 11 sandbox, Python 3.11.9, Node v22.22.3, an isolated
disposable PostgreSQL 18 cluster on localhost, and a local FastAPI/dashboard
instance. No existing local or production database was used. All 26 migration
files through `023_sos_resolution_detail.sql` applied to the disposable
`aqone_verify` database.

**Observed against the real local PostgreSQL database and HTTP routes:**

- Admin, MDRRMO, and LGU test accounts were created through the controlled
  setup route and logged in successfully. An unauthenticated active-SOS read
  returned `401`; MDRRMO attempts to issue a vessel pairing code or export the
  global audit log returned `403`.
- A direct test SOS was acknowledged with a server-derived absolute ETA,
  remained in the active feed while acknowledged, and left it only after
  resolution. Its case timeline contained `sos.acknowledge`, one aggregated
  `ops.case_view`, and `sos.resolve`. Three timeline reads inside the current
  15-minute application window produced one view record.
- Timeline output omitted actor IDs, resource IDs, the SOS note, responder
  note, and resolution reason. The database trigger rejected direct `UPDATE`
  and `DELETE` attempts against `operations_audit_events`.
- A sea-condition declaration, advisory creation, vessel pairing-code issue,
  and vessel-device revocation all produced the expected redacted audit
  actions. Admin search returned every expected action. A bounded JSON export
  returned 14 rows with the displayed filters, was not truncated, and carried
  the expected attachment header; export contents and credentials were not
  written to the repository or screenshots.
- Browser acceptance found and fixed a shared-state bug in
  `web/js/dashboard/dashboard-live-sos.js` that had left the console OFFLINE
  with `liveAlerts is not defined` even while `/api/sos/active` was healthy.
  After the minimal fix, a fresh-browser run showed LIVE freshness, rendered a
  new real SOS ahead of DEMO rows, acknowledged it with ETA/note, displayed its
  redacted case activity, resolved it, and returned the active count to zero.
  The admin Audit panel rendered the same action records, filtered to
  `sos.resolve`, and its JSON export control reached the backend export route.

**Automated gate:**

- `cd backend && python -m pytest -q --tb=short` — 291 passed, 5 skipped,
  1 xfailed, and 1 pre-existing failure:
  `tests/test_demo.py::test_firing_same_beat_is_idempotent` raises
  `ValueError: clear-day has baseline beat 0 only` in the untouched demo
  scenario code.
- `cd backend && python -m ruff check .` — the same 8 pre-existing findings in
  `app/demo/scenarios.py` and `calibrate_demo_squall.py`; none is in the
  operations-audit implementation or the Phase 5 live-feed fix.
- `cd web && node --check js/dashboard/dashboard-live-sos.js && node --test
  test/dashboard-utils.test.js` — syntax check passed; 77/77 tests passed.

**Open owner-policy blocker — no retention/deletion job was added:** there is
still no owner-approved audit retention period, backup/export handling rule,
named database administrator list, or approved case-view aggregation window.
The application currently aggregates repeated case views for 15 minutes, but
that value is implementation behavior, not an approved operating policy.
Automatic deletion must remain absent until the owner records those decisions.

**Deployment blocker:** a read-only request to the documented Railway
`/healthz` endpoint returned Railway's `404 Application not found` response on
31 August 2026. The local branch's role behavior and audit routes therefore
were not verified or deployed on Railway.

This is an application audit ledger, not an external immutable evidence store.
The append-only trigger blocks ordinary application writes, but a database
administrator can disable it; external archival, backup restore tests, legal
evidence handling, and retention enforcement remain unimplemented. Phase 5 is
not marked complete until the owner-policy decisions exist, Railway behavior is
verified, and the repository-wide backend test/lint gate is green.

## 2026-08-29 — manual SOS / responder-loop verification

Recorded per `docs/36_MANUAL_SOS_RESPONDER_LOOP_IMPLEMENTATION_PLAN.md` Phase
5, in the spirit of this file's own status table rather than as a rewrite of
it. Environment: Windows 11 sandbox, Python 3.11.9, Flutter 3.44.7, Node
v22.22.3, no attached Android/iOS device.

**Automated release gate — all green except pre-existing, unrelated failures
already present at Phase 0 baseline:**

- `cd backend && python -m pytest -q && ruff check .` — 108 passed, 1 xfailed.
  `test_demo.py::test_firing_same_beat_is_idempotent` and two
  `test_dashboard_coords.py` errors (missing `web/js/dashboard.js`, a stale
  path from before it moved under `web/js/dashboard/`) are pre-existing and
  unrelated to the SOS/responder-loop work; `ruff check .` has 8 pre-existing
  issues confined to `calibrate_demo_squall.py`, also unrelated.
- `cd mobile && flutter analyze && flutter test` — 0 analyzer issues, 151/151
  tests passed, including the new `sos_service_test.dart` and
  `responder_eta_dialog_test.dart`.
- `cd web && node --test test/dashboard-utils.test.js` — 32/32 passed,
  including the new `formatEta`/`responderStatusHtml` cases.
- `flutter build web` — succeeded cleanly (`Built build\web`), proving the
  handset app actually compiles and runs as a live instance, not just under
  `flutter test`'s widget harness.

**Manual, device-level acceptance script (pairing a real handset, pressing
Manual SOS, watching a live dashboard acknowledge and receive a reply) could
not be completed in this environment.** Recording the blockers rather than
skipping this silently, per the Hard Reset convention already used in
`docs/21_WEEK1_CONTRACT_FIXTURES.md`:

- The backend requires a real PostgreSQL database (`asyncpg`). A PostgreSQL 18
  server is installed locally, but its credentials are unknown and do not
  match `backend/.env.example`'s `postgres:postgres` default, so no local
  backend could be started against it.
- Docker Desktop is installed (would have given an isolated, disposable
  Postgres instead of touching the existing server) but its engine did not
  finish starting after roughly ten minutes of waiting, so that path was
  abandoned rather than pursued indefinitely.
- No Android or iOS device or emulator is attached, and Visual Studio (the
  "Desktop development with C++" workload) is not installed, so neither a
  real handset nor a Windows desktop build of the app was available.
  `flutter devices` offers only Windows (blocked on the above) and Edge; only
  Edge, not Chrome, is present.

What this means concretely: the SOS → backend → dispatcher-acknowledge →
fisher-reply loop is proven by the automated suite (including a real,
compiled, running build of the handset app), and its buoy-fallback half is
proven by `mobile/test/buoy_client_test.dart`'s fixture-based parsing of a
real ETA response and its 320-byte firmware truncation — but nobody has yet
watched an actual phone, buoy, and dispatcher screen agree with each other in
real time for this phase. That remains open work for whoever has a real
Postgres credential or a working Docker install in this environment (or is
running this on a machine already set up per `backend/.env.example`).

## 2026-08-29 — short messaging / weather / advisories verification

Recorded per `docs/37_SHORT_MESSAGING_WEATHER_ADVISORIES_IMPLEMENTATION_PLAN.md`
Phase 5, same environment as the responder-loop entry above: Windows 11
sandbox, Python 3.11.9, Flutter (via `C:\Users\User\flutter`), Node, no
attached Android/iOS device, on branch
`codex/short-messaging-weather-advisories`.

**Automated release gate — all green except the same pre-existing, unrelated
failures already present at the Phase 0 baseline of this handoff:**

- `cd backend && python -m pytest -q` — 125 passed, 1 xfailed, 1 pre-existing
  failure (`test_demo.py::test_firing_same_beat_is_idempotent`) and 2
  pre-existing errors (`test_dashboard_coords.py`, still missing
  `web/js/dashboard.js` at its old pre-modularisation path) — identical to
  the Phase 0 baseline, unrelated to this work. `ruff check .` — same 8
  pre-existing issues confined to `calibrate_demo_squall.py`, also
  unrelated and untouched.
- `cd mobile && flutter analyze` — 0 issues. `flutter test` — 180/180
  passed (baseline 151, +29 across the four phases: chat relay/status,
  advisory expiry/field-compat, forecast precedence/fallback, stale squall
  parsing and banner, and the new chat/squall ARB keys in all three
  locales).
- `cd web && node --test test/dashboard-utils.test.js` — 32/32 passed
  (unchanged; this handoff did not touch `web/`).

**What was directly verified, and how:**

- The live Railway base URL. `GET /healthz` against
  `https://aihackathon2026aquanonsaqone-production.up.railway.app` returned
  `200 {"status":"ok"}` before any code changes. The URL `ChatService` and
  `AqOneConfig.backendBaseUrl` previously defaulted to,
  `incredible-liberation-production-aad7.up.railway.app`, answered
  Railway's own `404 Application not found` — that deployment does not
  exist. This was an unannounced regression beyond the plan's own framing
  of the bug (which assumed `AqOneConfig.backendBaseUrl` was already
  correct); both defaults are now the verified live host. No write request
  was made against the live deployment — this was a read-only `/healthz`
  check only, per the plan's Phase 0 instruction.
- Every backend route change (mesh chat ordering/persistence, advisory
  expiry filtering and field naming, `/api/public/forecast`, the squall
  staleness guard) is exercised by `TestClient` against the real FastAPI
  routes and real SQL query text, with only the database connection faked
  (in-memory fake pools modelled on the existing `test_vessel_auth.py`
  pattern) — not mocked at the HTTP boundary. This is real route-level
  verification, not a unit test of isolated functions.
- Local Postgres was checked again for this handoff (same blocker as the
  responder-loop entry above): a server is running on `localhost:5432`, but
  connecting as `postgres:postgres` (the `.env.example` default) fails with
  `InvalidPasswordError`, and no other credential is known in this
  environment. Docker Desktop's engine is still not reachable
  (`npipe:////./pipe/dockerDesktopLinuxEngine`). No password was guessed or
  brute-forced.

**What was not verified, and is not claimed as done:**

- **No live device or staging acceptance script was run.** The manual
  script in the implementation plan (send a chat line and watch a `201`
  land in a real database with internet on/off; join a real Heltec hub over
  WiFi and check history backfill/no self-echo; create a future-dated and
  an expired advisory as a staging operator; watch the backend forecast and
  a fresh vs. stale squall fixture on a running app; switch locales on a
  live screen) needs a real Postgres connection, a Heltec buoy on WiFi, and
  a device/emulator, none of which were available here. Nothing above
  should be read as claiming that script ran.
- **None of this handoff's code changes are deployed.** Everything above
  is on the local branch only, not pushed, not merged, and not built onto
  the Railway deployment checked for `/healthz`. The live backend still
  runs whatever was deployed before this handoff.
- **No chat message, advisory, or squall reading was created against any
  real database** — local, staging, or production — consistent with the
  plan's instruction not to post test data anywhere without the owner's
  explicit approval.
- The Aklanon and Tagalog strings added in Phase 4
  (`chatStatus*`, `chatCharacterLimitLabel`, `squallStale*` in
  `mobile/lib/l10n/app_fil.arb` / `app_akl.arb`) are machine/AI-drafted,
  exactly like every other string in those two files per
  `mobile/lib/l10n/README.md` — untranslated by a human, not reviewed by a
  native speaker, and not verified against a running app in either
  language. `flutter test` confirms they render without a
  `MaterialLocalizations` exception and without a build-time overflow
  exception in all three locales; it does not confirm the words are
  correct.

## 2026-08-29 — automatic distress detection: open-trip freshness window decided

Per `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md` Phase 2 item
2, a stop-and-ask condition: "If the team has not selected a safe cadence,
stop this phase for that decision; guessing it changes emergency behaviour."

**Decision: `OPEN_TRIP_FRESHNESS_WINDOW = 12 hours`**
(`backend/app/ai/anomaly_service.py`). Made by the project lead, not guessed.

How long after a vessel's last buoy contact its most recent trip still counts
as "possibly still open" for scoring, versus excluded as stale/completed.
Rationale considered:

- Too short would exclude a vessel that is *already* hours overdue — the
  exact case this feature exists to catch, since an overdue vessel's defining
  characteristic is a growing gap since its last contact.
- Too long lets a trip from days or weeks ago re-alert just because the wall
  clock advanced — the design flaw `docs/31_DEMO_VERIFICATION_01.md` found in
  the previous dataset-max-timestamp approach, where the whole synthetic
  fleet scored ≈0.85 and alerted because their contacts were days behind the
  demo's freshly-written ones.
- The synthetic generator (`backend/app/simulation/generator.py`) models full
  trips — departure to return — of roughly 6–13 hours (departure ~04:20–06:35,
  fishing 1.8–6.5h, return same day ~16:10–19:15). 12 hours covers a complete
  trip cycle with headroom, while still excluding anything from a prior day.

There is currently no explicit "trip completed" signal other than a new
`trip_id` starting later, so this window is the only mechanism that
distinguishes "still out, buoy just hasn't seen them for a while" from "went
home a long time ago, nothing to worry about." It is a single named constant,
not tuned per vessel or scenario, and Phase 2's own instruction was explicit
that this work must not extend to retuning `trip_profile.py`'s model weights
or thresholds — only this eligibility guard.

## 2026-08-29 — automatic distress detection: offline evaluator fixed, false-alarm figure retracted

Per `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md` Phase 4.

**The bug.** `backend/app/ai/trip_profile_eval.py`'s normal-trip path
previously re-scored each trip only at its own historical contact
timestamps (`as_of = contacts[idx - 1].observed_at`), never past its own
final contact. `status == 'alert'` was therefore checked only at moments
the vessel was, by construction, still actively checking in — the
published **0% false-alarm rate across 496 normal trips was true by
construction, not by measurement** (`docs/30_DEMO_DECISION_01_ANOMALY.md`
§1.1 predicted exactly this).

**The fix.** Normal trips now sweep `as_of` forward from their own last
contact in 5-minute steps over the same 12-hour horizon the incident path
already used (matching `OPEN_TRIP_FRESHNESS_WINDOW`, the Phase 2 decision
above — the live pipeline never scores a trip past that age either, so this
measures exactly the window production can reach). Core logic extracted
into a pure `evaluate(rows, incidents)` function
(`backend/app/ai/trip_profile_eval.py`) so it can be regression-tested
without a database.

**What was verified here, without a database** (`backend/tests/test_trip_profile_eval.py`,
3/3 passing): with a controlled fixture — four historical trips on a fixed
three-buoy route, then a fifth trip that completes the same route and then
legitimately goes quiet — the corrected evaluator reaches `status: 'alert'`
about **two hours** after the vessel's last real contact, purely because no
further contact ever arrives. The pre-fix code could never reach this
outcome for any trip, by construction, regardless of the underlying model.
This reproduces exactly the mechanism `docs/31_DEMO_VERIFICATION_01.md`
found separately (a model with no "trip complete" concept eventually reads
silence as overdue) and confirms the fix actually exercises time the vessel
was never observed at.

**What was not run.** `python -m app.ai.trip_profile_eval` against the real
496-normal-trip synthetic dataset — same blocker recorded throughout this
file: no working local Postgres credential, Docker Desktop's engine
unreachable. The real false-alarm rate is therefore **unmeasured**, not
republished as a guess. `backend/app/ai/models/eval_results.json`'s
`trip_anomaly.false_alarm_rate` has been set to `null` with a
`retracted_reason` field explaining why, and the README's measured-performance
table and status row were updated to match (say "retracted" / "demo,
simulation-verified only" rather than the stale 0%) — per decision 30 §4:
"Publish whatever it gives... The real number may be considerably worse than
0%. That is the point." `median_detection_latency_minutes` (55 minutes) and
`incidents_detected` (8) are unaffected; decision 30 already verified that
sweep. Whoever next has a working local Postgres or a working Docker install
should run `python -m app.simulation.generator --days 14 --seed 42` then
`python -m app.ai.trip_profile_eval` and record the real number here.

## 2026-08-29 — automatic distress detection Phase 5: release gate green, deployment/device verification not performed

Per `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md` Phase 5,
same environment as every entry above: Windows 11 sandbox, Python 3.11.9,
Node, on branch `codex/short-messaging-weather-advisories`, continuing
directly from the Phase 1-4 work recorded above.

**Automated release gate — green, same pre-existing failures as every other
entry in this file:**

- `cd backend && python -m pytest -q` — 164 passed, 1 xfailed,
  1 pre-existing failure (`test_demo.py::test_firing_same_beat_is_idempotent`)
  — identical to every earlier baseline in this file, unrelated to this work.
  `ruff check .` — same 8 pre-existing issues confined to
  `calibrate_demo_squall.py`, untouched.
- `cd web && node --test test/dashboard-utils.test.js` — 51/51 passed
  (baseline 32, +19 for the Trip Checks queue's pure render helpers added
  in Phase 3).

**What was directly verified, read-only, against the live deployment.**
The current Railway URL from the README (not the dead
`incredible-liberation-production-aad7` host retired in an earlier
handoff):

- `GET https://aihackathon2026aquanonsaqone-production.up.railway.app/healthz`
  → `200 {"status":"ok"}`.
- `GET .../api/ai/anomaly/active` (no token) → `401 {"detail":"authentication
  required"}` — the pre-existing route's auth boundary is intact in
  production.
- `GET .../api/ai/anomaly/cases/open` (no token) → `404 {"detail":"Not
  Found"}` — confirms, honestly, that **none of this handoff's Phase 1-4
  code is deployed**. The new contact-ingest endpoint, the cases API, and
  the three new migrations exist only on the local branch.

No write request of any kind was made against the live deployment - these
were plain unauthenticated `GET`s, per the same read-only discipline every
earlier entry in this file used.

**What was not done, and why, rather than skipped silently:**

- **`GATEWAY_API_KEY` was not configured anywhere.** Doing so on the real
  Railway service requires Railway account/project access this environment
  does not have, and setting a production secret is exactly the kind of
  infrastructure change that needs the project owner's own credentials, not
  an agent guessing at deployment console access.
- **No fixture contact stream was submitted anywhere**, staging or
  production. Phase 5 item 2 requires a *non-production or explicitly
  approved demo environment* for this - none was available, and this
  handoff's own Phase 1-4 code is not deployed to try it against even if
  one existed.
- **The manual, device-level acceptance script (submit a fixture stream,
  watch a verification case and a responder-attention case appear, act on
  one, reload, confirm persistence, confirm a stale/normal fixture raises
  nothing) could not be completed** - same root blocker as every earlier
  entry in this file: no working local Postgres credential, Docker
  Desktop's engine unreachable, so no local backend could be started to
  drive even a local version of this script. The backend-level equivalent
  of every piece of this script - low/high confidence routing, one case per
  repeated evaluation, each responder action surviving a re-evaluation,
  auth boundaries, a stale trip producing no case - is covered by
  `backend/tests/test_anomaly_cases.py` (7/7 passing) and
  `backend/tests/test_anomaly_source.py`/`test_anomaly_active_readonly.py`
  against fake connection pools, not a real database or a real dispatcher's
  screen.
- **Nothing from this handoff has been pushed, merged, or deployed.**
  Everything above is on the local branch only.

**What this means concretely.** The five phases of docs/38 are implemented,
unit- and route-level tested without a database, and the live deployment's
existing surface was confirmed reachable and correctly protected - but
distress-detection-over-a-real-gateway-connection remains exactly what
`docs/38`'s own purpose section already says it is: unproven until a real
gateway submits real contact events and a real Postgres instance is
available to run migrations, the scheduled evaluator, and the manual
acceptance script against. Whoever next has Railway project access and/or a
working local Postgres/Docker should: set `GATEWAY_API_KEY` and confirm the
Railway cron service for `python -m app.ai.run_anomaly_evaluation`
(README "Scheduled anomaly evaluation"), run `migrate.py` to apply
`016_contact_events.sql` and `017_anomaly_cases.sql`, then run this
phase's manual acceptance script for real.

## 2026-08-29 — squall nowcasting Phase 5: staged verification, production not yet redeployed

Recorded per `docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md` Phase 5, same
environment as the entries above: Windows 11, Python 3.11.9, Flutter 3.44.7,
Node v24.14.0. A local PostgreSQL 18 service is running on this machine, but
its credentials are not the documented default and were not pursued further
at the user's explicit direction; Docker Desktop's engine did not start.

**Automated release gate — all green except the same pre-existing, unrelated
failures already present at this session's baseline:**

- `cd backend && python -m pytest -q` — 200 passed, 1 xfailed.
  `test_demo.py::test_firing_same_beat_is_idempotent` fails on a real
  pre-existing `NameError` in `fire_beat()` (`app/demo/scenarios.py`),
  unrelated to squall work and already tracked as its own task.
- `cd backend && ruff check .` — 8 pre-existing issues confined to
  `calibrate_demo_squall.py` and `app/demo/scenarios.py`, also unrelated.
- `cd mobile && flutter analyze` — no issues found;
  `flutter test test/squall_alert_test.dart` — 14/14 passed.
- `cd web && node --test test/dashboard-utils.test.js` — 58/58 passed.

**Two verification avenues not available in prior phases were used here:**

1. **Direct HTTP checks against the real Railway deployment**
   (`https://aihackathon2026aquanonsaqone-production.up.railway.app`),
   unauthenticated GETs and one deliberately-credential-less POST, no writes:
   - `GET /healthz` → `200 {"status":"ok"}`.
   - `GET /api/public/squall` → `200`, still the pre-Phase-3 response shape
     (`as_of`/`stale`/`stale_reason`), reporting a stale synthetic reading
     from 14 August 2026 — production has **not** been redeployed with this
     session's Phase 2-3 work (live-only reads, the quality gate, the
     alarm-safety clamp).
   - `POST /api/v1/pressure-events` with no `X-Api-Key` → `401` — Phase 1's
     gateway-only ingest endpoint **is** live and correctly gated.
   - `GET /api/demo/squall` → `404`, expected regardless of deployment
     state (this route only mounts when `DEMO_MODE` is set).
   - Confirmed via `git log`: local `HEAD` was 1 commit ahead of
     `origin/codex/short-messaging-weather-advisories` (Phase 4) and 3
     commits ahead of `origin/master` (Phase 3, a line-ending fix, and
     Phase 4) at the start of this phase.
2. **A real local browser DOM check** of the dashboard's new squall panel,
   serving this checkout's `web/` directory statically with no backend
   running (every fetch legitimately fails). Confirmed the panel renders a
   neutral "Squall status cannot be confirmed right now" state - never a
   false "no active detections" - and the RETURN NOW/header badges read
   `UNKNOWN`, not `MONITORING`. This check caught a real bug before it
   shipped: the client-side fallback for a totally unreachable backend was
   labelled `DEMO`, misrepresenting a plain connectivity failure as
   deliberately-synthetic data. Fixed in
   `web/js/dashboard-utils.js`'s `squallStatusHtml()` and covered by a new
   `web/test/dashboard-utils.test.js` case.

**What this means concretely.** The quality gate, live-only reads, the
`SQUALL_RETURN_NOW_ENABLED` safety clamp, and the demo-only presenter
surface are implemented, unit- and route-level tested, and now also directly
observed to behave correctly in a real browser against the real static
frontend - but, per the plan's own instruction not to overstate readiness:
nobody has watched a real phone, buoy, and dispatcher screen agree with each
other for this feature, production is still serving the pre-Phase-3 build,
and RETURN NOW remains unavailable for live use in every environment
pending a field-validation log this plan does not fabricate (see below).
Whoever next has Railway/GitHub merge access should merge this branch to
`master` and redeploy before treating any of the above as production
behavior.

---

## Squall field-validation log (template)

Per `docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md` Phase 4 item 3. This
is a **template**, not a completed log — every field below is blank because
field collection and weather-event labelling require the responsible
hardware/operations owners (real buoy deployment, clock sync, and an
official/observer ground truth this plan does not fabricate). Copy this
section, dated, once real field data collection begins; do not fill in
placeholder or synthetic numbers here.

This log is also the record `SQUALL_RETURN_NOW_ENABLED` (backend/.env.example,
`docs/05_PUBLIC_API.md` "Squall nowcast") is gated on: per the plan's release
gate, a named MDRRMO approver reviews a completed version of this log before
that flag is ever set in a deployment environment. An empty template below is
not review material — it is the shape review material must take.

**Deployment window:** `<start date>` – `<end date>`
**Recorded by:** `<name/role>`

### Fixed buoy locations

| Buoy ID | Latitude | Longitude | Deployed at | Notes |
|---|---|---|---|---|
| | | | | |

### Clock sync

| Buoy ID | Clock source (GPS/NTP/manual) | Last verified | Drift observed |
|---|---|---|---|
| | | | |

### Sampling continuity

| Buoy ID | Expected interval | Outage periods (start–end, cause) | Total uptime % over window |
|---|---|---|---|
| | | | |

### Calibration checks

| Buoy ID | Reference instrument | Reading vs. reference | Date checked |
|---|---|---|---|
| | | | |

### Weather events observed

One row per candidate squall, whether or not the model flagged it.

| Event date/time | Official PAGASA advisory? | Independent observer confirmation | Model output at the time (level, probability) | Outcome |
|---|---|---|---|---|
| | | | | |

`Outcome` is one of: **hit** (model raised `watch`/would-have-raised
`return_now` ahead of a confirmed event), **miss** (a confirmed event the
model never flagged), **false alert** (model raised a candidate with no
confirmed event), **excluded** (the array was quality-failing at the time —
cite the `status_reason`, do not backfill a guess).

### Summary figures (fill in once the table above is complete)

- Lead time (confirmed hits only): `<median / range>`
- False-alert rate: `<false alerts / total non-event evaluation windows>`
- Miss rate: `<misses / confirmed events>`
- Excluded windows: `<count and % of the evaluation window>`
- Outage periods materially affecting coverage: `<list>`

### Release gate sign-off

- [ ] Named MDRRMO approver: `<name, role, date>`
- [ ] Field-validation set above reviewed and accepted by that approver
- [ ] `SQUALL_RETURN_NOW_ENABLED` set in the deployment environment (Railway),
      not committed to the repository

Until every box above is checked with real names and real data,
`SQUALL_RETURN_NOW_ENABLED` stays unset and a live squall detection is
visible only as `watch`, never `return_now` — see
`backend/app/api/squall.py`'s `_return_now_enabled()` and the "Policy
decision" section of `docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md`.

---

## 2026-08-30 — drift/search re-tasking Phases 1-5: release gate green, live/local acceptance not performed

Per `docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md`,
Windows 11 sandbox, Python 3.11.9, Node v24.14.0, on a dedicated branch
(`codex/drift-prediction-search-retasking`, branched from `master` rather
than continuing the prior entries' branch, which belongs to an unrelated,
already-merged plan). Commits: `feat(drift): open responder-confirmed search
cases` (Phase 1), `fix(drift): make prediction inputs and snapshots honest`
(Phase 2), `feat(search): persist negative-search re-tasking` (Phase 3),
`feat(dashboard): support search-sector re-tasking` (Phase 4).

**Two policy decisions were escalated to the project owner (Lenard) rather
than guessed**, per the plan's own instruction not to choose a safety
threshold that changes a real search decision:

- Phase 2 production environmental-input quality policy: ≥2 fresh (≤60min)
  buoys near the last-known position, ≥50% observed-current coverage, wind
  non-degraded (60min ceiling structurally enforced by the existing 20min
  wind-cache TTL). Recorded in `docs/05_PUBLIC_API.md`.
- Phase 3 detection-probability presets: poor 0.3 / moderate 0.6 / good 0.9,
  named by search method/visibility, none reaching 1.0. Same doc.

**Automated release gate — green, same pre-existing failures as every other
entry in this file:**

- `cd backend && python -m pytest -q` — 218 passed, 1 xfailed, 1
  pre-existing failure (`test_demo.py::test_firing_same_beat_is_idempotent`,
  confirmed by stashing this work and re-running against a clean `master` -
  identical failure, unrelated to this handoff). `ruff check .` — same 8
  pre-existing issues confined to `calibrate_demo_squall.py`, untouched.
- `node --test web/test/dashboard-utils.test.js` — 57/57 passed (+5 for
  `eligibleForSearchReport`, the pure eligibility check the dashboard's
  "Mark a searched area" button is gated on).
- `node --check` on both changed dashboard JS files - no syntax errors.

**What was directly verified, read-only, against the live deployment**
(`https://aihackathon2026aquanonsaqone-production.up.railway.app`, per the
README):

- `GET /healthz` → `200 {"status":"ok"}`.
- `GET /api/ai/anomaly/active` and `GET /api/ai/drift/incidents` (no token)
  → `401 {"detail":"authentication required"}` - pre-existing auth
  boundaries intact.
- `GET /api/demo/drift/incident/1` (this handoff's new demo-gated route) →
  `404` - not deployed.
- `POST /api/ai/drift/cases` (this handoff's new case-open route, empty
  body, no token) → `405 Method Not Allowed` from the static-file catch-all
  mount, not from the drift router - the path isn't registered on the
  deployed app at all. Confirms, honestly, **none of this handoff's Phase
  1-4 code is deployed**; it exists only on the local branch.

No write request of any kind was made against the live deployment - plain
unauthenticated `GET`s and one deliberately-empty `POST` that never reached
a handler, per the same read-only discipline every earlier entry in this
file used.

**What was not done, and why, rather than skipped silently:**

- **The manual acceptance script (open a synthetic case, inspect the prior
  contour, submit a negative sector, reload, verify the posterior and
  next-area recommendation change, then confirm a production-mode case with
  no buoy data stops at the honest insufficiency state) could not be run.**
  A local PostgreSQL 18 service is running on this machine (`pg_isready`
  confirms it), but its password does not match the `.env.example`
  convention and is not otherwise known to this session; Docker Desktop's
  engine is also not running, closing that alternate path. Guessing at or
  brute-forcing the password was not attempted. The project owner was
  offered the choice to supply it, run the script themselves, or accept
  this documented gap, and chose the latter (this entry).
- **`python -m app.ai.drift_eval` was not run** - it requires `DATABASE_URL`
  and exits immediately without one (same blocker as above). The evaluator
  was still improved this phase: it now reports `excluded_low_quality_runs`
  (tracks too short to score) instead of silently dropping them from an
  inconsistent denominator, and `containment_rate`'s denominator was
  corrected to match `search_area_reduction_factor`/`prediction_runtime_ms`
  (all three now divide by the same evaluated count). No new numbers are
  published because none were measured.
- **The Phase 4 dashboard interaction (two-click rectangle, preset picker,
  confirm panel, submit) was not exercised in a browser.** It has no DOM
  dependency it could be unit-tested without a browser except the
  eligibility gate above, which is tested; the rendering and Leaflet-event
  wiring were reviewed by hand, not run.
- `README.md`'s status table previously read "✅ Built, measured, live" for
  drift prediction and Bayesian search re-tasking. That claim is corrected
  in this commit: the two rows now say what is actually true - built and
  tested, not yet deployed, and gated on zero-buoy reality even once it is.

**What this means concretely.** All five phases of docs/40 are implemented
and covered by fast, database-free unit/API tests (fake connection pools,
not a real Postgres instance or a real dispatcher's screen), and the live
deployment's existing surface was confirmed reachable, correctly protected,
and does not yet run any of this code. Whoever next has the local Postgres
password, Docker access, or Railway project access should: create a scratch
database, run `migrate.py` (through `021_search_sector_reports.sql`), seed
or acknowledge a real SOS, open a case via `POST /api/ai/drift/cases`, and
run the manual acceptance script above for real before this ships. Until
then, treat drift prediction and search re-tasking as demo/simulation- and
unit-verified only - exactly the caveat `docs/40`'s own "Purpose and
delivery rule" already anticipated: this plan makes the buoy/current
hardware's absence visible rather than fabricating a live search field.

---

## Judging weights — build toward these

| Criterion | Weight | Where it's won |
|---|---|---|
| **Technical Soundness** | **50%** | **The mentor's report — mentoring sessions, not the pitch** |
| Impact & Feasibility | 25% | Field research, deployment cost, who pays |
| Presentation | 15% | Storytelling, **live demo success**, Q&A defence |
| Innovation & Scalability | 10% | Creative impression, deployment path |

**Half the score comes from a mentor's judgement of your technical depth in
conversation.** Show them working hardware early. Bring a design question, not
a status update. Be explicit about what's simulated — mentors are technical and
will spot a fake instantly; labelling it yourself reads as competence.

---

## Demo script (5 minutes)

**1. Hook — 30s.**
> "We interviewed fishermen in New Washington. When they fish, *all of them* are
> in a cellular dead zone. Every safety app on the market stops working exactly
> where fishermen need it most."

**2. Stakes — 30s.**
MDRRMO currently learns about a capsizing hours later, by word of mouth.

**3. The demo — 2 min.**
- Hold up the phone. **Put it in airplane mode in front of the judges.**
- Press SOS.
- Narrate the delivery states as they advance: saved on phone → received by
  boat pod → received by AqOne → MDRRMO responded.
- The dashboard across the room lights up.
- **Hand a judge the phone and let them press it.**

**4. How it works — 1 min.** One slide: phone → boat-pod WiFi → direct LoRa →
gateway → backend → dashboard. Mention optional relay buoys, the signed
envelope, and replay protection here,
unprompted — that's your cybersecurity answer delivered before anyone asks.

**5. What's real, what's next — 45s.** Read the status table below out loud.
Then:
> "Safety drives adoption, adoption generates catch data, catch data enables the
> model — in that order."

That single sentence pre-empts the AI question and reframes it as sequencing
rather than absence.

**6. Close — 15s.** Cost per shared pod, where fixed sensor/relay buoys add
value, and who pays (LGU/BFAR). Have real numbers.

### Rehearse the airplane-mode moment specifically

It is the entire pitch. If the room's WiFi could plausibly explain the result,
the demo proves nothing. Make the isolation visible and undeniable — hold the
phone up, show the airplane icon, let a judge verify it.

---

## Contingency ladder

Work down. Each rung is still a credible demo. **Decide the rung before you
walk on stage, not during.**

| Rung | Situation | What you do | What you say |
|---|---|---|---|
| **1** | Everything works | Full live demo, judge presses the button | Nothing extra |
| **2** | IMU dead | Sensor-bypass mode, button-triggered frame | "Sensing is bypassed; the mesh path is real" |
| **3** | Mesh unreliable in the room | Move nodes closer, lower spreading factor, retry | "We're at close range because of RF conditions in this hall" |
| **4** | Radio dead | Play the screencast, show the hardware physically | "This ran last night; here's the recording and the hardware" |
| **5** | Backend/network down | Screencast + architecture walkthrough | "Our deployment is unreachable from this venue; here's the recorded run" |

**Rung 4 is why the screencast exists. Record it on Day 2, not Day 3.** Once it
exists, every hardware risk drops from fatal to embarrassing.

---

## Q&A — one prepared answer each, everyone answers the same way

**"Is the mesh actually working or simulated?"**
> Answer precisely. If one hop is real and multi-hop isn't, say exactly that.
> "One real LoRa hop, phone to boat pod to gateway. Optional stationary-buoy
> relay is implemented in firmware but still needs an outdoor range test."

**"What's your model's accuracy?"**
> "We deliberately didn't ship a model. With the catch data available, the
> target would be circular — predicting catch volume from catch volume. In a
> system that can flag zones for regulatory review, that has a real livelihood
> cost, so we scoped it post-MVP and built the safety layer that generates the
> data first."

**"How do you stop someone spoofing an SOS?"**
> "Per-device HMAC keys, signed frames, replay protection by message ID, and a
> timestamp window. Jamming we can't mitigate at this budget, and we say so."

**"What's the range?"**
> Give the number **you measured**, not the datasheet number.

**"Battery life?"**
> Duty-cycled SoftAP, LoRa listening continuously, solar sizing. Be honest that
> the demo unit runs the AP always-on.

**"What if the gateway is down?"**
> "Store-and-forward at the boat pod with backoff retry; an optional stationary
> relay can help if the direct path is weak. An SOS is never dropped from the
> queue."

**"Why not a satellite beacon / PLB?"**
> Cost per vessel. Have the price comparison ready — this is a small-scale
> fisherman's budget.

**"How much per pod or buoy? Who pays?"**
> Separate the shared pod cost from the optional fixed-buoy hull and mooring
> cost. LGU/BFAR procurement is the realistic path.

**"What happens when a pod or buoy is stolen or lost?"**
> "The key is revoked in the device registry; frames from it are rejected. A
> pod is removable and replaceable; a fixed buoy is serviced through the
> existing maintenance route."

---

## Status table — keep this true, update it live

This is the honesty artifact. It goes in the README, in the deck, and you read
it out loud. In v1 this had to be retrofitted across many files after claims had
drifted from reality; here it's maintained as you build.

| Capability | Status | Notes |
|---|---|---|
| SOS over direct LoRa, phone offline | ⬜ | Phone → boat pod → tall shore gateway. The core claim. Update the moment it works. |
| Signed frames + replay protection | ⬜ | |
| Store-and-forward at boat pod | ⬜ | |
| Optional multi-hop relay (3+ nodes) | ⬜ | Stationary relay buoy; likely bench-only — say so |
| Stationary buoy hazard sensing | ⬜ | Fixed barometer/current observations; do not claim hardware data before field validation |
| Dashboard live feed + acknowledge | ⬜ | |
| Deployed backend, healthcheck green | ⬜ | |
| Range measured on water | ⬜ | Record the metres |
| AI hotspot model | ❌ **Not built** | Deliberate — circular target, no data |
| Catch-decline detection | ❌ **Not built** | Deliberate — out of scope |
| Catch logging / photos | ❌ **Not built** | Deliberate |
| Push notifications | ❌ **Not built** | Roadmap |
| Aklanon localisation | ❌ **Not built** | Roadmap |

Legend: ✅ working & demonstrated · 🟡 partial (explain) · ⬜ not yet · ❌ deliberately out of scope

**Never mark something ✅ that hasn't been run end to end.** A judge finding one
false claim invalidates every true one.

---

## Historical event materials

The completed AI Fest submission checklist and Day 3 logistics are archived in
[`archive/AI_FEST_2026_DEADLINES.md`](archive/AI_FEST_2026_DEADLINES.md).

Current external event deadlines live in
[`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md).
