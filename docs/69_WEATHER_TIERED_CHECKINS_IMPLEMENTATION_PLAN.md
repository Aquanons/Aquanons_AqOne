# Implementation Plan: Weather-tiered check-ins (fleet watch)

**Status:** APPROVED - Revision 2; Phase 1 complete; Phase 2 detailed plan awaiting approval
**Owner:** Lenard (plan, backend, review), Daniel (firmware bench, shore hardware), Arnold (dashboard, gateway review)
**Created:** 2026-09-26T09:50:00+08:00
**Updated:** 2026-09-26T10:10:00+08:00
**Related:** `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md`, `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md` (Phases 3, 4, 7), `docs/67_STAGNANT_MODE_IMPLEMENTATION_PLAN.md`

Revision: 2
**Execution mode:** hard-stop
Feature spec and revision: `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md` Revision 3, approved 2026-09-26T09:50:00+08:00
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`, `docs/66` "Clean Architecture applied" (firmware policy header and host test)
Len's chat approval, 2026-09-26T09:50:00+08:00, of Revision 1: "Alright i approve of this decision lets work on it alongside the ui improvement workflow. Make sure to make a full scan of the documentations first before to ensure that stale files can be updated and conflicts is avoided".
Revision 2 (2026-09-26T10:05:00+08:00) adds only what that documentation scan found: doc-update tasks in Phases 1, 4, 7 and 8, the stale `docs/02` facts Phase 1 reconciles, and the parallel-workflow rules below. No behaviour or acceptance criterion changed.
Target branch: Phase 1 (contracts, Claude) on `master`; Phases 2 onward on `feat/fleet-watch` in its own worktree `../AqOne-fleet-watch` with its own `HANDOFF.md` (`docs/58`), each verified phase merged to `master` and pushed (Len: push verified work straight to `master`)
Roles: Claude writes each phase's red tests first; the implementer is the agent named in the root `HANDOFF.md`; Claude reviews; Daniel runs every bench step; Len flashes boards and deploys to Render.

Execution mode is `hard-stop` by the default rule: the plan changes shared contracts, migrations, backend, dashboard and firmware, and has more than 3 phases.

## Scope

Every requirement of `docs/68` Revision 3, `FEAT-068/REQ-001` to `FEAT-068/REQ-032`.
Each is mapped to exactly one phase below; the table at the end is the cross-check.

Existing work to preserve:
- The untracked `AqOne_Story_and_Data_Flow.md` is not ours; never stage it.
- Plan 65 work lives in `../AqOne-fisher-ux` on `ux/fisher-friction`; this plan touches no `mobile/` file.
- Plan 66 owns `AqOnePolicy.h`, `firmware/test/policy_test.cpp` and `provision_pod.py`; Phases 6 and 7 here add to them only after plan 66 has created them.

Running alongside plan 65 (Len, 2026-09-26T09:50:00+08:00):
- The two plans share no code path: plan 65 changes `mobile/`, `docs/06` and `docs/22`; this plan never touches them.
- Both append dated entries to `docs/08` and edit `docs/SPEC_INDEX.md` and `docs/README.md`; each checkpoint rebases on `origin/master` immediately before its commit, so those edits never collide.
- The backend and dashboard phases here change no endpoint the handset calls.

Documentation scan, 2026-09-26 (what Revision 2 is based on):
- Updated now, outside any phase: `docs/33` (the SF10 airtime was for a 94-byte frame; a real SOS is 1.6 to 2.3 s), `docs/13` (its plan to repurpose `0x04` is superseded), `docs/61` D10 (the gateway no longer posts a contact per frame), `docs/67` (conflict note: `STATUS` becomes the check-in, with 2 bytes reserved for stagnant mode), `docs/66` Phase 7 (slot enrolment extends `provision_pod.py`), `docs/55` and `docs/56` (the check-in receiver and the new input, marked not built), the PRD §5.2 roadmap item and `docs/07` amendment, and the registers.
- Stale, fixed in Phase 1 because they are contract text: `docs/02` still says payloads are at most 64 bytes and frames 94 bytes (firmware allows 225 and 255), lists 433 MHz and SF7 (firmware ships 915 MHz and SF10), and gives `STATUS` a JSON body nobody sends.
- Stale only once this plan ships, so fixed in the phase that makes them stale: `CLAUDE.md`, `AGENTS.md`, `README.md` and `firmware/README.md` say "two sketches" (Phase 7); `docs/18` lists two scheduler jobs (Phase 4); the firmware comment "roughly a second for a full frame" in `AqOneLoam.h` (Phase 7); `docs/16` and `docs/17` (Phases 4 and 8).
- Checked and left alone: `docs/08`'s dated 12 h freshness entry is a ledger record, and the code's 72 h window came later from `docs/62A` B7; `docs/guides/01_CONTRACTS.md` has an old enum table, but the guides README already says the numbered contracts win; `docs/23` and `docs/38` agree with this feature; plan 65 and `docs/64` do not overlap it.

## Dependencies and order

| Phase | Outcome | Can start when |
|---|---|---|
| 1 | Contracts written | Plan approved |
| 2 | Pure backend policy | Phase 1 |
| 3 | Storage, tier and slot endpoints | Phase 2 |
| 4 | Check-in ingest and missed-check-in detection | Phase 3 |
| 5 | Dashboard | Phase 4 |
| 6 | Pure firmware policy | Phase 5, and plan 66 Phase 3 done |
| 7 | Firmware adapters and the check-in receiver | Phase 6, plan 66 Phases 4 and 7 done (D5 answered), second shore board in hand |
| 8 | Bench evidence | Phase 7 flashed by Len |

Phases 1 to 5 need no hardware and can run now, subject to Len's sequencing against plans 66 and 65.
Len removed the outdoor range test and NTC confirmation as prerequisites (2026-09-26T09:42:00+08:00).

## Architecture placement

```text
backend/app/
  fleet_watch/                 NEW, framework-free (purity test like app/incidents)
    tier.py                    INTERVALS, Tier, fleet_tier(signals, override, now)
    watch.py                   is_watched, missed_deadline, evaluate_vessel, fleet_silence
    trips.py                   trip_action(checkin, open_trip, at_sea) -> open | attach | complete | none
    slots.py                   assign_slot(taken) -> 0..79 or FleetFull
    ports.py                   WeatherSignalSource, CheckinStore, CaseSink, SlotRegistry (Protocols)
    use_cases.py               publish_tier, ingest_checkins, evaluate_watch, enrol_slot
  api/fleet_watch.py           NEW adapter: tier (gateway), raise/end (dispatcher), batch ingest,
                               slot enrolment (admin), check-in history (mdrrmo, admin)
  fleet_watch_sql.py           NEW adapter: the SQL behind the four ports
  scheduler.py                 adds the 60 s watch job and the daily retention job
  ai/anomaly_service.py        skips contact_type = 'checkin' (REQ-032)
