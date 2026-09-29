# AqOne App - Features, How It Works, Technical Reference, and Data Sets

AqOne is an offline SOS mesh for small-scale fishermen in New Washington, Aklan who have no mobile signal at sea.
A phone hands an SOS to a nearby buoy over WiFi, buoys relay it over LoRa to a shore gateway with internet, the gateway forwards it to a FastAPI backend, and the backend pushes it to an MDRRMO dashboard.
This document summarizes the whole system on branch `Jade-backup`: the mobile app, the dashboard, the backend, the AI models, the hardware path, the technical reference, and every data set.

## 1. Mobile app (Flutter)

The handset app ships English, Tagalog (`fil`), and Aklanon (`akl`), with Aklanon as the default locale.
Four-tab shell: Home, Venture (at-sea map), Advisories, and Profile, plus onboarding, SOS flow, chat, enrolment, and info screens.

### 1.1 SOS flow

Tapping SOS starts a 5-second full-screen countdown (slide-to-cancel, cannot be dismissed by back button or tapping outside) so a pocket-dial can still be stopped.
Dispatch sends with no note first so typing never delays the alert, then a bottom sheet collects the emergency type (engine, capsizing, medical, other) plus free text, or slide-to-stand-down ("safe now", with undo).
Every SOS is attempted over two routes in parallel: direct HTTPS to the backend and buoy WiFi handoff for LoRa relay, and the backend dedupes on `(vessel_id, client_ts)`.
Delivery states are forward-only and honest: `saved, relayed, delivered, acknowledged`, refined for fishers into not-sent-yet, pod-has-it, rescue-centre-has-it, help-coming, cancelling, and closed.
The outbox is SQLite insert-first (survives dead battery and crashes), retries relay every 20 seconds, reconciles every 15 seconds, and a 5-minute late-GPS poll backfills position.
A foreground service keeps retrying while unsent SOS exist, and the SOS alarm loop plus vibration is foreground-only by design.

### 1.2 Offline at sea

The app assumes airplane mode with GPS still on, and the fisher joins the buoy SoftAP (`Aquan`, `http://192.168.4.1`, open by design so distress never asks for a password).
Phone-to-buoy HTTP covers SOS handoff, status, warnings, and advisories, plus a separate chat WebSocket on port 81 with offline queue and per-message honest states.
Buoys store-and-forward over LoRa (12-SOS flash queue, 15-minute expiry) until the mesh acknowledges, and there is deliberately no LoRa downlink to the handset.
ETA and acknowledgements reconcile from the backend directly when signal exists, or through the buoy proxy when it does not.
Maps work offline through a viewed-tiles disk cache plus a bundled mbtiles pack, with snapshots of feeds and an offline banner.

### 1.3 Other screens

Venture is the at-sea map with user dot, buoy markers and coverage circles, weather capsule, compass, and hazard popups.
Advisories lists MDRRMO/LGU warnings most-urgent-first and never fakes an all-clear when loading fails.
Boat-to-boat chat runs over the buoy hub with history backfill and honest queued/delivered states.
Profile covers avatar, identity, shore contacts, trust tier, theme, silent-SOS switch, language, device enrolment via pairing code, and logout that keeps SOS retry running.
A red full-screen RETURN NOW takeover exists for squall alerts, plus responder-ETA dialogs and system notifications.
Pitch mode (`PITCH_MODE=true`) hides squall surfaces for demos.
Not built on this branch: trip-checklist UI (table only), catch logging (removed), hotspot heatmap (renders only if the backend endpoint answers).

## 2. MDRRMO dashboard (web)

The operations console is a Leaflet map plus live panels served by the same backend on the same origin.
The header holds layer switching, search (visual only), language toggle, sync badge driven by real poll success, theme, fullscreen, and the operator profile pill.
Three live metric cards (LIVE SOS, RETURN NOW, LAST UPDATED) plus the APP USERS card form the top banner, followed by the `Live near-shore danger scan` map bar with retry and fullscreen buttons.

### 2.1 SOS operations

The live SOS feed polls every 3 seconds, badges rows LIVE or DEMO from backend provenance, sounds the klaxon only for new arrivals, and keeps last data on failed polls.
Clicking an incident pans the map and opens a drawer with vessel identity, position, live timer, nearest buoy, escalation stage, and responder block.
Acknowledge takes status 1-5, ETA chips plus free minutes, and a 40-byte note with version-conflict handling; Resolve takes a reason code with a 10-second Undo that reopens.
Incident Feed shows active calls, Resolved Incidents shows the 5 latest with a View-all toggle and per-row Reopen.
The APP USERS card opens the roster page: every vessel with name, license number, phone, Active/Inactive filter, sea status, and last GPS fix.

