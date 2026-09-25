# AqOne Extreme Edge Case Report

As of 2026-09-23 · Lenard.
Living copy: https://claude.ai/code/artifact/39702ee1-2dd0-4edd-b810-762a768d5697

AqOne has 68 edge cases worth fixing before deployment: 14 Critical, 23 High, 18 Medium and 13 Low.
Most Critical ones share one shape: a real SOS is lost, closed or never heard, while every screen still looks normal.

Two starting assumptions change.
A phone going overboard cannot cause a false trip anomaly today, because nothing in the firmware feeds that model (H6).
A FishR green badge would be forgeable, because the license field is free text the fisherman types (H10).

Based on the code at commit `a1d5cc5` on `fix/security-audit-remediation`.
Findings that need hardware or field confirmation say so, and SEC-xx marks overlap with the security audit.

## Ranked index

**Critical**: a real SOS is lost, closed or never heard without anyone noticing, or rescuers are put in danger.
**High**: long delays, false reassurance, a wrong search area, or false alarms nobody can tell apart.
**Medium**: degraded but recoverable.
**Low**: cosmetic, or a freak combination.

Likelihood runs Likely, Plausible, Rare, then Freak for the 0.0001% class.
It is a dropdown, so re-rate as the team learns more.

### Critical (14)

| ID | Finding | Likelihood | Triggered by | Status |
| --- | --- | --- | --- | --- |
| C1 | Every pod flashed from the default sketch shares node ID BUOY01 | Likely | Installer | New |
| C2 | Buoys remember acknowledgements for only 8 vessels until reboot | Likely | System, attacker | New |
| C3 | Once a pod accepts an SOS, the phone never tries the internet again | Likely | System | New |
| C4 | The phone is the only SOS trigger; the pod has no button or GPS yet | Likely | Sea and weather | Design gap |
| C5 | The production database is on Render’s free plan, which expires | Likely | System | New, confirm Render terms |
| C6 | An SOS already waiting when the dashboard opens never makes a sound | Likely | Operator | New |
| C7 | One click on Resolve closes a live SOS for good | Plausible | Operator | New |
| C8 | A half-cut emoji or ñ makes an SOS or its answer unreadable | Plausible | Fisherman, dispatcher | Needs bench test |
| C9 | Anyone online can post “MDRRMO” chat onto every phone at sea | Plausible | Attacker | Partly SEC-19 |
| C10 | Thirteen or more open incidents turn the gateway into a jammer | Plausible | System, attacker | New |
| C11 | The shared radio key lets anyone delete queued SOS and fake replies | Rare | Attacker | Key tracked (SEC-27) |
| C12 | A fake “Aquan” pod swallows SOS calls | Rare | Attacker | New |
| C13 | A man-in-the-middle on the gateway’s WiFi swallows SOS calls | Rare | Attacker | Tracked (SEC-28) |
| C14 | Pre-made fake rows capture a real SOS and its position | Freak | Attacker | New |

### High (23)

| ID | Finding | Likelihood | Triggered by | Status |
| --- | --- | --- | --- | --- |
| H1 | Most panic SOS carry no GPS position, and none is sent later | Likely | Sea and weather | Needs field test |
| H2 | SOS retries stop when Android kills the app in the background | Likely | System | New |
| H3 | Pod WiFi fights the phone’s normal internet, so fishermen turn it off | Likely | Fisherman | Needs device test |
| H4 | Every acknowledgement promises an ETA, 20 minutes by default | Likely | Operator | New |
| H5 | A note added after the SOS never crosses the mesh while it is queued | Likely | System | New |
| H6 | Trip anomaly detection has no live input and no schedule | Likely | System | Design gap |
| H7 | Phone-based contacts confuse “phone missing” with “boat missing” | Likely | Sea and weather | Design gap |
| H8 | New and solo fishermen are the least likely to be flagged | Likely | System | Design gap |
| H9 | A boat silent for 12+ hours drops out of anomaly evaluation | Likely | System | New |
| H10 | A FishR green badge would be forgeable; nobody can be verified today | Likely | Attacker, system | New |
| H11 | Relays collide where boats cluster: group fishing and the harbor | Likely | Sea and weather | Needs field test |
| H12 | One gateway fails in exactly the weather that causes emergencies | Likely | Sea and weather | New |
| H13 | Until the shore sends X-Api-Key, mesh SOS lose their seq | Likely | System | Tracked (plan Phase 5) |
| H14 | A typhoon warning is broadcast once; pods that miss it never get it | Likely | Sea and weather | Partly SEC-29 |
| H15 | An old undelivered SOS arrives days later as a fresh call | Plausible | Fisherman | New |
| H16 | A “safe” check-in mutes the overdue alarm for the whole trip | Plausible | Fisherman, attacker | New |
| H17 | Seq collisions can show an unseen SOS as acknowledged | Rare | System | New |
| H18 | A flood of anonymous SOS buries the real one | Rare | Attacker | Side effect of SEC-07 |
| H19 | Prank SOS through a pod arrive looking like trusted mesh traffic | Rare | Attacker | Partly tracked |
| H20 | Rescuers can be baited, diverted, or turned against a rival | Rare | Attacker | New |
| H21 | Anyone can fill blank profile fields with their own phone number | Rare | Attacker | Partly SEC-08 |
| H22 | No silent SOS, and a robber can force a cancel | Rare | Attacker | New |
| H23 | Lithium cells may charge inside a sun-baked, sealed pod | Rare | Sea and weather | Needs BOM check |

