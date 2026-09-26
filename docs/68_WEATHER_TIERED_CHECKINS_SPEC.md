# 68 - Weather-tiered check-ins (fleet watch) spec

**Status:** APPROVED - Revision 3
**Owner:** Lenard (spec, backend), Daniel (pod firmware, shore hardware), Arnold (gateway, dashboard)
**Created:** 2026-09-26T09:20:00+08:00
**Updated:** 2026-09-26T09:55:00+08:00
**Related:** `docs/02_LOAM_PACKET_SPEC.md`, `docs/04_INGEST_API.md`, `docs/05_PUBLIC_API.md`, `docs/07_SCOPE_OUT.md`, `docs/33_LORA_RF_BUDGET.md`, `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`, `docs/62D_EDGE_FIRMWARE_TRACK.md` (F2), `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md` (Phase 7, D5), `docs/67_STAGNANT_MODE_IMPLEMENTATION_PLAN.md`, PRD §5.2

Revision: 3
Origin: Len's proposal in chat, 2026-09-26: check in every 15 min in good weather, 5 min when the weather turns, 1 min when severe, so the network tracks boats instead of relying on someone pressing SOS.
A council review the same night kept the idea, proposed 2 min instead of 1 min for the severe tier, and set the guard rails in Section 7.
Revision 1 (2026-09-26T09:20:00+08:00): first draft with decisions D1 to D8 as proposals.
Len's chat answer, 2026-09-26T09:30:00+08:00: "accept all" (D1 to D8), and a fleet of about 50 boats (estimate).
Revision 2 records those answers (Section 8.2) and the finding they exposed (Section 1.1): with 50 boats at sea, check-ins sharing the SOS channel would hit the first SOS attempt 62% of the time at the Severe tier.
Revision 2 therefore adds two new proposals, D9 (a dedicated check-in channel with fixed time slots) and D10 (intervals in whole 2-minute steps), and writes the requirements on that basis.
Len's chat approval, 2026-09-26T09:42:00+08:00: "Yes proceed with D9 and D10, for the tests and the ntc confirmation dont worry about them." Revision 2 is approved with D1 to D10 accepted.
Len's same answer removes the outdoor range test (build step 6) and NTC confirmation as prerequisites for this feature; A2 and A4 stay recorded as accepted risks.
Revision 3 (2026-09-26T09:45:00+08:00), written while planning, changes three things the plan exposed and needs approval with plan 69:
- D11: a check-in at sea with no open trip opens one automatically, because `anomaly_cases.trip_id` is required and unique per trip (REQ-016).
- D12: missed-check-in cases are their own case kind, and the trip-profile model ignores check-ins (REQ-032).
- The two bench success criteria that needed 20 pods use one load-emulator board playing 50 slots (Section 1).

Len's chat approval, 2026-09-26T09:50:00+08:00: "Alright i approve of this decision lets work on it alongside the ui improvement workflow." Revision 3 is approved with D11 and D12 accepted, together with plan 69, to run alongside plan 65.

## 1. Purpose and success

Today the system only learns that a boat is in trouble when someone presses SOS.
A capsize, a fisher lost overboard with the phone, or a crew too hurt to act is silent.
The trip-anomaly model (`backend/app/ai/trip_profile.py`) was built for this, but it has no live input: nothing in the firmware or the app sends a contact event.

This feature makes every boat pod check in on its own, over LoRa, at an interval that tightens as the weather worsens.
A boat at sea that stops checking in is put in front of the MDRRMO within a bounded time, with its last known position.
The fisher does nothing: no button, no screen, no setting.

| Tier | Trigger (D3) | Check-in interval (D1, D10) | Silent boat flagged within (REQ-019, K = 3) |
|---|---|---|---|
| Normal | No active weather signal | 14 min | 52 min after its last check-in |
| Elevated | A published `Warning` advisory, or a dispatcher raise | 4 min | 16 min |
| Severe | A published `Emergency` advisory, or a dispatcher raise | 2 min | 9 min |

