# 19 — Heltec V3: Hybrid Data Flow to the Database

Practical wiring guide for the boat-pod, stationary-relay, and shore-gateway
firmware. Written against what the backend **actually implements today**, not
the older spec docs.

> ## ⚠️ Read this first — the spec docs are out of date
>
> `docs/04_INGEST_API.md` describes `POST /api/v1/ingest` with fields like
> `src_ext_id`, `relay_ext_id`, `ttl`, `hops`, `gateway_id`.
>
> **That endpoint does not exist.** It was never built. The backend implements
> **`POST /api/sos`** with a different, simpler shape.
>
> Build against this document. Treat `04_INGEST_API.md` as historical.

---

## The whole path in one picture

```
[1] Fisher's phone
     │  WiFi (phone joins the boat pod's access point)
     │  POST http://192.168.4.1/v1/sos
     ▼
[2] BOAT POD  (Heltec V3 — SoftAP + LoRa)
     │  Direct LoRa 915 MHz, binary frame
     ▼
[3] OPTIONAL SENSOR / RELAY BUOY(s)   (Heltec V3 — LoRa only)
     │  Fixed telemetry or TTL relay where needed
     ▼
[4] TALL SHORE GATEWAY  (Heltec V3 — LoRa + internet)
     │  HTTPS
     │  POST https://incredible-liberation-production-aad7.up.railway.app/api/sos
     ▼
[5] FastAPI → PostgreSQL → dashboard
```

The hybrid prototype is **one boat pod, one optional stationary node, and one
tall shore gateway**. Add stationary nodes only for fixed sensing, measured
coverage gaps, or redundancy.

---

## Each Heltec has one of four possible jobs

| Role | Radios in use | What it does |
|---|---|---|
| **Boat pod** | WiFi SoftAP + LoRa TX/RX | Hosts the phone's local WiFi, accepts an SOS over HTTP, queues it, and sends it toward shore |
| **Sensor buoy** | LoRa RX + TX | Reports fixed-position sensor data and can relay frames |
| **Relay buoy** | LoRa RX + TX | Receives a frame, checks it has not seen it before, decrements TTL, re-transmits |
| **Gateway** | LoRa RX + WiFi station | Receives frames, decodes them, POSTs JSON to the backend over the internet |

A single Heltec can perform the field-node roles, but **the gateway is the awkward one** — see the
radio constraint below.

---

## Step 1 — Phone to boat pod (WiFi)

The boat pod runs a WiFi access point. The phone joins it with its SIM in airplane
mode.

| Setting | Value |
|---|---|
| SSID | `Aquan` |
| Pod IP | `192.168.4.1` |
| Phone DHCP | Assigned by the ESP32 SoftAP |
| Protocol | Plain HTTP — no TLS. The hop is local; certificates on a pod are not worth the flash. |

### The boat pod must serve two routes

**`POST /v1/sos`** — the phone sends:

```json
{
  "v": 1,
  "vessel_id": "abc123",
  "boat": "Maria Gracia",
  "client_ts": 1754300000,
  "trust_tier": "self_declared",
  "lat": 11.6839,
  "lon": 122.4471,
  "note": "engine dead"
}
```

`lat`, `lon` and `note` may be absent. Everything else is always present.

The pod replies immediately — **do not wait for LoRa delivery**:

```json
{
  "accepted": true,
  "buoy_id": "BUOY01",
  "src_id": 65537,
  "seq": 42,
  "server_ts": 1754300001
}
```

The phone stores `seq` and `src_id` so it can match the SOS later.

**`GET /v1/status`** — buoy health. The app polls this to show "connected to
Buoy 01." Return battery, uptime, queue depth, last LoRa contact.

---

## Step 2 — Boat pod or relay buoy to shore (LoRa)

Full binary format is in `docs/02_LOAM_PACKET_SPEC.md`. The essentials:

```
byte 0      MAGIC 0xA5
byte 1      VERSION 0x01
...
byte 18     TTL          ← decrement on each relay
byte 19     HOPS         ← increment on each relay
byte 20-21  PAYLOAD_LEN  (0-64)
byte 22..   PAYLOAD      UTF-8 JSON
last 8      SIG          HMAC-SHA256 truncated to 8 bytes
```

Max frame **94 bytes**. Frame types: `0x01` SOS, `0x02` ACK, `0x03` PING,
`0x04` STATUS.

**The 64-byte payload limit is the constraint that shapes everything.** It's why
the de-duplication key is `(vessel_id, client_ts)` and not a UUID — a UUID does
not fit.

### Direct and relay logic — keep it this simple

```
on frame received at a pod or stationary relay:
    if MAGIC != 0xA5 or VERSION != 0x01:  drop
    if signature invalid:                  drop
    if (SRC_ID, SEQ) already in seen-set:  drop     ← stops broadcast storms
    add (SRC_ID, SEQ) to seen-set
    if TTL == 0:                           drop
    TTL  = TTL - 1
    HOPS = HOPS + 1
    re-transmit toward shore when no direct delivery is available
```

