# 02 — LoAM Packet Spec (LoRa binary frame)

The radio contract between boat pods, stationary sensor-relay buoys, and the
shore gateway. The firmware owner is Daniel and the gateway owner is Arnold.
Any packet that does not parse and verify is dropped; there is no negotiation.

## Scope

This doc defines the wire format for every LoRa frame in the hybrid network:
SOS, mesh ACK, ping, status, sensor telemetry, and downlink advisories. It does
**not** cover the phone↔boat pod WiFi hop
(`docs/03_PHONE_BUOY_WIFI.md`) or the gateway→backend hop
(`docs/04_INGEST_API.md`).

## Frame layout

All multi-byte integers are **big-endian**. Fixed header, variable payload,
trailing signature.

| Offset | Size | Field | Meaning |
|---|---|---|---|
| 0 | 1 | `MAGIC` | `0xA5`. First byte of every frame. |
| 1 | 1 | `VERSION` | Protocol version, `0x01`. |
| 2 | 1 | `TYPE` | Frame type (below). |
| 3 | 1 | `FLAGS` | Bit flags (below). |
| 4 | 4 | `SRC_ID` | Origin endpoint external id. |
| 8 | 4 | `RELAY_ID` | Endpoint that last relayed this frame. |
| 12 | 2 | `SEQ` | Origin sequence number, rolling counter. |
| 14 | 4 | `TS` | Origin epoch seconds, UTC. |
| 18 | 1 | `TTL` | Remaining hop budget. |
| 19 | 1 | `HOPS` | Hops taken so far. |
| 20 | 2 | `PAYLOAD_LEN` | `N`, the payload byte count (0–64). |
| 22 | N | `PAYLOAD` | Type-specific payload (JSON). |
| 22+N | 8 | `SIG` | HMAC-SHA256 truncated to 8 bytes. |

Max frame size = 22 + 64 + 8 = **94 bytes**, comfortably inside a LoRa packet
at the radio settings below.

## Node roles

- **Boat pod:** Originates SOS and optional boat telemetry, then sends directly
  to the shore gateway whenever possible.
- **Stationary sensor buoy:** Provides fixed-location telemetry and may relay
  frames when a direct boat-to-gateway path is unavailable.
- **Relay buoy:** Forwards new frames using TTL flooding and the seen-set.
- **Shore gateway:** Receives and acknowledges frames, forwards accepted events
  to the backend, and sends downlink warnings or responder updates.

Direct boat-pod frames use `HOPS = 0`. Relay buoys mutate `RELAY_ID`, decrement
`TTL`, and increment `HOPS` without re-signing the origin frame.

## Frame types (`TYPE`)

| Value | Name | Payload |
|---|---|---|
| `0x01` | `SOS` | Distress report (schema below). Highest radio priority. |
| `0x02` | `ACK` | Mesh-level ack for a previous frame. |
| `0x03` | `PING` | Presence / heartbeat. |
| `0x04` | `STATUS` | Non-SOS status update. |
| `0x05` | `CHAT` | Local mesh chat message. |
| `0x06` | `ETA` | Dispatcher acknowledgement and ETA downlink. |
| `0x07` | `WARN` | Weather warning / advisory downlink (schema below). Subordinate to SOS. |

## Flags (`FLAGS`)

| Bit | Mask | Meaning |
|---|---|---|
| 0 | `0x01` | `SIGNED` — `SIG` is valid; otherwise `SIG` is 8 zero bytes. |
| 1 | `0x02` | `WANTS_ACK` — sender wants a mesh `ACK` on receipt. |
| 2 | `0x04` | `ACK_FLAG` — this frame is an ack for `(SRC_ID, SEQ)`. |

## Payload schemas

Payloads are UTF-8 JSON with a `v` version field so a future revision can be
detected before parsing the rest.

### SOS (`0x01`)

