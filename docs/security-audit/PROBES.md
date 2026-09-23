# Security audit verification probes

**Purpose:** Decide which of the 32 `needs_validation` candidates in `REPORT.md` are real, by running them against the current code.
**Written by:** Claude Code, 2026-09-23, against `master` at `ef6cc7d` (the audit reviewed `c5312b8`).
**Executed by:** Antigravity (Gemini), following the run book below.
**Result files:** `VALIDATION-RESULTS.md` and `validation-results.json` in this folder, plus raw output under `probe-runs/`.

## 1. How a probe reads

Every probe asserts the **safe** behaviour.
A probe that fails its assertion has observed the unsafe behaviour.

| Probe outcome | Verdict for its finding |
|---|---|
| Python: FAILED with `AssertionError` or `Failed:` (including `DID NOT RAISE`) | CONFIRMED |
| Dart: `result: failure` (a failed `expect`) | CONFIRMED |
| PASSED / `result: success` | REFUTED |
| Python: FAILED with `ProbeBroken` or any other exception, or ERROR in setup | INCONCLUSIVE |
| Dart: `result: error` (any throw, including `ProbeBroken`) | INCONCLUSIVE |
| SKIPPED (no local Postgres) | NOT_RUN |

Rules for combining several probes into one verdict:

1. A finding id ending in `:control` is a harness check and must PASS. If a control fails, every probe of that finding is INCONCLUSIVE.
2. If at least one probe of a finding is CONFIRMED and its controls pass, the finding is CONFIRMED. Record which probes passed in `notes`.
3. If every probe of a finding PASSED, the finding is REFUTED.
4. `mobile.sos.buoy-only-reply-unroutable` has a backend half and a handset half. It is CONFIRMED only when both halves fail.
5. A finding id ending in `:measure` never gets a verdict. Report its numbers as MEASURED.
6. Trace tasks (section 4) are answered by reading code, and get TRACE_CONFIRMED, TRACE_REFUTED, or NEEDS_HARDWARE.

Python probes carry their finding id as a JUnit `<property name="finding">`.
Dart probes carry it as the `[finding-id]` prefix of the test or group name.

## 2. Probe map

Evidence levels: `fake` runs the real handler against an in-memory database stand-in, `postgres` runs against a throwaway migrated local database, `static` reads tracked source or artifacts, `trace` is a human-style code read.

