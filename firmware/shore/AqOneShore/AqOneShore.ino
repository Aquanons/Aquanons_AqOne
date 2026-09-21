// AqOneShore.ino — Heltec WiFi LoRa 32 V3 (ESP32-S3)
//
// THE SHORE GATEWAY. The board on the mast with the internet, the one no phone
// ever connects to. Its partner is firmware/buoy/AqOneBuoy — flash that one to
// the boards that float.
//
//   buoys --LoRa--> THIS BOARD --HTTPS--> backend --> MDRRMO dashboard
//   buoys <--LoRa-- THIS BOARD <--HTTPS-- backend <-- dispatcher's ETA
//
// Four jobs:
//   1. Hear SOS frames and POST them to /api/sos, then acknowledge over the
//      radio so the originating buoy can clear its queue
//   2. Carry chat both ways between the mesh and /api/mesh/chat
//   3. Poll for the dispatcher's acknowledgement and push it back down
//   4. Beacon, so buoys can tell "the shore is quiet" from "the shore is gone"
//      — and so a buoy with no internet learns what time it is
//
// It runs NO access point. docs/19_HELTEC_DATA_FLOW.md calls this option 1,
// "dedicate the gateway", and it is what sidesteps the ESP32's one-radio
// AP+station channel collision entirely: this board is a station and nothing
// else, so joining the uplink can never kick a fisher's phone off a buoy.
//
// Gateways never re-transmit mesh frames. That is the spec, and it is also why
// this file has no relay logic: a gateway that floods would double every
// frame it has already taken responsibility for.
//
// ---------------------------------------------------------------------------
// THE ONE THING THAT WILL BITE YOU
//
// The radio settings and the HMAC key in AqOneLoam.h must be IDENTICAL to the
// buoy board's copy of that file. A mismatch in frequency, spreading factor,
// bandwidth, coding rate, sync word or key behaves exactly like being out of
// range: no error, no log line, nothing arrives. After editing either copy:
//
//   diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
//
// It must print nothing.
// ---------------------------------------------------------------------------

// ===== IDENTITY — change this per board ====================================
//
// NODE_ID is the on-air identity: SRC_ID in the LoAM frame. It must be unique
// across the whole deployment — two nodes sharing an id make the seen-set drop
// one of them as a duplicate, which at the console is indistinguishable from a
// dead radio. Buoys use 0x0001xxxx; gateways use 0x000000xx.

#define AQONE_NODE_ID   0x000000FF
#define AQONE_NODE_NAME "SHORE01"

// ===========================================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// Built-in 128x64 SSD1306 OLED on the Heltec WiFi LoRa 32 V3.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// The shared radio layer: frame format, signing, seen-set, TX ring, SX1262
// driver, clock, OLED bring-up. Must come AFTER the two defines above.
#include "AqOneLoam.h"

// ===== CONFIGURE ME ========================================================

// This board's internet. On a real deployment it is the mast site's link; for
// a demo a phone hotspot is fine.
static const char* UPLINK_SSID = "Converge_2.4GHz_30D7";
static const char* UPLINK_PASS = "4eHfak6E";

static const char* BACKEND_HOST =
    "https://aqone-backend.onrender.com";

// Responder acknowledgements and ETAs come from GET /api/sos/downlink, the
// gateway-only view of the responder's answer. It is guarded by the same
// X-Api-Key / GATEWAY_API_KEY credential the contact, pressure and current
// ingest routes already use, so this board needs no human's account.
//
// It deliberately is NOT GET /api/sos/active. That one is behind require_user
// (a dispatcher login) and carries position, the fisher's own distress note,
// boat name, trust tier and the vessel owner's name, licence and phone. A key
// hardcoded in firmware on a mast must not unlock any of that. /downlink
// returns only what this board is about to broadcast in clear anyway.
//
// GET /api/sos/vessel/{id} is NOT usable here either: it is behind
// require_vessel_device and derives ownership from the handset's own paired
// credential, which a gateway does not have and cannot obtain.
//
// Set this to the same value as GATEWAY_API_KEY in the backend environment.
// With it empty, SOS still flows UP and chat still flows both ways - but the
// dispatcher's ETA cannot come back down, the OLED shows "no key", and
// pollAcks() says so on serial every 45 s rather than failing silently.
static const char* GATEWAY_API_KEY = "";