migrations/038_fleet_watch.sql NEW
firmware/
  */AqOnePolicy.h              adds adoptTier, nextCheckinAt, inHarbor, check-in codec, beacon time
  checkin/AqOneCheckin/        NEW third sketch: check-in receiver; byte-identical AqOneLoam.h and AqOnePolicy.h
  tools/AqOneLoadEmulator/     NEW test-only sketch: 50 emulated slots; never ships
web/js/dashboard/              tier banner, missed-check-in cases, last check-in
```

The third sketch is chosen over an `#if` build of the shore sketch: the receiver shares no behaviour with the SOS gateway beyond the two headers, and the existing identity test already proves header copies match.
`app/geo.py` is passed into the policy as a function; the policy never imports it.

## Gate commands

Run from the repository root.
Every phase runs the gates for the layers it touches.

```powershell
# Backend. DB-backed tests need a localhost Postgres admin URL; if they skip, the phase is not complete.
$env:AQONE_PROBE_PG_ADMIN_URL = "<localhost admin URL, from Len>"
cd backend; python -m ruff check .; python -m pytest -q

# Web
node --test web/test/*.test.js
Get-ChildItem web/js, web/test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }

# Firmware (scratch AqOneSecrets.h from each .example, deleted afterwards)
pio run -d firmware
git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/checkin/AqOneCheckin/AqOneLoam.h
git diff --no-index firmware/buoy/AqOneBuoy/AqOnePolicy.h firmware/shore/AqOneShore/AqOnePolicy.h
git diff --no-index firmware/buoy/AqOneBuoy/AqOnePolicy.h firmware/checkin/AqOneCheckin/AqOnePolicy.h
g++ -std=c++17 -Wall -Wextra -Werror -I firmware/buoy/AqOneBuoy firmware/test/policy_test.cpp -o $env:TEMP/policy_test.exe; & $env:TEMP/policy_test.exe
```

