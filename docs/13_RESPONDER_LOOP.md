# 13 — Responder Loop (dashboard → fisherman)

Closing the SOS loop: when a dispatcher acknowledges a distress call, the
fisherman learns that help is coming and roughly when.

Today the loop is open. A fisher presses SOS and receives silence. They cannot
tell whether the message got out, whether anyone saw it, or whether to stay
with the boat or start swimming. That silence is its own emergency.

---

## What is actually missing

Three gaps, found by reading the code rather than the architecture doc.

**1. The endpoint the phone polls does not exist.**
`backend_client.dart` calls `GET /api/v1/vessels/{id}/sos`. Nothing in
`backend/app/api/` serves that path. `reconcile()` has therefore never
returned anything - it 404s and silently gives up. The acknowledgement return
path is absent, not partial.

**2. Reconciliation matches on the wrong key.**
```dart
final seq = record.seq;
if (seq == null) continue;      // direct-path SOS have no seq
```
`seq` is assigned by the buoy ack. An SOS delivered only over the direct HTTPS
path never has one, so it can never be reconciled. Fixing this is part of the
work, not optional.

**3. The mesh has no downlink for payload.**
`docs/02_LOAM_PACKET_SPEC.md` defines `ACK` (`0x02`), but it is a mesh-level
acknowledgement for `(SRC_ID, SEQ)` and carries nothing. `GET /v1/status`
returns a fixed shape with no slot for a message to the phone. Sending an ETA
over LoRa needs a protocol change.

---

## Design decisions

### Store an absolute time, not a duration

The dispatcher types "15 minutes". The system stores **`eta_at`, a timestamp**.

A duration decays in transit. If the message spends four minutes traversing a
store-and-forward mesh, a phone told "15 minutes" counts down from 15 when only
11 remain - and the error grows with every relay hop. A timestamp is correct
however long delivery takes, and the handset derives the countdown locally.

### The countdown must not lie when it expires

When `eta_at` passes with no resolution, the app does **not** show 00:00 or a
negative number. It switches to *"Rescue delayed — still en route"*.

A countdown that reaches zero and stops implies the rescue failed or the system
stopped caring. Neither is true, and a person alone in the water reading that
will make worse decisions.

### Status codes, one byte

Free text is expensive in a 64-byte frame and invites inconsistency under
pressure. A fixed vocabulary costs one byte and translates cleanly into Aklanon
on the handset.

| Code | Name | Shown to the fisher |
|---|---|---|
| `0x01` | `RECEIVED` | "MDRRMO has your call" |
| `0x02` | `DISPATCHED` | "Rescue boat on the way" |
| `0x03` | `COAST_GUARD` | "Coast Guard notified" |
| `0x04` | `NEAREST_VESSEL` | "Nearby boats alerted" |
| `0x05` | `DELAYED` | "Delayed — still coming" |

`NEAREST_VESSEL` is the one worth building toward: it is PRD §5.6, the
nearest-responder broadcast, and off Basilan it was nearby fishing boats that
actually pulled people out.

### The fisher can answer

One tap, one byte back:

| Code | Name | Meaning |
|---|---|---|
| `0x01` | `STILL_IN_DANGER` | Received the ETA, situation unchanged |
| `0x02` | `SAFE_NOW` | Resolved — stand down |

This matters more than it looks. It confirms the fisher is **alive and
conscious** after the acknowledgement, and `SAFE_NOW` lets a dispatcher release
assets to another incident.

---

## Resolution codes (frozen 2026-09-24)

