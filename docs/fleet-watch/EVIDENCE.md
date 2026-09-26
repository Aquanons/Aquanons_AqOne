# Fleet watch (weather-tiered check-ins) - evidence

Evidence for `docs/69_WEATHER_TIERED_CHECKINS_IMPLEMENTATION_PLAN.md`, newest phase first.
Spec: `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md` Revision 3 (approved 2026-09-26T09:50:00+08:00).

## Phase 1 - Contracts written (2026-09-26)

Author: Claude Code (claude-opus-5-5), on `master`.

### Documentation scan before any contract edit

Len asked for a full scan of the documentation before work began, so stale files are updated and conflicts avoided.
The scan covered every numbered doc, `docs/guides/`, `README.md`, `CLAUDE.md`, `AGENTS.md` and `firmware/README.md`, searching for the frame types, check-ins, contact events, sketch counts, airtime figures, the freshness window, channel and board counts, and the surveillance boundary.
Its findings and what was done with each are recorded in plan 69's "Documentation scan" list (Revision 2).
In short:
- Conflicts resolved: `docs/13` planned to repurpose `0x04` (now marked superseded); `docs/61` D10 had the gateway post a contact per frame (now superseded by the check-in receiver); draft `docs/67` wanted a field in `STATUS` (now reserved as `STAGNANT_MIN` in the check-in, with a conflict note for its owners).
- Stale facts corrected: `docs/33` airtime (94-byte frame, not a real SOS); `docs/02` payload cap, frame cap and radio parameters (433 MHz and SF7 against shipped 915 MHz and SF10).
- Scope of record updated: PRD §5.2 item 5 (`[Roadmap — not implemented]`), `docs/07` amendment with the privacy limits, `docs/55` node roles, `docs/56` Lane 3, the registers.
- Deferred to the phase that makes them stale: sketch counts in `CLAUDE.md`, `AGENTS.md`, `README.md`, `firmware/README.md` (Phase 7); `docs/18`, `docs/17` (Phase 4); `docs/16` (Phase 8).

### Contract decisions made while writing (within the approved spec)

| Point | Choice | Why |
|---|---|---|
| Check-in payload | 15 bytes; the header `SEQ` is the check-in counter, so the payload carries no counter of its own | Leaves room for 2 reserved bytes (`STAGNANT_MIN`) inside the spec's 16-byte cap; frame is 45 bytes, inside the 46-byte cap |
| Check-in frequency | `LORA_CHECKIN_FREQ_MHZ` = 917.0 MHz, 2 MHz above the SOS channel, moving with the band if `docs/62D` M11 changes it | Same band, same antenna, clear of the SOS channel's 125 kHz |
| Slot timing | Cycles aligned to `epoch mod 120`; a pod sends in cycles where `floor(epoch / 120) mod (interval / 120) = 0` | Every tier lines up on the same slot grid (D10) |
| Clock | `PING` gains `ms`; receivers add the frame's airtime | Needed for the 100 ms slot tolerance (REQ-029) |
| Pod identity | `pod_id` = `AQ-XXXXXXXX`, derived from `SRC_ID` by plan 66's `nodeNameFromId` (C1) | The frame carries only `SRC_ID`; the name is deterministic, so no lookup table on the receiver |
| Pod enrolment roles | `lgu` and `admin`, the roles that already pair vessel devices | Same kind of privilege; `mdrrmo` cannot pair devices today |
| Vessel list | Added `GET /api/fleet-watch/vessels` for REQ-027's "last check-in N min ago"; `last_position` is `null` for `lgu` | REQ-027 needs a read model; D7 keeps positions from `lgu` |

### Files

- `docs/02_LOAM_PACKET_SPEC.md`: `STATUS` binary check-in, `PING` fields, check-in channel and slots, priority, relay fallback, malformed-frame rule, corrected caps and radio table, shared-key note.
- `docs/04_INGEST_API.md`: "Pod check-ins" (`GET /api/v1/fleet-tier`, `POST /api/v1/checkins`, `POST /api/v1/pods/{pod_id}/enrol`), storage and implicit-trip rules.
- `docs/05_PUBLIC_API.md`: "Fleet watch" (tier, raise, vessels, check-in history, missed-check-in cases), `/api/ops/status` additions, three rows in the roles table.
- `fixtures/loam/checkin_v1.json`: the worked example (45-byte frame, test key, decoded values), built and signed with Python's `hmac` over the signed region `docs/02` defines.

### Verification

- `cd backend; python -m ruff check .` - All checks passed.
- `cd backend; python -m pytest -q` - 519 passed, 59 skipped, 1 xfailed. The skips are the DB-backed tests (`AQONE_PROBE_PG_ADMIN_URL` not set); Phase 1 changes no code, so they do not gate it. From Phase 3 they must run.
- Review: every field named in `docs/68` Section 5 appears in one contract; no contract changes `docs/06`; no public route exposes a check-in position.

### Message for Len to send to Daniel and Arnold

> Contracts for weather-tiered check-ins are in (plan 69 Phase 1, spec docs/68). Daniel: docs/02 now defines STATUS (0x04) as a 15-byte binary pod check-in on a second channel at 917.0 MHz with 1.5 s slots in a 2-minute cycle, and the shore PING gains `ms`, `ct`, `cx`. It also corrects the payload cap to 225 and the radio table to 915 MHz / SF10 to match what the firmware already does. Nothing to build yet; firmware waits for plan 66 Phases 3, 4 and 7. Arnold: docs/04 adds `GET /api/v1/fleet-tier`, `POST /api/v1/checkins` and pod enrolment; docs/05 adds the fleet-watch routes and a `case_kind` on anomaly cases. We will also need one more Heltec board and antenna at the shore for the check-in receiver.