The `checkin` diffs apply from Phase 7, when that sketch exists.

## Phase 1: Contracts written

Requirements: the contract rows of `docs/68` Section 6 (they carry REQ-004, 005, 009, 012, 015, 016, 022, 025, 027, 028, 029, 031)
State: Complete 2026-09-26 (evidence: `docs/fleet-watch/EVIDENCE.md`)

### Tasks

- [x] `docs/02`, stale facts first: payload cap 225 bytes and frame cap 255 bytes, as `AqOneLoam.h` enforces; radio parameters 915 MHz, SF10, 125 kHz, CR 4/5, as shipped (band still subject to `docs/62D` M11); `STATUS`'s unused JSON body replaced by the check-in below; a note that every board shares `LOAM_KEY` today until plan 66 Phase 5.
- [x] `docs/02`: check-in channel (`LORA_CHECKIN_FREQ_MHZ`, in the same band and moving with `LORA_FREQ_MHZ` if M11 changes it; slot cycle 120 s, slot 1.5 s, 80 slots); binary `T_STATUS` check-in payload byte table (at most 16 bytes, fix absent marker, last 2 bytes reserved as `stagnant_min` for plan 67 and sent as 0), with one worked example in hex; the "payloads are JSON" exception; `T_PING` fields `ct`, `cx` and the millisecond time field; the relay rule of REQ-012.
- [x] `fixtures/loam/checkin_v1.json`: the worked example (frame hex and decoded values), the single source for the Phase 6 codec test.
- [x] `docs/04`: `POST /api/v1/checkins` batch (up to 128, per-item result), `GET /api/v1/fleet-tier` (gateway key), `POST /api/v1/pods/{pod_id}/enrol` (`lgu` or `admin`, like device pairing; returns vessel and slot); `contact_type = 'checkin'`, implicit trips (D11).
- [x] `docs/05`: `GET /api/fleet-watch/tier`, `POST` and `DELETE /api/fleet-watch/tier/raise` (mdrrmo, admin), missed-check-in cases in the existing anomaly case endpoints with `case_kind`, `GET /api/fleet-watch/vessels` (last check-in per vessel, for REQ-027) and `GET /api/fleet-watch/vessels/{id}/checkins` (mdrrmo, admin), `/api/ops/status` additions.
- [x] Tell Daniel and Arnold the contracts changed (message drafted in the evidence file for Len to send).

### Verification

- [x] Backend gates green (the security and identity tests read `docs/02` indirectly).
- [x] Claude review: every field named in `docs/68` Section 5 appears in exactly one contract; no contract contradicts `docs/06`.

### Review and checkpoint

- [x] Update this plan, `docs/fleet-watch/EVIDENCE.md` (new) and the handoff; commit.

Checkpoint message: `docs(fleet-watch): contracts for weather-tiered check-ins`
Stop for Len's go-ahead (hard-stop).

## Phase 2: Pure backend policy

Requirements: REQ-001, REQ-002, REQ-003 and REQ-004 (rules only), REQ-016 (trip decision), REQ-018, REQ-019, REQ-021 (decision), REQ-024, REQ-031 (slot choice)
State: Detailed plan drafted, awaiting Len's approval; no code yet (Len, 2026-09-26: "only creating an implementation plan")
Detailed plan: [`docs/fleet-watch/PHASE_2_PLAN.md`](fleet-watch/PHASE_2_PLAN.md) (module API, red tests T2-01 to T2-44, gates, findings P1 to P4)

### Tasks (red tests first)

- [ ] Red tests (Claude, commit 1): `tests/test_fleet_watch_tier.py`, `test_fleet_watch_watch.py`, `test_fleet_watch_trips.py`, `test_fleet_watch_slots.py`, and `app.fleet_watch` added to `tests/test_incidents_is_pure.py`, exactly as the detailed plan lists them.
- [ ] Implement `app/fleet_watch/` (`tier.py`, `watch.py`, `trips.py`, `slots.py`) until green; no I/O, no `datetime.now()` inside policy. `ports.py` moves to Phase 3, where its first consumer is.

### Verification

