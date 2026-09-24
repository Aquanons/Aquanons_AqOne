# Implementation Plan: Security audit remediation

Created: 2026-09-23T13:00:00+08:00
Updated: 2026-09-23T13:15:27+08:00
Revision: 2
Status: Approved
**Execution mode:** hard-stop
Feature spec and revision: `docs/security-audit/validation-results.json` run `20260923T1233` (verdicts re-checked by Claude against the raw JUnit/JSONL), `docs/security-audit/PROBES.md`
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`
Len's chat approval: Revision 2 approved by Len in chat, 2026-09-23T13:15:27+08:00
Target branch: `fix/security-audit-remediation`, created from `master` at `35a7822`
Revision 2: rebased on `35a7822` (PR #71 resolved-card warning line, PR #72 rebuilt APK); verification assets were written against `ef6cc7d` and still behave the same (backend untouched, mobile 259 passed, Dart probes 1 passed / 5 failed as before).
Implementer: Antigravity (Gemini). Reviewer: Claude Code.

## Scope

Fix the confirmed findings from the verification run.
Each requirement below names the probe that must turn from red to green; the probes are the acceptance tests.

Decisions Len made on 2026-09-23:

- Operator sessions get a server-side check (SEC-12).
- Location: coarsen weather coordinates to about 0.1 degrees and disclose weather and map tile use (SEC-24, SEC-25).
- LoRa: move `LOAM_KEY` out of committed source now; per-device keys are deferred (SEC-27).
- Fishing hotspots are out of scope for now.

Design choices Claude made (Len may override at approval):

- An SOS is never refused. Untrusted claims inside it are ignored instead, and the dispatcher feed is never truncated.
- No rate limit on SOS ingest: phones behind carrier NAT share IPs, and a throttle could drop a real distress call.
- Mesh chat retention is 30 days.
- Android release builds fail without the release keystore instead of silently using the debug key.

### Out of scope, and probes that stay red

| Finding | Why | Probe left red |
|---|---|---|
| backend.hotspots.minimum-cohort-policy-drift | Len: not now | `test_hotspot_cell_needs_five_distinct_reporters` |
| firmware.loam.shared-default-key (per-device part) | Deferred to roadmap; radios untested (build step 2) | `test_loam_signature_key_is_selected_per_source_id` |
| firmware.buoy.sos-queue-untrusted-capacity | Needs a bench test on hardware (Daniel) | none (trace only) |
| firmware.buoy.chat-starves-sos-tx-ring (runtime part) | The ring change here is static; starvation timing needs a bench test | none after SEC-30 |
| Fisher reply when the phone has no internet at all | No buoy reply route exists; product gap, not a regression | none |

### Requirements

| ID | Finding | Acceptance probe |
|---|---|---|
| SEC-01 | new.backend.anomaly.jsonb-parameter-encoding | `test_probe_anomaly.py::test_one_ordinary_live_trip_evaluates_on_real_postgres` |
| SEC-02 | backend.ai.anomaly.zero-contact-poison-run | `test_probe_anomaly.py` zero-contact probes (3) |
| SEC-03 | backend.contacts.optional-position-crash | `test_probe_anomaly.py::test_contact_without_coordinates_does_not_abort_fleet_evaluation` |
| SEC-04 | backend.contacts.future-timestamp-anomaly-suppression | `test_probe_ingest_trust.py::test_contact_ingest_rejects_a_day_ahead_timestamp` + control |
| SEC-05 | backend.ai.anomaly.authenticated-whole-fleet-recompute | `test_probe_anomaly.py::test_measure_whole_fleet_evaluation_cost` (MEASURE: must run and record numbers) |
| SEC-06 | backend.sos.untrusted-provenance-claims | `test_probe_sos.py` provenance probes (2) |
| SEC-07 | backend.sos.anonymous-incidents-crowd-dispatch-feed | `test_probe_sos.py::test_genuine_sos_survives_a_burst_of_anonymous_sos` |
| SEC-08 | backend.vessel-profile.unbound-owner-write | `test_probe_unauth_routes.py::test_anonymous_caller_cannot_replace_an_existing_vessel_identity` |
| SEC-09 | backend.trips.unbound-public-access | `test_probe_unauth_routes.py::test_trip_route_requires_a_bound_principal` (3) |
| SEC-10 | backend.warning-delivery.unbound-state-authority | `test_probe_unauth_routes.py::test_warning_delivery_route_requires_an_authority` (2) |
| SEC-11 | backend.catch.global-idempotency-cross-vessel-write | `test_probe_catch.py` |
| SEC-12 | backend.operator-jwt.no-server-revocation | `test_probe_auth.py::test_token_for_an_account_that_no_longer_exists_is_rejected` |
| SEC-13 | backend.auth.login-timing-enumeration | `test_probe_auth.py::test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password` |
| SEC-14 | backend.ai.squall.flag-authorizes-live-model-replacement | `test_probe_auth.py` squall probes (2) + control |
| SEC-15 | backend.public-sea-condition.operator-identity-disclosure | `test_probe_public_disclosure.py::test_public_sea_condition_does_not_expose_operator_account` |
| SEC-16 | backend.current-ingest.unbound-calibration-claim | `test_probe_ingest_trust.py::test_request_text_cannot_mark_a_current_reading_qualified` |
| SEC-17 | backend.demo-weather.unbounded-coordinate-expansion | `test_probe_resource_bounds.py::test_demo_weather_rejects_ten_thousand_coordinate_cells` |
| SEC-18 | backend.public-squall.unbounded-history-load | `test_probe_resource_bounds.py::test_public_squall_does_not_load_week_old_readings` |
| SEC-19 | backend.mesh.unbounded-public-storage | `test_probe_resource_bounds.py::test_mesh_chat_has_a_retention_or_admission_control` |
| SEC-20 | mobile.sos.standdown-intent-treated-resolved | `sos_probes_test.dart` stand-down group (2) + control |
| SEC-21 | mobile.sos.buoy-only-reply-unroutable | backend half in `test_probe_sos.py` + handset half in `sos_probes_test.dart`, both rescoped in Phase 4 |
| SEC-22 | mobile.eta.server-clock-discarded | `sos_probes_test.dart` ETA probe |
| SEC-23 | mobile.squall.ack-survives-missed-clear | `squall_probes_test.dart` |
| SEC-24 | mobile.location.undisclosed-weather-coordinate-egress | New Dart test (Phase 4) + trace T1 re-answered |
| SEC-25 | mobile.map.undisclosed-location-derived-tile-egress | Trace T2 re-answered (disclosure only) |
| SEC-26 | firmware.shore.committed-uplink-credential | `test_probe_repo_static.py::test_shore_sketch_holds_no_concrete_credential` (3) |
| SEC-27 | firmware.loam.shared-default-key (key out of source) | `test_probe_repo_static.py::test_loam_key_is_not_the_repository_default` |
| SEC-28 | firmware.shore.tls-peer-verification-disabled | `test_probe_repo_static.py::test_shore_verifies_the_backend_certificate` |
| SEC-29 | firmware.warning.missing-revision-tombstone | `test_probe_repo_static.py::test_buoy_warning_cache_orders_updates_by_revision` |
| SEC-30 | firmware.buoy.chat-starves-sos-tx-ring | `test_probe_repo_static.py::test_tx_ring_keeps_capacity_for_distress_frames` |
| SEC-31 | new: the two `AqOneLoam.h` copies differ (2 leading spaces, shore line 1) | `test_probe_repo_static.py::test_loam_control_headers_are_byte_identical` |
| SEC-32 | mobile.release.debug-signing-fallback | `test_probe_repo_static.py` signing probes (2) |
| SEC-33 | Operations: credentials and flags that live outside the repo | Len's checklist in Phase 6 |

## Rules for every phase

1. Read root `HANDOFF.md` and this plan; run `git status` and compare against the handoff before the first edit.
2. **Contract first.** If a phase changes a shared contract (`docs/02` to `docs/06`), edit that doc in the same phase before the code, and name the affected owner in the evidence (Daniel: `docs/02`, Arnold: `docs/04`/`docs/05`, Jade: mobile).
3. **Probes are the acceptance tests.** Do not edit a probe's assertion, expected value, or safe-behaviour condition. The only authorized probe changes are the ones this plan names (Phase 4, SEC-20 and SEC-21). Log any harness-only fix in the evidence file.
4. Root-cause fixes. Grep every caller of a function you change and fix the shared function once.
5. No em dashes. No new dependencies unless a task names one. New UI text goes in `mobile/lib/l10n/app_en.arb` with an `@key` description, plus `app_fil.arb` and `app_akl.arb` drafts.
6. Never print, copy, or commit a secret value. Name secrets by key only.
7. **Never edit an old migration.** New migrations continue from `029`.
8. Stage only the phase's paths (`git add <paths>`, never `git add -A`); inspect `git diff --cached`; commit with the phase message and no agent co-author line. Do not push.
9. `hard-stop`: after each phase's verification, update the evidence file and `HANDOFF.md`, then stop and wait for Len.
10. Three-attempt limit per failing gate, as in `AGENTS.md`. Then stop and write a failure report into `HANDOFF.md`.

### Shared commands

Backend default gate (PowerShell, from `backend/`):

```powershell
.\.venv\Scripts\Activate.ps1
Remove-Item Env:DATABASE_URL, Env:AQONE_SECURITY_PROBES -ErrorAction SilentlyContinue
python -m ruff check .
python -m pytest -q -p no:cacheprovider
```

Probe gate (from `backend/`; Postgres as in `PROBES.md` section 3 step 2, container `aqone-probe-pg` on port 55432):

```powershell
$env:AQONE_SECURITY_PROBES = '1'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:probe@localhost:55432/postgres'
python -m pytest tests/security_probes -p no:cacheprovider -rA --junitxml=../docs/security-audit/probe-runs/phase-N/backend-junit.xml
Remove-Item Env:AQONE_SECURITY_PROBES, Env:AQONE_PROBE_PG_ADMIN_URL
```

Mobile gate (from `mobile/`): `flutter analyze`, `flutter test`, `flutter test test_security_probes`.
Web gate (from repo root): `node --test web/test/*.test.js`, then `Get-ChildItem web/js, web/test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }`.

Evidence file: `docs/security-audit/REMEDIATION-EVIDENCE.md`, one section per phase with commands, counts, the red/green probe list, and limitations.

## Phase 0: Branch and baseline

Requirements: none (setup)
State: Completed

### Tasks

- [x] `git switch -c fix/security-audit-remediation` from `master`.
- [x] Stage the verification assets as they are: `backend/tests/conftest.py`, `backend/tests/security_probes/`, `mobile/test_security_probes/`, `docs/security-audit/PROBES.md`, `docs/security-audit/VALIDATION-RESULTS.md`, `docs/security-audit/validation-results.json`, `docs/security-audit/probe-runs/20260923T1233/`, and this plan.
- [x] Before staging, confirm the raw run files contain no credential value (they were redacted by Claude; re-check by searching for the `UPLINK_PASS` and `GATEWAY_API_KEY` values without printing them).

### Verification

- [x] Backend default gate: 387 passed.
- [x] Mobile gate: run `flutter gen-l10n` first (the generated `lib/l10n/app_localizations*.dart` files are gitignored and go stale after a pull), then 259 passed.
- [x] Probe gate: 40 failed, 3 passed (the 2026-09-23 baseline).

Checkpoint message: `test(security): add audit verification probes and results`

## Phase 1: Anomaly evaluation works on real Postgres

Requirements: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05
State: Completed

### Tasks

- [x] SEC-01: `profile.to_json()` returns a dict and `factors`/`reasons` are lists, but asyncpg without a codec wants a `str` for `$N::jsonb`. Follow the repo's existing convention (`json.dumps` at the call site, as `trips.py` and `advisories.py` do) in `app/ai/anomaly_service.py`. Then grep every `::jsonb` parameter under `backend/app` (`demo/scenarios.py`, `simulation/generator.py`, `audit.py` included) and make each argument a `str`. Do not register a global codec: existing reads `json.loads` string results.
- [x] SEC-01: make sure non-JSON values inside factors (datetimes) serialise; use ISO strings, not `default=str` on unknown types.
- [x] SEC-02: in `evaluate_and_persist`, run the whole evaluation inside `async with conn.transaction():` so a failure commits nothing. Handle eligible trips with zero contacts: fall back to the fleet profile when `profiles` has no entry for the vessel, and write `last_contact_at` from the trip's `departure_at`, then `reported_at`, then `as_of` (the column is `NOT NULL`). Check `_upsert_case` and `score_trip` for the same empty-list assumption.
- [x] SEC-03: in `_load_trip_rows`, use the buoy's position when the contact has none (`COALESCE(bc.latitude, b.lat)`, same for longitude). In `_group_latest_trips`, skip any row whose coordinates are still `None`, so one row can never abort the fleet.
- [x] SEC-04: move `current_events.py`'s `_reject_future_clock_skew` validator (5-minute skew) somewhere both models can import it, and apply it to `ContactEventIn.observed_at`. Update `docs/04_INGEST_API.md` "Contact events" with the rule.
- [x] SEC-05: no code change. Run the measure probe and record its numbers in the evidence file.
- [x] Add a unit test in `backend/tests/` for each of SEC-02, SEC-03 and SEC-04 in the existing fake-pool style, so the default suite also guards them.

### Verification

- [x] Backend default gate passes.
- [x] Probe gate: every SEC-01 to SEC-04 probe passes, and the SEC-05 measure probe passes with metrics recorded.
- [x] Evidence: Phase 1 section in `REMEDIATION-EVIDENCE.md`.

Checkpoint message: `fix(anomaly): make evaluation atomic and robust on real Postgres`

## Phase 2: Distress path integrity

Requirements: SEC-06, SEC-07, SEC-08, SEC-09, SEC-10, SEC-11
State: Completed

### Tasks

- [x] Contracts first: update `docs/04_INGEST_API.md` (SOS buoy provenance needs `X-Api-Key`, warning delivery needs `X-Api-Key`) and `docs/05_PUBLIC_API.md` (trips auth, vessel-profile overwrite rule, delivery read is operator-only, the `/api/sos/active` feed is untruncated).
- [x] SEC-06 in `app/api/sos.py` `ingest_sos`: the endpoint stays unauthenticated and never rejects.
  - Store `trust_tier='self_declared'` unless the request carries a valid vessel device bearer for the same `vessel_id`; then allow `phone_verified`. Never accept `confirmed_by_responder` from ingest.
  - Accept `source='buoy'`, `buoy_id`, `src_id`, `seq` only with a valid `X-Api-Key` (reuse `require_gateway_key`'s comparison as a non-raising helper). Without it, store the SOS as a direct delivery and drop the buoy fields, so no buoy row is auto-registered.
- [x] SEC-07: remove `LIMIT 100` from `active_sos` so every unresolved incident is returned. Check the dashboard (`web/js/dashboard/dashboard-live-sos.js`) renders a long list without breaking.
- [x] SEC-08 in `app/api/vessel_profile.py`: an unauthenticated POST may create a profile or fill blank fields, but changing a non-blank identity field needs a vessel device bearer bound to that `vessel_id`; otherwise answer 409 and change nothing. In `mobile/lib/services/backend_client.dart` `registerVesselProfile`, send the vessel bearer when one exists (`_withVesselAuth`).
- [x] SEC-09 in `app/api/trips.py`: GET routes need an operator (`require_user`). POST and PATCH need either an operator with a responder role, or a vessel device bearer whose vessel matches the trip. No client calls these routes today (checked: `mobile/lib`, `web/js`, firmware), so nothing else changes.
- [x] SEC-10 in `app/api/advisories.py`: `POST /api/advisories/delivery` needs the gateway key (`require_gateway_key`), and `GET /api/advisories/{id}/deliveries` needs an operator (`require_user`). The shore firmware header lands in Phase 5; until then, gateway delivery posts get 401. That is acceptable because no gateway is deployed.
- [x] SEC-11: new migration `029_catch_logs_vessel_scoped_local_id.sql` drops `uq_catch_logs_local_id` and creates a unique index on `(vessel_id, local_id) WHERE local_id IS NOT NULL`. Update the `ON CONFLICT` target in `app/api/catch.py`, and grep for any other `ON CONFLICT (local_id)` on `catch_logs`.
- [x] Update the existing tests that asserted the old behaviour (for example `tests/test_vessel_profile.py`, `tests/test_sos_ingest.py`), and add default-suite tests for the new rules.

### Verification

- [x] Backend and web gates pass.
- [x] Probe gate: every SEC-06 to SEC-11 probe passes. The Phase 1 probes stay green.
- [x] `python migrate.py` applies `029` cleanly on a fresh probe database (the probe fixture does this).

Checkpoint message: `fix(sos): stop anonymous callers forging provenance or overwriting vessel data`

## Phase 3: Operator sessions and public disclosure

Requirements: SEC-12, SEC-13, SEC-14, SEC-15, SEC-16, SEC-17, SEC-18, SEC-19
State: Completed

### Tasks

- [x] Contracts first: `docs/05_PUBLIC_API.md` (logout route, session rules, squall train admin-only, public sea-condition `set_by_label`) and `docs/04_INGEST_API.md` (current `calibration_status`).
- [x] SEC-12, operator sessions:
  - Migration `030_user_token_version.sql`: `ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0`.
  - `create_token` adds a `ver` claim. `require_user` loads `id, email, role, token_version` for `sub` through `app.db.get_pool()` and returns 401 when the user is missing, the role differs from the claim, or `ver` differs (a missing `ver` counts as a mismatch, so old tokens need one re-login).
  - Add `POST /api/logout` (`require_user`), which increments `token_version`. Make the dashboard logout button (`web/js/profile.js` around line 280) call it best-effort before clearing local state.
  - Keep the lookup in one function in `app/auth.py`. In `backend/tests/conftest.py`, add one autouse fixture that stubs it to trust the claims, so existing fake-pool tests keep working. The fixture must not apply under `tests/security_probes/`, and there must be default-suite tests that exercise the real lookup.
- [x] SEC-13: in `app/api/auth.py` `login`, when the email is unknown, call `verify_password(payload.password, _DUMMY_HASH)` so both branches pay one bcrypt check. `_DUMMY_HASH` is a module constant bcrypt hash of a random throwaway string.
- [x] SEC-14: `POST /api/ai/squall/train` needs `require_admin_role` as well as `ALLOW_TRAINING`.
- [x] SEC-15: give `public_sea_condition` its own serializer. It returns `set_by_label` (the setter's `users.full_name` when present, otherwise `MDRRMO`) and never `set_by_user_id`, `set_by_name`, or an email. The protected dashboard route keeps `_serialise`. In `mobile/lib/models/sea_condition.dart`, read `set_by_label`, falling back to `set_by_name` for older backends, and update its tests.
- [x] SEC-16: in `app/api/current_events.py`, store `uncalibrated` when a request claims `qualified`, because the backend has no instrument or calibration registry to check the claim against. Keep `synthetic` as it is. Return the stored value.
- [x] SEC-17: cap `coordinates()` in `app/demo/weather.py` at 64 cells (`ValueError` above that). First confirm the handset's largest request (`mobile/lib/services/forecast_provider.dart`) is below 64.
- [x] SEC-18: give `_load_rows` in `app/api/squall.py` an optional lower bound on `observed_at` for readings. `public_squall` and any other live caller pass `now - 24 hours`; training (`live=False`) stays unbounded. Confirm `build_squall_status` still reports the last real observation time when the window is empty.
- [x] SEC-19: in `app/api/mesh.py` `ingest_chat`, delete `mesh_chat` rows older than 30 days in the same connection after the insert. Add migration `031_mesh_chat_created_at_index.sql` for an index on `created_at` if none exists.

### Verification

- [x] Backend, web and mobile gates pass.
- [x] Probe gate: every SEC-12 to SEC-19 probe passes, and Phases 1 and 2 stay green.
- [x] Manual check with a local server: log in on the dashboard, press logout, and replay the old bearer against `/api/me` (expect 401). Record the result in the evidence file.

Checkpoint message: `fix(auth): server-checked operator sessions and no operator identity in public feeds`

## Phase 4: Handset tells the truth

Requirements: SEC-20, SEC-21, SEC-22, SEC-23, SEC-24, SEC-25
State: Completed

### Tasks

- [x] SEC-20: a stand-down is resolved only once the backend has it.
  - Persist a `fisher_reply_synced` flag in the outbox (bump the `AppDatabase` schema version with a migration).
  - Set it when `replyToSos`, `standDown`, or the reconcile flush gets HTTP 200, or when the backend reports `fisher_reply` or `resolved_at`.
  - `isStoodDown` becomes `fisherReply == 2 && fisherReplySynced`.
  - While a stand-down is unsynced, the UI shows a pending message (new ARB keys in en/fil/akl) instead of "MDRRMO was told".
  - `DeliveryStateTile` (PR #71) shows "Still in danger? Send another SOS." whenever `record.isResolved`; after this change it must appear only for a synced stand-down or a responder resolve, so extend `test/widget_test.dart` with the pending case.
  - Authorized probe change: if the stand-down control's fake backend needs a realistic reply body (`{"ok": true, "resolved_at": ...}`), update that fake only.
- [x] SEC-21: buoy-only SOS replies.
  - Before an un-credentialed handset replies to a record the backend has not confirmed as `delivered` over the direct path, it re-posts the same SOS directly (`BackendClient.postSos`). This is idempotent on `(vessel_id, client_ts)`, and the backend's `COALESCE` then records the `local_id`, so `POST /api/sos/reply/{local_id}` matches.
  - Put the re-post in the reply path in `SosService`, used by `replyToSos`, `standDown`, and the reconcile flush.
  - Authorized probe changes, both halves:
    - `test_probe_sos.py::test_handset_reply_reaches_an_sos_that_arrived_only_over_the_buoy`: after the keyed buoy ingest, POST the same SOS directly with `local_id`, then reply by that `local_id`. Keep the `fisher_reply == 2` assertion.
    - In the `sos_probes_test.dart` handset half, the fake backend answers `POST /api/sos` with 200 and records the `local_id`, and answers `/api/sos/reply/{local_id}` with 200 only for a recorded `local_id` (otherwise 404). Keep `expect(ok, isTrue)`.
- [x] SEC-22: ETA against server time.
  - Parse `server_time` from the backend envelopes (`vesselSos`, `ackByLocalId`) into `RemoteSos`, and from the buoy status response if the firmware provides it.
  - In `_applyRemote`, store the ETA converted to the device clock: device now plus (`eta_at` minus `server_time`). Without `server_time`, keep today's behaviour.
- [x] SEC-23: squall identity.
  - Backend: add `onset_at` (ISO) to the squall status when the level is `watch` or `return_now`, from the propagation onset anchor. Record it in `docs/05_PUBLIC_API.md` first.
  - Mobile: `SquallWatch.identity` becomes the sorted buoys plus `onset_at`. Without `onset_at`, use the sorted buoys plus `observed_at` floored to a 3-hour UTC bucket, so a later squall alarms again after a missed clear.
- [x] SEC-24: round the coordinates `forecast_provider.dart` sends (AqOne backend and Open-Meteo) and stores (`forecast_record_v2`) to 1 decimal place. Add a Dart test that records the outgoing URIs with a fake HTTP client.
- [x] SEC-24 and SEC-25: update the privacy text in `mobile/lib/ui/info_page.dart` (`InfoCopy.privacy`). Say that weather forecasts use your approximate location (about 11 km), and that the online map fetches tiles for the area you are viewing from OpenStreetMap. Keep "Position is only sent as part of an SOS you deliberately send" true by scoping it to precise position. `InfoCopy` is English-only today; moving it to ARB is out of scope, so note that in the evidence.

### Verification

- [x] Mobile gate passes, including all 7 Dart probes and the new tests.
- [x] Backend gate and probe gate pass (the SEC-21 backend half and the SEC-23 backend field).
- [x] Traces T1 and T2 from `PROBES.md` are re-answered in the evidence file.

Checkpoint message: `fix(mobile): honest stand-down, routable replies, server-relative ETA, coarse weather location`

## Phase 5: Firmware hardening

Requirements: SEC-26, SEC-27, SEC-28, SEC-29, SEC-30, SEC-31
State: Completed

### Tasks

- [x] Contract first: `docs/02_LOAM_PACKET_SPEC.md` gets the WARN `rev` field (SEC-29). Tell Daniel in the evidence file.
- [x] SEC-31: remove the two leading spaces on line 1 of `firmware/shore/AqOneShore/AqOneLoam.h`; the `diff` of the two copies must print nothing.
- [x] SEC-26 and SEC-27: move `UPLINK_SSID`, `UPLINK_PASS`, `GATEWAY_API_KEY` (shore) and `LOAM_KEY` (both) into a gitignored `AqOneSecrets.h` next to each sketch. Commit an `AqOneSecrets.h.example` with placeholders. Add `#error` when the header is missing or `LOAM_KEY` equals the old default. The shared `AqOneLoam.h` includes the secrets header, so both copies stay byte-identical. Add the ignore rules to `.gitignore` and update `firmware/README.md`.
- [x] Shore: send `X-Api-Key: GATEWAY_API_KEY` on the SOS post (`AqOneShore.ino` around line 179) and the warning-delivery post (around line 612), matching Phase 2.
- [x] SEC-28: replace `client.setInsecure()` with `client.setCACert(...)` holding the root CAs for the backend host (look up what `aqone-backend.onrender.com` currently chains to; include both the current root and one backup). Document the expiry and rotation in `firmware/README.md`.
- [x] SEC-29: the shore adds `rev` (the advisory's `updated_at` as epoch seconds from the backend feed) to each WARN payload. The buoy keeps `rev` per cached warning and ignores a frame whose `rev` is not newer. Check the backend advisory feed the shore reads exposes `updated_at`; if not, add it there and to `docs/05`.
- [x] SEC-30: `txEnqueue` takes a `reserve` count: chat frames need more than 2 free slots, and distress, ACK and WARN frames may use any slot. Update both `AqOneLoam.h` copies identically.

### Verification

- [x] `diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h` prints nothing.
- [x] Compile both environments with no warnings, using example secrets copied to `AqOneSecrets.h` in a scratch step (never committed): create a venv outside the repo, run `python -m pip install platformio`, then `pio run -d firmware`. If PlatformIO cannot be installed or build the boards, record that exactly and stop for Len; do not skip the gate.
- [x] Probe gate: SEC-26 to SEC-31 probes pass. `test_loam_signature_key_is_selected_per_source_id` stays red (deferred).
- [x] `git status` shows no `AqOneSecrets.h` staged.
- [ ] Hardware check for Daniel (not a Gemini gate): flash both boards, send one SOS and one warning over the bench mesh, and confirm TLS to the backend.

Checkpoint message: `fix(firmware): secrets out of source, verified TLS, warning revisions, SOS-first transmit ring`

## Phase 6: Release signing, probe promotion, and operations handover

Requirements: SEC-32, SEC-33
State: Approved, not started

### Tasks

- [ ] SEC-32: in `mobile/android/app/build.gradle.kts`, remove the release fallback to the debug signing config. With no `key.properties`, the release build fails with a message pointing at `mobile/README.md`. Update `mobile/README.md`: teammates without the key use `flutter build apk --debug`.
- [ ] SEC-32: `git rm mobile/releases/aqone-release.apk` and update `SHA256SUMS.txt`. Coordinate with Jade first: the `release/apk-master-*` branches (PRs #70, #72) keep committing debug-signed APKs (re-checked on `35a7822`), so the release workflow must move to the release key or stop committing APKs. **Len-gated:** Len builds and adds a release-key-signed APK. Anyone with the debug-signed build must reinstall, which clears the local SOS outbox, so tell testers first.
- [ ] Move every probe that is now green and needs no Postgres into `backend/tests/` (for example `backend/tests/test_security_regressions.py`), so the default suite guards them. Postgres probes and the deferred red probes stay behind `AQONE_SECURITY_PROBES`.
- [ ] Add an accepted-risk entry to `docs/16_QA_DISCLOSURES.md` for each deferred item in the Scope table.
- [ ] Write Len's operations checklist into the evidence file (SEC-33): rotate `GATEWAY_API_KEY` on Render and re-flash the shore; change the uplink WiFi password; set a real `LOAM_KEY` before any field flash; confirm `ALLOW_TRAINING` is unset on Render; decide whether to rewrite git history (recommended: no, because rotation makes the old values worthless).

### Verification

- [ ] All four gates pass (backend, probe, mobile, web).
- [ ] Final probe gate: only the deferred probes are red (the hotspot pair and the per-source LoRa key).
- [ ] `flutter build apk --release` fails without `key.properties` and names the fix.

Checkpoint message: `chore(release): require release signing and promote security regressions`

## Recovery

Follow `AGENTS.md` for the three-attempt limit and immediate blockers.
Record unresolved work and attempt counts in `HANDOFF.md`.
Interrupted or failing work stays uncommitted and the phase stays incomplete.
Stop and ask Len for: a gate blocked by missing tools or access, a finding whose fix would change a design decision recorded above, or any probe that seems to assert the wrong thing.