### Medium (18)

| ID | Finding | Likelihood | Triggered by | Status |
| --- | --- | --- | --- | --- |
| M1 | Dispatcher notes are cut at 40 bytes on the radio | Likely | Operator | New |
| M2 | A reinstall gives the phone a new vessel identity | Likely | Fisherman | New |
| M3 | Phones and boats don’t map one to one | Likely | Fisherman | New |
| M4 | The shore never syncs its clock if it boots before the router | Likely | Sea and weather | New |
| M5 | Buoy field hazards: theft, mooring boats, birds, drift, corrosion | Likely | Sea and weather, people | Needs field test |
| M6 | The only phone number on file is the phone at sea | Likely | System | Design gap |
| M7 | An SOS can hitchhike on a neighbouring boat’s pod | Plausible | Sea and weather | New |
| M8 | Two dispatchers acknowledging at once overwrite each other | Plausible | Operator | New |
| M9 | One mistaken SAFE\_NOW ends the rescue with no way back | Plausible | Fisherman | Related to SEC-20 |
| M10 | A call closed as a prank tells the boat “resolved” | Plausible | Operator | New |
| M11 | 915 MHz legality and neighbour interference are unresolved | Plausible | System | Needs NTC check |
| M12 | Mesh chat is readable by anyone on the internet | Plausible | Attacker | Partly SEC-19 |
| M13 | A phone without a boat profile cannot send an SOS | Plausible | Fisherman | New |
| M14 | The free web service sleeps, so the first direct SOS can time out | Plausible | System | New |
| M15 | The first clock a buoy hears wins until reboot | Rare | Attacker, system | New |
| M16 | A weak battery can reboot the pod mid-SOS in a loop | Rare | Sea and weather | Needs bench test |
| M17 | Drift starts from the phone’s clock, even if it is years off | Rare | Fisherman | New |
| M18 | An operator login stays valid for 7 days with no revocation | Rare | Attacker | Tracked (SEC-12) |

### Low (13)

| ID | Finding | Likelihood | Triggered by | Status |
| --- | --- | --- | --- | --- |
| L1 | Some SOS-flow text is English only | Likely | System | New |
| L2 | Midnight departures average to noon | Plausible | System | New |
| L3 | Trip distance is measured from the town centre | Plausible | System | New |
| L4 | Media volume at zero silences the SOS alarm | Plausible | Fisherman | New |
| L5 | Wet screens and pouches fight the 4-second countdown | Plausible | Sea and weather | New |
| L6 | Old frames replayed after the duplicate filter rolls over are accepted | Rare | Attacker | New |
| L7 | Invalid UTF-8 in a pod push drops the phone’s chat connection | Rare | System | New |
| L8 | A vessel with 20+ SOS rows can’t reconcile the older ones | Rare | Fisherman | New |
| L9 | A boat named “FALSE ALARM” labels its own real SOS | Rare | Fisherman | New |
| L10 | A firmware update can wipe an SOS waiting in the pod | Freak | Installer | New |
| L11 | Coordinates are always labelled N and E | Freak | System | New |
| L12 | Firmware timestamps wrap in 2106 | Freak | System | New |
| L13 | Two phones with one identity in the same second merge | Freak | Fisherman | New |

## Critical findings

**C1. Every pod flashed from the default sketch shares node ID BUOY01.**
The node ID is a `#define` at the top of the sketch, and nothing stops 20 pods shipping with the default.
A pod drops every frame that carries its own ID, so same-ID pods never relay each other’s SOS.
Fresh boards also start their frame counter at the same number, so the shore can treat a second pod’s SOS as a duplicate and send one ACK that makes both pods delete their queued call.
Evidence: `AqOneBuoy.ino:44-45`, `:832`, `:873-889`; `AqOneLoam.h:399-404`.

