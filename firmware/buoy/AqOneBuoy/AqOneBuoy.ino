// AqOneBuoy.ino — Heltec WiFi LoRa 32 V3 (ESP32-S3)
//
// THE BUOY. The board that floats, that the phones connect to, that has no
// internet of its own. Its partner is firmware/shore/AqOneShore — flash that
// one to the board with the hotspot.
//
//   phone --WiFi--> THIS BOARD --LoRa--> (relay buoys) --LoRa--> shore --> API
//   phone <--WiFi-- THIS BOARD <--LoRa-- (relay buoys) <--LoRa-- shore <-- API
//
// Three jobs:
//   1. WiFi access point for fishers' phones      (the "Aquan" network)
//   2. Chat hub between phones, and onto the mesh
//   3. SOS gateway: phone -> radio -> shore -> backend -> dashboard, and the
//      dispatcher's ETA back down
//
// It also relays other buoys' frames, which is the whole reason the mesh
// exists: the boat that can reach shore is rarely the boat in trouble.
//
// The chat and SOS protocols are unchanged from what mobile/ already speaks,
// so the Flutter app needs no changes.
//
// ---------------------------------------------------------------------------
// THE ONE THING THAT WILL BITE YOU
//
// The radio settings and the HMAC key in AqOneLoam.h must be IDENTICAL to the
// shore board's copy of that file. A mismatch in frequency, spreading factor,
// bandwidth, coding rate, sync word or key behaves exactly like being out of
// range: no error, no log line, nothing arrives. After editing either copy:
//
//   diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
//
// It must print nothing.
// ---------------------------------------------------------------------------

// ===== IDENTITY — change this per board ====================================
//
// NODE_ID is the on-air identity: SRC_ID in the LoAM frame, and `src_id` on the
// dashboard's mesh trail. It must be unique across the whole deployment — two
// nodes sharing an id make the seen-set drop one of them as a duplicate, which
// at the console is indistinguishable from a dead radio.
//
// BUOY01 = 0x00010001, BUOY02 = 0x00010002, and so on.

#define AQONE_NODE_ID   0x00010001
#define AQONE_NODE_NAME "BUOY01"

// ===========================================================================

#include <WiFi.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <DNSServer.h>

// Built-in 128x64 SSD1306 OLED on the Heltec WiFi LoRa 32 V3.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// The shared radio layer: frame format, signing, seen-set, TX ring, SX1262
// driver, clock, OLED bring-up. Must come AFTER the two defines above.
#include "AqOneLoam.h"

// ===== CONFIGURE ME ========================================================

// OPEN network — no password, by design.
//
// A person in distress cannot be asked for a WiFi password. The same reasoning
// already governs fisherman identity in the app (device-local id, no login):
// anything standing between a drowning person and the SOS button is a
// liability, not a security feature.
//
// Every buoy advertises the SAME SSID, so a phone roams between them
// automatically as the boat moves — the way it would between office access
// points. Which buoy you are actually on comes from GET /v1/status. Do not
// encode the buoy id in the SSID or roaming breaks.
static const char* AP_SSID     = "Aquan";
static const char* AP_PASSWORD = nullptr;   // nullptr => open network

// This board never joins another network, so nothing can push its AP onto a
// different channel mid-trip. Pick a channel and keep neighbouring buoys off
// it if you can; phones roam by SSID, not by channel.
static const int AP_CHANNEL = 6;

// An open AP is joinable by anyone in range, not just fishers. Accepted
// trade-off: the worst case is a spurious SOS, which a dispatcher can resolve
// in seconds. The alternative failure — a real SOS that never sends because
// someone forgot a password — is not recoverable.
static const int MAX_AP_CLIENTS = 10;

// The WebSockets library sizes its client table at compile time and defaults
// to 5 - half the AP's capacity. Boats 6 through 10 would associate, get the
// portal, and then silently never reach chat.
//
// It cannot be raised with a #define here: WebSocketsServer holds its client
// array by value in the header, so a value set only in this sketch would give
// the library's own .cpp a different object layout - corruption, not a bigger
// table. The flag has to reach every translation unit, which is what the
// build_opt.h beside this sketch does. If that file is not being picked up,
// this assert stops the build instead of letting a 5-boat cap ship quietly.
static_assert(
    WEBSOCKETS_SERVER_CLIENT_MAX >= MAX_AP_CLIENTS,
    "WEBSOCKETS_SERVER_CLIENT_MAX is below MAX_AP_CLIENTS. build_opt.h in this "
    "sketch folder sets it; see firmware/README.md if your IDE is not reading "
    "that file.");

// ===========================================================================

static const uint16_t HTTP_PORT = 80;
static const uint16_t WS_PORT   = 81;

WebServer        http(HTTP_PORT);
WebSocketsServer ws(WS_PORT);
DNSServer        dns;

// True when a frame handed to this buoy has a live path to shore right now.
bool meshUp() { return shoreSeen() && (millis() - lastShoreHeard) < MESH_STALE_MS; }

// ---------------------------------------------------------------------------
// Store-and-forward queue
//
// An SOS accepted from a phone must survive a brown-out. Solar plus an 18650
// means this board WILL lose power mid-delivery, and an SOS held only in RAM
// dies silently. Queue entries live in NVS until the SHORE acknowledges them
// over LoRa — not until they are transmitted. A transmitted frame nobody heard
// is not a delivered frame, and the difference is the whole point of the queue.
// ---------------------------------------------------------------------------

static const int MAX_QUEUE = 12;

struct SosItem {
  char     vesselId[33];
  char     boat[33];
  char     note[65];
  char     trust[20];
  double   lat;
  double   lon;
  uint32_t clientTs;
  uint32_t seq;        // app-facing counter, shown to the fisher

