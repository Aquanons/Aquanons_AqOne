# AqOne firmware — Heltec WiFi LoRa 32 V3

**Two sketches, one per kind of board.** The field sketch is used in the
strap-on boat safety pod and can also serve as the basis for a stationary relay
buoy. Nothing to configure to pick a role — open the folder that matches the
board in front of you.

| Sketch | Flash it to | Radios |
|---|---|---|
| [`buoy/AqOneBuoy/`](buoy/AqOneBuoy/) | Boat safety pod or optional stationary relay buoy | WiFi **AP only** + LoRa |
| [`shore/AqOneShore/`](shore/AqOneShore/) | The board on the mast with the internet | LoRa + WiFi **station only** |

```
phone --WiFi--> BOAT POD --direct LoRa--> SHORE --HTTPS--> backend
                         \--optional relay--> STATIONARY BUOY --LoRa--/
phone <--WiFi-- BOAT POD <--LoRa-- SHORE <--HTTPS-- backend
```

**Boat pod** — hosts the phone's local network, accepts SOS and chat over
HTTP/WebSocket, puts them on the radio, and stores them in flash until a direct
or relayed shore path is available. **No internet of its own.** A stationary
field node can use the same LoRa role for fixed sensor telemetry and optional
relay forwarding.

**Shore** — hears the mesh, posts to the backend, polls the backend, sends the
answers back down. **No access point**, which is `docs/19_HELTEC_DATA_FLOW.md`
option 1, "dedicate the gateway": a station-only board can never kick a fisher's
phone off a pod by dragging its AP onto another channel. Gateways never
re-transmit mesh frames.

## The shared header

Both sketches include `AqOneLoam.h` — the frame format, HMAC signing, seen-set,
TX ring, SX1262 driver, clock and OLED bring-up. The Arduino IDE only compiles
files inside the sketch folder, so **the file exists in both folders and the two
copies are maintained by hand**:

```
firmware/buoy/AqOneBuoy/AqOneLoam.h
firmware/shore/AqOneShore/AqOneLoam.h
```

Drift between them is the single most expensive mistake available here. Two
boards with different radio settings or a different frame layout behave
**exactly** like two boards out of range: no error, no log line, nothing
arrives. You will spend an afternoon on antennas.

After editing either copy:

```bash
diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
```

It must print nothing. `LOAM_VERSION` in the header is the runtime backstop —
bump it on any wire-format change and mismatched nodes drop each other's frames
loudly instead of half-decoding them.

## Configure before flashing

**Per board — the top of each `.ino`:**

```cpp
#define AQONE_NODE_ID   0x00010001    // MUST be unique across the deployment
#define AQONE_NODE_NAME "POD01"       // POD01, RELAY01, ... / SHORE01
```

Field nodes use `0x0001xxxx`, gateways `0x000000xx`. Two nodes sharing a `NODE_ID`
make the seen-set drop one of them as a duplicate — at the console that is
indistinguishable from a dead radio.

**Identical on every board — in `AqOneLoam.h`, both copies:**

```cpp
LORA_FREQ_MHZ  = 915.0
LORA_SF        = 10
LORA_BW_KHZ    = 125.0
LORA_CR        = 5
LORA_SYNC_WORD = 0x34
```

**Credentials and secrets - in gitignored `AqOneSecrets.h`:**

Secrets are moved out of sketch sources.
Each sketch directory contains an `AqOneSecrets.h.example` template:
- `firmware/buoy/AqOneBuoy/AqOneSecrets.h.example`: copy to `AqOneSecrets.h` and configure `LOAM_KEY`.
- `firmware/shore/AqOneShore/AqOneSecrets.h.example`: copy to `AqOneSecrets.h` and configure `UPLINK_SSID`, `UPLINK_PASS`, `GATEWAY_API_KEY`, and `LOAM_KEY`.