**C2. Buoys remember acknowledgements for only 8 vessels until reboot.**
Every pod caches the dispatcher’s answer in an 8-slot table that only a reboot clears.
The shore broadcasts an answer for every open incident in the system, direct-path ones included, so a buoy that runs for weeks fills up on drills and old calls.
From the ninth vessel on, offline phones never see “acknowledged” or the ETA, while the dispatcher believes the answer went out.
Eight anonymous `POST /api/sos` calls fill every buoy in range within one 45-second poll, and resolving them frees nothing.
Evidence: `AqOneBuoy.ino:267`, `:313-325`, `:525`, `:907-955`; `AqOneShore.ino:475-495`.

**C3. Once a pod accepts an SOS, the phone never tries the internet again.**
The outbox retries only records in the `saved` state, and a pod’s “accepted” moves the record to `relayed`, which ends retries on both paths.
If that pod then cannot deliver (out of range, wrong radio settings, flat battery, C1, C8, C12), the phone waits at `relayed` forever, even after it regains 4G near shore.
Evidence: `sos_record.dart:115`; `sos_service.dart:129-133`; `outbox_store.dart:42-51`.

**C4. The phone is the only SOS trigger; the pod has no button or GPS yet.**
The transport decision promises a physical SOS button and GPS on every pod, but the pod firmware has neither.
A phone that goes overboard, drowns in bilge water, runs flat or gets stolen leaves that boat unable to call for help, and every SOS position depends on the phone’s GPS (H1).
Evidence: `docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md:13-14`, `:48`; no button or GPS code in `AqOneBuoy.ino`.

**C5. The production database is on Render’s free plan, which expires.**
`render.yaml` records the database as a free plan created on 2026-09-15.
Render’s free Postgres expires 30 days after creation and is deleted after a grace period, so from about 2026-10-15 every SOS insert fails (confirm against Render’s current terms).
The gateway then withholds every ACK, pods retry forever, and SOS history, profiles and the audit trail can be lost.
Evidence: `render.yaml:1-6`, `:14`.

**C6. An SOS already waiting when the dashboard opens never makes a sound.**
The klaxon rings only for SOS IDs first seen after the page loaded.
Calls that arrive while the browser is closed stay silent after a crash, a Windows update restart, a sleeping laptop or a shift change.
Browsers also block audio until someone clicks the page, background tabs slow the 3-second poll to about once a minute, and after 7 days the expired login turns the wall screen into a login page.
Evidence: `dashboard-live-sos.js:245-270`; `dashboard-alarm.js:74-114`; `dashboard-core.js:107-120`; `render.yaml:35-36`.

**C7. One click on Resolve closes a live SOS for good.**
Resolve has no confirmation and no reason prompt, and the backend has no way to reopen an incident.
The incident list redraws every 3 seconds and new calls push rows down, so a hurried click can open and then close the wrong call.
The boat’s phone is then told its case is resolved.
Evidence: `dashboard-incidents.js:401-456`; `dashboard-vessels-alerts.js:197-243`; `sos.py:528-574`.

**C8. A half-cut emoji or ñ makes an SOS or its answer unreadable.**
The pod copies the boat name and note into fixed byte buffers of 32 and 64 bytes, which can split a multi-byte character.
If the backend then rejects the invalid text, the shore withholds the ACK and the pod retries every 2 minutes forever, while the phone sits at `relayed` (C3).
The shore also cuts the dispatcher’s note at 40 bytes, so a split ñ, curly quote or degree sign makes the pod serve invalid UTF-8, and the offline phone never shows the acknowledgement.
Evidence: `AqOneBuoy.ino:513-516`; `AqOneShore.ino:186`, `:215-221`, `:358-363`; `buoy_client.dart:162`.
Needs a bench test of the backend and parser behaviour.

**C9. Anyone online can post “MDRRMO” chat onto every phone at sea.**
`POST /api/mesh/chat` needs no login and accepts any sender name.
The shore pulls up to 10 new lines every 20 seconds and broadcasts each one, and every pod relays it.
A prank script can tell the fleet “Signal No. 3, return to port” or “all clear”, and a steady stream of posts fills the channel until SOS frames collide.
Evidence: `mesh.py:16-57`; `AqOneShore.ino:539-593`, `:921-924`.

**C10. Thirteen or more open incidents turn the gateway into a jammer.**
The downlink feed returns every unresolved incident with no age limit, up to 100 sorted by vessel ID.
The gateway tracks only 12 vessels and evicts slot 0 when full, so past 12 it re-broadcasts an answer for every extra vessel on every 45-second poll, and every pod relays each one.
Forgotten drills and never-resolved calls get there slowly, 100 anonymous POSTs get there at once, and the churn rewrites the gateway’s flash on every eviction (possible wear-out within weeks, estimate).
Evidence: `sos.py:375-427`; `AqOneShore.ino:259-310`, `:489-527`.

