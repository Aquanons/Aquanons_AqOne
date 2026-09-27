# AqOne: One Trip, Many Data Paths

**Purpose:** A story and data-flow brief for teammates who will present or explain AqOne.

**Audience:** Technical and non-technical teammates.

**Evidence date:** 2026-09-25, the date of the newest status evidence in the repository.

**Story status:** The fisher and incident below are illustrative, not a report of a real rescue.

This brief follows one fisher through a trip and shows what the system does behind each visible moment.

It also describes the related data flows that support safety, response, weather awareness, communication, and optional fisheries information.

It distinguishes implemented software from paths that have not been verified on current field hardware.

## The story in one sentence

A fisher leaves shore with weather information, loses cellular service, uses a nearby boat pod to hand off an SOS, and gives MDRRMO a better chance to learn about the emergency and respond, while AqOne reports exactly what has and has not been delivered.

## The cast and the system

- **The fisher** uses the AqOne mobile app and a shared boat safety pod.
- **The boat pod** connects to the phone over short-range WiFi, queues distress messages, and uses LoRa to reach shore.
- **Optional stationary buoys** can relay LoRa traffic or collect fixed environmental measurements where their placement is useful.
- **The shore gateway** receives LoRa traffic and has an internet connection to the backend.
- **The AqOne backend** validates and stores events, maintains current incident state, runs background evaluations, and serves authorized views.
- **The MDRRMO responder** uses the authenticated dashboard to review, acknowledge, update, and resolve incidents.
- **The on-call responder** may receive an SMS for an unanswered SOS when the SMS provider is configured.

The fisher does not need a mobile account to send an SOS.

The SOS path is deliberately independent of catch participation and AI model availability.

Operator accounts, paired vessel-device credentials, and gateway API keys serve different purposes and are not interchangeable.

## Scene 0: Prepare to go out

### What the fisher sees

Before leaving, the fisher checks current weather, the forecast, and any published local advisories or MDRRMO sea-condition notices.

The app may have previously cached some map and feed data, with its age shown so older information is not mistaken for live conditions.

### What happens under the hood

- Current conditions and forecasts come from Open-Meteo sources, either through the backend forecast proxy or the app's provider fallback.
- The backend forecast response is a transparent weather and marine-data proxy; it does not currently provide a fused server-side forecast risk model.
- Where the backend does not supply a risk block, the handset can apply its own forecast scoring logic.
- A responder-authored advisory is published through the operator API and served to the public mobile feed only while it is active.
- An MDRRMO sea condition is a separate human-declared status with its own public read route.
- The app caches selected feeds and timestamps for offline display.
- The bundled offline MBTiles map pack is documented as not yet generated, so cached viewed tiles and feed snapshots are not the same as a complete offline map package.

### What to say

“The phone can prepare with weather and local notices while it has a connection. AqOne shows where that information came from and whether it may be old.”

Do not call every weather score an AI prediction or an official PAGASA warning.

The phone's simple wind threshold is an indicator, not an official warning.

## Scene 1: Leave cellular coverage

### What the fisher sees

At sea, the phone loses cellular service.

It can still join the nearby boat pod's local WiFi network while the devices are within WiFi range.

### What happens under the hood

- The phone has no LoRa radio, so it does not communicate directly with the shore gateway.
- The phone-to-pod link is local WiFi and HTTP.
- The pod-to-shore link is LoRa.
- The shore gateway is the standard bridge from the radio mesh to the backend over HTTPS.
- A stationary buoy is an optional LoRa relay or fixed sensor station, not the default place a phone must find WiFi.
- The network is opportunistic store-and-forward, not guaranteed continuous connectivity.

### Routine contacts and overdue-trip monitoring

The system has a gateway-authenticated contact-event contract for recording that a vessel passed a buoy during a trip.

Those records can feed trip-profile and overdue review, but a contact record is not a distress call.

The backend evaluator uses live contacts in production, excludes handset-only contacts as sufficient evidence on their own, and reports when there is no recent qualifying contact source.

An overdue or anomalous trip becomes a responder review case.

It does not automatically become an SOS or dispatch a rescue.

The current status does not establish a live, end-to-end field source for routine vessel contacts or a verified handset trip/check-in flow.

Describe this as a software path and intended safety input, not as continuous live tracking.

## Scene 2: The fisher raises an SOS

### What the fisher sees

