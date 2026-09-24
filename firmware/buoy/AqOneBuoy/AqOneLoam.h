// AqOneLoam.h — the AqOne mesh radio layer, shared by both sketches.
//
// ===========================================================================
// THIS FILE EXISTS IN TWO PLACES AND THE TWO COPIES MUST BE IDENTICAL
//
//   firmware/buoy/AqOneBuoy/AqOneLoam.h
//   firmware/shore/AqOneShore/AqOneLoam.h
//
// The Arduino IDE only compiles files that sit inside the sketch folder, so a
// shared header cannot live in one place and be included from the other. The
// copies are therefore maintained by hand, and drift between them is the
// single most expensive mistake available here: two boards with different
// radio settings or a different frame layout behave EXACTLY like two boards
// out of range. You will spend an afternoon on antennas.
//
// After editing either copy:
//
//   diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
//
// It must print nothing. LOAM_VERSION below is the runtime backstop — bump it
// on any wire-format change and mismatched nodes drop each other's frames
// loudly instead of half-decoding them.
// ===========================================================================
//
// The sketch that includes this must define its identity FIRST:
//
//   #define AQONE_NODE_ID   0x00010001
//   #define AQONE_NODE_NAME "BUOY01"
//   #include "AqOneLoam.h"
//
// and must define onMeshFrame(), which this file declares and calls but does
// not implement — that is the whole difference between a buoy and a gateway.

#pragma once

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <time.h>
#include <sys/time.h>
#include "mbedtls/md.h"

#ifndef AQONE_NODE_ID
#error "Define AQONE_NODE_ID before including AqOneLoam.h"
#endif
#ifndef AQONE_NODE_NAME
#error "Define AQONE_NODE_NAME before including AqOneLoam.h"
#endif

static const uint32_t NODE_ID   = AQONE_NODE_ID;
static const char*    NODE_NAME = AQONE_NODE_NAME;

// ===== RADIO — identical on every board ====================================
//
// Every node in one mesh must agree on ALL of these AND on LOAM_KEY. Any
// mismatch is indistinguishable from "out of range" at the console.

// 915.0 for the AS923/US915 Heltec V3 and the 915 MHz antennas in the BOM.
// 433.0 if you are on the 470-510 board with a 433 whip.
//
// The repo docs disagree: docs/02_LOAM_PACKET_SPEC.md says 433.0, while
// docs/19_HELTEC_DATA_FLOW.md and the BOM in docs/16_QA_DISCLOSURES.md say
// 915, and docs/33_LORA_RF_BUDGET.md still lists the band as an open item.
// This ships at 915.0 to match the antennas that were actually bought. Check
// the sticker on your board before you trust a range test.
static const float    LORA_FREQ_MHZ  = 915.0;

// SF10 per docs/33_LORA_RF_BUDGET.md, which supersedes the SF7 still written
// into docs/02_LOAM_PACKET_SPEC.md. SF7 reaches ~4.5 km over water, which
// forces buoy spacing tight enough that the deployment cost stops working;
// SF12 lands exactly on the 10.1 km horizon and costs 4x the airtime for it.
static const uint8_t  LORA_SF        = 10;
static const float    LORA_BW_KHZ    = 125.0;
static const uint8_t  LORA_CR        = 5;      // 4/5
static const uint8_t  LORA_SYNC_WORD = 0x34;   // private network, not LoRaWAN
static const int8_t   LORA_TX_DBM    = 22;
static const uint16_t LORA_PREAMBLE  = 8;
static const float    LORA_TCXO_V    = 1.8;    // Heltec V3

// Secrets header must be provided next to each sketch (gitignored).
// See AqOneSecrets.h.example in the sketch folder.
#if __has_include("AqOneSecrets.h")
#include "AqOneSecrets.h"
#else
#error "Missing AqOneSecrets.h - copy AqOneSecrets.h.example to AqOneSecrets.h and set credentials"
#endif

#if defined(__GNUC__) || defined(__clang__)
__attribute__((unused))
#endif
static inline void _loam_key_security_check() {
  if (strcmp(LOAM_KEY, "aqone-dev-key-change-me") == 0) {
    extern void ERROR_LOAM_KEY_EQUALS_OLD_DEFAULT();
    ERROR_LOAM_KEY_EQUALS_OLD_DEFAULT();
  }
}

// Hop budget. 4 lets an edge buoy reach the shore through three relays, which
// is more than the 3-node build has. HOPS > 15 is dropped regardless.
static const uint8_t MESH_TTL = 4;