Frozen by `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Phase 0; built in Track B phase B1, Track M phase M4 and Track W phase W2.
A resolved incident carries one `resolution_code` (`docs/05` E5.1).
This table is the one place that says what each code means and what the boat is told.
The backend sends only the code; the phone maps it to localised text (never an enum field), and the dashboard shows the English label.

| Code | Radio `rc` (`docs/02` E2.1) | Dispatcher meaning | Boat is told (ARB key) |
| --- | --- | --- | --- |
| `rescued` | 1 | The crew was picked up or assisted. | "Closed by MDRRMO." (`sosClosedByMdrrmo`) |
| `safe_confirmed` | 2 | The dispatcher reached the boat and it is safe. | "Closed by MDRRMO." (`sosClosedByMdrrmo`) |
| `stood_down_by_fisher` | 3 | The fisher replied `SAFE_NOW`. | "Closed by MDRRMO." (`sosClosedByMdrrmo`) |
| `duplicate` | 4 | Another incident covers the same call. | Nothing new; the phone follows the surviving incident (`sosClosedDuplicate`). |
| `closed_unconfirmed` | 5 | Closed without reaching the boat, for example a suspected prank. | "MDRRMO closed this call without reaching you. If you still need help, press SOS again." (`sosClosedUnconfirmed`) |
| `unspecified` | 6 | Resolved without a reason (older dashboards). | Same as `closed_unconfirmed` (`sosClosedUnconfirmed`). |

Rules:

- A resolve with no reason is stored as `unspecified`, so the boat always gets the safe message by default (EC-M10).
- `STILL_IN_DANGER` within 2 hours of a resolve reopens the incident and rings the dashboard (EC-M9, `docs/05` E5.2).
- The dispatcher can reopen any resolved incident (`POST /api/sos/{id}/reopen`).
- Codes are validated with MDRRMO before field use (docs/61 Section 12, decision 6).

## Phase 1 — direct path (no firmware needed)

Deliverable: dispatcher acknowledges with an ETA, fisher sees it within one
poll cycle, whenever the handset has internet.

**Schema** (`migration 008`)

```
sos_events
  + eta_at            TIMESTAMPTZ
  + responder_status  SMALLINT        -- code table above
  + responder_note    TEXT            -- optional, direct path only
  + fisher_reply      SMALLINT        -- STILL_IN_DANGER / SAFE_NOW
  + fisher_replied_at TIMESTAMPTZ
  + resolved_at       TIMESTAMPTZ
