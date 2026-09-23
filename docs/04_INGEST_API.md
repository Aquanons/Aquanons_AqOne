# 04 — Ingest API (gateway → backend)

The HTTPS contract between the tall shoreline gateway (Arnold) and the FastAPI
backend (Lenard). The gateway is the only LoRa edge with internet and the only
caller of this API. It may receive a frame directly from a boat pod or through
an optional stationary sensor/relay buoy.

## Scope

- Authenticated submission of direct or relayed LoRa frames.
- Device / vessel registration (external id → UUID mapping).
- Dedupe semantics.

Out of scope: the LoRa wire format (`docs/02_LOAM_PACKET_SPEC.md`) and the
public read surface (`docs/05_PUBLIC_API.md`).

## Transport

- `HTTPS` only. Plain HTTP is refused by the backend.
- Base URL is a platform env var on the gateway, e.g.
  `https://incredible-liberation-production-aad7.up.railway.app`.
- Auth: header `X-Api-Key: <gateway api key>` on every request. Keys are
  issued per gateway and revoked in the backend admin console.

## Endpoints

### `POST /api/v1/ingest` — submit a decoded frame

The gateway verifies the LoRa signature first (`docs/02_LOAM_PACKET_SPEC.md`)
and converts external ids to UUIDs (`/api/v1/devices/lookup` below). Then it
posts the decoded, normalized event.

Request body (JSON):