**C11. The shared radio key lets anyone delete queued SOS and fake replies.**
A pod deletes its queued SOS when any correctly signed ACK names its node ID and a recent frame number, without checking that the shore sent it.
Both values travel in clear on the SOS frame, so a listener with the key can ACK every SOS the moment it is sent.
The same key forges ETAs, “resolved” messages, and typhoon warnings or all-clears.
Moving the key out of the repo (SEC-27) does not end this, because every pod shares one key and one stolen pod’s flash gives it back.
Evidence: `AqOneLoam.h:86`; `AqOneBuoy.ino:867-889`, `:899-1014`.

**C12. A fake “Aquan” pod swallows SOS calls.**
Every pod broadcasts the same open SSID, and the phone talks plain HTTP to `192.168.4.1`, the default address of any ESP32 access point.
A cheap board that answers `POST /v1/sos` with `{"accepted": true}` moves the phone to `relayed`, and C3 then stops every retry.
Evidence: `AqOneBuoy.ino:76-77`, `:386-400`; `buoy_client.dart:99-130`.

**C13. A man-in-the-middle on the gateway’s WiFi swallows SOS calls.**
The shore skips TLS certificate checks.
Anyone who controls its uplink WiFi, often a shared hall network or a phone hotspot, can answer `POST /api/sos` with a fake 200, and the shore then ACKs the pods, which delete the call.
Tracked as SEC-28 and listed here for the silent-loss consequence.
Evidence: `AqOneShore.ino:141-144`, `:769-781`.

**C14. Pre-made fake rows capture a real SOS and its position.**
The backend merges any SOS with the same vessel ID and phone timestamp into the first row, keeping that row’s position and note.
Vessel IDs travel in clear over LoRa, so an attacker can pre-create rows for the coming seconds with a fake position and resolve them through the reply-by-`local_id` route.
When the real SOS lands on one of those seconds it merges into a resolved row: no new incident, no alarm, and the phone still shows `delivered`.
Covering one vessel for a day takes about 170,000 requests, and ingest has no rate limit by design.
Evidence: `sos.py:205-241`, `:681-713`; `007_sos_ingest.sql:47-48`.

## High findings

**H1. Most panic SOS carry no GPS position, and none is sent later.**
`raiseSos` waits at most about 10 seconds for a fresh fix and sends whatever it has.
In airplane mode the phone gets no network assistance, so a cold GPS start usually takes longer, unless the map page has been open long enough to warm it (measure in the field).
The position is never updated afterwards, a no-fix SOS gets no map marker, and drift refuses to run without a position.
Evidence: `location_service.dart:118-139`; `config.dart:62`; `sos_service.dart:74-85`; `dashboard-live-sos.js:186-189`; `drift.py:452-453`.

**H2. SOS retries stop when Android kills the app in the background.**
Retries are timers inside the app process, with no foreground service or scheduled job behind them.
Budget phones common in the Philippines close background apps within minutes of the screen turning off.
A fisherman who presses SOS before joining the pod WiFi and pockets the phone may never send it.
Evidence: `sos_service.dart:44-53`; no background package in `pubspec.yaml`; no service in `AndroidManifest.xml`.

**H3. Pod WiFi fights the phone’s normal internet, so fishermen turn it off.**
The pod answers every DNS lookup with its own address, and when the mesh is up it tells Android it has internet.
Messenger, calls over data and the app’s own direct path then hit a dead end, so fishermen will tap “no” on the prompt, forget “Aquan” or switch WiFi off, which removes the offline path.
The app also does not bind its requests to the pod network, so with mobile data on, Android may route pod requests over cellular (test per Android version).
Evidence: `AqOneBuoy.ino:396-400`, `:702-719`; no network binding in `mobile/`.

**H4. Every acknowledgement promises an ETA, 20 minutes by default.**
The acknowledge dialog pre-selects 20 minutes and falls back to 20 when the field is empty.
There is no “received, no ETA yet” choice, although the backend supports one.
A fisherman told “20 minutes” may stay with a sinking boat instead of flagging down nearby boats, and minutes-only input invites mistakes like “2” meant as hours.
Evidence: `dashboard.html:892-896`; `dashboard-incidents.js:304`; `sos.py:447-457`.

**H5. A note added after the SOS never crosses the mesh while it is queued.**
The app sends the SOS with no note, then re-sends it with the chosen emergency type seconds later.
The pod sees the same vessel and timestamp, returns the existing queue entry and drops the new note.
“Taking water” and “engine dead” need different boats, and a dispatcher on the mesh path never learns which.
Evidence: `AqOneBuoy.ino:485-503`; `sos_service.dart:283-301`; `venture_page.dart:324-332`.