`AqOneLoam.h` includes `"AqOneSecrets.h"` directly and checks at compile time that the header is present, that `LOAM_KEY` is at least 16 characters, and that neither the old default key nor the example placeholder is used.
The example does not build until `LOAM_KEY` is replaced with a real random secret.
Existing local `AqOneSecrets.h` files must declare `static constexpr char LOAM_KEY[] = "...";` (switching from `const char*` to `constexpr char[]`) to satisfy the compile-time assertions.
**Never commit `AqOneSecrets.h`.**

**Gateway authorization rationale:**
`GATEWAY_API_KEY` in `AqOneSecrets.h` matches `GATEWAY_API_KEY` in the backend environment.
It unlocks only `/api/sos/downlink` (the gateway-only view of responder acknowledgements and ETAs to broadcast over LoRa).
It deliberately does not unlock `/api/sos/active`, which is operator-only and contains sensitive position, fisher notes, and vessel owner identities.
If `GATEWAY_API_KEY` is missing or invalid, SOS still flows up to the backend and chat flows both ways, but dispatcher ETAs will not downlink.

**Field sketch:** `AP_SSID` is `Aquan` on **every** boat pod - only the node name differs.
A shared SSID lets the phone use any participating pod without a new app configuration.
Stationary sensor-only nodes do not need to expose the phone API unless that is explicitly added later.

**Shore only:** `BACKEND_HOST` (`https://aqone-backend.onrender.com`), plus `UPLINK_SSID`, `UPLINK_PASS`, and `GATEWAY_API_KEY` configured in `AqOneSecrets.h`.

### Why the pod network is open

A person in distress cannot be asked for a WiFi password. This matches the
existing decision that fisherman identity is a device-local id with no login.

The trade-off is real and worth stating plainly if asked: anyone in range can
join and could send a spurious SOS. A dispatcher resolves that in seconds. The
opposite failure — a genuine SOS that never sends because someone did not know
the password — is not recoverable.

### The three things that will bite you

**1. The band.** `LORA_FREQ_MHZ` must match what your board and antenna were
built for. A 915 MHz whip fed 433 MHz radiates almost nothing and the link
silently does not exist. **The repo docs disagree:**
`docs/02_LOAM_PACKET_SPEC.md` says 433.0, while
`docs/19_HELTEC_DATA_FLOW.md` and the BOM in `docs/16_QA_DISCLOSURES.md` say
915. The header ships at **915.0** to match the antennas that were actually
bought. Check the sticker on your board before you trust a range test —
`docs/33_LORA_RF_BUDGET.md` still lists the band as an open item.

**2. Every node must agree** on frequency, SF, bandwidth, coding rate, sync word
**and the HMAC key**. That is what the `diff` above is for.

**3. Heltec V3 needs `setDio2AsRfSwitch(true)` and a 1.8 V TCXO voltage** passed
to `begin()`. The header does both. Omit either and the radio initialises
cleanly, reports no error, and transmits nothing anyone can hear.

## Arduino IDE setup

**Board:** Heltec WiFi LoRa 32(V3) — install "Heltec ESP32 Series Dev-boards"
via Boards Manager.

**Libraries** (Library Manager):

| Library | Author | Needed by |
|---|---|---|
| `RadioLib` (v7+) | Jan Gromeš | both |
| `ArduinoJson` (v7+) | Benoit Blanchon | both |
| `Adafruit GFX Library` | Adafruit | both |
| `Adafruit SSD1306` | Adafruit | both |
| `WebSockets` | Markus Sattler | buoy only |

`WiFi`, `WebServer`, `HTTPClient`, `Preferences`, `SPI`, `Wire`, `DNSServer` and
mbedTLS (the HMAC) ship with the ESP32 core.

Installing `Adafruit SSD1306` prompts to pull in `Adafruit BusIO` — accept it,
or the sketch fails to link.

### `build_opt.h` is part of the field sketch — do not delete it

It contains one line, `-DWEBSOCKETS_SERVER_CLIENT_MAX=10`. The WebSockets
library defaults that to 5 while the AP accepts 10 phones, so without it boats
6–10 associate, get the captive portal, and never reach chat.