"Flagged within" is the REQ-019 deadline (3 intervals plus 20%) plus one evaluation period (REQ-020), rounded up.
It assumes the pod had already heard the current tier; a tier that has just risen is covered by REQ-019's "longer interval" rule.
Len asked for 15 and 5 min; D10 proposes 14 and 4 so every interval is a whole number of 2-minute slot cycles (Section 5.3), which makes each tier slightly faster than asked, never slower.

Success is measured, not modelled:
- On the bench, a pod that is switched off while "at sea" produces a missed-check-in case on the dashboard inside the table's bound for each tier.
- With a load-emulator board playing 50 pods in their slots at the Severe tier, an SOS reaches the dashboard no more than 10% slower than with the emulator off, and the backend receives at least 99% of the emulated check-ins over 1 h.
- A pod switched off inside the harbor produces no case.

The load emulator is a test build of the pod firmware that sends signed check-ins for 50 test pod IDs, each in its own slot; it never ships.

### 1.1 Capacity finding (Revision 2)

Modelled for 50 pods at sea, a 0.54 s check-in frame and a 1.8 s SOS frame at SF10, with every pod transmitting on the one SOS channel at random times (the Revision 1 design):

| Interval | Share of radio time | Check-ins lost to collisions | First SOS attempt hit by a check-in | False missed-check-in cases per hour |
|---|---|---|---|---|
| 15 min | 3% | 6% | 12% | about 0 |
| 5 min | 9% | 16% | 32% | about 2 |
| 2 min | 23% | 36% | 62% | about 45 |
| 1 min | 45% | 59% | 86% | about 255 |

At 2 min this breaks both guard rails: SOS stops going first, and the fleet-silence guard would fire constantly and hide real cases.
The priority rule in REQ-010 cannot help, because it only orders frames inside one pod; collisions happen between pods.

D9 moves check-ins onto a second LoRa channel, heard by a second receiver board at the shore, and gives every pod a fixed time slot on it.
Check-ins then never touch the SOS channel, and never collide with each other while slots are unique and clocks hold.
A 2-minute cycle of 1.5 s slots gives 80 slots, enough for 50 boats with room for 30 more.

## 2. Scope and non-goals

### In scope

- The fleet tier: how it is decided, published, and carried to the pods.
- The pod check-in frame, its channel, its slot and its timing.
- A check-in receiver board at the shore that buffers and uploads check-ins.
- Backend ingest, missed-check-in detection, and fleet-silence detection.
- A missed-check-in case on the dashboard, reviewed through the existing anomaly case actions.
- A dispatcher override that raises the tier.

### Not in scope

- **No automatic SOS.** A missed-check-in case is advisory and a dispatcher decides what happens next (the manual SOS path stays independent of every model).
- **No live tracking map for the public or for regulators.** `docs/07` rules out surveillance and fisheries enforcement; Section 5.6 limits who sees positions.
- **No handset change.** The phone is not involved; the pod checks in by itself.
- **No LoRa downlink to the handset** (still scoped out).
- **No new weather model.** The squall nowcast has no live input since the barometer was removed, and an automatic PAGASA feed does not exist in the backend yet; both can plug in later behind the same port (Section 3).
- **No per-vessel intervals.** One fleet tier for the whole area.
- **No fleet above 80 pods per receiver.** More needs a second check-in channel or shorter slots; revisit then.

## 3. Domain model and architecture

### 3.1 Terms

| Term | Meaning |
|---|---|
| Check-in | A small periodic frame from a pod saying "this pod is powered, here is my fix". Not a delivery state and never shown to the fisher. |
| Fleet tier | `normal`, `elevated` or `severe`. One value for the whole area at any time. |
| Weather signal | Anything that can raise the tier: today an advisory or a dispatcher raise; later PAGASA or the squall nowcast. |
| SOS channel | The existing LoRa frequency. SOS, ACK, ETA, chat, warnings and the shore beacon stay here. |
| Check-in channel | A second LoRa frequency used only for check-ins (D9). Pods only transmit on it; only the check-in receiver listens to it. |
| Slot | A pod's fixed 1.5 s position inside every 2-minute cycle, assigned at enrolment and unique in the fleet. |
| Check-in receiver | A second shore board that listens on the check-in channel and uploads batches; it never touches SOS traffic. |
| Direct pod | A pod that hears the shore beacon with `HOPS = 0`. Only direct pods use the check-in channel. |
| Watched vessel | A vessel whose latest positioned check-in was at sea. Only watched vessels can be flagged. |
| Missed check-in case | The advisory case raised when a watched vessel misses K check-ins in a row. |
| Fleet silence | Many watched vessels going quiet together; treated as a network problem, not many emergencies. |