  // Frame SEQs of the last few transmissions, matched against an incoming
  // ACK. A RETRY MUST USE A FRESH SEQ or every relay's seen-set drops it as
  // a duplicate - so by the time the shore's ack for attempt N arrives, the
  // buoy may already be on attempt N+1. Matching only the newest seq would
  // discard that ack and keep retransmitting an SOS the backend already has.
  uint16_t meshSeq[4];
  uint8_t  meshSeqAt;

  uint8_t  attempts;
  bool     hasFix;
  bool     used;
};

SosItem  queueBuf[MAX_QUEUE];
uint32_t nextSeq = 1;
uint32_t queueRetryAt[MAX_QUEUE];   // RAM only: a reboot retries immediately

void queueSave() {
  prefs.begin("aqone", false);
  prefs.putBytes("queue", queueBuf, sizeof(queueBuf));
  prefs.putUInt("seq", nextSeq);
  prefs.end();
}

void queueLoad() {
  prefs.begin("aqone", true);
  size_t n = prefs.getBytesLength("queue");
  // A size mismatch means the struct changed across a firmware update. Zeroing
  // is the only safe read — reinterpreting old bytes would produce a plausible
  // looking SOS with a corrupt vessel_id.
  if (n == sizeof(queueBuf)) prefs.getBytes("queue", queueBuf, sizeof(queueBuf));
  else memset(queueBuf, 0, sizeof(queueBuf));
  nextSeq = prefs.getUInt("seq", 1);
  prefs.end();
  memset(queueRetryAt, 0, sizeof(queueRetryAt));
}

int queueFreeSlot() {
  for (int i = 0; i < MAX_QUEUE; i++) if (!queueBuf[i].used) return i;
  return -1;
}

int queueDepth() {
  int n = 0;
  for (int i = 0; i < MAX_QUEUE; i++) if (queueBuf[i].used) n++;
  return n;
}

// ---------------------------------------------------------------------------
// SOS payload
//
// Degrades rather than fails. A frame that will not fit sheds optional fields;
// a distress call with fields missing is still a rescue, and one that did not
// fit is not.
// ---------------------------------------------------------------------------

size_t buildSosPayload(const SosItem& it, char* out, size_t cap) {
  for (int attempt = 0; attempt < 3; attempt++) {
    JsonDocument doc;
    doc["v"]    = 1;
    // No "kind" here any more, matching the ETA payload: TYPE 0x01 in the
    // authenticated header already says this is an SOS, and nothing on either
    // board or in the backend ever read the field - it was 13 bytes of pure
    // restatement in the tightest payload in the system. Reclaiming them is
    // what pays for "sq" below without pushing the fisher's note down the
    // shedding ladder.
    doc["vid"]  = it.vesselId;
    doc["ts"]   = it.clientTs;
    doc["bid"]  = NODE_NAME;
    // The handset's matching key, and the reason it is above the shedding
    // ladder rather than in it.
    //
    // A LoRa frame has no room for the local_id a phone would otherwise be
    // matched on, so when the dispatcher's answer comes back down the app
    // pairs it to the right outbox record by seq alone
    // (mobile/lib/services/sos_service.dart _applyRemote). That is THIS
    // number - the value handlePostSos() already returned to the phone - not
    // the mesh frame seq, which rotates on every retry by design. Shedding it
    // would deliver an acknowledgement the fisher never sees.
    doc["sq"]   = it.seq;
    if (it.trust[0]) doc["tt"] = it.trust;
    // Omit lat/lon entirely when there is no fix. Never send 0,0 — that is a
    // real location in the Gulf of Guinea and it would be plotted as one.
    if (it.hasFix) { doc["lat"] = it.lat; doc["lon"] = it.lon; }
    // Shedding order: the BOAT NAME goes first, the note last.
    //
    // This looks backwards and is not. The boat name is already in the vessels
    // table from registration and the backend looks it up by vessel_id -
    // `payload.boat or payload.vessel_id` in sos.py, and the INSERT COALESCEs
    // it - so a dropped boat name costs the dispatcher nothing. The fisher's
    // note exists nowhere else on earth. "taking water" and "engine dead" send
    // different boats; losing that to save a name the database already has
    // would be the wrong trade.
    //
    // Not hypothetical: vessel_id is ALWAYS 32 chars, so a full boat name plus
    // a 64-char note is 255 bytes of JSON and WILL shed the name.
    if (attempt < 1 && it.boat[0]) doc["boat"] = it.boat;
    if (attempt < 2 && it.note[0]) doc["n"] = it.note;

    size_t n = serializeJson(doc, out, cap);
    if (n > 0 && n <= LOAM_MAX_PAYLOAD) {
      if (attempt > 0)
        Serial.printf("[sos] %s trimmed to fit a frame (pass %d)\n",
                      it.vesselId, attempt);
      return n;
    }
  }
  return 0;
}

// ---------------------------------------------------------------------------
// Responder acknowledgement cache — the return path
//
// The dispatcher acknowledges on the dashboard with an ETA. The backend turns
// that into an absolute eta_at. The shore gateway reads it and pushes an ETA
// frame onto the mesh; every buoy that hears it caches it, whether or not the
// SOS came through that particular buoy — a boat drifts, and the phone that
// needs the answer may well have roamed onto a different buoy by then.
//
// Fields are stored structurally and the JSON is rendered on request. An older
// firmware cached the backend's response body in a fixed 320-byte buffer and
// could truncate it mid-JSON; mobile/lib/services/buoy_client.dart still
// carries a BuoyInvalidResponse path for exactly that. Nothing here can
// produce a truncated body any more, but keep that client-side guard: a buoy
// running older firmware still can.
// ---------------------------------------------------------------------------

static const int MAX_TRACKED = 8;

static const int RESPONDER_STATUS_MIN = 1;
static const int RESPONDER_STATUS_MAX = 5;

