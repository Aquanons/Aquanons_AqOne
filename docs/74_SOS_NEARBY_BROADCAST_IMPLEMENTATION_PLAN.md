# 74 - SOS Nearby Broadcast Implementation Plan

**Status:** APPROVED - Revision 2; Phases 1 to 3 merged as built (`fd029fb`); Phase 1b merged 2026-10-01 except the G10 device check; Phase 4 open
**Owner:** Lenard (backend), Arnold (dashboard), Jade (mobile), Daniel (firmware/gateway)
**Created:** 2026-09-30
**Updated:** 2026-10-01T00:30:00+08:00
**Related:** `docs/73_SOS_NEARBY_BROADCAST_SPEC.md`, `docs/73_MOCKUP_venture-nearby-container.html`, `docs/13_RESPONDER_LOOP.md`

Revision: 2
**Execution mode:** hard-stop, except Phase 1b, which runs auto (Len, 2026-10-01)
Feature spec and revision: `docs/73_SOS_NEARBY_BROADCAST_SPEC.md` Revision 2
Len's chat approval, 2026-09-30T23:10:00+08:00: approve the as-built Phase 1 and turn its gaps into work.
Revision 0 (DRAFT) was coded before its Phase 0 gate; Revision 1 records what was built and adds Phase 1b for the gaps.

Success condition: dispatcher ACK creates one broadcast that online nearby phones show as a Venture top container with live distance, a looping `broadcastalarm.mp3` and one notification, and resolve clears it.
Next hard stop: do not start Phase 5 until Phase 4 is verified on Render plus one Android handset.

## Phase 0 - decisions (Len) - DONE

- [x] 0.1 Fresh-position source: the phone's own fix (spec D1).
- [x] 0.2 Two feeds: `GET /api/public/sos-nearby` (spec D2).
- [x] 0.3 Default radius 10 km, dashboard options 5, 10, 20 km (spec D3).
- [x] 0.4 Mockup approved (spec D4).

## Phase 1 - backend online broadcast (Lenard) - MERGED as built

- [x] 1.1 Migration `040_sos_broadcasts.sql`.
- [x] 1.2 `POST /api/sos/{id}/acknowledge` takes `broadcast_enabled` (default true) and `broadcast_radius_km`.
- [x] 1.3 Create on ACK, update in place on re-ACK, expire on resolve, reactivate on reopen.
- [x] 1.4 `GET /api/public/sos-nearby`: rounded position only, no identity fields, excludes the caller's vessel, synthetic and expired. Unauthenticated (gap G1).
- [x] 1.5 `broadcast_state` on `GET /api/sos/active`; audit `sos.broadcast` and `sos.broadcast_expire`. No `broadcast_id` or count (spec D1).
- [x] 1.6 `backend/tests/test_sos_broadcast.py`: one broadcast per incident, re-ACK in place, synthetic never broadcasts, radius filter, resolve expires.

## Phase 2 - dashboard (Arnold) - MERGED as built

- [x] 2.1 `sos-btn-broadcast` enabled after acknowledge, reading `Alert Nearby Vessels`, then `Nearby Vessels Alerted`.
- [x] 2.2 Ack modal checkbox (default on) and radius select 5, 10, 20 km.
- [x] 2.3 Drawer shows `Broadcast ACTIVE`; no count (spec D1) and no `EXPIRED` state (gap G11).
- [x] 2.4 `expected_version` 409 path unchanged.
- [x] 2.5 Web node tests updated (`web/test/dashboard-incidents.test.js`, `dashboard-runtime.test.js`).

## Phase 3 - mobile online (Jade) - MERGED as built

- [x] 3.1 `NearbySos` model and `VentureFeeds.nearbySos`, polled on the 30 s hazard tick.
- [x] 3.2 `NearbyAlarm` looping `audio/broadcastalarm.mp3` on its own player.
- [x] 3.3 Venture top container, collapsible, nearest first.
- [x] 3.4 Distance in metres below 1 km, else one-decimal km; `distance unknown` without GPS. Wording is hard-coded English (gap G9).
- [x] 3.5 First-sighting dialog, red map markers, `nearby_help` notification once per id per app run (gap G2, G10).
- [x] 3.6 ARB keys in `app_en.arb` with `fil` and `akl` drafts.
- [x] 3.7 Dismiss stops sound and keeps the container; Respond centres the map.
- [x] 3.8 `mobile/test/nearby_sos_test.dart`.