### 3.2 Layers and dependency direction

Policy is pure and knows nothing about HTTP, SQL, LoRa or the scheduler.
Adapters translate and call it; they make no decisions.

| Layer | Where | Contents |
|---|---|---|
| Policy (backend) | `backend/app/fleet_watch/` (new, framework-free) | `tier.py`: interval table, `fleet_tier(signals, override, now)`. `watch.py`: `is_watched`, `missed_deadline`, `evaluate_vessel`, `fleet_silence`. `slots.py`: `assign_slot(taken)`. Plain dataclasses in, plain dataclasses out. |
| Ports (owned by policy) | same package | `WeatherSignalSource`, `CheckinStore`, `CaseSink`, `SlotRegistry` as `Protocol`s. |
| Use cases | same package | `publish_tier(now)`, `ingest_checkins(batch)`, `evaluate_watch(now)`, `enrol_slot(pod)`. |
| Adapters (backend) | `app/api/fleet_watch.py`, a scheduler job, SQL repositories | Advisory table as the first `WeatherSignalSource`; `buoy_contacts` as the `CheckinStore`; `anomaly_cases` as the `CaseSink`. |
| Policy (pod) | shared header, host-tested in `policy_test.cpp` | `nextCheckinAt(now, tier, slot, direct)`, `adoptTier(beacon, now)`, `inHarbor(fix)`. |
| Adapters (pod, shore) | `AqOneBuoy.ino`, `AqOneShore.ino`, the check-in receiver build | Radio send and channel switch, GPS read, beacon parse, HTTPS batch upload. |

The purity rule is enforced the way `app/incidents/` is: a test fails if any `app/fleet_watch` module imports `fastapi`, `asyncpg`, `httpx` or `app.db`.
The geography question "is this point at sea?" stays in `app/geo.py` and is passed in as a function, so the policy does not import it directly.
Whether the check-in receiver is a third sketch or a build environment of the shore sketch is an implementation-plan choice; either way it includes the byte-identical `AqOneLoam.h`.

## 4. Flows

**F1 Normal day.**
Each direct pod sends a check-in every 14 min, in its own slot, on the check-in channel.
The check-in receiver uploads a batch every 30 s.
The dashboard shows each vessel's last check-in time.

**F2 The weather turns.**
A dispatcher publishes a `Warning` advisory for New Washington.
Within 60 s the backend's tier becomes `elevated`; the shore picks it up on its next 60 s poll and puts it in its beacon.
Each pod that hears the beacon moves to the 4-minute interval at its next slot.
Every pod in range is on the new interval within about 3 min of the advisory.

**F3 A boat goes silent in a storm.**
At the Severe tier, a pod at sea stops checking in.
Within about 8 min of its last check-in, a missed-check-in case appears on the dashboard with the last position, its age, battery, and a link to the drift forecast from that point.
If the case is high confidence the dashboard alarm sounds.
The dispatcher acknowledges, escalates, dismisses or resolves it with the existing case actions.

**F4 A boat comes home.**
The pod's last check-in is inside the harbor or on land, so the vessel is no longer watched.
Switching the pod off at home raises nothing.

**F5 The network goes quiet.**
The check-in receiver loses power or internet.
The backend raises one "check-ins not arriving" condition instead of dozens of vessel cases, and marks any vessel cases in that window low confidence.

**F6 A tier gets stuck or is forged.**
A pod that stops hearing a beacon with a valid tier falls back to Normal when the tier's expiry passes.
The backend caps every tier and override with an expiry.

**F7 No GPS fix.**
The pod still checks in, without a position.
The vessel stays watched if its last positioned check-in was at sea; a resulting case says "no recent position".

