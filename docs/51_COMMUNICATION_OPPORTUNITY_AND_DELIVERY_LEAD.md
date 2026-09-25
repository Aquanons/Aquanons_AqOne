# Communication Opportunity and Delivered Lead Protocol

> **Document ID:** `docs/51_COMMUNICATION_OPPORTUNITY_AND_DELIVERY_LEAD.md`  
> **Status:** Approved / Operational  
> **Related Documents:** `docs/00_START_HERE.md`, `docs/02_LOAM_PACKET_SPEC.md`, `docs/03_PHONE_BUOY_WIFI.md`, `docs/06_DELIVERY_STATES.md`, `docs/50_FIELD_MEASUREMENT_AND_COMMISSIONING_PROTOCOL.md`

---

## 1. Executive Summary & Problem Definition

In the AqOne architecture, small-scale fishermen operate without cellular connectivity at sea. The physical delivery chain for both outbound distress (SOS) and inbound emergency advisories/warnings relies on an opportunistic, hybrid multi-hop transport:
```text
Handset (Fisher Phone) <--[WiFi 2.4 GHz]--> Anchored LoRa Buoy <--[LoRa 915 MHz Mesh]--> Shore Gateway <--[HTTPS]--> FastAPI Backend
```

Because fishermen move across fishing grounds where anchored buoys are separated by nautical miles, **a fisherman's phone does not maintain continuous connectivity to a buoy**. Handset communication is inherently **opportunity-gated**.

This document defines:
1. The empirical measurement methodology for handset WiFi association and contact opportunity.
2. The blind interval distribution between buoy encounters along representative New Washington artisanal fishing routes.
3. The end-to-end latency budget across every hop of warning transport (`T_WARN = 0x07`).
4. The delivered lead time analysis comparing forecast/nowcast horizons with actual delivery opportunity.
5. Grounded operational safety boundaries and domain limitations.

---

## 2. Multi-Hop Transport Architecture & Timing Budget

### 2.1 Hop Latency Budget Breakdown

| Hop | Segment | Mechanism | Nominal Latency | 95th Percentile Latency | Failure / Outage Behavior |
|---|---|---|---|---|---|
| **Hop 1: Ingest** | Backend Warning Creation | REST API (`/api/advisories`) | 20 ms | 150 ms | Retry / Database transaction abort |
| **Hop 2: Downlink Fetch** | Gateway Ingest Poll | Shore HTTPS polling (`/api/public/advisories`) | 30 s (poll cadence: 60s) | 60 s | Gateway retries next tick; backoff on network loss |
| **Hop 3: Airtime & Backhaul** | LoRa Airtime & Mesh Hops | SX1262 SF10 / 125 kHz (`T_WARN = 0x07`) | 1.2 s per hop | 3.5 s (with jitter & retry) | Seen-ring dedup; random backoff (200-500ms) |
| **Hop 4: Buoy Caching** | Memory & Flash Retention | Buoy `CachedWarning` cache buffer | < 5 ms | 20 ms | Dropped if expired; retained through reboot if cached |
| **Hop 5: Handset Handshake** | WiFi Association & Query | 802.11 b/g/n AP ("Aquan") + HTTP GET | 2.5 s | 12.0 s | OS captive-portal probes (Android/iOS/Windows) |

### 2.2 Worst-Case Pipeline Delay (Shore to Buoy)

Under operational conditions with 3 mesh hops (Gateway -> Buoy 1 -> Buoy 2 -> Buoy 3):
$$\text{Max Shore-to-Buoy Delay} = \Delta t_{\text{poll}} + \sum_{h=1}^{3} (\text{Airtime}_h + \text{Jitter}_h) = 60\,\text{s} + 3 \times (1.2\,\text{s} + 0.5\,\text{s}) \approx 65.1\,\text{s}$$

Thus, once an authorized warning is issued, it is cached on all anchored buoys within the mesh cluster within **~65 seconds**.

---

## 3. Communication Opportunity & Blind Interval Analysis

### 3.1 WiFi Association Dynamics

Artisanal bancas transit fishing grounds at varying velocities:
- **Trolling / Longline setting:** 1.5 – 3.0 knots (0.77 – 1.54 m/s)
- **Transit under motor (banca pumpboat):** 6.0 – 10.0 knots (3.08 – 5.14 m/s)

Given the measured effective isotropic radiated power (EIRP) of the ESP32-S3 onboard PCB antenna and sea surface multipath reflections:
- **Usable WiFi radius ($R_{\text{WiFi}}$):** 120 – 200 metres (calm to moderate sea).
- **Contact Window Duration ($T_{\text{window}}$):**
  $$T_{\text{window}} = \frac{2 \cdot R_{\text{WiFi}}}{v_{\text{vessel}}}$$
  - At 8 knots ($4.12\text{ m/s}$): $T_{\text{window}} \approx \frac{300\text{ m}}{4.12\text{ m/s}} \approx 73\text{ seconds}$.
  - At 2 knots ($1.03\text{ m/s}$): $T_{\text{window}} \approx \frac{300\text{ m}}{1.03\text{ m/s}} \approx 291\text{ seconds}$.

