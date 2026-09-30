# 73 - SOS Nearby Broadcast Spec (dashboard ACK triggers nearby help alert)

**Status:** DRAFT
**Owner:** Lenard (backend), Arnold (dashboard), Jade (mobile), Daniel (firmware/gateway)
**Created:** 2026-09-30
**Updated:** 2026-09-30
**Related:** `docs/13_RESPONDER_LOOP.md`, `docs/06_DELIVERY_STATES.md`, `docs/05_PUBLIC_API.md`, `docs/04_INGEST_API.md`, `docs/03_PHONE_BUOY_WIFI.md`, `docs/02_LOAM_PACKET_SPEC.md`, `docs/73_MOCKUP_venture-nearby-container.html`

## 1. What the user asked

Yes, your understanding is correct today.
The fisher presses SOS in the handset app and that SOS lands on the MDRRMO dashboard.
The dispatcher acknowledges it and sets an ETA.
What is missing is the next step: once the dashboard has acknowledged, other fishers nearby should be told that someone near them sent an SOS and needs help.
This spec describes that missing step.

## 2. Current flow (verified in code)

SOS origin is the handset app only.
`mobile/lib/services/sos_service.dart:83-113` saves the SOS locally first, then relays it on two routes in parallel.
Direct HTTPS is `POST https://aqone-backend.onrender.com/api/sos` via `BackendClient.postSos`.
Buoy WiFi handoff is `POST http://192.168.4.1/v1/sos` via `BuoyClient.handoff`.
Backend dedupes on `(vessel_id, client_ts)` or `(vessel_id, nonce)` in `backend/app/api/sos.py:523-579`.

Backend ingest is unauthenticated by design.
The dashboard live feed is `GET /api/sos/active` polled every 3 seconds by `web/js/dashboard/dashboard-live-sos.js:262-357`.
Acknowledge is `POST /api/sos/{id}/acknowledge {eta_minutes, responder_status 1-5, responder_note, expected_version}` in `backend/app/api/sos.py:441-520`.
Status code 4 is named `Nearest Vessel` or `Nearby boats alerted`, but today it is a label only and triggers nothing.

Return path today is 1:1 to the originator only.
Backend exposes `GET /api/sos/downlink` for the gateway, and the handset polls `GET /api/sos/ack/{local_id}` or `GET /api/sos/vessel/{vessel_id}` every 15 seconds while an SOS is live.
The originator sees the ETA card, the countdown, and the local notification via `EtaNotifier`.
No other vessel is notified.

Nearby broadcast is explicitly disabled today.
`web/html/dashboard.html:909` has `sos-btn-broadcast` disabled with title `Broadcast to nearby vessels is not supported`.
`web/js/dashboard/dashboard-incidents.js:583-599` shows `Broadcast unavailable: LoRa downlink to vessels is not supported` on click.
There is no `GET /nearby` radius query, no push channel, no SOS-linked advisory, and no multi-recipient downlink.

## 3. Proposed flow

```text
1. Fisher A presses SOS in app.
2. SOS reaches backend (direct or buoy relay) and appears on dashboard live feed.
3. Dispatcher opens incident drawer, sets status plus ETA minutes, presses Acknowledge.
4. Backend stores acknowledged_at plus eta_at and marks incident as ACKED.
5. Backend creates one nearby-broadcast record linked to that sos_event id.
6. Nearby fishers B, C poll or receive that broadcast and see NEEDS-HELP alert.
7. Fisher A still gets the existing 1:1 ETA card as today, unchanged.
8. On resolve or reopen, broadcast expires or reactivates automatically.
```

Trigger rule is simple.
Broadcast is created only after a human acknowledge, never on SOS arrival alone.
This avoids prank or pocket-dial spam to the whole fleet.
Re-acknowledge with a new ETA updates the same broadcast rather than creating a second one.

## 4. Who counts as nearby

Nearby means active vessels with a fresh position within radius R of the SOS position.
Default R is 10 km, dispatcher-adjustable 5 to 20 km at acknowledge time.
Fresh means last fix within 60 minutes from `vessels.last_seen_at`, `vessel_trips`, or `buoy_contacts.observed_at`.
The distressed vessel itself is excluded from its own broadcast audience.
Synthetic or demo incidents never broadcast, matching the existing downlink rule.
Position for the broadcast is rounded to about 500 m so helpers can find the area without exposing an exact live track.

Open question for Lenard: confirm the canonical fresh-position source.
`buoy_contacts` plus `vessel_trips` plus `vessels.last_seen_at` all exist but no radius query exists yet.

