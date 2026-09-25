# Implementation Plan: Edge-case review fixes

Created: 2026-09-25T09:00:00+08:00
Revision: 2 (2026-09-25: F5 may also edit the responder-loop fake pool; see F5)
Status: Approved (Len, in chat, 2026-09-25)
**Execution mode:** auto
Implementer: GPT Luna.
Reviewer: Claude Code.
Branch and worktree: `edge/fixes`, `../AqOne-edge-fixes` (already created: `master` plus `edge/backend`, `edge/mobile` and `edge/web` merged, no conflicts).
Evidence file: `docs/edge-remediation/EVIDENCE-fixes.md` (create it in step 0).
Source: Claude's review of the three edge tracks, 2026-09-25.
Contracts: `docs/02` to `docs/06` "Edge-case remediation contract" sections; `docs/05` E5.7 was amended on this branch for F3.

This plan fixes the defects found in review.
It does not add features.
Every fix starts with a failing test.

---

## 1. Rules (strict)

Read these before anything else.
Breaking any of them fails the review, even if the code works.

1. **Tests before code, every time.**
   For each fix, write the tests named in its section, run them, and paste the failing output (test names and the assertion message) into the evidence file **before** you change any non-test file.
   A test marked **red** must fail on the current code for the reason stated.
   If it passes before your fix, the test is wrong: rewrite it until it fails for that reason, and never weaken it to make it pass later.
   A test marked **guard** is expected to pass before and after; it pins behaviour the fix must not break.
2. **Touch only the files each fix names**, plus the test files it names, the evidence file and `HANDOFF.md`.
   If a fix seems to need another file, stop and record why in `HANDOFF.md`.
3. **Never edit a contract doc** (`docs/02` to `docs/06`), `docs/08`, `docs/16`, `docs/61`, `docs/62*` or this plan.
   If a contract looks wrong, stop and record it.
4. **No new dependencies**, in any language.
5. **Keep line endings.**
   Files that are CRLF on `master` stay CRLF; LF files stay LF.
   Check with `git diff --stat` and `git diff --ignore-cr-at-eol --stat`: the two must agree for every file you touch.
6. **Commits.**
   One commit per fix section, with the exact message given.
   No agent name and no co-author line in any commit message (CLAUDE.md).
   Stage only the paths you changed for that section: never `git add -A` or `git add .`.
7. **Never merge into or push to `master`.**
   Push `edge/fixes` after each commit: `git push -u origin edge/fixes`.
   Claude reviews the branch and Len merges it.
8. **Three-attempt limit** (AGENTS.md "Recovery").
   If the same test or gate still fails after three correction attempts, stop, leave the work uncommitted, and write the failure report in `HANDOFF.md`.
9. **No em dash** ("—") in anything you write.
   Use a plain dash.
10. **Comments** only for a non-obvious reason (a hidden constraint or a workaround), never to narrate the code.

---

## 2. Environment and gates

Run from the worktree root `../AqOne-edge-fixes` unless a command says otherwise.

**Postgres for backend tests.**
A throwaway PostgreSQL 18 cluster may already be running on port 55432 (`%TEMP%\aqone-edge-pg`, trust auth).
Check with `psql -h localhost -p 55432 -U postgres -Atc "select 1"`.
If it is not running, start one exactly as in `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Section 4.1.
Never use or guess Len's own Postgres password.

**Gate commands** (run all of them after every fix section, because these fixes cross layers):

```powershell
# backend
cd backend
python -m ruff check app tests
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'
python -m pytest -q -p no:cacheprovider
$env:AQONE_SECURITY_PROBES = '1'; python -m pytest -q -p no:cacheprovider tests/security_probes; Remove-Item Env:AQONE_SECURITY_PROBES
cd ..

# mobile
cd mobile
flutter gen-l10n
flutter analyze
flutter test
flutter test test_security_probes
cd ..

