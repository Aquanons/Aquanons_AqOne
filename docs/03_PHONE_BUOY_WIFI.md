# 03 — Phone ↔ Buoy WiFi (SoftAP HTTP)

The contract between the Flutter app (Jade, Doreen Kay) and the buoy firmware
(Daniel) over the buoy's WiFi access point. The phone is in airplane mode: no
cellular, WiFi station to the buoy's SoftAP only.

## Scope

- WiFi association and AP details.
- SOS handoff and the buoy ack.
- Delivery-state reporting the phone persists locally (SQLite).

Out of scope: the LoRa side (`docs/02_LOAM_PACKET_SPEC.md`) and anything that
needs the internet.

## SoftAP profile

| Parameter | Value |
|---|---|
| SSID | `Aquan` |
| Password | none — the buoy AP is open by design for emergency use |
| Phone role | WiFi **station** (phone keeps its SIM in airplane mode) |
| Buoy IP | `192.168.4.1` |
| Phone DHCP | assigned by the buoy SoftAP |
| HTTP | plain HTTP (no TLS on the buoy; the hop is 1:1 and local) |

The buoy SHOULD serve a captive portal at `http://192.168.4.1/` with:
- the buoy name and battery level,
- a button that deep-links into the Flutter app,
- the one-line status ("buoy online, mesh reachable / mesh unreachable").

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
| `vessel_id` | yes | Device-local stable id (≤ 32 chars). This is the phone's identity the buoy maps into a `SRC_ID`. |
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
| `accepted` | The buoy accepted the SOS into its store-and-forward queue. |
| `buoy_id` | External id of the buoy (matches `RELAY_ID` on LoRa). |
| `src_id` | External id the buoy assigned to this vessel session. |
| `seq` | The LoRa frame `SEQ` the buoy will transmit this SOS with. |
| `server_ts` | Buoy epoch seconds. |

Errors: `400` for a malformed body, `503` if the buoy cannot accept (queue
full). The phone treats a `200` as delivery state `relayed`; a network error
keeps the message `saved` (`docs/06_DELIVERY_STATES.md`).

### `GET /v1/status` — buoy health

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

`mesh` is `"ok"` if the buoy recently heard another radio endpoint, otherwise
`"degraded"`. `queued` is the number of SOS messages still waiting to be
forwarded on LoRa. The app uses this for the honest signal meter.

### `GET /v1/warnings` — active weather warnings & advisories

Offline handsets poll this endpoint when connected to buoy WiFi to retrieve
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
| `advisories` | Array of active, unexpired advisories currently cached on the buoy. |
| `id` | Advisory identifier. |
| `title` | Short summary title. |
| `priority` | `"Emergency"`, `"Warning"`, `"Information"`, or `"Community"`. |
| `municipality` | Applicable area or `"All"`. |
| `description` | Full text instruction or warning description. |
| `source` | Authority (`"MDRRMO"`, `"LGU"`, `"AqOne Research"`). |
| `publish_date` | RFC 3339 timestamp or Philippine date string (`YYYY-MM-DD`). |
| `expiration_date` | RFC 3339 timestamp or Philippine date string. If absent, handset bounds retention to max 48h. |

Expired advisories are automatically pruned by the buoy cache and not returned.

## Phone-side rules

- Keep the SOS in a local **outbox** (SQLite) until a `200` changes its state
  to `relayed`. The outbox survives app restarts and is the single source of
  truth for the fisherman.
- One outstanding SOS per vessel at a time is recommended; a new SOS replaces
  or queues after the old one only with explicit user choice.
- If the buoy reports `mesh: degraded`, tell the user the message will wait on
  the buoy (state stays `relayed` until the mesh delivers).

## Buoy-side rules

- On `POST /v1/sos`, the buoy assigns `src_id` and `seq` and enqueues a signed
  LoRa `SOS` frame (`docs/02_LOAM_PACKET_SPEC.md`). The `vessel_id` maps to
  the 32-bit `src_id`; the buoy keeps that mapping in NVS.
- The buoy acks the phone only after the frame is in its store-and-forward
  queue (not after LoRa transmission — the phone cannot know about radio
  success, and we do not fake it).
- The buoy retransmits queued SOS frames per the relay rules until a mesh
  `ACK` arrives or the message expires (default 15 minutes).

## Example exchange

```
Phone  ──►  Buoy            POST /v1/sos  {v:1, vessel_id, boat, note, client_ts}
Phone  ◄──  Buoy            200 {"accepted":true,"buoy_id":1001,"src_id":1001,"seq":42,...}
Phone  ──►  Buoy            GET /v1/status
Phone  ◄──  Buoy            200 {"v":1,"buoy_id":1001,"batt":86,"mesh":"ok","queued":3}
```

## Versioning

Bump `v` on breaking changes. Update this doc first, then tell Daniel and the
mobile pair.
