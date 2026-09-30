# 74 - SOS Nearby Broadcast Implementation Plan

**Status:** DRAFT
**Owner:** Lenard (backend decision), Arnold (dashboard), Jade (mobile), Daniel (firmware/gateway)
**Created:** 2026-09-30
**Updated:** 2026-09-30
**Related:** `docs/73_SOS_NEARBY_BROADCAST_SPEC.md`, `docs/73_MOCKUP_venture-nearby-container.html`, `docs/13_RESPONDER_LOOP.md`

Success condition: dispatcher ACK creates one broadcast that online nearby phones show as a Venture top container with live distance plus looping `broadcastalarm.mp3` plus one notification, and resolve clears it.
Next hard stop: do not start Phase 2 until Phase 1 is verified on Render plus one Android handset.

## Phase 0 - decisions (Lenard, 1 short review)

0.1 Confirm fresh-position source for nearby query.
0.2 Choose one feed versus two feeds: extend `GET /api/public/advisories` with `kind=sos_nearby` or add `GET /api/public/sos-nearby`.
0.3 Confirm default radius 10 km plus options 5, 10, 20 km.
0.4 Approve mockup `docs/73_MOCKUP_venture-nearby-container.html`.

Gate: decisions recorded in spec Section 4 plus Section 6 before any migration.

## Phase 1 - backend online broadcast (Lenard)

1.1 Add migration for `sos_broadcasts` per spec Section 6.
1.2 Extend `POST /api/sos/{id}/acknowledge` with `broadcast_enabled` default true plus `broadcast_radius_km`.
1.3 Create broadcast on ACK, update in place on re-ACK, expire on resolve plus reopen reactivates.
1.4 Add nearby read endpoint with vessel-device auth, rounded position only, no identity fields, exclude self plus synthetic plus expired.
1.5 Add `broadcast_id`, `broadcast_state`, `broadcast_count` to `GET /api/sos/active` plus audit `sos.broadcast` events.
1.6 Tests: one broadcast per sos id, re-ACK updates without duplicate, resolve expires, outside-radius excluded, synthetic never broadcasts.

Verify: `pytest backend/tests -k broadcast` plus `ruff check backend`.

## Phase 2 - dashboard (Arnold)

2.1 Enable `sos-btn-broadcast`, show `Alert N nearby vessels` only after acknowledge.
2.2 Extend ack modal `dashboard.html:942-990` with checkbox default ON plus radius select.
2.3 Drawer shows `Broadcast ACTIVE to N boats`, `EXPIRED`, or `OFF`, with live ETA countdown reuse.
2.4 Keep `expected_version` 409 path unchanged.
2.5 Tests: web node tests for modal plus drawer states.

Verify: `npm test` in `web`, manual ACK on staging shows broadcast row.

## Phase 3 - mobile online (Jade)

3.1 Add `NearbySos` model plus `NearbySosService` polling on existing `VentureFeeds` tick (30 s) plus 15 s while any broadcast unacked.
3.2 Add `NearbyAlarm` cloned from `SosAlarm` with source `audio/broadcastalarm.mp3`, `ReleaseMode.loop`, own player, vibration pattern reuse.
3.3 Add `_buildNearbyHelpContainer` in `venture_page.dart` per mockup order: weather, nearby, squall, offline, my-SOS.
3.4 Distance via `latlong2 Distance`, format meters below 1 km else 1-decimal km, `distance unknown` without GPS.
3.5 Add `NearbyHelpDialog` on first sighting plus red map markers plus `nearby_help` notification channel once per id via `flutter_local_notifications`.
3.6 Add ARB keys in `app_en.arb` with descriptions, plus `fil` plus `akl` drafts, no enum display text.
3.7 Dismiss stops sound but keeps container, Respond recenters map, expiry removes marker within one poll.
3.8 Tests: source is `broadcastalarm.mp3`, loop on, duplicate id no re-ring, distance text correct, stop cancels sound plus vibration.

Verify: `flutter analyze` plus `flutter test` clean, manual two-device check with staging backend.

## Phase 4 - verification (all)

4.1 Fisher A SOS appears on dashboard within 3 s poll.
4.2 ACK creates exactly one broadcast row with rounded position.
4.3 Fisher B inside radius hears loop plus sees container `X km away` plus notification within one poll.
4.4 Fisher C outside radius sees nothing.
4.5 Re-ACK updates ETA without duplicate alert.
4.6 Resolve clears container plus marker within one poll.
4.7 Record evidence in `docs/08_DEMO_AND_STATUS.md`.

## Phase 5 - offline LoRa downlink (Daniel plus Arnold, deferred)

5.1 Extend `WARN` or new frame with broadcast id plus rounded lat/lon plus ETA timestamp plus TTL.
5.2 Gateway polls broadcast slot alongside ETA plus chat, buoy caches and serves via `GET /v1/warnings`.
5.3 Phone merges buoy warnings with online feed by broadcast id.
5.4 Gated on two-board bench plus range log, same as build order step 6.

Non-goals: no push via FCM, no exact live tracking, no identity in broadcast, no auto-broadcast before human ACK.