// ===========================================================================

bool   uplinkUp = false;
// Last HTTP status from the downlink poll. 0 = not polled yet. Surfaced on
// the OLED so a board that cannot read acknowledgements says so on its face,
// instead of looking identical to one with nothing to report.
int    lastAckHttp = 0;

int    lastChatId = 0;      // since_id cursor into GET /api/mesh/chat
// The first poll after a boot only moves the cursor. Without this, a gateway
// that restarts asks for since_id=0, gets the last 50 lines of history back,
// and spends the next minute reading the whole backlog onto the radio - while
// a queued SOS waits behind it.
bool   chatPrimed = false;

void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(UPLINK_SSID, UPLINK_PASS);
  Serial.print("[wifi] uplink");
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    uplinkUp = true;
    Serial.printf("[wifi] uplink ok  ip=%s\n", WiFi.localIP().toString().c_str());
    // UTC, no offset. This board's clock is the whole mesh's clock: every
    // frame it sends carries `now`, and that is how buoys with no internet
    // learn what time it is.
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  } else {
    // Not fatal. LoRa still runs and frames are still received - they simply
    // are not acknowledged, so the buoys keep them queued and keep retrying,
    // which is exactly the right behaviour when the gateway is deaf to the
    // internet.
    Serial.println("[wifi] no uplink - mesh traffic will be held");
  }
}

bool online() { return uplinkUp && WiFi.status() == WL_CONNECTED; }

// TLS certificates are not verified. There is no cert store on this board and
// no way to rotate one on a mast. Acceptable for a prototype; a production
// gateway pins a CA. Say so if asked rather than letting it be discovered.
bool httpsBegin(WiFiClientSecure& client, HTTPClient& https, const String& url) {
  client.setInsecure();
  return https.begin(client, url);
}

// ---------------------------------------------------------------------------
// Uplink to the backend
// ---------------------------------------------------------------------------

// POST /api/sos — deliberately unauthenticated. A gateway relaying a distress
// call has no bearer token and no way to obtain one.
//
// client_ts is forwarded EXACTLY as the phone sent it, carried untouched
// through the LoRa frame. It is half of the de-duplication key
// (vessel_id, client_ts). If we substituted our own clock, the same emergency
// arriving here AND over the fisher's own mobile data would create two
// separate incidents on the dispatcher's screen.
bool postSos(const JsonDocument& in, uint32_t srcId, uint16_t seq) {
  if (!online()) return false;

  const char* vid = in["vid"] | "";
  uint32_t    ts  = in["ts"]  | 0;
  if (!vid[0] || ts == 0) return false;

  WiFiClientSecure client;
  HTTPClient https;
  if (!httpsBegin(client, https, String(BACKEND_HOST) + "/api/sos")) return false;
  https.addHeader("Content-Type", "application/json");
  https.setTimeout(12000);

  JsonDocument doc;
  doc["vessel_id"]  = vid;
  doc["client_ts"]  = ts;
  doc["boat"]       = in["boat"] | "";
  doc["trust_tier"] = in["tt"] | "self_declared";
  doc["source"]     = "buoy";
  doc["buoy_id"]    = in["bid"] | NODE_NAME;
  doc["src_id"]     = srcId;
  // The buoy's own SOS counter, not the mesh frame seq.
  //
  // These are different numbers and only one of them is any use downstream.
  // `seq` here is the frame seq, which rotates on every retransmission - a
  // retry MUST use a fresh one or each relay's seen-set drops it as a
  // duplicate. The handset, meanwhile, holds the value the buoy returned from
  // POST /v1/sos, and that is what it matches the dispatcher's answer against
  // when it comes back down with no local_id to pair on. Storing the frame
  // seq here meant the acknowledgement reached the buoy correctly and then
  // failed to match anything on the phone.
  //
  // `| 0` covers a buoy on firmware that predates the `sq` field: fall back
  // to the frame seq, which is what this always used to send. it.seq counts
  // from 1, so 0 is unambiguously "absent".
  uint32_t payloadSeq = in["sq"] | 0;
  doc["seq"]        = payloadSeq ? payloadSeq : (uint32_t)seq;
  if (in["n"].is<const char*>()) doc["note"] = in["n"];
  if (in["lat"].is<double>() && in["lon"].is<double>()) {
    doc["lat"] = in["lat"];
    doc["lon"] = in["lon"];
  }

  String body;
  serializeJson(doc, body);
  int code = https.POST(body);
  https.end();

  Serial.printf("[sos] POST %s -> %d\n", vid, code);
  // 200 covers both "created" and "already recorded". Either way the backend
  // has it and the buoy can stop retrying.
  return code == 200;
}