It has to be a build flag rather than a `#define` in the `.ino`:
`WebSocketsServer` holds its client table by value in its header, so a value
visible only to the sketch would give the library's own `.cpp` a different
object layout — corruption, not a bigger table. The Arduino IDE passes this
file's contents to every compilation unit, which is what makes it safe.

The file is fed straight to the compiler as a response file, so it may contain
flags only — **no comments**. `AqOneBuoy.ino` `static_assert`s on the value, so
a build that misses the flag fails with an explanatory message instead of
silently capping at 5 boats.

The shore sketch has no access point and no WebSocket, so it needs no
`build_opt.h`.

### PlatformIO

The `firmware/platformio.ini` file configures both environments (`buoy` and `shore`).
A pre-script (`select_src_dir.py`) sets `PROJECT_SRC_DIR` dynamically from each environment's `custom_src_dir`, so plain `pio run` builds both environments with no `PLATFORMIO_SRC_DIR` environment variable needed:

```bash
pio run -d firmware                     # Build both envs (buoy and shore)
pio run -d firmware -e buoy             # Build buoy only
pio run -d firmware -e shore            # Build shore only
pio run -d firmware -e buoy -t upload   # Flash buoy to board
pio run -d firmware -e shore -t upload  # Flash shore to board
```

Last verified: both sketches compile clean on 2026-09-24 — field sketch 866 KB flash /
59 KB RAM (18.3% / 26.0%), shore 984 KB / 51 KB (15.6% / 29.8%). **Compiling is not the same as working on the
water** — see "Test it in this order".

### Forward declarations in `AqOneLoam.h` — keep them

Both the Arduino IDE and PlatformIO auto-generate a prototype for every function
in a `.ino` and splice the whole block in ahead of the *first* function
definition, which can be earlier in the file than the structs those prototypes
mention. The `struct LoamFrame;` block in the header is what keeps that
generated block compiling; without it the build fails with errors pointing at
comment lines. Add a function taking one of those types and its type needs to be
on that list.

## The radio protocol

`docs/02_LOAM_PACKET_SPEC.md` owns the frame format; `docs/33_LORA_RF_BUDGET.md`
owns the deployment parameters. The firmware implements the spec with these
**recorded deviations** — reconcile the docs before anyone else builds against
them:

| Deviation | Why |
|---|---|
| `PAYLOAD_LEN` cap raised 64 → 225 bytes | `vessel_id` is **always** 32 chars (`IdentityStore.generateVesselId` fills `maxVesselIdLength`) and is half the backend's de-duplication key, so it can never be dropped — 64 bytes cannot hold it alongside a boat name and a note. 225 is the ceiling, not a round number: the SX1262 carries 255 payload bytes, and 22 header + 225 + 8 signature is exactly that. The field is already 2 bytes wide, so the wire layout is unchanged — only the "drop if > 64" receive rule moves. |
| New `TYPE 0x05 CHAT` | Already reserved for chat by `docs/19_HELTEC_DATA_FLOW.md`. |
| New `TYPE 0x06 ETA` | The dispatcher's acknowledgement coming back down. The original type list had no frame for it at all. |
| SF10, not SF7 | `docs/33` supersedes the SF7 in the spec's radio table. |

Everything else is as specified: `0xA5` magic, big-endian header,
HMAC-SHA256-truncated-to-8 over the frame with the hop bytes zeroed, relays do
not re-sign, TTL flood with a 64-entry seen-set, gateways never re-transmit.

### Graceful degradation, not failure

A distress call with fields missing is still a rescue; a distress call that did
not fit is not. So a frame that will not fit sheds fields rather than failing —
and **the shedding order is a deliberate decision, not a convenience**:

| Frame | Sheds first | Sheds second | Never sheds |
|---|---|---|---|
| SOS `0x01` | boat name | note | `vessel_id`, `client_ts`, position |
| ETA `0x06` | dispatcher name (truncated to 16) | note (truncated to 40) | `eta_at`, `delivery_state`, status code |