// Mirrors RESPONDER_STATUS_LABELS in backend/app/api/sos.py. Kept here rather
// than sent over the air: the label is up to 24 bytes of airtime per frame to
// carry a value fully determined by a single integer. If the backend table
// changes, change this one too.
const char* responderLabel(int status) {
  switch (status) {
    case 1: return "MDRRMO has your call";
    case 2: return "Rescue boat on the way";
    case 3: return "Coast Guard notified";
    case 4: return "Nearby boats alerted";
    case 5: return "Delayed - still coming";
    default: return nullptr;
  }
}

struct Tracked {
  char     vesselId[33];
  bool     used;

  bool     hasEta;
  int32_t  eventId;
  char     state[16];      // relayed | delivered | acknowledged
  int32_t  eventSeq;
  uint32_t clientTs;
  uint32_t ackedAt;
  uint32_t etaAt;
  uint32_t resolvedAt;
  int8_t   responderStatus;
  char     ackedBy[24];
  char     note[49];
};

Tracked tracked[MAX_TRACKED];

Tracked* trackFind(const char* vesselId) {
  for (int i = 0; i < MAX_TRACKED; i++)
    if (tracked[i].used && strcmp(tracked[i].vesselId, vesselId) == 0)
      return &tracked[i];
  return nullptr;
}

Tracked* trackVessel(const char* vesselId) {
  Tracked* t = trackFind(vesselId);
  if (t) return t;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (tracked[i].used) continue;
    memset(&tracked[i], 0, sizeof(Tracked));
    strncpy(tracked[i].vesselId, vesselId, 32);
    tracked[i].responderStatus = -1;
    tracked[i].used = true;
    return &tracked[i];
  }
  return nullptr;
}

// ---------------------------------------------------------------------------
// Chat history
//
// A phone that joins mid-trip should see what was already said. The last
// MAX_HISTORY lines live in RAM only: chat is conversation, not distress
// traffic, and it is not worth the flash wear that the SOS queue earns. A
// reboot loses the backlog, and that is the right trade.
// ---------------------------------------------------------------------------

static const int MAX_HISTORY = 20;

struct ChatLine {
  char   from[33];
  char   text[65];
  time_t at;        // 0 when the buoy had no clock; see clockValid()
  bool   used;
};

ChatLine history[MAX_HISTORY];
int      historyHead = 0;   // next slot to write == oldest line once wrapped

void historyAdd(const char* from, const char* text) {
  ChatLine& line = history[historyHead];
  memset(&line, 0, sizeof(line));
  strncpy(line.from, from, sizeof(line.from) - 1);
  strncpy(line.text, text, sizeof(line.text) - 1);
  line.at   = clockValid() ? time(nullptr) : 0;
  line.used = true;
  historyHead = (historyHead + 1) % MAX_HISTORY;
}

// ---------------------------------------------------------------------------
// Cached warnings (Task 2.5)
// ---------------------------------------------------------------------------

struct CachedWarning {
  int      id;
  char     src[16];
  char     priority[16];
  char     area[24];
  char     title[49];
  char     description[81];
  uint32_t publishDate;
  uint32_t expirationDate;
  bool     used;
};

static const int MAX_CACHED_WARNINGS = 6;
CachedWarning cachedWarnings[MAX_CACHED_WARNINGS];

// ---------------------------------------------------------------------------
// WiFi — access point only.
//
// An older build ran AP+STA and had to bring the station link up first so the
// AP would land on the same channel, kicking every connected phone when it
// did. With LoRa carrying the uplink there is no station link, so that entire
// failure mode is gone.
// ---------------------------------------------------------------------------

void setupWiFi() {
  WiFi.mode(WIFI_AP);

  // Open AP: passing nullptr as the password is what makes it open. The extra
  // args are (channel, hidden=0, maxConnections).
  WiFi.softAP(AP_SSID, AP_PASSWORD, AP_CHANNEL, 0, MAX_AP_CLIENTS);
  Serial.printf("[wifi] OPEN AP '%s' up on %s ch=%d max=%d\n",
                AP_SSID, WiFi.softAPIP().toString().c_str(),
                AP_CHANNEL, MAX_AP_CLIENTS);

  // Captive-portal DNS: every hostname resolves to the buoy. Without this,
  // phones that try to reach a name before we answer their connectivity probe
  // will fail and may drop the network.
  dns.start(53, "*", WiFi.softAPIP());
}

// ---------------------------------------------------------------------------
// SOS delivery over LoRa
//
// Retry until the shore acknowledges. Backoff widens so a buoy that is out of
// range of everything does not hold the channel, but it never gives up:
// docs/19 is explicit that a queued distress frame retries until it is
// acknowledged or the board dies.
// ---------------------------------------------------------------------------

static const uint32_t SOS_RETRY_MS[]  = { 8000, 15000, 30000, 60000, 120000 };
static const int      SOS_RETRY_STEPS = sizeof(SOS_RETRY_MS) / sizeof(SOS_RETRY_MS[0]);

void sosTransmit(int slot) {
  SosItem& it = queueBuf[slot];

  char payload[LOAM_MAX_PAYLOAD + 1];
  size_t n = buildSosPayload(it, payload, sizeof(payload));
  if (!n) {
    Serial.printf("[sos] %s cannot be encoded - dropping\n", it.vesselId);
    it.used = false;
    queueSave();
    return;
  }

  it.meshSeq[it.meshSeqAt % 4] = meshSeq;   // the SEQ meshSend will consume
  it.meshSeqAt++;
  if (!meshSend(T_SOS, F_WANTS_ACK, payload, n)) {
    // The TX ring was full - transient, and not this SOS's fault. Come back
    // shortly without burning a retry step, or the backoff ladder would widen
    // for a reason that has nothing to do with whether anyone is listening.
    queueRetryAt[slot] = millis() + 2000;
    return;
  }

  if (it.attempts < 250) it.attempts++;
  int step = it.attempts - 1;
  if (step >= SOS_RETRY_STEPS) step = SOS_RETRY_STEPS - 1;
  if (step < 0) step = 0;
  queueRetryAt[slot] = millis() + SOS_RETRY_MS[step] + random(3000);

  Serial.printf("[sos] tx %s seq=%u frame=%u attempt=%u\n",
                it.vesselId, it.seq, it.meshSeq[(it.meshSeqAt - 1) % 4], it.attempts);
  queueSave();
}