**H6. Trip anomaly detection has no live input and no schedule.**
No firmware sends contact events, the only input the detector trusts.
The evaluator’s cron lived on Railway, and `render.yaml` schedules nothing.
The dashboard then shows “No active vessel risk rows available”, the same text as a calm sea, while squall nowcasting correctly says “unknown”.
So today a phone going overboard cannot cause a false alarm, because nothing is scored at all.
Evidence: `contacts.py:113-151`; no `/api/v1/contacts` call in `firmware/`; `run_anomaly_evaluation.py:3`; `dashboard-ai-ops.js:628`.

**H7. Phone-based contacts confuse “phone missing” with “boat missing”.**
Once contacts come from the phone, a phone that drowns, dies, runs out of load or stays home makes a safe boat look overdue.
The reverse is worse: a person falls overboard, the phone stays aboard, and the drifting empty boat keeps checking in as normal.
A phone carried on a different boat is scored against the wrong vessel’s habits.
Evidence: design gap; contacts are keyed by vessel and buoy only (`contacts.py:62-80`).

**H8. New and solo fishermen are the least likely to be flagged.**
New profiles have their score multiplied by 0.9, so first trips need stronger evidence.
A trip with no contacts and no declared return time stays `normal` forever.
Scoring has no idea whether a boat is solo or in a group, so the fisherman with no witnesses gets the same threshold as a convoy.
Evidence: `trip_profile.py:458-513`, `:620-621`.

**H9. A boat silent for 12+ hours drops out of anomaly evaluation.**
Trips without a trip record fall back to a 12-hour freshness window, and no client creates trip records today.
A boat that went quiet at dusk has aged out by morning, when overnight survival matters most.
Cases created before that persist, but none is created after.
Evidence: `anomaly_service.py:71`, `:153-196`; the docs/59 SEC-09 note that no client calls the trip routes.

**H10. A FishR green badge would be forgeable; nobody can be verified today.**
`license_type` is any text up to 24 characters, typed by the fisherman and shown as-is, so a badge keyed on “fishr” turns any prankster green.
Real verification has no path: the app has an enrol method that no screen calls, the 24-hour device token is never refreshed, the phone always sends `self_declared`, and no endpoint lets a responder confirm a vessel.
A yellow “unregistered” badge will mostly mark the poorest fishermen, and under pressure yellow reads as lower priority.
Evidence: `vessel_profile.py:31`; `dashboard-live-sos.js:160-162`; `backend_client.dart:162-215`; `identity_store.dart:297-301`; `sos.py:147-156`.

**H11. Relays collide where boats cluster: group fishing and the harbor.**
A full SOS frame takes about 2.2 seconds at SF10 and 125 kHz, but relays wait only 200 to 600 ms and never listen before sending.
Every pod that hears a frame relays it once, so ten boats together produce ten overlapping 2-second transmissions that the next hop hears as noise.
The 64-entry duplicate filter was sized for “a 3-node mesh”, and every moored boat’s pod stays on at the harbor all night.
Evidence: `AqOneLoam.h:335-353`, `:449-463`, `:545-548` (the comment there assumes about one second per frame).
Airtime is from the Semtech formula; needs a field test.

**H12. One gateway fails in exactly the weather that causes emergencies.**
There is one shore board with one internet link and one power feed, on a mast.
Lightning, typhoon power cuts and ISP outages hit it when SOS calls peak.
It also goes deaf to the radio during each blocking HTTPS call of up to 12 seconds, so when a squall triggers several SOS at once, most frames arrive while it is busy and wait for pod retries of up to 2 minutes.
Evidence: `AqOneShore.ino:158-222`, `:899-929`.

**H13. Until the shore sends X-Api-Key, mesh SOS lose their seq.**
Phase 2 of the security fix (SEC-06) drops `buoy_id`, `src_id` and `seq` from any SOS without a gateway key, and the shore adds that header only in Phase 5.
Offline phones match acknowledgements by seq alone, so every mesh SOS becomes unmatchable and the dashboard labels it “direct internet”.
The plan notes no gateway is deployed yet; the gap opens the day one is.
Evidence: `sos.py:158-174`; `AqOneShore.ino:179-181`; `docs/archive/plans/59_SECURITY_AUDIT_REMEDIATION_IMPLEMENTATION_PLAN.md:176`, `:264`.

**H14. A typhoon warning is broadcast once; pods that miss it never get it.**
The shore sends each warning one time and skips it on later polls while it is unchanged.
A pod that was out of range, transmitting or rebooting at that moment never receives it, and pods keep only 6 warnings in RAM, overwriting slot 0 whatever its priority.
A boat coming back into range, or a pod that browned out overnight, then shows no warning while a typhoon warning is active.
Evidence: `AqOneShore.ino:688-719`; `AqOneBuoy.ino:374-375`, `:961-1014`.
Partly tracked (SEC-29).

