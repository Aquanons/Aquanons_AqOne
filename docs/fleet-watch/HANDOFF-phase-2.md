# Handoff: fleet watch plan 69, Phase 2 (pure backend policy)

**Status:** ACTIVE
**Owner:** implementer Len assigns (Gemini in Antigravity by default), Claude Code (reviewer), Len (merge)
**Created:** 2026-09-26T10:15:00+08:00
**Updated:** 2026-09-26T10:15:00+08:00
**Related:** `docs/fleet-watch/PHASE_2_PLAN.md` Revision 2 (the design; read it whole), `docs/69_WEATHER_TIERED_CHECKINS_IMPLEMENTATION_PLAN.md` Phase 2, `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md`

## What you are doing

Create `backend/app/fleet_watch/` so the failing tests pass, and nothing else.
The package decides the fleet check-in tier, whether a boat has missed its check-ins, when silence is the network's fault, what a check-in does to a trip, and which radio slot a pod gets.
It is pure policy: no database, no web framework, no clock, no randomness, no `app.geo`.
Plan 69 is `hard-stop`: when Phase 2 is verified and committed, stop and report.

## Where you work

| Item | Value |
|---|---|
| Worktree | `../AqOne-fleet-watch`; its own `HANDOFF.md` holds live state |
| Branch | `feat/fleet-watch`, with the failing tests already committed |
| Allowed paths | `backend/app/fleet_watch/**` (new), `docs/fleet-watch/**`, plan 69 Phase 2 checkboxes, the worktree `HANDOFF.md` |
| Not yours | every test file, every other `backend/` file, `migrations/`, `web/`, `firmware/`, `mobile/`, the shared contracts `docs/02` to `docs/06`, `AqOne_Story_and_Data_Flow.md` |

## Read first

1. `AGENTS.md` (Ponytail rules, no em dashes, no agent co-author on commits).
2. `docs/fleet-watch/PHASE_2_PLAN.md` Sections 4 and 5: the exact module names, dataclasses, functions and rules.
3. The five test files below.

## The failing tests (do not edit them)

| Test file | IDs | Pins down |
|---|---|---|
| `backend/tests/test_fleet_watch_tier.py` | T2-01 to T2-19 | `Tier`, intervals 840/240/120, advisory and raise decision, raise validation, published revision and expiry, naive datetimes rejected |
| `backend/tests/test_fleet_watch_watch.py` | T2-20 to T2-34 | watched, effective interval, 7.2 min and 50.4 min deadlines, missed count, stagnant, fleet silence (minimum 3 vessels), receiver stale, confidence, alarm; T2-26 keeps the interval numbers out of every module except `tier.py` |
| `backend/tests/test_fleet_watch_trips.py` | T2-35, T2-36 | the eight trip cases and `auto-<vessel>-<epoch>` ids |
| `backend/tests/test_fleet_watch_slots.py` | T2-37 to T2-42 | lowest free slot of 80, re-enrol keeps a slot, `FleetFull`, 1.5 s offsets |
| `backend/tests/test_incidents_is_pure.py` | T2-43, T2-44 | the four module files exist; imports are standard library or `app.fleet_watch` only; no clock or random calls |

Today they fail only because `app.fleet_watch` does not exist: 2 failed, 4 collection errors, 519 passed.
If a test looks wrong after you understand it, stop and write why in the worktree `HANDOFF.md`; do not change it.

## Rules that are easy to miss

- `Checkin.has_fix` is a property; `VesselVerdict` carries `path`.
- `trips.py` imports `Checkin` from `app.fleet_watch.watch`; `watch.py` imports `Tier` and `INTERVAL_S` from `app.fleet_watch.tier` (never repeat the numbers, T2-26).
- `RaiseRejected` and `FleetFull` are frozen dataclasses compared by value (`RaiseRejected('cannot_lower')`).
- Every public function that takes `now` raises `ValueError` for a naive datetime.
- Keep it small: plain functions and frozen dataclasses, no classes with behaviour beyond `Tier.wire` and `Checkin.has_fix`, no new dependency.

## Done when

```powershell
cd backend
python -m ruff check .
python -m pytest -q tests/test_fleet_watch_tier.py tests/test_fleet_watch_watch.py tests/test_fleet_watch_trips.py tests/test_fleet_watch_slots.py tests/test_incidents_is_pure.py
python -m pytest -q
```

- Ruff clean; the five files all pass; the full suite shows 0 failed and the same 59 skipped and 1 xfailed as `master`.
- `git diff master -- backend/tests` shows only the red-test commit, untouched by you.
- Append the commands and their real output to `docs/fleet-watch/EVIDENCE.md` under a "Phase 2" heading; tick plan 69 Phase 2's task and verification boxes; update the worktree `HANDOFF.md`.
- One commit: `feat(fleet-watch): pure tier, watch and slot policy`. Then stop for Claude's review.