| Finding | Probe(s) | Evidence |
|---|---|---|
| backend.sos.untrusted-provenance-claims | `backend/tests/security_probes/test_probe_sos.py::test_anonymous_sos_cannot_self_assert_responder_confirmation`, `::test_anonymous_sos_cannot_claim_buoy_delivery_without_gateway_key` | fake |
| backend.sos.anonymous-incidents-crowd-dispatch-feed | `test_probe_sos.py::test_genuine_sos_survives_a_burst_of_anonymous_sos` | postgres |
| mobile.sos.buoy-only-reply-unroutable | `test_probe_sos.py::test_handset_reply_reaches_an_sos_that_arrived_only_over_the_buoy` and `mobile/test_security_probes/sos_probes_test.dart` "handset half" | postgres + fake |
| backend.trips.unbound-public-access | `test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal` (3 routes) | fake |
| backend.warning-delivery.unbound-state-authority | `test_probe_unauth_routes.py::test_warning_delivery_route_requires_an_authority` (2 routes) | fake |
| backend.vessel-profile.unbound-owner-write | `test_probe_unauth_routes.py::test_anonymous_caller_cannot_replace_an_existing_vessel_identity` | postgres |
| backend.public-sea-condition.operator-identity-disclosure | `test_probe_public_disclosure.py::test_public_sea_condition_does_not_expose_operator_account` | fake |
| backend.hotspots.minimum-cohort-policy-drift | `test_probe_public_disclosure.py::test_hotspot_cell_needs_five_distinct_reporters` (3, 4) + control | fake |
| backend.current-ingest.unbound-calibration-claim | `test_probe_ingest_trust.py::test_request_text_cannot_mark_a_current_reading_qualified` | fake |
| backend.contacts.future-timestamp-anomaly-suppression | `test_probe_ingest_trust.py::test_contact_ingest_rejects_a_day_ahead_timestamp` + control | fake |
| backend.contacts.optional-position-crash | `test_probe_anomaly.py::test_contact_without_coordinates_does_not_abort_fleet_evaluation` | fake |
| backend.ai.anomaly.zero-contact-poison-run | `test_probe_anomaly.py::test_zero_contact_trip_for_a_fresh_vessel_...`, `::..._known_vessel_...`, `::test_failed_evaluation_does_not_commit_score_deactivation` | fake + postgres |
| backend.ai.anomaly.authenticated-whole-fleet-recompute | `test_probe_anomaly.py::test_measure_whole_fleet_evaluation_cost` | postgres, MEASURE |
| new.backend.anomaly.jsonb-parameter-encoding | `test_probe_anomaly.py::test_one_ordinary_live_trip_evaluates_on_real_postgres` | postgres |
| backend.auth.login-timing-enumeration | `test_probe_auth.py::test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password` | fake |
| backend.operator-jwt.no-server-revocation | `test_probe_auth.py::test_token_for_an_account_that_no_longer_exists_is_rejected` | fake |
| backend.ai.squall.flag-authorizes-live-model-replacement | `test_probe_auth.py::test_non_admin_operator_cannot_replace_the_live_squall_model` (mdrrmo, lgu) + control | fake |
| backend.catch.global-idempotency-cross-vessel-write | `test_probe_catch.py::test_one_vessel_cannot_rewrite_another_vessels_catch_log` | postgres |
| backend.demo-weather.unbounded-coordinate-expansion | `test_probe_resource_bounds.py::test_demo_weather_rejects_ten_thousand_coordinate_cells` | fake |
| backend.public-squall.unbounded-history-load | `test_probe_resource_bounds.py::test_public_squall_does_not_load_week_old_readings` | postgres |
| backend.mesh.unbounded-public-storage | `test_probe_resource_bounds.py::test_mesh_chat_has_a_retention_or_admission_control` | static |
| firmware.shore.committed-uplink-credential | `test_probe_repo_static.py::test_shore_sketch_holds_no_concrete_credential` (3 keys) | static |
| firmware.loam.shared-default-key | `test_probe_repo_static.py::test_loam_key_is_not_the_repository_default`, `::test_loam_signature_key_is_selected_per_source_id` + control | static |
| firmware.shore.tls-peer-verification-disabled | `test_probe_repo_static.py::test_shore_verifies_the_backend_certificate` | static |
| firmware.warning.missing-revision-tombstone | `test_probe_repo_static.py::test_buoy_warning_cache_orders_updates_by_revision` | static |
| firmware.buoy.chat-starves-sos-tx-ring | `test_probe_repo_static.py::test_tx_ring_keeps_capacity_for_distress_frames` | static (runtime needs hardware) |
| mobile.release.debug-signing-fallback | `test_probe_repo_static.py::test_release_build_does_not_fall_back_to_debug_signing`, `::test_tracked_release_apk_is_not_debug_signed` | static |
| mobile.sos.standdown-intent-treated-resolved | `mobile/test_security_probes/sos_probes_test.dart` group + control | fake |
| mobile.eta.server-clock-discarded | `sos_probes_test.dart` "rescue ETA is measured against server time" | fake |
| mobile.squall.ack-survives-missed-clear | `mobile/test_security_probes/squall_probes_test.dart` | fake |
| mobile.location.undisclosed-weather-coordinate-egress | Trace T1 | trace |
| mobile.map.undisclosed-location-derived-tile-egress | Trace T2 | trace |
| firmware.buoy.sos-queue-untrusted-capacity | Trace T3 | trace, NEEDS_HARDWARE |

Known limits of individual probes, so a verdict is not over-read:

- The login-timing probe counts calls to `app.api.auth.verify_password`. It is a stand-in for a timing measurement, not one.
- The mesh-chat and firmware probes are static. They prove what the tracked source says, not what is flashed or deployed.
- The APK probe looks for the `Android Debug` certificate subject in the file bytes. Confirm with `apksigner` (section 3, step 6).
- The buoy-only reply probes encode the route today's handset uses. They must be revisited when a fix changes that route.
- `new.backend.anomaly.jsonb-parameter-encoding` is not an audit finding. It was spotted while writing these probes and needs its own verdict.

## 3. Run book

Run everything from the repository root on Windows PowerShell unless a step says otherwise.
Do not change production code, and do not commit or push.

1. **Record the starting point.**
   Run `git rev-parse HEAD` and `git status --short`, and save both to `probe-runs/<RUN>/environment.txt`, where `<RUN>` is a timestamp like `20260923T1500`.
   Also record `python --version`, `flutter --version`, and the Postgres server version.

2. **Start a throwaway local Postgres.**
   Prefer Docker: `docker run -d --name aqone-probe-pg -e POSTGRES_PASSWORD=probe -p 55432:5432 postgres:18`, then use `postgresql://postgres:probe@localhost:55432/postgres`.
   If Docker is unavailable, use the local PostgreSQL 18 service with credentials Len provides.
   Never point the probes at Render or at any `DATABASE_URL` from a `.env` file; the fixture refuses non-local hosts anyway.
   If no local Postgres can be started, continue: the database probes SKIP and their findings become NOT_RUN.