The fisher presses the SOS button in the app.

The phone records the incident locally before trying to send it.

The app can show whether the message is still saved, accepted by the pod, delivered to the backend, or acknowledged by a responder.

The pod also has a physical SOS button as an alternate distress origin.

### What happens under the hood

1. The app creates a local outbox record with a local incident ID, vessel ID, client timestamp, a once-per-incident nonce, and the available GPS position.
2. The SOS record is written to the phone's SQLite outbox before transport attempts begin.
3. The app initially attempts the pod and direct backend routes concurrently when both are due.
4. With the phone in airplane mode, the direct HTTPS attempt cannot reach the backend, but the local WiFi path to the pod can still work.
5. The phone posts the SOS to the pod's `/v1/sos` endpoint.
6. The pod validates the basic request, saves it in its flash-backed queue, allocates its radio sequence, then acknowledges the phone.
7. That response means “the pod accepted and queued this message.” It does not mean the gateway or MDRRMO has received it.
8. The pod transmits an SOS LoRa frame toward shore and retries while the frame remains eligible for delivery.
9. If direct LoRa coverage is unavailable, optional relay nodes can use bounded TTL forwarding and duplicate suppression.
10. SOS frames take priority over routine chat, warning broadcasts, and beacons on the radio channel.

### The four delivery states

| State | Meaning | Evidence that permits the state |
|---|---|---|
| `saved` | The phone has the SOS, but no route has handed it to a pod or backend. | The local outbox record exists. |
| `relayed` | A pod accepted the SOS into its queue. | The pod returned an accepted response. |
| `delivered` | The backend ingested the incident. | Backend event state and delivery projection. |
| `acknowledged` | A responder acknowledged the incident. | Persisted backend acknowledgement. |

The phone must not translate pod acceptance into “MDRRMO received it.”

While an SOS remains `relayed`, the app continues direct-path retries on its backoff schedule and may retry both paths after the pod-delivery deadline.

The backend merges duplicate arrivals so the same incident received over direct internet and the mesh should not create two separate SOS records.

### What to say

“The phone saves the call first. The pod's reply tells us only that it has the call in its queue. We wait for the backend before saying the response team has received it.”

## Scene 3: The SOS reaches shore and the dashboard

### What the responder sees

The new SOS appears in the dashboard's active feed with available location, note, vessel context, delivery provenance, and any advisory plausibility flags.

The dashboard distinguishes live and synthetic records.

### What happens under the hood

1. The shore gateway receives and verifies the LoRa frame.
2. It converts the frame payload to the backend's SOS request shape and sends it to `POST /api/sos` over HTTPS.
3. The gateway supplies its API key so the backend can trust mesh provenance fields such as the source radio and sequence.
4. The backend accepts SOS ingest without requiring a fisher login.
5. The backend validates fields, applies incident deduplication and merge rules, writes the event record, and updates the current SOS projection.
6. If the same call had already arrived directly from the handset, the backend merges the second route's delivery details into that incident.
7. The dashboard authenticates as an operator and polls `GET /api/sos/active` every three seconds.
8. The dashboard uses the successful poll time to show live, stale, or offline feed status.
9. The responder can acknowledge, set an ETA and response status, add a short note, resolve the incident with a reason, or reopen it when appropriate.
10. High-impact responder actions are persisted and recorded in the operations audit log.

The dashboard's active SOS view is polled, not currently driven by SSE.

The backend has SSE support in the public API contract, but the current dashboard code uses polling for its SOS feed.

### Trust and safety checks

- An SOS is not rejected just because the caller has no account.
- A self-declared identity stays self-declared unless the backend has stronger device or responder evidence.
- Gateway-reported mesh provenance is trusted only when the request carries the valid gateway key.
- Position and timing plausibility flags are advisory; they do not hold the SOS back.
- Duplicate or repeated arrivals are merged rather than treated as separate calls when they match the incident identity.

### What to say

“The shore gateway gives the radio message an internet path. The backend records it once, and the dashboard checks for new calls every few seconds.”

## Scene 4: A second alert path for the responder

### What the on-call responder would receive

If a real SOS remains unacknowledged and unresolved for at least two minutes, the backend scheduler attempts an SMS to configured on-call numbers.

The text identifies the vessel or boat, includes a position when available, and gives the reported time.

### What happens under the hood