void flushQueue() {
  uint32_t now = millis();
  for (int i = 0; i < MAX_QUEUE; i++) {
    if (!queueBuf[i].used) continue;
    if (queueRetryAt[i] && (int32_t)(now - queueRetryAt[i]) < 0) continue;
    sosTransmit(i);
    return;   // one distress frame per tick; the flood needs room to answer
  }
}

// ---------------------------------------------------------------------------
// HTTP routes served to phones on the AP
// ---------------------------------------------------------------------------

// POST /v1/sos — what the Flutter app calls over the buoy's WiFi.
// We answer immediately. Delivery to the mesh happens right after.
// Blocking the reply on a LoRa round trip would leave a person in distress
// staring at a spinner for a second and a half.
void handlePostSos() {
  if (!http.hasArg("plain")) {
    http.send(400, "application/json", "{\"error\":\"empty body\"}");
    return;
  }

  JsonDocument in;
  if (deserializeJson(in, http.arg("plain"))) {
    http.send(400, "application/json", "{\"error\":\"bad json\"}");
    return;
  }

  const char* vesselId = in["vessel_id"] | "";
  uint32_t    clientTs = in["client_ts"] | 0;
  if (!vesselId[0] || clientTs == 0) {
    http.send(422, "application/json",
              "{\"error\":\"vessel_id and client_ts are required\"}");
    return;
  }

  // Same emergency handed to us twice - the app retrying, or the fisher
  // pressing again - is one queue entry, not two. (vessel_id, client_ts) is
  // the backend's de-duplication key; applying it here too saves the airtime.
  for (int i = 0; i < MAX_QUEUE; i++) {
    if (queueBuf[i].used && queueBuf[i].clientTs == clientTs &&
        strcmp(queueBuf[i].vesselId, vesselId) == 0) {
      JsonDocument dup;
      dup["accepted"]  = true;
      dup["buoy_id"]   = NODE_NAME;
      dup["src_id"]    = NODE_ID;
      dup["seq"]       = queueBuf[i].seq;
      dup["server_ts"] = clockValid() ? (uint32_t)time(nullptr)
                                      : (uint32_t)(millis() / 1000);
      String body;
      serializeJson(dup, body);
      http.send(200, "application/json", body);
      return;
    }
  }

  int slot = queueFreeSlot();
  if (slot < 0) {
    http.send(503, "application/json", "{\"error\":\"queue full\"}");
    return;
  }

  SosItem& it = queueBuf[slot];
  memset(&it, 0, sizeof(it));
  strncpy(it.vesselId, vesselId,                           32);
  strncpy(it.boat,     in["boat"] | "",                    32);
  strncpy(it.note,     in["note"] | "",                    64);
  strncpy(it.trust,    in["trust_tier"] | "self_declared", 19);
  it.clientTs = clientTs;
  it.seq      = nextSeq++;
  it.hasFix   = in["lat"].is<double>() && in["lon"].is<double>();
  if (it.hasFix) { it.lat = in["lat"]; it.lon = in["lon"]; }
  it.used = true;
  queueRetryAt[slot] = 0;
  queueSave();

  trackVessel(vesselId);

  JsonDocument out;
  out["accepted"]  = true;
  out["buoy_id"]   = NODE_NAME;
  out["src_id"]    = NODE_ID;
  out["seq"]       = it.seq;
  out["server_ts"] = clockValid() ? (uint32_t)time(nullptr)
                                  : (uint32_t)(millis() / 1000);
  String body;
  serializeJson(out, body);
  http.send(200, "application/json", body);

  Serial.printf("[sos] queued %s seq=%u depth=%d\n",
                vesselId, it.seq, queueDepth());

  // Straight onto the radio. The 5-second tick is the retry path, not the
  // first-attempt path — an SOS should not wait on a timer.
  sosTransmit(slot);
}

// GET /v1/sos/status?vessel_id=... — the ETA the dispatcher sent back.
//
// Shape matches GET /api/sos/vessel/{id} exactly, because the app parses both
// with the same RemoteSos.fromJson. Reconstructed from the ETA frame's fields
// rather than proxied, since the full backend body does not fit in a LoRa
// packet and never will.
void handleGetSosStatus() {
  String vid = http.arg("vessel_id");

  JsonDocument doc;
  doc["vessel_id"] = vid;
  if (clockValid()) doc["server_time"] = isoUtc(time(nullptr));
  JsonArray events = doc["events"].to<JsonArray>();

  Tracked* t = trackFind(vid.c_str());
  if (t && t->hasEta) {
    JsonObject e = events.add<JsonObject>();
    e["id"]       = t->eventId;
    e["local_id"] = nullptr;   // a LoRa frame has no room for a UUID
    if (t->eventSeq >= 0) e["seq"] = t->eventSeq;
    if (t->clientTs)      e["client_ts"] = t->clientTs;
    e["delivery_state"]   = t->state;
    // Explicit nulls, not omissions: RemoteSos.fromJson reads every one of
    // these keys, and an absent key and a null key must look the same to it.
    if (t->ackedAt)    e["acknowledged_at"] = isoUtc(t->ackedAt);
    else               e["acknowledged_at"] = nullptr;
    if (t->ackedBy[0]) e["acked_by"] = t->ackedBy;
    else               e["acked_by"] = nullptr;
    if (t->etaAt)      e["eta_at"] = isoUtc(t->etaAt);
    else               e["eta_at"] = nullptr;
    if (t->responderStatus >= RESPONDER_STATUS_MIN &&
        t->responderStatus <= RESPONDER_STATUS_MAX) {
      e["responder_status"]       = t->responderStatus;
      e["responder_status_label"] = responderLabel(t->responderStatus);
    } else {
      e["responder_status"]       = nullptr;
      e["responder_status_label"] = nullptr;
    }
    if (t->note[0])    e["responder_note"] = t->note;
    else               e["responder_note"] = nullptr;
    e["fisher_reply"]  = nullptr;   // the reply path is not on the mesh yet
    if (t->resolvedAt) e["resolved_at"] = isoUtc(t->resolvedAt);
    else               e["resolved_at"] = nullptr;
  }

  String body;
  serializeJson(doc, body);
  http.send(200, "application/json", body);
}

