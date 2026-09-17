# AqOne firmware — Heltec WiFi LoRa 32 V3

**Two sketches, one per kind of board.** Nothing to configure to pick a role —
open the folder that matches the board in front of you.

| Sketch | Flash it to | Radios |
|---|---|---|
| [`buoy/AqOneBuoy/`](buoy/AqOneBuoy/) | The boards that float | WiFi **AP only** + LoRa |
| [`shore/AqOneShore/`](shore/AqOneShore/) | The board on the mast with the internet | LoRa + WiFi **station only** |

```
phone --WiFi--> BUOY --LoRa--> (relay buoys) --LoRa--> SHORE --HTTPS--> backend
phone <--WiFi-- BUOY <--LoRa-- (relay buoys) <--LoRa-- SHORE <--HTTPS-- backend
```

**Buoy** — hosts the phones' network, accepts SOS and chat over HTTP/WebSocket,
puts them on the radio, plays back what the mesh sends down, and relays other
buoys' frames. **No internet of its own.** If the radio is quiet, an SOS sits in
flash until it is not — never silently dropped, never reported as sent.

**Shore** — hears the mesh, posts to the backend, polls the backend, sends the
answers back down. **No access point**, which is `docs/19_HELTEC_DATA_FLOW.md`
option 1, "dedicate the gateway": a station-only board can never kick a fisher's
phone off a buoy by dragging its AP onto another channel. Gateways never
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
#define AQONE_NODE_NAME "BUOY01"      // BUOY01, BUOY02, ... / SHORE01
```

Buoys use `0x0001xxxx`, gateways `0x000000xx`. Two nodes sharing a `NODE_ID`
make the seen-set drop one of them as a duplicate — at the console that is
indistinguishable from a dead radio.

**Identical on every board — in `AqOneLoam.h`, both copies:**

```cpp
LORA_FREQ_MHZ  = 915.0
LORA_SF        = 10
LORA_BW_KHZ    = 125.0
LORA_CR        = 5
LORA_SYNC_WORD = 0x34
LOAM_KEY       = "aqone-dev-key-change-me"
```

**Buoy only:** `AP_SSID` is `Aquan` on **every** buoy — only the node name
differs. A shared SSID lets a phone roam between buoys as the boat moves;
`GET /v1/status` reports which buoy it is actually on. Putting the buoy id in
the SSID breaks roaming.

**Shore only:** `UPLINK_SSID`/`UPLINK_PASS`, `BACKEND_HOST` (already set to the
Railway deployment), and `OPS_TOKEN` **or** `OPS_EMAIL`/`OPS_PASSWORD` — see
"The acknowledgement path needs a credential" below.

### Why the buoy network is open

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

### `build_opt.h` is part of the BUOY sketch — do not delete it

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

Each sketch folder is a self-contained `src/`. A minimal project per board:

```ini
[env:buoy]
platform = espressif32
board = heltec_wifi_lora_32_V3
framework = arduino
build_flags = -DWEBSOCKETS_SERVER_CLIENT_MAX=10
lib_deps =
  bblanchon/ArduinoJson@^7.0.0
  links2004/WebSockets@^2.4.1
  adafruit/Adafruit SSD1306@^2.5.9
  adafruit/Adafruit GFX Library@^1.11.9
  jgromes/RadioLib@^7.0.0