The SOS order looks backwards and is not. The boat name is already in the
`vessels` table from registration and the backend looks it up by `vessel_id`
(`payload.boat or payload.vessel_id`, then COALESCEd on insert), so dropping it
costs the dispatcher nothing. The fisher's note exists nowhere else. "Taking
water" and "engine dead" send different boats.

The worst case is not hypothetical: `vessel_id` is always 32 chars, so an SOS
with a full 32-char boat name and a 64-char note is 255 bytes of JSON and
**will** shed its boat name. A typical one (`"Maria Gracia"`, `"engine dead"`)
is 182 bytes and sheds nothing.

The ETA payload also omits `kind` and `client_ts` — `TYPE 0x06` in the
authenticated header already says what the frame is, and `RemoteSos.fromJson`
never reads `client_ts`.

## What the boat pod exposes to phones (`192.168.4.1`)

Unchanged from the WiFi-gateway build — **the Flutter app needs no changes.**

| Route | Purpose |
|---|---|
| `POST /v1/sos` | Accept an SOS. Replies immediately, transmits in the background. A duplicate `(vessel_id, client_ts)` returns the original ack rather than queuing twice. |
| `GET /v1/sos/status?vessel_id=` | The dispatcher's ETA once it arrives over the mesh. Same shape as the backend's `GET /api/sos/vessel/{id}`, so the app parses both with one parser. |
| `GET /v1/status` | Pod health, queue depth, **LoRa** state, last RSSI/SNR. |
| `GET /history` | Chat backfill — `{"messages":[{"from","text","time"}]}`, last 20 lines, RAM only. |
| `ws://192.168.4.1:81` | Chat WebSocket. Relayed to every phone **except** the sender, and onto the radio. Pushes `sos_update` when an ETA lands. |
| `GET /portal` | Captive-portal page showing whether the radio link to shore is up. |
| `/generate_204`, `/ncsi.txt`, `/hotspot-detect.html` | OS connectivity probes. |

`uplink` in `GET /v1/status` reports the **LoRa path**, not an internet connection
this board does not have: `true` means a frame handed to this pod has a live
path to shore right now. That is the question the app's copy actually asks, and
`docs/06_DELIVERY_STATES.md` requires the pod to report mesh ok/degraded rather
than claiming anything was "sent".

### The connectivity probes are not optional

Android, iOS and Windows all fetch a known URL right after joining a network to
decide whether it has real internet. If that probe fails, Android marks the
network "no internet" and will keep routing over mobile data — or leave the
network entirely for something better. At sea that is fatal: the phone abandons
the only network that can carry its SOS.

The buoy answers 204 / `Microsoft NCSI` when the **mesh** is up and redirects to
`/portal` when it is not. It does not route packets to the internet and never
will, but it does carry a message to shore and back, which is what the probe is
standing in for. When the mesh is degraded the portal says so plainly rather
than the phone silently leaving.

## What the shore calls on the backend

| Call | When | Auth |
|---|---|---|
| `POST /api/sos` | On every SOS frame received | **`X-Api-Key: GATEWAY_API_KEY`** (authenticates buoy provenance & trust tier) |
| `POST /api/mesh/chat` | On every chat frame received, tagged `origin: "mesh"` | none |
| `GET /api/mesh/chat?since_id=` | Every 20 s | none |
| `GET /api/sos/downlink` | Every 45 s | **`X-Api-Key: GATEWAY_API_KEY`** |
| `POST /api/advisories/delivery` | On warning received & queued | **`X-Api-Key: GATEWAY_API_KEY`** |
| `GET /api/public/advisories` | Every 60 s | none |

### Gateway authentication

The shore gateway authenticates to the backend with `X-Api-Key: GATEWAY_API_KEY` configured in `AqOneSecrets.h` (matching `GATEWAY_API_KEY` on Render).