**F8 SOS during a storm.**
Check-ins are on their own channel, so an SOS on the SOS channel never collides with one.
Inside one pod, an SOS, ACK, ETA or chat frame waiting to go out makes the pod skip that check-in slot.

**F9 A pod beyond direct range.**
A pod that hears the shore beacon only through a relay cannot reach the check-in receiver.
It sends its check-in on the SOS channel at the Normal interval whatever the tier, relayed at most 2 hops, and the backend expects it at that interval.
These boats are watched less closely than direct ones; the range test decides whether that zone needs a relay with a check-in radio.

**F10 Clock lost.**
A pod that has not had a beacon time for 10 min stops using its slot, because a drifting clock could land it on a neighbour's slot.
It falls back to F9 behaviour until it hears a beacon again.

## 5. Requirements and acceptance criteria

### 5.1 Tier policy (backend)

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-001 | Three tiers with intervals Normal 840 s, Elevated 240 s, Severe 120 s (D1, D10), defined once in `app/fleet_watch/tier.py`, each a whole multiple of the 120 s slot cycle. | A unit test reads each interval from the one table and asserts each is a multiple of 120; grep finds no other definition of these values in `backend/app`. |
| REQ-002 | The tier is the highest of: every published, unexpired advisory for New Washington or `All` (`Warning` gives Elevated, `Emergency` gives Severe, anything else Normal) and any active dispatcher raise. | Unit tests: no advisory gives Normal; one `Warning` gives Elevated; `Warning` plus `Emergency` gives Severe; an expired `Emergency` gives Normal; a `Draft` advisory is ignored. |
| REQ-003 | A dispatcher (`mdrrmo` or `admin`) can raise the tier with a reason and an expiry of at most 12 h. It can only raise, never lower below what the advisories give. Every raise and end is written to the ops audit log. | API test: a raise to Severe with a 2 h expiry is reflected in the published tier; a raise with a 13 h expiry is rejected 422; an attempt to lower is rejected 422; the audit log has one row per action. |
| REQ-004 | The published tier carries `tier`, `interval_s`, `rev` (increases on every change) and `exp` (10 min after publication, refreshed while the tier holds). | `GET` on the gateway tier endpoint returns all four; two reads 1 min apart with no change keep `rev` and move `exp` forward. |

### 5.2 Tier and time downlink (shore and pod)

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-005 | The shore reads the tier every 60 s and adds `ct` (tier) and `cx` (expiry, epoch s) to its existing `T_PING` beacon on the SOS channel. | Shore serial log shows each beacon with `ct` and `cx`; after the backend tier changes, the next beacon within 120 s carries it. |
| REQ-006 | A pod adopts `ct` only from a valid signed beacon, and uses Normal when it has no valid clock, has never heard a tier, or `cx` has passed. | `policy_test.cpp`: an expired `cx` gives Normal; a missing `ct` gives Normal; a valid `severe` gives Severe until `cx`. |
| REQ-007 | A tier change takes effect at the pod's next slot: when the tier rises, the next check-in is at the next occurrence of its slot that fits the new interval; when it falls, the check-in already scheduled is kept. | `policy_test.cpp`: a pod due in 12 min that adopts Severe checks in within 2 min; a pod due in 1 min that adopts Normal still checks in in 1 min. |
| REQ-029 | The shore beacon carries time to within 100 ms (a millisecond field next to `now`, sent so the pod can subtract the known airtime), and the pod keeps its slot clock from it. | Bench: two pods' check-in start times, logged by the check-in receiver, stay within 100 ms of their slot start over 1 h. |