Preferences prefs;

// ---------------------------------------------------------------------------
// Forward declarations — keep these
//
// Both the Arduino IDE and PlatformIO auto-generate a prototype for every
// function in a .ino and splice the whole block in ahead of the FIRST function
// definition in the sketch. Types named in those prototypes must already exist
// at that point. Reference and pointer parameters only need the name, which is
// why incomplete types are enough.
// ---------------------------------------------------------------------------

struct LoamFrame;
struct SeenKey;
struct TxItem;
struct SosItem;
struct Tracked;
struct ChatLine;
struct VesselWatch;

// Implemented by the sketch, not here. This is the entire difference between a
// buoy and a gateway.
void onMeshFrame(const uint8_t* raw, size_t total, const LoamFrame& f);

// ---------------------------------------------------------------------------
// Clock
//
// A buoy has no internet and therefore no NTP. It learns the time from the
// mesh instead: the gateway stamps `now` into the frames it sends, and the
// first one that arrives sets the board's clock. Until then timestamps are
// omitted rather than invented — an uptime is not a timestamp.
// ---------------------------------------------------------------------------

// Any epoch after 2023 means a real clock reading, not a boot-time zero.
bool clockValid() { return time(nullptr) > 1700000000; }

void adoptClock(uint32_t epoch) {
  if (epoch < 1700000000UL || clockValid()) return;
  struct timeval tv = { .tv_sec = (time_t)epoch, .tv_usec = 0 };
  settimeofday(&tv, nullptr);
  Serial.printf("[time] clock adopted from mesh: %lu\n", (unsigned long)epoch);
}

String isoUtc(time_t at) {
  struct tm tm;
  gmtime_r(&at, &tm);
  char buf[24];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tm);
  return String(buf);
}

// Days since the Unix epoch for a civil date. Howard Hinnant's algorithm.
// Needed because the ESP32's newlib has no timegm(), and mktime() would apply
// a local zone this board does not have.
static int32_t daysFromCivil(int32_t y, uint32_t m, uint32_t d) {
  y -= m <= 2;
  const int32_t  era = (y >= 0 ? y : y - 399) / 400;
  const uint32_t yoe = (uint32_t)(y - era * 400);
  const uint32_t doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const uint32_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + (int32_t)doe - 719468;
}

// "2026-08-15T09:10:02+00:00" and "2026-08-15T09:12:44.120000+00:00" both
// parse; the scan stops at the seconds field either way. Returns 0 on garbage,
// which every caller treats as "absent" rather than 1970.
uint32_t iso8601ToEpoch(const char* s) {
  if (!s || !*s) return 0;
  int Y, M, D, h = 0, mi = 0, se = 0;
  if (sscanf(s, "%d-%d-%dT%d:%d:%d", &Y, &M, &D, &h, &mi, &se) != 6) {
    if (sscanf(s, "%d-%d-%d", &Y, &M, &D) != 3) return 0;
    h = 0; mi = 0; se = 0;
  }
  int32_t days = daysFromCivil(Y, (uint32_t)M, (uint32_t)D);
  if (days < 0) return 0;
  return (uint32_t)days * 86400UL + (uint32_t)h * 3600UL + (uint32_t)mi * 60UL + (uint32_t)se;
}

// ---------------------------------------------------------------------------
// LoAM frame — docs/02_LOAM_PACKET_SPEC.md
//
// | 0 |1| MAGIC 0xA5 | 1 |1| VERSION | 2 |1| TYPE | 3 |1| FLAGS |
// | 4 |4| SRC_ID | 8 |4| RELAY_ID | 12 |2| SEQ | 14 |4| TS |
// | 18 |1| TTL | 19 |1| HOPS | 20 |2| PAYLOAD_LEN | 22 |N| PAYLOAD |
// | 22+N |8| SIG |
//
// Big-endian throughout. Deliberate deviations from the spec document, all
// recorded in firmware/README.md:
//
//   * PAYLOAD_LEN cap raised from 64 to 225 bytes. vessel_id is ALWAYS 32
//     chars and is half the backend's de-duplication key, so it can never be
//     dropped — 64 bytes cannot hold it alongside a boat name and a note. 225
//     is the ceiling, not a round number: the SX1262 carries 255 payload
//     bytes, and 22 header + 225 + 8 signature is exactly that. The field is
//     already 2 bytes wide, so the wire layout is unchanged; only the "drop if
//     > 64" receive rule moves.
//
//   * Two new TYPEs, 0x05 CHAT and 0x06 ETA. 0x05 for chat is what
//     docs/19_HELTEC_DATA_FLOW.md already reserves. 0x06 carries the
//     dispatcher's acknowledgement back down, which the original type list had
//     no frame for at all.
// ---------------------------------------------------------------------------