- A backend background scheduler checks for due SOS escalations about every 30 seconds.
- Synthetic SOS events are excluded.
- The event is claimed before the notification attempt so concurrent scheduler instances do not both send it.
- The backend sends through Semaphore when both the API credential and on-call number list are configured.
- The notification outcome is recorded in the operations audit log.
- A failed provider request releases the escalation claim so a later scheduler pass can retry.
- A not-configured result is audited but does not send a text.

The latest status says Semaphore credentials and on-call numbers are not configured.

The SMS branch is implemented in software, but no live SMS delivery should be claimed in the demo until the provider is configured and a delivery is observed.

SMS notifies on-call responders; it is not the channel that carries the responder's acknowledgement back to the fisher.

## Scene 5: The responder's answer travels back

### What the fisher may see

The fisher may see a responder status, an ETA, and a note.

The response may reach the app directly over internet or return through the radio path to the pod and then over local WiFi.

### What happens under the hood

1. The gateway polls the authenticated `GET /api/sos/downlink` endpoint for eligible open or recently resolved incidents.
2. The backend returns a compact, gateway-appropriate response, not the full private dashboard feed.
3. The gateway encodes an ETA/status frame and sends it over LoRa when the responder's information changes.
4. The pod caches the returned state and serves it from its local `/v1/sos/status` endpoint to a phone connected over WiFi.
5. The app matches the response to its outstanding outbox incident using the available radio sequence or incident identifiers.
6. When the backend is reachable directly, the app reconciles its local outbox from the backend instead.
7. The fisher can send `STILL_IN_DANGER` or `SAFE_NOW` when a response record is available; the reply is saved locally first and synchronized over an available backend path.

The handset reply is not currently carried from the pod back to shore over LoRa.

The return path exists in current source, but the latest evidence says the current shore firmware has not been reflashed and an acknowledgement has not been observed reaching a handset.

Present the return as an implemented software path awaiting current-device verification, not as a completed live hardware demonstration.

## Scene 6: If the event starts as a missed return

An SOS is the fisher's direct call for help.

A trip-anomaly case is a separate process that may help a responder notice a missed expected contact.

### What happens under the hood

1. A gateway-authenticated routine contact event records a vessel, trip, buoy, observed time, and optional location.
2. A scheduled backend evaluator compares a vessel's current trip/contact history against causally prior history.
3. Stale data, insufficient history, no recent contact source, and synthetic inputs must remain visible as limitations rather than silently becoming a live emergency.
4. The system can create or refresh a persistent responder-review case with its source, age, reasons, and confidence/status.
5. A responder reviews the case and may acknowledge, dismiss, escalate, or resolve it.
6. Escalating an anomaly is a human action and does not itself dispatch a rescue.
7. Only an acknowledged SOS or a human-escalated anomaly may be used to open a real drift/search case.

The anomaly evaluator is scheduled separately from the SOS SMS job.

The latest code starts the anomaly evaluation job every five minutes, while the SOS SMS job checks every thirty seconds.

No live field contact source has been established in the current status evidence, so do not stage a real boat's overdue warning as live tracking.

## Scene 7: Search support after human confirmation

Drift prediction belongs after a responder has confirmed an incident for search review.

It is not a live tracker, automatic dispatch system, or guarantee of where a person will be found.

### What happens under the hood

- The responder opens a drift case only from an acknowledged SOS or a human-escalated anomaly.
- The position and fix time come from the source event; a caller cannot substitute an arbitrary position.
- The responder selects the object class, such as a person in water or a damaged boat.
- The backend checks for usable wind and observed current support before producing a real-case run.
- If current observations or field geometry do not meet the quality policy, the system records insufficient environmental data and returns no search contour.
- If the run qualifies, the physics-based simulation produces a probability distribution and 50%, 75%, and 95% contours for responder review.
- A responder can record the area and time searched; a negative search result can update the posterior distribution for that run.
- The next-area result is a recommendation for human review, never an assigned crew, route, or autonomous dispatch.

The current status says fixed buoys, current measurements, and in-water drift validation are pending.

The real-case quality gate should therefore be expected to abstain when those field inputs are unavailable.

## Parallel flow: localized weather and warnings

These related weather flows should be explained separately because their origins differ.

### Forecast and current weather