### 5.3 Pod check-in

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-008 | A direct pod sends its check-in at the start of its slot: at the times where `epoch mod 120 = slot x 1.5 s`, once per interval of its tier (D9, D10). | `policy_test.cpp`: slot 7 at Severe sends at 10.5 s into every 120 s cycle; at Elevated every second cycle; at Normal every seventh cycle. |
| REQ-009 | The check-in payload carries the fix (latitude and longitude as signed integers of 1e-5 degree), fix age in seconds, battery percent, the tier the pod believes, and a check-in counter. Payload at most 16 bytes, frame at most 46 bytes (D4). | Encoder test: a full check-in encodes to 46 bytes or fewer and decodes back to the same values; a check-in with no fix encodes with the fix fields marked absent. |
| REQ-010 | A pod skips a check-in slot when an SOS, ACK, ETA or chat frame of its own is waiting, never holds more than one check-in in its TX ring, and never sends a check-in with `WANTS_ACK`. A skipped check-in waits for the next scheduled slot. | `policy_test.cpp`: with an SOS waiting the slot is skipped; the TX ring never holds two check-ins; the receiver log shows no ACK for a check-in. |
| REQ-011 | A pod whose fix is inside a configured harbor zone checks in at the Normal interval in every tier (D6). | `policy_test.cpp`: a fix inside the harbor zone at Severe gives 840 s; a fix 1 km outside it gives 120 s. |
| REQ-012 | Check-ins on the check-in channel are never relayed. A pod that hears the beacon only with `HOPS > 0`, or has had no beacon time for 10 min, sends its check-in on the SOS channel at the Normal interval with a random offset, relayed at most 2 hops (D5); SOS relaying is unchanged. | `policy_test.cpp`: `HOPS = 0` beacon gives the check-in channel and slot timing; `HOPS = 1` gives the SOS channel and 840 s; a 10 min old clock gives the SOS channel. Bench: a relay forwards a relayed check-in with `HOPS = 1` and not with `HOPS = 2`. |
| REQ-030 | The pod switches to the check-in channel only for its own check-in and returns to the SOS channel as soon as the frame has gone. | Bench: across 1 h at Severe, the pod's time off the SOS channel is under 1%; an SOS from a second board sent during a check-in is relayed on the pod's next retry cycle at worst. |

### 5.4 Shore: check-in receiver and slots

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-013 | Check-ins are received and uploaded by a separate check-in receiver board listening on the check-in channel (D9). The SOS gateway board's only change is the beacon fields in REQ-005 and REQ-029. | Code review: no check-in upload code in the SOS gateway build. Bench: with the receiver board unplugged, SOS behaviour and timing are unchanged. |
| REQ-014 | The receiver keeps up to 128 check-ins in memory, drops duplicates by pod and counter, uploads a batch every 30 s, and keeps the batch if the upload fails. When full it drops the oldest. | Bench: 20 pods at Severe produce one upload about every 30 s; with the uplink down for 10 min the buffer holds the newest 128 and uploads them on return. |
| REQ-031 | Every pod gets a unique slot from 0 to 79 when it is enrolled, written with its vessel ID (plan 66 D5, `provision_pod.py`). The backend is the one registry of slot assignments and refuses a duplicate. | API test: enrolling two pods gives two different slots; enrolling an 81st pod is refused with a clear message; re-enrolling a pod keeps its slot. |

