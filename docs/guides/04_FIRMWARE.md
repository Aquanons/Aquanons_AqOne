# 04 — FIRMWARE (ESP32-S3 field node)

**Owner: Daniel. This is the critical path — the boat pod and fixed field nodes are the product.**

Toolchain: **Arduino IDE + RadioLib**. Read `01_CONTRACTS.md` §2 before
writing any packet code.

The current deployment decision is hybrid: use this field-node guidance for the
removable boat pod first, and retain stationary buoys only for fixed sensing or
measured relay gaps. The active topology is defined in
`docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`.

---

## Hardware

| Part | Notes |
|---|---|
| ESP32-S3 dev board | WiFi + BLE, plenty of RAM for this; used in the strap-on pod or an optional fixed node |
| SX1262 LoRa module | **Confirm your module's band before flashing** |
| MPU6050 | Optional for the demo — see sensor-bypass mode below |
| Push button | GPIO, triggers a test SOS. Essential for the demo. |
| LED | Status feedback. Essential for debugging in a hotel room. |

### Frequency band — confirm before anything else

Philippine ISM allocations include **433 MHz** and **915 MHz**. SX1262 modules
are band-specific; a 433 MHz module will not work at 915 MHz.

```cpp
#define LORA_FREQ_MHZ 433.0   // CONFIRM: must match your physical module
```

Put the measured band in the README. A judge may ask about regulatory
compliance, and "we confirmed it against NTC allocations" is a good answer.

### Radio parameters — same on every node or nothing talks

```cpp
#define LORA_FREQ_MHZ      433.0
#define LORA_BANDWIDTH_KHZ 125.0
#define LORA_SPREADING     9      // SF9: good range/airtime balance. SF7 = faster,
                                  // shorter. Raise to SF10-12 only if range fails.
#define LORA_CODING_RATE   7      // 4/7
#define LORA_SYNC_WORD     0x34
#define LORA_TX_POWER_DBM  17     // check local limits and module rating
#define LORA_PREAMBLE_LEN  8
```

**Every field node and the gateway must use identical values.** A mismatch is silent:
no error, just nothing received. If two nodes won't talk, check these first.

---

## Libraries (Arduino IDE → Library Manager)

- **RadioLib** (Jan Gromeš) — SX1262 driver
- **mbedtls** — bundled with the ESP32 core, provides HMAC-SHA256
- **Preferences** — bundled, for NVS storage of device ID and key
- **Adafruit MPU6050** + **Adafruit Unified Sensor** — only if using the IMU

---

## Pin map — fill in for your wiring, then keep it here

```cpp
// SX1262  <-> ESP32-S3   (adjust to your board, then DO NOT change silently)
#define PIN_LORA_NSS   10
#define PIN_LORA_DIO1  14
#define PIN_LORA_RST   12
#define PIN_LORA_BUSY  13
// SPI: SCK=12? MOSI=11, MISO=13 -- verify against your board's pinout

#define PIN_BUTTON      0   // boot button works fine
#define PIN_LED        48   // onboard RGB on many S3 boards
```

---

## Frame encoding — must match `01_CONTRACTS.md` §2 exactly

46 bytes, little-endian. Do not reorder fields.

```cpp
#include <string.h>
#include "mbedtls/md.h"

#define FRAME_LEN      46
#define FRAME_SIGNED   38     // bytes 0..37 are covered by the signature
#define SIG_LEN         8

struct __attribute__((packed)) Frame {
  uint8_t  ver;         // 0   : 1
  uint8_t  type;        // 1   : 1 = sos.manual
  uint8_t  flags;       // 2   : bits0-1 priority, bits2-4 ttl
  uint8_t  src[6];      // 3   : device id
  uint8_t  msg_id[16];  // 9   : ULID binary
  uint32_t ts;          // 25  : unix seconds
  int32_t  lat;         // 29  : degrees * 1e7
  int32_t  lon;         // 33  : degrees * 1e7
  uint8_t  battery;     // 37  : percent, 255 = unknown
  uint8_t  sig[8];      // 38  : truncated HMAC-SHA256
};
static_assert(sizeof(Frame) == FRAME_LEN, "frame must be 46 bytes");

inline uint8_t packFlags(uint8_t priority, uint8_t ttl) {
  return (uint8_t)((priority & 0x03) | ((ttl & 0x07) << 2));
}
inline uint8_t priorityOf(uint8_t flags) { return flags & 0x03; }
inline uint8_t ttlOf(uint8_t flags)      { return (flags >> 2) & 0x07; }

void signFrame(Frame *f, const uint8_t *key, size_t keyLen) {
  uint8_t full[32];
  const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, info, 1);
  mbedtls_md_hmac_starts(&ctx, key, keyLen);
  mbedtls_md_hmac_update(&ctx, (const uint8_t *)f, FRAME_SIGNED);
  mbedtls_md_hmac_finish(&ctx, full);
  mbedtls_md_free(&ctx);
  memcpy(f->sig, full, SIG_LEN);
}

bool verifyFrame(const Frame *f, const uint8_t *key, size_t keyLen) {
  Frame copy = *f;
  signFrame(&copy, key, keyLen);
  uint8_t diff = 0;                        // constant-time compare
  for (int i = 0; i < SIG_LEN; i++) diff |= copy.sig[i] ^ f->sig[i];
  return diff == 0;
}
```

Coordinates: `lat_int = (int32_t)lround(lat_degrees * 1e7)`.

---

## Identity and keys

Device ID and shared key live in **NVS (Preferences)**, never in source.
Committing a key to a public repo is fatal — see `07_SECURITY.md`.

