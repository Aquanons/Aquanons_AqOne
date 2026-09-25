# Aqone — Product Requirements Document

**A hybrid boat-pod and stationary-buoy maritime mesh network with AI search-and-rescue support for Philippine municipal fishers**

| | |
|---|---|
| **Version** | 3.0 |
| **Date** | August 2026 |
| **Submission** | AI Fest |
| **Status** | Concept / PRD |

---

## 1. Summary

Aqone is a hybrid network of boat-mounted LoRa safety pods, stationary sensor buoys, optional relay buoys, and a tall shoreline gateway that reduces communication dead zones in Philippine municipal waters. An AI layer predicts the weather that kills small boats, detects when a boat has failed to return before anyone reports it missing, and narrows the water where a missing person is still alive.

The radio network is the product's foundation. Boat pods are the primary SOS origin; stationary buoys provide fixed environmental observations and optional relay coverage. The AI is what the network makes possible — and what nothing else can do without it.

**One line:** *Aqone gives municipal boats a strap-on safety link to shore, while stationary buoys sense the water — forecasting the squall, noticing the boat that never came back, and shrinking the search area while someone is still alive.*

---

## 2. The problem

### 2.1 Two million people work in a communications void

Over 2.5 million fisherfolk are registered with BFAR's FishR / FishCore system as of 2024, the overwhelming majority of them municipal small-scale fishers operating wooden-hulled outriggers within 15 km of shore — though many range well beyond it.

Cellular coverage from shore-based towers extends roughly 16–24 km (10–15 miles) offshore at best, and degrades sharply before that. There is nothing to mount a tower on at sea, and the curvature of the Earth caps the range regardless of tower density. The result is a hard connectivity edge that municipal fishers routinely cross, and beyond which they have no way to call for help. Communities as significant as Pag-asa Island — 480 km west of Puerto Princesa, home to 184 civilians, mostly fisherfolk — have depended on analog radio and intermittent roaming for basic contact with the mainland.

A fisher in trouble beyond that edge has three options: a handheld VHF radio with limited range and no guarantee anyone is listening, a flare, or nothing.

### 2.2 The delay between the incident and the alarm is the thing that kills

Because there is no way to signal from beyond the coverage edge, a distress event is usually not reported when it happens. It is reported when the boat fails to come home — often many hours later, sometimes the next morning.

By then the search does not begin from a position. It begins from a guess about a departure heading, and the target has been drifting the entire time. The cases follow a consistent pattern:

- **February 2026, Occidental Mindoro** — four fishers suffered engine failure and drifted for five days. Three were rescued alive; one was found dead.
- **August 2025, Zambales** — a fisher was recovered after three days adrift in the South China Sea.
- **Typhoon Ragasa, off Cagayan** — the fishing vessel *Jobhenz* capsized in deteriorating weather with 13 crew aboard. Seven died; six survived.

These are the incidents that reached national reporting. The Philippine Coast Guard is the designated national maritime SAR authority, but no comprehensive public dataset aggregates municipal fisher deaths and disappearances at sea. **The absence of that dataset is itself part of the problem** — a hazard that isn't measured doesn't get budgeted against.

### 2.3 Why existing options don't close the gap

| Option | Why it fails for municipal fishers |
|---|---|
| **VHF radio** | Line-of-sight range, requires someone monitoring the channel, requires a conscious operator, no position data |
| **Satellite EPIRB** | Unit and subscription costs are prohibitive at municipal fisher income levels |
| **Mobile phone** | No signal past ~20 km — the exact scenario where help is needed |
| **Satellite messengers** | Recurring subscription, individual purchase, no local SAR integration |

Most of these require the fisher to buy and carry dedicated hardware. **Aqone keeps the pod shared and easy to strap on, while retaining fixed shoreline and buoy infrastructure; the fisher uses the phone already in their pocket.**

---

## 3. Users