### 5.5 Backend ingest and detection

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-015 | A gateway-key batch endpoint accepts up to 128 check-ins, is idempotent per check-in, resolves each pod to its provisioned vessel (plan 66 D5), and rejects an unknown pod per item, not the whole batch. It accepts batches from both the check-in receiver and the SOS gateway (F9). | API tests: the same batch twice stores each check-in once; a batch with one unknown pod stores the others and reports the one; no key gives 401. |
| REQ-016 | Check-ins are stored as `buoy_contacts` rows with `contact_via = 'pod'` and `contact_type = 'checkin'`, attached to the vessel's open trip. An at-sea check-in with no open trip opens one (`reporter_type = 'gateway'`, departure at that check-in); a check-in inside the harbor or on land completes a trip that was opened this way (D11). A check-in in harbor with no open trip is stored without one. The row records which path it came by (direct or relayed). New migration; old migrations untouched. | Migration test on a disposable database. API tests: an at-sea check-in with no open trip creates one trip and attaches to it; the next at-sea check-in reuses it; a harbor check-in completes it; a handset-opened trip is attached to and never completed by a check-in. |
| REQ-017 | `observed_at` is the time the receiving board heard the frame; the fix age is stored separately. | API test: a check-in with fix age 300 s stores the receiver time as `observed_at` and 300 as fix age. |
| REQ-018 | A vessel is watched when its latest positioned check-in is at sea per `app/geo.py`, or it has no position in its latest check-in but its previous positioned one was at sea. | Unit tests with a fake at-sea function: at sea gives watched; harbor gives not watched; latest without fix after an at-sea fix gives watched. |
| REQ-019 | A watched vessel is missed when no check-in has arrived for K = 3 intervals plus 20% of that total (D8). The interval is the longer of the one in force at its last check-in and the current one, and Normal for a vessel whose last check-in came relayed. | Unit tests: Severe, last check-in 7.3 min ago gives missed; 7.1 min ago gives not missed; tier rose from Normal 3 min ago gives not missed until 50.4 min after the last check-in; a relayed vessel at Severe uses 840 s. |
| REQ-020 | Missed-check-in evaluation runs every 60 s. | A scheduler test shows the job registered at 60 s; a replay test raises the case no more than 60 s after the REQ-019 deadline. |
| REQ-021 | If 30% or more of the watched vessels become missed in the same window (D8), or the check-in receiver's last upload is older than 3 min, the backend raises one fleet-silence condition and marks the vessel cases in that window low confidence without sounding the alarm. | Unit test: 4 of 10 missed together gives one fleet-silence condition and 4 low-confidence cases; 1 of 10 gives one normal case. API test: `/api/ops/status` reports the condition. |
| REQ-022 | A missed-check-in case shows the vessel, last check-in time and position, fix age, battery, tier, missed count and confidence, and links to the drift forecast from the last position. It uses the existing anomaly case actions and never creates an SOS incident. A high-confidence case at the Severe tier sounds the dashboard alarm. | Dashboard check at 1280 px, light and dark: the case shows every listed field; acknowledge, escalate, dismiss and resolve work; no row appears in the SOS incidents table; the alarm rings for a high-confidence Severe case only. |
| REQ-023 | A new check-in from the vessel resolves its open missed-check-in case with the reason "check-in resumed", kept in the case history. | API test: a check-in after a case opens resolves it with that reason; the history shows both events. |
| REQ-024 | A stagnant declaration (plan 67) suppresses missed-check-in cases in Normal and Elevated, and not in Severe (D2). | Unit tests for each tier with an active stagnant declaration. |
| REQ-032 | A missed-check-in case is its own case kind, so it and a trip-profile case for the same trip never overwrite each other. The trip-profile model ignores `contact_type = 'checkin'` rows, because its learned intervals assume sparse buoy contacts (D12). | Migration test: one trip holds one case of each kind. Unit test: `anomaly_service` given only check-in rows scores nothing; given buoy contacts plus check-ins scores the same as with buoy contacts alone. |

### 5.6 Privacy and visibility

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-025 | Check-in positions are never exposed by any public endpoint. The per-vessel check-in history is readable by `mdrrmo` and `admin` only; `lgu` sees missed-check-in cases but not the history (D7). | API tests: every `/api/public/*` response contains no check-in position; the history endpoint returns 403 for `lgu` and 401 without a token. |
| REQ-026 | Check-in positions older than 30 days are deleted unless attached to an incident or a case (D7). | A job test on a disposable database: a 31-day-old unattached row is gone, an attached one remains. |
| REQ-027 | The dashboard shows the current tier, what set it (advisory title or dispatcher raise with reason) and when it expires, plus each watched vessel's "last check-in N min ago". | Dashboard check: publishing a `Warning` advisory changes the tier banner within 60 s and names the advisory. |

### 5.7 Capacity guard

| ID | Required behavior | Observable pass/fail criterion |
|---|---|---|
| REQ-028 | `/api/ops/status` reports slots assigned out of 80, check-ins received per cycle, and the share of relayed (F9) check-ins, and warns when more than 70 slots are assigned or relayed check-ins exceed 20% of the fleet. | API test: 71 assigned slots shows the warning; 70 does not. |

## 6. Data and interfaces

Contract changes, each written in its doc before any code (`AGENTS.md`, Shared contracts):