// GET /v1/status — buoy health, so the app can show "connected to BUOY01".
//
// `uplink` reports the MESH, not an internet connection this board does not
// have: true means a frame handed to this buoy has a live path to shore right
// now. That is the question the app's copy actually asks ("an SOS sent now
// will reach the rescue centre"), and docs/06_DELIVERY_STATES.md requires the
// buoy to report mesh ok/degraded rather than claiming anything was "sent".
void handleStatus() {
  JsonDocument doc;
  doc["buoy_id"]     = NODE_NAME;
  doc["role"]        = "buoy";
  doc["src_id"]      = NODE_ID;
  doc["uplink"]      = meshUp();
  doc["mesh"]        = meshUp() ? "ok" : "degraded";
  doc["queue_depth"] = queueDepth();
  doc["clients"]     = WiFi.softAPgetStationNum();
  doc["uptime_s"]    = millis() / 1000;
  doc["lora"]        = radioReady;
  doc["shore_seen"]  = shoreSeen();
  if (lastMeshRx) {
    doc["last_rx_age_s"] = (millis() - lastMeshRx) / 1000;
    doc["rssi"]          = lastMeshRssi;
    doc["snr"]           = lastMeshSnr;
  }
  String body;
  serializeJson(doc, body);
  http.send(200, "application/json", body);
}

// GET /history — the Flutter chat page backfills from here on connect.
//
// The shape is {"messages":[...]}, which is what the app parses.
//
// `time` is omitted rather than faked when the buoy has no clock. The app
// falls back to arrival time for those, which is honest: we genuinely do not
// know when the line was said, and stamping 1970 on it would sort the whole
// backlog out of the app's 24-hour retention window.
void handleHistory() {
  JsonDocument doc;
  JsonArray arr = doc["messages"].to<JsonArray>();
  for (int i = 0; i < MAX_HISTORY; i++) {
    const ChatLine& line = history[(historyHead + i) % MAX_HISTORY];
    if (!line.used) continue;
    JsonObject entry = arr.add<JsonObject>();
    entry["from"] = line.from;
    entry["text"] = line.text;
    if (line.at > 0) entry["time"] = isoUtc(line.at);
  }
  String body;
  serializeJson(doc, body);
  http.send(200, "application/json", body);
}

// GET /v1/warnings — offline handsets read active unexpired advisories/warnings here.
void handleGetWarnings() {
  JsonDocument doc;
  JsonArray arr = doc["advisories"].to<JsonArray>();

  uint32_t nowEpoch = clockValid() ? (uint32_t)time(nullptr) : 0;
  for (int i = 0; i < MAX_CACHED_WARNINGS; i++) {
    if (!cachedWarnings[i].used) continue;
    if (nowEpoch > 0 && cachedWarnings[i].expirationDate > 0 && nowEpoch > cachedWarnings[i].expirationDate) {
      cachedWarnings[i].used = false;
      continue;
    }
    JsonObject w = arr.add<JsonObject>();
    w["id"] = cachedWarnings[i].id;
    w["title"] = cachedWarnings[i].title;
    w["priority"] = cachedWarnings[i].priority;
    w["municipality"] = cachedWarnings[i].area;
    w["description"] = cachedWarnings[i].description;
    w["source"] = cachedWarnings[i].src;
    if (cachedWarnings[i].publishDate) w["publish_date"] = isoUtc(cachedWarnings[i].publishDate);
    if (cachedWarnings[i].expirationDate) w["expiration_date"] = isoUtc(cachedWarnings[i].expirationDate);
  }

  String body;
  serializeJson(doc, body);
  http.send(200, "application/json", body);
}

// ---------------------------------------------------------------------------
// Connectivity probes — the thing that makes or breaks an open network
//
// Android, iOS and Windows all fetch a known URL right after joining a WiFi
// network to decide whether it has real internet. If that probe fails, Android
// shows "no internet" and will happily keep routing traffic over mobile data —
// or drop the network entirely to reconnect to something better.
//
// For a buoy at sea that is fatal: the phone leaves the only network that can
// carry its SOS. Answering the probes correctly is not cosmetic.
//
// The probe answer is tied to the MESH, not to an IP route. This board does
// not route packets to the internet and never will, but it does carry a
// message to shore and back, which is what the probe is standing in for here.
// When the mesh is degraded we answer with a redirect instead, so the phone
// pops the captive-portal page — which states plainly what is and is not
// working — rather than silently leaving the network.
// ---------------------------------------------------------------------------

void handleGenerate204() {
  if (meshUp()) {
    http.send(204, "text/plain", "");
  } else {
    http.sendHeader("Location", "http://192.168.4.1/portal", true);
    http.send(302, "text/plain", "");
  }
}

