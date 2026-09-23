# 03 — Phone ↔ Boat Pod WiFi (SoftAP HTTP)

The contract between the Flutter app (Jade, Doreen Kay) and the boat safety pod
firmware (Daniel) over the pod's WiFi access point. The phone is in airplane
mode: no cellular, WiFi station to the pod's SoftAP only. The filename remains
`03_PHONE_BUOY_WIFI.md` for compatibility with existing links.

## Scope

- WiFi association and AP details.
- SOS handoff and the pod ack.
- Delivery-state reporting the phone persists locally (SQLite).

Out of scope: the LoRa side (`docs/02_LOAM_PACKET_SPEC.md`) and anything that
needs the internet.

## SoftAP profile

| Parameter | Value |
|---|---|
| SSID | `Aquan` |
| Password | none — the pod AP is open by design for emergency use |
| Phone role | WiFi **station** (phone keeps its SIM in airplane mode) |
| Pod IP | `192.168.4.1` |
| Phone DHCP | assigned by the pod SoftAP |
| HTTP | plain HTTP (no TLS on the pod; the hop is 1:1 and local) |

The pod SHOULD serve a captive portal at `http://192.168.4.1/` with:
- the boat pod name and battery level,
- a button that deep-links into the Flutter app,
- the one-line status ("pod online, mesh reachable / mesh unreachable").

## Endpoints

### `POST /v1/sos` — hand off an SOS

Request body (JSON):

```json
{
  "v": 1,
  "vessel_id": "fisher-7f3a",
  "boat": "BG-123",
  "lat": 11.6050,
  "lon": 122.3125,
  "note": "engine down",
  "client_ts": 1722700000
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `vessel_id` | yes | Device-local stable id (≤ 32 chars). This is the phone's identity the pod maps into a `SRC_ID`. |
| `boat` | yes | Display name (≤ 32 chars). |
| `lat` / `lon` | no | Decimal degrees; omit if no GPS fix. |
| `note` | no | Free text (≤ 64 chars). |
| `client_ts` | yes | Phone epoch seconds — used for ordering, not trust. |

Success response `200 OK`:

```json
{
  "accepted": true,
  "buoy_id": 1001,
  "src_id": 1001,
  "seq": 42,
  "server_ts": 1722700002
}
```

| Field | Meaning |
|---|---|
| `accepted` | The pod accepted the SOS into its store-and-forward queue. |
| `buoy_id` | Compatibility field carrying the serving pod's external node id. |
| `src_id` | External id the pod assigned to this vessel session. |
| `seq` | The LoRa frame `SEQ` the pod will transmit this SOS with. |
| `server_ts` | Pod epoch seconds. |

Errors: `400` for a malformed body, `503` if the pod cannot accept (queue
full). The phone treats a `200` as delivery state `relayed`; a network error
keeps the message `saved` (`docs/06_DELIVERY_STATES.md`).

### `GET /v1/status` — pod health

Response `200 OK`:

```json
{
  "v": 1,
  "buoy_id": 1001,
  "batt": 86,
  "mesh": "ok",
  "queued": 3
}
```

`mesh` is `"ok"` if the pod recently heard another radio endpoint, otherwise
`"degraded"`. `queued` is the number of SOS messages still waiting to be
forwarded on LoRa. The app uses this for the honest signal meter.

### `GET /v1/warnings` — active weather warnings & advisories

Offline handsets poll this endpoint when connected to pod WiFi to retrieve
active warnings relayed from shore over LoRa.

Response `200 OK`:

```json
{
  "advisories": [
    {
      "id": 101,
      "title": "Gale Warning",
      "priority": "Warning",
      "municipality": "New Washington",
      "description": "Rough seas expected over eastern seaboard.",
      "source": "MDRRMO",
      "publish_date": "2026-09-15T00:00:00Z",
      "expiration_date": "2026-09-16T23:59:59Z"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `advisories` | Array of active, unexpired advisories currently cached on the pod. |
| `id` | Advisory identifier. |
| `title` | Short summary title. |
| `priority` | `"Emergency"`, `"Warning"`, `"Information"`, or `"Community"`. |
| `municipality` | Applicable area or `"All"`. |
| `description` | Full text instruction or warning description. |
| `source` | Authority (`"MDRRMO"`, `"LGU"`, `"AqOne Research"`). |
| `publish_date` | RFC 3339 timestamp or Philippine date string (`YYYY-MM-DD`). |
| `expiration_date` | RFC 3339 timestamp or Philippine date string. If absent, handset bounds retention to max 48h. |

Expired advisories are automatically pruned by the pod cache and not returned.

## Phone-side rules

- Keep the SOS in a local **outbox** (SQLite) until a `200` changes its state
  to `relayed`. The outbox survives app restarts and is the single source of
  truth for the fisherman.
- One outstanding SOS per vessel at a time is recommended; a new SOS replaces
  or queues after the old one only with explicit user choice.
- If the pod reports `mesh: degraded`, tell the user the message will wait on
  the pod (state stays `relayed` until the mesh delivers).

## Pod-side rules

- On `POST /v1/sos`, the pod assigns `src_id` and `seq` and enqueues a signed
  LoRa `SOS` frame (`docs/02_LOAM_PACKET_SPEC.md`). The `vessel_id` maps to
  the 32-bit `src_id`; the pod keeps that mapping in NVS.
- The pod acks the phone only after the frame is in its store-and-forward
  queue (not after LoRa transmission — the phone cannot know about radio
  success, and we do not fake it).
- The pod retransmits queued SOS frames directly toward the shore gateway, or
  through optional relay buoys, until a mesh
  `ACK` arrives or the message expires (default 15 minutes).

Stationary sensor and relay buoys do not need to expose this phone API by
default. They may run LoRa-only firmware unless a field test gives them a
specific local WiFi purpose.

## Example exchange

```
Phone  ──►  Boat pod        POST /v1/sos  {v:1, vessel_id, boat, note, client_ts}
Phone  ◄──  Boat pod        200 {"accepted":true,"buoy_id":1001,"src_id":1001,"seq":42,...}
Phone  ──►  Boat pod        GET /v1/status
Phone  ◄──  Boat pod        200 {"v":1,"buoy_id":1001,"batt":86,"mesh":"ok","queued":3}
```

## Versioning

Bump `v` on breaking changes. Update this doc first, then tell Daniel and the
mobile pair.
