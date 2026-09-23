# 21 — Week 1 Contract Fixtures (ground truth, Phase 0)

This document records the *historical* JSON shapes observed in the checked-in
firmware and backend on 2026-08-15, as required by
`docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md` Phase 0. It is a
dated fixture record, not the current architecture decision. The current
phone-to-field-node naming and hybrid topology are in
`docs/03_PHONE_BUOY_WIFI.md` and
`docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`; the fixtures remain useful
for the firmware shapes they capture.

Fixture files: `fixtures/accepted_sos.json`, `fixtures/queue_full.json`,
`fixtures/buoy_offline.json`, `fixtures/no_eta.json`,
`fixtures/eta_acknowledged.json`.

## Canonical contract — verified against firmware

`firmware/buoy/AqOneBuoy/AqOneBuoy.ino`:
- `HTTP_PORT = 80`, AP started via `WiFi.softAP(...)` → default AP IP
  `192.168.4.1`. Confirms the plan's canonical HTTP base URL.
- `WS_PORT = 81` (`WebSocketsServer ws(WS_PORT)`), a **separate** WebSocket
  server from the HTTP server, no path routing (raw `WebSocketsServer`, not
  mounted at `/ws`). Confirms the plan's canonical `ws://192.168.4.1:81`.
- Routes actually registered: `POST /v1/sos`, `GET /v1/sos/status`,
  `GET /v1/status`, `GET /history`, `GET /portal`, plus OS captive-portal
  probe endpoints. This matches the plan's canonical table exactly.

**Verdict: apply the plan's canonical contract decision as written.** The
conflicts below are all on the *client* side (Flutter) and in stale docs, not
in the firmware. The `buoy` names in these fixtures are retained wire/API
compatibility names and may identify a boat pod or stationary field node.

## Discrepancies found (client/doc vs. firmware — not yet fixed, Phase 1 work)

| Surface | Current value | Firmware truth | File |
|---|---|---|---|
| `AqOneConfig.buoyBaseUrl` default | `http://10.0.0.1` | `http://192.168.4.1` | `mobile/lib/core/config.dart:6` |
| `ChatService` WS URL | `ws://192.168.4.1/ws` (port 80, path `/ws`) | `ws://192.168.4.1:81` (no path, raw WS) | `mobile/lib/ui/chathubb.dart:41,68` |
| `BuoyStatus.buoyId` parsed as `int` | expects `json['buoy_id']` numeric | firmware sends `BUOY_ID` as the **string** `"BUOY01"` | `mobile/lib/models/buoy_contact.dart:36` vs `.ino:381` |
| `BuoyStatus` reads `json['batt']`, `json['mesh']`, `json['queued']` | expects those three keys | firmware's `GET /v1/status` sends `buoy_id, uplink, queue_depth, clients, uptime_s` — **no `batt`, no `mesh`, and the queue key is `queue_depth` not `queued`** | `mobile/lib/models/buoy_contact.dart:20-45` vs `.ino:373-385` |
| `docs/03_PHONE_BUOY_WIFI.md` | documents `buoy_id`/`src_id` as integers, buoy IP `10.0.0.1`, no `/v1/sos/status` endpoint, `GET /v1/status` returning `batt`/`mesh`/`queued` | firmware disagrees on all points above | `docs/03_PHONE_BUOY_WIFI.md` |
| `mobile/lib/services/buoy_client.dart` | has no method for `GET /v1/sos/status` | firmware serves it and proxies `GET /api/sos/vessel/{id}` verbatim | Phase 2 work |

None of these were silently changed. They are recorded here per Hard Reset
rule 2 and left for Phase 1/2 to fix with tests.

## Verified JSON shapes

### `POST /v1/sos` success (buoy accepted) — `firmware/buoy/AqOneBuoy/AqOneBuoy.ino:339-346`

```json
{ "accepted": true, "buoy_id": "BUOY01", "seq": 42, "server_ts": 172963201 }
```