```json
{
  "v": 1,
  "kind": "sos",
  "boat": "BG-123",
  "lat": 11.6050,
  "lon": 122.3125,
  "note": "engine down"
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `kind` | yes | `"sos"` |
| `boat` | yes | Display name, ≤ 32 chars. |
| `lat` / `lon` | no | Decimal degrees; omit if the phone has no fix. |
| `note` | no | ≤ 64 chars free text. |

### ACK (`0x02`)

```json
{
  "v": 1,
  "ok": true,
  "src": 1001,
  "seq": 42
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `ok` | yes | Received and accepted (`true`) or rejected (`false`). |
| `src` | yes | `SRC_ID` of the frame being acked. |
| `seq` | yes | `SEQ` of the frame being acked. |

### PING (`0x03`)

```json
{ "v": 1 }
```

### STATUS (`0x04`)

```json
{
  "v": 1,
  "kind": "status",
  "lat": 11.6050,
  "lon": 122.3125,
  "batt": 86
}
```

`batt` is battery percent 0–100.

### WARN (`0x07`)

```json
{
  "v": 1,
  "id": 101,
  "rev": 1,
  "src": "MDRRMO",
  "pr": "Warning",
  "area": "New Washington",
  "iss": 1789401600,
  "exp": 1789487999,
  "ttl": "Gale Warning",
  "txt": "Rough seas expected over eastern seaboard.",
  "sig_type": "official"
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `id` | yes | Integer advisory/warning identifier. |
| `rev` | no | Revision number (default `1`). Newer revision replaces older; older revision cannot resurrect a cancelled warning. |
| `src` | yes | Origin authority, e.g. `"MDRRMO"`, `"LGU"`, or `"AqOne Research"`. |
| `pr` | yes | Priority level: `"Emergency"`, `"Warning"`, `"Information"`, `"Community"`. |
| `area` | yes | Geographic applicability, e.g. `"All"`, `"New Washington"`. |
| `iss` | no | Issue timestamp epoch seconds (UTC). |
| `exp` | no | Expiry timestamp epoch seconds (UTC). If missing/zero, bounded retention policy applies (max 48h), never immortal. |
| `ttl` | no | Title string, truncated to ≤ 48 chars. |
| `txt` | no | Description text, truncated to ≤ 80 chars. |
| `sig_type` | no | `"official"` for MDRRMO/LGU authored notices, `"research"` for automated/uncalibrated models. |

### Radio priority rules

SOS distress traffic (`0x01`) has absolute priority over the LoRa channel.
Warning broadcasts (`0x07`), chat (`0x05`), and routine beacons (`0x03`) are
strictly subordinate: queued warning frames yield immediately if an SOS frame
is received or pending transmission. Warning retries/rebroadcasts are rate-limited
and must never saturate the radio channel.

## Signature scheme

- Algorithm: HMAC-SHA256, truncated to the first 8 bytes.
- Key: the **origin endpoint's** HMAC key, looked up by `SRC_ID` in a key
  registry on the gateway (external id → key). Relays do **not** re-sign; they
  forward the frame as-is.
- Signed region: the frame with relay-mutable bytes (RELAY_ID at offsets 8..11, and TTL/HOPS at offsets 18..19) neutralized to zeroes so relays may mutate them without invalidating the origin's signature. Compute HMAC over:

  ```
  frame[0..7] ++ { 0x00, 0x00, 0x00, 0x00 } ++ frame[12..17] ++ { 0x00, 0x00 } ++ frame[20 .. 21+N]
  ```

  i.e. `MAGIC`..`SRC_ID`, zeroed `RELAY_ID`, `SEQ`..`TS`, zeroed `TTL` and `HOPS`, and `PAYLOAD_LEN`..payload.
- If `FLAGS.SIGNED` is clear, `SIG` is all zeroes and the frame is accepted
  without verification (development mode only — gateways must log any unsigned
  packet they forward).

### Keys

- All endpoints must have a registered external id and key before they enter
  the mesh.
- Development builds may share one key; production deploys per-device keys.
- Key distribution is out of scope for this doc (provisioned at first setup,
  matching `docs/04_INGEST_API.md` device registry).

## Radio parameters

Deployment configuration, not part of the frame. Firmware and gateway must
agree or packets never decode.

| Parameter | Value |
|---|---|
| Modulation | LoRa |
| Frequency | 433.0 MHz (PH ISM band) — set per region |
| SF | 7 |
| Bandwidth | 125 kHz |
| Coding rate | 4/5 |
| Header | Explicit |
| CRC | Enabled (SX1262) |

## Relay rules

- On receive, a stationary relay buoy verifies `MAGIC`/`VERSION`, parses,
  checks the seen-set, and if new: stores it, decrements `TTL` by 1, increments
  `HOPS` by 1, and re-transmits **only if** `TTL > 0`.
- Duplicate `(SRC_ID, SEQ, TYPE)` frames are dropped (small recent seen-set).
- If `WANTS_ACK` is set and the receiving endpoint is the destination (the shore
  gateway for `SOS`), it sends an `ACK` back. Relay buoys may also ack to claim
  receipt; the ack travels the same flooding rules.
- Gateways never re-transmit; on receipt they verify the signature, then
  hand the frame to the ingest pipeline (`docs/04_INGEST_API.md`).

## Malformed frames

A receiver must drop, without forwarding, any frame where:

- `MAGIC` ≠ `0xA5` or `VERSION` ≠ `0x01`
- `TYPE` / `FLAGS` have unknown bits set
- `PAYLOAD_LEN` > 64 or payload fails JSON parse
- `TTL` is 0 on arrival at a relay, or `HOPS` > 15
- signature verification fails when `FLAGS.SIGNED` is set

## Worked example

A signed SOS from external id `0x00010001`, seq 42, TTL 5, payload
`{"v":1,"kind":"sos","boat":"BG-123"}` (34 bytes):

```
A5 01 01 03 00 01 00 01 00 01 00 01 00 2A 00 00 00 00 05 00 00 22
7B 22 76 22 3A 31 2C 22 6B 69 6E 64 22 3A 22 73 6F 73 22 2C 22 62
6F 61 74 22 3A 22 42 47 2D 31 32 33 22 7D
<8-byte SIG>
```

## Versioning

Bump `VERSION` on any breaking change. Non-breaking payload additions bump the
payload `v`. Update this doc first, then tell the affected owners
(`docs/00_START_HERE.md` contract table).