// Chat off the mesh goes into the database tagged `mesh`, and downlink skips
// anything carrying that tag. Without it, a line a fisher sent from a boat
// would be stored, read back on the next poll, and rebroadcast to the boat it
// came from — arriving on its own sender's screen a second time, minutes later.
bool postChat(const char* sender, const char* text) {
  if (!online()) return false;

  WiFiClientSecure client;
  HTTPClient https;
  if (!httpsBegin(client, https, String(BACKEND_HOST) + "/api/mesh/chat")) return false;
  https.addHeader("Content-Type", "application/json");
  https.setTimeout(10000);

  JsonDocument doc;
  doc["sender"] = sender;
  doc["text"]   = text;
  doc["origin"] = "mesh";

  String body;
  serializeJson(doc, body);
  int code = https.POST(body);
  https.end();

  Serial.printf("[chat] POST %s -> %d\n", sender, code);
  return code == 201 || code == 200;
}

// ---------------------------------------------------------------------------
// Vessels this gateway has heard from, and what it last told them.
//
// The signature is how a re-poll becomes a downlink only when something the
// fisher would actually see has changed. Without it the gateway would burn a
// second of airtime every 45 s repeating an ETA nobody's screen needs again.
// ---------------------------------------------------------------------------

static const int MAX_VESSELS = 12;

struct VesselWatch {
  char     vesselId[33];
  bool     used;
  uint32_t signature;
};

VesselWatch watched[MAX_VESSELS];

// Persisted, unlike most of this gateway's state. A shore reboot between an
// SOS and the dispatcher acknowledging it would otherwise lose the only record
// of which vessels this mesh can answer - and nothing would rebuild it,
// because the buoy stops retransmitting the moment it is acked. The fisher
// would sit at `relayed` forever while the dashboard showed the rescue under
// way.
void watchSave() {
  prefs.begin("aqone", false);
  prefs.putBytes("watch", watched, sizeof(watched));
  prefs.end();
}

void watchLoad() {
  prefs.begin("aqone", true);
  size_t n = prefs.getBytesLength("watch");
  if (n == sizeof(watched)) prefs.getBytes("watch", watched, sizeof(watched));
  else memset(watched, 0, sizeof(watched));
  prefs.end();
  // Signatures are deliberately NOT trusted across a reboot: re-sending one
  // ETA per open incident on the first poll is cheap, and silence is not.
  for (int i = 0; i < MAX_VESSELS; i++) watched[i].signature = 0;
}