static const uint8_t LOAM_MAGIC   = 0xA5;
static const uint8_t LOAM_VERSION = 0x01;

static const uint8_t T_SOS    = 0x01;
static const uint8_t T_ACK    = 0x02;
static const uint8_t T_PING   = 0x03;
static const uint8_t T_STATUS = 0x04;
static const uint8_t T_CHAT   = 0x05;
static const uint8_t T_ETA    = 0x06;
static const uint8_t T_WARN   = 0x07;

static const uint8_t F_SIGNED    = 0x01;
static const uint8_t F_WANTS_ACK = 0x02;
static const uint8_t F_ACK       = 0x04;
static const uint8_t F_KNOWN     = 0x07;   // any other bit set => drop

static const size_t LOAM_HEADER  = 22;
static const size_t LOAM_SIG_LEN = 8;

// See the note above: this is the SX1262's ceiling, not a preference.
static const size_t LOAM_MAX_PAYLOAD = 225;
static const size_t LOAM_MAX_FRAME   = LOAM_HEADER + LOAM_MAX_PAYLOAD + LOAM_SIG_LEN;

struct LoamFrame {
  uint8_t  type;
  uint8_t  flags;
  uint32_t src;
  uint32_t relay;
  uint16_t seq;
  uint32_t ts;
  uint8_t  ttl;
  uint8_t  hops;
  char     payload[LOAM_MAX_PAYLOAD + 1];
  uint16_t len;
  float    rssi;
  float    snr;
};

static void put16(uint8_t* p, uint16_t v) { p[0] = v >> 8; p[1] = v; }
static void put32(uint8_t* p, uint32_t v) {
  p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v;
}
static uint16_t get16(const uint8_t* p) { return ((uint16_t)p[0] << 8) | p[1]; }
static uint32_t get32(const uint8_t* p) {
  return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
         ((uint32_t)p[2] << 8)  | p[3];
}

// HMAC-SHA256 truncated to 8 bytes, over the frame with the relay-mutable bytes
// zeroed (RELAY_ID at 8..11, and TTL/HOPS at 18..19) so relays may mutate them
// without invalidating the origin's signature:
// frame[0..7] ++ {0,0,0,0} ++ frame[12..17] ++ {0,0} ++ frame[20 .. 21+N].
//
// `out` is a plain pointer rather than uint8_t[LOAM_SIG_LEN] on purpose: the
// array bound decays anyway, and spelling a constant in the signature would
// put it inside the auto-generated prototype block. Callers pass a
// LOAM_SIG_LEN buffer.
static void loamSign(const uint8_t* frame, size_t payloadLen, uint8_t* out) {
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, info, 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)LOAM_KEY, strlen(LOAM_KEY));

  static const uint8_t zeroRelay[4] = { 0, 0, 0, 0 };
  static const uint8_t zeroHops[2]  = { 0, 0 };
  mbedtls_md_hmac_update(&ctx, frame, 8);
  mbedtls_md_hmac_update(&ctx, zeroRelay, 4);
  mbedtls_md_hmac_update(&ctx, frame + 12, 6);
  mbedtls_md_hmac_update(&ctx, zeroHops, 2);
  mbedtls_md_hmac_update(&ctx, frame + 20, 2 + payloadLen);

  uint8_t full[32];
  mbedtls_md_hmac_finish(&ctx, full);
  mbedtls_md_free(&ctx);
  memcpy(out, full, LOAM_SIG_LEN);
}

// Returns total byte count, or 0 if the payload does not fit.
static size_t loamEncode(uint8_t* buf, uint8_t type, uint8_t flags,
                         uint32_t src, uint32_t relay, uint16_t seq,
                         uint32_t ts, uint8_t ttl, uint8_t hops,
                         const char* payload, size_t payloadLen) {
  if (payloadLen > LOAM_MAX_PAYLOAD) return 0;

  buf[0] = LOAM_MAGIC;
  buf[1] = LOAM_VERSION;
  buf[2] = type;
  buf[3] = flags | F_SIGNED;
  put32(buf + 4, src);
  put32(buf + 8, relay);
  put16(buf + 12, seq);
  put32(buf + 14, ts);
  buf[18] = ttl;
  buf[19] = hops;
  put16(buf + 20, (uint16_t)payloadLen);
  if (payloadLen) memcpy(buf + LOAM_HEADER, payload, payloadLen);

  loamSign(buf, payloadLen, buf + LOAM_HEADER + payloadLen);
  return LOAM_HEADER + payloadLen + LOAM_SIG_LEN;
}

