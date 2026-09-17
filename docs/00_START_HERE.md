# 00 — START HERE

## The problem

Small-scale fishermen in New Washington, Aklan, Philippines work in an
environment with no mobile signal. Team field interviews established this is
not an edge case — **when fishermen go out to fish, all of them are in a
cellular dead zone.**

Consequences today:
- No way to call for help from the water.
- MDRRMO (the local disaster-response office) typically learns about a
  capsizing hours later, by word of mouth.
- Every consumer safety app stops working exactly where it is needed.

## The solution

Boat-mounted safety pods carrying an ESP32-S3 and an SX1262 LoRa radio give each
fisherman's phone a short local WiFi handoff. The pod sends the SOS directly over
LoRa to a tall shoreline gateway, which forwards it to the backend and pushes it
to the MDRRMO dashboard. Stationary navigational buoys remain as fixed sensor
stations and optional LoRa relays where measured coverage requires them.

The phone never needs cellular signal.

## Architecture

```
┌───────────────┐  WiFi SoftAP   ┌──────────────────────┐
│ Vessel phone  │ ─────────────► │ Boat pod (ESP32-S3)  │
│ Flutter       │                │ • SX1262 LoRa        │
│ • SQLite      │ ◄───────────── │ • physical SOS btn   │
│   outbox      │   pod ack      │ • store & forward    │
│ • airplane    │                │ • signs packets      │
│   mode OK     │                └──────────┬───────────┘
└───────────────┘                           │ LoRa
                                            ▼
                                 ┌──────────────────────┐
                                 │ Optional sensor/relay │
                                 └──────────┬───────────┘
                                            │ LoRa
                                            ▼
                                 ┌──────────────────────┐
                                 │ TALL GATEWAY (internet)│
                                 │ • verify signature   │
                                 │ • external ID → UUID │
                                 │ • HTTPS to backend   │
                                 └──────────┬───────────┘
                                            │ HTTPS
                                            ▼
                        ┌───────────────────────────────────┐
                        │ BACKEND — FastAPI + PostgreSQL    │
                        │ ingest → dedupe → event log →     │
                        │ projection → SSE push             │
                        └──────────┬────────────────────────┘
                                   │ SSE / REST
                                   ▼
                        ┌───────────────────────────────────┐
                        │ DASHBOARD — MDRRMO live SOS feed  │
                        └───────────────────────────────────┘
```

## Users and roles

| Role | Enum value | Sees |
|---|---|---|
| Fisherman | `fisherman` | Mobile app only. Sends SOS, sees own status. |
| MDRRMO responder | `mdrrmo` | Dashboard. Live SOS feed, acknowledge. |
| Admin | `admin` | Everything MDRRMO sees. |

BFAR/LGU regulator roles existed in v1 and are **out of scope** for this build.

## Team and ownership

| Person | Owns |
|---|---|
| Lenard | Lead dev — backend, architecture, deployment |
| Arnold | Full stack — ingest pipeline, gateway |
| Daniel | **Hardware/firmware — boat pod, sensor buoy, and relay hardware. Critical path.** |
| Jade | Dashboard |
| Doreen Kay | UI/UX, pitch deck |

Daniel is on the critical path. The field hardware is the product; if firmware
or the enclosure slips, everything else is decoration.

## Build order

Strictly sequential. Do not start a step before the previous one demonstrably
works.

1. **Deployed skeleton** — FastAPI on Railway, green healthcheck, migrations
   run. (~1 hr)
2. **Two radios talk** — raw LoRa packet between two ESP32s, no protocol yet.
   (~1 hr, parallel with 1)
3. **Boat pod → shore gateway → backend** — a pod button press creates a real
   SOS row via direct LoRa. (~1.5 hr)
4. **Phone → boat pod → backend** — phone in airplane mode, SOS lands. (~2 hr)
5. **Dashboard live feed + acknowledge** — full path visible. (~1 hr)
6. **Range test outdoors** — record the actual metres achieved. (~1 hr)
7. **Add a stationary sensor or relay buoy only where testing justifies it.**
8. **Freeze, rehearse ×3, record screencast.**

## Definition of done for the whole build

- [ ] Phone in airplane mode sends an SOS that reaches the dashboard
- [ ] Dashboard acknowledge persists across a reload
- [ ] The four delivery states are visible and honest in the app
- [ ] Deployed, healthcheck green, demo URL reachable from outside the venue
- [ ] Repo public, no secrets, README with setup instructions
- [ ] Screencast recorded
- [ ] `docs/08_DEMO_AND_STATUS.md` status table reflects reality

## What we are deliberately not building

See `docs/07_SCOPE_OUT.md` for the full list, including which items have since
been amended into scope. Short version of what is **still** out: no catch
logging, no photos, no fisheries-enforcement or surveillance features, and no
LoRa downlink to the handset.

AI models, advisories, accounts and "did not return" detection were originally
scoped out and have since been built — `docs/07_SCOPE_OUT.md` records where each
now lives. The canonical scope is `Aqone_PRD (2).md` (v3.0), where anything not
yet built is tagged `[Roadmap — not implemented]`.

## External deadlines

Event deadlines are maintained separately from the implementation brief in
[`53_EXTERNAL_DEADLINES.md`](53_EXTERNAL_DEADLINES.md). The completed AI Fest
schedule is archived in [`archive/AI_FEST_2026_DEADLINES.md`](archive/AI_FEST_2026_DEADLINES.md).