**H15. An old undelivered SOS arrives days later as a fresh call.**
The outbox never expires a record and sends the oldest first.
A test press at home, or an SOS from a trip with no pod in range, goes out the next time the phone meets a pod or signal.
The dashboard times it from when the backend received it, not when it was pressed, so it rings as a new emergency.
Evidence: `outbox_store.dart:42-51`; `dashboard-live-sos.js:129`, `:172`.

**H16. A “safe” check-in mutes the overdue alarm for the whole trip.**
A `safe` welfare status caps the overdue factor at 0.15 for the rest of the trip.
A fisherman who reports safe at noon and capsizes at 3 pm stays below the alert line, and so does one forced to report safe.
Evidence: `trip_profile.py:543-546`.

**H17. Seq collisions can show an unseen SOS as acknowledged.**
Mesh SOS reach the backend without the phone’s `local_id`, so the phone matches answers by the pod’s seq.
Each pod counts from 1 and restarts after a flash erase, so an old and a new SOS can share a seq.
The phone’s lookup then keeps the older incident, marks the new call acknowledged and resolved, and stops watching it; after an app restart, a SAFE\_NOW saved for the old call can be sent against the new one.
Evidence: `sos_service.dart:438-457`, `:486-503`; `AqOneBuoy.ino:154`, `:518`.

**H18. A flood of anonymous SOS buries the real one.**
SEC-07 removed the 100-row cap on the active feed so a flood cannot evict a real call.
Now every open dashboard pulls and redraws every row every 3 seconds, and the klaxon never stops.
Ten thousand fake calls hide one real one and can freeze the browser.
Evidence: `sos.py:315-361`; `dashboard-live-sos.js:21`, `:241-243`; `dashboard-vessels-alerts.js:197`.

**H19. Prank SOS through a pod arrive looking like trusted mesh traffic.**
Anyone who joins a pod’s open WiFi can queue up to 12 SOS with any vessel ID and position.
The pod stores them in flash and relays them, and the dashboard shows “LoRa mesh via BUOY01”, which reads as corroboration.
Out of shore range, the 12 entries survive reboots and answer the boat’s own phone with “queue full”.
Evidence: `AqOneBuoy.ino:465-544`.
Queue capacity is tracked (`sos-queue-untrusted-capacity`, deferred); the provenance angle is new.

**H20. Rescuers can be baited, diverted, or turned against a rival.**
An SOS’s position and identity are whatever the phone sends, and nothing compares the position with the relaying buoy’s range or the boat’s last contact.
That allows an ambush at a chosen spot, a decoy call that pulls the only rescue boat away from illegal fishing or smuggling, false alarms sent under a rival’s vessel ID (IDs travel in clear over LoRa), and an SOS record used as evidence for an insurance claim.
A green registration badge stops none of these: registered boats get stolen and skippers get coerced.
Evidence: `sos.py:101-107`; `AqOneBuoy.ino:206-223`.

**H21. Anyone can fill blank profile fields with their own phone number.**
SEC-08 stops anonymous overwrites, but a blank field can still be filled by anyone who knows the vessel ID, and most fishermen skip the optional phone and license fields.
The dispatcher then calls the attacker to check the SOS and hears “false alarm”.
Evidence: `vessel_profile.py:47-89`, `:104-124`.

**H22. No silent SOS, and a robber can force a cancel.**
Tapping SOS starts a loud alarm and vibration at once, which is dangerous during a robbery at sea.
The 4-second slide-to-cancel, the stand-down and SAFE\_NOW can all be forced, and nothing marks a coerced cancel.
Evidence: `venture_page.dart:299-343`; `sos_alarm.dart`.

**H23. Lithium cells may charge inside a sun-baked, sealed pod.**
A sealed box in tropical sun can pass 60 °C, while lithium cells should not charge above about 45 °C.
If the charger has no temperature cutoff, the cell can swell or vent on a wooden boat.
Evidence: `AqOneBuoy.ino:121-122` (solar plus an 18650); the charger part has not been checked.

## Medium findings

**M1. Dispatcher notes are cut at 40 bytes on the radio.**
The backend accepts notes of any length, but the shore keeps only the first 40 bytes for the radio, and the pod shows that fragment.
A safety instruction can lose its ending mid-word, and nothing on the dashboard warns the dispatcher.
Evidence: `sos.py:457`; `AqOneShore.ino:360-363`.