- The mobile app fetches weather information from Open-Meteo sources, directly or through the backend forecast proxy.
- The backend proxy currently returns source data rather than a server-side fusion model.
- The handset may calculate its own simple forecast risk score from available fields.
- Missing wave information remains unknown rather than being replaced with calm conditions.
- Cached data can be shown offline with its age; stale hazard data is not proof that conditions are safe.

### Human-authored official advisories

1. An authorized operator drafts or publishes an advisory.
2. The public backend feed serves only notices that are published, active, and not expired.
3. When online, the app can read the public feed and cache it.
4. The shore gateway polls active advisories and selects `Warning` and `Emergency` priority items for LoRa broadcast.
5. A pod or relay buoy can cache and forward an unexpired warning.
6. A phone connected to a pod can retrieve its cached warnings locally.
7. Warning delivery states track each hop separately; receiving a packet does not prove the fisher read or understood it.

This radio warning path is currently driven by the published advisory feed.

Do not imply that every model alert is automatically converted into an offline LoRa warning.

### Squall nowcast

- The backend accepts pressure-event telemetry through a gateway-keyed route and distinguishes live from synthetic readings.
- The live squall endpoint checks timestamp freshness, buoy count, and array geometry before reporting a result.
- An insufficient array reports `unknown`, not `clear`.
- The model's calibration is documented as synthetic, and a live `RETURN NOW` alarm is gated off unless its deployment flag and field-approval gate are satisfied.
- The mobile app polls the public squall endpoint when it can reach the backend and can show an alarm for an eligible `RETURN NOW` state.
- The mobile squall fetch has no pod-cache fallback in the current code, so do not promise an offline squall alarm over the mesh.
- The latest status says physical fixed-buoy observations and local field validation are pending.

### Danger-zone model

The dashboard has a browser-side marine risk model that evaluates weather inputs for map sectors and provides readable reasons.

Its historical inputs are environmental proxies, not locally collected New Washington outcomes.

Describe it as prototype decision support, not a prediction that a particular boat will capsize.

## Parallel flow: nearby-boat group chat

Chat is an everyday communication feature and is separate from SOS delivery.

- A handset can submit a chat line directly when it has internet or through the pod/gateway mesh path.
- The backend stores the message with an origin derived from available credentials; the responder dashboard and authorized listeners can read it.
- Messages are group-visible, not private messages to family.
- The mesh does not preserve a stable message ID end to end, so duplicate display is a known limitation.
- Current mesh chat requires the updated shore gateway authentication behavior; the status says the gateway must be reflashed before chat to boats can be restored and verified.

Chat must never be narrated as the SOS channel or as confidential communication.

## Parallel flow: voluntary catch activity

Catch activity is purpose-separated from safety traffic.

It must not be a condition for sending an SOS, receiving a warning, or receiving rescue assistance.

### Intended flow

1. A fisher records species, estimated amount, date, optional method/notes, and optional location.
2. The handset queues the entry while offline and synchronizes it over cellular or ordinary WiFi when possible.
3. The backend checks the vessel-device credential and stores the initial estimate idempotently.
4. A later reweighed amount is a separate confirmation update.
5. A public hotspot view groups eligible recent reports into coarse cells and withholds cells below its independent-vessel threshold.
6. The published surface is relative reported catch activity, not a guarantee of fish abundance or a safety signal.

### Current limits

- The latest README says backend catch intake and hotspot aggregation exist, but there is no catch-entry screen or current handset catch service/outbox flow.
- The catch endpoint requires a vessel-device credential.
- The per-entry `share_for_hotspots` field defaults to false, but the responsible-data plan says durable consent provenance and withdrawal handling remain incomplete.
- Current hotspot code uses a three-vessel threshold, 0.02-degree cells, and a thirty-day window.
- Some architecture documentation says five contributors and different cell sizing; the code and current endpoint response are the better evidence for current behavior.

Present this as an incomplete product lane, not a demonstrated fisher journey.

Catch records are not sent over LoRa.

## Evidence labels for the demo

Use one of these labels whenever a scene or screen could be mistaken for field proof.

