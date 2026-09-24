# Track B - Backend (edge-case remediation)

Master plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` (read Sections 1 to 4 first).
Design: `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md`.
**Execution mode:** auto (master plan Section 4.1: continue through phases without sign-off; never merge)
Branch and worktree: `edge/backend`, `../AqOne-edge-backend`
Owns: `backend/**`, `render.yaml`.
Approved: with the master plan, Revision 1, 2026-09-24.
Len's chat approval, 2026-09-25T00:05:00+08:00: tracks B, M and W run in `auto` mode - agents continue through their phases without per-phase sign-off, under master plan Section 4.1.
Evidence: `docs/edge-remediation/EVIDENCE-backend.md`.
State: In progress (auto mode)

## Rules for this track

- **Architecture.**
  New business policy goes in `backend/app/incidents/` as pure functions: no `fastapi`, `asyncpg`, `httpx` or `app.db` imports.
  `app/api/*.py` stays a humble adapter: parse, call policy, run SQL, audit.
  SQL stays in the adapters, with no repository classes or interfaces.
- **Clean code.**
  - One concept, one name: the contract names in master plan Section 3 are the names in code.
  - Small functions, each at one level of abstraction.
  - No boolean mode flags.
  - Comments only for rationale.
  - When a phase touches a function that duplicates another, merge them, as in B1's single event serializer.
- **Tests first.**
  Every phase starts by writing its listed tests.
  Record the red run (command and failing test names) in the evidence file before changing `app/`.
- **Postgres tests.**
  Tests that depend on real SQL behaviour (partial unique indexes, `ON CONFLICT`, advisory locks) use the `probe_db` fixture and are named `test_edge_*_pg.py`.
  They skip when `AQONE_PROBE_PG_ADMIN_URL` is unset.
- **Migrations** are new numbered files from `032`, never edits to old ones.
- **Gate commands** (every phase), run from `backend/`:

  ```powershell
  python -m ruff check app tests
  python -m pytest -q -p no:cacheprovider
  $env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres:<local-pw>@localhost:55432/postgres'
  python -m pytest -q -p no:cacheprovider tests/
  $env:AQONE_SECURITY_PROBES = '1'; python -m pytest -q -p no:cacheprovider tests/security_probes
  ```

  The expected security-probe result is unchanged from `docs/security-audit/REMEDIATION-EVIDENCE.md` Phase 6: only the deferred probes are red.

---

## Phase B1: Incident lifecycle - reasons, versions, reopen

Requirements: EC-C7 (backend), EC-M8, EC-M9 (backend), EC-M10 (backend), EC-M1
Merge after: Phase 0
State: Done - 059b3b0

### Tasks

- [x] Move the `probe_db` fixture from `tests/security_probes/conftest.py` to `tests/conftest.py`, unchanged, so both suites share it.
  Confirm the security probes still collect and run.
- [x] Write red tests:
  - `tests/test_incident_lifecycle.py` (pure):
    - every `ResolutionCode` value
    - `resolution_code_from(None)` returns `UNSPECIFIED`
    - `fisher_reply_reopens(resolved_at, reply, now)` is true only for `STILL_IN_DANGER` within 2 h
    - `can_reopen(resolved_at)`
  - `tests/test_incidents_is_pure.py`: imports every module in `app/incidents/`, and fails if any of them imports `fastapi`, `asyncpg`, `httpx` or `app.db` (check each module's `__dict__` for module objects).
  - `tests/test_edge_lifecycle_pg.py`:
    - `test_resolve_without_reason_stores_unspecified`
    - `test_resolve_with_reason_code_is_returned_in_vessel_feed` (`/vessel/{id}` and `/ack/{local_id}` both carry `resolution_code`)
    - `test_reopen_restores_active` (the incident is back in `/active` and `/downlink`, and an audit row `sos.reopen` exists)
    - `test_reopen_of_open_incident_is_no_change`
    - `test_ack_with_stale_version_conflicts` (409, `detail == "version_conflict"`, body carries the current event)
    - `test_transport_merge_does_not_bump_version`
    - `test_still_in_danger_reopens_within_two_hours` (both reply routes)
    - `test_still_in_danger_after_window_stays_resolved`
  - `tests/test_responder_loop.py` additions: `test_responder_note_over_40_bytes_rejected` (40 `ñ` characters is 80 bytes, so 422 `responder_note_too_long`) and `test_responder_note_of_40_bytes_accepted`.
- [x] Add `migrations/032_incident_lifecycle.sql`:
  - `sos_events.version INT NOT NULL DEFAULT 0`
  - `resolution_code TEXT` with a CHECK on the six codes, or NULL
  - `reopened_at TIMESTAMPTZ`
  - `reopened_by TEXT`
- [x] Create `app/incidents/__init__.py` (empty) and `app/incidents/delivery.py`.
  Move `_delivery_state` there as the public `delivery_state(row)`; `sos.py` imports it.
- [x] Create `app/incidents/lifecycle.py` containing:
  - `ResolutionCode(StrEnum)` with the six codes
  - `REOPEN_WINDOW = timedelta(hours=2)`
  - `resolution_code_from(raw)`
  - `fisher_reply_reopens(resolved_at, reply, now)`
  - `can_reopen(resolved_at)`

  There is no display text here; the phone and dashboard localise the codes.
- [x] In `app/api/sos.py`:
  - Add one `_event_json(row, server_time)` serializer, used by `/ack/{local_id}`, `/vessel/{id}` and `/downlink`, replacing the three hand-written dicts.
    It adds `version`, `resolution_code` and `reopened_at`.
  - `AcknowledgeIn`: add `expected_version: int | None`, and a validator limiting `responder_note` to 40 UTF-8 bytes.
    Acknowledge runs `version = version + 1` inside `WHERE id = $1 AND ($n::int IS NULL OR version = $n)`.
    When no row matches and the event exists, return 409 with the current event.
  - `ResolveIn`: add `reason_code: ResolutionCode | None` and `expected_version`.
    Store `resolution_code_from(reason_code)`, apply the same version rule, and keep the existing audit.
  - Add `POST /{event_id}/reopen` on `protected_router` with `require_responder_roles`.
    Clear `resolved_at`, `resolved_by` and `resolution_code`, set `reopened_at = NOW()` and `reopened_by = email`, bump the version, and audit `sos.reopen`.
    An open incident returns `outcome = "no_change"`.
  - In both fisher reply routes, keep the frozen-after-resolve rule except when `fisher_reply_reopens(...)` is true.
    In that case reopen with `reopened_by = 'fisher'` and store the reply.
    Lifecycle writes bump the version; transport merges in `ingest_sos` do not.

### Verification

- [x] The gate commands (above) are green.
- [x] B1 red and green runs are recorded in the evidence file.
- [x] Migration 032 applies on fresh probe databases (`tests/test_migrate.py` passes).

### Review and checkpoint

- [x] Diff review: `sos.py` is shorter net of the new route; lifecycle policy is outside SQL.
- [x] Update this file's checkboxes, the evidence file and `HANDOFF.md`.
- [x] Stage only `backend/**` and this track's docs; commit; do not open a PR (Section 4.1).

Checkpoint message: `feat(sos): resolution reasons, reopen, and versioned incident writes`

---

## Phase B2: Incident nonce and safe text

Requirements: EC-C14, EC-L13, EC-L8, EC-C8 (backend), EC-H17 (backend)
Merge after: B1
State: Done - 32a1635

### Tasks

- [x] Write red tests:
  - `tests/test_sos_text.py` (pure), for `truncate_utf8(text, max_bytes)`:
    - ASCII is unchanged
    - `ñ` straddling the limit is dropped whole
    - a 4-byte emoji at the boundary is dropped whole
    - the result always has `len(result.encode()) <= max_bytes`
    - an empty string stays empty
  - `tests/test_sos_ingest.py` additions: `test_sos_note_truncated_on_char_boundary` (a 70-byte note is stored as valid UTF-8 of 64 bytes or fewer, with 200 and not 422) and `test_sos_boat_truncated_to_32_bytes`.
  - `tests/test_edge_nonce_pg.py`:
    - `test_prepared_rows_cannot_capture_nonce_sos`: post 60 anonymous rows (no nonce) for the next 60 `client_ts` values with a fake position and chosen `local_id`s, resolve them via `/reply/{local_id}`, then post the real SOS with a nonce and a real position.
      Expect a new, unresolved row at the real position, and it appears in `/active`.
    - `test_same_second_different_nonce_two_rows`
    - `test_same_nonce_merges_across_transports` (direct plus a gateway-keyed `source=buoy` delivery give one row with both delivery flags)
    - `test_position_conflict_stores_alt_position` (second delivery more than 1 km away)
    - `test_close_positions_do_not_conflict` (500 m)
    - `test_legacy_without_nonce_still_merges_on_client_ts`
    - `test_vessel_feed_returns_all_unresolved` (25 unresolved plus 30 resolved returns 25 plus the newest 20 resolved)
- [x] Add `migrations/033_sos_nonce.sql`:
  - add `nonce BIGINT`, `alt_latitude DOUBLE PRECISION`, `alt_longitude DOUBLE PRECISION`
  - `CREATE UNIQUE INDEX uq_sos_events_vessel_nonce ON sos_events (vessel_id, nonce) WHERE nonce IS NOT NULL`
  - replace `uq_sos_events_vessel_client_ts` (from `007_sos_ingest.sql:47`) with a partial unique index on `(vessel_id, client_ts) WHERE nonce IS NULL`, so two nonce-carrying calls in the same second can coexist
- [x] Create `app/incidents/text.py` with `truncate_utf8(text, max_bytes) -> str`.
  Encode, cut at the byte limit, then decode with `errors='ignore'` so a partial trailing character is dropped.
- [x] In `SosIn`:
  - Add `nonce: int | None = Field(default=None, ge=0, le=4294967295)`.
  - Replace `max_length` on `note` and `boat` with `BeforeValidator`s that call `truncate_utf8` at 64 and 32 bytes.
  - Update the class docstring: truncation, not rejection.
- [x] Split `ingest_sos` so the handler reads top-down: resolve provenance, then upsert, then respond.
  - Extract `_upsert_sos(conn, payload, provenance)`, which picks the conflict target (`(vessel_id, nonce)`, or `(vessel_id, client_ts) WHERE nonce IS NULL` for legacy).
  - On conflict, set `alt_latitude` and `alt_longitude` from the incoming position only when both positions exist, no alternative is stored yet, and they differ by more than `CONFLICT_DEGREES = 0.009`.
    Explain in a `ponytail:` comment that this is about 1 km at 11 degrees N as a box test, with a haversine as the upgrade if the area of operation moves far from the equator.
  - The response adds `nonce`.
- [x] `/vessel/{id}` query: `WHERE vessel_id = $1 AND (resolved_at IS NULL OR id IN (newest 20 resolved))`, ordered newest first.
- [x] `_event_json` adds `nonce`.

### Verification

- [x] Gate commands green, with red and green runs recorded.
- [x] Manual: `curl -X POST /api/sos` with a 70-byte `ñ` note against a local server gives 200 and the stored note is valid UTF-8.

### Review and checkpoint

As in B1.
Checkpoint message: `feat(sos): end-to-end incident nonce and byte-safe distress text`

---

## Phase B3: Downlink cap and gateway last-seen

Requirements: EC-C10, EC-C2 (backend half), EC-H12 (visibility)
Merge after: B2
State: Done - 3dd0618

### Tasks

- [x] Write red tests:
  - `tests/test_downlink_policy.py` (pure), for `select_downlink(candidates, now)`:
    - never returns more than 12
    - band order is acknowledged-open, then unacknowledged-open, then resolved
    - latest change first within a band
    - synthetic rows are excluded
    - open rows unchanged for more than 24 h are excluded
    - resolved rows older than 6 h are excluded
  - `tests/test_edge_downlink_pg.py`:
    - `test_downlink_caps_and_orders_by_priority` (30 vessels in a mix of states)
    - `test_downlink_poll_records_gateway_last_seen`
    - `test_ops_status_reports_gateway_last_poll` (operator only; the gateway key gets 401)
- [x] Create `app/incidents/downlink.py` containing:
  - `DOWNLINK_MAX = 12`, `OPEN_WINDOW`, `RESOLVED_WINDOW`
  - `last_change(row)`: the latest of `created_at`, `acknowledged_at`, `resolved_at`, `reopened_at` and `fisher_replied_at`
  - `priority_band(row)`
  - `select_downlink(candidates, now)`

  A docstring states why 12: it is the smallest table on the path (gateway `MAX_VESSELS`, and buoy `MAX_TRACKED` after F1).
- [x] `sos_downlink()`: SQL fetches candidates (newest per vessel, non-synthetic, inside the widest window), then Python calls `select_downlink`.
  Remove `LIMIT 100`, and delete the old `DOWNLINK_RESOLVED_WINDOW_HOURS` constant in favour of the policy module.
- [x] Add `migrations/034_gateway_status.sql`: `gateway_status (gateway_key TEXT PRIMARY KEY, last_poll_at TIMESTAMPTZ NOT NULL)`.
  The downlink route upserts `'default'` on every poll.
- [x] Create `app/api/ops_status.py` with `GET /api/ops/status` (`require_user`), returning `gateway_last_poll_at` and `gateway_stale` (older than 135 s).
  B6 extends this route.
  Register it in `main.py` with the other protected routers.

### Verification

Gate commands green, with red and green runs recorded.

### Review and checkpoint

As in B1.
Checkpoint message: `feat(downlink): cap the radio feed to the smallest table and record gateway polls`

---

## Phase B4: Dispatcher triage, flags and late calls

Requirements: EC-H18, EC-H20, EC-H15 (backend), EC-M3, EC-L11 (backend flag), EC-H19 (data for wording)
Merge after: B2
State: Done - 4167f3d

### Tasks

- [x] Write red tests:
  - `tests/test_triage.py` (pure):
    - `triage_key` sorts unacknowledged before acknowledged, corroborated before not, then newest
    - `flood_status(events, now)` is active above 10 unknown vessels in 60 s
  - `tests/test_plausibility.py` (pure), for `flags(event, context)`:
    - `position_on_land` (a point on land per `app.geo.point_in_water`)
    - `position_beyond_radio_range` (pod-delivered, further from the gateway than the context's maximum range)
    - `position_jump` (more than 20 km from a contact within 1 h)
    - `many_calls_same_vessel` (3 or more open)
    - `position_conflict` (an alternative position is present)
    - no flags for a normal event
    - direct-path calls never get `position_beyond_radio_range`
  - `tests/test_edge_active_pg.py`:
    - `test_active_orders_known_vessel_above_flood` (500 anonymous calls plus 1 from a vessel with a `vessel_trips` row; the vessel is first)
    - `test_active_limit_and_total`
    - `test_active_marks_late_calls`
    - `test_active_counts_open_calls_per_vessel`
    - `test_active_reports_delivery_path`
- [x] Create `app/incidents/triage.py` (`triage_key`, `flood_status`) and `app/incidents/plausibility.py` (`flags`, plus a small frozen `PlausibilityContext` dataclass).
  The gateway position comes from the shore station in `app/geo.py`.
  The maximum range is one named constant taken from `docs/33_LORA_RF_BUDGET.md`, and the docstring cites the section.
  Reuse `app.geo.km_per_deg_lon` for distances; add `distance_km` to `app/geo.py` if it is missing, and do not duplicate the one in `app/ai/trip_profile.py`.
  Point `trip_profile` at it if the change is one line.
- [x] `active_sos`:
  - Add `limit: int = Query(200, ge=1, le=1000)`.
  - The query adds the open-calls count per vessel (window function), an `EXISTS` for trip history, and the latest contact within 1 h.
  - Python builds each event, attaches `pressed_at`, `is_late`, `flags`, `open_calls_for_vessel`, `alt_*`, `delivery_path` and `vessel_verified` (the tier is `phone_verified` or better; B5 extends this), sorts by `triage_key`, and slices to `limit`.
  - It returns `{events, total, flood}`.
  Keep the handler readable by extracting `_enrich(row, context)`.

### Verification

Gate commands green, with red and green runs recorded.
Also run a timing note: `/active` with 10,000 rows on local Postgres; record the milliseconds in the evidence file (not a gate).

### Review and checkpoint

As in B1.
Checkpoint message: `feat(sos): triage-ordered dispatcher feed with advisory plausibility flags`

---

## Phase B5: Chat authority, identity and trust

Requirements: EC-C9, EC-M12, EC-H21, EC-H10 (backend), EC-M6 (backend), EC-M2 (backend)
Merge after: B4
State: Done - 8dbb767

### Tasks

- [x] Write red tests:
  - `tests/test_chat_policy.py` (pure):
    - `sender_is_reserved` catches "MDRRMO", "mdrrm0", "M.D.R.R.M.O", "Coast Guard", "PCG", "PAGASA", "Admin" and "Official", and passes "Juan", "Mang Dodong" and "Bangka 7"
    - `chat_origin(credential)` for operator, vessel, gateway and anonymous
  - `tests/test_mesh_chat.py` additions:
    - `test_reserved_sender_refused` (422 `sender_reserved`)
    - `test_anonymous_post_forced_app_origin` (a posted `origin=mdrrmo` is ignored)
    - `test_operator_chat_is_official`
    - `test_chat_rate_limit_429` (the 7th post in 60 s)
    - `test_chat_read_requires_credential`
    - `test_gateway_can_read_chat`
  - `tests/test_edge_identity_pg.py`:
    - `test_enrolled_vessel_blank_fill_needs_device`
    - `test_unenrolled_blank_fill_records_anonymous`
    - `test_license_text_never_sets_tier` (`license_type="FishR"` gives `vessel_verified == false`)
    - `test_confirm_vessel_sets_tier_and_audits`
    - `test_profile_stores_shore_contact`
    - `test_refresh_accepts_recently_expired_token` (3 days past expiry)
    - `test_refresh_rejects_revoked_device`
    - `test_refresh_rejects_token_older_than_grace` (31 days)
- [x] Put chat policy in `app/mesh/chat_policy.py`, beside `loam.py`:
  - `normalise_sender(name)`
  - `sender_is_reserved(name)`
  - `chat_origin(credential_kind)`
  - `RateLimiter`, a token bucket keyed by `(normalised sender, client IP)`, 6 a minute.
    A `ponytail:` comment says it is in memory for a single instance and should move to Postgres if scaled out.
- [x] `app/api/mesh.py`:
  - `POST` resolves the credential (optional operator, optional vessel device, optional gateway key), sets origin and sender per master plan 3.6, checks reserved names and the rate limit, then inserts.
  - `GET` requires one of the three credentials.
  - Update the misleading "unauthenticated" comment in `main.py` next to the mesh router.
- [x] Add `migrations/035_vessel_identity_provenance.sql`: `vessels` gains `phone_set_by TEXT`, `license_set_by TEXT`, `shore_contact_name TEXT`, `shore_contact_phone TEXT`, `confirmed_at TIMESTAMPTZ` and `confirmed_by TEXT`.
- [x] Create `app/incidents/trust.py` with `vessel_verified(has_active_device, confirmed_at)`, pure.
  `/active` uses it and adds `phone_set_by`, `shore_contact_name` and `shore_contact_phone`.
- [x] `app/api/vessel_profile.py`:
  - Any write to a vessel with an active, unrevoked device requires that device's bearer.
  - Otherwise, blank fills record `*_set_by = 'anonymous'`, and device writes record `'device'`.
  - Accept `shore_contact_name` (64 characters or fewer) and `shore_contact_phone` (20 or fewer).
  - Add `POST /api/vessels/{vessel_id}/confirm` on a protected router (responder roles, audited `vessel.confirm`).
- [x] `app/auth.py`: add `decode_vessel_device_token(token, *, expired_grace)`, reusing `decode_token`'s key and algorithm with PyJWT `leeway`.
  `POST /api/vessel-auth/refresh` uses a 30-day grace and still checks the device row is not revoked.

### Verification

- [x] Gate commands green, with red and green runs recorded.
- [x] The security probes stay at their Phase 6 result.
  Pay particular attention to SEC-08 and SEC-19: SEC-08's 409 rule must still hold for unenrolled vessels with non-blank fields.

### Review and checkpoint

As in B1.
Checkpoint message: `feat(identity): official-only MDRRMO chat, device-bound profiles, responder confirmation`

---

### Green verification

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 501 passed, 39 skipped, 1 xfailed.
- PostgreSQL 18 full suite: 535 passed, 5 skipped, 1 xfailed.
- Migration checks: 5 passed; migration 035 applied by PostgreSQL tests.
- Focused B5 policy/API checks: 73 passed; identity/profile PostgreSQL checks: 13 passed.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed, 0 errors. The same two Phase 6 hotspot cohort probes and firmware shared LoRa key probe remain deferred.

## Phase B6: Scheduler, SMS escalation, ops status, operator refresh

Requirements: EC-C6 (backend), EC-H6 (schedule), EC-C5 (expiry data), EC-M18
Merge after: B3
State: Done - fc77aad

### Tasks

- [x] Write red tests:
  - `tests/test_escalation.py` (pure), for `due_for_escalation(events, now)`:
    - unacknowledged, non-synthetic, open, older than 2 min, with no `escalated_at`: due
    - acknowledged, synthetic, resolved or already escalated: not due
    - `escalation_text(event)` is 160 characters or fewer and names the vessel, position and time
  - `tests/test_notify.py`: the Semaphore adapter posts the right form to `https://api.semaphore.co/api/v4/messages` (use `httpx.MockTransport`), and returns `NotifyResult.NOT_CONFIGURED` with no network call when `SEMAPHORE_API_KEY` or `ONCALL_SMS_NUMBERS` is unset.
  - `tests/test_edge_scheduler_pg.py`:
    - `test_scheduler_single_runner` (two concurrent `run_job_once` calls; exactly one executes, via `pg_try_advisory_lock`)
    - `test_escalation_marks_and_audits` (`escalated_at` set, and audit `sos.escalate` with outcome `sent` or `not_configured`)
    - expiry and SMS status assertions in `test_ops_status_reports_database_expiry_and_sms_configuration`
    - SMS configured status assertion in `test_ops_status_reports_database_expiry_and_sms_configuration`
  - `tests/test_auth_session.py` additions: `test_operator_token_refresh` and `test_operator_token_refresh_rejects_revoked`.
- [x] Add `migrations/036_escalation_and_jobs.sql`: `sos_events.escalated_at TIMESTAMPTZ`, and `scheduler_runs (job TEXT PRIMARY KEY, last_run_at TIMESTAMPTZ NOT NULL)`.
- [x] Create `app/incidents/escalation.py` with `ESCALATE_AFTER = timedelta(minutes=2)`, `due_for_escalation` and `escalation_text`.
  The text is English because it goes to MDRRMO staff, not fishermen.
- [x] Create `app/notify.py` with `async def send_sms(text) -> NotifyResult`, one Semaphore implementation using the installed `httpx`, and no interface.
  Env: `SEMAPHORE_API_KEY`, `ONCALL_SMS_NUMBERS` (comma-separated), optional `SEMAPHORE_SENDER_NAME`.
  Use a 10 s timeout; failures return `FAILED` and never raise into the scheduler.
- [x] Create `app/scheduler.py`:
  - `run_job_once(job_id, fn)` takes `pg_try_advisory_lock(hashtext(job_id))`, runs `fn`, records `scheduler_runs` and unlocks.
  - `start(app_state)` spawns asyncio tasks: escalation every 30 s, anomaly evaluation every 5 min (call the existing evaluation entry point used by `POST /api/anomaly/evaluate`; do not copy it).
  - `stop()` cancels the tasks on shutdown.
  - It is enabled unless `AQONE_SCHEDULER=0`; `tests/conftest.py` sets it to `0`.
  - Wire it into the existing `lifespan` in `main.py`.
- [x] Extend `GET /api/ops/status` with `sms_configured`, `db_expires_at`, `db_days_left` and `scheduler_last_run`.
- [x] Add `POST /api/token/refresh` in `app/api/auth.py`: `require_user`, then a new token from `create_token` with the same `ver`.
- [x] `render.yaml`: add `SEMAPHORE_API_KEY`, `ONCALL_SMS_NUMBERS`, `SEMAPHORE_SENDER_NAME` and `DB_EXPIRES_AT` with `sync: false` (values set in the Render dashboard, never in the repo).
  Replace the database comment with a pointer to `docs/runbooks/RENDER_FREE_DB_ROTATION.md`.

### Verification

- [x] Gate commands green, with red and green runs recorded.
- [x] Manual: run locally with `SEMAPHORE_API_KEY` unset.
  Post an SOS, wait 2.5 min, and `/api/ops/status` shows the escalation job ran; the audit row says `not_configured`.

### Review and checkpoint

As in B1.
Checkpoint message: `feat(ops): scheduled SMS escalation for unanswered SOS and operations status`

---

### Green verification

- `python -m ruff check app tests`: passed.
- `python -m pytest -q -p no:cacheprovider`: 507 passed, 44 skipped, 1 xfailed.
- With `AQONE_PROBE_PG_ADMIN_URL` set to the throwaway PostgreSQL 18 instance, `python -m pytest -q -p no:cacheprovider tests/`: 546 passed, 5 skipped, 1 xfailed.
- B6 focused policy, notify, scheduler, auth and migration checks: 27 passed.
- `AQONE_SECURITY_PROBES=1 python -m pytest -q -p no:cacheprovider tests/security_probes`: 11 passed, 3 failed, 0 errors. The same two Phase 6 hotspot cohort probes and firmware shared LoRa key probe remain deferred.
- Manual local run with Semaphore credentials unset: POST `/api/sos` returned 200; after 155 seconds the scheduled escalation had an `escalated_at`, the audit outcome was `not_configured`, `/api/ops/status` reported `sms_configured=false` and the `sos-escalation` last run. The isolated PostgreSQL database was dropped after verification.

## Phase B7: Honest anomaly detection and drift clock

Requirements: EC-H6 (monitoring status), EC-H7 (tagging), EC-H8, EC-H9, EC-H16, EC-L2, EC-L3, EC-M17
Merge after: B6
State: Not started

### Tasks

- [x] Write red tests:
  - `tests/test_anomaly_source.py`:
    - `test_monitoring_unavailable_without_contacts` (no contact in 30 min gives `monitoring == "unavailable"` with a reason)
    - `test_silent_vessel_evaluated_for_72h`
    - `test_handset_contacts_never_raise_overdue_alone`
  - `tests/test_trip_profile.py`:
    - `test_new_profile_not_damped`
    - `test_no_contact_trip_becomes_check_needed`
    - `test_safe_checkin_caps_only_two_hours`
    - `test_departure_hour_is_circular` (23:30 and 00:30 give about 00:00 with a small spread)
    - `test_distance_from_home_landing`
  - `tests/test_drift.py`: `test_drift_start_ignores_implausible_client_ts` (a `client_ts` 3 years old gives `created_at` and `clock_suspect == true`).
- [ ] Add `migrations/037_contact_via_and_welfare_time.sql`: `buoy_contacts.contact_via TEXT NOT NULL DEFAULT 'buoy'` with a CHECK on `pod`, `handset` and `buoy`.
  Add `vessel_trips.welfare_updated_at TIMESTAMPTZ` only if no welfare timestamp already exists; check `024_vessel_trips_and_current_events.sql` first.
- [ ] `app/api/contacts.py`: `ContactEventIn.contact_via` (optional, default `buoy`), stored.
  The existing `source` (`live` or `synthetic`) is unchanged; `docs/04` E4.2 froze the new name because `source` was taken.
- [ ] `app/ai/trip_profile.py`:
  - Remove the new-profile `0.9` damping (around `:621`).
  - Add a `check_needed` status: after the fleet's 90th-percentile trip duration with no contacts and no declared return.
  - `safe` welfare caps the overdue factor only within 2 h of `welfare_updated_at`.
  - Use a circular mean of departure hours via `math.atan2`.
  - Measure distance from the vessel's home landing (the median first-contact position of completed trips), falling back to `geo.CENTER_LAT` and `geo.CENTER_LON`.
- [ ] `app/ai/anomaly_service.py`:
  - Replace `OPEN_TRIP_FRESHNESS_WINDOW` (12 h) with a 72 h window on the last at-sea contact (`geo.point_in_water`).
  - Handset-only evidence cannot produce `overdue`.
- [ ] The `GET /api/anomaly/active` route adds `monitoring` and `monitoring_reason`.
- [ ] `app/ai/drift.py`: the start time uses `client_ts` only inside `[created_at - 24 h, created_at + 5 min]`; otherwise it uses `created_at` and sets `clock_suspect`.
  The drift response exposes `clock_suspect`.
- [ ] Rerun `python -m app.ai.trip_profile_eval` and write the numbers to `models/eval_results.json` as the eval workflow requires.
  Note the change in the evidence file.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Eval numbers recorded before and after, and not presented as field accuracy (docs/16 rule).

### Review and checkpoint

As in B1.
Checkpoint message: `fix(ai): honest monitoring status, silence ages up, and fairer trip priors`

---

## Phase B8: Radio signing service (runs only when Track F reaches F4)

Requirements: EC-C11 (backend half)
Merge after: B7 and build step 3 recorded in `docs/08`
State: Blocked (gated)

Tasks are defined in `docs/62D_EDGE_FIRMWARE_TRACK.md` Phase F4, under "backend part".
It runs in this worktree because it touches `backend/**` and adds the `cryptography` dependency to `backend/requirements.txt`.

## Recovery

Follow project `AGENTS.md` for the three-attempt limit.
Record unresolved work and attempt counts in this worktree's `HANDOFF.md`.