### 2.2 Map intelligence

The danger-zone scan scores near-shore cells from live Open-Meteo weather/marine plus a committed GradientBoosting model, drawing colored circles with popups (wind, wave, depth, trigger, model version) and an `EXPERIMENTAL - NOT FOR NAVIGATION` badge.
Squall and drift panels render only what the backend returns, including honest `unknown` and insufficient-data states rather than invented all-clears.
The toolbox offers 12 layer toggles, pan/pin/measure modes, map snapshot export, and keyboard shortcuts.
Buoy health draws the live network (buoys, gateways, LoRa coverage, mesh links), ops status reports gateway/SMS/database health, and audit gives case timelines plus an admin-only global audit search and export.
A 7-lesson tutorial mode replays recorded backend responses so anyone can learn without an account.

## 3. Backend (FastAPI + PostgreSQL)

SOS ingest accepts both transports unauthenticated by design (a fisherman at sea holds no account) and merges duplicates idempotently.
Delivery states are `relayed, delivered, acknowledged`; the gateway return leg (`GET /api/sos/downlink`) exposes only ack/ETA fields under a separate gateway key, never SOS positions.
The incident lifecycle covers acknowledge with ETA, resolve with reason codes, reopen by operator or by the fisher's STILL-IN-DANGER reply, and SAFE-NOW stand-down that resolves.
Trips, advisories with delivery receipts, catch logs with opt-in hotspots, vessel pairing codes with 24-hour device tokens, mesh chat, sea condition, and public proxies (forecast, buoys, squall, hotspots) round out the API.
A scheduler escalates stale SOS over SMS and evaluates anomaly queues under database locks.
Demo mode mounts a scripted scenario engine only when explicitly enabled, and migrations run automatically on every deploy.

## 4. AI models

All production models are honestly labeled with their calibration, and every one is synthetic-calibrated except the marine-hazard model below.
The squall nowcaster (logistic regression on 21 barometric features) predicts onset probability at 30-90 minute leads but stays `unknown` without 3 fresh live buoys, and live `return_now` is capped at `watch` until field validation.
The trip anomaly detector is rule-based (overdue weight 0.85 plus sequence, distance, weather), never auto-dispatches, and its published false-alarm rate is an honest 1.0 under 72-hour silent sweeps.
The drift model runs a 2000-particle Monte Carlo leeway cone with 50/75/95% contours, refuses to draw without sufficient live current observations, and supports Bayesian searched-area updates.
The marine-hazard model behind the dashboard danger scan is the one real-data model: GradientBoostingClassifier on Open-Meteo history 2023-2025 plus ERA5 waves, IBTrACS cyclones, and GEBCO depth (ROC 0.965, F1 0.827).
Catch hotspots are deterministic density bins with reporter anonymity, not ML.

## 5. Hardware path (firmware)

Heltec WiFi LoRa 32 V3 boards (ESP32-S3 + SX1262) run two sketches: the boat pod/buoy and the shore gateway.
The pod hosts the open `Aquan` AP, queues SOS in flash across reboots, and floods LoRa frames (22-byte header plus JSON payload, HMAC-signed, TTL 4) directly to shore or via relay buoys.
The frame family covers SOS, ACK, PING beacons, STATUS, CHAT, ETA downlink, and WARN downlink at 915 MHz SF10.
The shore gateway verifies signatures, dedupes, and POSTs to the backend over HTTPS with the gateway key, while polling downlink ETA, chat, and advisories back onto the mesh.
Captive-portal probes keep phones from abandoning pod WiFi, and all secrets live in a gitignored header, never in the repo.

## 6. Technical reference

Stack: Flutter 3.44 (plain setState/ValueNotifier, SQLite outbox v15, Keystore tokens) · FastAPI on Python 3.11 with asyncpg · Leaflet 1.9.4 vendored, Esri/Carto tiles · ESP32-S3 firmware via PlatformIO.
Auth: bcrypt passwords, HS256 JWT with token-version revocation, operator roles (mdrrmo/lgu/admin), vessel pairing codes with short-lived device tokens, gateway API key isolated to ingest/downlink routes.
Database: 41 migration files (001-038 with duplicates), key tables `sos_events, vessels, vessel_devices, buoys, buoy_contacts, vessel_trips, catch_logs, advisories, users`, applied in order at container start.
Deployment: single Docker image (backend plus web) on Render from the deploy branch, `/health/ready` healthcheck, required secrets `DATABASE_URL, JWT_SECRET, ADMIN_SETUP_KEY, GATEWAY_API_KEY`.
Contracts: LoRa binary frame (`docs/02`), phone-buoy WiFi (`docs/03`), gateway HTTPS (`docs/04`), public REST (`docs/05`), delivery states (`docs/06`).
Verification: backend pytest plus ruff, firmware PlatformIO build, mobile `flutter analyze` plus `flutter test`, dashboard node tests, headless-Edge render checks against disposable databases.