The seen-set is the whole flood-control mechanism. A ring buffer of the last
~64 `(SRC_ID, SEQ)` pairs is plenty.

> **Coordinate with your teammate on frame types.** The chathub should use
> `0x05`, not `0x04` — `0x04` is already allocated to STATUS.

---

## Step 3 — Gateway to backend (HTTPS)

This is where the earlier docs will mislead you. **Use this:**

```
POST https://incredible-liberation-production-aad7.up.railway.app/api/sos
Content-Type: application/json
```

```json
{
  "vessel_id": "abc123",
  "client_ts": 1754300000,
  "boat": "Maria Gracia",
  "lat": 11.6839,
  "lon": 122.4471,
  "note": "engine dead",
  "trust_tier": "self_declared",
  "source": "buoy",
  "buoy_id": "BUOY01",
  "src_id": 65537,
  "seq": 42
}
```

### Field rules

| Field | Required | Notes |
|---|---|---|
| `vessel_id` | **yes** | From the frame payload |
| `client_ts` | **yes** | Origin epoch seconds — **not** the gateway's clock |
| `source` | **yes** | Must be exactly `"buoy"` for the current backend contract. This compatibility value covers a boat pod or stationary buoy radio endpoint. |
| `boat` | no | Defaults to empty |
| `lat` / `lon` | no | Omit entirely if no fix. **Do not send 0,0** — that is a real place in the Atlantic |
| `note` | no | ≤ 64 chars |
| `buoy_id`, `src_id`, `seq` | no | Send them; `buoy_id` is the retained compatibility field for the serving pod or stationary node, and these fields populate the radio trail on the dashboard |

### Three things that matter

**No authentication.** `POST /api/sos` is deliberately unauthenticated. A
gateway relaying a distress call cannot be asked for a bearer token.

**`client_ts` must be the phone's original timestamp**, carried through the LoRa
frame untouched. Together with `vessel_id` it is the de-duplication key. If the
gateway substitutes its own clock, the same emergency arriving by both the boat
pod path and the phone's direct internet path will create **two incidents** on
the dispatcher's screen.

**HTTP 200 means done.** It covers both "created" and "already recorded." Stop
retrying on 200. Retry on network failure or 5xx, with backoff.

---

## The radio and gateway constraint

The Heltec's WiFi is now deliberately local: a phone only needs to reach the
boat-mounted safety pod strapped to its own boat. The pod does not need WiFi
coverage over the water and does not use WiFi as its long-range backhaul.

The tall shoreline gateway is dedicated to LoRa plus its internet uplink. It
has no phone SoftAP. This avoids sharing the Heltec's single WiFi radio between
an access point and an upstream station, while putting the long-range antenna
where height actually helps.

Stationary navigational buoys are optional radio participants: they can report
fixed-position sensor data and, where a direct boat-to-shore path is weak, act
as relay nodes. A direct boat-pod frame uses `HOPS=0`; an optional relay applies
the existing TTL/seen-set rules.

---

## Power and store-and-forward

Boat pods and stationary nodes can brown out or lose power. Two rules:

**Persist the queue to flash**, not RAM. An SOS held in RAM dies with the
battery. Use NVS or SPIFFS.

**Never drop an SOS to save power.** Reduce PING frequency, dim the LED, sleep
longer between listens — but a queued distress frame retries until it is
acknowledged or the board dies.

---

## Build order — do not skip ahead

Each step must actually work before the next.

1. **Two Heltecs exchange any LoRa packet.** No protocol, no JSON. Just proof
   the radios talk at range.
2. **Add the frame format** — MAGIC, TTL, HMAC, seen-set. Verify a relay
   forwards once and only once.
3. **Gateway POSTs a hardcoded SOS** to `/api/sos`. Watch it appear on the
   dashboard. *This proves the whole backend half without any phone involved.*
4. **Boat pod serves `POST /v1/sos`** over SoftAP. Test with `curl` from a
   laptop joined to the pod's WiFi, before involving the Flutter app.
5. **Phone in airplane mode → boat pod → direct LoRa → gateway → dashboard.**
   The primary demo path.
6. **Add one stationary relay buoy** and prove TTL/seen-set forwarding only
   after the direct path works.
7. **Outdoor range test.** Record actual metres in
   `docs/08_DEMO_AND_STATUS.md` — this is still an open item and you currently
   have no measured figure.

**Step 3 is the highest-value early win.** A gateway posting a fake SOS proves
the entire cloud path is live, and it needs no LoRa, no phone and no mesh.

---

## Testing without hardware

You can exercise the backend half right now:

```bash
curl -X POST https://incredible-liberation-production-aad7.up.railway.app/api/sos \
  -H "Content-Type: application/json" \
  -d '{"vessel_id":"TEST-01","client_ts":1754300000,"boat":"Test Banca",
       "lat":11.6839,"lon":122.4471,"note":"firmware test",
       "source":"buoy","buoy_id":"BUOY01","seq":1}'
```

It should appear on the dashboard map within 10 seconds as a pulsing red marker.
Send it twice with the same `client_ts` — you should still see **one** incident.
That is the de-duplication working.