`buoy_id` is a string (the firmware's `BUOY_ID` constant), not numeric.
`seq` is a monotonically increasing `uint32_t` per buoy. `server_ts` is
`millis()/1000` since boot, **not** wall-clock epoch seconds — do not treat it
as an absolute timestamp.

### `POST /v1/sos` — queue full — `.ino:328-331`

`503` with body `{"error":"queue full"}`.

### `POST /v1/sos` — malformed/missing fields — `.ino:308-323`

`400 {"error":"empty body"}` or `400 {"error":"bad json"}` or
`422 {"error":"vessel_id and client_ts are required"}`.

### Buoy unreachable

Not a JSON response — a connection timeout/refused/DNS failure at the HTTP
client layer. `mobile/lib/services/buoy_client.dart` already maps this to
`BuoyUnreachable`.

### `GET /v1/status` — `.ino:373-385`

```json
{ "buoy_id": "BUOY01", "uplink": true, "queue_depth": 0, "clients": 1, "uptime_s": 4213 }
```

`uplink` is whether the buoy currently has a working shore/internet link.
There is no battery or mesh-health field in the firmware today, despite both
the plan and `docs/03` assuming one.

### `GET /v1/sos/status?vessel_id=<id>` — no tracked events — `.ino:361-370`

```json
{ "events": [] }
```

This is the *only* hardcoded shape the firmware returns itself.

### `GET /v1/sos/status?vessel_id=<id>` — with an ETA — `.ino:267-285` + `backend/app/api/sos.py:293-344`

The firmware does not construct this JSON. It polls
`GET /api/sos/vessel/{vessel_id}` on the backend and stores the **raw response
body verbatim**, then serves that same body back to the phone. The real shape
is therefore whatever `vessel_sos()` in `backend/app/api/sos.py` returns:

```json
{
  "vessel_id": "fisher-7f3a",
  "server_time": "2026-08-15T09:12:44.120000+00:00",
  "events": [
    {
      "id": 118,
      "local_id": "a3f9c2e1-88d1-4b0a-9d4e-2f6a7b0c9e11",
      "seq": 42,
      "client_ts": 1755248500,
      "delivery_state": "acknowledged",
      "acknowledged_at": "2026-08-15T09:10:02+00:00",
      "acked_by": "dispatcher_maria",
      "eta_at": "2026-08-15T09:40:00+00:00",
      "responder_status": 2,
      "responder_status_label": "Rescue boat on the way",
      "responder_note": "Coast Guard boat en route from Dumaguit",
      "fisher_reply": null,
      "resolved_at": null
    }
  ]
}
```

`responder_status` values come from `RESPONDER_STATUS_LABELS` in
`backend/app/api/sos.py` (1 received, 2 dispatched, 3 coast guard, 4 nearest
vessel, 5 delayed). `delivery_state` is one of the four states in
`docs/06_DELIVERY_STATES.md`, computed server-side; the client must not move
a state backward when merging this with what it already has.

### `GET /v1/sos/status?vessel_id=<id>` — malformed buoy response

Not observed from the real firmware (it proxies the backend body as-is,
truncated to 320 bytes by `char payload[320]`). A response longer than 320
bytes will be **silently truncated mid-JSON** by the firmware, producing an
invalid JSON body the phone must handle without crashing. This is a real
firmware constraint worth a dedicated Flutter test case (`fixtures/no_eta.json`
covers the empty case; a truncated-JSON case should be added in Phase 2).

### `GET /api/sos/active` (dashboard) — `backend/app/api/sos.py:175-217`

Not yet inspected field-by-field in this pass; same row shape as
`vessel_sos()` above, filtered to active/unresolved incidents, behind
`require_user`.

## Dashboard honesty findings (ground truth for Phase 3)

- `web/html/dashboard.html:76` — `<span class="sync-text">LIVE</span>` is
  static markup. Nothing in `web/js/dashboard.js` ever updates it. It reads
  "LIVE" even when `loadActiveSos()` has been failing.
- `web/js/dashboard.js:1604-1609` — a failed `/api/sos/active` poll only
  does `console.warn(...)`; there is no visible stale/offline state shown to
  the dispatcher, contradicting Hard Reset rule 4.
- `web/js/dashboard.js:1396` — `${a.isLive ? '<span class="alert-live-badge">LIVE</span>' : ''}${a.desc}` —
  `a.desc` is built from server-provided `boat` and `note` text
  (`web/js/dashboard.js` `liveAlertFromEvent`) and inserted via template
  literal into `innerHTML` with no escaping found anywhere in the file (no
  `escapeHtml`/`escapeHTML` helper exists yet). This is the XSS gap Phase 3
  rule 5 exists to close.
- The hardcoded demo buoys/vessels (`web/js/dashboard.js:131-152`, `status:
  'active'`) render on the same map/list surfaces as live SOS markers with no
  demo-mode label distinguishing them.

## Environment blockers hit while establishing the Phase 0 baseline

Recorded per Hard Reset rule 5 — commands run, not assumed:

- `cd backend && pytest -q` — **blocked**. `backend/requirements.txt` pins
  `numpy==2.4.6`, which requires Python ≥3.11/3.12. This sandbox has Python
  3.10.12 only; `pip install -r backend/requirements.txt` fails to resolve
  numpy. A minimal `pytest`/`fastapi`/`httpx` install (without the full
  requirements) collects but fails on `from datetime import UTC` (added in
  Python 3.11) in `app/api/advisories.py` and `tests/test_trip_profile.py` —
  15 collection errors, 0 tests run. Needs a Python 3.11+ interpreter.
- `cd backend && ruff check .` — **ran** (installed `ruff` standalone via
  pip, version 0.16.3 vs. the pinned 0.16.1 — close enough to trust the
  result). Found 1 real issue: `app/api/metrics.py:31` missing a trailing
  newline (`W292`), auto-fixable.
- `cd mobile && flutter analyze` / `cd mobile && flutter test` — **blocked**.
  No Flutter SDK is installed in this sandbox (`which flutter` empty, no
  `flutter*` binary found on the filesystem). Needs a machine/CI runner with
  Flutter installed; cannot be run from here.
- `node --check web/js/dashboard.js` — **ran, passed.** Node v22.22.3.

## Non-sensitive secret finding (Hard Reset rule 6)

`firmware/buoy/AqOneBuoy/AqOneBuoy.ino:60-61` hardcodes a real upstream WiFi
password: set `UPLINK_PASS` and `UPLINK_SSID` in the sketch to the
uplink network for your demo. Do not commit real credentials.
Per rule 6 this is reported, not copied further or repeated elsewhere; it
should be moved out of source (e.g. `Preferences`/NVS set at flash time or a
build-time define) before this file is shared publicly. Not fixed in this
phase — out of the Phase 0-4 work list — but flagged for the owner (Daniel).