**M2. A reinstall gives the phone a new vessel identity.**
The vessel ID is generated on the phone and app backup is off, so reinstalling creates a new vessel, and so does the planned switch to release signing (SEC-32).
Any open SOS is orphaned with no way to stand it down or reply, the anomaly profile starts cold, and the old vessel lingers on the backend.
Evidence: `identity_store.dart:233-268`, `:339-346`; `AndroidManifest.xml:39`; `docs/archive/plans/59_SECURITY_AUDIT_REMEDIATION_IMPLEMENTATION_PLAN.md:287`.

**M3. Phones and boats don’t map one to one.**
Two phones on one boat create two vessels and two incidents for one emergency.
A phone moved to another boat keeps the old boat’s name, and a group sharing one phone looks like one vessel.
Evidence: `identity_store.dart:233-268`.

**M4. The shore never syncs its clock if it boots before the router.**
NTP starts only if WiFi connects within about 15 seconds of boot, and later reconnects never start it.
After a power cut the router usually takes longer, so the mesh never learns the time: warnings never expire on pods, chat loses its timestamps, and pods stop sending `server_time`.
Evidence: `AqOneShore.ino:110-134`, `:931-935`.

**M5. Buoy field hazards: theft, mooring boats, birds, drift, corrosion.**
Batteries and solar panels are worth stealing, and fishermen tie up to buoys or crowd them like fish aggregating devices, which exhausts the 10-client WiFi limit.
Seabird droppings cover solar panels, and a snapped mooring leaves a buoy relaying from far off its registered position.
A corroded antenna connector keeps `radioReady` true while nothing is heard.
Evidence: `AqOneBuoy.ino:88`, `:1119-1125`; needs a deployment test.

**M6. The only phone number on file is the phone at sea.**
A profile stores one phone number: the handset that is now offshore, often without signal.
There is no family or shore contact to confirm whether a boat is missing or its phone is just dead.
Evidence: `vessel_profile.py:17-33`.

**M7. An SOS can hitchhike on a neighbouring boat’s pod.**
All pods share one SSID, so a phone on a rafted boat can join the neighbour’s pod.
If that boat then leaves, it carries the SOS away in its queue, and C3 stops the phone trying anything else.
Evidence: `AqOneBuoy.ino:72-77`.

**M8. Two dispatchers acknowledging at once overwrite each other.**
Acknowledge is last-write-wins on status, note and ETA.
Two dispatchers answering the same call send the boat alternating messages, such as “Rescue boat on the way, 20 min” then “Coast Guard notified, 60 min”.
Evidence: `sos.py:460-491`.

**M9. One mistaken SAFE\_NOW ends the rescue with no way back.**
SAFE\_NOW resolves the incident, and a resolved incident cannot be reopened.
A slipped thumb, a child or a panicked tap closes the call, the rescue boat may be recalled, and the fisherman must start a new SOS.
Evidence: `sos.py:640-678`.
Related to SEC-20.

**M10. A call closed as a prank tells the boat “resolved”.**
A dispatcher who resolves a suspected prank without reaching the boat sends “resolved by MDRRMO” to the phone.
If the call was real, the fisherman’s only recourse is a new SOS.
Evidence: `sos.py:40-52`; `venture_page.dart:862`.

**M11. 915 MHz legality and neighbour interference are unresolved.**
The firmware transmits at 22 dBm on 915.0 MHz, a band that docs/33 still lists as an open item for the Philippines.
That frequency sits on the top edge of the GSM-900 uplink band (880 to 915 MHz).
A board ordered in the 433 MHz variant can never join, and says nothing.
Evidence: `AqOneLoam.h:60-78`.
Needs an NTC check.

**M12. Mesh chat is readable by anyone on the internet.**
`GET /api/mesh/chat` needs no login, so rivals or robbers can read what fishermen tell each other at sea, including where the catch is and who is out.
The pod also broadcasts the names of connected phones to everyone on its WiFi.
Evidence: `mesh.py:60-101`; `AqOneBuoy.ino:757-766`, `:792-794`.
Partly SEC-19.

**M13. A phone without a boat profile cannot send an SOS.**
`raiseSos` refuses without a vessel ID and boat name, and saves nothing.
A borrowed phone or a crew member’s phone gets “set up your boat” instead of an SOS, and the SOS button exists only on the map page.
Evidence: `sos_service.dart:68-72`; `venture_page.dart:333-336`, `:853`.

**M14. The free web service sleeps, so the first direct SOS can time out.**
Render’s free web service sleeps after about 15 idle minutes and takes tens of seconds to wake.
If the gateway is offline and no dashboard is open, a phone’s first direct SOS hits the 12-second timeout and waits for the next 20-second retry.
Evidence: `render.yaml:14`; `config.dart:49-51`.

