# 04 — Ingest API (gateway → backend)

The HTTPS contract between the gateway node (Arnold) and the FastAPI backend
(Lenard). The gateway is the only mesh edge with internet and the only caller
of this API.

## Scope

- Authenticated submission of mesh frames.
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
or `{"known": false}`. The gateway caches lookups; on `known: false` it may
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
| `observed_at` | yes | RFC 3339 timestamp of the contact itself, not the ingest time. |
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

Errors: `401` bad/missing API key; `422` malformed body (bad timestamp,
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

## Warning delivery tracking

Warning events track the hop-by-hop delivery of safety advisories down to the
fisher:

### `POST /api/advisories/delivery` — record a warning delivery state

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