void watchVessel(const char* vesselId) {
  for (int i = 0; i < MAX_VESSELS; i++)
    if (watched[i].used && strcmp(watched[i].vesselId, vesselId) == 0) return;
  for (int i = 0; i < MAX_VESSELS; i++) {
    if (watched[i].used) continue;
    memset(&watched[i], 0, sizeof(VesselWatch));
    strncpy(watched[i].vesselId, vesselId, 32);
    watched[i].used = true;
    watchSave();
    return;
  }
  // Full. Evict rather than refuse: the vessel that just sent a distress call
  // is the one with a rescue still in progress, and it is the one that needs
  // the dispatcher's answer routed back to it.
  memset(&watched[0], 0, sizeof(VesselWatch));
  strncpy(watched[0].vesselId, vesselId, 32);
  watched[0].used = true;
  watchSave();
}

VesselWatch* watchFind(const char* vesselId) {
  for (int i = 0; i < MAX_VESSELS; i++)
    if (watched[i].used && strcmp(watched[i].vesselId, vesselId) == 0)
      return &watched[i];
  return nullptr;
}

static uint32_t fnv1a(uint32_t h, const char* s) {
  if (!s) return h;
  while (*s) { h ^= (uint8_t)*s++; h *= 16777619UL; }
  return h;
}

// ---------------------------------------------------------------------------
// Downlink payloads
// ---------------------------------------------------------------------------

size_t buildEtaPayload(const JsonObject& ev, const char* state, char* out, size_t cap) {
  for (int attempt = 0; attempt < 3; attempt++) {
    JsonDocument doc;
    // No "kind" here, unlike the SOS payload: TYPE 0x06 in the authenticated
    // header already says what this is, and at 32 hex chars of vessel_id plus
    // four timestamps this payload has no 14 bytes to spare on restating it.
    // No client_ts either - RemoteSos.fromJson does not read it.
    doc["v"]   = 1;
    doc["vid"] = ev["vessel_id"];
    doc["id"]  = ev["id"];
    doc["ds"]  = state;
    if (clockValid()) doc["now"] = (uint32_t)time(nullptr);
    if (ev["seq"].is<int>()) doc["sq"] = ev["seq"];

    uint32_t ackAt = iso8601ToEpoch(ev["acknowledged_at"] | "");
    uint32_t etaAt = iso8601ToEpoch(ev["eta_at"] | "");
    uint32_t resAt = iso8601ToEpoch(ev["resolved_at"] | "");
    if (ackAt) doc["ack"] = ackAt;
    if (etaAt) doc["eta"] = etaAt;
    if (resAt) doc["res"] = resAt;
    if (ev["responder_status"].is<int>()) doc["rs"] = ev["responder_status"];

    // Both of these are truncated hard before they are shed, because half a
    // dispatcher's note still reads. The NAME goes first if something must go:
    // "Coast Guard boat en route from Dumaguit" tells a frightened person more
    // than "dispatcher_maria" does. The ETA and the status code never shed -
    // they are the message, the rest is context.
    if (attempt < 1) {
      const char* by = ev["acked_by"] | "";
      if (by[0]) doc["by"] = String(by).substring(0, 16);
    }
    if (attempt < 2) {
      const char* note = ev["responder_note"] | "";
      if (note[0]) doc["n"] = String(note).substring(0, 40);
    }

    size_t n = serializeJson(doc, out, cap);
    if (n > 0 && n <= LOAM_MAX_PAYLOAD) return n;
  }
  return 0;
}