```

Drop `links2004/WebSockets` and the `build_flags` line for the shore env.

Last verified: both sketches compile clean on 2026-09-12 — buoy 866 KB flash /
59 KB RAM, shore 984 KB / 51 KB. **Compiling is not the same as working on the
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

## What the buoy exposes to phones (`192.168.4.1`)

Unchanged from the WiFi-gateway build — **the Flutter app needs no changes.**

| Route | Purpose |
|---|---|
| `POST /v1/sos` | Accept an SOS. Replies immediately, transmits in the background. A duplicate `(vessel_id, client_ts)` returns the original ack rather than queuing twice. |
| `GET /v1/sos/status?vessel_id=` | The dispatcher's ETA once it arrives over the mesh. Same shape as the backend's `GET /api/sos/vessel/{id}`, so the app parses both with one parser. |
| `GET /v1/status` | Buoy health, queue depth, **mesh** state, last RSSI/SNR. |
| `GET /history` | Chat backfill — `{"messages":[{"from","text","time"}]}`, last 20 lines, RAM only. |
| `ws://192.168.4.1:81` | Chat WebSocket. Relayed to every phone **except** the sender, and onto the radio. Pushes `sos_update` when an ETA lands. |
| `GET /portal` | Captive-portal page showing whether the radio link to shore is up. |
| `/generate_204`, `/ncsi.txt`, `/hotspot-detect.html` | OS connectivity probes. |

`uplink` in `GET /v1/status` reports the **mesh**, not an internet connection
this board does not have: `true` means a frame handed to this buoy has a live
path to shore right now. That is the question the app's copy actually asks, and
`docs/06_DELIVERY_STATES.md` requires the buoy to report mesh ok/degraded rather
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
| `POST /api/sos` | On every SOS frame received | none, by design |
| `POST /api/mesh/chat` | On every chat frame received, tagged `origin: "mesh"` | none |
| `GET /api/mesh/chat?since_id=` | Every 20 s | none |
| `GET /api/sos/active` | Every 45 s | **bearer required** |
| `POST /api/login` | Once, if `OPS_EMAIL`/`OPS_PASSWORD` are set | — |

### The acknowledgement path needs a credential

`GET /api/sos/vessel/{id}` — what the old firmware polled — is behind
`require_vessel_device` and derives ownership from the handset's own paired
credential. **A gateway does not have one and cannot obtain one.** So the shore
reads `GET /api/sos/active` instead, which needs an operator bearer: set
`OPS_TOKEN`, or `OPS_EMAIL`/`OPS_PASSWORD` and let it log in and refresh on 401.

With neither set, **SOS still flows up and chat still flows both ways** — only
the dispatcher's ETA cannot come back down, and the buoys' `GET /v1/status`
reports `shore_seen` honestly rather than the app waiting forever for an answer
that is not coming.

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

**2. Flash both boards.** Buoy sketch to one, shore sketch to the other. Watch
Serial at 115200. On each you want:

```
[lora] up  915.0 MHz  SF10  BW125  CR4/5  id=0x00010001
```

Then on the buoy:

```
[wifi] OPEN AP 'Aquan' up on 192.168.4.1 ch=6 max=10
[boot] buoy ready. 0 SOS recovered from flash
```

**3. Prove the radios talk, on the bench, a metre apart.** The shore beacons
every 60 s; within a minute the buoy's OLED should change from `Mesh: no shore`
to `Mesh: to shore`, and Serial should show `[lora] rx type=0x03`. If this never
happens, nothing below will work: run the `diff` on the two `AqOneLoam.h` copies
and re-check the band before touching anything else.

**4. Post an SOS from a laptop** joined to the buoy's AP — no phone app needed:

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

**No range has been measured.** The firmware implements the mesh; nobody has put
it on the water. `docs/33` models SF10 at ~7.5 km buoy-to-buoy against a 10.1 km
horizon at 1.5 m antenna height, and explicitly warns that free-space numbers
are ~5× too optimistic. Do not quote a range until step 8 is done.

**The HMAC key is shared and checked into git.** Until `LOAM_KEY` is changed,
anyone with this repo can inject a distress call into your mesh. Per-device keys
by `SRC_ID` are what the spec calls for in production.

**TLS certificates are not verified** on the shore gateway.
`client.setInsecure()` skips validation — there is no cert store on the board and
no way to rotate one on a mast. Acceptable for a prototype; a production gateway
pins a CA. Say so if asked rather than letting it be discovered.

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