## 7. Data sets

| Data set | Location | Contents | Consumer |
|---|---|---|---|
| Synthetic operational simulation | `backend/app/simulation/generator.py` | 30-50 vessels, 8-12 buoys, contacts, pressure, squall events, currents, incidents with drift tracks, all `is_synthetic=TRUE` | Model calibration and eval, demo and render-check seeds |
| Marine-hazard training data (real) | Open-Meteo archive, ERA5 marine, IBTrACS cyclones, GEBCO depth (upstream APIs, frozen model card) | 12,456 train / 8,760 test rows, 2023-08-01 to 2025-12-31 | Dashboard danger-zone model, the only real-data-trained model |
| Live weather-marine proxy (real) | Open-Meteo Forecast + Marine APIs via `GET /api/public/forecast` | 7-day daily plus hourly wind, gust, precipitation, wave height | Home outlook strip, safety heuristic, danger-zone scoring |
| PAGASA advisories (real, official) | Backend advisories API, relayed as LoRa WARN frames | Official warnings with revision superseding | Handset warnings, dashboard warn-fleet |
| Service-area geography | `backend/app/geo.py` | Batan Bay/Sibuyan Sea water polygon, 3 shore stations, ops center | Sampling, demo markers, drift beaching |
| LoRa worked-example fixture | `fixtures/loam/checkin_v1.json` | 45-byte STATUS frame example with header decode | Spec readers, codec tests |
| Phone-buoy contract fixtures | `fixtures/week1_contract/*.json` | Accepted SOS, queue-full, offline, ETA ack, no-ETA request/response pairs | Mobile client tests |
| Tutorial recordings (synthetic replay) | `web/data/tutorial/*.json` (7 lessons) | Full canned API answers recorded from a real backend scenario | Dashboard Learn mode, offline-capable |
| Render-check and tutorial seeds | `tools/render-check/*.sql`, `record_tutorial.mjs`, `render_check.mjs` | Fabricated field currents and tutorial state, disposable-DB guarded | Headless-Edge dashboard audits |
| Demo scenario beats | `backend/app/demo/scenarios.py` | Deterministic squall, drift, and incident beats per run id | Demo-mode API and dashboard |
| Field-eval manifest (template) | `manifests/field_eval_manifest_v1.json` | Normal trip plus 2 controlled drill drifts, placeholder hashes | Calibration validation tests |
| Eval results (synthetic calibration) | `backend/app/ai/models/eval_results.json` | Drift containment 0.875, squall P0.286/R0.133, anomaly FAR 1.0 | Dashboard SAR Metrics tab |
| Live telemetry tables (empty until field) | `buoy_contacts`, `current_observations`, `barometric_readings` | Real rows only via gateway key; `qualified` auto-downgraded to `uncalibrated` | Anomaly, squall, and drift live gates |

No GEBCO, IBTrACS, or ERA5 raw files live in the repo; only API access plus hashes and features in the model card.
No production buoy time series or AIS data exists in the repo.

## 8. Real vs synthetic, and what is not yet field-proven

Every operational row carries `is_synthetic`, telemetry adds `source: live|synthetic`, and the UI badges LIVE, DEMO, TUTORIAL, and synthetic-replay states explicitly.
Production readers accept only live rows: anomaly needs live contacts, squall needs 3 fresh live buoys, drift needs live qualified currents, and downlink never carries synthetic incidents.
Synthetic wind or current is substituted only with a `degraded` flag, never silently, and SMS escalation audits even when the provider keys are unset.
Not yet proven in the real world: phone-offline SOS over LoRa end to end, ack/ETA reaching a handset, signed-frame replay on hardware, power-cycle store-and-forward, multi-hop relay, any buoy in the water, any measured on-water radio range, and live AI operation (all three models await field-baseline review).
The deployed backend health endpoint is green, and the dashboard flows are software-verified with backend, web, and render-check suites passing.