## Phase 1b - close the gaps (spec 73 Revision 2, Section 14)

**Execution mode:** auto (Len, 2026-10-01: no hard stops inside Phase 1b; the reviewer checks the whole branch at the end).
Implementer: Gemini on branch `fix/reconcile-2026-09-30`, briefed by [`reconciliation/HANDOFF-gemini-2026-09-30.md`](reconciliation/HANDOFF-gemini-2026-09-30.md); reviewer: Claude Code.
The acceptance tests were written first by the spec author and were red on 2026-09-30 for the reasons listed in the brief; the implementer must not edit them.
G1 and G5 are not in this phase; they wait for Len.

- [x] G12, G6 Savepoint and log every broadcast statement; feeds log errors (`backend/tests/test_sos_broadcast_pg.py`: `test_broadcast_failure_is_logged_and_the_ack_still_lands`, `test_resolve_still_lands_when_broadcast_expiry_fails`, `test_feed_failures_are_logged_not_hidden`).
- [x] G4 Cancel through `broadcast_enabled: false`; reopen never revives a cancelled broadcast (`test_ack_with_broadcast_off_cancels_an_active_broadcast`, `test_ack_with_broadcast_off_and_no_broadcast_creates_nothing`, `test_cancelled_broadcast_can_be_turned_back_on`, `test_reopen_never_revives_a_cancelled_broadcast`).
- [x] G7 Audit create, update, cancel, expire and reactivate distinctly (`test_reack_audits_an_update_not_a_second_create`, `test_reopen_revives_an_expired_broadcast_and_audits_it`).
- [x] G8 Radius 5, 10 or 20 only (`test_broadcast_radius_is_5_10_or_20`).
- [x] G4, G11 Dashboard states and stop button (`web/test/dashboard-broadcast-states.test.js`).
- [x] G2 `SeenBroadcastStore`, database version 16 (`mobile/test/seen_broadcast_store_test.dart`).
- [x] G2, G3 `NearbySosWatcher` owned by the shell (`mobile/test/nearby_sos_watcher_test.dart`).
- [x] G3 `NearbyHelpBanner` on Home and Advisories (`mobile/test/nearby_help_banner_test.dart`).
- [x] G9 Localized distance, no "MDRRMO" in the notification (`mobile/test/nearby_sos_test.dart`).
- [ ] G10 Notification payload and tap routing: code and `mobile/test/eta_notifier_payload_test.dart` done; the device check in the brief is NOT VERIFIED.

Verify: every command in the brief's final gate, pasted verbatim into `docs/reconciliation/EVIDENCE.md`.

## Phase 4 - verification (all)

- [ ] 4.1 Fisher A SOS appears on the dashboard within the 3 s poll.
- [ ] 4.2 ACK creates exactly one broadcast row with a rounded position.
- [ ] 4.3 Fisher B inside the radius hears the loop and sees the container `X km away` and the notification within one poll.
- [ ] 4.4 Fisher C outside the radius sees nothing.
- [ ] 4.5 Re-ACK updates the ETA without a duplicate alert.
- [ ] 4.6 Resolve clears the container and marker within one poll.
- [ ] 4.7 Record evidence in `docs/08_DEMO_AND_STATUS.md`.

## Phase 5 - offline LoRa downlink (Daniel plus Arnold, deferred)

- [ ] 5.1 Extend `WARN` or add a frame with broadcast id, rounded lat/lon, ETA timestamp and TTL (`docs/02` first).
- [ ] 5.2 Gateway polls the broadcast slot alongside ETA and chat; the buoy caches it and serves it via `GET /v1/warnings`.
- [ ] 5.3 Phone merges buoy warnings with the online feed by broadcast id.
- [ ] 5.4 Gated on the two-board bench plus range log, as build order step 6.

Non-goals: no push via FCM, no exact live tracking, no identity in the broadcast, no auto-broadcast before a human ACK.