| User | Need | What Aqone gives them |
|---|---|---|
| **Municipal fisher** | Contact with shore; not dying | Messaging and weather beyond the coverage edge through a shared boat pod; SOS from their own phone |
| **Fisher's family** | To know the boat is safe | Check-in visibility; notification on alert or overdue return |
| **Philippine Coast Guard** | Actionable position, not a search area the size of a province | Last-contact position and timestamp, drift-narrowed probability field, prioritized tasking |
| **BFAR / LGU** | Maritime safety compliance; fleet visibility | Trip telemetry; incident data; measurable safety outcomes |

**Buyer note:** the fisher is the user, not the customer. Aqone is maritime safety infrastructure procured by BFAR, the PCG, or LGUs — the same channel that already funds and maintains navigation aids — not a consumer product sold one unit at a time.

---

## 4. The system

### 4.1 Architecture

```
    Fisher's phone
       (Aqone app)
             |
       local WiFi
             |
       [ BOAT POD ] -------- direct LoRa --------┐
       SOS button, GPS                            |
                                                  v
     [ OPTIONAL STATIONARY SENSOR / RELAY BUOYS ]
             GPS, optional relay                  |
                                                  v
                         Tall shoreline gateway
                    (coastal barangay, BFAR station)
                        |
                 Aqone backend  <──── PAGASA weather API
        (squall alerts · trip anomaly · drift model)
                        |
         PCG / BFAR operations console
```

### 4.2 Field nodes

The system has two field-node forms. The boat pod is the primary SOS origin and
is designed to be shared and strapped onto a participating boat. Stationary
navigational buoys are retained where their fixed sensor data or relay position
has independent value.

#### Boat safety pod

| Component | Purpose |
|---|---|
| LoRa radio | Direct long-range link to the shoreline gateway; optional relay path |
| WiFi access point | Short-range link to the phone on the same boat |
| GPS | Boat/pod position attached to an SOS or telemetry record |
| Physical SOS button | Distress origin even when the phone interaction is difficult |
| Flash-backed queue | Store-and-forward through temporary radio loss or power cycling |
| Battery + waterproof strap-on enclosure | Shared, removable boat deployment |

#### Stationary sensor / relay buoy

| Component | Purpose |
|---|---|
| LoRa radio | Fixed sensor telemetry and optional relay toward shore |
| GPS / surveyed position | Stable location for relay and current observations |
| Current sensing | Optional mooring-line or current-meter measurement |
| Solar + battery | Autonomous operation |

The pod is not a personal device: it is shared equipment that can be moved
between boats. This shifts the deployment problem from placing a WiFi contact
zone around every route to supplying enough pods and strategically justified
fixed nodes.

### 4.3 Connectivity model — honest framing

Phones connect to the boat pod over short-range WiFi. The pod then attempts a
direct LoRa link to the tall shoreline gateway. Where that link is weak,
stationary relay buoys can forward the frame using the existing TTL/seen-set
rules. Coverage is therefore determined by pod-to-shore radio geometry plus
selective relay placement, not by a dense WiFi zone around every buoy. This is
still an opportunistic, store-and-forward network, not always-on connectivity.

This is a real constraint and the PRD treats it as one. It shapes every design decision below, and it is why the detection strategy in §5.2 is built around contact events rather than continuous telemetry.

### 4.4 Everyday value

The network earns its keep without any AI at all: **messages to family queued on
the phone and delivered through the boat pod, and current weather synced on
each successful contact** — in water where there is otherwise no signal.
Stationary buoys add fixed observations and can provide a relay when needed.
Safety is the reason the system exists; connectivity is the reason fishers use
it.

Critically, ordinary use *is* the safety data: every routine check-in builds the trip pattern that §5.2 depends on.

---

## 5. AI components

Three components, mapped to the three phases of a maritime incident. Trip
anomaly and drift consume data produced by the Aqone hybrid radio network.
Squall warnings consume official PAGASA weather data; the buoys carry no
barometer.

---

### 5.1 Before — Squall alerts (PAGASA weather API)

**Problem.** Sudden localized convective squalls are a leading killer of small boats. They develop and strike faster than regional forecast products resolve, and PAGASA has no dense offshore observation network over municipal waters.

