// AqOneBuoy.ino — Heltec WiFi LoRa 32 V3 (ESP32-S3)
//
// One buoy node doing three jobs:
//   1. WiFi access point for fishers' phones      (the "Aquan" network)
//   2. Chat hub between phones in range            (your existing chathub)
//   3. SOS gateway: phone -> buoy -> backend -> dashboard, and the
//      dispatcher's ETA back down to the phone
//
// The chat protocol is unchanged from the sketch mobile/lib/ui/chathubb.dart
// already speaks, so the existing Flutter chat page keeps working as-is.
//
// ---------------------------------------------------------------------------
// THE ONE THING THAT WILL BITE YOU
//
// The ESP32-S3 has a single WiFi radio. Access-point and station mode can run
// together, but they MUST share a channel. When this board joins the upstream
// hotspot, its own AP is forced onto that hotspot's channel — any phone already
// connected gets kicked and must rejoin.
//
// So: bring up the station link FIRST, read the channel it landed on, then
// start the AP on that same channel. That is what setupWiFi() below does, and
// it is why the order of those two calls is not arbitrary.
// ---------------------------------------------------------------------------

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <DNSServer.h>

// Heltec WiFi LoRa 32 V3 on-board 0.96" OLED (SSD1306, I2C).
// Requires the "Heltec ESP32 Dev-Boards" library (Sketch > Include Library >
// Manage Libraries > search "Heltec ESP32"). We only use the display half of
// that library here — LoRa radio and deep-sleep helpers are untouched.
#include "heltec.h"

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
static const char* AP_SSID      = "Aquan";
static const char* AP_PASSWORD  = nullptr;   // nullptr => open network
static const char* BUOY_ID      = "BUOY01";

// An open AP is joinable by anyone in range, not just fishers. Accepted
// trade-off: the worst case is a spurious SOS, which a dispatcher can resolve
// in seconds. The alternative failure — a real SOS that never sends because
// someone forgot a password — is not recoverable.
static const int MAX_AP_CLIENTS = 10;

// Upstream internet. On a real buoy this is the shore gateway link; for a demo
// a phone hotspot is fine.
static const char* UPLINK_SSID  = "YOUR_UPLINK_SSID";
static const char* UPLINK_PASS  = "YOUR_UPLINK_PASS";

static const char* BACKEND_HOST =
    "https://aqone-backend.onrender.com";

// ===========================================================================

static const uint16_t HTTP_PORT = 80;
static const uint16_t WS_PORT   = 81;

WebServer        http(HTTP_PORT);
WebSocketsServer ws(WS_PORT);
Preferences      prefs;
DNSServer        dns;

// ---------------------------------------------------------------------------
// Store-and-forward queue
//
// An SOS accepted from a phone must survive a brown-out. Solar plus an 18650
// means this board WILL lose power mid-delivery, and an SOS held only in RAM
// dies silently. Queue entries live in NVS until the backend returns 200.
// ---------------------------------------------------------------------------

static const int MAX_QUEUE = 12;

struct SosItem {
  char     vesselId[33];
  char     boat[33];
  char     note[65];
  double   lat;
  double   lon;
  uint32_t clientTs;
  uint32_t seq;
  bool     hasFix;
  bool     used;
};

SosItem  queueBuf[MAX_QUEUE];
uint32_t nextSeq = 1;

void queueSave() {
  prefs.begin("aqone", false);
  prefs.putBytes("queue", queueBuf, sizeof(queueBuf));
  prefs.putUInt("seq", nextSeq);
  prefs.end();
}