- [ ] Backend gates green, same skip count as `master`.
- [ ] Static test T2-26 shows the interval literals only in `fleet_watch/tier.py` (REQ-001). It replaces the earlier `rg` check, which could never pass because `240` is already a note length in `api/catch.py` and `api/trips.py`.

### Review and checkpoint

- [ ] Update plan, evidence, handoff; commit.

Checkpoint message: `feat(fleet-watch): pure tier, watch and slot policy`
Stop for Len's go-ahead (hard-stop).

## Phase 3: Storage, tier and slot endpoints

Requirements: REQ-003, REQ-004, REQ-031, REQ-032 (schema)
State: Awaiting approval

### Tasks (red tests first)

- [ ] `tests/test_fleet_watch_pg.py` (DB-backed): migration 038 applies on a disposable database; one trip holds one case of each `case_kind`; a duplicate slot is refused by the database.
- [ ] `tests/test_fleet_watch_api.py`: tier from advisories; raise to Severe for 2 h reflected; 13 h rejected 422; lowering rejected 422; one audit row per raise and end; gateway tier read returns `tier`, `interval_s`, `rev`, `exp` with `rev` stable and `exp` moving when nothing changes; enrolment gives distinct slots, keeps a re-enrolled pod's slot, refuses the 81st; no key 401; wrong role 403.
- [ ] `migrations/038_fleet_watch.sql`: `pod_enrolments` (pod_id, vessel_id, slot unique 0..79, enrolled_at); `fleet_tier_raises` (tier, reason, expires_at, raised_by, ended_at); `fleet_tier_state` (single row: tier, rev, updated_at); `buoy_contacts` columns `fix_age_s`, `battery_pct`, `path` (`direct` or `relayed`); `anomaly_cases.case_kind` default `trip_profile`, unique on (vessel_id, trip_id, case_kind) replacing the old unique.
- [ ] `fleet_watch_sql.py` adapters for `WeatherSignalSource` (advisories), `SlotRegistry`, and the tier state; `api/fleet_watch.py` routes for tier, raise, end and enrolment, calling the use cases.

### Verification

- [ ] Backend gates green, DB-backed tests not skipped.

### Review and checkpoint

- [ ] Update plan, evidence, handoff; commit.

Checkpoint message: `feat(fleet-watch): tier, raise and pod slot enrolment`
Stop for Len's go-ahead (hard-stop).

## Phase 4: Check-in ingest and missed-check-in detection

Requirements: REQ-015, REQ-016, REQ-017, REQ-020, REQ-021, REQ-022 (backend), REQ-023, REQ-025, REQ-026, REQ-028, REQ-032 (model)
State: Awaiting approval

### Tasks (red tests first)

- [ ] API and DB tests for: batch idempotency; unknown pod rejected per item; implicit trip open, reuse and complete, and a handset trip never completed; `observed_at` from the receiver and `fix_age_s` stored; missed case raised no later than 60 s after the deadline in a replay; `case_type` `responder_attention` for high confidence and `verification` for low; fleet-silence condition in `/api/ops/status` and low-confidence marking; "check-in resumed" auto-resolve with history; no check-in position in any `/api/public/*` response; history 403 for `lgu`, 401 anonymous; retention deletes a 31-day unattached row and keeps an attached one; capacity warning at 71 slots and at relayed share above 20%; `anomaly_service` unchanged by check-in rows.
- [ ] Batch ingest route and `CheckinStore` adapter; `ingest_checkins` use case applies `trip_action`.
- [ ] `evaluate_watch` use case and `CaseSink` adapter writing `case_kind = 'missed_checkin'`; scheduler job at 60 s; daily retention job.
- [ ] `anomaly_service._load_trip_rows` skips `contact_type = 'checkin'`.
- [ ] `/api/ops/status`: fleet silence, receiver last upload, slots assigned, check-ins per cycle, relayed share, warnings.
- [ ] Docs this phase makes stale: `docs/18` (the `fleet_watch` package and the two new jobs), `docs/17` (a plain-language paragraph on check-ins and missed-check-in cases).

### Verification

- [ ] Backend gates green, DB-backed tests not skipped.
- [ ] Local end-to-end with synthetic batches posted by a script from the evidence folder: a vessel checks in at sea at Severe, stops, and its case appears in `GET /api/ai/anomaly/cases/open` within 8.2 min of simulated time; a harbor stop raises nothing.