// Any frame that does not parse and verify is dropped. There is no negotiation
// and no partial acceptance: a malformed distress frame is worse than a
// missing one, because it would be shown to a dispatcher as fact.
static bool loamDecode(const uint8_t* buf, size_t total, LoamFrame& out) {
  if (total < LOAM_HEADER + LOAM_SIG_LEN) return false;
  if (buf[0] != LOAM_MAGIC || buf[1] != LOAM_VERSION) return false;
  if (buf[3] & ~F_KNOWN) return false;

  uint16_t n = get16(buf + 20);
  if (n > LOAM_MAX_PAYLOAD) return false;
  if (total != LOAM_HEADER + n + LOAM_SIG_LEN) return false;

  uint8_t expect[LOAM_SIG_LEN];
  loamSign(buf, n, expect);
  if (memcmp(expect, buf + LOAM_HEADER + n, LOAM_SIG_LEN) != 0) return false;

  out.type  = buf[2];
  out.flags = buf[3];
  out.src   = get32(buf + 4);
  out.relay = get32(buf + 8);
  out.seq   = get16(buf + 12);
  out.ts    = get32(buf + 14);
  out.ttl   = buf[18];
  out.hops  = buf[19];
  out.len   = n;
  memcpy(out.payload, buf + LOAM_HEADER, n);
  out.payload[n] = 0;

  if (out.hops > 15) return false;
  return true;
}

// ---------------------------------------------------------------------------
// Seen-set — the entire flood-control mechanism
//
// A TTL flood without this is a broadcast storm: three buoys in earshot of
// each other rebroadcast the same SOS until the band is unusable. 64 entries
// covers far more traffic than a 3-node mesh generates in the relevant window.
// ---------------------------------------------------------------------------

struct SeenKey { uint32_t src; uint16_t seq; uint8_t type; bool used; };

static const int SEEN_MAX = 64;
SeenKey seenRing[SEEN_MAX];
int     seenHead = 0;

bool seenBefore(uint32_t src, uint16_t seq, uint8_t type) {
  for (int i = 0; i < SEEN_MAX; i++)
    if (seenRing[i].used && seenRing[i].src == src &&
        seenRing[i].seq == seq && seenRing[i].type == type) return true;
  return false;
}

void seenRemember(uint32_t src, uint16_t seq, uint8_t type) {
  seenRing[seenHead] = { src, seq, type, true };
  seenHead = (seenHead + 1) % SEEN_MAX;
}

// ---------------------------------------------------------------------------
// Radio
// ---------------------------------------------------------------------------

// Heltec WiFi LoRa 32 V3 SX1262 wiring. Board traces, not preferences.
static const int LORA_NSS  = 8;
static const int LORA_DIO1 = 14;
static const int LORA_RST  = 12;
static const int LORA_BUSY = 13;
static const int LORA_SCK  = 9;
static const int LORA_MISO = 11;
static const int LORA_MOSI = 10;

SPIClass loraSpi(HSPI);
SX1262   radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY, loraSpi);

volatile bool radioIrq     = false;
bool          radioReady   = false;
bool          radioSending = false;

void IRAM_ATTR onRadioIrq() { radioIrq = true; }

// Outbound frames wait here rather than going straight out. Two reasons:
// transmitting is half-duplex (anything arriving mid-TX is simply not heard),
// and a flood mesh where every node answers instantly collides with itself.
// Each item carries a `dueAt` so senders can jitter their own backoff.
struct TxItem {
  uint8_t  bytes[LOAM_MAX_FRAME];
  size_t   len;
  uint32_t dueAt;
  bool     used;
};

static const int TX_MAX = 10;
TxItem   txRing[TX_MAX];
uint32_t txBusyUntil = 0;

// Mesh sequence counter. Two bytes on the wire, so it wraps — that is fine,
// the seen-set window is far shorter than 65536 frames. Bumped by 100 and
// persisted once per boot so a brown-out mid-flood cannot reuse a sequence
// number that neighbours still have in their seen-set (which would make the
// first frames after recovery look like duplicates and vanish).
uint16_t meshSeq = 1;