void queueLoad() {
  prefs.begin("aqone", true);
  size_t n = prefs.getBytesLength("queue");
  if (n == sizeof(queueBuf)) prefs.getBytes("queue", queueBuf, sizeof(queueBuf));
  else memset(queueBuf, 0, sizeof(queueBuf));
  nextSeq = prefs.getUInt("seq", 1);
  prefs.end();
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
// WiFi — station first, then AP on the same channel. See the note at the top.
// ---------------------------------------------------------------------------

bool uplinkUp = false;

void setupWiFi() {
  WiFi.mode(WIFI_AP_STA);

  WiFi.begin(UPLINK_SSID, UPLINK_PASS);
  Serial.print("[wifi] uplink");
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  int channel = 1;
  if (WiFi.status() == WL_CONNECTED) {
    uplinkUp = true;
    channel  = WiFi.channel();
    Serial.printf("[wifi] uplink ok  ip=%s  ch=%d\n",
                  WiFi.localIP().toString().c_str(), channel);
  } else {
    // No internet is not fatal. Chat still works, and SOS still queues — the
    // fisher is not told "failed", because the buoy genuinely still has it.
    Serial.println("[wifi] no uplink - running offline, SOS will queue");
  }

  // Open AP: passing nullptr as the password is what makes it open. The extra
  // args are (channel, hidden=0, maxConnections).
  WiFi.softAP(AP_SSID, AP_PASSWORD, channel, 0, MAX_AP_CLIENTS);
  Serial.printf("[wifi] OPEN AP '%s' up on %s ch=%d max=%d\n",
                AP_SSID, WiFi.softAPIP().toString().c_str(),
                channel, MAX_AP_CLIENTS);

  // Captive-portal DNS: every hostname resolves to the buoy. Without this,
  // phones that try to reach a name before we answer their connectivity probe
  // will fail and may drop the network.
  dns.start(53, "*", WiFi.softAPIP());
}

// ---------------------------------------------------------------------------
// Backend calls
// ---------------------------------------------------------------------------

// POST /api/sos — deliberately unauthenticated. A buoy relaying a distress
// call has no bearer token and no way to obtain one.
//
// client_ts is forwarded EXACTLY as the phone sent it. It is half of the
// de-duplication key (vessel_id, client_ts). If we substituted our own clock,
// the same emergency arriving here AND over the fisher's own mobile data would
// create two separate incidents on the dispatcher's screen.
bool postSos(const SosItem& item) {
  if (!uplinkUp || WiFi.status() != WL_CONNECTED) return false;

  WiFiClientSecure client;
  client.setInsecure();   // no cert store on the buoy; see the note below

  HTTPClient https;
  String url = String(BACKEND_HOST) + "/api/sos";
  if (!https.begin(client, url)) return false;
  https.addHeader("Content-Type", "application/json");
  https.setTimeout(12000);

  JsonDocument doc;
  doc["vessel_id"]  = item.vesselId;
  doc["client_ts"]  = item.clientTs;
  doc["boat"]       = item.boat;
  doc["trust_tier"] = "self_declared";
  doc["source"]     = "buoy";
  doc["buoy_id"]    = BUOY_ID;
  doc["seq"]        = item.seq;
  if (item.note[0]) doc["note"] = item.note;
  // Omit lat/lon entirely when there is no fix. Never send 0,0 — that is a
  // real location in the Gulf of Guinea and it would be plotted as one.
  if (item.hasFix) {
    doc["lat"] = item.lat;
    doc["lon"] = item.lon;
  }

  String body;
  serializeJson(doc, body);

  int code = https.POST(body);
  https.end();

  Serial.printf("[sos] POST %s -> %d\n", item.vesselId, code);
  // 200 covers both "created" and "already recorded". Either way the backend
  // has it and this buoy can stop retrying.
  return code == 200;
}

void flushQueue() {
  for (int i = 0; i < MAX_QUEUE; i++) {
    if (!queueBuf[i].used) continue;
    if (postSos(queueBuf[i])) {
      queueBuf[i].used = false;
      queueSave();
    } else {
      return;   // keep order; retry on the next tick
    }
  }
}

// ---------------------------------------------------------------------------
// ETA cache — the return path
//
// The dispatcher acknowledges on the dashboard with an ETA. The backend turns
// that into an absolute eta_at. The phone cannot reach the internet itself, so
// this buoy polls on its behalf and serves the answer over the local AP.
//
// We poll only for vessels that have actually sent an SOS through this buoy.
// ---------------------------------------------------------------------------

static const int MAX_TRACKED = 8;

struct Tracked {
  char vesselId[33];
  char payload[320];   // last JSON answer from the backend
  bool used;
};

Tracked tracked[MAX_TRACKED];

void trackVessel(const char* vesselId) {
  for (int i = 0; i < MAX_TRACKED; i++)
    if (tracked[i].used && strcmp(tracked[i].vesselId, vesselId) == 0) return;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].used) {
      strncpy(tracked[i].vesselId, vesselId, 32);
      tracked[i].vesselId[32] = 0;
      tracked[i].payload[0]   = 0;
      tracked[i].used         = true;
      return;
    }
  }
}

