# 73 - SOS Nearby Broadcast Spec (dashboard ACK triggers nearby help alert)

**Status:** APPROVED - Revision 2 (Phase 1b designed in Section 14; G1 and G5 wait for Len)
**Owner:** Lenard (backend), Arnold (dashboard), Jade (mobile), Daniel (firmware/gateway)
**Created:** 2026-09-30
**Updated:** 2026-10-01T00:30:00+08:00
**Related:** `docs/74_SOS_NEARBY_BROADCAST_IMPLEMENTATION_PLAN.md`, `docs/13_RESPONDER_LOOP.md`, `docs/06_DELIVERY_STATES.md`, `docs/05_PUBLIC_API.md`, `docs/04_INGEST_API.md`, `docs/03_PHONE_BUOY_WIFI.md`, `docs/02_LOAM_PACKET_SPEC.md`, `docs/73_MOCKUP_venture-nearby-container.html`

Revision: 2
Revision 0 (DRAFT, 2026-09-30) was implemented and merged before approval (`fd029fb`, PR #86) and was live on Render at `3f07b3b`.
Len's chat approval, 2026-09-30T23:10:00+08:00: approve the as-built Phase 1 and record its gaps.
Revision 1 records the as-built answers to the Phase 0 questions as decisions (Section 12) and lists every difference from Revision 0 as a gap (Section 13).
The gaps are work items in plan 74 Phase 1b; they are not approved behaviour.
Revision 2, Len's instruction 2026-10-01T00:00:00+08:00 to fix the issues found: Section 14 sets the Phase 1b behaviour for G2 to G4 and G6 to G12, with acceptance tests written before the code.
G12 was found by those tests.
G1 (access rule of the nearby feed) and G5 (rate limit) are not in Revision 2 and wait for Len.

## 1. Purpose

A fisher presses SOS in the handset app, the SOS lands on the MDRRMO dashboard, and the dispatcher acknowledges it with an ETA.
Before this feature nothing happened next for anyone except the caller.
Once the dashboard has acknowledged a call, other fishers nearby should be told that someone near them needs help, because nearby boats are often the fastest rescuers (`docs/13_RESPONDER_LOOP.md`, responder status `NEAREST_VESSEL`).

## 2. Flow before this feature (verified in code, 2026-09-30, before `fd029fb`)

SOS origin is the handset app only.
`mobile/lib/services/sos_service.dart:83-113` saves the SOS locally first, then relays it on two routes in parallel.
Direct HTTPS is `POST https://aqone-backend.onrender.com/api/sos` via `BackendClient.postSos`.
Buoy WiFi handoff is `POST http://192.168.4.1/v1/sos` via `BuoyClient.handoff`.
The backend dedupes on `(vessel_id, client_ts)` or `(vessel_id, nonce)` in `backend/app/api/sos.py`.

Backend ingest is unauthenticated by design.
The dashboard live feed is `GET /api/sos/active`, polled every 3 seconds by `web/js/dashboard/dashboard-live-sos.js`.
Acknowledge is `POST /api/sos/{id}/acknowledge {eta_minutes, responder_status 1-5, responder_note, expected_version}`.
Status code 4 is named `Nearest Vessel` or `Nearby boats alerted`, but it was a label only and triggered nothing.

The return path was 1:1 to the originator only.
The backend exposes `GET /api/sos/downlink` for the gateway, and the handset polls `GET /api/sos/ack/{local_id}` or `GET /api/sos/vessel/{vessel_id}` every 15 seconds while an SOS is live.
The originator sees the ETA card, the countdown, and the local notification via `EtaNotifier`.
No other vessel was notified, and the dashboard's `sos-btn-broadcast` was disabled with `Broadcast to nearby vessels is not supported`.

## 3. Flow

```text
1. Fisher A presses SOS in app.
2. SOS reaches backend (direct or buoy relay) and appears on dashboard live feed.
3. Dispatcher opens incident drawer, sets status plus ETA minutes, presses Acknowledge.
4. Backend stores acknowledged_at plus eta_at and marks incident as ACKED.
5. Backend creates one nearby-broadcast record linked to that sos_event id.
6. Nearby fishers B, C poll that broadcast and see a NEEDS-HELP alert.
7. Fisher A still gets the existing 1:1 ETA card, unchanged.
8. On resolve the broadcast expires; on reopen it reactivates.
```

A broadcast is created only after a human acknowledge, never on SOS arrival alone.
This avoids prank or pocket-dial alarms across the whole fleet.
Re-acknowledging with a new ETA updates the same broadcast rather than creating a second one.

## 4. Who counts as nearby (decision D1)

Nearby is decided by the caller, not by a server-side audience list.
Each handset sends its own current GPS fix to `GET /api/public/sos-nearby`, and the server returns the active broadcasts whose rounded centre lies within both the broadcast's radius and the radius the phone asked for.
A phone without a GPS fix sends the default map centre (`AqOneConfig.defaultMapLat`, `defaultMapLon`) and shows `distance unknown`.
The server therefore never knows how many boats received a broadcast, and there is no recipient count.

The default broadcast radius is 10 km; the dispatcher chooses 5, 10 or 20 km at acknowledge time (decision D3).
The distressed vessel excludes itself by sending its own `vessel_id`.
Synthetic or demo incidents never broadcast, matching the existing downlink rule.
The broadcast position is rounded to 0.005 degrees (about 550 m) so helpers can find the area without exposing an exact live track.

## 5. What nearby users see, hear, and get notified

The nearby handset shows a persistent container at the top of the At sea (Venture) screen, plus a dialog on first arrival, not a silent list row.
The dialog title is `Fisher needs help`.
Its body carries the distance, the MDRRMO ETA if set, and `Respond` plus `Dismiss` actions.
Respond stops the alarm and centres the Venture map on the rounded SOS position.
Dismiss stops the alarm and keeps the container visible until the broadcast expires, so dismissal never looks like the emergency ended.
Sound never outlives a user action, matching the `SosAlarm.stop` rule.

The container sits in the existing Venture stack under the weather capsule, in the pill style of `_buildSosStatus`, so it is visible above the map without covering the right-side action rail.
It shows the nearest broadcasts first, at most 3 rows plus a `+N more` row, and can be collapsed.
Each row shows a red alert icon, `Fisher needs help`, the distance, and the MDRRMO ETA if set.
Distance is formatted as metres below 1 km and one-decimal kilometres at or above 1 km, and it updates on every feed poll.
Without a GPS fix the row shows `distance unknown` rather than hiding the emergency.
The map shows a red distress marker for each active broadcast beside the blue user dot and the buoy markers.
The Revision 0 compact banner on Home and Advisories is not built (G3).

The alarm uses `mobile/assets/audio/broadcastalarm.mp3`, looped by a separate `NearbyAlarm` class so `sos_alarm.wav` stays reserved for the fisher's own SOS.
The loop is foreground-only by design, the same caveat as `SosAlarm` and `SquallAlarm`.
A second trigger for the same broadcast id while ringing is a no-op.

A system notification fires once per broadcast id alongside the alarm, on the channel `nearby_help` with `Importance.high` and `Priority.high` (`EtaNotifier.showNearbyHelp`).
If notification permission is denied or the plugin fails, the in-app alarm still rings.
Seen broadcast ids are held in memory only, so an app restart re-rings (G2), and tapping the notification does not yet open the map (G10).

Nearby users never see the owner name, phone number, licence number, shore contact, note, or exact GPS.
The downlink already strips identity, and this broadcast keeps that rule.

## 6. Backend design (decision D2: a separate feed)

The broadcast has its own read feed rather than riding on `GET /api/public/advisories`.

- `POST /api/sos/{id}/acknowledge` gains `broadcast_enabled` (default `true`) and `broadcast_radius_km` (default 10).
  When enabled, and the incident has a position and is not synthetic, it creates or updates the incident's broadcast and returns it as `broadcast`.
- `GET /api/public/sos-nearby?lat&lon&radius_km&vessel_id` returns the active broadcasts near the caller, nearest first, with no identity fields (`docs/05`).
  It is unauthenticated like the other handset safety feeds (G1).
- `GET /api/sos/active` rows gain `broadcast_state`: `active`, or `off` when the incident has no active broadcast.
- `POST /api/sos/{id}/resolve` expires the broadcast; `POST /api/sos/{id}/reopen` reactivates it.
- The gateway broadcast slot for offline boats is Phase 2 (Section 9).

Table `sos_broadcasts` (migration `040_sos_broadcasts.sql`):

```text
sos_broadcasts
  id SERIAL PK
  sos_event_id INTEGER NOT NULL UNIQUE FK sos_events ON DELETE CASCADE
  center_lat DOUBLE PRECISION NOT NULL   rounded to 0.005 degrees
  center_lon DOUBLE PRECISION NOT NULL   rounded to 0.005 degrees
  radius_km INTEGER NOT NULL DEFAULT 10
  eta_at TIMESTAMPTZ NULL                copy of the incident ETA
  responder_status SMALLINT NULL         copy of the incident status
  state TEXT NOT NULL DEFAULT 'active'   active | expired
  created_by TEXT NULL                   acknowledging operator's email
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  expired_at TIMESTAMPTZ NULL
```

There is at most one row per `sos_event_id`; re-acknowledge updates it in place.
Transitions are audited as `sos.broadcast` (create and every update) and `sos.broadcast_expire`; reactivation on reopen is not audited (G7).

The handset reuses its existing 30-second hazard poll (`AqOneConfig.hazardPollInterval`) in the Venture page, which stays mounted in the app shell's `IndexedStack`, so no new background service is needed.

## 7. Dashboard

The acknowledge modal has an `Also alert nearby vessels that help is needed` checkbox, on by default, and a radius select of 5, 10 or 20 km.
`sos-btn-broadcast` is disabled until the incident is acknowledged.
After an acknowledge without a broadcast it reads `Alert Nearby Vessels` and re-sends the acknowledge with `broadcast_enabled: true`, a 10 km radius, and no ETA change.
While a broadcast is active the button reads `Nearby Vessels Alerted` and the drawer says `Broadcast ACTIVE - nearby boats can see this call.`
Version-conflict handling stays as today with `expected_version` and the 409 path.
The dispatcher cannot yet cancel a broadcast without resolving the incident (G4).

## 8. Mobile

- `NearbySos` (`mobile/lib/models/nearby_sos.dart`) parses the feed.
- `VentureFeeds.nearbySos` calls `GET /api/public/sos-nearby` with the phone's fix and `vessel_id`.
- `NearbyAlarm` (`mobile/lib/services/nearby_alarm.dart`) loops `broadcastalarm.mp3` on its own player.
- `venture_page.dart` shows the container, the first-sighting dialog and the map markers.
- Strings are in `app_en.arb` with `fil` and `akl` drafts, except the distance text (G9).

## 9. Firmware and gateway (Phase 2, deferred)

Phase 1 works only for boats with internet, which matches the existing direct-path responder loop.
Phase 2 extends the `WARN` downlink so offline boats behind a buoy also get the broadcast.
This needs Daniel plus Arnold: a new LoRa frame or an extended `WARN` payload with broadcast id, rounded lat/lon, ETA timestamp and TTL.
The gateway polls the broadcast slot alongside the ETA and chat downlinks, and the buoy caches it and serves it via `GET /v1/warnings`, which the phone already polls.

## 10. Safety and abuse rules

- A broadcast requires a human acknowledge with a responder role, the same auth as `POST /api/sos/{id}/acknowledge`.
- No auto-broadcast on ingest.
- One broadcast per incident, updated in place, expired on any resolve, including a `closed_unconfirmed` prank resolve.
- Synthetic and demo incidents never broadcast.
- The dispatcher can cancel a broadcast without un-acknowledging the incident (not built, G4).
- Rate limit: one create plus three updates per incident per 10 minutes (not built, G5).
- Every action is logged in the case timeline and the global audit search.

## 11. Acceptance criteria

- Fisher A's SOS appears on the dashboard within the 3-second poll as today.
- Dispatcher ACK with ETA creates exactly one `sos_broadcasts` row with a rounded position and the chosen radius.
- Fisher B within the radius hears the looping `broadcastalarm.mp3`, sees the Venture container `Fisher needs help - 2.3 km away` and a `nearby_help` notification within one poll tick, with no owner or phone fields in the payload.
- The container distance updates as the helper moves, shows `distance unknown` without GPS, and clears within one poll tick of resolve.
- Fisher C outside the radius sees nothing.
- Re-ACK updates the ETA in place with no duplicate alert.
- Resolve expires the broadcast and removes the marker on nearby phones within one poll tick.
- A synthetic or demo SOS never creates a broadcast.
- Backend pytest plus ruff, web node tests, and `flutter analyze` plus `flutter test` stay green.

None of these has been verified on a device yet; plan 74 Phase 4 records the evidence.

## 12. Decisions (Len, 2026-09-30T23:10:00+08:00, approving the as-built answers)

| ID | Question (plan 74 Phase 0) | Decision |
|---|---|---|
| D1 | Fresh-position source for the nearby query | The phone's own reported fix; no server-side audience query and no recipient count (Section 4). |
| D2 | One feed or two | Two: a separate `GET /api/public/sos-nearby` (Section 6). |
| D3 | Radius | Default 10 km; the dashboard offers 5, 10 and 20 km. |
| D4 | Mockup `73_MOCKUP_venture-nearby-container.html` | Approved as the reference for the Venture container. |

## 13. Gaps between Revision 0 and the as-built code

Each gap is a plan 74 Phase 1b item.

| ID | Gap | Owner |
|---|---|---|
| G1 | `GET /api/public/sos-nearby` is unauthenticated, so anyone can list the rounded positions of active broadcasts around any point within 50 km. Revision 0 required a vessel-device token, but most handsets are not paired and would then get no alerts. Decide: token, token or rate limit, or public with the rounded position. | Lenard |
| G2 | Seen broadcast ids are kept in memory (`_announcedBroadcasts`), not SQLite, so an app restart re-rings and re-notifies every active broadcast. | Jade |
| G3 | No compact nearby banner on Home and Advisories. The alarm, dialog and notification do fire there, because Venture stays mounted. | Jade |
| G4 | No dispatcher cancel. An acknowledge with the checkbox off leaves an existing broadcast active. | Lenard, Arnold |
| G5 | No rate limit on broadcast create and update. | Lenard |
| G6 | Broadcast errors are swallowed without a log (`except Exception` in `_ensure_broadcast`, `_expire_broadcast`, `_reactivate_broadcast`, the `active_sos` join and `public_sos_nearby`), so a missing table looks exactly like "no broadcast". | Lenard |
| G7 | Audit: re-ACK logs `sos.broadcast` again instead of `sos.broadcast_update`, and reactivation on reopen is not audited. | Lenard |
| G8 | The API accepts `broadcast_radius_km` 1 to 50 while D3 is 5, 10 or 20; only the dashboard clamps. | Lenard |
| G9 | `NearbySos.distanceText` returns hard-coded English (`2.3 km away`) that is passed into `nearbyHelpAway` (`{distance} away`), so English shows `2.3 km away away` and Aklanon mixes English into the line. The notification body also says `MDRRMO`, which `docs/64` P6 keeps off the fisher's core path. | Jade |
| G10 | Tapping the `nearby_help` notification does not open the Venture map at the broadcast. | Jade |
| G11 | The drawer shows `ACTIVE` or nothing; an expired broadcast is indistinguishable from no broadcast. | Arnold |
| G12 | Found 2026-09-30 by the Phase 1b acceptance tests: a failing broadcast statement aborts the Postgres transaction of the acknowledge or resolve it runs in; the exception is swallowed, the endpoint answers 200, and Postgres rolls the acknowledge or resolve back. The dispatcher sees "Acknowledged" or "Resolved" while nothing was saved. | Lenard |

## 14. Phase 1b behaviour (Revision 2)

Designed by the spec author on Len's instruction of 2026-10-01; each rule below has an acceptance test named in plan 74 Phase 1b.
Anything this section does not state stays as Sections 4 to 10 describe.

### 14.1 Backend

- **Cancel (G4).** `POST /api/sos/{id}/acknowledge` with `broadcast_enabled: false` sets the incident's `active` broadcast to `cancelled`, stamps `expired_at`, audits `sos.broadcast_cancel`, and returns the row as `broadcast`.
  It does not change the ETA, note or acknowledgement.
  With no broadcast it creates nothing and returns `broadcast: null`.
  A later acknowledge with `broadcast_enabled: true` makes the same row `active` again.
- **States.** `sos_broadcasts.state` is `active`, `expired` (ended by resolve) or `cancelled` (ended by the dispatcher).
  `GET /api/sos/active` reports each incident's `broadcast_state` as its broadcast's state, or `off` when it has none.
- **Reopen.** Reopening an incident revives an `expired` broadcast and never a `cancelled` one.
- **Audit (G7).** `sos.broadcast` on the first create only; `sos.broadcast_update` on every later acknowledge that keeps it on; `sos.broadcast_cancel`, `sos.broadcast_expire` and `sos.broadcast_reactivate` for the three transitions.
- **Radius (G8).** `broadcast_radius_km` accepts only 5, 10 or 20; anything else is `422` before any write.
- **Failures (G6, G12).** Every broadcast statement runs in its own savepoint (a nested `conn.transaction()`), so a broadcast failure can never roll back the acknowledge, resolve or reopen it rides on.
  The failure is logged at `ERROR` with its traceback through the module's `logging.getLogger(__name__)`.
  The two feeds that read `sos_broadcasts` (`GET /api/sos/active` and `GET /api/public/sos-nearby`) log the same way and still answer `200`, with `off` and `[]` respectively.

### 14.2 Dashboard (G4, G11)

The drawer's broadcast button and state line (`sos-btn-broadcast`, `sos-broadcast-msg`) follow the incident's `broadcast_state`, and opening or refreshing the drawer must not blank the state line.

| Incident | Button | Enabled | State line | Click sends |
|---|---|---|---|---|
| Not acknowledged | `Broadcast to Nearby Vessels` | No | empty | nothing |
| Acknowledged, `off` | `Alert Nearby Vessels` | Yes | empty | acknowledge with `broadcast_enabled: true`, `broadcast_radius_km: 10`, the current `responder_status` and `expected_version`, no `eta_minutes` |
| `active` | `Stop Nearby Alert` | Yes | `Broadcast ACTIVE - nearby boats can see this call.` | acknowledge with `broadcast_enabled: false`, the current `responder_status` and `expected_version`, no `eta_minutes` |
| `cancelled` | `Alert Nearby Vessels` | Yes | `Broadcast CANCELLED - nearby boats no longer see this call.` | as for `off` |

A failed request says `Broadcast not changed - try again.` and restores the button for the current state.

### 14.3 Handset

- **Seen store (G2).** `SeenBroadcastStore` (`mobile/lib/data/seen_broadcast_store.dart`) wraps `AppDatabase`; `Future<bool> markSeen(int broadcastId)` is `true` only the first time this phone ever sees that id.
  Its table `seen_broadcasts` arrives with database version 16, in both `onCreate` and `onUpgrade`.
- **App-wide watcher (G2, G3).** `NearbySosWatcher` (`mobile/lib/services/nearby_sos_watcher.dart`) replaces the polling inside `venture_page.dart`:

  ```dart
  NearbySosWatcher({
    required Future<List<NearbySos>> Function(double lat, double lon) fetch,
    required Future<Fix?> Function() position,
    required SeenBroadcastStore seen,
    required NearbyAlarm alarm,
    required Future<void> Function(NearbySos item) notify,
  });
  ValueListenable<List<NearbySos>> get items;
  bool get hasFix;
  Stream<NearbySos> get firstSightings;
  Future<void> poll();
  void start();           // polls now, then every AqOneConfig.hazardPollInterval
  Future<void> silence(); // stops the alarm, keeps the list
  void dispose();
  ```

  A poll asks around the phone's fix, or around `AqOneConfig.defaultMapLat`, `defaultMapLon` with `hasFix` false, publishes the list, and for each id that `markSeen` reports new: starts the alarm once, calls `notify`, and emits it on `firstSightings`.
  An empty list stops the alarm.
  The app shell creates, starts and disposes the watcher, so nearby calls ring whether or not At sea has been opened (At sea is built lazily, see `_ventureOpened` in `app_shell.dart`).
  `notify` is `EtaNotifier.showNearbyHelp` with the localized title and body, and `fetch` is `VentureFeeds.nearbySos` with the phone's `vessel_id`.
  The shell shows the first-sighting dialog from `firstSightings` on whichever tab is open; Respond switches to At sea and centres the map on the broadcast; Dismiss calls `silence()`.
  At sea draws its container and markers from the watcher and no longer polls on its own.
- **Banner (G3).** `NearbyHelpBanner({required List<NearbySos> items, required bool hasFix, required VoidCallback onTap})` (`mobile/lib/ui/widgets/nearby_help_banner.dart`) shows the nearest call as `Fisher needs help - <distance> away`, `distance unknown` without a fix, and `+N more` when there are more; it renders nothing for an empty list.
  `HomePage` and `AdvisoriesPage` take `NearbySosWatcher? nearby` and `VoidCallback? onOpenNearby` and show the banner at the top; the shell passes `onOpenNearby` as "select At sea".
- **Wording (G9).** `NearbySos.distanceText(double? km, AppLocalizations t)` returns the localized distance without "away" (`450 m`, `2.3 km`, or `nearbyHelpDistanceUnknown`); callers wrap it in `nearbyHelpAway`.
  `nearbyHelpNotifTitle` and `nearbyHelpNotifBody` say "rescue centre" (the `docs/64` placeholder term) and never "MDRRMO", in `en`, `fil` and `akl`.
- **Notification tap (G10).** `EtaNotifier.nearbyPayload(int id)` is `nearby:<id>`; `broadcastIdFromPayload(String?)` parses it back or returns `null`; `handleNotificationPayload(String?)` publishes a parsed id on the broadcast stream `nearbyTaps`.
  `showNearbyHelp` sets the payload; the plugin's `onDidReceiveNotificationResponse` and, for a tap that starts the app, `getNotificationAppLaunchDetails` call `handleNotificationPayload`; the shell opens At sea centred on that broadcast.