### Review and checkpoint

- [ ] Update plan, evidence, handoff; commit.

Checkpoint message: `feat(fleet-watch): check-in ingest and missed-check-in cases`
Stop for Len's go-ahead (hard-stop).

## Phase 5: Dashboard

Requirements: REQ-003 (raise control), REQ-022 (display and alarm), REQ-027
State: Awaiting approval

### Tasks (red tests first)

- [ ] `web/test/dashboard-fleet-watch.test.js`: tier banner text for each tier and source; expiry shown; raise form sends reason and expiry and refuses more than 12 h client-side; a missed-check-in case renders every REQ-022 field; alarm rings only for a high-confidence Severe missed case; "last check-in N min ago" formatting.
- [ ] `web/js/dashboard/dashboard-fleet-watch.js` (banner, raise control, last check-in) and the missed-check-in variant in `dashboard-trip-checks.js`, using the existing case actions and `dashboard-alarm.js`.

### Verification

- [ ] Web gates green.
- [ ] Browser check against a local backend at 1280 px, light and dark, with real mouse events: publish a `Warning` advisory and see the banner change within 60 s naming it; raise to Severe with a reason; a synthetic silent vessel produces a case with every field; acknowledge, escalate, dismiss and resolve work; no SOS incident row appears. Screenshots in `docs/fleet-watch/`.

### Review and checkpoint

- [ ] Update plan, evidence, `docs/08` (dated entry: backend and dashboard done, firmware pending) and handoff; commit.
- [ ] Len deploys to Render; `/health/ready` reports the commit.

Checkpoint message: `feat(fleet-watch): tier banner and missed-check-in cases on the dashboard`
Stop for Len's go-ahead (hard-stop).

## Phase 6: Pure firmware policy

Requirements: REQ-006, REQ-007, REQ-008, REQ-009, REQ-010 (decision), REQ-011, REQ-012 (decision)
State: Awaiting approval; gated on plan 66 Phase 3
Owner: agent (code), Daniel (review)

### Tasks (red tests first)

- [ ] `policy_test.cpp`: every `policy_test.cpp` criterion of the listed requirements; the codec round-trips `fixtures/loam/checkin_v1.json` byte for byte; slot 7 lands at 10.5 s of each cycle and at the right cycle per tier; harbor and relayed fallbacks; a 10 min old clock leaves the check-in channel.
- [ ] `tools/gen_harbor_zones.py`: writes the harbor zone constants from `app/geo.py` shore stations into both `AqOnePolicy.h` copies; `tests/test_fleet_watch_harbor.py` fails if the header and `app/geo.py` disagree.
- [ ] Implement in `AqOnePolicy.h` (both copies, byte-identical): `adoptTier`, `nextCheckinAt`, `inHarbor`, `useCheckinChannel`, `encodeCheckin` and `decodeCheckin`, `beaconTime`.

### Verification

- [ ] Firmware gates green (host test, both builds, identity diffs empty).
- [ ] Backend gates green (identity and header-purity tests).

### Review and checkpoint

- [ ] Update plan, evidence, handoff; commit.

Checkpoint message: `feat(fleet-watch): pod check-in schedule and codec in the policy header`
Stop for Len's go-ahead (hard-stop).

## Phase 7: Firmware adapters and the check-in receiver

Requirements: REQ-005, REQ-010 (TX ring), REQ-012 (relay), REQ-013, REQ-014, REQ-029, REQ-030
State: Awaiting approval; gated on plan 66 Phases 4 and 7 (D5) and a second shore board
Owner: agent (code), Daniel (bench), Len (flash)

### Tasks