void pollEta() {
  if (!uplinkUp || WiFi.status() != WL_CONNECTED) return;

  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].used) continue;

    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient https;
    String url = String(BACKEND_HOST) + "/api/sos/vessel/" + tracked[i].vesselId;
    if (!https.begin(client, url)) continue;
    https.setTimeout(8000);

    if (https.GET() == 200) {
      String body = https.getString();
      strncpy(tracked[i].payload, body.c_str(), sizeof(tracked[i].payload) - 1);
      tracked[i].payload[sizeof(tracked[i].payload) - 1] = 0;

      // Push it straight to connected phones too, so an acknowledgement lands
      // without the app having to poll us. A fisher waiting on a rescue should
      // not depend on a refresh interval.
      JsonDocument ev;
      ev["type"]      = "sos_update";
      ev["vessel_id"] = tracked[i].vesselId;
      ev["data"]      = body;
      String out;
      serializeJson(ev, out);
      ws.broadcastTXT(out);
    }
    https.end();
  }
}

// ---------------------------------------------------------------------------
// HTTP routes served to phones on the AP
// ---------------------------------------------------------------------------

// POST /v1/sos — what the Flutter app calls over the buoy's WiFi.
// We answer immediately. Delivery to the backend happens on the next tick.
// Blocking the reply on an HTTPS round trip would leave a person in distress
// staring at a spinner.
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

  int slot = queueFreeSlot();
  if (slot < 0) {
    http.send(503, "application/json", "{\"error\":\"queue full\"}");
    return;
  }

  SosItem& it = queueBuf[slot];
  memset(&it, 0, sizeof(it));
  strncpy(it.vesselId, vesselId,               32);
  strncpy(it.boat,     in["boat"] | "",        32);
  strncpy(it.note,     in["note"] | "",        64);
  it.clientTs = clientTs;
  it.seq      = nextSeq++;
  it.hasFix   = in["lat"].is<double>() && in["lon"].is<double>();
  if (it.hasFix) { it.lat = in["lat"]; it.lon = in["lon"]; }
  it.used = true;
  queueSave();

  trackVessel(vesselId);

  JsonDocument out;
  out["accepted"]  = true;
  out["buoy_id"]   = BUOY_ID;
  out["seq"]       = it.seq;
  out["server_ts"] = (uint32_t)(millis() / 1000);
  String body;
  serializeJson(out, body);
  http.send(200, "application/json", body);

  Serial.printf("[sos] queued %s seq=%u depth=%d\n",
                vesselId, it.seq, queueDepth());
}

// GET /v1/sos/status?vessel_id=... — the ETA the dispatcher sent back.
void handleGetSosStatus() {
  String vid = http.arg("vessel_id");
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (tracked[i].used && vid == tracked[i].vesselId && tracked[i].payload[0]) {
      http.send(200, "application/json", tracked[i].payload);
      return;
    }
  }
  http.send(200, "application/json", "{\"events\":[]}");
}

// GET /v1/status — buoy health, so the app can show "connected to BUOY01".
// Reports the uplink honestly: a fisher should be able to tell the difference
// between "the buoy has my SOS" and "the SOS has reached shore".
void handleStatus() {
  JsonDocument doc;
  doc["buoy_id"]       = BUOY_ID;
  doc["uplink"]        = uplinkUp && WiFi.status() == WL_CONNECTED;
  doc["queue_depth"]   = queueDepth();
  doc["clients"]       = WiFi.softAPgetStationNum();
  doc["uptime_s"]      = millis() / 1000;
  String body;
  serializeJson(doc, body);
  http.send(200, "application/json", body);
}

// GET /history — unchanged; the Flutter chat page backfills from here.
String chatHistory = "[]";
void handleHistory() { http.send(200, "application/json", chatHistory); }

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
// When our uplink is alive we answer "internet is fine" (204 / Microsoft's
// exact NCSI string). When it is not, we answer with a redirect so the phone
// pops the captive-portal page instead of silently leaving.
// ---------------------------------------------------------------------------

bool haveInternet() { return uplinkUp && WiFi.status() == WL_CONNECTED; }

void handleGenerate204() {
  if (haveInternet()) {
    http.send(204, "text/plain", "");
  } else {
    http.sendHeader("Location", "http://192.168.4.1/portal", true);
    http.send(302, "text/plain", "");
  }
}