| Contract | Change |
|---|---|
| `docs/02` | The check-in channel's frequency and slot timing. `T_STATUS` (0x04) gets the binary check-in payload (D4) and becomes pod-originated; the doc's "payloads are JSON" rule gains that one exception. `T_PING` gains optional `ct`, `cx` and a millisecond time field. Check-in relay rule (REQ-012). |
| `docs/03` | None. The phone is not involved. |
| `docs/04` | Batch check-in endpoint; `trip_id` optional for pod check-ins; `contact_type = 'checkin'`; gateway tier endpoint; slot enrolment. |
| `docs/05` | Tier read and dispatcher raise; missed-check-in cases in the existing anomaly case endpoints; check-in history (restricted); fleet-silence and slot use in `/api/ops/status`. |
| `docs/06` | None. Check-ins are not delivery states and never change what the fisher sees. |

Radio budget at SF10 / 125 kHz for a 46-byte check-in frame: about 0.54 s, inside a 1.5 s slot with about 0.5 s of guard on each side.
A JSON payload of the same content would be about 80 bytes and 0.86 s, which would not leave a safe guard.

## 7. Quality constraints

- **SOS first, by construction.** Direct check-ins never use the SOS channel; enabling check-ins at any tier must not slow an SOS by more than 10% (Section 1 bench test).
- **No check-in collisions.** Slots are unique and clocks are held to 100 ms (REQ-029, REQ-031); a pod without a good clock leaves the check-in channel (F10).
- **Silence is weak evidence.** Every case carries a confidence; fleet-wide silence never becomes many alarms (REQ-021).
- **Fail safe to Normal.** Any missing, expired or unreadable tier means Normal on the pod (REQ-006).
- **Pure policy.** Tier, slot and watch rules are tested without a database, web server, radio or clock (fakes and injected `now`).
- **Power.** Daniel measures the pod's extra daily charge at the Severe tier on the bench; the number goes in `docs/08`.
- **Honesty.** Until the range test (build step 6) and the bench tests pass, docs and pitch describe this as roadmap.

## 8. Decisions and assumptions

### 8.1 Observed facts (2026-09-26)

- `T_STATUS` (0x04) exists in `AqOneLoam.h:220`; pods relay it and nothing originates it.
- The shore sends a signed `T_PING` beacon every 60 s (`BEACON_EVERY_MS`) with `now` in whole seconds, and polls `/api/public/advisories` every 60 s.
- Advisory priorities are `Emergency`, `Warning`, `Information`, `Community` (`backend/app/api/advisories.py:21`); advisories are published by dispatchers.
- No automatic PAGASA feed exists in the backend; the squall model reads buoy pressure, and the barometer was removed.
- `POST /api/v1/contacts` exists with `contact_via = 'pod'` and requires `trip_id`; nothing calls it with live data.
- The pod firmware reads no GPS today; plan 66 Phase 7 adds `TinyGPSPlus` (D6 approved there), gated on plan 66 D5 (pod provisioned with its vessel ID, still open).
- Each Heltec V3 has one SX1262, which listens on one frequency and one spreading factor at a time; a second channel at the shore needs a second board.
- The shore is deaf to the radio during each blocking HTTPS call of up to 12 s; `docs/62D` Phase F2 fixes it and is gated. With D9 the check-in uploads do not run on that board.
- Anomaly scoring runs every 300 s (`backend/app/scheduler.py:103`); anomaly cases already have acknowledge, dismiss, escalate and resolve.
- `RESPONDER_ROLES` includes `lgu` (`backend/app/auth.py:27`).

### 8.2 Decisions