- SOS post provenance (`POST /api/sos`): providing `X-Api-Key` allows the backend to accept buoy provenance fields (`buoy_id`, `src_id`) and `self_declared` trust tier.
- Warning delivery confirmation (`POST /api/advisories/delivery`): requires `GATEWAY_API_KEY`.
- Responder downlink (`GET /api/sos/downlink`): requires `GATEWAY_API_KEY`.

### TLS verification and Root CA rotation

The shore gateway enforces TLS peer verification via `WiFiClientSecure::setCACert(...)` with embedded Root CAs (`BACKEND_CA_CERTS` in `AqOneShore.ino`):
- **GlobalSign ECC Root CA - R4** (valid through 2038-01-19) - Primary Root CA for Render (`aqone-backend.onrender.com` via Google Trust Services WE1 intermediate).
- **GTS Root R1** (valid through 2036-06-22) - Google Trust Services backup root.
- **ISRG Root X1** (valid through 2035-06-04) - Let's Encrypt backup root.

**Rotation procedure:**
If the backend certificate authority changes or approaches expiration:
1. Export the new Root CA in PEM format.
2. Update `BACKEND_CA_CERTS` in `firmware/shore/AqOneShore/AqOneShore.ino`.
3. Build and re-flash the shore gateway board.

### Chat does not echo

Chat off the mesh is stored with `origin: "mesh"`, and the downlink skips
anything carrying that tag. Without it, a line a fisher sent would be stored,
read back on the next poll, and rebroadcast to the boat it came from — arriving
on its own sender's screen a second time, minutes later.

## Test it in this order

Each step must actually work before the next. **Do not skip ahead** — a failure
at step 5 is unattributable if steps 1–4 were assumed.

**1. Backend path, no hardware.** Confirms the cloud half is alive:

```bash
curl -X POST https://incredible-liberation-production-aad7.up.railway.app/api/sos -H "Content-Type: application/json" -d '{"vessel_id":"TEST-01","client_ts":1754300000,"boat":"Test Banca","source":"buoy","buoy_id":"BUOY01","seq":1}'
```

Should appear on the dashboard within 10 seconds. As of 2026-09-10 the
deployment returned `404 Application not found` — if it still does, fix that
before blaming a radio.

**2. Flash both boards.** Field sketch to one, shore sketch to the other. Watch
Serial at 115200. On each you want:

```
[lora] up  915.0 MHz  SF10  BW125  CR4/5  id=0x00010001
```

Then on the boat pod:

```
[wifi] OPEN AP 'Aquan' up on 192.168.4.1 ch=6 max=10
[boot] buoy ready. 0 SOS recovered from flash
```

**3. Prove the radios talk, on the bench, a metre apart.** The shore beacons
every 60 s; within a minute the buoy's OLED should change from `Mesh: no shore`
to `Mesh: to shore`, and Serial should show `[lora] rx type=0x03`. If this never
happens, nothing below will work: run the `diff` on the two `AqOneLoam.h` copies
and re-check the band before touching anything else.

**4. Post an SOS from a laptop** joined to the pod's AP — no phone app needed:

```bash
curl -X POST http://192.168.4.1/v1/sos -H "Content-Type: application/json" -d '{"vessel_id":"BANCA-7","client_ts":1754300500,"boat":"Maria Gracia","lat":11.6839,"lon":122.4471,"note":"engine dead"}'
```

Expect `{"accepted":true,...}` instantly. Then on buoy Serial:

```
[sos] queued BANCA-7 seq=1 depth=1
[sos] tx BANCA-7 seq=1 frame=101 attempt=1
```

on shore Serial:

```
[lora] rx type=0x01 src=0x00010001 seq=101 hops=0 rssi=-42
[sos] POST BANCA-7 -> 200
```

back on buoy Serial:

```
[sos] delivered BANCA-7 seq=1 after 1 attempt(s)
```

and a pulsing red marker on the dashboard. **That last line is the one that
matters** — it means the shore confirmed the backend has it, not merely that a
frame was transmitted.