3. **Run the backend probes.**

   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
   $env:AQONE_SECURITY_PROBES = '1'
   $env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
   python -m pytest tests/security_probes -rA -p no:cacheprovider --junitxml=../docs/security-audit/probe-runs/<RUN>/backend-junit.xml *> ../docs/security-audit/probe-runs/<RUN>/backend-output.txt
   ```

4. **Run the mobile probes.**

   ```powershell
   cd mobile
   flutter test test_security_probes --reporter expanded --file-reporter json:../docs/security-audit/probe-runs/<RUN>/mobile-results.jsonl *> ../docs/security-audit/probe-runs/<RUN>/mobile-output.txt
   ```

5. **Answer the trace tasks** in section 4, citing `file:line` for every claim.

6. **Check the tracked APK signer** if Android build-tools are installed: `apksigner verify --print-certs mobile/releases/aqone-release.apk`.
   Record the signer DN and certificate SHA-256 digest; neither is secret.

7. **Prove the default suites are untouched.**
   With `AQONE_SECURITY_PROBES` and `DATABASE_URL` unset, run `python -m pytest -q` in `backend` and `flutter test` in `mobile`.
   Record the pass counts; they were 387 and 258 on 2026-09-23.

8. **Tear down** with `docker rm -f aqone-probe-pg`, and remove the two environment variables.

9. **Write the results** (section 5), then update root `HANDOFF.md`.

### What you may and may not change

- You may fix the probe **harness** when a probe cannot reach the behaviour: an import, a fixture, a column name, or a request body that gets HTTP 422.
  Log every such change in `probe_changes` with the reason, and rerun.
- You may not change what a probe asserts, its expected values, or its safe-behaviour condition.
  If a probe seems to assert the wrong thing, leave it, mark the finding INCONCLUSIVE, and explain why in `notes`.
- Never print or copy a secret value.
  The credential probes report key names and lengths only; do not open the configuration block of `AqOneShore.ino` to "double-check".
- Send no traffic to any deployed service, transmit nothing over radio, and flash no board.

## 4. Trace tasks

Answer each question with yes or no plus `file:line` evidence.

**T1 - mobile.location.undisclosed-weather-coordinate-egress**

1. Does `HomePage` read the device position during initialisation, without the fisher tapping anything? (`mobile/lib/ui/home_page.dart`, `mobile/lib/services/location_service.dart`)
2. Are those coordinates placed in a request to the AqOne backend forecast route, to `api.open-meteo.com`, or both? (`mobile/lib/services/forecast_provider.dart`)
3. Are the requested coordinates persisted, for example under the `forecast_record_v2` SharedPreferences key?
4. What does the in-app location or privacy text say location is used for? Quote the ARB key and English string from `mobile/lib/l10n/app_en.arb`.

TRACE_CONFIRMED if 1 and 2 are yes and the text in 4 mentions only SOS use.

**T2 - mobile.map.undisclosed-location-derived-tile-egress**

1. Does the Venture map centre its camera on the device fix? (`mobile/lib/ui/venture_page.dart`)
2. When the offline MBTiles asset is missing, does tile loading fall back to `tile.openstreetmap.org`? (`mobile/lib/services/mbtiles_provider.dart`, `mobile/lib/services/tile_cache.dart`)
3. Is the MBTiles asset both declared in `mobile/pubspec.yaml` and present on disk?
4. Same privacy-text question as T1.4.

TRACE_CONFIRMED if 1 and 2 are yes, 3 is no, and the text mentions only SOS use.

**T3 - firmware.buoy.sos-queue-untrusted-capacity**

1. What is `MAX_QUEUE` in `firmware/buoy/AqOneBuoy/AqOneBuoy.ino`?
2. What key does `handlePostSos` de-duplicate on, and can one handset fill every slot by varying `client_ts`?
3. Does a full queue answer 503 to the next request, whoever sends it?
4. Are slots freed only by a matching signed ACK, and do they survive a reboot (NVS)?

The verdict is NEEDS_HARDWARE, with these facts attached for the bench test.

## 5. Results format

Write two files in `docs/security-audit/`.

**`validation-results.json`** is the machine-readable record:

```json
{
  "run": {
    "run_id": "<RUN>",
    "started_at": "ISO 8601 +08:00",
    "finished_at": "ISO 8601 +08:00",
    "git_head": "sha",
    "worktree_dirty_before": true,
    "python": "3.11.x",
    "flutter": "3.x",
    "postgres": "18.x or null",
    "db_probes_ran": true,
    "agent": "Antigravity (<model>)"
  },
  "findings": [
    {
      "id": "backend.sos.untrusted-provenance-claims",
      "verdict": "CONFIRMED | REFUTED | INCONCLUSIVE | NOT_RUN | MEASURED | TRACE_CONFIRMED | TRACE_REFUTED | NEEDS_HARDWARE",
      "evidence_level": "fake | postgres | static | trace | measure",
      "probes": [
        {
          "test_id": "tests/security_probes/test_probe_sos.py::test_...",
          "outcome": "passed | failed | error | skipped",
          "message": "first line of the assertion or exception message"
        }
      ],
      "controls_ok": true,
      "notes": "anything a reviewer needs; empty string if none"
    }
  ],
  "measurements": [
    {"id": "backend.ai.anomaly.authenticated-whole-fleet-recompute", "metrics": {}}
  ],
  "traces": [
    {"id": "T1", "answers": [{"question": 1, "answer": "yes", "evidence": "file:line"}], "verdict": "TRACE_CONFIRMED"}
  ],
  "apk_signer": {"checked": true, "subject": "CN=...", "sha256": "..."},
  "probe_changes": [
    {"file": "path", "reason": "why the harness needed it", "change": "one-line summary"}
  ],
  "new_observations": [
    "anything unexpected seen while running, with file:line"
  ],
  "default_suites": {"backend": "N passed", "mobile": "N passed"}
}
```

`findings` must hold exactly one entry for each of the 33 ids in section 2, including the one `new.` id.

**`VALIDATION-RESULTS.md`** is the human summary:

1. A one-paragraph headline with counts per verdict.
2. A table with one row per finding: id, verdict, evidence level, and a one-line reason.
3. Every INCONCLUSIVE and NOT_RUN finding, with what blocked it.
4. The measurement numbers.
5. The trace answers.
6. Every probe change, and every new observation.

Put each full sentence on its own line, and use a plain hyphen, never an em dash.