```cpp
#include <Preferences.h>
Preferences prefs;

uint8_t  g_deviceId[6];
uint8_t  g_key[32];

void loadIdentity() {
  prefs.begin("aqone", true);
  size_t idLen  = prefs.getBytes("devid", g_deviceId, sizeof(g_deviceId));
  size_t keyLen = prefs.getBytes("devkey", g_key, sizeof(g_key));
  prefs.end();
  if (idLen != 6 || keyLen != 32) {
    Serial.println("NO IDENTITY - run the provisioning sketch first");
    // Blink the LED fast forever; do not transmit unsigned frames.
  }
}
```

Write a tiny separate `provision.ino` that stores the ID and key once per
device. Record each device in the backend `devices` table
(`scripts/provision_device.py`).

---

## Roles: field node vs gateway

Same firmware, one compile-time flag.

```cpp
#define ROLE_BUOY    1
#define ROLE_GATEWAY 2
#define NODE_ROLE ROLE_BUOY     // change per device before flashing
```

**Boat pod:** raises SoftAP, accepts a frame from the phone, signs/sends over
LoRa, stores queued frames, and sends its own SOS on button press. A stationary
relay buoy may use the same LoRa forwarding behavior without exposing the phone
SoftAP.

**Gateway:** listens on LoRa, verifies, converts the binary frame to the JSON
envelope (`01_CONTRACTS.md` §4), POSTs to `/api/ingest/mesh` over WiFi/internet
with the gateway secret header. Retries with backoff and queues on failure.

---

## Store and forward — non-negotiable for an SOS

If no path to a gateway exists right now, the message must not be lost.

```cpp
#define QUEUE_MAX 32

struct QueueEntry {
  Frame    frame;
  uint32_t nextAttemptMs;
  uint8_t  attempts;
  bool     used;
};
QueueEntry g_queue[QUEUE_MAX];

// Backoff: 2s, 4s, 8s, 16s, 32s, then every 60s.
// SOS (priority 0) NEVER expires from the queue.
// Lower priorities may be evicted when the queue is full.
```

Dedupe relays with a small ring buffer of recently seen `msg_id`s (32 entries
is plenty) so a message doesn't loop forever between field nodes.

---

## SoftAP for the phone

```cpp
#define AP_SSID_PREFIX "AqOne-Buoy-"     // + last 4 hex of device id
#define AP_PASSWORD    "aqone-demo-2026" // demo only; per-device in production
#define AP_PORT        8080
```

The phone POSTs the 46-byte frame as raw binary to the pod's local endpoint
`http://192.168.4.1:8080/tx`.
Respond `200` with the `msg_id` **only after** the frame is queued — that
response is what advances the app to `received_by_buoy`. Never ack before
queueing; a false ack on an SOS is the worst bug this system can have.

**Power note:** an always-on SoftAP is the dominant battery drain. For the demo
leave it always on. For the README, document the production design: LoRa
listening continuously, SoftAP raised on a schedule or on demand.

---

## Sensor-bypass mode — build this, you will need it

The team has already burnt one MPU6050. If the IMU dies an hour before judging,
the demo must still run.

```cpp
#define SENSOR_BYPASS 1   // 1 = ignore IMU, button sends a canned hazard/SOS
```

With bypass on, the button emits a fully valid signed frame with no sensor
involvement. **Say so out loud in the demo** — "sensing is bypassed here, the
mesh path is real" is a strong, honest statement.

---

## Sketch skeleton

```cpp
#include <RadioLib.h>
SX1262 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_RST, PIN_LORA_BUSY);

void setup() {
  Serial.begin(115200);
  loadIdentity();

  int st = radio.begin(LORA_FREQ_MHZ, LORA_BANDWIDTH_KHZ, LORA_SPREADING,
                       LORA_CODING_RATE, LORA_SYNC_WORD, LORA_TX_POWER_DBM,
                       LORA_PREAMBLE_LEN);
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("LoRa init failed: %d\n", st);
    while (true) { blinkError(); }
  }
  radio.setDio1Action(onLoRaPacket);
  radio.startReceive();

#if NODE_ROLE == ROLE_BUOY
  startSoftAP();
#else
  connectWiFiUplink();
#endif
  pinMode(PIN_BUTTON, INPUT_PULLUP);
}

void loop() {
  serviceQueue();        // retries with backoff
  handleButton();        // debounced -> buildSosFrame() -> enqueue()
  handleReceived();      // verify, dedupe, TTL--, relay or upload
  heartbeatLed();
}
```

---

## Bring-up order — do not skip steps

1. **Blink an LED.** Confirms toolchain, board, and USB.
2. **`radio.begin()` returns 0** on both boards. Wiring is correct.
3. **Raw string TX/RX** between two boards, 1 m apart. *This is Day 1's goal.*
4. **46-byte frame TX/RX**, verify signature on the receiver.
5. **Gateway POSTs to the backend**, real SOS row appears.
6. **Phone → SoftAP → LoRa → backend.**
7. **Range test outdoors.** Walk it. Write down the metres.

Do not attempt step 5 before step 3 works reliably. Most lost time in radio
projects comes from debugging three layers at once.

---

## Field notes

- **Test at the venue early.** A hotel is a hostile RF environment — concrete,
  WiFi, other teams' radios. Discover this on Day 1, not Day 3.
- **Antennas must be attached before transmitting.** Transmitting without one
  can damage the SX1262.
- **Bring spares of everything**, especially the IMU and one whole spare board.
- **Serial logs are your only debugger.** Log every TX, RX, signature result,
  and queue action with a timestamp.
- **Record the actual range you measure**, not the datasheet figure. "We
  measured 800 m over water at SF9" is a far better answer than "LoRa does
  10 km."