| Label | Meaning | Current examples |
|---|---|---|
| **Software verified** | The code path is covered by current software checks, but that alone does not prove field operation. | Backend and dashboard software; mobile software; SOS state and responder controls. |
| **Bench reported, current build not re-run** | An earlier bench session reported success, but current firmware has changed and no current-device run is recorded. | Pod-to-shore SOS bench path and gateway downlink work. |
| **Implemented, not field verified** | Source and contracts exist, but the physical path has not been demonstrated on current hardware. | Airplane-mode phone-to-dashboard SOS; acknowledgement/ETA reaching the phone; warning over LoRa; mesh chat. |
| **Prototype / research** | Software exists, but live local calibration or field inputs are not validated. | Squall, trip anomaly, drift support, and danger-zone risk. |
| **Not end to end in the app** | A backend capability exists without the complete user-facing path. | Catch logging and hotspot contribution. |
| **Not configured** | A feature cannot perform its external side effect in the current environment. | SMS provider delivery. |

The latest project status says the full phone-in-airplane-mode to pod to shore to dashboard journey has not yet been run on real devices.

Keep that limitation visible if a screen recording, staged data, or synthetic scenario stands in for a live run.

## Documentation and implementation differences to keep visible

The repository contains historical and target-architecture text that does not always match the current implementation.

For this story, use the README for current project priority, the canonical PRD for scope, the relevant contract for intended interfaces, and the newest dated status plus current code for what has actually been observed.

Material differences found while tracing the flow:

1. Older architecture text describes the dashboard's SOS updates as SSE; the current dashboard polls `GET /api/sos/active` every three seconds.
2. The gateway ingest contract describes `POST /api/v1/ingest`; current shore firmware posts SOS directly to `POST /api/sos` with gateway provenance.
3. The LoAM spec says 433 MHz, while the current firmware and firmware README say 915 MHz; the RF budget doc still marks the band unresolved.
4. The technical flow spec describes a five-reporter catch threshold; current hotspot code uses three distinct vessels.
5. Some older scope/architecture text says catch logging is queued on the handset; the latest README and mobile source indicate the handset screen and upload flow are not present.
6. Older responder-loop documentation says the mesh return path is absent; current source contains an ETA downlink path, but current-device handset receipt has not been verified.
7. The active scope includes weather/advisory, trip, AI, and catch-related work that older architecture and scope summaries still describe as excluded or complete more broadly than current status supports.

These are not cosmetic disagreements.

The story should not silently resolve them by presenting a target design as an observed field result.

## Recommended presentation structure

For each scene, keep two tracks visible:

- **Human track:** what the fisher or responder sees, chooses, or learns.
- **Data track:** what device accepted the event, where it traveled, what the backend stored, and which state has evidence.

Recommended sequence:

1. Introduce the cellular dead-zone problem and the shared boat pod.
2. Show weather/advisory preparation, identifying sources and data age.
3. Put the handset in airplane mode and explain the local WiFi handoff.
4. Trace the SOS from phone outbox to pod, LoRa, gateway, backend, and MDRRMO feed.
5. Explain `saved`, `relayed`, `delivered`, and `acknowledged` as evidence-based states.
6. Show responder acknowledgement and ETA, labeling the mesh return as pending current-device verification.
7. Show SMS as a separate unanswered-call escalation branch and state that provider credentials are not configured.
8. Close with the separate warning, overdue-review, search-support, chat, and catch lanes, each labeled with its current evidence status.

This keeps the SOS as the emotional story while still giving technical teammates a truthful map of the system around it.

## Source documents

- [Current project README](README.md)
- [Documentation index and source-of-truth order](docs/SPEC_INDEX.md)
- [Canonical product requirements document](docs/Aqone_PRD%20(2).md)
- [Current demo status and evidence ledger](docs/08_DEMO_AND_STATUS.md)
- [Hybrid transport decision](docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md)
- [Technical architecture and data-flow specification](docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md)
- [LoAM frame contract](docs/02_LOAM_PACKET_SPEC.md)
- [Phone-to-pod contract](docs/03_PHONE_BUOY_WIFI.md)
- [Gateway ingest contract](docs/04_INGEST_API.md)
- [Public REST and SSE contract](docs/05_PUBLIC_API.md)
- [SOS delivery-state definitions](docs/06_DELIVERY_STATES.md)
- [Responder loop and return-path notes](docs/13_RESPONDER_LOOP.md)
- [AI explanation and limits](docs/17_AI_EXPLAINED_SIMPLY.md)
- [Scope amendments](docs/07_SCOPE_OUT.md)
- [AI accuracy and data protocol](docs/49_AI_ACCURACY_DATA_PROTOCOL.md)
- [Field readiness and measurement handoff](docs/54_FIELD_READINESS_AND_MEASUREMENT_HANDOFF.md)