**M15. The first clock a buoy hears wins until reboot.**
A pod takes the time from the first signed frame that carries `now` and never corrects it.
A replayed old frame, or chat relayed from a buoy with a wrong clock, can set it months off, so expired warnings reappear or current ones are dropped as expired.
Every pod shares its clock in chat frames, so the error spreads.
Evidence: `AqOneLoam.h:126-133`, `:567-570`.

**M16. A weak battery can reboot the pod mid-SOS in a loop.**
After boot the pod raises its WiFi access point and, within about 5 seconds, transmits any queued SOS at 22 dBm.
On a weak cell that current spike can brown out the board, which reboots and tries again, so the frame never completes.
Evidence: `AqOneBuoy.ino:1095-1151`, `:1169-1174`.
Needs a bench test.

**M17. Drift starts from the phone’s clock, even if it is years off.**
Drift takes its start time from the phone’s timestamp and rejects only values more than 5 minutes in the future.
A phone whose clock reset to an old date silently moves the drift start years back.
Evidence: `drift.py:475-497`.

**M18. An operator login stays valid for 7 days with no revocation.**
`JWT_EXPIRY_HOURS` is 168, and tokens are not checked against the account.
A dismissed or compromised account keeps acknowledge and resolve rights for up to a week.
Evidence: `render.yaml:35-36`.
Tracked as SEC-12.

## Low findings

**L1. Some SOS-flow text is English only.**
A few messages on the SOS path are hard-coded English, such as “SOS stood down.” and “No SOS sent yet.”, so an Aklanon-only user reads English at the worst moment.
Evidence: `venture_page.dart:391`; `home_page.dart:448`.

**L2. Midnight departures average to noon.**
The typical departure hour is a plain average of clock hours, so a fisher who leaves at 23:30 one night and 00:30 the next averages to 12:00 with a huge spread.
Evidence: `trip_profile.py:294-328`.

**L3. Trip distance is measured from the town centre.**
Distance is measured from the municipal centre rather than the boat’s own landing, so fishermen who launch from outlying barangays always look far out.
Evidence: `trip_profile.py:305-307`, `:552-561`.

**L4. Media volume at zero silences the SOS alarm.**
The alarm plays on the media stream, so a phone with media volume at zero stays silent and only vibrates.
Evidence: `sos_alarm.dart`.

**L5. Wet screens and pouches fight the 4-second countdown.**
Water on a touchscreen causes ghost touches that can cancel a real SOS during the slide-to-cancel countdown.
Through a waterproof pouch, the cancel slide can be too hard to do after an accidental tap.
Evidence: `venture_page.dart:42`, `:345-358`.

**L6. Old frames replayed after the duplicate filter rolls over are accepted.**
Frames carry a timestamp but nothing checks it, and the 64-entry filter forgets quickly.
A recorded frame replayed later counts as new: SOS merge harmlessly, but old warnings and answers come back.
Evidence: `AqOneLoam.h:297-353`.

**L7. Invalid UTF-8 in a pod push drops the phone’s chat connection.**
The pod pushes acknowledgements to phones as WebSocket text.
A note split mid-character (C8) makes an invalid text frame, which a standard client treats as a protocol error and disconnects.
Evidence: `AqOneBuoy.ino:927-943`.

**L8. A vessel with 20+ SOS rows can’t reconcile the older ones.**
The vessel feed returns only the newest 20 incidents, so older outbox records on a heavily pressed phone never match again and stay pending.
Evidence: `sos.py:593-606`.

**L9. A boat named “FALSE ALARM” labels its own real SOS.**
Boat names are free text and appear in the SOS title, so a joke name like “TEST ONLY” or “FALSE ALARM” makes a real call look dismissible.
Evidence: `dashboard-live-sos.js:116`, `:128`.

**L10. A firmware update can wipe an SOS waiting in the pod.**
If a new build changes the size of the queue record, the pod zeroes its stored queue on boot.
An SOS waiting in flash at that moment is erased, and the phone will not resend it (C3).
Evidence: `AqOneBuoy.ino:164-175`.

**L11. Coordinates are always labelled N and E.**
The dashboard appends “° N” and “° E” to any value, so a glitched negative or swapped coordinate still looks like a normal reading at a glance.
Evidence: `dashboard-live-sos.js:112`; `dashboard-vessels-alerts.js:216`.

**L12. Firmware timestamps wrap in 2106.**
Frame and phone timestamps are unsigned 32-bit values in firmware, which overflow on 7 February 2106.
Evidence: `AqOneLoam.h:224`; `AqOneBuoy.ino:137`.

**L13. Two phones with one identity in the same second merge.**
If a cloned phone shares a vessel ID and both phones press SOS in the same second, the backend merges them and keeps only the first position.
Evidence: `sos.py:213-225`.
