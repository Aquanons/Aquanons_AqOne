# Security Audit Verification Results

## 1. Headline

Verification of 33 audit candidates (32 from the initial audit report and 1 new candidate discovered during probe authoring) yielded 28 CONFIRMED findings, 2 TRACE_CONFIRMED findings, 2 INCONCLUSIVE findings, 1 finding marked NEEDS_HARDWARE, 0 REFUTED findings, and 0 NOT_RUN findings.
All 8 throwaway PostgreSQL database probes ran successfully against a local PostgreSQL 18 server.
Both project default test suites remain green and untouched, with 387 passed in backend and 258 passed in mobile.

## 2. Findings Summary Table

| Finding ID | Verdict | Evidence | Reason |
|---|---|---|---|
| backend.sos.untrusted-provenance-claims | CONFIRMED | fake | Anonymous SOS requests can self-assert responder-confirmed trust tier and mesh delivery without a gateway API key. |
| backend.sos.anonymous-incidents-crowd-dispatch-feed | CONFIRMED | postgres | A burst of anonymous SOS requests exhausts the 50-incident feed limit and evicts genuine distress calls. |
| mobile.sos.buoy-only-reply-unroutable | CONFIRMED | postgres + fake | Handset reply uses an unassigned client-side ID that causes HTTP 404 on backend because buoy-only SOS lacks a database row ID. |
| backend.trips.unbound-public-access | CONFIRMED | fake | Trip endpoints (/api/v1/trips, /api/v1/trips/{id}) accept unauthenticated read and patch requests without principal binding. |
| backend.warning-delivery.unbound-state-authority | CONFIRMED | fake | Advisory delivery endpoints allow unauthenticated callers to record and read warning deliveries without authority check. |
| backend.vessel-profile.unbound-owner-write | CONFIRMED | postgres | Anonymous POST requests can overwrite an existing vessel's profile and boat name without ownership proof. |
| backend.public-sea-condition.operator-identity-disclosure | CONFIRMED | fake | Anonymous GET /api/public/sea-condition returns set_by_user_id, leaking internal operator database account IDs. |
| backend.hotspots.minimum-cohort-policy-drift | CONFIRMED | fake | Catch hotspot cells are published with fewer than 5 distinct reporting vessels (cohort sizes 3 and 4). |
| backend.current-ingest.unbound-calibration-claim | CONFIRMED | fake | Unauthenticated current-reading submissions can self-declare calibration_status=qualified without verification. |
| backend.contacts.future-timestamp-anomaly-suppression | CONFIRMED | fake | Contact event ingest accepts day-ahead future timestamps without validation, allowing anomaly suppression. |
| backend.contacts.optional-position-crash | CONFIRMED | fake | Ingesting a contact without latitude/longitude causes TypeError during fleet-wide anomaly evaluation. |
| backend.ai.anomaly.zero-contact-poison-run | CONFIRMED | postgres | Open trips with zero buoy contacts abort anomaly evaluation with KeyError/IndexError and leave active scores cleared. |
| backend.ai.anomaly.authenticated-whole-fleet-recompute | INCONCLUSIVE | measure | Evaluation threw ProbeBroken because evaluate_and_persist crashes on real Postgres due to unencoded JSONB parameters. |
| new.backend.anomaly.jsonb-parameter-encoding | CONFIRMED | postgres | Calling evaluate_and_persist on real Postgres raises asyncpg DataError because Python dicts and lists are passed unencoded to jsonb parameters. |
| backend.auth.login-timing-enumeration | CONFIRMED | fake | Unknown email skips bcrypt evaluation while existing email executes bcrypt, exposing account existence via response timing. |
| backend.operator-jwt.no-server-revocation | CONFIRMED | fake | Operator JWT tokens remain valid and accepted even after the backing user account is deleted from the database. |
| backend.ai.squall.flag-authorizes-live-model-replacement | CONFIRMED | fake | Non-admin roles (mdrrmo, lgu) can trigger squall model retraining and overwrite weights when ALLOW_TRAINING is true. |
| backend.catch.global-idempotency-cross-vessel-write | CONFIRMED | postgres | Reusing a local_id across different vessels allows one vessel to overwrite another vessel's catch log record. |
| backend.demo-weather.unbounded-coordinate-expansion | CONFIRMED | fake | Demo weather route accepts arbitrarily large coordinate ranges without bounding cell expansion. |
| backend.public-squall.unbounded-history-load | CONFIRMED | postgres | Public squall reading endpoint loads unbounded historical readings spanning days rather than recent window. |
| backend.mesh.unbounded-public-storage | CONFIRMED | static | Mesh chat message storage has no retention pruning, automated cleanup, or volume rate limiting. |
| firmware.shore.committed-uplink-credential | CONFIRMED | static | Shore gateway sketch contains hardcoded WiFi credentials (SSID/password) and gateway API key. |
| firmware.loam.shared-default-key | INCONCLUSIVE | static | Control probe test_loam_control_headers_are_byte_identical failed due to 2 leading spaces in shore header, invalidating probe per Rule 1. |
| firmware.shore.tls-peer-verification-disabled | CONFIRMED | static | Shore gateway firmware explicitly disables TLS peer certificate verification via setInsecure(). |
| firmware.warning.missing-revision-tombstone | CONFIRMED | static | Buoy warning cache overwrites warnings on incoming packets without enforcing increasing revision numbers. |
| firmware.buoy.chat-starves-sos-tx-ring | CONFIRMED | static | Buoy transmission ring allocates slots first-come first-served with no reserved capacity for distress SOS frames. |
| mobile.release.debug-signing-fallback | CONFIRMED | static | Release build configuration falls back to Android debug key, and tracked release APK is signed with Android Debug certificate. |
| mobile.sos.standdown-intent-treated-resolved | CONFIRMED | fake | Stand-down requests that are rejected by backend (503) or never dispatched are treated locally as resolved. |
| mobile.eta.server-clock-discarded | CONFIRMED | fake | Rescue ETA countdown computes remaining time against local handset clock rather than authoritative server time. |
| mobile.squall.ack-survives-missed-clear | CONFIRMED | fake | Acknowledging a squall alert permanently suppresses alarms for future squalls sharing the same buoy identifier. |
| mobile.location.undisclosed-weather-coordinate-egress | TRACE_CONFIRMED | trace | HomePage reads GPS coordinates on startup and transmits them to backend and Open-Meteo despite privacy notice claiming SOS-only use. |
| mobile.map.undisclosed-location-derived-tile-egress | TRACE_CONFIRMED | trace | Map centres camera on GPS fix and fetches OpenStreetMap tiles over network when offline MBTiles asset is missing. |
| firmware.buoy.sos-queue-untrusted-capacity | NEEDS_HARDWARE | trace | Buoy queue has 12 slots keyed on (vessel_id, client_ts) returning 503 when full; physical bench test required to verify mesh behaviour. |