- [ ] Pod (`AqOneBuoy.ino`): read the tier and time from the beacon; send the check-in in its slot on the check-in channel and switch back; skip the slot when an SOS, ACK, ETA or chat frame is waiting; relayed fallback on the SOS channel; relays forward a relayed check-in at most 2 hops.
- [ ] Shore (`AqOneShore.ino`): read `GET /api/v1/fleet-tier` every 60 s; beacon carries `ct`, `cx` and milliseconds; forward relayed check-ins heard on the SOS channel into the same batch endpoint through its existing upload path.
- [ ] `firmware/checkin/AqOneCheckin/`: listen on the check-in channel only; 128-entry buffer with duplicate drop and oldest-first eviction; batch upload every 30 s over verified TLS with `X-Api-Key`; no code path touches the SOS channel.
- [ ] `firmware/tools/AqOneLoadEmulator/`: 50 test pod IDs in slots 0 to 49 at the Severe tier; build env excluded from `default_envs`.
- [ ] `platformio.ini`: `checkin` env (and `loademu`, not default); extend `test_security_regressions.py` to the third header copies; `provision_pod.py` asks the backend for the pod's slot at enrolment and writes it with the vessel ID.
- [ ] Static probe: no check-in upload code in the shore build (REQ-013).
- [ ] Docs this phase makes stale: "two sketches" becomes three in `CLAUDE.md`, `AGENTS.md` (repository layout), `README.md` and `firmware/README.md`, with the identity `diff` commands for the third copy; `docs/19` gains the check-in flow; the `AqOneLoam.h` comment "roughly a second for a full frame" is corrected (both copies).

### Verification

- [ ] Firmware and backend gates green; `pio run -d firmware -e loademu` builds.
- [ ] Two-board smoke test (Daniel): one pod and the receiver; the pod's check-ins land in `buoy_contacts` with the right slot timing in the receiver log.

### Review and checkpoint

- [ ] Update plan, evidence, handoff; commit.

Checkpoint message: `feat(fleet-watch): pod check-ins, check-in receiver and load emulator`
Stop for Len's go-ahead (hard-stop).

## Phase 8: Bench evidence

Requirements: `docs/68` Section 1 success criteria, REQ-014, REQ-029, REQ-030, the power constraint
State: Awaiting approval
Owner: Daniel (bench), Claude (records)

### Verification

- [ ] A pod switched off "at sea" (GPS fix outside the harbor zone, or a test fix) raises a missed-check-in case within 9 min at Severe and 16 min at Elevated; Normal's 52 min is covered by the Phase 4 replay test, and the bench runs it once if time allows.
- [ ] A pod switched off inside the harbor zone raises nothing in 30 min at Severe.
- [ ] Load emulator on for 1 h at Severe: at least 99% of emulated check-ins reach the backend; SOS dashboard latency over 10 SOS sends is within 10% of 10 sends with the emulator off.
- [ ] Two pods' slot start times stay within 100 ms over 1 h (REQ-029); a pod's time off the SOS channel is under 1% (REQ-030).
- [ ] Receiver uplink unplugged for 10 min, then restored: the newest 128 check-ins upload (REQ-014).
- [ ] Pod extra daily charge at Severe measured and recorded.

### Review and checkpoint

- [ ] Evidence in `docs/fleet-watch/EVIDENCE.md`; dated entry and status row in `docs/08`; `docs/16` gains the accepted risks A2 and A4.
- [ ] Update plan and handoff; commit.

Checkpoint message: `docs(fleet-watch): bench evidence for weather-tiered check-ins`
Stop for Len (plan complete).

## Requirement cross-check

| Requirement | Phase | Requirement | Phase |
|---|---|---|---|
| REQ-001 | 2 | REQ-017 | 4 |
| REQ-002 | 2 | REQ-018 | 2 |
| REQ-003 | 3, 5 | REQ-019 | 2 |
| REQ-004 | 3 | REQ-020 | 4 |
| REQ-005 | 7 | REQ-021 | 2, 4 |
| REQ-006 | 6 | REQ-022 | 4, 5 |
| REQ-007 | 6 | REQ-023 | 4 |
| REQ-008 | 6 | REQ-024 | 2 |
| REQ-009 | 6 | REQ-025 | 4 |
| REQ-010 | 6, 7 | REQ-026 | 4 |
| REQ-011 | 6 | REQ-027 | 5 |
| REQ-012 | 6, 7 | REQ-028 | 4 |
| REQ-013 | 7 | REQ-029 | 7, 8 |
| REQ-014 | 7, 8 | REQ-030 | 7, 8 |
| REQ-015 | 4 | REQ-031 | 2, 3 |
| REQ-016 | 2, 4 | REQ-032 | 3, 4 |

## Recovery

Follow project `AGENTS.md` for the three-attempt limit and immediate blockers.
Record unresolved work and attempt counts in the current `HANDOFF.md`.
Interrupted or failing work remains uncommitted and the phase remains incomplete.
