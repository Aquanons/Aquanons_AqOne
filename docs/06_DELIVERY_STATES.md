# 06 — Delivery States

The four states are the shared product language. Every surface — the mobile
outbox, the buoy, the backend, the dashboard — must show a message's real
state and must never fake a later one. This is a definition of done:
"the four delivery states are visible and honest in the app."

## The four states

```
saved ──► relayed ──► delivered ──► acknowledged
```

| State | Meaning | Where it is observed |
|---|---|---|
| `saved` | The SOS exists on the phone and is waiting to be handed to a buoy. No WiFi reachable, or the phone is offline. | Mobile app outbox |
| `relayed` | A buoy accepted the SOS into its store-and-forward queue and acked the phone. It is now on the mesh (LoRa) heading for a gateway — or waiting on a buoy. | Mobile app, after buoy ack |
| `delivered` | The backend ingested the SOS and pushed it to the dashboard. An MDRRMO responder can see it. | Dashboard feed, backend |
| `acknowledged` | An MDRRMO responder acknowledged it; the ack is persisted. | Dashboard, backend |

## Honesty rules

- A state may only move forward. There is no regression.
- The phone can only observe `saved` and `relayed` by itself; it learns
  `delivered`/`acknowledged` only if it later has internet to reconcile
  (`docs/05_PUBLIC_API.md`).
- The buoy knows it accepted a message but not whether a gateway ever heard it.
  It reports `mesh: ok` / `mesh: degraded` and its queue depth, never "sent".
- The backend is the only authority for `delivered` and `acknowledged`.
- If a message is stuck, the UI shows the stuck state honestly — the whole
  point of the app is that an SOS in a dead zone may sit at `relayed`.

## Transitions

| From | To | Trigger | Authority |
|---|---|---|---|
| `saved` | `relayed` | Buoy `POST /v1/sos` returns `accepted: true` | Buoy |
| `relayed` | `delivered` | Backend dedupes a `sos` ingest and updates the projection | Backend |
| `delivered` | `acknowledged` | MDRRMO `POST /api/v1/sos/{id}/ack` | Backend |

## Why the four

The mesh is lossy and unidirectional (mostly). A fisherman whose phone has no
cellular needs to know his SOS was at least accepted by a buoy, and an MDRRMO
needs to know an SOS is being acted on. Two more states than that (a full
message-return path over the mesh) is scope we are not building
(`docs/07_SCOPE_OUT.md`).

## Display conventions (all surfaces)

- Show the state as a word and a short line, never a raw enum.
- `saved` → "Not sent — no buoy nearby. Will send automatically."
- `relayed` → "Handed to the buoy. Waiting for the mesh."
- `delivered` → "Received by the MDRRMO dashboard."
- `acknowledged` → "Responder acknowledged this SOS."

The English above is the source of truth. In the mobile app these sentences
live in `mobile/lib/l10n/app_en.arb` under the `deliveryState*` keys and are
resolved through the `DeliveryStateL10n` extension, not as fields on the
`DeliveryState` enum — a const enum field can never be translated. Editing
the wording here means editing the ARB template too; `mobile/test/
delivery_state_test.dart` asserts the two agree.

Translations (Tagalog `fil`, Aklanon `akl`) must preserve the honesty rules
above. In particular `relayed` must not read as though anyone has received
the SOS. See `docs/22_LOCALIZATION_PLAN.md`.

The dashboard and backend remain English-only.

## API mapping

- Dashboard/backend surface `delivery_state` on every SOS row
  (`docs/05_PUBLIC_API.md`).
- The phone keeps the state in SQLite keyed by a local id, and can reconcile
  `delivered`/`acknowledged` from `GET /api/v1/vessels/{id}/sos`.
- The buoy's ack payload carries the `seq` the phone records so later
  reconciliation can match rows.

## Warning delivery states (downlink)

Distinct from the four canonical SOS delivery states above. Warning delivery
tracks downlink advisories propagating from MDRRMO to fishermen:

```
generated ──► gateway_accepted ──► buoy_received ──► phone_received ──► user_acknowledged
```

| State | Meaning | Authority |
|---|---|---|
| `generated` | Warning created in the system (MDRRMO authored or research). | Backend |
| `gateway_accepted` | Gateway received advisory from backend and queued for LoRa broadcast. | Gateway |
| `buoy_received` | Buoy received and cached the warning frame over LoRa mesh. | Buoy |
| `phone_received` | Offline phone connected to buoy WiFi and retrieved the warning. | Handset |
| `user_acknowledged` | Fisherman deliberately acknowledged reading the warning on screen. | Handset / Fisherman |

Rules:
- Byte receipt (`buoy_received`, `phone_received`) does NOT prove display, comprehension, or compliance.
- `user_acknowledged` requires deliberate user interaction on the handset.
- Unconnected handsets remain honestly un-delivered; no speculative acknowledgement.