void handleNcsi() {
  if (meshUp()) {
    // Windows compares this string byte-for-byte.
    http.send(200, "text/plain", "Microsoft NCSI");
  } else {
    http.sendHeader("Location", "http://192.168.4.1/portal", true);
    http.send(302, "text/plain", "");
  }
}

// The page a fisher sees if they open a browser on the buoy's network.
void handlePortal() {
  String page =
    "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<style>body{font-family:system-ui;background:#0b1220;color:#e2e8f0;"
    "margin:0;padding:28px;line-height:1.55}"
    "h1{font-size:20px;margin:0 0 4px}.b{font-size:13px;color:#94a3b8}"
    "     .s{margin-top:18px;padding:12px;border-radius:8px;"
    "background:rgba(34,197,94,.12);border:1px solid #22c55e}"
    ".w{margin-top:18px;padding:12px;border-radius:8px;"
    "background:rgba(245,158,11,.12);border:1px solid #f59e0b}</style>"
    "<h1>AqOne &mdash; " + String(NODE_NAME) + "</h1>"
    "<div class=b>You are connected to an AqOne safety buoy.</div>";

  page += meshUp()
    ? "<div class=s><b>Radio link to shore is up.</b><br>An SOS sent from the "
      "AqOne app will reach the rescue centre now.</div>"
    : "<div class=w><b>Radio link to shore is down.</b><br>You can still send "
      "an SOS &mdash; this buoy will hold it and keep retrying automatically "
      "until the link returns.</div>";

  page += "<div class=b style='margin-top:18px'>Open the AqOne app to send an "
          "SOS or message nearby boats.</div>";
  http.send(200, "text/html", page);
}

// ---------------------------------------------------------------------------
// Chat WebSocket — same message shapes the Flutter client already sends
// ---------------------------------------------------------------------------

// Sized to match MAX_AP_CLIENTS. WebSocketsServer indexes clients by `num`,
// so an undersized array here silently drops names off the roster for the
// last phones to join - which on an open network is exactly the boats that
// arrived most recently.
String clientNames[MAX_AP_CLIENTS];

void broadcastClients() {
  JsonDocument doc;
  doc["type"] = "clients";
  JsonArray list = doc["list"].to<JsonArray>();
  for (int i = 0; i < MAX_AP_CLIENTS; i++)
    if (clientNames[i].length()) list.add(clientNames[i]);
  String out;
  serializeJson(doc, out);
  ws.broadcastTXT(out);
}

// A line that arrived over the radio, shown to every phone on this buoy.
void chatDeliverLocal(const char* from, const char* text) {
  historyAdd(from, text);
  JsonDocument out;
  out["type"] = "msg";
  out["from"] = from;
  out["text"] = text;
  String s;
  serializeJson(out, s);
  ws.broadcastTXT(s);
}

void onWsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_DISCONNECTED) {
    if (num < MAX_AP_CLIENTS) clientNames[num] = "";
    broadcastClients();
    return;
  }
  if (type != WStype_TEXT) return;

  JsonDocument in;
  if (deserializeJson(in, payload, len)) return;
  const char* kind = in["type"] | "";

  if (strcmp(kind, "hello") == 0) {
    if (num < MAX_AP_CLIENTS) clientNames[num] = String((const char*)(in["name"] | "?"));
    broadcastClients();
  } else if (strcmp(kind, "msg") == 0) {
    const char* from = in["from"] | "?";
    const char* text = in["text"] | "";
    if (!text[0]) return;

    historyAdd(from, text);

    JsonDocument out;
    out["type"] = "msg";
    out["from"] = from;
    out["text"] = text;
    String s;
    serializeJson(out, s);

    // Relay to everyone EXCEPT the phone that sent it. The app draws its own
    // message the instant the fisher hits send - it cannot wait for a round
    // trip through a buoy that may have no uplink - so broadcasting back to
    // the sender put every message on their screen twice, which reads as
    // having sent it twice. sendTXT to a slot with no client is a no-op.
    for (uint8_t i = 0; i < WEBSOCKETS_SERVER_CLIENT_MAX; i++) {
      if (i != num) ws.sendTXT(i, s);
    }

    // ...and onto the radio, so boats on other buoys and the shore database
    // see it too. Chat waits behind distress traffic by design: the delay is
    // enqueued, so a queued SOS frame goes out first.
    char frame[LOAM_MAX_PAYLOAD + 1];
    size_t n = buildChatPayload(from, text, frame, sizeof(frame));
    if (n) meshSend(T_CHAT, 0, frame, n, 300 + random(500));
  }
}