```json
{
  "v": 1,
  "type": "sos",
  "src_ext_id": 1001,
  "relay_ext_id": 1001,
  "src_id": "8f7b2c41-...",
  "relay_id": "a1b2c3d4-...",
  "seq": 42,
  "ts": 1722700000,
  "ttl": 5,
  "hops": 3,
  "payload": {
    "kind": "sos",
    "boat": "BG-123",
    "lat": 11.6050,
    "lon": 122.3125,
    "note": "engine down"
  },
  "gateway_id": "gw-01",
  "recv_ts": 1722700005
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `type` | yes | `sos` \| `ack` \| `ping` \| `status` |
| `src_ext_id` | yes | External id from the frame. |
| `relay_ext_id` | yes | External id of the last relay. |
| `src_id` | no | UUID for `src_ext_id` if already resolved. |
| `relay_id` | no | UUID for `relay_ext_id` if already resolved. |
| `seq` | yes | Origin sequence number (dedupe key). |
| `ts` | yes | Origin epoch seconds. |
| `ttl` | yes | As received. |
| `hops` | yes | As received. |
| `payload` | yes | Type-specific payload (frame payload JSON). |
| `gateway_id` | yes | Gateway external id. |
| `recv_ts` | yes | Gateway epoch seconds. |

Success `200`:

```json
{
  "accepted": true,
  "event_id": "evt_1234",
  "deduped": false,
  "vessel_id": "8f7b2c41-..."
}
```

`deduped: true` means the backend already had `(src_ext_id, seq)` and this
submission was dropped (still `accepted: true`, with the original `event_id`).

Errors: `401` bad/missing API key; `400` malformed body; `429` rate limit.

### `GET /api/v1/devices/lookup?ext_id=<n>` — resolve an external id

Returns `200` with `{"id": "<uuid>", "kind": "buoy"|"vessel", "known": true}`
or `{"known": false}`. The existing `buoy` kind covers a boat pod or a
stationary field node at this contract boundary. The gateway caches lookups; on
`known: false` it may
call `POST /api/v1/devices/register`.

### `POST /api/v1/devices/register` — first sighting

```json
{
  "v": 1,
  "ext_id": 1001,
  "kind": "buoy",
  "label": "AqOne-BUOY01"
}
```

Returns `200` with the assigned UUID. The backend owns this mapping and never
reassigns an external id.

## Contact events (routine vessel-buoy contact)

Distinct from the mesh frames above. A contact event is a routine, low-
priority record that a vessel was in range of a buoy during an active trip —
the only trustworthy input to the trip-anomaly/overdue detector
(`docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`). It is not a
distress signal and carries no priority/TTL/hop metadata.

### `POST /api/v1/contacts` — submit one contact event

Same transport and `X-Api-Key` auth as `/api/v1/ingest` above, via its own
`GATEWAY_API_KEY` credential.

Request body (JSON):

```json
{
  "v": 1,
  "event_id": "gw-01-000042",
  "vessel_id": "NW-001",
  "trip_id": "trip-2026-08-29-01",
  "buoy_id": "BUOY01",
  "observed_at": "2026-08-29T05:00:00Z",
  "latitude": 11.6050,
  "longitude": 122.3125,
  "source": "live"
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `event_id` | yes | Upstream event id from the gateway. The idempotency key — resubmitting the same `event_id` returns the original contact, never a duplicate row. |
| `vessel_id` | yes | Vessel identifier, ≤ 32 chars. |
| `trip_id` | yes | Identifies the vessel's current trip, ≤ 64 chars. |
| `buoy_id` | yes | Must already be a registered buoy; an unrecognized id is rejected rather than silently creating one. |
| `observed_at` | yes | RFC 3339 timestamp of the contact itself, not the ingest time. Rejected if more than 5 minutes ahead of the server clock - that indicates a broken buoy clock, not a real future contact. |
| `latitude` / `longitude` | no | Last known position at this contact, if the buoy has it. |
| `source` | yes | `live` for a real field contact, `synthetic` for demo/test data. Production trip-anomaly evaluation only ever reads `live` rows — see docs/38 Phase 1 item 5. Neither the handset nor the public dashboard can submit a contact event at all, live or synthetic; only a holder of `GATEWAY_API_KEY` can. |

Success `200`:

```json
{
  "accepted": true,
  "event_id": "gw-01-000042",
  "deduped": false,
  "contact_id": 1042,
  "vessel_id": "NW-001",
  "trip_id": "trip-2026-08-29-01"
}
```

`deduped: true` means `event_id` was already stored; the response reflects
the original contact, not a new one — no second logical contact is ever
created, and the response is otherwise identical either way so a retrying
gateway does not need to branch on it.

Errors: `401` bad/missing API key; `422` malformed body (bad/future timestamp,
empty/oversized id, missing/invalid `source`); `400` unknown `buoy_id`.

## Pressure events (buoy barometric telemetry)

The trusted-telemetry contract squall nowcasting is gated on
(`docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md` Phase 1). Squall
nowcasting reads only rows that arrived through this endpoint with
`source: 'live'`; nothing else is a live pressure reading no matter what a
model or dashboard route later claims.

### `POST /api/v1/pressure-events` — submit one pressure reading

Same transport and `X-Api-Key` auth as `/api/v1/ingest` above, via its own
`GATEWAY_API_KEY` credential (the same one `/api/v1/contacts` uses).

Request body (JSON):

```json
{
  "v": 1,
  "event_id": "gw-01-000099",
  "buoy_id": "BUOY01",
  "observed_at": "2026-08-29T05:00:00Z",
  "pressure_hpa": 1008.4,
  "source": "live"
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `event_id` | yes | Upstream event id from the gateway. The idempotency key — resubmitting the same `event_id` returns the original reading, never a duplicate row. |
| `buoy_id` | yes | Must already be a registered buoy; an unrecognized id is rejected rather than silently creating one. |
| `observed_at` | yes | RFC 3339 timestamp of the reading itself, not the ingest time. Rejected if more than 5 minutes ahead of the server clock — that indicates a broken buoy clock, not a real future reading. No lower bound: a delayed gateway resend after an outage still carries a genuinely old `observed_at` and must still be accepted here — whether data that old is still *trustworthy* for a live nowcast is a separate freshness decision made at read time (squall Phase 2), not an ingest rejection. |
| `pressure_hpa` | yes | Rejected outside `850`–`1100` hPa. This is a physical-plausibility guard against malformed input only — the lowest sea-level pressure ever recorded is ~870 hPa (in a typhoon) and the highest ~1085 hPa. It is deliberately **not** the tighter operational sanity range squall Phase 2 must set from an MDRRMO/technical-owner decision; that range decides whether an array is trustworthy enough to nowcast from, this one only rejects garbage. |
| `source` | yes | `live` for a real field reading, `synthetic` for demo/test data. Unlike `/api/v1/contacts`, a `synthetic` pressure event is **not** accepted through the gateway key alone: it additionally requires `DEMO_MODE` enabled and a valid `X-Demo-Key` header (the same credential `/api/demo/*` routes use), because a squall reading can reach a handset `RETURN NOW` alarm and a demo/test value must never be able to fabricate one. `live` readings are always evaluated by squall nowcasting; `synthetic` readings never are. |

Success `200`:

```json
{
  "accepted": true,
  "event_id": "gw-01-000099",
  "deduped": false,
  "reading_id": 5031,
  "buoy_id": "BUOY01",
  "source": "live"
}
```

`deduped: true` means `event_id` was already stored; the response reflects
the original reading, not a new one — no second logical reading is ever
created, and the response is otherwise identical either way so a retrying
gateway does not need to branch on it.

Errors: `401` bad/missing gateway API key; `403` `source: 'synthetic'`
submitted without `DEMO_MODE` and a valid `X-Demo-Key`; `422` malformed body
(bad/future timestamp, empty/oversized id, pressure outside sanity range,
missing/invalid `source`); `400` unknown `buoy_id`.

## SOS downlink (the responder's answer, backend -> gateway)

Every other endpoint in this document flows gateway -> backend. This one is
the return leg: the shore gateway reads the dispatcher's acknowledgement and
ETA here and puts them back on the LoRa mesh, where the buoy caches them and
pushes them to the fisher's handset.

### `GET /api/sos/downlink` - the responder's answer to every live call

Same transport and `X-Api-Key` auth as `/api/v1/ingest` above, via the same
`GATEWAY_API_KEY` credential `/api/v1/contacts` and `/api/v1/pressure-events`
use. No body, no query parameters.

This is deliberately **not** `GET /api/sos/active`, which serves the same
underlying incidents to the dashboard. `/active` is behind `require_user` (a
dispatcher login) and carries position, the fisher's own distress note, boat
name, trust tier and the vessel owner's name, licence number and phone. The
gateway key ships hardcoded in firmware on a mast; if it leaks it must not
become a live feed of where every boat in the municipality is and who owns
it. `/downlink` returns only fields the gateway is about to broadcast over
the radio in clear anyway, so it discloses nothing the fisher is not already
being told.

```json
{
  "events": [
    {
      "id": 41,
      "vessel_id": "NW-001",
      "seq": 7,
      "delivery_state": "acknowledged",
      "acknowledged_at": "2026-09-21T03:00:00+00:00",
      "acked_by": "dispatcher_maria",
      "eta_at": "2026-09-21T03:40:00+00:00",
      "responder_status": 2,
      "responder_note": "Coast Guard boat en route from Dumaguit",
      "resolved_at": null
    }
  ]
}
```

| Field | Notes |
| --- | --- |
| `delivery_state` | Collapsed server-side (`relayed` / `delivered` / `acknowledged`, docs/06). The gateway used to recompute this from the delivery flags, which put a second copy of `_delivery_state()` in firmware that only a reflash could correct. |
| `responder_status` | The one-byte vocabulary from docs/13. The label is **not** sent - the buoy renders it locally, so the text survives a mesh with no internet. |
| `resolved_at` | Set once a dispatcher closes the incident. |

Unlike `/api/sos/active`, which drops an incident the moment it is resolved,
this feed holds resolved incidents for `DOWNLINK_RESOLVED_WINDOW_HOURS`
(6 h). The gateway polls on a 45 s cycle, so an incident acknowledged and then
resolved between two polls would otherwise leave the mesh without the closure
ever going out, and the handset would count down an ETA for a rescue that had
already finished. Capped at 100 events, newest first.

Errors: `401` missing or wrong `X-Api-Key` - including a valid operator bearer
token or demo key, neither of which substitutes for it.

Gateway configuration: set `GATEWAY_API_KEY` in
`firmware/shore/AqOneShore/AqOneShore.ino` to the same value as the backend's
`GATEWAY_API_KEY` environment variable. Left empty, SOS still flows up and
chat still flows both ways, but no acknowledgement can reach a boat - the
gateway's OLED shows `Ack : no key` and it says so on serial every poll.

## Warning delivery tracking

Warning events track the hop-by-hop delivery of safety advisories down to the
fisher:

### `POST /api/advisories/delivery` - record a warning delivery state

Requires `X-Api-Key` header with a valid gateway API key.
Anonymous or unauthorized callers receive HTTP 401.

Request body (JSON):

```json
{
  "warning_id": 101,
  "vessel_id": "NW-001",
  "buoy_id": "BUOY01",
  "delivery_state": "buoy_received",
  "occurred_at": "2026-09-15T01:15:00Z",
  "details": {}
}
```

| Field | Required | Notes |
|---|---|---|
| `warning_id` | yes | Identifier of the advisory. |
| `delivery_state` | yes | One of: `generated`, `gateway_accepted`, `buoy_received`, `phone_received`, `user_acknowledged`. |
| `vessel_id` | conditional | Required for `user_acknowledged` and `phone_received`. |
| `buoy_id` | conditional | Gateway or buoy external identifier. |
| `occurred_at` | no | Occurrence timestamp in RFC 3339; defaults to server time. |
| `details` | no | Arbitrary JSON metadata (hop count, RSSI, SNR). |

Deduplication: submissions for `(warning_id, delivery_state, buoy_id, vessel_id)`
are idempotent (`deduped: true`), preserving the earliest occurrence and
authoritative receipt time.

## SOS ingest provenance rules (`POST /api/sos`)

The SOS ingest endpoint (`POST /api/sos`) accepts distress calls from either the handset (direct internet) or the shore gateway (relayed LoRa frame).
To guarantee life-safety delivery, the endpoint never rejects an unauthenticated distress call.
However, provenance claims are strictly gated:
- Claiming buoy relay provenance (`source: 'buoy'`, `buoy_id`, `src_id`, `seq`) requires a valid `X-Api-Key` header matching `GATEWAY_API_KEY`.
- If an unauthenticated caller submits buoy fields without a valid gateway key, the distress call is safely accepted but stored as a direct delivery (`source: 'direct'`), and all buoy fields (`buoy_id`, `src_id`, `seq`, `delivered_via_buoy`) are dropped.
- This prevents untrusted callers from forging mesh delivery states or injecting unregistered buoy rows into the database.
- Trust tier: incoming `trust_tier` is stored as `self_declared` unless verified by a bound vessel device token (`phone_verified`).
- The value `confirmed_by_responder` is never accepted from ingest.


## Dedupe and ordering

- Dedupe key: `(src_ext_id, seq)`. The first accepted submission wins; later
  duplicates return `deduped: true` and do not re-enter the event log.
- `ts` is advisory (origin clock); `recv_ts` is the trustworthy ingest order.
- The backend appends every accepted frame to the append-only event log before
  updating projections (`docs/01_ARCHITECTURE.md`).

## Backend pipeline for `type: sos`

```
verify api key → resolve ids → dedupe (src_ext_id, seq)
→ append event log → upsert sos_events projection → SSE push (05_PUBLIC_API.md)
```

## Versioning

Bump `v` on breaking changes. Update this doc first, then tell Arnold and
Lenard.