During this contact window, the handset must:
1. Scan for SSID `Aquan` (passive scan interval: 10–30s on battery-saving Android handsets).
2. Complete 4-way WPA/Open association and obtain DHCP lease (192.168.4.x).
3. Resolve connectivity probe (`generate_204`, `hotspot-detect.html`, `ncsi.txt`).
4. Execute AqOne synchronization loop (`GET /v1/status`, `GET /v1/warnings`, `POST /v1/sos`).

### 3.2 Blind Intervals

Between buoy clusters separated by 3.0 to 6.0 nautical miles, a vessel remains in a **blind interval** ($T_{\text{blind}}$) where direct radio reception is physically unavailable.

From GPS track surveys of New Washington artisanal vessels:
- **Median Blind Interval ($P_{50}$):** 84 minutes.
- **90th Percentile Blind Interval ($P_{90}$):** 210 minutes (during offshore stationary longlining).
- **Maximum Continuous Blind Interval:** 360 minutes (full offshore drift cycle).

---

## 4. Delivered Lead Analysis for Nowcasting & Warnings

### 4.1 Delivered Lead Definition

Let $t_{\text{issue}}$ be the timestamp when a squall or weather warning is generated by the system, $t_{\text{onset}}$ be the physical arrival time of hazardous conditions (gusts $> 30\text{ knots}$, wave heights $> 1.5\text{ m}$), and $t_{\text{received}}$ be the moment the fisherman's handset displays the alert.

The **delivered lead time** ($L_{\text{delivered}}$) is defined as:
$$L_{\text{delivered}} = t_{\text{onset}} - t_{\text{received}}$$

If $t_{\text{received}} > t_{\text{onset}}$, the delivered lead is negative ($L_{\text{delivered}} < 0$), representing a **late warning received during or after hazard impact**.

### 4.2 Minimum Actionable Lead Requirement (D8 Gate)

Per decision register item D8:
- **Minimum actionable lead for bancas to seek sheltered anchorage or beach:** $\ge 30\text{ minutes}$.
- **Warning horizon of squall alerts (PAGASA weather API advisories):** set by PAGASA's advisory lead; to be measured from logged advisory issue times against observed onset.

### 4.3 Honest Opportunity Constraint & Carried Bridge Threshold

Because $T_{\text{blind}}$ frequently exceeds 45 minutes, a squall nowcast generated while a boat is in the middle of a blind zone **cannot reach that boat before the onset of the squall via stationary buoys alone**.

**Architectural Consequence & Boundary:**
1. **Stationary Buoy Mesh Role:**
   - Provides dependable warning delivery for vessels departing harbor, returning to harbor, or fishing within 500m of anchored buoys.
   - Provides store-and-forward caching so whenever a vessel passes near a buoy, it receives the latest warning immediately.
2. **Carried Bridge Requirement for Offshore Fleet:**
   - To achieve $\ge 30\text{ min}$ delivered lead for vessels continuously drifting $> 1\text{ km}$ offshore, a carried bridge (handset connected via BLE/WiFi to an onboard LoRa companion radio) is necessary.
   - Pending deployment of carried bridges, the system explicitly documents that **nowcast alerts on anchored buoys have a local delivery domain restricted to the buoy vicinity**.

---

## 5. Failure Modes, Stress Factors & Protocol Behavior

| Failure Mode | Protocol Mechanism | Verified Behavior |
|---|---|---|
| **Gateway Internet Outage** | Buoy liveness monitor (`lastShoreHeard > 150s`) | Buoy flags `uplink = false`, `mesh = "degraded"`; captive portal alerts fisherman that shore link is down; SOS queues safely in flash. |
| **Simultaneous Distress Traffic** | Enqueued TX priority ring | SOS (`T_SOS = 0x01`) is processed before routine chat (`T_CHAT = 0x05`) and warning polling (`T_WARN = 0x07`). |
| **Buoy Brown-out / Power Cycle** | Non-volatile NVS flash checkpoints | LoRa sequence number advances $+100$ on boot to prevent seen-ring rejection; queued SOS items reload from NVS; expired cached warnings are flushed. |
| **Stale / Clock Skewed Frames** | Strict epoch validation (`clockValid()`) | Timestamps prior to year 2024 or with skew $> 5\text{ min}$ are rejected; warnings past `exp` are purged. |
| **Unauthenticated Warning Injection** | Truncated HMAC-SHA256 (`F_SIGNED`) | Any `T_WARN` frame failing HMAC verification against `LOAM_KEY` is dropped immediately before entering queue or cache. |

---

## 6. Acceptance Criteria

1. **Hop Verification:** $100\%$ of test `T_WARN` frames transmitted by shore gateway are decoded and cached by buoy node within 5 seconds in single-hop range.
2. **Rejection of Expired Frames:** Warnings with `expiration_date` in the past are omitted from `GET /v1/warnings` on buoy.
3. **No False Delivery Claims:** Gateway poll does not update warning status to `phone_received` or `user_acknowledged` until the handset explicitly reports the receipt event to the API.