// ===========================================================================
// Mesh receive — the one place inbound frames are interpreted
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

  // Any frame from the gateway is proof the path to shore is alive, duplicate
  // or not — a duplicate still travelled the whole way here.
  //
  // Keyed on frame type rather than on a hard-coded gateway id: only the shore
  // originates these three, and a buoy that has to be told the gateway's id is
  // a buoy that stops working when the gateway is replaced.
  if (f.type == T_ACK || f.type == T_ETA || f.type == T_PING) lastShoreHeard = millis();
  if (parsed && p["now"].is<uint32_t>()) adoptClock(p["now"]);

  if (dup) return;   // seen it; relay already happened the first time

  Serial.printf("[lora] rx type=0x%02X src=0x%08lX seq=%u hops=%u rssi=%.0f\n",
                f.type, (unsigned long)f.src, f.seq, f.hops, f.rssi);

  switch (f.type) {

    case T_SOS:
      // A buoy relays distress traffic for its neighbours. This is the whole
      // reason the mesh exists: the boat that can reach shore is rarely the
      // boat in trouble.
      meshRelay(raw, total, f);
      break;

    case T_ACK: {
      if (!parsed) break;
      uint32_t ackSrc = p["src"] | 0;
      uint16_t ackSeq = (uint16_t)(p["seq"] | 0);
      bool ok = p["ok"] | false;

      if (ackSrc == NODE_ID && ok) {
        for (int i = 0; i < MAX_QUEUE; i++) {
          if (!queueBuf[i].used) continue;
          // Only slots actually written: a fresh entry is memset to zero, and
          // a rolling uint16 does eventually wrap through 0.
          int held = queueBuf[i].meshSeqAt < 4 ? queueBuf[i].meshSeqAt : 4;
          bool mine = false;
          for (int k = 0; k < held; k++)
            if (queueBuf[i].meshSeq[k] == ackSeq) { mine = true; break; }
          if (!mine) continue;

          Serial.printf("[sos] delivered %s seq=%u after %u attempt(s)\n",
                        queueBuf[i].vesselId, queueBuf[i].seq, queueBuf[i].attempts);
          queueBuf[i].used = false;
          queueRetryAt[i]  = 0;
          queueSave();
          break;
        }
      } else {
        // Someone else's ack. Pass it along — the buoy it belongs to may be a
        // hop further out than the gateway can reach.
        meshRelay(raw, total, f);
      }
      break;
    }

    case T_ETA: {
      if (!parsed) break;
      const char* vid = p["vid"] | "";
      if (!vid[0]) break;

      // Cached even when this buoy never saw the original SOS. The boat may
      // have drifted onto a different buoy since it sent the call, and the
      // phone asks whichever buoy it is on now.
      Tracked* t = trackVessel(vid);
      if (t) {
        t->hasEta  = true;
        t->eventId = p["id"] | 0;
        strncpy(t->state, p["ds"] | "delivered", sizeof(t->state) - 1);
        t->state[sizeof(t->state) - 1] = 0;
        t->eventSeq        = p["sq"].is<int>() ? (int32_t)p["sq"] : -1;
        t->clientTs        = p["cts"] | 0;
        t->ackedAt         = p["ack"] | 0;
        t->etaAt           = p["eta"] | 0;
        t->resolvedAt      = p["res"] | 0;
        t->responderStatus = p["rs"].is<int>() ? (int8_t)(int)p["rs"] : -1;
        strncpy(t->ackedBy, p["by"] | "", sizeof(t->ackedBy) - 1);
        t->ackedBy[sizeof(t->ackedBy) - 1] = 0;
        strncpy(t->note, p["n"] | "", sizeof(t->note) - 1);
        t->note[sizeof(t->note) - 1] = 0;

        // Push it straight to connected phones too, so an acknowledgement
        // lands without the app having to poll us. A fisher waiting on a
        // rescue should not depend on a refresh interval.
        JsonDocument ev;
        ev["type"]      = "sos_update";
        ev["vessel_id"] = vid;
        JsonObject d = ev["data"].to<JsonObject>();
        d["delivery_state"] = t->state;
        if (t->etaAt)      d["eta_at"]          = isoUtc(t->etaAt);
        if (t->ackedAt)    d["acknowledged_at"] = isoUtc(t->ackedAt);
        if (t->ackedBy[0]) d["acked_by"]        = t->ackedBy;
        if (t->responderStatus >= RESPONDER_STATUS_MIN &&
            t->responderStatus <= RESPONDER_STATUS_MAX) {
          d["responder_status"]       = t->responderStatus;
          d["responder_status_label"] = responderLabel(t->responderStatus);
        }
        if (t->note[0]) d["responder_note"] = t->note;
        String out;
        serializeJson(ev, out);
        ws.broadcastTXT(out);
      }
      meshRelay(raw, total, f);   // other buoys need it too
      break;
    }

    case T_WARN: {
      if (!parsed) break;
      int wid = p["id"] | 0;
      if (!wid) break;

      uint32_t expAt = p["exp"] | 0;
      if (clockValid() && expAt > 0 && (uint32_t)time(nullptr) > expAt) {
        Serial.printf("[warn] dropped expired warning id=%d\n", wid);
        break;
      }

      int slot = -1;
      for (int i = 0; i < MAX_CACHED_WARNINGS; i++) {
        if (cachedWarnings[i].used && cachedWarnings[i].id == wid) {
          slot = i;
          break;
        }
        if (!cachedWarnings[i].used && slot < 0) slot = i;
      }
      if (slot < 0) slot = 0;

      cachedWarnings[slot].id = wid;
      strncpy(cachedWarnings[slot].src, p["src"] | "MDRRMO", sizeof(cachedWarnings[slot].src) - 1);
      cachedWarnings[slot].src[sizeof(cachedWarnings[slot].src) - 1] = 0;
      strncpy(cachedWarnings[slot].priority, p["pr"] | "Warning", sizeof(cachedWarnings[slot].priority) - 1);
      cachedWarnings[slot].priority[sizeof(cachedWarnings[slot].priority) - 1] = 0;
      strncpy(cachedWarnings[slot].area, p["area"] | "All", sizeof(cachedWarnings[slot].area) - 1);
      cachedWarnings[slot].area[sizeof(cachedWarnings[slot].area) - 1] = 0;
      strncpy(cachedWarnings[slot].title, p["ttl"] | "", sizeof(cachedWarnings[slot].title) - 1);
      cachedWarnings[slot].title[sizeof(cachedWarnings[slot].title) - 1] = 0;
      strncpy(cachedWarnings[slot].description, p["txt"] | "", sizeof(cachedWarnings[slot].description) - 1);
      cachedWarnings[slot].description[sizeof(cachedWarnings[slot].description) - 1] = 0;
      cachedWarnings[slot].publishDate = p["iss"] | 0;
      cachedWarnings[slot].expirationDate = expAt;
      cachedWarnings[slot].used = true;

      JsonDocument ev;
      ev["type"] = "warning";
      JsonObject d = ev["data"].to<JsonObject>();
      d["id"] = wid;
      d["title"] = cachedWarnings[slot].title;
      d["priority"] = cachedWarnings[slot].priority;
      d["municipality"] = cachedWarnings[slot].area;
      d["description"] = cachedWarnings[slot].description;
      if (cachedWarnings[slot].publishDate) d["publish_date"] = isoUtc(cachedWarnings[slot].publishDate);
      if (cachedWarnings[slot].expirationDate) d["expiration_date"] = isoUtc(cachedWarnings[slot].expirationDate);
      String out;
      serializeJson(ev, out);
      ws.broadcastTXT(out);

      Serial.printf("[warn] cached warning id=%d prio=%s\n", wid, cachedWarnings[slot].priority);
      meshRelay(raw, total, f);
      break;
    }

    case T_CHAT: {
      if (!parsed) break;
      const char* from = p["from"] | "?";
      const char* text = p["text"] | "";
      if (!text[0]) break;
      chatDeliverLocal(from, text);
      meshRelay(raw, total, f);
      break;
    }

    case T_PING:
    case T_STATUS:
      // Nothing to act on, but neighbours further out still benefit from
      // knowing the gateway is alive.
      meshRelay(raw, total, f);
      break;

    default:
      break;   // unknown type: dropped, not forwarded
  }
}