## 5. What nearby users see, hear, and get notified

The nearby handset shows a persistent top container in Venture mode, plus a full-screen or banner alert on first arrival, not a silent list row.
Title is `Nearby fisher needs help`.
Body carries distance plus bearing, emergency type if known, MDRRMO ETA if set, and a `Respond` plus `Dismiss` action.
Tapping Respond opens Venture map centered on the rounded SOS position with the helper route hint.
Tapping Dismiss silences the looping sound but keeps the top container visible until the broadcast expires, so dismissal never looks like the emergency ended.
Tapping the top container re-opens the detail dialog and re-centers the map.
Tapping Dismiss or Respond stops the alarm immediately, matching the existing `SosAlarm.stop` rule that sound never outlives user action.

Venture top container placement follows the existing stack in `mobile/lib/ui/venture_page.dart:461-488`.
Order from top is weather capsule, then nearby-help container, then squall banner, then offline banner, then my-own-SOS status.
It is pinned under the weather capsule with the same margin plus pill shape as `_buildWeatherCapsule` and `_buildSosStatus`, so it is visible above the map without covering the right-side action rail.
It stays visible on Home and Advisories as a compact banner, but Venture is the canonical surface.
One container per active broadcast, nearest first, max 3 shown plus `+N more` row that opens the full list.
Each row shows red alert icon, `Fisher needs help`, live distance `450 m away` or `2.3 km away`, MDRRMO ETA countdown if set, and chevron.
Distance is computed on-device from the helper GPS fix to the rounded broadcast position via `latlong2 Distance`, formatted as meters below 1 km and 1-decimal km at or above 1 km, and it updates on every `_locate` plus every feed poll.
If own GPS is unavailable the row shows `distance unknown` rather than hiding the emergency.
Map shows a red distress marker for each active broadcast plus the existing blue user dot and buoy circles, so direction is visible at a glance.

Alarm uses the existing asset `mobile/assets/audio/broadcastalarm.mp3`.
It loops via `audioplayers` with `ReleaseMode.loop` plus the SOS vibration pattern, following the `mobile/lib/services/sos_alarm.dart` pattern.
It uses a separate `NearbyAlarm` class so `sos_alarm.wav` stays reserved for my-own-SOS and `broadcastalarm.mp3` stays reserved for someone-else-needs-help.
Loop is foreground-only by design, same caveat as `SosAlarm` and `SquallAlarm`.
Second trigger for the same broadcast id while already ringing is a no-op and never restarts the sound from zero.

A system notification fires once per broadcast id alongside the alarm.
It uses a new channel `nearby_help` with `Importance.high` plus `Priority.high`, following the `mobile/lib/services/eta_notifier.dart` pattern.
It is deduplicated on broadcast id in SQLite, so re-polls and ETA updates never re-notify.
Notification tap opens the same Venture map position as Respond.
If notification permission is denied or the plugin fails, the in-app alarm still rings, so notification failure never blocks the alarm.
Strings must go in `mobile/lib/l10n/app_en.arb` with `@key` descriptions, read via `AppLocalizations`, with `fil` and `akl` drafts, and no display text on enums per `AGENTS.md`.

What nearby users do NOT see: owner name, phone number, license number, shore contact, or exact GPS.
Downlink today deliberately strips identity, and this broadcast keeps that rule.

## 6. Backend design (minimum change)

Reuse the advisories pipe rather than inventing a new push system.
`POST /api/advisories/alert` plus `GET /api/public/advisories` already has multi-recipient delivery plus `warning_delivery_events` receipts.
Add `source_key = sos:{sos_event_id}` and `kind = sos_nearby` so the phone can parse SOS broadcasts through one code path.

New or changed endpoints:

- `POST /api/sos/{id}/acknowledge` gains optional `broadcast_radius_km` and `broadcast_enabled` flag.
- New `GET /api/public/sos-nearby?lat&lon&radius_km` returns active broadcasts near the caller, credentialed by vessel-device token, no identity fields.
- Or extend `GET /api/public/advisories` with `kind=sos_nearby` filter if Lenard prefers one feed.
- `GET /api/sos/active` response gains `broadcast_id`, `broadcast_count`, and `broadcast_state`.
- Gateway downlink gains a broadcast slot so offline boats via buoy `GET /v1/warnings` can also poll it.

New table `sos_broadcasts`:

```text
sos_broadcasts
  id UUID PK
  sos_event_id FK unique
  center_lat DOUBLE
  center_lon DOUBLE rounded to 500 m
  radius_km INT
  eta_at TIMESTAMPTZ nullable copy
  responder_status SMALLINT nullable copy
  state TEXT active|expired|cancelled
  created_by_user_id FK
  created_at TIMESTAMPTZ
  expired_at TIMESTAMPTZ nullable
```

Idempotency: one active row per `sos_event_id`.
Re-acknowledge does `UPDATE`, resolve does `state=expired`, reopen reactivates.
Audit every transition as `sos.broadcast`, `sos.broadcast_update`, `sos.broadcast_expire`.

Polling intervals reuse existing ones.
Handset `VentureFeeds` already polls advisories every 30 seconds, and SOS reconcile runs every 15 seconds while live.
Nearby check rides on those polls, so no new background service is needed for Phase 1.

## 7. Dashboard changes

Enable the disabled button.
`sos-btn-broadcast` becomes enabled only after acknowledge, showing `Alert N nearby vessels`.
The ack modal in `web/html/dashboard.html:942-990` gains a checkbox `Also alert nearby vessels` default ON plus radius select 5, 10, 20 km.
Incident drawer shows broadcast state: `Broadcast ACTIVE to 4 boats`, `EXPIRED`, or `OFF`.
Version-conflict handling stays as today with `expected_version` and 409 path.

## 8. Mobile changes

Add `NearbySosService` that polls the new nearby feed on the existing `VentureFeeds` tick.
Store seen broadcast ids in SQLite so the alert plus notification plus alarm fire once.
Add `_buildNearbyHelpContainer` in `venture_page.dart` reusing the `_buildSosStatus` pill style, wired to `_userLocation` for live distance, with tap to recenter plus dialog.
Show `NearbyHelpDialog` on first sighting plus Venture map red distress markers, one per active broadcast.
Play `mobile/assets/audio/broadcastalarm.mp3` in a loop through a new `NearbyAlarm` class cloned from `SosAlarm`, with its own `AudioPlayer` instance so both alarms never share a player.
Stop on Respond, Dismiss, broadcast expiry, or resolve.
Background behavior matches existing foreground-service rule: no new always-on service, only poll while app or foreground service is alive.
Add widget plus unit tests that assert `broadcastalarm.mp3` is the source, loop mode is on, duplicate ids do not re-ring, container shows correct distance text, and stop cancels both sound and vibration.

## 9. Firmware and gateway changes (Phase 2)

Phase 1 works for boats with internet, which matches the existing direct-path responder loop.
Phase 2 extends `WARN` downlink so offline boats behind a buoy also get it.
This needs Daniel plus Arnold: new LoRa frame or extended `WARN` payload with broadcast id, rounded lat/lon, ETA timestamp, and TTL.
Gateway polls the new broadcast slot alongside ETA and chat downlink.
Buoy caches it and serves it via `GET /v1/warnings` which the phone already polls.

## 10. Safety and abuse rules

Broadcast requires human acknowledge with a valid responder role, same auth as `POST /api/sos/{id}/acknowledge`.
No auto-broadcast on ingest.
One broadcast per incident, updated in place, expired on resolve.
Dispatcher can cancel broadcast without un-acknowledging the incident.
Rate limit: one create plus three updates per incident per 10 minutes to prevent drawer spam.
Log all actions in the case timeline and global audit search.
Prank handling: `closed_unconfirmed` resolve expires the broadcast immediately and phones remove the marker.

## 11. Acceptance criteria

- Fisher A SOS appears on dashboard within 3 second poll as today.
- Dispatcher ACK with ETA creates exactly one `sos_broadcasts` row with rounded position and correct radius.
- Fisher B within radius hears looping `broadcastalarm.mp3` plus vibration, sees Venture top container `Fisher needs help - 2.3 km away` plus `nearby_help` notification within one poll tick, with no owner or phone fields in payload.
- Venture container distance updates live as helper moves, shows `distance unknown` without GPS, and clears within one poll tick of resolve.
- Fisher C outside radius sees nothing.
- Re-ACK updates ETA in place with no duplicate alert, only an updated countdown.
- Resolve expires broadcast and removes marker on nearby phones within one poll tick.
- Synthetic or demo SOS never creates a broadcast.
- Backend pytest plus ruff, web node tests, and `flutter analyze` plus `flutter test` stay green.

## 12. Next step after this spec

Approve this spec, then break it into an implementation plan with Phase 1 (backend plus dashboard plus online mobile) and Phase 2 (gateway plus buoy plus offline mobile).
Do not code until the nearby-source question in Section 4 and the one-feed versus two-feed question in Section 6 are decided by Lenard.
