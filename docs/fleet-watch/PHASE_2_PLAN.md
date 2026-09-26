# Plan 69 Phase 2 - pure backend policy: detailed implementation plan

**Status:** APPROVED - Revision 2
**Owner:** Claude Code (plan, red tests, review), implementer named in the worktree `HANDOFF.md`, Len (merge)
**Created:** 2026-09-26T10:05:00+08:00
**Updated:** 2026-09-26T10:15:00+08:00
**Related:** `docs/69_WEATHER_TIERED_CHECKINS_IMPLEMENTATION_PLAN.md` Phase 2, `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md` Revision 3, `docs/02`, `docs/04`, `docs/05` (fleet-watch sections from `1f2a5bd`)

Len, 2026-09-26: "Go for phase 2, note that we're only creating an implementation plan. Dont modify any code yet."
This document is that plan.
Len's chat approval of Revision 1, 2026-09-26T10:09:00+08:00: "Start". Section 9 offered "answers P1 (or accepts the proposal)", so P1 is accepted as proposed: `FLEET_SILENCE_MIN_VESSELS = 3`. P2 stays open until the team supplies the landing-site coordinates (needed before Phase 4).
Revision 2 (2026-09-26T10:15:00+08:00) is editorial: while writing the red tests, five details of Section 5 were pinned down to match them (the `advisory_tier` result for normal, `VesselVerdict.path`, the `fleet_silence` signature, how "recent fix" is measured, eight trip cases instead of seven, and the purity test's wider import ban). No rule changed.
It names every module, type, function and test, so the red tests and the implementation can be written from it without further design.
Nothing under `backend/` changes until Len approves this plan and says to start.

## 1. Outcome

A framework-free package, `backend/app/fleet_watch/`, holding every fleet-watch decision that does not need a database, a web request, a radio or a clock:
what the tier is, when a vessel is watched, when it has missed its check-ins, when silence is the network's fault, what a check-in does to a trip, and which slot a pod gets.
Phases 3 and 4 then only wire storage and HTTP around it.

Requirements covered: `docs/68` REQ-001, REQ-002, REQ-003 (the rules only), REQ-004 (the rules only), REQ-016 (the trip decision), REQ-018, REQ-019, REQ-021 (the decision), REQ-024, REQ-031 (the slot choice).

## 2. Findings from planning (need Len before Phase 4, not before Phase 2)

| # | Finding | Proposal | Blocks |
|---|---|---|---|
| P1 | **Fleet silence can hide a real emergency in a small fleet.** With the 30% rule alone, 1 missed vessel out of 2 watched is 50%, so that case would be marked low confidence and would not sound the alarm. | Fleet silence also needs at least 3 missed vessels (`FLEET_SILENCE_MIN_VESSELS = 3`). 4 of 10 still triggers it; 1 of 2 does not. | Accepted, Len 2026-09-26T10:09:00+08:00 |
| P2 | **The harbor zones cannot come from `SHORE_STATIONS`.** `app/geo.py` moves every shore station about 1.7 km west of its real position so it sits on land for `tests/test_geo.py`, and the real landing sites fall inside `WATER_POLYGON`. Zones drawn around those points would miss the real harbors, and every boat moored at home would count as at sea. | A new `HARBOR_ZONES` constant in `app/geo.py`: the real landing sites (at least Dumaguit Port and the Poblacion landing), each a centre and a 500 m radius, from the team's map. Both the backend's "at sea" test and the generated firmware header read it. This amends spec D6's source, not its behaviour. | Phase 4 (backend wiring) and Phase 6 (firmware header) |
| P3 | Advisory expiry is a date, not a time (`advisories.expiration_date`). | An advisory is active through the end of its expiry date in Manila time (23:59:59+08:00); the adapter converts, the policy only sees a datetime. | Nothing |
| P4 | A dispatcher raise equal to the advisory tier changes nothing. | A raise must be strictly above the advisory tier when it is made (`cannot_lower` otherwise). If advisories later rise to meet it, the advisory is named as the source and the raise stays on record until it expires. | Nothing |

Two corrections to plan 69 Phase 2, applied in the same commit as this document:
- Its REQ-001 check `rg "900|840|240|120" backend/app` cannot pass: `240` is already a note length in `api/catch.py` and `api/trips.py`. It is replaced by the static test T2-26 below.
- `ports.py` moves to Phase 3, where the first use case consumes it; in Phase 2 it would have no caller.

## 3. Where the work happens (when Len says start)

| Item | Value |
|---|---|
| Worktree | `../AqOne-fleet-watch` (new), with its own `HANDOFF.md` per `docs/58` |
| Branch | `feat/fleet-watch` from `master` at or after `1f2a5bd` |
| Allowed paths | `backend/app/fleet_watch/**`, `backend/tests/test_fleet_watch_*.py`, `backend/tests/test_incidents_is_pure.py`, `docs/fleet-watch/**`, plan 69 Phase 2 checkboxes, the worktree `HANDOFF.md` |
| Not touched | every other `backend/` file, `migrations/`, `web/`, `firmware/`, `mobile/`, the shared contracts, `AqOne_Story_and_Data_Flow.md` |

Two commits:
1. `test(fleet-watch): failing tests for the pure policy` (Claude). The suite fails only because `app.fleet_watch` does not exist yet.
2. `feat(fleet-watch): pure tier, watch and slot policy` (implementer), which makes them pass without editing them.

Claude reviews commit 2; Len merges to `master` and pushes.

## 4. Package layout

```text
backend/app/fleet_watch/
  __init__.py      empty
  tier.py          tiers, intervals, the fleet-tier decision, raise validation, published-tier revision
  watch.py         watched, effective interval, missed deadline, vessel verdict, fleet silence, confidence
  trips.py         what a check-in does to a trip
  slots.py         slot assignment
```

Rules for every module:
- Standard library only (`dataclasses`, `datetime`, `enum`, `math`, `typing`, `collections.abc`).
- No import of `fastapi`, `asyncpg`, `httpx`, `app.db` or `app.geo`; "is this point at sea?" arrives as a callable.
- No `datetime.now()`, `time.time()` or randomness; every function that needs the time takes `now`.
- Plain frozen dataclasses in and out; no dicts with implied keys across the boundary.
- All datetimes are timezone-aware; a naive datetime is a programming error (`ValueError`).

## 5. API

Signatures below are the design, not code to paste.
Names are final so the tests and the implementation agree.

### 5.1 `tier.py` (REQ-001 to REQ-004)

```text
class Tier(IntEnum): NORMAL = 0, ELEVATED = 1, SEVERE = 2
    .wire -> 'normal' | 'elevated' | 'severe'

SLOT_CYCLE_S = 120
INTERVAL_S: Mapping[Tier, int] = {NORMAL: 840, ELEVATED: 240, SEVERE: 120}
PUBLISHED_TIER_TTL = timedelta(minutes=10)
MAX_RAISE = timedelta(hours=12)
AREAS = frozenset({'new washington', 'all'})          compared case-insensitively

@dataclass(frozen) WeatherSignal:
    advisory_id: int, title: str, priority: str, status: str,
    area: str, expires_at: datetime | None
@dataclass(frozen) Raise:
    tier: Tier, reason: str, raised_by: str, expires_at: datetime
@dataclass(frozen) TierSource:
    kind: 'advisory' | 'raise' | 'none', advisory_id: int | None, title: str | None, raise_: Raise | None
@dataclass(frozen) TierDecision:
    tier: Tier, interval_s: int, source: TierSource
@dataclass(frozen) PublishedTier:
    tier: Tier, interval_s: int, rev: int, exp: datetime
@dataclass(frozen) RaiseRejected:
    code: 'raise_too_long' | 'cannot_lower' | 'reason_invalid'

signal_tier(signal, now) -> Tier
    Only a signal that is published, for an area in AREAS, and not expired
    (expires_at is None or now <= expires_at) counts:
    'Emergency' -> SEVERE, 'Warning' -> ELEVATED, any other priority -> NORMAL.
    A signal that does not count -> NORMAL.
advisory_tier(signals, now) -> tuple[Tier, WeatherSignal | None]
    Highest signal_tier; ties go to the signal with the latest expires_at (None counts as latest).
    (NORMAL, None) when no signal counts.
fleet_tier(signals, active_raise, now) -> TierDecision
    Raise counts only while now < raise.expires_at.
    Higher of advisory tier and raise tier; the raise is the source only if strictly higher.
validate_raise(tier, reason, duration, advisory_tier, now, raised_by) -> Raise | RaiseRejected
    reason stripped 1..200 chars; duration > 0 and <= MAX_RAISE; tier > advisory_tier.
next_published(previous: PublishedTier | None, decision, now) -> PublishedTier
    rev = previous.rev + 1 if the tier changed (or no previous, starting at 1), else previous.rev;
    exp = now + PUBLISHED_TIER_TTL.
```

### 5.2 `watch.py` (REQ-018, REQ-019, REQ-021, REQ-024)

```text
MISSED_AFTER_INTERVALS = 3          K, spec D8
GRACE_FRACTION = 0.2
FLEET_SILENCE_SHARE = 0.30          spec D8
FLEET_SILENCE_MIN_VESSELS = 3       finding P1, pending Len
RECEIVER_STALE_AFTER = timedelta(minutes=3)
RECENT_POSITION = timedelta(minutes=30)

AtSea = Callable[[float, float], bool]

@dataclass(frozen) Checkin:
    observed_at: datetime, latitude: float | None, longitude: float | None,
    path: 'direct' | 'relayed', fix_age_s: int | None
    .has_fix -> latitude and longitude both present
@dataclass(frozen) VesselWatchInput:
    vessel_id: str, trip_id: str | None,
    latest: Checkin, last_positioned: Checkin | None,
    tier_at_latest: Tier, stagnant_until: datetime | None
@dataclass(frozen) VesselVerdict:
    vessel_id: str, trip_id: str | None,
    state: 'not_watched' | 'on_time' | 'stagnant' | 'missed',
    interval_s: int, deadline: datetime | None, missed_count: int,
    path: 'direct' | 'relayed'                       the latest check-in's path
@dataclass(frozen) FleetSilence:
    active: bool, reason: 'share' | 'receiver_stale' | None
@dataclass(frozen) CaseConfidence: 'high' | 'low'   (maps to case_type responder_attention | verification)

is_watched(latest, last_positioned, at_sea) -> bool
    latest.has_fix: at_sea(latest.lat, latest.lon).
    Otherwise: last_positioned is not None and at_sea(its lat, lon).
effective_interval_s(tier_at_latest, current_tier, latest_path) -> int
    'relayed' -> INTERVAL_S[NORMAL]; else max(INTERVAL_S[tier_at_latest], INTERVAL_S[current_tier]).
missed_deadline(last_at, interval_s) -> datetime
    last_at + K * interval_s * (1 + GRACE_FRACTION) seconds.
evaluate_vessel(item, current_tier, now, at_sea) -> VesselVerdict
    not watched -> 'not_watched'.
    stagnant_until > now and current_tier < SEVERE -> 'stagnant'.
    now > deadline -> 'missed', missed_count = floor((now - latest.observed_at) / interval_s).
    else -> 'on_time'.
fleet_silence(verdicts, receiver_last_upload_at, now) -> FleetSilence
    receiver_last_upload_at is None or older than RECEIVER_STALE_AFTER (strictly) -> active, 'receiver_stale'
        (only when at least one watched verdict has path 'direct').
    watched = verdicts not 'not_watched'; missed = 'missed'.
    len(missed) >= FLEET_SILENCE_MIN_VESSELS and len(missed) / len(watched) >= FLEET_SILENCE_SHARE -> active, 'share'.
    else inactive.
case_confidence(verdict, item, silence, now) -> CaseConfidence
    'low' if silence.active, or the vessel has no fix taken within RECENT_POSITION of now; else 'high'.
    A fix was taken at observed_at - fix_age_s (fix_age_s None counts as 0), using the latest check-in
    when it has a fix, otherwise last_positioned.
should_sound_alarm(confidence, current_tier) -> bool
    'high' and current_tier == SEVERE (REQ-022's rule, decided here so the dashboard only reads it).
```

"Same window" in REQ-021 is the current evaluation: every vessel whose deadline has passed and that has not checked in again counts as missed now.
A missed vessel that checks in again leaves the count on the next evaluation, which is also what resolves its case (REQ-023, Phase 4).

### 5.3 `trips.py` (REQ-016, spec D11)

```text
@dataclass(frozen) OpenTrip: trip_id: str, reporter_type: str
@dataclass(frozen) TripAction:
    kind: 'open' | 'attach' | 'complete' | 'none', trip_id: str | None

auto_trip_id(vessel_id, observed_at) -> str       'auto-<vessel_id>-<epoch seconds>'
trip_action(vessel_id, checkin, open_trip, at_sea) -> TripAction
```

| Check-in | Open trip | Result |
|---|---|---|
| Fix at sea | none | `open`, `auto_trip_id(...)` |
| Fix at sea | any (gateway or handset) | `attach` to it |
| Fix in harbor or on land | opened by `gateway` | `complete` it (the check-in attaches first) |
| Fix in harbor or on land | opened by anyone else | `attach` (a handset trip is never completed by a check-in) |
| Fix in harbor or on land | none | `none` (stored with no trip) |
| No fix | any | `attach` |
| No fix | none | `none` |

### 5.4 `slots.py` (REQ-031)

```text
SLOT_COUNT = 80
SLOT_LENGTH_S = 1.5
@dataclass(frozen) FleetFull: code = 'fleet_full'

assign_slot(pod_id, taken: Mapping[str, int]) -> int | FleetFull
    pod_id already in taken -> its slot.
    else the lowest slot in 0..79 not in taken.values(); none left -> FleetFull.
slot_offset_s(slot) -> float                     slot * SLOT_LENGTH_S, for the firmware contract and tests
```

## 6. Red tests

Four files, one per module, plus the purity test.
Every test injects `now`; `at_sea` is a fake (`lambda lat, lon: lat > 11.60`, so 11.65 is "at sea" and 11.55 is "harbor").
Times are built from one base, `T0 = datetime(2026, 9, 26, 2, 0, tzinfo=UTC)`.

### `tests/test_fleet_watch_tier.py`

| ID | Case | Expect |
|---|---|---|
| T2-01 | `INTERVAL_S` | 840, 240, 120; each a multiple of `SLOT_CYCLE_S` (REQ-001) |
| T2-02 | No signals, no raise | `NORMAL`, source `none` |
| T2-03 | One published `Warning`, area `All` | `ELEVATED`, source advisory with its id and title |
| T2-04 | `Warning` plus `Emergency` | `SEVERE`, source is the `Emergency` |
| T2-05 | `Emergency` with `expires_at` 1 s before `now` | `NORMAL` |
| T2-06 | `Emergency` with status `Draft` | `NORMAL` |
| T2-07 | `Emergency` for area `Kalibo`; area `NEW WASHINGTON` | `NORMAL`; `SEVERE` (case-insensitive) |
| T2-08 | `Information` and `Community` | `NORMAL` |
| T2-09 | Raise `SEVERE` over advisory `ELEVATED`, unexpired | `SEVERE`, source `raise` |
| T2-10 | Same raise 1 s after `expires_at` | `ELEVATED`, source advisory |
| T2-11 | Raise `SEVERE`, advisories later reach `SEVERE` | `SEVERE`, source advisory (P4) |
| T2-12 | `validate_raise` 2 h, `SEVERE` over `ELEVATED` | a `Raise` expiring `now + 2 h` (REQ-003) |
| T2-13 | `validate_raise` 12 h 1 min | `RaiseRejected('raise_too_long')` |
| T2-14 | `validate_raise` `ELEVATED` while advisories give `ELEVATED`; `NORMAL` while `ELEVATED` | `cannot_lower` both |
| T2-15 | `validate_raise` reason `"   "`; reason of 201 chars | `reason_invalid` both |
| T2-16 | `next_published(None, ELEVATED)` | `rev 1`, `exp = now + 10 min` (REQ-004) |
| T2-17 | Same tier 1 min later | same `rev`, `exp` moved 1 min |
| T2-18 | Tier changes | `rev + 1` |
| T2-19 | A naive `now` | `ValueError` |

### `tests/test_fleet_watch_watch.py`

| ID | Case | Expect |
|---|---|---|
| T2-20 | Latest fix at sea; latest fix in harbor | watched; not watched (REQ-018) |
| T2-21 | Latest without fix, previous fix at sea; previous in harbor; no previous | watched; not; not |
| T2-22 | Severe both times, direct, last check-in 7.3 min ago; 7.1 min ago | `missed`; `on_time` (REQ-019, deadline 7.2 min) |
| T2-23 | Tier was `NORMAL` at the last check-in, `SEVERE` now: 50 min after; 50.5 min after | `on_time`; `missed` (deadline 50.4 min) |
| T2-24 | Relayed latest check-in, current tier `SEVERE`, 8 min ago | `on_time`, `interval_s` 840 |
| T2-25 | `missed_count` 25 min after a Severe check-in | 12 |
| T2-26 | Static: no `fleet_watch` module other than `tier.py` contains the literals `840`, `240` or `120` as numbers | passes (replaces plan 69's `rg` check) |
| T2-27 | Stagnant until `now + 1 h`, missed by time: at `NORMAL`, `ELEVATED`, `SEVERE` | `stagnant`, `stagnant`, `missed` (REQ-024) |
| T2-28 | Stagnant until `now - 1 s` | `missed` |
| T2-29 | 4 of 10 watched missed, receiver fresh | silence active, `share` (REQ-021) |
| T2-30 | 1 of 10 missed; 1 of 2 missed; 2 of 4 missed | inactive in all three (P1 minimum of 3) |
| T2-31 | Receiver last upload 3 min 1 s ago, one direct watched vessel; `None`; all watched vessels relayed | active `receiver_stale`; active; inactive |
| T2-32 | `case_confidence`: silence active; no fix within 30 min; fresh fix, no silence | `low`; `low`; `high` |
| T2-33 | `should_sound_alarm` high at `SEVERE`; high at `ELEVATED`; low at `SEVERE` | `True`; `False`; `False` |
| T2-34 | Not-watched vessels are ignored in the silence share | 3 missed of 5 watched plus 20 not watched: active |

### `tests/test_fleet_watch_trips.py`

| ID | Case | Expect |
|---|---|---|
| T2-35 | The rows of the table in 5.3, with "any" split into a gateway and a handset trip (eight cases) | the listed `TripAction` each (REQ-016, D11) |
| T2-36 | `auto_trip_id('NW-001', 2026-09-21T14:13:20Z)` | `auto-NW-001-1790000000` (matches `docs/04`) |

### `tests/test_fleet_watch_slots.py`

| ID | Case | Expect |
|---|---|---|
| T2-37 | Empty registry | slot 0 |
| T2-38 | Slots 0, 1, 3 taken | slot 2 |
| T2-39 | Pod already holds slot 7 | 7 (re-enrol keeps the slot) |
| T2-40 | 80 slots taken, new pod | `FleetFull` (REQ-031) |
| T2-41 | 80 taken, pod already enrolled | its slot |
| T2-42 | `slot_offset_s(7)` | 10.5 (matches `docs/02`) |

### `tests/test_incidents_is_pure.py` (extended)

| ID | Case | Expect |
|---|---|---|
| T2-43 | Every `app.fleet_watch` module, read with `ast` so `from x import y` is caught | imports none of `fastapi`, `asyncpg`, `httpx`, `app.db`, `app.geo`, `app.api`, `app.ai`, `numpy`, nor bare `app` |
| T2-44 | Source of every `app.fleet_watch` module | contains no `datetime.now(`, `time.time(` or `random` |

## 7. Gates

```powershell
cd backend
python -m ruff check .
python -m pytest -q tests/test_fleet_watch_tier.py tests/test_fleet_watch_watch.py tests/test_fleet_watch_trips.py tests/test_fleet_watch_slots.py tests/test_incidents_is_pure.py
python -m pytest -q
```

- After commit 1: the four new files fail at import (`ModuleNotFoundError: app.fleet_watch`), T2-43 and T2-44 fail the same way, and every other test is unchanged. Recorded run (`pytest -q --continue-on-collection-errors`): 2 failed, 519 passed, 59 skipped, 1 xfailed, 4 errors, against 519 passed on `master`.
- After commit 2: all green, with the same skip count as `master` (DB tests need `AQONE_PROBE_PG_ADMIN_URL`; Phase 2 adds none).
- Review (Claude): no test edited between the commits; no file outside the allowed paths; each function no longer than the rule it encodes.

## 8. What Phase 2 does not do

- No migration, SQL, route, scheduler job or dashboard change (Phases 3 to 5).
- No `ports.py` or use cases (Phase 3).
- No `HARBOR_ZONES` in `app/geo.py` (finding P2, before Phase 4).
- No change to `app/ai/anomaly_service.py` (Phase 4, REQ-032).

## 9. To start Phase 2

1. Len approves this plan, answers P1 (or accepts the proposal), and says start.
2. Create the worktree: `git worktree add ../AqOne-fleet-watch -b feat/fleet-watch master`, and write its `HANDOFF.md`.
3. Claude writes and commits the red tests (commit 1), then hands the worktree to the implementer.