// GET /api/sos/downlink in one call rather than per vessel: one request
// covers every live incident, and it is the gateway-only view of the
// responder's answer (see GATEWAY_API_KEY at the top of this file).
void pollAcks() {
  if (!online()) return;

  if (!GATEWAY_API_KEY[0]) {
    // Repeated on every poll, not logged once at boot. The failure this
    // guards is a fisher watching a screen that never changes while a
    // dispatcher believes the ETA was sent - it must be impossible to miss
    // on a serial monitor, and it must still be shouting an hour in.
    Serial.println("[ack] GATEWAY_API_KEY is empty - the dispatcher's ETA "
                   "CANNOT reach the boats. Set it and reflash.");
    return;
  }

  WiFiClientSecure client;
  HTTPClient https;
  if (!httpsBegin(client, https, String(BACKEND_HOST) + "/api/sos/downlink")) return;
  https.addHeader("X-Api-Key", GATEWAY_API_KEY);
  https.setTimeout(12000);

  int code = https.GET();
  lastAckHttp = code;
  if (code != 200) {
    https.end();
    Serial.printf("[ack] downlink poll -> %d%s\n", code,
                  code == 401 ? " - GATEWAY_API_KEY rejected, check it matches"
                                " the backend environment" : "");
    return;
  }

  // Filtered parse straight off the socket. Materialising the whole feed as a
  // String first is the allocation that kills the board.
  JsonDocument filter;
  JsonObject f = filter["events"].add<JsonObject>();
  f["id"] = true; f["vessel_id"] = true; f["seq"] = true;
  f["delivery_state"] = true;
  f["acknowledged_at"] = true; f["acked_by"] = true; f["eta_at"] = true;
  f["responder_status"] = true; f["responder_note"] = true;
  f["resolved_at"] = true;

  JsonDocument doc;
  DeserializationError err =
      deserializeJson(doc, https.getStream(), DeserializationOption::Filter(filter));
  https.end();
  if (err) { Serial.printf("[ack] parse failed: %s\n", err.c_str()); return; }

  for (JsonObject ev : doc["events"].as<JsonArray>()) {
    const char* vid = ev["vessel_id"] | "";
    if (!vid[0]) continue;
    VesselWatch* w = watchFind(vid);
    if (!w) continue;   // never came through this mesh; nothing to send it to

    // Taken from the server, not recomputed. This board used to mirror
    // _delivery_state() from backend/app/api/sos.py, which meant a second
    // implementation of it lived in firmware and only a reflash could correct
    // a drift between the two.
    const char* state = ev["delivery_state"] | "relayed";

    uint32_t sig = 2166136261UL;
    sig = fnv1a(sig, state);
    sig = fnv1a(sig, ev["acknowledged_at"] | "");
    sig = fnv1a(sig, ev["eta_at"] | "");
    sig = fnv1a(sig, ev["resolved_at"] | "");
    sig = fnv1a(sig, ev["responder_note"] | "");
    sig = fnv1a(sig, String((int)(ev["responder_status"] | 0)).c_str());
    if (sig == w->signature) continue;

    char payload[LOAM_MAX_PAYLOAD + 1];
    size_t n = buildEtaPayload(ev, state, payload, sizeof(payload));
    if (!n) continue;
    if (!meshSend(T_ETA, 0, payload, n)) continue;

    w->signature = sig;
    Serial.printf("[ack] downlink %s -> %s\n", vid, state);
  }
}

// GET /api/mesh/chat?since_id= — everything said on the dashboard or by a boat
// on some other hub, pushed down to the boats on this mesh.
void pollChat() {
  if (!online()) return;

  WiFiClientSecure client;
  HTTPClient https;
  String url = String(BACKEND_HOST) + "/api/mesh/chat?limit=10&since_id=" + String(lastChatId);
  if (!httpsBegin(client, https, url)) return;
  https.setTimeout(10000);

  if (https.GET() != 200) { https.end(); return; }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, https.getStream());
  https.end();
  if (err) return;

  bool priming = !chatPrimed;
  chatPrimed = true;

  for (JsonObject m : doc["messages"].as<JsonArray>()) {
    int id = m["id"] | 0;
    if (id > lastChatId) lastChatId = id;
    if (priming) continue;

    // Anything tagged `mesh` came up off the radio and is already on the
    // boats' screens. Sending it back down is an echo, not a delivery.
    const char* origin = m["origin"] | "app";
    if (strcmp(origin, "mesh") == 0) continue;

    const char* sender = m["sender"] | "shore";
    const char* text   = m["text"] | "";
    if (!text[0]) continue;

    char payload[LOAM_MAX_PAYLOAD + 1];
    // The database field is 256 chars; a buoy's history line is 64. Truncating
    // here rather than at the buoy keeps the airtime down and makes what the
    // fisher sees identical on every board.
    String clipped = String(text).substring(0, 64);
    size_t n = buildChatPayload(sender, clipped.c_str(), payload, sizeof(payload));
    if (n) meshSend(T_CHAT, 0, payload, n, random(400));
  }
}