void meshSeqInit() {
  prefs.begin("aqone", false);
  meshSeq = prefs.getUShort("mseq", 1) + 100;
  prefs.putUShort("mseq", meshSeq);
  prefs.end();
}

void meshSeqCheckpoint() {
  // Once every 64 frames, not every frame: NVS has finite write endurance and
  // the +100 boot jump already covers whatever is lost in between.
  if ((meshSeq & 0x3F) != 0) return;
  prefs.begin("aqone", false);
  prefs.putUShort("mseq", meshSeq);
  prefs.end();
}

bool txEnqueue(const uint8_t* bytes, size_t len, uint32_t delayMs = 0, size_t reserve = 0) {
  int freeSlots = 0;
  for (int i = 0; i < TX_MAX; i++) {
    if (!txRing[i].used) freeSlots++;
  }
  if (freeSlots <= (int)reserve) {
    Serial.println("[lora] TX ring reserve limit reached - frame dropped");
    return false;
  }
  for (int i = 0; i < TX_MAX; i++) {
    if (txRing[i].used) continue;
    memcpy(txRing[i].bytes, bytes, len);
    txRing[i].len   = len;
    txRing[i].dueAt = millis() + delayMs;
    txRing[i].used  = true;
    return true;
  }
  Serial.println("[lora] TX ring full - frame dropped");
  return false;
}

// Build, sign and enqueue an origin frame from this node.
bool meshSend(uint8_t type, uint8_t flags, const char* payload, size_t len,
              uint32_t delayMs = 0) {
  uint8_t buf[LOAM_MAX_FRAME];
  uint32_t ts = clockValid() ? (uint32_t)time(nullptr) : 0;
  uint16_t seq = meshSeq++;
  meshSeqCheckpoint();

  size_t total = loamEncode(buf, type, flags, NODE_ID, NODE_ID, seq, ts,
                            MESH_TTL, 0, payload, len);
  if (!total) {
    Serial.printf("[lora] payload too large for type 0x%02X (%u bytes)\n",
                  type, (unsigned)len);
    return false;
  }
  // Remember our own frames so an echo relayed back by a neighbour is dropped
  // instead of being processed as new traffic.
  seenRemember(NODE_ID, seq, type);
  size_t reserve = (type == T_CHAT) ? 2 : 0;
  return txEnqueue(buf, total, delayMs, reserve);
}

// Re-transmit someone else's frame with the hop bytes advanced. The signature
// is NOT recomputed: relays do not re-sign, which is calibrated so the hop bytes
// are excluded from the signed region.
void meshRelay(const uint8_t* raw, size_t total, const LoamFrame& f) {
  if (f.ttl == 0) return;
  uint8_t buf[LOAM_MAX_FRAME];
  memcpy(buf, raw, total);
  buf[18] = f.ttl - 1;
  buf[19] = f.hops + 1;
  put32(buf + 8, NODE_ID);   // RELAY_ID, outside the signed region

  // Random backoff. Without it, two relays that heard the same frame answer in
  // the same millisecond and cancel each other at every listener.
  size_t reserve = (f.type == T_CHAT) ? 2 : 0;
  txEnqueue(buf, total, 200 + random(400), reserve);
}

bool radioSetup() {
  loraSpi.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  int st = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR,
                       LORA_SYNC_WORD, LORA_TX_DBM, LORA_PREAMBLE,
                       LORA_TCXO_V, false);
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("[lora] begin failed: %d\n", st);
    return false;
  }

  // Both of these are Heltec V3-specific and both fail SILENTLY if omitted:
  // the radio initialises cleanly, reports no error, and transmits nothing
  // anyone can hear.
  radio.setDio2AsRfSwitch(true);
  radio.setCRC(2);

  radio.setDio1Action(onRadioIrq);
  st = radio.startReceive();
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("[lora] startReceive failed: %d\n", st);
    return false;
  }

  Serial.printf("[lora] up  %.1f MHz  SF%u  BW%.0f  CR4/%u  id=0x%08lX\n",
                LORA_FREQ_MHZ, LORA_SF, LORA_BW_KHZ, LORA_CR,
                (unsigned long)NODE_ID);
  return true;
}

// Mesh liveness. A buoy cannot see the internet, so "is the shore reachable"
// is inferred from whether the gateway has been heard lately. Anything the
// gateway sends counts: an ACK, an ETA, a downlinked chat line, or its beacon.
static const uint32_t MESH_STALE_MS   = 150000;   // 2.5 beacon intervals
static const uint32_t BEACON_EVERY_MS = 60000;