```

**Backend**

- `POST /api/sos/{id}/acknowledge` — extend to accept `eta_minutes` and
  `responder_status`. Server converts minutes to `eta_at = NOW() + interval`,
  so the clock is authoritative and not the browser's.
- `GET /api/sos/active` — the dashboard's live feed returns every
  **unresolved** event, including one already acknowledged, so a dispatcher
  can see the fisher's `STILL_IN_DANGER` / `SAFE_NOW` reply land on it. An
  event leaves this feed only once resolved (see `docs/05_PUBLIC_API.md`).
- `GET /api/sos/vessel/{vessel_id}` — what the handset polls. Returns delivery
  state, acknowledgement, `eta_at`, status code and any note. Requires the
  vessel-device bearer token (`docs/05_PUBLIC_API.md`'s Option A) bound to
  that vessel; ingest itself stays unauthenticated, but this per-vessel read
  is not. Returns only that vessel's own events.
- `GET /api/sos/ack/{local_id}` — the read-back for a **direct-path handset
  with no vessel-device token**, which therefore could never call the
  credentialed vessel feed (the app ships no enrolment UI). Exactly as
  unauthenticated as the ingest that raised the call, for the same trust
  rationale (`docs/05`). Keyed on the handset's own `local_id`; returns that
  one incident's acknowledgement fields only, 404 until the id exists on the
  backend. Mirrors the vessel-feed event shape so the phone parses both
  through one code path.
- `POST /api/sos/{id}/reply` — the one-byte answer. Requires the same
  vessel-device bearer token, and only updates an event owned by that token's
  vessel. Monotonic once resolved: a retry after `SAFE_NOW` cannot reopen the
  incident or replace what was recorded.

**Dashboard**

- Acknowledge becomes a small modal: ETA in minutes (quick picks 10 / 20 / 30 /
  45 / 60 plus free entry) and a status dropdown from the code table.
- The incident row shows a live countdown and flips to *Delayed* when `eta_at`
  passes without resolution.
- The fisher's reply appears on the row — `STILL_IN_DANGER` in red,
  `SAFE_NOW` resolving the incident.

**Flutter app**

- Fix reconciliation: match on `local_id` when present, fall back to `seq`.
  Without this, direct-path SOS never reconcile.
- `SosRecord` gains `etaAt`, `responderStatus`, `responderNote`.
- Venture shows a responder card once acknowledged: status line, live
  countdown, and a **"Still in danger"** button.
- Poll faster while an SOS is live. `reconcileInterval` of 2 minutes is fine for
  housekeeping and far too slow for someone waiting on an answer — drop to
  ~15 seconds while any record is unresolved, then back off.
- A system notification fires when reconcile first sees an acknowledgement
  with an ETA, carrying the ETA minutes. The in-app dialog alone is invisible
  on a locked or backgrounded phone; the shade is the "help is on the way"
  moment if the fisher is not looking at the screen. Fired once, deduplicated
  on the same `local_id` as the dialog.

---

## Phase 2 — LoRa downlink (needs Daniel + Arnold)

Deliverable: the same acknowledgement reaches a handset with no internet.

**Repurpose frame type `0x04`**, currently marked "future use", as
`RESPONDER_STATUS`. Payload is 9 bytes:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | `DST_ID` — target endpoint (the handset's `SRC_ID`) |
| 4 | 1 | `STATUS` — code table above |
| 5 | 4 | `ETA_TS` — absolute epoch seconds, 0 if unknown |

Well inside the 64-byte payload budget, leaving room for a short note later.

**Flow:** backend → gateway → LoRa (`0x04`, `DST_ID` = handset) → buoys relay
with TTL as usual → destination buoy caches it.

**Buoy change:** `GET /v1/status` gains an optional `messages` array so a phone
that connects can collect anything waiting for it. Buoys are already
store-and-forward for uplink; this is the same mechanism pointed the other way.

**Contract owners:** `docs/02_LOAM_PACKET_SPEC.md` (Daniel),
`docs/03_PHONE_BUOY_WIFI.md` (Daniel + mobile), `docs/04_INGEST_API.md`
(Arnold). Update the docs before writing code, per `AGENTS.md`.

---

## Risks

| Risk | Handling |
|---|---|
| Dispatcher gives an optimistic ETA and misses it | `DELAYED` status plus the honest "still en route" state. Never a countdown that expires into silence. |
| A vessel-device token is stolen or a reply is replayed | The reply endpoint requires that token and only affects the event owned by its vessel; it cannot touch another vessel's incident or create a new one (`docs/05_PUBLIC_API.md`'s Option A). |
| Phone battery dies while polling every 15s | Fast polling only while an SOS is unresolved, then back to 2 minutes. |
| Fisher never sees the ETA because they are offline | Exactly what Phase 2 exists to fix. Until then the app must say "waiting for signal" rather than implying nobody answered. |

---

## 2026-08-29 — verification record

Phase 1 of this document (the direct path: acknowledge with ETA, the fisher's
`STILL_IN_DANGER` / `SAFE_NOW` reply, and the responder card) is implemented
and covered by the automated suite - see `docs/08_DEMO_AND_STATUS.md`'s
matching entry for the full command list and results (backend 108 passed,
mobile 151/151, web 32/32, `flutter build web` succeeded). Phase 2 (the LoRa
downlink) remains unbuilt, as this document already states.

A real end-to-end run - a paired handset pressing Manual SOS, a dispatcher
acknowledging it on a live dashboard, and the handset showing and answering
that acknowledgement - was attempted but not completed in this environment:
no working local PostgreSQL credential or Docker install was available to run
the backend against, and no physical device, emulator, or Windows build was
available to run the handset app outside its test harness. See
`docs/08_DEMO_AND_STATUS.md` for the specific blockers. This is an accurate
account of what was checked, not a claim that the loop has been watched
working live.

---

## Why this is worth building

It converts AqOne from an alarm into a conversation. In PRD terms it strengthens
§5.6: once the backend can address a specific handset, the same channel can warn
*other* vessels near a distress position - which is how people were actually
rescued off Basilan.

It is also the most human part of the demo. "The fisherman sees that help is
20 minutes away" lands harder than any model metric.