**Approach.** The backend pulls official weather data from the **PAGASA
weather API** — thunderstorm advisories, rainfall and wind warnings, and
forecasts covering New Washington and the Aklan coast — with Open-Meteo marine
wind/wave data as a secondary feed. When an advisory covers the fishing grounds,
the backend issues a **RETURN NOW** alert, delivered through the radio network
and to phones when they connect to a boat pod or fixed node. Aqone does not
operate its own pressure sensors: the buoys carry no barometer, and the earlier
buoy-barometer array design has been dropped.

**What this is and is not.** This is an advisory relay: it gets PAGASA's
warning to a boat that has no signal. It is not an independent local forecast,
so its lead time and spatial resolution are PAGASA's, not better. A squall that
PAGASA does not flag, Aqone will not flag.

**Open question.** PAGASA API access, rate limits, update cadence and terms of
use must be confirmed with PAGASA before this is described as live.

**Delivery under intermittent connectivity.** Alerts propagate through the
LoRa network to the shore gateway and optional relay buoys. A boat pod can
receive relevant downstream status when it has a shore path; stationary buoys
can also carry a physical alert — light or audible signal — for a boat in visual
range.

**Why it matters anyway.** PAGASA's warnings already exist; what is missing is
delivery to a boat beyond cellular coverage. Aqone's radio path is that
delivery.

---

### 5.2 During — Trip anomaly and overdue detection

**Design change from v1, stated plainly.** The primary field node is now a
boat-mounted safety pod with a physical SOS button, GPS, local phone WiFi, and
LoRa. It can provide a faster origin event than a phone-only design, but it is
still store-and-forward and does not claim guaranteed second-scale capsize
detection. The pod is shared equipment, not a personal subscription device.

**Problem.** Today the alarm is raised when a boat fails to come home and a family member walks to the Coast Guard station. That is the reporting mechanism, and it is why the drift cases in §2.2 ran for three and five days.

**Approach.** Every phone–pod contact and pod radio event is a logged event:
vessel identity, serving pod or fixed node, timestamp, position, and direction
of travel. From this event stream:

1. **Learned trip profiles.** A per-vessel model of normal behaviour — which
   pods or fixed nodes this boat typically contacts, in what order, at what
   intervals, at what times, under what conditions, with what seasonal
   variation. Municipal fishing is strongly habitual, which makes these
   patterns highly learnable.
2. **Expected next contact.** From the profile and last observed heading, the system predicts where and when the boat should next appear on the network. A missed expected contact is an anomaly — and because the expectation is personalised and learned rather than a fixed timeout, the alert is far earlier and far more specific than "they're not back yet."
3. **Escalation ladder.** A missed contact triggers a silent check-in request
queued at the serving pod and any reachable fixed nodes. Continued silence
combined with adverse conditions, an unusual last heading, or a seaward
trajectory escalates to a scored alert on the PCG console.
4. **Stagnant mode.** [Roadmap — not implemented] A fisher who will stay in
   one spot on purpose (anchoring, longlining) declares a duration from the
   app. Silence-based overdue scoring is held off until that time runs out,
   then the ladder resumes. An SOS always overrides it. See
   `docs/67_STAGNANT_MODE_IMPLEMENTATION_PLAN.md`.

**This is unsupervised anomaly detection over a learned behavioural baseline** — it requires no labelled disaster dataset, only ordinary usage, which the network generates from day one.

**False alarm scoring — non-negotiable.** A system that cries wolf is ignored by the Coast Guard within a month, and is then worse than nothing. Every alert carries a confidence score fusing deviation magnitude, prevailing and forecast weather, the vessel's own historical variability, and corroboration from other boats in the same water. High-confidence alerts dispatch; low-confidence alerts request a check-in first.

**The seed for everything downstream.** Even when detection is slow, the network delivers what no current system can: **a timestamped last-known position on the water.** Today a search begins from a village and a guess. With Aqone it begins from "contact at pod 14, 09:40, heading northwest" or a fixed sensor contact — which is precisely the input §5.3 requires.

---

### 5.3 After — Drift prediction and search allocation

**Problem.** A last-known position is not where the target is. A person or disabled boat moves with current and wind, and the search area expands quadratically with elapsed time. The five-day and three-day drift cases in §2.2 are the direct consequence.