uint32_t lastShoreHeard = 0;   // millis(), 0 = never
uint32_t lastMeshRx     = 0;
float    lastMeshRssi   = 0;
float    lastMeshSnr    = 0;

bool shoreSeen() { return lastShoreHeard != 0; }

void radioService() {
  if (!radioReady) return;

  if (radioIrq) {
    radioIrq = false;

    if (radioSending) {
      radio.finishTransmit();
      radioSending = false;
      radio.startReceive();
    } else {
      uint8_t buf[LOAM_MAX_FRAME];
      size_t  len = radio.getPacketLength();
      if (len > 0 && len <= sizeof(buf) && radio.readData(buf, len) == RADIOLIB_ERR_NONE) {
        LoamFrame f;
        if (loamDecode(buf, len, f)) {
          f.rssi = radio.getRSSI();
          f.snr  = radio.getSNR();
          onMeshFrame(buf, len, f);
        }
      }
      radio.startReceive();
    }
  }

  if (radioSending) return;

  uint32_t now = millis();
  if ((int32_t)(now - txBusyUntil) < 0) return;

  for (int i = 0; i < TX_MAX; i++) {
    if (!txRing[i].used) continue;
    if ((int32_t)(now - txRing[i].dueAt) < 0) continue;

    int st = radio.startTransmit(txRing[i].bytes, txRing[i].len);
    if (st == RADIOLIB_ERR_NONE) {
      radioSending = true;
      // Airtime at SF10/125 kHz is roughly a second for a full frame. Holding
      // the radio for a beat afterwards keeps a burst of queued frames from
      // stepping on each other and on anyone answering them.
      txBusyUntil = now + 400;
    } else {
      Serial.printf("[lora] startTransmit failed: %d\n", st);
    }
    txRing[i].used = false;
    return;   // one frame per pass; loop() stays responsive
  }
}

// ---------------------------------------------------------------------------
// Chat payload — the one payload builder both roles need
// ---------------------------------------------------------------------------

size_t buildChatPayload(const char* from, const char* text, char* out, size_t cap) {
  JsonDocument doc;
  doc["v"]    = 1;
  doc["kind"] = "chat";
  doc["from"] = from;
  doc["text"] = text;
  // Whoever has a clock shares it, so time spreads outward through the mesh
  // from the gateway rather than only reaching buoys the gateway can hear.
  // adoptClock() ignores this once a board already knows the time.
  if (clockValid()) doc["now"] = (uint32_t)time(nullptr);
  size_t n = serializeJson(doc, out, cap);
  return (n > 0 && n <= LOAM_MAX_PAYLOAD) ? n : 0;
}

// ---------------------------------------------------------------------------
// Onboard OLED
//
// Heltec WiFi LoRa 32 V3 pinout. These are board wiring, not preferences — the
// panel is soldered to these pins and will stay dark on any others. Each
// sketch draws its own oledDraw(); this is only the bring-up both share.
// ---------------------------------------------------------------------------

static const int OLED_SDA = 17;
static const int OLED_SCL = 18;
static const int OLED_RST = 21;

// V3 routes the OLED through the Vext switch, which is ACTIVE LOW. Miss this
// and begin() fails with correct wiring, because the panel has no power yet.
static const int VEXT_CTRL = 36;

static const uint8_t OLED_ADDR = 0x3C;
static const int     OLED_W    = 128;
static const int     OLED_H    = 64;

Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, OLED_RST);

// Set only if begin() succeeded. Every draw checks it, so a dead or absent
// panel costs one boolean per frame and never blocks SOS handling.
bool oledReady = false;

void oledSetup() {
  pinMode(VEXT_CTRL, OUTPUT);
  digitalWrite(VEXT_CTRL, LOW);   // active low: power the panel
  delay(50);                      // let the rail settle before I2C

  Wire.begin(OLED_SDA, OLED_SCL);
  oledReady = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  if (!oledReady) {
    Serial.println("[oled] not found at 0x3C - continuing without display");
    return;
  }
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 0);
  oled.print(F("AqOne booting..."));
  oled.display();
}

// Header and divider, identical on both boards so a glance tells you which is
// which. The sketch fills in the four lines below it.
void oledHeader() {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 0);
  oled.print(F("AqOne "));
  oled.print(NODE_NAME);
  oled.drawFastHLine(0, 10, OLED_W, SSD1306_WHITE);
}
