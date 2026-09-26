# 02 — LoAM Packet Spec (LoRa binary frame)

The radio contract between boat pods, stationary sensor-relay buoys, and the
shore gateway. The firmware owner is Daniel and the gateway owner is Arnold.
Any packet that does not parse and verify is dropped; there is no negotiation.

## Scope

This doc defines the wire format for every LoRa frame in the hybrid network:
SOS, mesh ACK, ping, the pod check-in (`STATUS`), sensor telemetry, and
downlink advisories, and the two radio channels they use. It does
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
| 20 | 2 | `PAYLOAD_LEN` | `N`, the payload byte count (0-225). |
| 22 | N | `PAYLOAD` | Type-specific payload: JSON, except `STATUS`, which is binary. |
| 22+N | 8 | `SIG` | HMAC-SHA256 truncated to 8 bytes. |

Max frame size = 22 + 225 + 8 = **255 bytes**, the SX1262's packet ceiling
(`LOAM_MAX_PAYLOAD` in `AqOneLoam.h`).
Corrected 2026-09-26: this doc said 64 and 94 bytes, but the firmware has
always enforced 225 and 255, and a real SOS frame is about 170 to 255 bytes.

## Node roles

- **Boat pod:** Originates SOS and optional boat telemetry, then sends directly
  to the shore gateway whenever possible.
- **Stationary sensor buoy:** Provides fixed-location telemetry and may relay
  frames when a direct boat-to-gateway path is unavailable.
- **Relay buoy:** Forwards new frames using TTL flooding and the seen-set.
- **Shore gateway:** Receives and acknowledges frames, forwards accepted events
  to the backend, and sends downlink warnings or responder updates.
- **Shore check-in receiver** (approved 2026-09-26, not built): listens only on
  the check-in channel, never transmits, and uploads check-ins in batches
  (`docs/04`, "Pod check-ins"). Design: `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md`.

Direct boat-pod frames use `HOPS = 0`. Relay buoys mutate `RELAY_ID`, decrement
`TTL`, and increment `HOPS` without re-signing the origin frame.

## Frame types (`TYPE`)

| Value | Name | Payload |
|---|---|---|
| `0x01` | `SOS` | Distress report (schema below). Highest radio priority. |
| `0x02` | `ACK` | Mesh-level ack for a previous frame. |
| `0x03` | `PING` | Shore beacon: presence, clock, fleet tier (schema below). |
| `0x04` | `STATUS` | Pod check-in, binary (schema below). Lowest priority. |
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
The one exception is `STATUS`, a fixed binary layout whose first byte carries
its version, because every pod sends it every 2 to 14 minutes and airtime is
the binding constraint (`docs/68` D4).

### SOS (`0x01`)