// ---------------------------------------------------------------------------
// Warning downlink (Task 2.5)
// ---------------------------------------------------------------------------

struct WarningWatch {
  int      warningId;
  uint32_t signature;
  bool     used;
};

static const int MAX_WARN_WATCH = 10;
WarningWatch warnWatched[MAX_WARN_WATCH];

void reportWarningDelivery(int warningId, const char* state) {
  if (!online()) return;
  WiFiClientSecure client;
  HTTPClient https;
  String url = String(BACKEND_HOST) + "/api/advisories/delivery";
  if (!httpsBegin(client, https, url)) return;
  https.addHeader("Content-Type", "application/json");
  https.setTimeout(5000);

  JsonDocument doc;
  doc["warning_id"] = warningId;
  doc["delivery_state"] = state;
  doc["buoy_id"] = NODE_NAME;

  String body;
  serializeJson(doc, body);
  https.POST(body);
  https.end();
}

size_t buildWarnPayload(const JsonObject& adv, char* out, size_t cap) {
  JsonDocument doc;
  doc["v"]   = 1;
  doc["id"]  = adv["id"];
  doc["src"] = adv["source"] | "MDRRMO";
  doc["pr"]  = adv["priority"] | "Warning";
  doc["area"]= adv["municipality"] | "All";
  if (clockValid()) doc["now"] = (uint32_t)time(nullptr);

  uint32_t pubAt = iso8601ToEpoch(adv["publish_date"] | "");
  uint32_t expAt = iso8601ToEpoch(adv["expiration_date"] | "");
  if (pubAt) doc["iss"] = pubAt;
  if (expAt) doc["exp"] = expAt;

  String title = adv["title"] | "";
  if (title.length()) doc["ttl"] = title.substring(0, 48);

  String desc = adv["description"] | "";
  if (desc.length()) doc["txt"] = desc.substring(0, 80);

  size_t n = serializeJson(doc, out, cap);
  return (n > 0 && n <= LOAM_MAX_PAYLOAD) ? n : 0;
}

void pollWarnings() {
  if (!online()) return;

  WiFiClientSecure client;
  HTTPClient https;
  String url = String(BACKEND_HOST) + "/api/public/advisories";
  if (!httpsBegin(client, https, url)) return;
  https.setTimeout(10000);

  if (https.GET() != 200) { https.end(); return; }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, https.getStream());
  https.end();
  if (err) return;

  for (JsonObject adv : doc["advisories"].as<JsonArray>()) {
    int wid = adv["id"] | 0;
    if (!wid) continue;

    const char* prio = adv["priority"] | "";
    if (strcmp(prio, "Warning") != 0 && strcmp(prio, "Emergency") != 0) continue;

    uint32_t sig = 2166136261UL;
    sig = fnv1a(sig, adv["title"] | "");
    sig = fnv1a(sig, adv["priority"] | "");
    sig = fnv1a(sig, adv["publish_date"] | "");
    sig = fnv1a(sig, adv["expiration_date"] | "");
    sig = fnv1a(sig, adv["description"] | "");

    bool known = false;
    int freeSlot = -1;
    for (int i = 0; i < MAX_WARN_WATCH; i++) {
      if (warnWatched[i].used && warnWatched[i].warningId == wid) {
        if (warnWatched[i].signature == sig) { known = true; break; }
        freeSlot = i;
        break;
      }
      if (!warnWatched[i].used && freeSlot < 0) freeSlot = i;
    }
    if (known) continue;
    if (freeSlot < 0) freeSlot = 0;

    char payload[LOAM_MAX_PAYLOAD + 1];
    size_t n = buildWarnPayload(adv, payload, sizeof(payload));
    if (!n) continue;

    if (meshSend(T_WARN, 0, payload, n, 200 + random(300))) {
      warnWatched[freeSlot].warningId = wid;
      warnWatched[freeSlot].signature = sig;
      warnWatched[freeSlot].used = true;
      Serial.printf("[warn] downlink id=%d prio=%s\n", wid, prio);
      reportWarningDelivery(wid, "gateway_accepted");
    }
  }
}