void handleNcsi() {
  if (haveInternet()) {
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
    "<h1>AqOne &mdash; " + String(BUOY_ID) + "</h1>"
    "<div class=b>You are connected to an AqOne safety buoy.</div>";

  page += haveInternet()
    ? "<div class=s><b>Link to shore is up.</b><br>An SOS sent from the AqOne "
      "app will reach the rescue centre now.</div>"
    : "<div class=w><b>Link to shore is down.</b><br>You can still send an SOS "
      "&mdash; this buoy will hold it and deliver it automatically once the "
      "link returns.</div>";

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
    JsonDocument out;
    out["type"] = "msg";
    out["from"] = in["from"] | "?";
    out["text"] = in["text"] | "";
    String s;
    serializeJson(out, s);
    ws.broadcastTXT(s);
  }
}

// ---------------------------------------------------------------------------
// OLED status screen
//
// Serial is useless once this board is untethered at sea. This gives anyone
// standing next to the buoy a glance-and-know signal: is the uplink alive,
// how many boats are on the AP, is anything stuck in the SOS queue.
//
// Smiley = uplink good and queue empty ("all clear"). Anything else and it
// swaps to a flat mouth, so the face itself doubles as the health signal —
// no need to read the text to know something needs attention.
// ---------------------------------------------------------------------------

void drawFace(bool ok, int x, int y) {
  Heltec.display->drawCircle(x, y, 10);
  Heltec.display->fillCircle(x - 4, y - 3, 1);
  Heltec.display->fillCircle(x + 4, y - 3, 1);
  if (ok) {
    // upward curve = smile
    Heltec.display->drawLine(x - 5, y + 3, x - 2, y + 6);
    Heltec.display->drawLine(x - 2, y + 6, x + 2, y + 6);
    Heltec.display->drawLine(x + 2, y + 6, x + 5, y + 3);
  } else {
    // flat mouth = "something needs a look"
    Heltec.display->drawLine(x - 5, y + 5, x + 5, y + 5);
  }
}

void updateDisplay() {
  bool ok = haveInternet() && queueDepth() == 0;

  Heltec.display->clear();
  Heltec.display->setFont(ArialMT_Plain_10);

  Heltec.display->setTextAlignment(TEXT_ALIGN_LEFT);
  Heltec.display->drawString(0, 0,  String(BUOY_ID));
  Heltec.display->drawString(0, 12, haveInternet() ? "uplink: UP" : "uplink: DOWN");
  Heltec.display->drawString(0, 24, "clients: " + String(WiFi.softAPgetStationNum()));
  Heltec.display->drawString(0, 36, "sos queue: " + String(queueDepth()));

  drawFace(ok, 108, 20);

  Heltec.display->display();
}

// ---------------------------------------------------------------------------

unsigned long lastFlush   = 0;
unsigned long lastPoll    = 0;
unsigned long lastDisplay = 0;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== AqOne buoy " + String(BUOY_ID) + " ===");

  // Display-only init: (LoRa disabled, PABOOST irrelevant, Serial already up,
  // freq unused). Heltec.begin's other params are for the LoRa radio, which
  // this sketch does not use — leaving them off avoids fighting the WiFi
  // radio for airtime.
  Heltec.begin(true /*DisplayEnable*/, false /*LoRa*/, false /*Serial*/);
  Heltec.display->flipScreenVertically();
  Heltec.display->setFont(ArialMT_Plain_10);
  Heltec.display->clear();
  Heltec.display->drawString(0, 0, "AqOne booting...");
  Heltec.display->display();

  queueLoad();
  memset(tracked, 0, sizeof(tracked));
  setupWiFi();

  http.on("/v1/sos",        HTTP_POST, handlePostSos);
  http.on("/v1/sos/status", HTTP_GET,  handleGetSosStatus);
  http.on("/v1/status",     HTTP_GET,  handleStatus);
  http.on("/history",       HTTP_GET,  handleHistory);
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

  Serial.printf("[boot] ready. %d SOS recovered from flash\n", queueDepth());
}

void loop() {
  dns.processNextRequest();   // captive portal
  http.handleClient();
  ws.loop();

  unsigned long now = millis();

  if (now - lastFlush > 5000) {     // deliver queued SOS
    lastFlush = now;
    if (queueDepth()) flushQueue();
  }

  if (now - lastPoll > 15000) {     // check for dispatcher ETAs
    lastPoll = now;
    pollEta();
  }

  if (now - lastDisplay > 2000) {   // refresh OLED status
    lastDisplay = now;
    updateDisplay();
  }

  // Reconnect the uplink if it drops. Never blocks the AP or the chat.
  if (WiFi.status() != WL_CONNECTED && now % 30000 < 50) {
    WiFi.begin(UPLINK_SSID, UPLINK_PASS);
  }
}