**Approach.** Established SAR practice — the US Coast Guard's SAROPS and the open-source OpenDrift/Leeway framework, which models 275 drifting object classes with distinct downwind and crosswind leeway coefficients — provides the physical backbone. Aqone contributes three things that framework cannot supply on its own:

**(a) Local current fields from the stationary sensor-buoy array.** Global ocean models such as HYCOM operate at roughly 8 km resolution. The Philippine archipelago is straits, channels, and nearshore eddies at **sub-kilometre** scale — these models are effectively blind exactly where fishers die, and nobody has ground-truth data there because instrumenting it has never been economical.

**A moored buoy is a current-measuring station.** Mooring-line tilt and watch-circle excursion respond directly to current, and a fixed station produces a continuous time series at a known coordinate — the highest-value form of oceanographic observation for model correction. An array of them across municipal waters is a persistent current observatory. Aqone learns a downscaled local current field from its own array and uses it to correct the coarse global model.

> **This is the core insight of the stationary sensor layer.** Fixed buoys generate the oceanographic dataset required to find drifting people. Their relay role is useful, but the sensor data remains valuable even when a boat pod can reach shore directly.

**(b) Object classification.** Windage differs enormously between a person in a life vest, a swamped banca, and an inverted fibreglass hull — the same wind pushes them in materially different directions. Aqone infers likely object type from the registered vessel profile, the nature of the alert, and conditions at the time, then selects the corresponding leeway coefficients.

**(c) Bayesian search allocation.** The output is not a point. It is a probability density over water, propagated forward from the last-contact position and timestamp — this part is built, and the 50/75/95% contours come from it.

The re-tasking half is now built. As assets search sectors and report negative findings, `POST /api/ai/drift/incident/{id}/searched` applies the sector's detection probability to the posterior, renormalises, persists the updated grid to `incidents.posterior_grid`, and returns fresh contours — so the search area shifts toward the highest remaining probability mass rather than staying static. Implemented in `backend/app/ai/search.py` (`update_posterior`, `contours_from_grid`), covered by `backend/tests/test_search.py`.

**Survivability weighting.** [Roadmap — not implemented] Predicted time-in-water viability, given sea state and temperature, prioritises tasking when multiple incidents compete for one asset.

**Residual learning.** [Roadmap — not implemented] Every completed rescue is a labelled example: predicted position versus actual recovery position. The drift model improves with every incident it is used on.

---

### 5.4 Why the AI is not decoration

The standard test: remove the AI — does the product still work?

| Component | Without AI |
|---|---|
| Squall alerts | **Still works — not an AI component.** Squall alerts relay PAGASA warnings; the value is delivery beyond cellular coverage, not a model. |
| Trip anomaly detection | **Impossible.** Contact logs without a learned baseline are a database nobody reads. A fixed timeout would drown the PCG in false alarms. |
| Drift prediction | **Impossible.** A last-known position with no drift model is a dot on a map that was wrong an hour ago. |

The hybrid radio network degrades gracefully. If fixed sensor buoys are offline,
drift loses fresh local current observations; if the PAGASA feed is stale,
squall alerts say so rather than reporting calm; if a relay is offline, a
boat pod may still reach the tall gateway directly. The transport layer remains
useful for manual SOS, while model outputs become older or less complete rather
than being presented as live certainty.

---

### 5.5 Mass-casualty dispersion — [Roadmap — not implemented]

**Problem.** When multiple vessels are caught in the same event (typhoon, squall line, grounding), search assets must be allocated across incidents simultaneously, not sequentially. The drift model in §5.3 treats each incident independently; it does not account for shared hazards, overlapping search areas, or the resource constraint of a single PCG asset covering multiple victims.

**Approach.** A multi-incident allocation layer that takes the probability density fields from §5.3 for all active incidents and the known asset inventory, then solves for optimal sector assignment. The objective function balances expected survival probability (from survivability weighting) against coverage overlap and transit time.

---

### 5.6 Live roster — [Roadmap — not implemented]

**Problem.** The trip anomaly model in §5.2 detects that a boat has not appeared where expected, but it does not know how many people are on board or whether anyone else is monitoring the situation. The PCG receives a single-vessel alert with no crew count, no passenger manifest, and no visibility into whether other boats in the area witnessed the incident.

