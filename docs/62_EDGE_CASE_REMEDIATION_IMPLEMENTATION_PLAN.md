# Implementation Plan: Edge case remediation (master)

Created: 2026-09-24T10:00:00+08:00
Updated: 2026-09-25T13:00:00+08:00
Revision: 1
Status: ACTIVE - tracks B (B1-B7), M (M1-M6) and W (W1-W4) plus the review fixes (`docs/archive/plans/63_EDGE_REVIEW_FIXES.md`) merged to `master` in PR #79 (`9630553`, 2026-09-25) and live on Render. Open: Phase I integration walkthrough, Phase 0a (UptimeRobot, NTC inquiry), and the gated B8, M7 and Track F.
**Execution mode:** auto (tracks B, M and W; Section 4.1)
Feature spec and revision: `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md` (approved 2026-09-24, with Len's decisions in its header), findings in `docs/60_EXTREME_EDGE_CASE_REPORT.md`
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`, `docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`
Len's chat approval: Revision 1 (this master plan and track files 62A to 62D) approved by Len in chat, 2026-09-24T11:45:00+08:00
Len's chat approval, 2026-09-25T00:05:00+08:00: tracks B, M and W run in `auto` mode - agents continue through their phases without per-phase sign-off, under master plan Section 4.1.
Target branches: `edge/contracts`, then `edge/backend`, `edge/mobile` and `edge/web` in parallel (Section 4)
Implementers: three AI coding agents, one per track.
Reviewer: Claude Code.

This file is the master plan.
Each agent works from its own track file, and only that agent edits it:

| Track | File | Agent owns |
| --- | --- | --- |
| B - Backend | `docs/62A_EDGE_BACKEND_TRACK.md` | `backend/**`, `render.yaml` |
| M - Mobile | `docs/62B_EDGE_MOBILE_TRACK.md` | `mobile/**` |
| W - Web dashboard | `docs/62C_EDGE_WEB_TRACK.md` | `web/**` |
| F - Firmware (gated, unassigned) | `docs/62D_EDGE_FIRMWARE_TRACK.md` | `firmware/**` |

---

## 1. Scope

This plan implements docs/61, design changes D1 to D11.
D12 (hardware) belongs to Daniel and is tracked in 62D as bench and field tasks, not agent work.
Requirement IDs are the finding IDs from docs/60, prefixed `EC-` (for example `EC-C3`).
The new finding from docs/61 Section 3 is `EC-N1`.

### 1.1 Len's decisions (2026-09-24)

- **Render free tier, no spend.**
  The database gets a rotation runbook, an expiry banner and manual backups instead of a paid plan (Phase 0a).
  The web service is kept awake by a free uptime monitor instead of a paid instance.
- **Escalation channel: SMS.**
  One adapter, `app/notify.py`, is used, with Semaphore (a Philippine SMS API) as the recommended provider.
  With no credentials set, escalation runs, is audited, and the dashboard shows "SMS escalation not configured".
  No message is lost silently.
- **Libraries approved:** `flutter_foreground_task` (Track M) and `cryptography` (backend part of Track F, gated).
- **All other docs/61 recommendations accepted.**
  Per-node keys and signed broadcasts (EC-C11) are approved and gated after build step 3.

### 1.2 Refinements to docs/61 found while planning

1. **Chat intake (D7.1).**
   The handset posts chat straight to `POST /api/mesh/chat` with no credential (`mobile/lib/ui/chathubb.dart:389`).
   A 401 for anonymous posts would silence every phone that has not been enrolled.
   The rule becomes:
   - Anonymous posts are still accepted, but are forced to `origin=app`.
   - Reserved sender names are refused.
   - Each sender is rate-limited.
   - Only an operator session produces `origin=mdrrmo` and the "Official" badge.
   - Reading chat (`GET`) still requires a credential.

   This closes the impersonation part of C9 and all of M12.
   A flood of anonymous posts is limited by the rate limit, not refused.
2. **Boat-facing closure text (D3.1).**
   `boat_message()` does not live on the backend.
   CLAUDE.md forbids display text on an enum, and the phone needs the text in three languages.
   So the backend sends `resolution_code`, and the phone maps each code to localised text.
3. **Missing resolve reason (D3.2).**
   A resolve without `reason_code` is stored as `unspecified`.
   The boat is then told what `closed_unconfirmed` tells it ("closed without reaching you - press SOS again if you still need help").
   This keeps the currently deployed dashboard working, and the safe message is the default, so no follow-up change is needed to make the field required.
4. **Nonce before backend.**
   Pydantic ignores unknown fields, so the phone can send `nonce` before Track B merges.
   The pod ignores unknown JSON keys too.
   Tracks M and B therefore have no merge-order dependency for the nonce.

### 1.3 Out of scope

| Item | Why |
| --- | --- |
| Paid Postgres or a paid web instance | Len: no spend. Revisit when funded (Section 8). |
| SSE or WebSocket dashboard push | docs/61 D4 skip: the escalation watchdog removes the dependency on an open tab. |
| Automated FishR lookup | No API exists; MDRRMO verifies in person. |
| Duress cancel (D11.4 second half) | Needs a written MDRRMO procedure first. |
| L12 (2106 timestamp wrap) | Accepted in docs/61. |

### 1.4 Start gates

- **Phase 0a (ops runbook)** starts on approval, because EC-C5 is date-driven (expiry around 2026-10-15).
- **Phase 0 (contracts)** starts once `fix/security-audit-remediation` has merged to `master` (its Phase 6 is still open) and Len confirms that teammates' in-flight features have landed.
  Both branches touch `docs/04` and `docs/05`, so starting earlier would create conflicts.
- **Tracks B, M and W** start when Phase 0 has merged.
- **Track F** starts when build step 2 ("two radios talk") passes and is recorded in `docs/08`.

---

## 2. Requirements

| ID | Finding (docs/60) | Track and phase | Acceptance test (red first) |
| --- | --- | --- | --- |
| EC-C1 | Shared node ID BUOY01 | F1 | Two-board bench step 1 |
| EC-C2 | Buoy 8-slot ack cache | B3, F1 | `test_downlink_caps_and_orders_by_priority`; bench step 3 |
| EC-C3 | Phone stops after `relayed` | M1 | `delivery_policy_test.dart`, `sos_service_test.dart` "relayed record retries direct" |
| EC-C4 | No pod button or GPS | F5 (Daniel) | Hardware demo recorded in docs/08 |
| EC-C5 | Free database expires | 0a, B6 | Runbook dry run on a local database; `test_ops_status_reports_db_days_left` |
| EC-C6 | Waiting SOS never rings | W1, B6 | `dashboard-alarm.test.js` "first load rings for unacknowledged"; `test_due_for_escalation` |
| EC-C7 | One-click resolve | B1, W2 | `test_reopen_restores_active`; `dashboard-incidents.test.js` "resolve needs reason and confirm" |
| EC-C8 | Split UTF-8 text | B2, M3, F1 | `test_sos_note_truncated_on_char_boundary`; `text_clamp_test.dart`; `utf8_copy_test.c` |
| EC-C9 | Anyone posts "MDRRMO" chat | B5 | `test_reserved_sender_refused`, `test_operator_chat_is_official` |
| EC-C10 | Gateway jammer past 12 incidents | B3, F1 | `test_downlink_caps_and_orders_by_priority`; bench step 3 |
| EC-C11 | Shared radio key | F4 | Bench: an ACK signed with another pod's key is ignored |
| EC-C12 | Fake pod | M1 (consequence), M7 (cause, P3) | M1 tests; device test |
| EC-C13 | MITM on gateway | Done (SEC-28) | Bench: gateway reaches backend with verified TLS |
| EC-C14 | Pre-made rows capture SOS | B2, M3, F1 | `test_prepared_rows_cannot_capture_nonce_sos` |
| EC-H1 | No GPS on panic SOS | M3, F1, F5 | `sos_service_test.dart` "late fix re-posts same nonce" |
| EC-H2 | Android kills retries | M2 | Device test: 30 min screen off on the cheapest target phone |
| EC-H3 | Pod WiFi fights internet | M7 (P3) | Device test on Android 10 to 14 |
| EC-H4 | Default 20-minute ETA | W2, M4 | `dashboard-incidents.test.js` "ack defaults to no ETA"; `widget_test.dart` "no ETA copy" |
| EC-H5 | Note dropped on pod dup | F1 | Bench step 6 |
| EC-H6 | Anomaly has no input or schedule | B6, B7, W4 | `test_monitoring_unavailable_without_contacts`; `test_scheduler_runs_anomaly` |
| EC-H7 | Phone missing vs boat missing | B7 (tagging), F5 (input) | `test_handset_contacts_never_raise_overdue_alone` |
| EC-H8 | New and solo under-flagged | B7 | `test_new_profile_not_damped`, `test_no_contact_trip_becomes_check_needed` |
| EC-H9 | Silent 12 h drops out | B7 | `test_silent_vessel_evaluated_for_72h` |
| EC-H10 | Forgeable badge, no verification | B5, M5, W4 | `test_license_text_never_sets_tier`; `enrolment_page_test.dart`; web badge test |
| EC-H11 | Relay collisions | F3 (P3) | Field record in docs/08 |
| EC-H12 | Single gateway | B3 (visibility), F2, F5 | `test_ops_status_reports_gateway_last_poll`; bench |
| EC-H13 | X-Api-Key missing | Done (Phase 5) | Bench: mesh SOS lands with `seq` |
| EC-H14 | Warning sent once | F1 | Bench step 7 |
| EC-H15 | Old SOS arrives as new | B4, M1, W3 | `test_active_marks_late_calls`; `sos_service_test.dart` "stale prompt" |
| EC-H16 | Safe check-in mutes trip | B7 | `test_safe_checkin_caps_only_two_hours` |
| EC-H17 | Seq collisions | B2, M3, F1 | `sos_service_test.dart` "same seq, different nonce" |
| EC-H18 | Flood buries real SOS | B4, W3 | `test_active_orders_known_vessel_above_flood`; web "+N more" test |
| EC-H19 | Prank via pod looks trusted | F1, W3 | Bench per-client cap; web wording test |
| EC-H20 | Rescuers baited | B4, W3 | `test_plausibility_flags` |
| EC-H21 | Blank profile fill | B5 | `test_enrolled_vessel_blank_fill_needs_device` |
| EC-H22 | No silent SOS | M6 | `widget_test.dart` "silent SOS starts no alarm" |
| EC-H23 | Lithium charging hot | F5 (Daniel) | Bench at 60 °C |
| EC-M1 | Note cut at 40 bytes | B1, W2 | `test_responder_note_over_40_bytes_rejected`; web counter test |
| EC-M2 | Reinstall new identity | M5, B5 | `test_refresh_accepts_recently_expired_token`; backup rules file test |
| EC-M3 | Phones and boats not 1:1 | B4, W3 | `test_active_counts_open_calls_per_vessel` |
| EC-M4 | Shore NTP before router | F1 | Bench step 4 |
| EC-M5 | Buoy field hazards | F5 (Daniel) | Field record |
| EC-M6 | Only phone number is at sea | B5, M5, W4 | `test_profile_stores_shore_contact` |
| EC-M7 | SOS hitchhikes neighbour pod | M1, M7 | M1 tests; device test |
| EC-M8 | Concurrent ack overwrite | B1, W2 | `test_ack_with_stale_version_conflicts` |
| EC-M9 | Mistaken SAFE_NOW final | B1, M4 | `test_still_in_danger_reopens_within_two_hours`; `widget_test.dart` "undo stand-down" |
| EC-M10 | Prank close says "resolved" | B1, M4 | `test_resolution_code_in_vessel_feed`; `closure_text_test.dart` |
| EC-M11 | 915 MHz legality | 0a (Len inquiry), F5 | NTC answer recorded in docs/08 |
| EC-M12 | Chat readable by anyone | B5 | `test_chat_read_requires_credential` |
| EC-M13 | No profile, no SOS | M5 | `sos_service_test.dart` "SOS without boat name" |
| EC-M14 | Free web sleeps | 0a | Uptime monitor configured (Len), recorded |
| EC-M15 | First clock wins | F1 | Bench |
| EC-M16 | Brownout loop | F5 (Daniel) | Bench step 5 |
| EC-M17 | Drift trusts wrong clock | B7 | `test_drift_start_ignores_implausible_client_ts` |
| EC-M18 | 7-day session | B6, W4 | `test_operator_token_refresh` |
| EC-L1 | English-only SOS text | M6 | `localization_test.dart` covers new keys |
| EC-L2 | Midnight averages to noon | B7 | `test_departure_hour_is_circular` |
| EC-L3 | Distance from town centre | B7 | `test_distance_from_home_landing` |
| EC-L4 | Media volume silences alarm | M6 | `sos_alarm_test.dart` audio context is alarm usage |
| EC-L5 | Wet screens vs countdown | M7 (P3) | Wet-screen device test |
| EC-L6 | Replay after filter rollover | F1 | Bench |
| EC-L7 | Invalid UTF-8 drops WS | M3, F1 | `buoy_client_test.dart` malformed bytes |
| EC-L8 | 20-row vessel feed | B2 | `test_vessel_feed_returns_all_unresolved` |
| EC-L9 | Joke boat name as title | W1 | web title test |
| EC-L10 | Firmware update wipes queue | F1 | README procedure plus boot log |
| EC-L11 | Always N and E | W1, B4 | web hemisphere test; `on_land` flag test |
| EC-L13 | Same-second clone merge | B2 | `test_same_second_different_nonce_two_rows` |
| EC-N1 | TLS may need a synced clock | F1 | Bench step 4 |

---

## 3. Shared contract summary (frozen in Phase 0)

Agents build against these shapes in parallel.
Phase 0 writes them into docs/02 to docs/06.
If an agent finds a gap, it stops that task, records the gap in its `HANDOFF.md`, and Claude amends the contract on `master`.
No agent edits a contract doc.

### 3.1 SOS ingest - `docs/04`

- `SosIn.nonce: int | None`, range `0..4294967295`.
  With a nonce, the merge key is `(vessel_id, nonce)`; without one, it stays `(vessel_id, client_ts)` for legacy clients.
- `note` and `boat` are truncated to 64 and 32 UTF-8 bytes on a character boundary, never rejected.
  `vessel_id` limits stay as they are.
- A merge where both deliveries carry positions more than 1 km apart sets `position_conflict = true` and stores the second position in `alt_latitude` and `alt_longitude`.
  The first position stays primary.
- The response adds `nonce`.

### 3.2 Event shape - every feed that returns an SOS event

That means `/active`, `/vessel/{id}`, `/ack/{local_id}` and `/downlink`.
Each adds:

| Field | Type | Meaning |
| --- | --- | --- |
| `nonce` | int or null | the phone's incident nonce |
| `version` | int | incremented on every write |
| `resolution_code` | string or null | `rescued`, `safe_confirmed`, `stood_down_by_fisher`, `duplicate`, `closed_unconfirmed`, `unspecified` |
| `reopened_at` | ISO or null | last reopen time |

The phone maps `resolution_code` to localised text:
- `rescued`, `safe_confirmed` and `stood_down_by_fisher` mean "Closed by MDRRMO".
- `duplicate` means follow the surviving incident.
- `closed_unconfirmed` and `unspecified` mean "MDRRMO closed this call without reaching you. If you still need help, press SOS again."

### 3.3 Operator actions - `docs/05`

- `POST /api/sos/{id}/acknowledge` adds `expected_version`.
  `responder_note` may be at most 40 UTF-8 bytes, or the response is 422 with `detail = "responder_note_too_long"`.
- `POST /api/sos/{id}/resolve` body: `{reason_code?, reason?, expected_version?}`.
  A missing `reason_code` is stored as `unspecified`.
- `POST /api/sos/{id}/reopen` body: `{reason?, expected_version?}`.
  Reopening an open incident returns 200 with `outcome = "no_change"`.
  It is audited.
- A version conflict on any of the three returns 409 `{"detail": "version_conflict", "current": <event>}`.
- `POST /api/sos/{id}/reply` and `POST /api/sos/reply/{local_id}`: `STILL_IN_DANGER` on an incident resolved less than 2 h ago reopens it, with `reopened_by = "fisher"`.
- `POST /api/token/refresh`: a valid operator token gets a fresh token.
  SEC-12 revocation still applies.

### 3.4 Dispatcher feed - `GET /api/sos/active?limit=200`

The response is `{events, total, flood}`.
`flood` is `{unknown_vessels_last_minute: int, active: bool}`, where `active` means more than 10 in the last minute.

Events are in triage order:
1. unacknowledged before acknowledged
2. then corroborated (gateway-delivered, `phone_verified` or better, or a vessel with trip history)
3. then newest

Each event also adds:

| Field | Type | Meaning |
| --- | --- | --- |
| `pressed_at` | ISO | from `client_ts` |
| `is_late` | bool | `created_at - client_ts` more than 30 min |
| `flags` | list of strings | `position_on_land`, `position_beyond_radio_range`, `position_jump`, `many_calls_same_vessel`, `position_conflict` |
| `open_calls_for_vessel` | int | open incidents for the same vessel |
| `alt_latitude`, `alt_longitude` | float or null | the conflicting position |
| `delivery_path` | string | `direct` or `pod` |
| `vessel_verified` | bool | `phone_verified` or better |
| `phone_set_by` | string or null | `device`, `anonymous` or `operator` |
| `shore_contact_name`, `shore_contact_phone` | string or null | from the profile |

### 3.5 Vessel and identity - `docs/05`

- `GET /api/sos/vessel/{id}` returns every unresolved incident plus the newest 20 resolved ones.
- `POST /api/vessels/{vessel_id}/confirm` (responder roles, audited) sets the vessel's tier to `confirmed_by_responder`.
- The vessel profile gains optional `shore_contact_name` (at most 64 characters) and `shore_contact_phone` (at most 20).
- A vessel with an active enrolled device needs that device's bearer for every profile write, including blank fills (401 without it, 403 for another vessel's device).
- `license_type` text never changes the trust tier.
- `POST /api/vessel-auth/refresh` accepts a token up to 30 days past expiry if the device is not revoked.

### 3.6 Mesh chat - `docs/05`

Posting (`POST /api/mesh/chat`) depends on the caller's credential:

| Credential | `origin` | `sender` |
| --- | --- | --- |
| Operator session | `mdrrmo` | the account's display label |
| Vessel device bearer | `app` | the vessel's boat name |
| Gateway key | `mesh` | as relayed |
| None (anonymous) | forced to `app` | as given |

- Reserved names are refused with 422 `sender_reserved` unless the origin is `mdrrmo`.
  They are MDRRMO, Coast Guard, PCG, PAGASA, Admin and Official, matched case-insensitively after removing non-letters and mapping 0 to o and 1 to l.
- Each sender (plus client IP) may post 6 times a minute; beyond that the response is 429.
- `GET /api/mesh/chat` requires the gateway key, an operator session or a vessel device bearer.

### 3.7 Operations - `docs/05`

`GET /api/ops/status` (operator) returns:
- `gateway_last_poll_at`
- `gateway_stale` (more than 3 missed 45 s polls)
- `sms_configured`
- `db_expires_at` and `db_days_left` (from env `DB_EXPIRES_AT`, or null)
- `scheduler_last_run: {escalation, anomaly}`

Anomaly changes:
- The vessel-risk response (`GET /api/anomaly/active`) adds `monitoring` (`active` or `unavailable`) and `monitoring_reason`.
- Anomaly statuses gain `check_needed`.
- Contact events (`docs/04`) gain an optional `contact_via` of `pod`, `handset` or `buoy`, defaulting to `buoy`.
  (Phase 0 renamed it from `source`, which already means `live` or `synthetic` on that route.)
  Handset-only contacts never raise `overdue` on their own.

Drift responses add `clock_suspect: bool`.

### 3.8 Downlink - `docs/04`

- At most `DOWNLINK_MAX = 12` events.
- `is_synthetic` rows are excluded.
- Selection: open incidents changed in the last 24 h, plus incidents resolved in the last 6 h.
- Order: acknowledged-open, then unacknowledged-open, then resolved; within each group, latest change first.
- Every poll records the gateway's last-seen time.

### 3.9 Phone and pod - `docs/03`, and LoRa - `docs/02`

- The handoff request adds `nonce`.
- `accepted: true` means queued on the pod only; it is not delivered.
- After F1, the pod fills an empty `note`, `lat` or `lon` when a handoff duplicates a queued `(vessel_id, nonce)`, and `/v1/sos/status` returns `nonce` and `resolution_code`.
- LoRa: reserve `nc` (uint32) in the SOS and T_ETA payloads, and `rc` (resolution code as a small int, in the order of the list in 3.2 starting at 1) in T_ETA.
- All text is UTF-8, cut only on character boundaries.
- Relay, clock and key rules are defined in Track F's own contract step (F0).

### 3.10 Delivery states - `docs/06`

- `relayed` is not terminal: the phone keeps trying the direct path until `delivered`.
- `resolved` is a flag that a reopen can clear, not a fifth state.

---

## 4. Branches, worktrees and merge order

```text
master (after security remediation merges)
  └─ edge/contracts            Phase 0 - Claude, docs only, merged first
       ├─ edge/backend         Track B   worktree ../AqOne-edge-backend
       ├─ edge/mobile          Track M   worktree ../AqOne-edge-mobile
       └─ edge/web             Track W   worktree ../AqOne-edge-web
  (later) edge/firmware        Track F   worktree ../AqOne-edge-firmware
```

- Each agent works only in its own worktree, and each worktree keeps its own ignored `HANDOFF.md` (AGENTS.md).
- **File ownership is exclusive** (the table at the top).
  An agent never edits another track's directory, a contract doc, `docs/08`, `docs/16` or this master plan.
  Its progress goes in its own track file and in `docs/edge-remediation/EVIDENCE-<track>.md`.
- **One PR per phase** into `master`, rebased on `master` first.
- **Merge order within a phase pair.**
  A web or mobile phase that calls a new backend field or route merges only after the backend phase that provides it.
  Each track file lists its `Merge after:` dependencies.
  Development runs in parallel; only merging waits.
- The dashboard is served by the same Render service as the API, so merging a backend phase and its web phase back to back deploys them together.
- Migrations belong to Track B only, numbered from `032` in phase order.

### 4.1 Auto execution rules

Tracks B, M and W run in `auto` mode (approved by Len, see the header).
An agent finishes a phase, checkpoints it, and starts the next phase in its track file without waiting for anyone.

**After each phase:**
1. Gate commands green, with the red and green runs recorded in the track's evidence file.
2. Tick the phase's boxes and set its `State:` to `Done - <commit>` in the track file; update `HANDOFF.md`.
3. Stage only the track's own paths plus its track file and evidence file, and commit with the phase's checkpoint message.
   No agent name or co-author line in the commit message (CLAUDE.md).
4. `git push origin edge/<track>`, then start the next phase on the same branch.

**Never:**
- merge into `master`, push to `master`, or open or merge a PR yourself.
  Claude reviews the phase commits and Len merges them in the order of Section 4; "Merge after:" lines limit merging only, never development.
- touch Render, its environment variables, or the deployed database.
- add a dependency the plan has not approved (`flutter_foreground_task` is the only new one for these tracks).
- edit a contract doc, another track's paths, `docs/08`, `docs/16` or this plan.

**Checks an agent cannot do** (device tests, a real phone, a second person) are not blockers.
Record each one in the evidence file as `Pending - Len: <what to do>`, leave its box unticked, and continue.
Checks an agent can do (a local server and `curl`, an emulator, a browser if one is available) are done, not deferred.

**Building against unmerged backend work.**
Mobile and web phases build against the frozen contract in `docs/03` to `docs/06` (the "Edge-case remediation contract" sections), with stubbed responses in tests.
They do not wait for, or copy code from, `edge/backend`.

**Local Postgres for backend tests.**
Never use or guess Len's local Postgres password.
Start a throwaway cluster outside the repository and point the probe variable at it:

```powershell
$pg = "$env:TEMP\aqone-edge-pg"
& 'C:\Program Files\PostgreSQL\18\bin\initdb.exe' -D $pg -U postgres -A trust -E UTF8
Start-Process -WindowStyle Hidden 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -ArgumentList '-D', $pg, '-o', '"-p 55432"', '-l', "$pg.log", 'start'
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'
```

Stop it with `pg_ctl -D $pg stop` when the session ends.

**Stop and wait for Len only when:**
- the next phase is gated (`State: Blocked (gated)`: B8, M7), or every phase is done;
- a gate still fails after three attempts (AGENTS.md "Recovery");
- a contract in `docs/02` to `docs/06` looks wrong or incomplete (record the gap in `HANDOFF.md`);
- a decision belongs to Len: spend, credentials, a new dependency, or a design change beyond docs/61 and this plan.

When stopping, leave interrupted work uncommitted, set `HANDOFF.md` **Status** and **The Baton** precisely, and say why in the track's evidence file.

### Dependency map

| Consumer phase | Needs merged first |
| --- | --- |
| W2 resolve and ack dialogs | B1 |
| W3 triage and flags | B2, B4 |
| W4 badges and ops status | B3, B5, B6, B7 |
| M4 closure text and reopen | B1 (M4 degrades gracefully without it, so it can merge first) |
| M5 enrolment refresh grace | B5 |
| F1 (gateway chat key, `nc`/`rc` in frames) | B2, B5 |
| F4 signed broadcasts | B-F4 signing endpoint (in 62D) |

Phases with no row can merge in any order.

---

## 5. Phase 0a: Free-tier database safety (not gated)

Requirements: EC-C5, EC-M14, EC-M11
State: In progress - runbook written, expiry confirmed, rehearsal passed; waiting on Len's UptimeRobot monitor and NTC inquiry
Owner: Claude writes; Len executes the Render steps.

### Tasks

- [x] Write `docs/runbooks/RENDER_FREE_DB_ROTATION.md`, covering:
  - reading the expiry date on the Render dashboard
  - `pg_dump --format=custom` from the external URL to Len's machine (never committed, never uploaded to GitHub, because it contains phone numbers)
  - deleting the old free database, then creating the new one under the same name `aqone-db` so the `render.yaml` binding still resolves
  - `pg_restore`, then redeploy so `migrate.py` runs
  - checking `/health/ready`, and posting and resolving a test SOS
  - setting env `DB_EXPIRES_AT` to the new expiry
  - choosing a midday window, when boats are out and the gateway and phones retry anyway
- [x] In the same runbook, add a keep-awake section: a free UptimeRobot HTTP monitor on `/healthz` every 5 min.
  One always-on free service uses about 744 of the 750 free instance hours a month, so it only fits if no other free service runs in the workspace.
  Going over suspends every free web service until the next month (Render docs, checked 2026-09-24).
- [x] Record the NTC band inquiry as an open item in the runbook's "Len actions" list.
- [x] Len: confirm the real expiry date (confirmed in chat 2026-09-24: around 2026-10-15).
- [x] Dry run of the dump and restore against a local Postgres (Claude, 2026-09-24, throwaway cluster).
- [ ] Len: set up UptimeRobot and send the NTC inquiry.

### Verification

- [x] Dry run of dump and restore into local Postgres 18: row counts match for `sos_events`, `vessels`, `users` and `operations_audit_events`.
- [x] Evidence goes in `docs/edge-remediation/EVIDENCE-ops.md` (row counts only, never data).

### Review and checkpoint

- [x] Review the runbook for secrets: environment variable names only.
- [x] Commit on `docs/edge-case-report` (runbook, merged as `c13010f`); rehearsal evidence committed on `edge/contracts`.

Checkpoint message: `docs(ops): free-tier Render database rotation and keep-awake runbook`

---

## 6. Phase 0: Contract freeze (Claude, before the tracks split)

Requirements: all rows in Section 2 that change a contract
State: Done - merged to `master` as `06dd18b` (PR #76), 2026-09-24
Gate: Section 1.4.

### Tasks

- [x] Create `edge/contracts` from `master`, and bring over docs/60, docs/61, this plan and the four track files.
- [x] Write Section 3 into its contract docs (each as a dated "Edge-case remediation contract" section, with **Changing:** pointers on the endpoints it changes):
  - 3.1, 3.8 and the gateway parts of 3.6 into `docs/04_INGEST_API.md`
  - 3.2 to 3.7 into `docs/05_PUBLIC_API.md`
  - 3.9 into `docs/03_PHONE_BUOY_WIFI.md` and `docs/02_LOAM_PACKET_SPEC.md` (the `nc`/`rc` reservation and the UTF-8 rule only)
  - 3.10 into `docs/06_DELIVERY_STATES.md`
- [x] Add the resolution code vocabulary to `docs/13_RESPONDER_LOOP.md`.
- [x] Add the new string keys from Track M's phase list to `docs/22_LOCALIZATION_PLAN.md`.
- [x] Add the badge rule (positive only; never colour or priority by tier) and the plausibility-tag style to `docs/47_VISUAL_DESIGN_GUIDE.md`.
- [x] Add the accepted risks from docs/61 Section 13 to `docs/16_QA_DISCLOSURES.md`.
- [x] Create `docs/edge-remediation/` with empty `EVIDENCE-backend.md`, `EVIDENCE-mobile.md`, `EVIDENCE-web.md` and `EVIDENCE-firmware.md`.
- [ ] Notify the owners named in docs/61 Section 10: Arnold, Daniel, Jade and Doreen Kay (Len; the message is drafted in the PR description).

### Verification

Phase 0 found one gap and closed it: Section 3.7's contact `source` collided with the existing `source` (`live` or `synthetic`) on `POST /api/v1/contacts`, so the frozen name is `contact_via` (`docs/04` E4.2, and B7 in 62A updated to match).

- [x] Every field and route in Section 3 appears in exactly one contract doc (a manual checklist in the PR description).
- [x] `git diff --stat master` lists only `docs/` paths.

### Review and checkpoint

- [x] Merge `edge/contracts` to `master`, then create the three track branches and worktrees from the new `master`:
  `git worktree add ../AqOne-edge-backend -b edge/backend master`, and likewise for mobile and web.
- [x] Write an ACTIVE `HANDOFF.md` in each worktree, with the Baton set to that track's first phase.

Checkpoint message: `docs(contracts): freeze edge-case remediation contracts`

---

## 7. Phase I: Integration and field readiness (Claude and Len, after B7, M6 and W4 merge)

Requirements: end-to-end confirmation of every P1 row
State: Not started - unblocked 2026-09-25 (B7, M6 and W4 merged in PR #79)

### Tasks

- [ ] Run end to end on a local stack: backend plus local Postgres, the dashboard in a browser, and the phone on an emulator in airplane mode where relevant.
  Walk through:
  - C3: pod accepts then goes silent; the phone keeps trying the direct path
  - C6: page load with a waiting SOS rings
  - C7: resolve needs a reason; undo reopens
  - M8: two tabs acknowledge; the second gets a 409 prompt
  - M9: fisher undo reopens and re-alarms
  - H15: a late badge appears
  - H18: 500 anonymous calls; a known vessel stays on top
  - C9: a "MDRRMO" post is refused
- [ ] Deploy to Render.
  Repeat C6, C7 and C9 against the deployed URL.
  Confirm that `/api/ops/status` shows `db_days_left` and SMS status.
- [ ] Send one real escalation SMS to the duty phone (if credits exist), or record that SMS is not configured.
- [ ] Build a release APK and run the M2 foreground-service device test.
- [ ] Update `docs/08_DEMO_AND_STATUS.md` with a dated entry linking each track's evidence file.

### Verification

- [ ] All four suite gates are green on `master`: backend ruff and pytest (including the Postgres-backed tests with `AQONE_PROBE_PG_ADMIN_URL` set), mobile analyze and test, and web tests and syntax.
- [ ] Each walkthrough step is recorded with its observed result in `docs/edge-remediation/EVIDENCE-integration.md`.

Checkpoint message: `docs(status): edge-case remediation integration evidence`

---

## 8. Revisit when

- **Funding arrives:** replace Phase 0a with a paid Postgres (daily backups) and a paid web instance, and drop the rotation runbook.
- **The deployment has more than one backend instance:** the in-memory chat rate limit moves to Postgres; the scheduler's advisory locks already cover multiple instances.
- **Build step 2 fails in a way that changes the frame layout:** Track F re-checks the `nc`/`rc` reservation before F1.

---

## 9. Agent kickoff prompts

Give each agent its prompt only after Phase 0 has merged and its worktree exists.

**Backend agent (Track B)**

> You are the backend implementer for AqOne edge-case remediation.
> Work only in the worktree `../AqOne-edge-backend` on branch `edge/backend`.
> Read `AGENTS.md`, `CLAUDE.md`, then `HANDOFF.md` in this worktree, then `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Sections 1 to 4, then your track file `docs/62A_EDGE_BACKEND_TRACK.md`.
> Start with the phase named in the Baton.
> Execution mode is auto: follow master plan Section 4.1. After each phase's verification, update your track file, `docs/edge-remediation/EVIDENCE-backend.md` and `HANDOFF.md`, commit, push `edge/backend`, and go straight on to the next phase.
> Stop only for the conditions in Section 4.1. Never merge into or push to `master`.
> You own `backend/**` and `render.yaml` only.
> Never edit contract docs, `web/`, `mobile/` or `firmware/`; if a contract seems wrong, stop and record it in `HANDOFF.md`.
> Every phase starts by writing the listed failing tests and recording the red run before any fix.
> Apply the clean-architecture, clean-code and ponytail skills: policy in `app/incidents/` as pure functions, SQL stays in `app/api/`, and no new abstractions beyond the track file.

**Mobile agent (Track M)**

> The same as above, with worktree `../AqOne-edge-mobile`, branch `edge/mobile`, track file `docs/62B_EDGE_MOBILE_TRACK.md`, evidence file `EVIDENCE-mobile.md`, and ownership of `mobile/**` only.
> New user-facing text goes in `mobile/lib/l10n/app_en.arb` with `@key` descriptions and drafts in `app_fil.arb` and `app_akl.arb`.
> Policy goes in `mobile/lib/models/` as pure Dart with an injected clock.

**Web agent (Track W)**

> The same as above, with worktree `../AqOne-edge-web`, branch `edge/web`, track file `docs/62C_EDGE_WEB_TRACK.md`, evidence file `EVIDENCE-web.md`, and ownership of `web/**` only.
> The dashboard renders what the backend sends; it never re-implements triage, lifecycle or trust rules.
> Build against the frozen contracts with stubbed responses; `Merge after:` lines limit merging only, which Len does.

## Recovery

Follow project `AGENTS.md` for the three-attempt limit and immediate blockers.
Record unresolved work and attempt counts in the worktree's `HANDOFF.md`.
Interrupted or failing work remains uncommitted, and the phase remains incomplete.