**5. Acknowledge on the dashboard** with an ETA. Within ~45 s the shore picks it
up, sends an ETA frame, and `GET /v1/sos/status?vessel_id=BANCA-7` on the buoy
returns it. Connected phones get a `sos_update` push without polling.

**6. Chat both ways.** Send from the app on buoy A: it should appear on phones
on buoy B (via LoRa) *and* in `GET /api/mesh/chat`. Post to
`POST /api/mesh/chat` with `origin: "app"` and it should appear on both buoys'
phones within ~20 s — and **not** come back a second time.

**7. Pull the shore board's power**, post an SOS, power-cycle the *buoy*,
restore the shore. The SOS should still be delivered — that is the
store-and-forward queue surviving a brown-out, which is the whole point.

**8. Outdoor range test.** Record actual metres in
`docs/08_DEMO_AND_STATUS.md`. This is still an open item and there is no
measured figure yet — every range number in `docs/33_LORA_RF_BUDGET.md` is
modelled.

## Known limitations — do not overstate these

**No range has been measured.** The firmware implements the direct and optional
relay paths; nobody has put it on the water. `docs/33` models SF10 at ~7.5 km
low-node-to-low-node against a 10.1 km
horizon at 1.5 m antenna height, and explicitly warns that free-space numbers
are ~5× too optimistic. Do not quote a range until step 8 is done.

**The HMAC key is shared across nodes.**
`LOAM_KEY` is stored in gitignored `AqOneSecrets.h` and guarded at compile time, but all nodes in a given mesh still share the same key.
Per-device keys by `SRC_ID` remain on the roadmap for full fleet rollout.

**TLS certificates are verified via embedded root CAs.**
The shore gateway uses `client.setCACert(BACKEND_CA_CERTS)` containing trusted root certificates:
1. `GTS Root R4` (Expires: 2036-06-22) - Primary root for Google Trust Services WE1 (Render)
2. `GlobalSign Root CA` (Expires: 2028-01-28) - Cross-sign backup for GTS Root R4
3. `GTS Root R1` (Expires: 2036-06-22) - Google Trust Services RSA root backup
4. `ISRG Root X1` (Expires: 2035-06-04) - Let's Encrypt Root backup
Rotate `BACKEND_CA_CERTS` in `AqOneShore.ino` before the GlobalSign Root CA expires in 2028 or whenever the backend deployment changes certificate authority chains.

**Transmitting is half-duplex and slow.** A full frame at SF10 is roughly a
second of airtime, during which the node hears nothing. The TX ring, the random
relay backoff and the one-SOS-per-tick sweep exist to keep a three-node flood
from talking over itself; a denser mesh needs measurement, not more nodes.

**The fisher's reply is not on the mesh.** `fisher_reply` is always `null` in
the buoy's `/v1/sos/status`. The acknowledgement travels down; the one-tap
answer back up does not yet.

**No `local_id`.** A LoRa frame has no room for a UUID, so SOS that arrive via
the mesh cannot be matched to the handset's outbox record by id — only by
`(vessel_id, client_ts)`, which is exactly why that is the de-duplication key.

**Chat history is RAM only, last 20 lines, 64 chars.** A reboot loses the
backlog. The database keeps the full record; the buoy is a relay, not an
archive. Timestamps come from the shore's clock over the radio — lines heard
before the first gateway frame are served without a `time`, and the app dates
those to when it received them rather than the buoy inventing a clock reading.

**Queue holds 12 SOS.** Beyond that `POST /v1/sos` returns 503. Raise
`MAX_QUEUE` if you expect more, watching NVS size.

**Shore state is thin.** The vessel watch list survives a reboot (NVS); the chat
cursor does not, so a restarted gateway skips whatever was said while it was
down rather than replaying it onto the radio.

**One relay hop is untested.** `MESH_TTL` is 4 and the relay logic is written,
but the 3-node build has no middle node to prove it with. Two boards prove the
link, not the mesh.