// A heartbeat so buoys can tell "the shore is quiet" from "the shore is gone",
// and so a buoy that booted with no clock gets one without waiting for someone
// to send an SOS.
void sendBeacon() {
  JsonDocument doc;
  doc["v"] = 1;
  if (clockValid()) doc["now"] = (uint32_t)time(nullptr);
  doc["net"] = online();
  char payload[LOAM_MAX_PAYLOAD + 1];
  size_t n = serializeJson(doc, payload, sizeof(payload));
  if (n) meshSend(T_PING, 0, payload, n);
}

// ===========================================================================
// Mesh receive — the one place inbound frames are interpreted
//
// No meshRelay() anywhere below: gateways never re-transmit.
// ===========================================================================

void onMeshFrame(const uint8_t* raw, size_t total, const LoamFrame& f) {
  if (f.src == NODE_ID) return;   // our own frame, echoed by a relay

  lastMeshRx   = millis();
  lastMeshRssi = f.rssi;
  lastMeshSnr  = f.snr;

  bool dup = seenBefore(f.src, f.seq, f.type);
  if (!dup) seenRemember(f.src, f.seq, f.type);

  JsonDocument p;
  bool parsed = f.len && !deserializeJson(p, f.payload, f.len);

  if (parsed && p["now"].is<uint32_t>()) adoptClock(p["now"]);

  if (dup) return;

  Serial.printf("[lora] rx type=0x%02X src=0x%08lX seq=%u hops=%u rssi=%.0f\n",
                f.type, (unsigned long)f.src, f.seq, f.hops, f.rssi);

  switch (f.type) {

    case T_SOS: {
      if (!parsed) break;
      const char* vid = p["vid"] | "";
      if (!vid[0]) break;
      watchVessel(vid);

      if (postSos(p, f.src, f.seq)) {
        // Mesh-level ACK, addressed by (src, seq) exactly as the spec defines.
        // It is sent only after the backend has the SOS, so the buoy's queue
        // clears on delivery rather than on transmission.
        JsonDocument a;
        a["v"]   = 1;
        a["ok"]  = true;
        a["src"] = f.src;
        a["seq"] = f.seq;
        if (clockValid()) a["now"] = (uint32_t)time(nullptr);
        char payload[LOAM_MAX_PAYLOAD + 1];
        size_t n = serializeJson(a, payload, sizeof(payload));
        if (n) meshSend(T_ACK, F_ACK, payload, n, random(300));
      } else {
        // No ack. The originating buoy keeps the SOS and keeps retrying, which
        // is the correct outcome when this gateway has lost its own uplink.
        Serial.println("[sos] not delivered - withholding ack");
      }
      break;
    }

    case T_CHAT: {
      if (!parsed) break;
      const char* from = p["from"] | "?";
      const char* text = p["text"] | "";
      if (!text[0]) break;
      postChat(from, text);
      break;
    }

    case T_ACK:
    case T_ETA:
    case T_PING:
    case T_STATUS:
      // Frames this gateway originates, heard back off a relay, or status
      // traffic it has nothing to do with. Nothing to act on and nothing to
      // forward.
      break;

    default:
      break;   // unknown type: dropped
  }
}