# web
node --test web/test/*.test.js
Get-ChildItem web/js, web/test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }

# firmware headers stay identical (must print nothing)
git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
```

**Baseline** (Claude, 2026-09-25, before any fix):
- backend: ruff clean; 559 passed, 5 skipped, 1 xfailed.
- security probes: exactly 3 failing, all deferred and also failing on `master`: `test_hotspot_cell_needs_five_distinct_reporters[3]`, `[4]`, and `test_loam_signature_key_is_selected_per_source_id`.
- mobile: analyze 0 issues; 316 passed; security probes 6 passed.
- web: 171 passed; all `.js` files pass `node --check`.

Any new failure beyond the baseline blocks the commit.
Pass counts go up only by the tests you add.

---

## 3. Step 0: set up

- [ ] Read `AGENTS.md`, `CLAUDE.md`, `HANDOFF.md` in this worktree, then this plan end to end.
- [ ] Run every gate command and confirm the baseline above.
  Record the numbers in a new `docs/edge-remediation/EVIDENCE-fixes.md`, with a heading per fix section to fill in as you go.
- [ ] If the baseline differs, stop and record the difference in `HANDOFF.md`.

---

## 4. Fixes

Do them in this order.
Each section lists: the defect, the red tests, the change, and the commit message.

### F1 - Shore gateway sends its key on chat calls

**Defect.**
`firmware/shore/AqOneShore/AqOneShore.ino` calls `POST /api/mesh/chat` (`postChat`, about line 328) and `GET /api/mesh/chat` (`pollChat`, about line 639) without `X-Api-Key`.
The backend now answers an unauthenticated `GET /api/mesh/chat` with 401 (`docs/05` E5.6), so chat to the boats stops, and gateway posts are stored as `origin = app` instead of `mesh` (`docs/04` E4.4).

**Red test** - add to `backend/tests/test_firmware_security.py`:
- `test_shore_chat_calls_send_gateway_key`:
  - Read `SHORE_SKETCH`.
  - Extract the body of `bool postChat(` and of `void pollChat(` by matching braces from the function's opening `{` to its closing `}` (write a small local helper; no regex across the whole file).
  - Assert each body contains `https.addHeader("X-Api-Key", GATEWAY_API_KEY);`.
  - Red reason: neither body contains it.

**Change** - `firmware/shore/AqOneShore/AqOneShore.ino` only:
- In `postChat` and in `pollChat`, add `https.addHeader("X-Api-Key", GATEWAY_API_KEY);` immediately after the successful `httpsBegin(...)` check, the same way the downlink and ingest calls already do (around lines 280, 490 and 715).
- Do not touch either `AqOneLoam.h`.

**Verification.**
- The red test passes; the `AqOneLoam.h` diff prints nothing.
- PlatformIO is not installed on this machine, so record in the evidence file: `Pending - Len: pio run -d firmware -e shore, then flash the shore and confirm a dashboard chat line reaches a boat.`

Commit: `fix(shore): send the gateway key on mesh chat calls`

### F2 - Version conflicts return `current`, as the contract says

**Defect.**
`backend/app/api/sos.py` `_version_conflict` (about line 243) returns `{"detail": "version_conflict", "event": ...}`.
`docs/05` E5.2 and the dashboard (`web/js/dashboard/dashboard-incidents.js` about line 437) use `current`, so the dashboard's conflict message is blank and its retry drops `expected_version`.

**Red tests** - add to `backend/tests/test_edge_lifecycle_pg.py`:
- `test_version_conflict_body_carries_current_for_acknowledge`: acknowledge with a stale `expected_version`; assert 409, `detail == "version_conflict"`, `current["id"]` is the event id and `current["version"]` is the stored version.
- `test_version_conflict_body_carries_current_for_resolve`: the same through `/resolve`.
- `test_version_conflict_body_carries_current_for_reopen`: the same through `/reopen` on a resolved event.
- Red reason: the body has `event`, not `current`.

**Guard test** - `web/test/dashboard-incidents.test.js` already has `409 displays the current answer and waits for another confirmation`; it must stay green.

**Change** - `backend/app/api/sos.py` only: rename the key `event` to `current` in `_version_conflict`.
Grep `backend/` for any other reader of that key and update it.

Commit: `fix(sos): version conflicts return the current event under current`

### F3 - Anomaly monitoring is fleet-wide and top level

**Defect.**
`backend/app/api/anomaly.py` puts `monitoring` on each row (`_score_response`, about line 30), decided from that row's own contact age.
The dashboard reads it at the top level, so an empty list, which is exactly the case EC-H6 exists for, still reads as "all clear".
`docs/05` E5.7 is amended on this branch: the response is `{"rows": [...], "monitoring": ..., "monitoring_reason": ...}`, and `monitoring` is fleet-wide.

**Red tests** - add a new file `backend/tests/test_edge_monitoring_pg.py` (uses `probe_db`, like the other `test_edge_*_pg.py` files):
- `test_active_is_unavailable_without_live_contacts`: no `buoy_contacts` rows; `GET /api/ai/anomaly/active` returns 200 with `rows == []`, `monitoring == "unavailable"` and a non-empty `monitoring_reason`.
- `test_active_is_available_with_a_recent_buoy_contact`: one live, non-synthetic contact with `contact_via = 'buoy'` observed 5 minutes ago; `monitoring == "active"` and `monitoring_reason is None`.
- `test_handset_contacts_alone_leave_monitoring_unavailable`: only a `contact_via = 'handset'` contact 5 minutes ago; `monitoring == "unavailable"`.
- `test_stale_contacts_leave_monitoring_unavailable`: only a buoy contact 31 minutes ago; `monitoring == "unavailable"`.
- Red reason: the route returns a bare list.

**Existing tests to update** (say so in the evidence file):
- `backend/tests/test_anomaly_source.py::test_monitoring_unavailable_without_contacts` tests the per-row rule you are removing: delete it, since the four tests above replace it.
- `backend/tests/test_anomaly_active_readonly.py`: if it indexes the response as a list, read `response.json()["rows"]` instead; its read-only assertion must stay.

**Change.**
- `backend/app/api/anomaly.py`:
  - Remove `monitoring` and `monitoring_reason` from `_score_response`.
  - `active()` returns `{"rows": [...], "monitoring": ..., "monitoring_reason": ...}`.
  - Decide `monitoring` with one read-only query: does a `buoy_contacts` row exist with `source = 'live'`, `is_synthetic IS FALSE`, `contact_via <> 'handset'` and `observed_at >= NOW() - INTERVAL '30 minutes'`?
  - Put the 30 minutes in one module constant `MONITORING_WINDOW = timedelta(minutes=30)`.
  - The reason text is `No live vessel contact in the last 30 minutes.`
- `web/js/dashboard/dashboard-ai-ops.js`:
  - Delete `anomalyRows()` and read `payload.rows` directly (the one shape the backend now sends).
  - If `payload.rows` is not an array (a bare list or a malformed body), call `renderRiskFeed(null, 'offline')`, the existing "feed unavailable" state; never render it as an empty all-clear.
  - Keep reading `payload.monitoring` and `payload.monitoring_reason` as today.

**Web red test** - add to `web/test/dashboard-runtime.test.js`, using the existing stub harness:
- `anomaly feed renders Not monitoring for an empty unavailable payload`: serve `{rows: [], monitoring: 'unavailable', monitoring_reason: 'No live vessel contact in the last 30 minutes.'}` and assert `#ai-risk-list` contains `Not monitoring - no live contact source`.
- `anomaly feed ignores a bare list`: serve `[]`, a bare list, and assert the list shows the unavailable-feed state, not an empty all-clear.
  Red reason: `anomalyRows([])` treats a bare list as valid rows.

Commit: `fix(anomaly): report fleet-wide monitoring status at the top of the risk feed`

### F4 - A fisher reply marks a call reopened only when it really reopens

**Defect.**
`backend/app/api/sos.py` `_apply_fisher_reply` (about line 740) sets `reopened_at = NOW()` and `reopened_by = 'fisher'` on every `STILL_IN_DANGER` reply, including on calls that were never resolved, and it writes no audit record when it does reopen.
The phone (`mobile/lib/services/sos_service.dart` about line 640) then treats the call as reopened on every reconcile and clears the fisher's own reply each time.

**Red tests, backend** - add to `backend/tests/test_edge_lifecycle_pg.py`:
- `test_still_in_danger_on_open_incident_does_not_mark_reopened`: an open, never-resolved event; reply `1` by `local_id`; assert `reopened_at IS NULL` and `reopened_by IS NULL` in the row, and `fisher_reply = 1`.
- `test_still_in_danger_reopen_is_audited`: resolved 30 minutes ago; reply `1`; assert `reopened_by = 'fisher'`, `reopened_at` set, and an `operations_audit_events` row with `action = 'sos.reopen'` for that event.
- Red reasons: the first gets `reopened_at` set; the second finds no audit row.

**Red tests, mobile** - add to `mobile/test/sos_service_test.dart`:
- `fisher reply survives reconcile when the incident was never closed`: a local record never resolved, with `fisherReply = 1` saved; the fake backend returns the same row with `reopened_at` set and `resolved_at` null; after two `reconcile()` calls the record still has `fisherReply == 1`.
- `a reopen clears a closed record once, not on every reconcile`: a local record resolved at T; the remote row has `reopened_at` at T + 1 min and `resolved_at` null; after the first reconcile the record is no longer resolved; then save `fisherReply = 1`; after a second reconcile with the same remote row, `fisherReply` is still 1.
- Red reason: `isReopened` is true whenever the local record is unresolved, so `clearResolved` wipes the reply.

**Change.**
- `backend/app/api/sos.py` `_apply_fisher_reply`:
  - Pass the computed `reopen` boolean into the SQL as a parameter, and set `reopened_at` and `reopened_by` only when it is true.
  - When `reopen` is true, call `record_audit_event(conn, actor=None, action='sos.reopen', resource_type='sos_event', resource_id=row['id'], outcome='updated', metadata={'reopened_by': 'fisher'}, is_demo=row['is_synthetic'])` inside the same transaction.
    Check `record_audit_event`'s signature in `backend/app/audit.py` and match it exactly.
- `mobile/lib/services/sos_service.dart`: `isReopened` requires `localResolved != null && remoteReopened.isAfter(localResolved)`; drop the `localResolved == null ||` branch.

Commit: `fix(sos): only a real reopen marks a call reopened, and it is audited`

### F5 - A fisher's SAFE_NOW closes the call as `stood_down_by_fisher`

**Defect.**
`_apply_fisher_reply` stores `resolution_code = 'safe_confirmed'` for a `SAFE_NOW` reply.
`docs/13` "Resolution codes" says a fisher's `SAFE_NOW` is `stood_down_by_fisher`; `safe_confirmed` means the dispatcher reached the boat.

**Red test** - add to `backend/tests/test_edge_lifecycle_pg.py`:
- `test_safe_now_reply_stores_stood_down_by_fisher`: an open event; reply `2`; assert `resolution_code == 'stood_down_by_fisher'` in the row and in `GET /api/sos/ack/{local_id}`.

**Change** - `backend/app/api/sos.py`: use `ResolutionCode.STOOD_DOWN_BY_FISHER.value`, passed as a parameter rather than a SQL literal.

**Also allowed in F5 (Revision 2)** - `backend/tests/test_responder_loop.py`, the `_FakePool.fetchrow` branch for `UPDATE sos_events ... SET fisher_reply` only.
Its guard test `test_safe_now_resolves_and_removes_the_event_from_the_active_feed` breaks because the fake unpacks four SQL parameters and F5 adds a fifth.
The fake also still re-implements the two-hour reopen rule and names its fourth parameter `still_in_danger`, which F4 turned into the `reopen` boolean.
Make the fake mirror the real SQL exactly and decide nothing itself:

```python
event_id, reply, safe_now, reopen, safe_now_code = args
event = self.sos_events.get(int(event_id))
if event is None:
    return None
event['fisher_reply'] = reply
event['fisher_replied_at'] = datetime.now(UTC)
event['resolved_at'] = datetime.now(UTC) if reply == safe_now else None
event['resolution_code'] = safe_now_code if reply == safe_now else None
if reopen:
    event['reopened_at'] = datetime.now(UTC)
    event['reopened_by'] = 'fisher'
event['version'] += 1
return event
```

The "already resolved and not reopening" early return stays in `_apply_fisher_reply`, which runs before the SQL, so the fake must not repeat it.
Remove any import in that test file that this leaves unused (ruff will say).
Every other test in `test_responder_loop.py` must stay green unchanged.

Commit: `fix(sos): a fisher stand-down closes the call as stood_down_by_fisher`

### F6 - `many_calls_same_vessel` fires at two open calls

**Defect.**
`backend/app/incidents/plausibility.py` (about line 49) raises the flag at 3 or more open calls; `docs/05` E5.4 says above 1.

**Red test** - in `backend/tests/test_plausibility.py`:
- Add `test_many_calls_flag_at_two_open_calls`: `open_calls_for_vessel=2` gives the flag; `open_calls_for_vessel=1` does not.
- The existing test using `open_calls_for_vessel=3` stays (it still holds).

**Change**: `if context.open_calls_for_vessel > 1:`.

Commit: `fix(triage): flag many calls from one vessel at two open calls`

### F7 - Scheduler reports the contract's job names

**Defect.**
`backend/app/scheduler.py` (about line 98) runs jobs named `sos-escalation` and `anomaly-evaluation`, so `GET /api/ops/status` reports `scheduler_last_run` under those keys; `docs/05` E5.7 says `escalation` and `anomaly`.

**Red tests** - add to `backend/tests/test_edge_scheduler_pg.py`:
- `test_ops_status_scheduler_keys_match_contract`: run `scheduler.run_job_once` for both production job ids (import them from `app.scheduler`, see Change), then `GET /api/ops/status`; assert `set(body['scheduler_last_run']) == {'escalation', 'anomaly'}`.
- `test_scheduler_starts_the_contract_jobs`: monkeypatch `scheduler._run_periodically` with a recorder, call `await scheduler.start()`, then `await scheduler.stop()`; assert the recorded job ids are exactly `{'escalation', 'anomaly'}`.
- Red reason: the ids are `sos-escalation` and `anomaly-evaluation` (the first test fails on import until you add the constants, which counts as red).

**Change** - `backend/app/scheduler.py`: add `ESCALATION_JOB = 'escalation'` and `ANOMALY_JOB = 'anomaly'` and use them in `start()`.
Also remove the unused `_app_state` parameter from `start()`, and update its one caller in `backend/app/main.py`.

Commit: `fix(ops): scheduler job names match the ops status contract`

### F8 - A failed escalation SMS is retried

**Defect.**
`backend/app/scheduler.py` `run_escalation_job` sets `escalated_at` before sending, and never clears it when `send_sms` returns `FAILED`, so a call whose SMS failed is never escalated again.

**Red tests** - add to `backend/tests/test_edge_scheduler_pg.py`:
- `test_failed_sms_is_retried_on_the_next_run`: seed one unacknowledged, non-synthetic event older than 2 minutes; monkeypatch `scheduler.send_sms` to return `NotifyResult.FAILED` on the first call and `NotifyResult.SENT` on the second; run `run_escalation_job()` twice; assert `send_sms` was called twice, `escalated_at` is set at the end, and the audit rows for that event have outcomes `failed` then `sent`.
- `test_unconfigured_sms_is_not_retried`: `send_sms` returns `NotifyResult.NOT_CONFIGURED`; run twice; assert one call, `escalated_at` set, one audit row.
- Red reason: the second run of the first test sends nothing.

**Change** - `run_escalation_job` only: when the result is `NotifyResult.FAILED`, set `escalated_at = NULL` for that event in the same transaction that records the audit event.
`NOT_CONFIGURED` keeps `escalated_at` set, so an unconfigured deployment does not re-audit every 30 s.

Commit: `fix(ops): retry an escalation whose SMS failed`

### F9 - Line endings and rationale comments in `sos.py` and `anomaly_service.py`

No behaviour changes, so there are no red tests; every gate must stay green.

- **Line endings.**
  `backend/app/api/sos.py` is CRLF on `master` and now mixes CRLF and LF.
  Convert it to CRLF throughout.
  Verify: `file backend/app/api/sos.py` reports only CRLF line terminators, and `git diff master --ignore-cr-at-eol --stat -- backend/app/api/sos.py` does not change from before the conversion.
- **Restore the reasons the agents deleted** (the facts below are still true; do not add anything else):
  - `backend/app/api/sos.py`, `sos_downlink` docstring, replace the one-line docstring with:

    ```python
    """The responder's answer to each live call, for the LoRa shore gateway.

    Deliberately not gateway-key access to /active: /active carries position,
    the fisher's note and the owner's name, licence and phone, and the gateway
    key ships in firmware on a mast. This returns only what the gateway is
    about to broadcast to the boat in clear anyway.

    One row per vessel, its newest call: the gateway downlink and the buoy
    cache are keyed by vessel, so older calls used to overwrite the newer one
    and the fisher was told about the oldest.

    delivery_state is collapsed here so firmware never carries a second copy
    of delivery_state() that only a reflash could correct.

    Resolved calls stay for RESOLVED_WINDOW so a closure between two 45 s polls
    still goes out; select_downlink caps the feed at DOWNLINK_MAX to fit the
    gateway and buoy tables.
    """
    ```

  - `backend/app/api/sos.py`, `ingest_sos`, restore the two SEC-06 comments above the `trust_tier` block and above the `has_valid_gateway` block exactly as they read on `master` (`git show master:backend/app/api/sos.py`).
  - `backend/app/ai/anomaly_service.py`, replace the comment above `OPEN_TRIP_FRESHNESS_WINDOW` with:

    ```python
    # How long after a vessel's last at-sea contact its latest trip stays
    # eligible. Was 12 h (decided 2026-08-29, docs/08); raised to 72 h for
    # EC-H9 so a boat silent overnight is still evaluated instead of dropping
    # out. Trips from earlier days still age out, so the wall-clock re-alert
    # flaw found in docs/31 stays fixed.
    ```

Commit: `chore(sos): restore CRLF line endings and the downlink rationale`

### F10 - Over-engineering cuts

No behaviour changes, so there are no red tests; the existing tests are the guard and must stay green, with the same counts.
If a cut breaks a test, the cut is wrong: revert it and note it in the evidence file instead of changing the test.

1. `mobile/lib/services/sos_service.dart`: the three near-identical matching loops in `_applyRemote` (by `localId`, then `nonce`, then `seq`) become one local helper `void claim(bool Function(SosRecord, RemoteSos) matches)` called three times with the three predicates, keeping the same order and the same "claimed events" rule.
2. `backend/app/api/sos.py` `_upsert_sos`: the `alt_latitude` and `alt_longitude` `CASE` blocks repeat the same 1 km condition; build the condition string once in Python and use it in both.
3. `web/js/dashboard/dashboard-incidents.js`: delete the hand-rolled `utf8ByteLength` fallback (lines 17 to 28); use `ns.utf8ByteLength`, which `dashboard-core.js` always sets.
4. `backend/app/ai/anomaly_service.py`: the handset filter is applied twice; keep the one in `_load_trip_rows` and delete the one in `_group_latest_trips`.
5. `backend/app/notify.py`: delete `_SEND_LIMIT` (the scheduler's advisory lock already makes sending single-writer), and move the duplicated `ONCALL_SMS_NUMBERS` parsing into one `_oncall_numbers()` function used by both `sms_configured()` and `send_sms()`.
6. `backend/app/incidents/lifecycle.py`: inline `can_reopen()` and `resolution_code_from()` at their call sites in `backend/app/api/sos.py`, then delete them; keep `ResolutionCode`, `REOPEN_WINDOW` and `fisher_reply_reopens`.
   Update `backend/tests/test_incident_lifecycle.py` only where it imports the two deleted functions, by deleting those test cases (their behaviour is covered by `test_edge_lifecycle_pg.py`).
7. `mobile/lib/core/config.dart`: delete the `maxBoatLength` and `maxNoteLength` aliases and rename their callers to `maxBoatBytes` and `maxNoteBytes`.
8. `mobile/lib/ui/widgets/closure_text.dart`: list only the non-default groups (`rescued`, `safe_confirmed`, `stood_down_by_fisher` to `sosClosedByMdrrmo`; `duplicate` to `sosClosedDuplicate`) and let `default` return `sosClosedUnconfirmed`.
9. `web/js/dashboard-utils.js` `deliveryLabel`: drop `event.pod_id`, which no feed sends; use `event.buoy_id`.

Commit: `refactor(edge): remove duplication and dead flexibility found in review`

---

## 5. Finish

- [ ] All gates green against the baseline, with only your added tests on top.
- [ ] `git log --format=%B master..edge/fixes` contains no "Co-Authored-By" line and no agent name in any commit you made.
- [ ] Every fix section in `EVIDENCE-fixes.md` has: the red run (for F1 to F8), the green run, and the gate numbers.
- [ ] `Pending - Len` lines are listed together at the end of the evidence file.
- [ ] `HANDOFF.md`: **Status** `COMPLETED`, **The Baton** "Claude reviews `edge/fixes` against docs/63, then Len merges it into `master`".
- [ ] `git push origin edge/fixes`, then stop.

## 6. Stop and wait for Len when

- a gate still fails after three attempts;
- a fix seems to need a file its section does not name, or a contract change;
- the baseline in step 0 does not match;
- anything would require touching `master`, Render, credentials or a dependency.

## Recovery

Follow `AGENTS.md` "Recovery".
Interrupted work stays uncommitted, and `HANDOFF.md` records the exact next step and the attempt count.