| ID | Question | Decision | State |
|---|---|---|---|
| D1 | Severe interval | 2 min. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D2 | Does Severe override a stagnant declaration? | Yes in Severe, no in Normal and Elevated. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D3 | What raises the tier in v1? | Published advisories (`Warning` to Elevated, `Emergency` to Severe) plus a dispatcher raise-only override. PAGASA feed and squall nowcast later, as more `WeatherSignalSource` adapters. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D4 | Binary or JSON check-in payload? | Binary, 16 bytes or fewer. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D5 | How far are check-ins relayed? | At most 2 hops. Under D9 this applies only to relayed check-ins on the SOS channel (F9). | Accepted, Len 2026-09-26T09:30:00+08:00; scope narrowed by D9 if D9 is accepted |
| D6 | Harbor rule on the pod? | Pods inside a configured harbor zone use Normal in every tier; zones generated from the shore stations in `app/geo.py` into the shared header. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D7 | Who sees positions, and for how long? | History for `mdrrmo` and `admin` only; `lgu` sees cases; unattached positions deleted after 30 days. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D8 | Missed and fleet-silence thresholds? | K = 3 misses; fleet silence at 30% of watched vessels. | Accepted, Len 2026-09-26T09:30:00+08:00 |
| D9 | How do 50 pods check in without drowning SOS? | A second LoRa channel for check-ins only, heard by a second receiver board at the shore, with a unique 1.5 s slot per pod in a 2-minute cycle (80 slots). Pods beyond direct range fall back to relayed check-ins at the Normal interval on the SOS channel. | Accepted, Len 2026-09-26T09:42:00+08:00 |
| D10 | Intervals | 14 / 4 / 2 min, so every tier is a whole number of 2-minute cycles and slots line up across tiers. | Accepted, Len 2026-09-26T09:42:00+08:00 |
| D11 | What trip does a check-in belong to when the handset never opened one? | An at-sea check-in opens a trip automatically; a harbor check-in completes a trip opened that way. Handset-opened trips are never completed by a check-in. | Accepted, Len 2026-09-26T09:50:00+08:00 |
| D12 | How do missed-check-in cases and trip-profile cases coexist? | A `case_kind` on `anomaly_cases` (new migration), unique per vessel, trip and kind; the trip-profile model skips check-in rows. | Accepted, Len 2026-09-26T09:50:00+08:00 |

Alternatives considered for D9:
- Keep one channel with random timing (Revision 1): fails at 50 boats (Section 1.1).
- One channel with slots: check-ins would fill about a quarter of every cycle, and an SOS, which can start at any time, would still land on them.
- Longer intervals on one channel: an SOS hit rate of 12% or less needs about 15 min at Severe, which defeats the feature.

### 8.3 Assumptions

- **A1 Fleet size.** About 50 boats (Len's estimate, 2026-09-26). The 80-slot cycle leaves room for 30 more.
- **A2 Range and relays (accepted risk).** Unmeasured; Len removed the range test as a prerequisite (2026-09-26T09:42:00+08:00). Direct pods get slot check-ins; if the field shows many boats in the relayed zone (F9), REQ-028 warns and a relay with its own check-in radio is the follow-up.
- **A3 Clock.** Pods set their slot clock from the shore beacon; a pod that has never heard one, or not for 10 min, does not use the check-in channel.
- **A4 Second frequency (accepted risk).** A second channel is assumed allowed in the band the project uses; Len removed NTC confirmation as a prerequisite (2026-09-26T09:42:00+08:00).

## 9. Open questions and readiness

Blocking before the firmware phases of plan 69 (dependencies, not decisions for this spec):
- Plan 66 Phase 3 (`AqOnePolicy.h` and the host test), Phase 4 (unique node IDs, C1) and Phase 7 with D5 (pod GPS and vessel identity; slot enrolment rides on the same provisioning step).
- A second shore board and antenna for the check-in receiver (Daniel).

The backend and dashboard phases of plan 69 have no hardware dependency.
`docs/62D` Phase F2 is no longer a prerequisite under D9, because check-in uploads run on their own board; it is still needed for SOS bursts.
Sequencing, Len 2026-09-26T09:50:00+08:00: plan 69 runs alongside plan 65 (fisher friction); plan 66 firmware phases still gate plan 69 Phases 6 and 7.

Approval: D1 to D8 accepted in chat, 2026-09-26T09:30:00+08:00; D9 and D10 accepted and Revision 2 approved, 2026-09-26T09:42:00+08:00. Revision 3 approved, 2026-09-26T09:50:00+08:00.