// ---------------------------------------------------------------------------
// OLED
// ---------------------------------------------------------------------------

// Phones joined to the AP. Not the same as chat clients: a handset can be on
// the WiFi without having opened the chat page, which is worth seeing.
int apClientCount() { return WiFi.softAPgetStationNum(); }

// Chat clients that sent a "hello" and are still connected.
int chatClientCount() {
  int n = 0;
  for (int i = 0; i < MAX_AP_CLIENTS; i++)
    if (clientNames[i].length()) n++;
  return n;
}

void oledDraw() {
  if (!oledReady) return;
  oledHeader();

  oled.setCursor(0, 14);
  oled.print(F("Net  : "));
  oled.print(AP_SSID);

  oled.setCursor(0, 26);
  oled.print(F("Boats: "));
  oled.print(apClientCount());
  oled.print(F("  Chat:"));
  oled.print(chatClientCount());

  oled.setCursor(0, 38);
  oled.print(F("Queue: "));
  oled.print(queueDepth());
  if (lastMeshRx) {
    oled.print(F("  "));
    oled.print((int)lastMeshRssi);
    oled.print(F("dBm"));
  }

  oled.setCursor(0, 50);
  oled.print(F("Mesh : "));
  oled.print(radioReady ? (meshUp() ? F("to shore") : F("no shore")) : F("radio!"));

  // ":>" in the bottom-right corner. At text size 1 a glyph is 6x8, so two
  // characters start 12px in from the right edge and clear the text on that
  // line, which never reaches that far.
  oled.setCursor(OLED_W - 12, 50);
  oled.print(F(":>"));

  oled.display();
}

// ---------------------------------------------------------------------------

unsigned long lastDisplay = 0;
unsigned long lastFlush   = 0;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== AqOne buoy " + String(NODE_NAME) + " ===");

  oledSetup();
  queueLoad();
  meshSeqInit();
  memset(tracked, 0, sizeof(tracked));
  memset(seenRing, 0, sizeof(seenRing));
  memset(txRing, 0, sizeof(txRing));

  // Seeded off the MAC so two boards powered from the same switch do not pick
  // identical relay backoffs forever and collide on every single flood.
  randomSeed((uint32_t)ESP.getEfuseMac());

  setupWiFi();

  radioReady = radioSetup();
  if (!radioReady) {
    // Not fatal: phones can still reach this buoy, SOS still queues, and both
    // the portal and /v1/status report the mesh as down rather than letting a
    // fisher believe a dead radio is a working one.
    Serial.println("[lora] RADIO DOWN - mesh unavailable");
  }

  http.on("/v1/sos",        HTTP_POST, handlePostSos);
  http.on("/v1/sos/status", HTTP_GET,  handleGetSosStatus);
  http.on("/v1/status",     HTTP_GET,  handleStatus);
  http.on("/history",       HTTP_GET,  handleHistory);
  http.on("/v1/warnings",   HTTP_GET,  handleGetWarnings);
  http.on("/portal",        HTTP_GET,  handlePortal);

  // Connectivity probes, per platform.
  http.on("/generate_204",             HTTP_GET, handleGenerate204);  // Android
  http.on("/gen_204",                  HTTP_GET, handleGenerate204);  // Android
  http.on("/hotspot-detect.html",      HTTP_GET, handlePortal);       // iOS/macOS
  http.on("/library/test/success.html",HTTP_GET, handlePortal);       // iOS
  http.on("/ncsi.txt",                 HTTP_GET, handleNcsi);         // Windows
  http.on("/connecttest.txt",          HTTP_GET, handleNcsi);         // Windows

  // Anything else on the AP lands on the portal rather than a bare 404.
  http.onNotFound(handlePortal);

  http.begin();

  ws.begin();
  ws.onEvent(onWsEvent);

  Serial.printf("[boot] buoy ready. %d SOS recovered from flash\n", queueDepth());
}

void loop() {
  radioService();

  dns.processNextRequest();   // captive portal
  http.handleClient();
  ws.loop();

  unsigned long now = millis();

  // 500ms is fast enough for a join to feel instant and slow enough that the
  // I2C write never competes with SOS handling or the chat socket.
  if (now - lastDisplay > 500) {
    lastDisplay = now;
    oledDraw();
  }

  // Retry sweep for anything still unacknowledged. The first transmission
  // already happened inside handlePostSos(); this is only the retry ladder.
  if (now - lastFlush > 5000) {
    lastFlush = now;
    if (queueDepth() && radioReady) flushQueue();
  }
}