**Approach.** A per-vessel crew manifest maintained on the phone (optional,
privacy-preserving) that is included in the SOS payload. When the backend
receives an SOS, it broadcasts a situational request through reachable boat pods
and fixed nodes: any vessel that was in the area within the last N minutes is
asked for a brief witness report (saw / did not see, conditions at time of
observation). The roster aggregates these into a common operating picture.

---

### 5.7 Nearest-responder broadcast — [Roadmap — not implemented]

**Problem.** The current system routes all SOS traffic through the gateway to the backend, then to the PCG. But the nearest other fisher may be 500 metres away and able to render assistance in minutes, while the PCG asset is an hour out. The hybrid LoRa network already connects boat pods, fixed sensor buoys, and the shore gateway; a nearest-responder broadcast remains a roadmap capability.

**Approach.** When an SOS is received, the buoy network broadcasts a prioritised assistance request to all phones within LoRa range of the incident position. The request includes the incident type, position, and the sender's estimated distance. Nearby fishers can acknowledge and redirect, providing immediate assistance while the PCG asset transits. Acknowledgements propagate back to the PCG console so dispatchers know whether self-rescue is underway.

---

## 6. Success metrics

| Metric | Why it matters |
|---|---|
| **Time from incident to alert** | The primary killer is the delay before anyone knows. Target: tens of minutes, versus hours or overnight today. |
| **Search area at hour 1 / 6 / 24** | Direct measure of drift model value. Search area is the resource cost of a rescue. |
| **Survival rate of alerted incidents** | The outcome that actually matters. |
| **False alarm rate** | Governs whether the PCG keeps responding. Must stay low or the system is worthless. |
| **Boat-pod direct coverage of municipal water area** | Determines how often an SOS can reach shore without a relay. |
| **Stationary sensor/relay coverage** | Determines fixed-observation quality and fills measured radio dead zones. |
| **App and shared-pod adoption among registered fisherfolk** | The app still has to be installed and the pod must be available on the boat. |
| **Squall alert lead time and hit rate** | Prevention value. |

---

## 7. Scope

### In scope (v1)

- Strap-on boat safety pods: physical SOS button, GPS, local WiFi, LoRa, flash-backed queue, battery, and waterproof enclosure
- LoRa transport from boat pods to a tall shoreline gateway, with optional relay buoys
- Stationary buoy instrumentation: GPS, optional current sensing, solar power (no barometer)
- Phone app: opportunistic messaging, weather sync, manual SOS
- Squall alerts relayed from the PAGASA weather API as RETURN NOW, including buoy-side physical signalling
- Learned trip profiles and overdue/anomaly detection with confidence scoring
- Drift prediction producing a probability density and 50/75/95% search contours,
  with Bayesian re-tasking on negative search results (§5.3(c))
- PCG / BFAR operations console
- Privacy-preserving catch-activity heatmap from explicitly consented catch
  logs. Output is coarse cells only, requires multiple independent vessels,
  expires old observations, and is guidance rather than a catch guarantee.

### Explicitly out of scope