## 3. Inconclusive and Not-Run Findings

### backend.ai.anomaly.authenticated-whole-fleet-recompute (INCONCLUSIVE)
The measurement probe test_measure_whole_fleet_evaluation_cost threw ProbeBroken during execution.
The underlying evaluate_and_persist function crashed with asyncpg.exceptions.DataError ("invalid input for query argument $2: ... expected str, got dict").
This crash was caused by finding new.backend.anomaly.jsonb-parameter-encoding, where Python dictionaries are passed directly to jsonb parameters without a registered asyncpg JSON codec.
Because the anomaly evaluation pipeline fails on real PostgreSQL, whole-fleet timing measurements could not be gathered.

### firmware.loam.shared-default-key (INCONCLUSIVE)
The finding's harness control probe test_loam_control_headers_are_byte_identical failed.
Line 1 of firmware/shore/AqOneShore/AqOneLoam.h contains two leading whitespace characters ("  // AqOneLoam.h") compared to firmware/buoy/AqOneBuoy/AqOneLoam.h ("// AqOneLoam.h").
Under Section 1 Rule 1 of PROBES.md, a failing control probe invalidates all paired probes and forces the finding verdict to INCONCLUSIVE.
Substantively, both tracked headers still contain the shared default key "aqone-dev-key-change-me" and sign HMACs using a single global key across 3 call sites.

## 4. Measurement Numbers

No numerical benchmarks could be recorded for backend.ai.anomaly.authenticated-whole-fleet-recompute.
The measurement run was aborted due to the JSONB encoding exception documented above.

## 5. Trace Answers

### T1 - mobile.location.undisclosed-weather-coordinate-egress (TRACE_CONFIRMED)
1. Does HomePage read the device position during initialisation, without the fisher tapping anything?
Yes.
Evidence: mobile/lib/ui/home_page.dart:112, 116, 183, 226 and mobile/lib/services/location_service.dart:75-96.
2. Are those coordinates placed in a request to the AqOne backend forecast route, to api.open-meteo.com, or both?
Both.
Evidence: mobile/lib/services/forecast_provider.dart:86-99, 115-128, 169-171, 184-189, 200-205.
3. Are the requested coordinates persisted, for example under the forecast_record_v2 SharedPreferences key?
Yes.
Evidence: mobile/lib/ui/home_page.dart:244, mobile/lib/data/forecast_cache.dart:17, 31, and mobile/lib/models/forecast_outlook.dart:153-160.
4. What does the in-app location or privacy text say location is used for?
Quote from mobile/lib/l10n/app_en.arb:281 ("privacyPolicy": "Privacy Policy"), which links to mobile/lib/ui/info_page.dart:102-104: "Position is only sent as part of an SOS you deliberately send. The app does not track or transmit your location in the background, and it does not record where you fish."
Additionally, mobile/lib/services/location_service.dart:50 states "AqOne needs location permission to send your position."
Verdict: TRACE_CONFIRMED.

