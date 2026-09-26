# 67 — Stagnant Mode Implementation Plan

**Status:** DRAFT
**Owner:** Team Aquanons (backend: Lenard, gateway: Arnold, pod firmware: Daniel, mobile: Jade/Doreen Kay, dashboard: Jade)
**Created:** 2026-09-25
**Updated:** 2026-09-25
**Related:** [`38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`](38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md), [`51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md`](51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md), [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md), [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md), [`04_INGEST_API.md`](04_INGEST_API.md), [`06_DELIVERY_STATES.md`](06_DELIVERY_STATES.md), PRD §5.2

**Success condition:** A fisher declares "stagnant for N minutes"; the declaration
reaches the backend over the existing phone → pod → LoRa → gateway path; no
overdue candidate is raised for that trip until the declared time runs out;
after it runs out with no new contact, the normal escalation ladder resumes
and the case says why.

**Next hard stop:** Do not start before the active plan
([`62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`](62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md))
is complete and the team agrees the maximum duration (Open question 1).

## Problem

Overdue detection ([`trip_profile.py`](../backend/app/ai/trip_profile.py))
treats silence as the danger signal: when a vessel misses its expected-contact
window, or passes `expected_return_at`, the `overdue` factor (85% of the
score) climbs toward `alert`. A fisher who anchors or longlines in one spot on
purpose looks exactly like a boat in trouble. Doc 51 measures a P90 blind
interval of 210 minutes during offshore stationary longlining — long enough
to produce false candidates that train MDRRMO to ignore the queue.

## What stagnant mode is

- The fisher chooses a duration ("I'll be here for 2 hours") from the app.
  The trip records `stagnant_until = declared_at + duration`.
- **While active:** the overdue factor for that trip is capped low, the same
  way `welfare_status = 'safe'` already caps it, and the explanation reads
  "Stagnant mode declared until HH:MM."
- **When it expires:** the expected-contact window restarts from
  `stagnant_until`, not from the last contact, so a fisher is not instantly
  "hours overdue" the moment the timer ends. Continued silence then escalates
  normally, with the explanation "Stagnant mode expired at HH:MM with no
  contact."
- **Ended early:** any new contact, a new declaration, or trip completion
  replaces it.

## Hard rules

- An SOS always overrides stagnant mode. `welfare_status = 'distress'` always
  overrides it.
- It suppresses **silence-based** scoring only. It never hides squall
  warnings, advisories, or anything shown to the fisher.
- The duration is capped: never past `expected_return_at`, and never past a
  team-agreed maximum (Open question 1). The backend clamps; it does not trust
  the handset.
- It is visible to responders. The dashboard shows "Stagnant until HH:MM" on
  the vessel, so a quiet boat is visibly a declared one, not a hidden one.
- It is not motion detection. Nothing verifies the boat is actually still;
  the pod has GPS but no position cadence today. Verifying stillness from pod
  GPS is a later, separate item.
- No LoRa downlink to the handset (still scoped out). The app shows the
  declaration's delivery state honestly using the four states in doc 06; it
  cannot claim the backend accepted it.

## Phase 1 — Contracts first

Update the shared contracts before any code, and tell the owners:

1. [`03_PHONE_BUOY_WIFI.md`](03_PHONE_BUOY_WIFI.md): a phone → pod request
   carrying vessel ID, trip ID, and duration in minutes.
2. [`02_LOAM_PACKET_SPEC.md`](02_LOAM_PACKET_SPEC.md): how the declaration
   crosses LoRa. Prefer a field inside the existing `STATUS` (`0x04`) payload
   over a new frame type; add a type only if `STATUS` cannot carry it. SOS
   keeps radio priority.
   **Conflict note (2026-09-26):** approved `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md`
   turns `STATUS` into a 16-byte binary pod check-in sent every 2 to 14 min,
   and `docs/02` reserves its last 2 bytes as `stagnant_min` (minutes of
   stagnant mode left, 0 = none) for this plan. Proposed for this plan's
   owners: the pod stores the phone's declaration and repeats it in every
   check-in, so a lost frame costs one interval, not the declaration. Plan 68
   REQ-024 already defines the Severe-tier override (D2).
3. [`04_INGEST_API.md`](04_INGEST_API.md): the gateway-only ingest shape,
   idempotent on the upstream event ID like other contact events.
4. [`05_PUBLIC_API.md`](05_PUBLIC_API.md): `stagnant_until` on the trip/vessel
   read model the dashboard already polls.

## Phase 2 — Backend

1. One migration: `vessel_trips.stagnant_until TIMESTAMPTZ NULL`. Record each
   declaration in the existing `amendments` log rather than a new table.
2. Accept the declaration on the gateway ingest path and on
   `PATCH /trips/{trip_id}` ([`trips.py`](../backend/app/api/trips.py)); clamp
   the duration there.
3. In `score_trip` ([`trip_profile.py`](../backend/app/ai/trip_profile.py)),
   in both the with-contacts and zero-contacts branches: cap `overdue` while
   `as_of < stagnant_until`; after expiry, measure lateness from
   `max(last_contact_at, stagnant_until)`.
4. Tests: active declaration raises no candidate; expired declaration with
   continued silence escalates with the expiry explanation; a declaration
   longer than the cap is clamped; SOS/distress overrides it. Run
   `ruff check backend` and the targeted anomaly and trips tests.

## Phase 3 — Mobile

1. A "Stagnant mode" control with a small set of preset durations (bounded by
   the cap), sent over the existing buoy client.
2. All strings in `mobile/lib/l10n/app_en.arb` with `@key` descriptions;
   `fil`/`akl` drafts marked unreviewed. No display text on enums.
3. Show the remaining time and the declaration's delivery state.
4. `flutter analyze` and `flutter test`.

## Phase 4 — Pod firmware and gateway

1. Pod: accept the phone request and send it over LoRa per Phase 1. It is
   store-and-forward like any other frame and never delays an SOS.
2. Gateway: forward it to the ingest endpoint.
3. PlatformIO build, then one bench test through the full path.

## Phase 5 — Dashboard and record

1. Show "Stagnant until HH:MM" on the vessel and the trip-check case.
2. Record the bench result in [`08_DEMO_AND_STATUS.md`](08_DEMO_AND_STATUS.md)
   and move the PRD line out of `[Roadmap — not implemented]` only once it
   works end to end.

## Open questions

1. What is the maximum declarable duration? Doc 51's 210-minute P90 is a
   starting point, not a decision. Guessing it changes emergency behaviour.
2. Should the pod's physical button also be able to declare it, for fishers
   who don't have their phone out?
3. What should the mode be called in Tagalog and Aklanon? "Stagnant" may read
   as negative to fishers; the UI name should come from Doreen Kay's UX pass.