- **Continuous guaranteed capsize detection.** The boat pod can provide a physical SOS button and optional telemetry, but v1 remains store-and-forward and does not claim an always-connected, second-scale capsize detector.
- Market pricing, marketplace features *(catch logging itself — species, quantity, date, method, notes — is back in scope as a lightweight offline-first log; see `docs/07_SCOPE_OUT.md`'s "Amended — now in scope". It stops at recording the catch, not selling it.)*
- Fisheries enforcement and illegal fishing detection *(technically feasible on this data; deferred to avoid positioning a safety network as a surveillance network, which would undermine fisher adoption)*
- Voice communication
- Open-ocean / commercial vessel operations

### Non-goals

Aqone does not replace the PCG, VHF radio, or EPIRB. It fills the gap beneath them: the municipal fisher who cannot afford a satellite beacon and is beyond cellular range.

---

## 8. Key risks

| Risk | Mitigation |
|---|---|
| **Intermittent connectivity limits alert speed** | Stated openly rather than hidden. v1 targets tens of minutes, not seconds — still a step change from overnight. Learned expected-contact modelling extracts maximum signal from sparse contacts. |
| **Direct pod-to-shore coverage gaps** | Validate the direct link outdoors; add relay buoys only where measured dead zones or fixed-sensor needs justify them. |
| **Shared pod availability and maintenance** | Use a simple strap-on enclosure, physical button, flash-backed queue, and a checkout/charging routine through partner boats or LGU/BFAR stations. |
| **False alarms erode PCG trust** | Confidence scoring with per-vessel baselines and peer corroboration; check-in request before dispatch on low-confidence alerts; false-alarm rate tracked as a headline metric. |
| **App and pod adoption** | Everyday messaging and weather are the hook; pods are shared rather than individually purchased. Distribution via BFAR's existing FishR registration and partner boats. |
| **Buoy and pod maintenance, vandalism, theft** | Keep fixed buoys on existing BFAR/PCG maintenance regimes; make pods removable, low-value, waterproof, and self-reporting when they reconnect. |
| **No historical incident data to train on** | All three models cold-start on synthetic, physics-derived, or unsupervised approaches. None require a labelled disaster dataset. |
| **Drift model accuracy without validation data** | Built on validated open frameworks (OpenDrift / Leeway); improves via residual learning from real recoveries. Honest framing: v1 narrows the search, it does not pinpoint. |

---

## 9. Open questions

1. What direct LoRa range is realistic from the strap-on pod to the tall shoreline gateway at the real antenna heights and sea state?
2. What contact frequency is required for learned trip profiles to detect an overdue vessel within the target window?
3. What stationary sensor-buoy density is needed for the learned current field to outperform raw HYCOM, and where are relay buoys actually justified?
4. How many shared pods are needed per partner fleet, and what charging/checkout process keeps them on boats?
5. What is the PCG's operational threshold — what confidence level justifies dispatching an asset?
6. Can BFAR's FishR / FishCore registration serve as the app distribution and vessel-identity channel?
7. What PAGASA API access, rate limits, update cadence and terms of use apply to squall alerts?
8. What is the real municipal fisher fatality baseline? No comprehensive public dataset exists — establishing it may be a contribution in itself.

---

## Sources

- [Philippine Fisheries Profile 2022 — BFAR](https://www.bfar.da.gov.ph/wp-content/uploads/2024/02/2022-Philippine-Fisheries-Profile.pdf)
- [Philippines: number of municipal fisherfolk — Statista](https://www.statista.com/statistics/1350775/philippines-number-of-municipal-fisherfolk-by-type-of-livelihood/)
- [Maritime Search and Rescue — Philippine Coast Guard](https://www.coastguard.gov.ph/index.php/transparency/functions/marsar)
- [PCG: Three missing fishermen rescued, one dead after drifting at sea for 5 days — Manila Bulletin](https://mb.com.ph/2026/02/15/pcg-three-missing-fishermen-rescued-one-dead-after-drifting-at-sea-for-5-days)
- [Filipino fisherman rescued after three days adrift in South China Sea — Baird Maritime](https://www.bairdmaritime.com/security/emergency-services/search-and-rescue/filipino-fisherman-rescued-after-three-days-adrift-in-south-china-sea)
- [Seven dead after fishing boat capsizes in bad weather off Cagayan — Baird Maritime](https://www.bairdmaritime.com/security/incidents/accidents/video-seven-dead-after-fishing-boat-capsizes-in-bad-weather-off-cagayan-philippines)
- [Pag-asa Island gets cellular signal back — Palawan News](https://palawan-news.com/pag-asa-island-gets-cellular-signal-back/)
- [What is mobile coverage like at sea? — FarrPoint](https://www.farrpoint.com/news/mobile-signal-at-sea)
- [OpenDrift Leeway model documentation](https://opendrift.github.io/autoapi/opendrift/models/leeway/index.html)
- [Validation of OpenDrift-Based Drifter Trajectory Prediction for Maritime SAR — JOET](https://www.joet.org/journal/view.php?number=3110)
- [Application of OpenDrift-based trajectory prediction for maritime search and rescue — Frontiers in Marine Science](https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2026.1852504/full)