### T2 - mobile.map.undisclosed-location-derived-tile-egress (TRACE_CONFIRMED)
1. Does the Venture map centre its camera on the device fix?
Yes.
Evidence: mobile/lib/ui/venture_page.dart:208, 293-295, 674.
2. When the offline MBTiles asset is missing, does tile loading fall back to tile.openstreetmap.org?
Yes.
Evidence: mobile/lib/services/mbtiles_provider.dart:223-232, mobile/lib/services/tile_cache.dart:171-190, mobile/lib/ui/venture_page.dart:688-690, and mobile/lib/core/config.dart:86-87.
3. Is the MBTiles asset both declared in mobile/pubspec.yaml and present on disk?
No.
Evidence: mobile/pubspec.yaml:119-127 omits the asset, and directory mobile/assets/map/ does not exist on disk.
4. What does the in-app location or privacy text say location is used for?
Same privacy policy text as T1.4: mobile/lib/l10n/app_en.arb:281 and mobile/lib/ui/info_page.dart:102-104 state that position is only transmitted as part of a deliberate SOS.
Verdict: TRACE_CONFIRMED.

### T3 - firmware.buoy.sos-queue-untrusted-capacity (NEEDS_HARDWARE)
1. What is MAX_QUEUE in firmware/buoy/AqOneBuoy/AqOneBuoy.ino?
12.
Evidence: firmware/buoy/AqOneBuoy/AqOneBuoy.ino:128.
2. What key does handlePostSos de-duplicate on, and can one handset fill every slot by varying client_ts?
Deduplication key is (vessel_id, client_ts).
Yes, any client can consume all 12 queue slots by submitting different client_ts values.
Evidence: firmware/buoy/AqOneBuoy/AqOneBuoy.ino:486-523.
3. Does a full queue answer 503 to the next request, whoever sends it?
Yes, it answers HTTP 503 with {"error":"queue full"}.
Evidence: firmware/buoy/AqOneBuoy/AqOneBuoy.ino:505-509.
4. Are slots freed only by a matching signed ACK, and do they survive a reboot (NVS)?
Yes, slots are freed only when receiving a matching signed ACK (or if payload fails encoding), and survive reboots via ESP32 NVS persistence.
Evidence: firmware/buoy/AqOneBuoy/AqOneBuoy.ino:157-175, 419-423, 873-888, 1107.
Verdict: NEEDS_HARDWARE.

## 6. Probe Changes and New Observations

### Probe Harness Changes
1. File: backend/tests/security_probes/test_probe_auth.py
Reason: Pydantic EmailStr rejects RFC 2606 .invalid top-level domain with HTTP 422.
Change: Replaced nobody@example.invalid with nobody@example.com in test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password to allow request to reach the login endpoint handler.
2. File: backend/tests/security_probes/test_probe_anomaly.py
Reason: In test_one_ordinary_live_trip_evaluates_on_real_postgres, an untyped parameter in the interval subtraction expression caused PostgreSQL to infer type interval rather than timestamptz, throwing DatatypeMismatchError during test fixture setup.
Change: Added an explicit ::timestamptz cast to parameter $1 in the buoy_contacts insertion query.

### New Observations
1. In firmware/shore/AqOneShore/AqOneLoam.h:1, two leading spaces precede the comment header, causing byte comparison with firmware/buoy/AqOneBuoy/AqOneLoam.h to fail in test_loam_control_headers_are_byte_identical.
2. In backend/app/ai/anomaly_service.py:204-256, Python dictionaries and lists are passed directly to SQL parameters with ::jsonb casts without registering an asyncpg JSON codec, triggering DatatypeMismatchError / DataError on real PostgreSQL.
3. In mobile/releases/aqone-release.apk, apksigner verified that the tracked APK is signed with the Android Debug key (CN=Android Debug, O=Android, C=US, SHA-256 a8e90fc589764bb96b405ff5a9332b369db27f2b8b92aaec08a7d1ef0961dba4).