// ---------------------------------------------------------------------------
// OLED
// ---------------------------------------------------------------------------

void oledDraw() {
  if (!oledReady) return;
  oledHeader();

  oled.setCursor(0, 14);
  oled.print(F("Role : shore gateway"));

  oled.setCursor(0, 26);
  oled.print(F("Net  : "));
  oled.print(online() ? F("online") : F("offline"));

  oled.setCursor(0, 38);
  oled.print(F("LoRa : "));
  if (lastMeshRx) {
    oled.print((int)lastMeshRssi);
    oled.print(F("dBm "));
    oled.print((millis() - lastMeshRx) / 1000);
    oled.print(F("s"));
  } else {
    oled.print(radioReady ? F("listening") : F("radio!"));
  }

  oled.setCursor(0, 50);
  oled.print(F("Ack  : "));
  if (!GATEWAY_API_KEY[0])      oled.print(F("no key"));
  else if (lastAckHttp == 200)  oled.print(F("armed"));
  else if (lastAckHttp == 0)    oled.print(F("waiting"));
  else                        { oled.print(F("http ")); oled.print(lastAckHttp); }

  // ":>" in the bottom-right corner. At text size 1 a glyph is 6x8, so two
  // characters start 12px in from the right edge and clear the text on that
  // line, which never reaches that far.
  oled.setCursor(OLED_W - 12, 50);
  oled.print(F(":>"));

  oled.display();
}

// ---------------------------------------------------------------------------

unsigned long lastDisplay  = 0;
unsigned long lastPoll     = 0;
unsigned long lastChatPoll = 0;
unsigned long lastBeacon   = 0;
unsigned long lastWarnPoll = 0;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== AqOne shore gateway " + String(NODE_NAME) + " ===");

  oledSetup();
  meshSeqInit();
  memset(seenRing, 0, sizeof(seenRing));
  memset(txRing, 0, sizeof(txRing));

  // Seeded off the MAC so two boards powered from the same switch do not pick
  // identical backoffs forever and collide on every single flood.
  randomSeed((uint32_t)ESP.getEfuseMac());

  setupWiFi();

  radioReady = radioSetup();
  if (!radioReady) {
    // Fatal in practice: a gateway that cannot hear the mesh is a gateway with
    // nothing to forward. Said plainly here because the OLED's "radio!" line
    // is the only other place it shows.
    Serial.println("[lora] RADIO DOWN - this gateway will forward nothing");
  }

  watchLoad();
  int open = 0;
  for (int i = 0; i < MAX_VESSELS; i++) if (watched[i].used) open++;
  Serial.printf("[boot] shore gateway ready. %d vessel(s) recovered from flash\n", open);
}

void loop() {
  radioService();

  unsigned long now = millis();

  if (now - lastDisplay > 500) {
    lastDisplay = now;
    oledDraw();
  }

  if (now - lastBeacon > BEACON_EVERY_MS) {
    lastBeacon = now;
    if (radioReady) sendBeacon();
  }

  // 45 s: fast enough that a dispatcher's ETA reaches the boat while it still
  // means something, slow enough to stay well inside a sane request rate.
  if (now - lastPoll > 45000) {
    lastPoll = now;
    pollAcks();
  }

  if (now - lastChatPoll > 20000) {
    lastChatPoll = now;
    pollChat();
  }

  if (now - lastWarnPoll > 60000) {
    lastWarnPoll = now;
    pollWarnings();
  }

  // Reconnect the uplink if it drops.
  if (WiFi.status() != WL_CONNECTED && now % 30000 < 50) {
    WiFi.begin(UPLINK_SSID, UPLINK_PASS);
  }
  if (WiFi.status() == WL_CONNECTED) uplinkUp = true;
}