```json
{
  "v": 1,
  "vid": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
  "ts": 1790000000,
  "bid": "BUOY01",
  "sq": 7,
  "tt": "self_declared",
  "lat": 11.6050,
  "lon": 122.3125,
  "boat": "BG-123",
  "n": "engine down"
}
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `vid` | yes | Vessel id, always 32 chars. With `ts` it forms the backend's de-duplication key. |
| `ts` | yes | `client_ts`, the handset's own send time. |
| `bid` | yes | Id of the buoy that queued this call. |
| `sq` | yes | The queuing buoy's SOS counter — the value it returned to the handset from `POST /v1/sos`, persisted in NVS so it survives a reboot. **This is the handset's matching key**: a LoRa frame has no room for a `local_id`, so when the dispatcher's answer comes back down the app pairs it to the right outbox record by this number alone. Not to be confused with the frame header's `SEQ`, which rotates on every retransmission by design. |
| `tt` | no | Trust tier; defaults to `self_declared`. |
| `lat` / `lon` | no | Decimal degrees; omit if the phone has no fix. Never sent as `0,0` — that is a real position in the Gulf of Guinea. |
| `boat` | no | Display name, ≤ 32 chars. **Sheds first** when the payload will not fit: the backend already has it from registration and looks it up by `vid`. |
| `n` | no | ≤ 64 chars free text. **Sheds last** — the fisher's note exists nowhere else. |

There is deliberately no `kind`: `TYPE 0x01` in the authenticated header
already says what this is, and in the tightest payload in the system those 13
bytes are better spent on `sq`.

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

Sent by the shore gateway every 60 s on the SOS channel.

```json
{ "v": 1, "now": 1790000000, "ms": 250, "net": true, "ct": 2, "cx": 1790000600 }
```

| Field | Required | Notes |
|---|---|---|
| `v` | yes | `1` |
| `now` | no | Shore clock, epoch seconds UTC, at the start of transmission. Absent until the shore has a valid clock. |
| `ms` | no | Milliseconds (0-999) to add to `now`. A receiver sets its clock to `now + ms` plus the frame's time-on-air at receive-complete, which holds pods within the 100 ms slot tolerance (`docs/68` REQ-029). Approved 2026-09-26, not built. |
| `net` | no | `true` while the shore has an uplink. |
| `ct` | no | Fleet check-in tier: `0` normal, `1` elevated, `2` severe (`docs/68`). Absent when the shore has no current tier. Approved 2026-09-26, not built. |
| `cx` | with `ct` | Epoch seconds after which `ct` must be ignored. A pod with no valid `ct` uses normal. |

### STATUS (`0x04`) - pod check-in

Approved 2026-09-26, not built (`docs/68_WEATHER_TIERED_CHECKINS_SPEC.md`).
Replaces an earlier JSON body that no firmware ever sent.

Binary payload, exactly 15 bytes, big-endian:

| Offset | Size | Field | Meaning |
|---|---|---|---|
| 0 | 1 | `VER_FLAGS` | High nibble: payload version, `1`. Low nibble: bit 0 `HAS_FIX`; bits 1-3 zero. |
| 1 | 4 | `LAT_E5` | Latitude x 100000 as a signed int32; `0` when `HAS_FIX` is clear. |
| 5 | 4 | `LON_E5` | Longitude x 100000 as a signed int32; `0` when `HAS_FIX` is clear. |
| 9 | 2 | `FIX_AGE_S` | Seconds since the fix was taken; `65535` when unknown or older. |
| 11 | 1 | `BATT` | Battery percent 0-100; `255` when unknown. |
| 12 | 1 | `TIER` | The tier the pod is using: `0` normal, `1` elevated, `2` severe. |
| 13 | 2 | `STAGNANT_MIN` | Reserved for `docs/67` stagnant mode: minutes left, `0` for none. Sent as `0` until plan 67 defines it. |

- The frame header's `SRC_ID` identifies the pod and `SEQ` is its check-in counter; receivers deduplicate on `(SRC_ID, SEQ)`.
- `FLAGS` is `SIGNED` only. A check-in never sets `WANTS_ACK` and is never acknowledged.
- On the check-in channel `TTL` and `HOPS` are `0` and nothing relays it.
  A pod out of direct range sends it on the SOS channel with `TTL = 2` instead (see "Check-in channel and slots").
- Frame size is 22 + 15 + 8 = **45 bytes**, about 0.54 s at SF10.
- Worked example with a test key: `fixtures/loam/checkin_v1.json`.

```
A5 01 04 01 A1 B2 C3 D4 A1 B2 C3 D4 01 2C 6A B1 3B 80 00 00 00 0F
11 00 11 B5 34 00 BA A2 52 00 0C 56 02 00 00
3C 63 F5 D2 57 71 F9 FF
```

Pod `0xA1B2C3D4`, `SEQ` 300, `TS` 1790000000, fix 11.60500, 122.31250 taken
12 s ago, battery 86%, tier severe, not stagnant; the last line is the `SIG`
under the fixture's test key.

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
| `rev` | no | Revision timestamp epoch seconds (UTC), derived from advisory `updated_at` (default 0). Newer revision replaces older; a frame whose `rev` is not newer is ignored by receiving buoys and cannot resurrect a cancelled warning. |
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
The transmit ring buffer reserves capacity for distress traffic via the `reserve` parameter in `txEnqueue`.
`STATUS` check-ins are the lowest priority of all: a pod skips its check-in slot while any `SOS`, `ACK`, `ETA` or `CHAT` frame of its own is waiting, never holds more than one check-in in the ring, and never catches up on a skipped slot (approved 2026-09-26, not built).
`CHAT` frames require more than 2 free ring slots.
Distress (`SOS`), `ACK`, and `WARN` frames may use any free slot so they are never starved by routine chat traffic.

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

Today every board shares one key, `LOAM_KEY` in the gitignored `AqOneSecrets.h`; per-device keys arrive with `docs/66` Phase 5 (C11).

- All endpoints must have a registered external id and key before they enter
  the mesh.
- Development builds may share one key; production deploys per-device keys.
- Key distribution is out of scope for this doc (provisioned at first setup,
  matching `docs/04_INGEST_API.md` device registry).

## Radio parameters

Deployment configuration, not part of the frame. Firmware and gateway must
agree or packets never decode.

| Parameter | SOS channel | Check-in channel (approved 2026-09-26, not built) |
|---|---|---|
| Modulation | LoRa | LoRa |
| Frequency | `LORA_FREQ_MHZ` = 915.0 MHz | `LORA_CHECKIN_FREQ_MHZ` = 917.0 MHz |
| SF | 10 | 10 |
| Bandwidth | 125 kHz | 125 kHz |
| Coding rate | 4/5 | 4/5 |
| Sync word | `0x34` (private) | `0x34` (private) |
| TX power | +22 dBm | +22 dBm |
| Preamble | 8 symbols | 8 symbols |
| Header | Explicit | Explicit |
| CRC | Enabled (SX1262) | Enabled (SX1262) |

Corrected 2026-09-26: this table said 433.0 MHz and SF7; the firmware ships
915.0 MHz to match the antennas bought, and SF10 per
`docs/33_LORA_RF_BUDGET.md`. The band is still subject to the NTC answer
(`docs/62D` M11); if it moves, both channels move together and stay at least
1 MHz apart inside the permitted band.

## Check-in channel and slots

Approved 2026-09-26, not built (`docs/68` D9, D10, REQ-008, REQ-012, REQ-029).

- **Who uses it.** Only `STATUS` check-ins from pods that hear the shore
  `PING` directly (`HOPS = 0`) and have had a `PING` clock in the last 10 min.
  Only the check-in receiver listens on it.
- **Cycle.** 120 s, aligned to UTC: a cycle starts whenever `epoch mod 120 = 0`.
- **Slots.** 80 slots of 1.5 s; slot `k` (0-79) starts `k x 1.5 s` into the
  cycle. Every pod has a unique slot, assigned at enrolment (`docs/04`,
  "Pod check-ins").
- **When a pod sends.** At the start of its slot, in the cycles where
  `floor(epoch / 120) mod (interval / 120) = 0`, with `interval` 840 s
  (normal), 240 s (elevated) or 120 s (severe). A pod inside a harbor zone
  uses 840 s whatever the tier.
- **Channel switch.** The pod retunes to `LORA_CHECKIN_FREQ_MHZ` for its
  own check-in only and returns to the SOS channel as soon as the frame is
  sent.
- **Fallback.** A pod that hears `PING` only through a relay, or has had no
  `PING` clock for 10 min, sends its check-in on the SOS channel every 840 s
  at a random offset, with `TTL = 2`; relays forward it under the normal
  relay rules, so it travels at most 2 hops.


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
- `PAYLOAD_LEN` > 225, or a JSON payload fails to parse, or a `STATUS` payload is not exactly 15 bytes or its version nibble is not `1`
- `TTL` is 0 on arrival at a relay, or `HOPS` > 15
- signature verification fails when `FLAGS.SIGNED` is set

## Worked example

A signed SOS from external id `0x00010001`, seq 42, TTL 5. The payload bytes
below are a short illustrative string, chosen to keep the hex readable — not
the current SOS field set above; this example is about the frame layout:

```
A5 01 01 03 00 01 00 01 00 01 00 01 00 2A 00 00 00 00 05 00 00 22
7B 22 76 22 3A 31 2C 22 6B 69 6E 64 22 3A 22 73 6F 73 22 2C 22 62
6F 61 74 22 3A 22 42 47 2D 31 32 33 22 7D
<8-byte SIG>
```

## Edge-case remediation contract

Frozen by `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Phase 0 (Section 3.9).
Phase 0 reserves field names and fixes the text rule only.
**Firmware status (2026-09-25): not built.** `nc`, `rc` and the byte-safe UTF-8 copy land with Track F phase F1 (`docs/62D_EDGE_FIRMWARE_TRACK.md`), gated on build step 2.
The backend and handset already truncate on character boundaries (PR #79).
Relay, clock, node-ID and key rules are written by Track F's own contract step (docs/62D Phase F0) when that track opens.

### E2.1 Reserved payload fields (Track F phase F1)

| Field | Payloads | Type | Meaning |
| --- | --- | --- | --- |
| `nc` | SOS (`0x01`) and ETA (`0x06`, `T_ETA` in firmware) | uint32 | The phone's incident nonce (`docs/03` E3.1, `docs/04` E4.1). |
| `rc` | ETA (`0x06`) only | small int | The resolution code, numbered in the order of `docs/05` E5.1 starting at 1. |

`rc` values:

| `rc` | `resolution_code` |
| --- | --- |
| absent | open (not resolved) |
| 1 | `rescued` |
| 2 | `safe_confirmed` |
| 3 | `stood_down_by_fisher` |
| 4 | `duplicate` |
| 5 | `closed_unconfirmed` |
| 6 | `unspecified` |

Receivers ignore unknown payload keys, so frames without `nc` or `rc` stay valid.
Both are payload additions, so they bump the payload `v` only when F1 makes them required (see "Versioning" below).

### E2.2 UTF-8 text rule (Track F phase F1, EC-C8, EC-L7)

- All text in every payload (`boat`, `n`, chat text, `ttl`, `txt`, responder notes) is UTF-8.
- Any length limit is in bytes, and text is cut only on a character boundary, never inside a multi-byte sequence.
- A receiver that still meets invalid UTF-8 replaces the bad bytes rather than dropping the frame or the connection.

## Versioning

Bump `VERSION` on any breaking change. Non-breaking payload additions bump the
payload `v`. Update this doc first, then tell the affected owners
(`docs/00_START_HERE.md` contract table).
