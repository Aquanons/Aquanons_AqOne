# 61 - Edge Case Remediation Design

**Status:** APPROVED by Len in chat, 2026-09-24, with the Section 12 decisions below.
Implementation plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`.

**Len's Section 12 decisions (2026-09-24):**
1. Hosting stays on Render's free tier with no spend.
   D9.1 and D9.2 are replaced by the zero-cost variant in docs/62 (a free-database rotation runbook, an expiry banner, and a free uptime ping).
2. Escalation channel: SMS.
3. to 8. Accepted as recommended, including both libraries (`flutter_foreground_task` and backend `cryptography`).
   Per-node keys and signed broadcasts are approved and remain gated after build step 3.
**Owner:** Lenard (architecture), with Arnold, Daniel, Jade and Doreen Kay per section.
**Created:** 2026-09-24
**Answers:** `docs/60_EXTREME_EDGE_CASE_REPORT.md` (68 findings, based on commit `a1d5cc5`).
**Re-verified against:** commit `0bad918` on `fix/security-audit-remediation` (security plan Phases 0 to 5 done).
**Method:** Clean Architecture rules for where policy lives, a Council debate for the contested decisions, and the Ponytail ladder to find the smallest fix.

---

## 1. Summary

The 68 findings do not need 68 separate fixes.
They come from **11 root causes**, and **12 design changes** (D1 to D12) address all of them.
Most of the Critical findings come from just three of those causes:

1. **The phone treats "a pod has it" as good enough and stops trying** (C3, C12, C13, M7, L10).
   Fix: `relayed` stops being the end of the line.
   The phone keeps trying until the backend confirms it has the SOS (D1).
2. **Fixed-size tables in firmware are treated as if they were unbounded** (C1, C2, C10, H14, H19, M15).
   Fix: the backend only sends what the smallest table can hold, and every table drops its least useful entry first instead of whatever sits in slot 0 (D5).
3. **Anonymous input reaches the fleet or quietly overwrites a real call** (C9, C14, H17, H21, M12).
   Fix: an unguessable incident nonce that travels end to end (D2), and a rule that SOS intake stays open to anyone while anything sent out to the fleet must be authenticated (D7).

The rest sort into dispatcher workflow safety (D3, D4), text encoding (D6), identity (D8), hosting (D9), honest AI (D10), handset behaviour at sea (D11) and hardware (D12).

Three findings are already closed or narrowed by the security remediation (Section 3).
Re-checking the code turned up one new risk, N1: now that the gateway verifies TLS, its clock may matter much more.

The one item with a hard date is **C5**.
The production database is on Render's free plan, created 2026-09-15, and will probably expire around 2026-10-15.
That is 21 days from today, and it does not wait for anything else.

---

## 2. How to read this

- Section 3 lists what has changed since the report was written.
- Section 4 sets the rules every design follows.
- Section 5 is the Council deliberation on the overall strategy.
- Section 6 maps findings to root causes.
- Section 7 is the design itself, D1 to D12.
  Each part gives the problem, the design, where the policy lives, contract changes, findings addressed, what we deliberately skip, and the one check it leaves behind.
- Section 8 is the full traceability matrix for all 68 findings.
- Sections 9 to 13 cover phasing, contracts, module placement, decisions needed and accepted risks.

Outcome words in the matrix:
**Closes** means the failure can no longer happen as described.
**Mitigates** means it becomes rarer, visible or recoverable, and a residual risk is named.
**Accepts** means we deliberately do not fix it, with the reason recorded.

---

## 3. Re-verification against `0bad918`

The report was written against `a1d5cc5`.
Security plan Phases 3 to 5 have landed since then.

| Finding | Change since report | Status now |
| --- | --- | --- |
| C13 MITM on gateway WiFi | SEC-28: `client.setCACert(BACKEND_CA_CERTS)` replaced `setInsecure()` | **Fixed in code**, hardware verification pending |
| H13 Mesh SOS lose seq without X-Api-Key | Phase 5: shore `postSos` sends `X-Api-Key` | **Fixed in code**, hardware verification pending |
| M18 7-day operator login, no revocation | SEC-12: `token_version` check on every request, `POST /api/logout` | **Revocation fixed**; the 7-day expiry remains (see D4) |
| H14 Warning broadcast once | SEC-29: WARN `rev` field; the buoy ignores older or equal revisions | **Narrowed**; the one-shot broadcast remains, but rebroadcast is now safe (D5) |
| C9 / M12 Anonymous mesh chat | SEC-19: 30-day retention only | **Still open** |
| C10 radio flood | SEC-30: chat needs more than 2 free TX slots | **Narrowed**; chat can no longer starve SOS frames, but downlink churn remains |
| C11 Shared radio key | SEC-26/27: key moved out of the repo; per-device keys deferred | **Still open**, by recorded decision |
| M9 One SAFE_NOW ends rescue | SEC-20: stand-down shown only once the backend has confirmed it | **Still open**; honesty improved, but there is still no way back |

All other findings were spot-checked at their evidence lines and still hold.
Line numbers in docs/60 have shifted by a few lines in `sos.py` and `AqOneShore.ino`.

### N1 (new) - The TLS fix may make the gateway's clock critical

SEC-28 turned on certificate verification.
If the ESP32 mbedTLS build checks certificate validity dates (`MBEDTLS_HAVE_TIME_DATE`), a gateway whose clock never synced (M4) will reject the backend's certificate.
Every HTTPS call would then fail: no SOS forwarded, no ACK, and pods retrying forever.
That would promote M4 from Medium to Critical.
**Needs a bench test:** boot the shore with the router off, bring the router up after 30 s, then try `postSos`.
D5 fixes M4 either way.

---

## 4. Design principles

### 4.1 Product invariants (unchanged, restated because every design is checked against them)

- The manual SOS path works independently of every model; AI is advisory only.
- The phone never needs cellular signal.
- The app never displays a later delivery state without evidence for it (`docs/06_DELIVERY_STATES.md`).
- SOS intake stays unauthenticated.
  A fisherman at sea has no account, and a rejected distress call is the worst possible outcome (settled in `sos.py` and docs/59).

### 4.2 New invariants this design adds

1. **Nothing short of backend evidence ends the phone's attempts.**
   A pod saying "accepted" does not mean MDRRMO has the call.
2. **SOS intake is open to anyone; anything sent to the fleet is authenticated.**
   Anyone may raise an SOS.
   Only MDRRMO, a verified vessel or the gateway may put words on fishermen's phones.
3. **The backend decides what the radio carries, sized to the smallest table on the path.**
   Firmware never has to guess what to drop.
4. **Every fixed table evicts by relevance, never by slot index.**
   Resolved before open, old before new, and chat before distress.
5. **Every byte limit is enforced on UTF-8 character boundaries at every layer.**
   A distress call is never rejected over text formatting; it is truncated safely instead.
6. **Closing a call is never final.**
   Every resolve has a reason, can be undone, and never silently closes the call on the boat's screen.
7. **"No data" never looks like "all clear".**
   Every monitor that can be blind says so.

### 4.3 Clean Architecture rules applied here

- Business policy is written as plain functions with no FastAPI, asyncpg, Flutter, or Arduino types in their signatures.
  Examples are incident lifecycle transitions, downlink selection, triage order, escalation rules and the phone's retry policy.
- Adapters (`app/api/*.py`, `SosService`, the `.ino` loop) stay humble: they parse, call the policy, persist and send.
- No repository interfaces and no ports with one implementation.
  SQL stays in the API adapter.
  The boundary is enforced by the policy module importing nothing from the outer layers, which one test checks (Section 11).
  This is the lightest boundary that can still be enforced, and it is the point where the Clean Architecture and Ponytail lenses agree.
- Contracts are changed in their docs first (Section 10), then in code.

### 4.4 Ponytail rules applied here

- Reuse before writing.
  Examples: SEC-29's `rev` makes rebroadcast safe for free, the existing pairing-code enrolment is the verification path, and the existing COALESCE merge fills late positions.
- Use native platform features before new dependencies.
  Examples: ESP32 eFuse MAC for node IDs, SX1262 channel activity detection, both ESP32-S3 cores, Android `CompanionDeviceManager` and `WifiNetworkSpecifier`, the Android alarm audio stream, and the browser Notification API.
- Only two new dependencies are proposed, both behind a decision (Section 12): an Android foreground-service plugin (D1) and `cryptography` on the backend (D7, roadmap only).

---

## 5. Council deliberation: overall strategy

Mode B, two-round debate.
The question: *how should AqOne answer 68 edge cases while the radios are still untested (build step 2 not done)?*

### Round 1 - Opening positions

- 😈 **Devil's Advocate:** Most firmware findings are theoretical until two boards talk.
  Fixing C1, C2 and C10 now could mean fixing code that step 2 rewrites anyway.
  Meanwhile C5 takes production down in three weeks and nobody is looking at it.
- ✂️ **Simplicity Champion:** 68 tickets is a bug farm.
  Group them by root cause and most disappear.
  C3 alone is the multiplier behind C8, C12, C13, M7 and L10.
  Changing one query (`awaitingRelay`) to also include `relayed`, plus a deadline, closes the silent-loss consequence of five findings.
- 🛡️ **Security Auditor:** Distress intake is deliberately open, so everything downstream of it must assume hostile input.
  The dangerous findings (C9, C11, C14) are where anonymous input gets *amplified*: sent to the whole fleet, or merged into a real call.
  Keep intake open, but authenticate anything that fans out.
- 🛠️ **Architect / DX Lead:** `sos.py` is 722 lines of HTTP, SQL and lifecycle policy mixed together.
  Adding resolve reasons, reopen, versions, triage and downlink caps there makes it unreadable at 2 AM.
  Extract the policy into small pure modules before adding to it.

### Round 2 - Rebuttal

- 😈 → ✂️: "Keep retrying `relayed`" means a phone with no internet and a fake pod re-hands the SOS to the same fake pod forever.
  You have hidden the bug, not fixed it.
  - ✂️ answers: True, and that part is roadmap (pod pairing, D11).
    But today the phone *stops*, even when 4G comes back.
    Retrying the direct path closes the common case at once.
    The fake-pod-and-no-internet case stays as a named residual.
- ✂️ → 🛠️: Do not build a repository layer, a domain package and a notifier interface for one database and one SMS provider.
  - 🛠️ concedes: Pure policy modules only.
    SQL stays where it is, and there are no interfaces until a second implementation exists.
- 🛡️ → ✂️: Nonces and per-node keys are not over-engineering.
  C14 only needs a laptop and a list of vessel IDs heard on the radio.
  - ✂️ concedes the nonce: it is one column, one field and one index, and it also fixes H17, L13 and L8.
    It holds the line on per-node keys and signed broadcasts until the radios work, because nobody can test crypto on radios that do not yet exchange a packet.
- 😈 → 🛡️: Authenticating chat still leaves the shared LoRa key.
  Anyone with a pod's flash can still fake MDRRMO over the air.
  - 🛡️ answers: Yes, that is C11, and it is the only fix that needs new cryptography.
    Recorded as a decision for Len (Section 12), gated after build step 3.

### Synthesis

#### 1. Grounding

- **Observed facts:**
  - The findings were re-checked against `0bad918` (Section 3).
  - `awaitingRelay` selects `state = saved` only (`outbox_store.dart:42-51`).
  - `watchVessel` evicts slot 0 (`AqOneShore.ino:362-366`).
  - `trackVessel` returns null when full, with no eviction (`AqOneBuoy.ino:314-325`).
  - `POST /api/mesh/chat` has no auth dependency (`mesh.py:42-43`).
  - The dedupe key is `(vessel_id, client_ts)` (`sos.py:213`).
  - The downlink has `LIMIT 100` and no age limit on open incidents (`sos.py:413-427`).
  - Pairing-code enrolment already exists (`vessel_auth.py:46-168`), but no screen uses it.
  - Device tokens last 24 hours, and refreshing one requires an unexpired token.
  - There is no SSE on the backend or the dashboard, which polls every 3 s.
  - `render.yaml` sets `plan: free` for both the database and the web service.
- **Unverified assumptions:**
  - The Render free Postgres expiry date and terms.
  - Whether mbedTLS checks certificate dates (N1).
  - Android OEM background-kill behaviour on target phones.
  - SF10 airtime of about 2.2 s per SOS frame.
  - Which LoRa band the NTC allows in the Philippines.
  - That fishermen will tolerate a persistent notification while an SOS is pending.

#### 2. Perspectives and debate

- 😈 **Devil's Advocate:** Do firmware work only after build step 2, but do the date-driven hosting move now.
- ✂️ **Simplicity Champion:** Fix root causes, not findings; roughly 12 mechanisms, and most are small diffs.
- 🛡️ **Security Auditor:** Intake open, fan-out authenticated; the nonce now, crypto after step 3.
- 🛠️ **Architecture / DX:** Pure policy modules, humble adapters, contracts first.

#### 3. Consensus vs tension

- **Where all seats agree:**
  - C5 first.
  - C3 is the highest-leverage software fix.
  - The dashboard must not let one click close a live call.
  - Firmware changes wait for two boards that talk.
- **Core tension:** fixing on paper now (theoretical correctness) against fixing once the hardware can be measured (evidence).
  It is resolved by phasing: backend, dashboard and phone now; firmware on the bench; radio behaviour in the field.

#### 4. The verdict

- **Recommended path:**
  - Phase 0: hosting.
  - Phase 1: software-only fixes that need no radio.
  - Phase 2: firmware, once build step 2 passes.
  - Phase 3: field-gated items.
  - Phase 4: roadmap items needing Len's decisions.
- **Revisit when:**
  - Build step 2 fails in a way that changes the frame format (redo D2/D5 frame fields).
  - The range test shows pods reach the gateway directly (drop relay work in D5.6).
  - The team decides to keep the Render free tier (then D4.4 escalation and D9 scheduling need another host).

---

## 6. Root-cause map

| # | Root cause | Findings |
| --- | --- | --- |
| R1 | The phone treats "a pod has it" as final | C3, C12, C13, M7, L10, H2, H15, M14 |
| R2 | Incident identity is guessable and coarse: `(vessel_id, client_ts)` and a per-pod `seq` | C14, H17, H5, L13, L8, M3 |
| R3 | Incident lifecycle is one-way, with no reason, version or reopen | C7, M8, M9, M10, H4, M1 |
| R4 | Dispatcher attention depends on an open, clicked, foreground browser tab | C6, H18, L9, L11, M18 |
| R5 | Fixed firmware tables have no relevance-based eviction, and the backend overfills them | C1, C2, C10, H14, H19, H11, M4, M15, L6 |
| R6 | Text limits are counted in characters in one layer and bytes in another | C8, L7, M1 |
| R7 | Anonymous input fans out to the fleet, or looks like corroboration | C9, C11, C12, M12, H19, H20, H21 |
| R8 | Identity is tied to the phone, not the boat, and verification has no working path | H10, H21, M2, M3, M6, M13, L9 |
| R9 | Single points of failure in hosting and gateway | C5, M14, H12, H6 (schedule) |
| R10 | AI monitors can be blind without saying so, or are tuned to the wrong prior | H6, H7, H8, H9, H16, L2, L3, M17 |
| R11 | Physical and at-sea conditions the code does not model | C4, H1, H3, H22, H23, L4, L5, L1, M5, M11, M16, L12 |

---

## 7. The design

Position of each design change along the SOS path:

```text
 [Phone]----WiFi----[Pod]====LoRa====[Gateway]----HTTPS----[Backend]----poll----[Dashboard]
  D1 retry policy    D5 tables         D5 downlink cap        D2 nonce merge         D3 resolve/reopen
  D2 nonce           D6 utf8Copy       D5 NTP, dual-core      D3 lifecycle           D4 alarm, triage
  D6 byte clamp      D5 node ID        D6 utf8Copy            D4 escalation          D8 badges
  D8 enrol, backup   D12 button, GPS   D9 2nd gateway         D7 fan-out auth
  D11 GPS, WiFi bind                                          D9 paid tier, scheduler
                                                              D10 honest AI
```

### D1 - Delivery policy: `relayed` is not terminal

**Problem (R1).**
Once any pod replies `accepted`, the phone moves the record to `relayed` and never retries any route (`outbox_store.dart:42-51`, `sos_service.dart:129-133`).
Any downstream failure then strands the SOS silently.
Causes include no range, a fake pod, a MITM, text encoding, a flat pod, a neighbour's pod leaving, or a queue wipe on a firmware update.
Retries also live in in-process timers that Android kills (H2).
An SOS never sent comes out days later looking like a new call (H15).

**Design.**

1. A pure function `DeliveryPolicy.routesDue(record, now)` in `mobile/lib/models/delivery_policy.dart` returns which routes to attempt now.
   - `saved`: pod and direct, every retry tick (today's behaviour).
   - `relayed`: direct on a backoff of 20 s, 60 s, 5 min, then 5 min thereafter.
     The pod is tried again only after `podDeliveryDeadline` (10 min) passes with no delivery evidence.
     Handing off to the same pod again is safe because the pod treats it as a duplicate; handing off to a different pod is a genuine second chance.
   - `delivered` or later: no retries; reconcile only.
2. `OutboxStore.awaitingRelay()` becomes `awaitingDelivery()`: `state IN (saved, relayed)`.
   `SosService.retryPending()` asks the policy which routes to try for each record.
3. **Honest UI.**
   After the deadline, a `relayed` record shows "Your pod has not confirmed delivery to MDRRMO. Still trying."
   It never shows "sent".
4. **Background survival (H2).**
   While any record is `saved` or `relayed`, the app runs an Android foreground service with a persistent notification ("SOS pending - trying to deliver").
   The same retry loop runs inside it.
   During onboarding, the app asks for battery-optimisation exemption.
   The service stops when every record is at least `delivered`.
5. **Late SOS (H15).** Never dropped.
   - The backend already stores `client_ts`.
     The dashboard labels any call where `created_at - client_ts > 30 min` as **"LATE - pressed 3 d 4 h ago"** and uses the press time as the incident time.
   - On app open, any unsent record older than 12 h triggers a prompt: "An SOS from <date> was never delivered. Still send it?"
     The default is send, and it goes after 60 s with no answer.
     A home test can be cancelled; an unconscious fisher's call still goes out.

**Where the policy lives.**
`delivery_policy.dart` is pure Dart with no plugins and takes an injected `now`.
`SosService` is the adapter that executes the routes it returns.

**Contracts.**
`docs/06_DELIVERY_STATES.md` gets a new rule: "`relayed` is not terminal. The handset keeps attempting the direct path until `delivered`."
`docs/05` gets the dashboard "late" rule.

**Addresses.**
- Closes C3, H2 (to be measured per OEM) and H15.
- Mitigates the silent-loss consequences of C12, C13, M7, L10 and C8 whenever any internet appears.

**Skipped.**
Pod pairing, which is what would prevent handing off to a fake pod at all, is roadmap (D11.3).
Residual risk: a fake pod combined with no internet for the whole emergency.

**Check left behind.**
One table test of `routesDue` covering each state, both sides of the deadline and the backoff steps.
One widget test for the "not confirmed" copy.

---

### D2 - End-to-end incident nonce

**Problem (R2).**
- The merge key `(vessel_id, client_ts)` is guessable (C14) and too coarse (L13).
- Mesh answers are matched on a per-pod `seq` that restarts after a flash erase (H17).
- A note added after the SOS is dropped by the pod's duplicate check (H5).
- The vessel feed caps at 20 rows (L8).

**Design.**

1. The phone generates `nonce`: a 32-bit value from `Random.secure()` per SOS, stored in a new outbox column (schema v15).
2. The nonce travels on every path:
   - direct JSON `nonce`
   - pod handoff `nonce`
   - LoRa SOS payload key `nc` (about 14 bytes; it survives the retry-time shedding of `boat` and `n`)
   - T_ETA payload `nc`, replacing `sq`
   - pod `/v1/sos/status` `nonce`
3. **Backend merge.**
   New column `sos_events.nonce BIGINT`, with a partial unique index on `(vessel_id, nonce) WHERE nonce IS NOT NULL`.
   Ingest branches:
   - with a nonce: `ON CONFLICT (vessel_id, nonce)`
   - without one (older APKs): today's `(vessel_id, client_ts)`
   The legacy branch is removed once no pre-nonce client is in the field.
4. **Race hardening (C14 residual).**
   Suppose an anonymous row exists and a gateway-authenticated delivery of the same `(vessel_id, nonce)` arrives with a position more than 1 km away.
   Both positions are kept (`alt_latitude`, `alt_longitude`, `position_conflict = true`), and the dashboard shows both.
   This covers an attacker who sniffs the nonce off the air and races the gateway.
5. **Phone matching (H17).**
   `_applyRemote` matches on `local_id`, then `nonce`, then `seq` (legacy).
   The pod's tracked table is keyed by vessel and nonce.
6. **Pod fill-if-empty (H5, and H1 on the mesh path).**
   When a handoff duplicates a queued `(vessel_id, nonce)`, the pod fills an empty `note`, `lat` or `lon` from the new request instead of ignoring it.
   This mirrors the backend's COALESCE merge, so the rule is the same everywhere.
7. **Vessel feed (L8).**
   `GET /api/sos/vessel/{id}` returns every unresolved incident plus the newest 20 resolved ones, not the newest 20 overall.
8. **Multiple phones on one boat (M3, partial).**
   The dashboard groups open incidents from the same `vessel_id` into one card ("2 calls from this vessel").

**Where the policy lives.**
Merge rules stay in SQL; this is a data invariant, so it belongs in the database.
The conflict flag rule is a small pure function in `app/incidents/merge.py`.

**Contracts.**
`docs/02` (the `nc` field in SOS and ETA payloads), `docs/03` (handoff `nonce`, duplicate fill-if-empty, status `nonce`) and `docs/04` (`SosIn.nonce`, merge rule, `position_conflict`).

**Addresses.**
Closes C14 for nonce-carrying clients (residual: an on-air key holder racing, which is flagged and not silent), H17, H5, L13 and L8.
Mitigates M3.

**Skipped.**
128-bit nonces: 32 bits within a single vessel is enough, because an attacker has to guess before the real call arrives.
A full UUID over LoRa: no room.

**Check left behind.**
Backend test: pre-create rows for 60 consecutive `client_ts` values with a fake position, then send the real SOS with a nonce; it must create a new, unresolved row.
Phone test: two remote rows with the same seq and different nonces; the phone matches the right one.

---

### D3 - Incident lifecycle: reasons, versions, reopen

**Problem (R3).**
- Resolve is one click, with no reason and no undo (C7).
- A prank closure tells the boat "resolved" (M10).
- A mistaken SAFE_NOW is final (M9).
- Concurrent acknowledgements overwrite each other (M8).
- Every acknowledgement promises an ETA, 20 minutes by default (H4).
- Notes get cut at 40 bytes on the radio (M1).

**Design.**

1. **Pure lifecycle module** `backend/app/incidents/lifecycle.py`:
   - States: `open`, `acknowledged`, `resolved`.
   - `ResolutionReason`: `rescued`, `safe_confirmed` (dispatcher reached the boat), `stood_down_by_fisher`, `duplicate`, `closed_unconfirmed` (suspected prank, boat not reached).
   - `boat_message(reason)` is the single table that decides what the boat is told:
     - `rescued`, `safe_confirmed`, `stood_down_by_fisher`: "Closed by MDRRMO."
     - `duplicate`: nothing new; the phone follows the surviving incident.
     - `closed_unconfirmed`: "MDRRMO closed this call without reaching you. If you still need help, press SOS again." (M10)
   - `can_transition(from, to, actor)`: the only place transitions are allowed or refused.
2. **Resolve requires a reason** (`ResolveIn.reason_code`, required; the free-text `reason` stays optional).
3. **Reopen.**
   - `POST /api/sos/{id}/reopen` (responder roles, audited) clears `resolved_at`, keeps the history in the audit log, and puts the incident back in `/active` and the downlink.
   - A fisher reply of `STILL_IN_DANGER` within 2 hours of a resolve reopens the call automatically and rings the dashboard alarm (M9).
     Today the reply route freezes after a resolve (`sos.py:658`); that rule changes only for this case.
4. **Versioning (M8).**
   - `sos_events.version INT NOT NULL DEFAULT 0` is incremented by every write.
   - Acknowledge, resolve and reopen accept `expected_version`.
     A mismatch returns 409 with the current row.
   - The dashboard then shows "Answered by <name> at 14:02: Coast Guard notified, 60 min. Review before sending."
   - Old clients that send no `expected_version` keep last-write-wins.
5. **ETA honesty (H4).**
   - The acknowledge dialog defaults to **"Received - no ETA yet"** (`eta_minutes: null`), which the backend already supports.
   - ETA is picked from quick buttons (15, 30, 45, 60, 90, 120 min) or a duration field, and the dialog previews the absolute time ("arrives about 14:35").
   - The phone shows "Help is being arranged - no arrival time yet" when `eta_at` is null.
6. **Note budget (M1).**
   `AcknowledgeIn.responder_note` is validated at 40 UTF-8 bytes or less, with a 422 whose message the dashboard shows.
   The dashboard displays a live byte counter.
   The gateway then never needs to truncate.
7. **Phone-side SAFE_NOW friction (M9).**
   Stand-down asks for a slide and a confirmation screen ("Rescue will be called off").
   A 2-minute **Undo** follows, which sends `STILL_IN_DANGER`.

**Where the policy lives.**
Transitions, reasons, boat messages and the auto-reopen window live in `app/incidents/lifecycle.py` as pure functions.
`sos.py` calls them and runs the SQL.
The dashboard renders reason labels from `docs/05`, not from its own copy.

**Contracts.**
- `docs/05`:
  - `reason_code` required on resolve
  - `POST /reopen`
  - `expected_version` and 409
  - `responder_note` limited to 40 bytes
  - boat message per reason
- `docs/13_RESPONDER_LOOP.md`: the reason vocabulary.
- `docs/06`: an incident can leave `resolved`.

**Addresses.**
Closes C7 (with D4's confirm dialog), M8, M9, M10, H4 and M1.

**Skipped.**
Separate internal dispatcher notes: `resolved_reason` free text already covers that.
Full event sourcing: the audit log already records every transition.

**Check left behind.**
One table test of `can_transition` and `boat_message`.
One API test: two acknowledgements with the same `expected_version`; the second gets 409.

---

### D4 - Dispatcher attention that does not depend on a browser tab

**Problem (R4).**
- A call waiting at page load never rings (C6).
- Browsers block audio until a click, background tabs slow the poll, and the session expires after 7 days.
- A flood buries the real call and freezes the browser (H18).
- Joke boat names and coordinates always labelled N/E mislead at a glance (L9, L11).

**Design.**

1. **First-load alarm (C6).**
   On first load, `sosAlarm.sync(events)` runs and starts the alarm if any event is unacknowledged.
   The old comment's goal ("don't ring for handled events") is kept, because "handled" means acknowledged.
2. **Audio unlock.**
   A red, persistent "Alarm sound is OFF - click to enable" banner shows until an `AudioContext` has been resumed by a user gesture.
3. **Background tab.**
   On every new SOS, the page also raises a browser `Notification`.
   Notifications fire from background tabs, a native feature.
   The document title flashes "(1) SOS".
   The existing LIVE/STALE/OFFLINE indicator stays.
4. **Out-of-band escalation watchdog.**
   This is the only fix that survives "no dashboard open".
   - Pure policy `app/incidents/escalation.py::due_for_escalation(events, now)` returns unacknowledged, non-synthetic incidents older than 2 minutes that have not yet been escalated.
   - A scheduled task (D9.3) runs it every 30 s and sends through one adapter function, `notify_oncall(text)`.
     The channel (SMS, email or Telegram) is a decision for Len (Section 12).
   - Escalations are recorded in the audit log so nothing escalates twice.
5. **Session continuity (M18 remainder).**
   - `POST /api/token/refresh` issues a new token while the current one is valid and has less than 24 h left.
     SEC-12 revocation still applies to the new token.
   - A banner warns one hour before expiry.
   - The 7-day ceiling is kept only for idle sessions.
6. **Flood triage (H18).**
   - `/active` gains an optional `limit` (default 200) and returns `total`.
   - Rows are ordered by the pure `app/incidents/triage.py::priority`:
     unacknowledged first, then corroborated (gateway-delivered, `phone_verified`, or a vessel with trip history), then newest.
     SEC-07's intent holds: a flood cannot push out a known vessel's call, because it sorts first.
   - The dashboard renders the first page and shows "+N more".
     A **flood banner** appears when more than 10 new unknown vessels arrive in a minute.
   - The alarm rings once per burst, not once per row.
7. **Display hygiene (L9, L11).**
   - The incident title is always "SOS - <vessel id>", with the boat name in quotes as a subtitle.
   - Coordinates get a hemisphere from their sign (`11.7° N`, `-11.7` becomes `11.7° S`).
   - A position that `app/geo.py` rejects as not at sea is shown with an "on land?" flag.

**Where the policy lives.**
`escalation.py` and `triage.py` are pure.
The dashboard only renders the order the backend sends.

**Contracts.**
`docs/05`: `limit`, `total`, triage order, token refresh, and escalation behaviour.

**Addresses.**
Closes C6, L9 and L11.
Mitigates H18, and M18 beyond what SEC-12 already fixed.

**Skipped.**
SSE or WebSockets for the dashboard.
The watchdog removes the dependency on a live tab, so real push is an improvement, not a fix.
Add it when the 3 s poll becomes a measured cost.

**Check left behind.**
A web test: first load with one unacknowledged event starts the alarm.
A pure test of `due_for_escalation`.

---

### D5 - Bounded radio tables and a radio budget

**Problem (R5).**
- Every pod ships as `BUOY01` (C1).
- The buoy's 8-slot tracked table never evicts (C2).
- The gateway evicts slot 0 against an uncapped downlink, re-broadcasting forever and wearing out flash (C10).
- Warnings are sent once (H14).
- Anyone on a pod's WiFi can fill its queue (H19).
- Relays collide (H11).
- Clocks: the shore never syncs if it boots before the router (M4), the first clock a buoy hears wins (M15), and old frames replay (L6).
- The shore is deaf to the radio during each HTTPS call (H12).

**Design.**

1. **The backend caps the downlink (C10, C2).**
   `app/incidents/downlink.py` defines `DOWNLINK_MAX = 12` and the selection rule:
   - Exclude `is_synthetic` rows.
   - Include open incidents with any change in the last 24 h, plus incidents resolved within the last 6 h (today's closure window).
   - Priority order: acknowledged-open with a new change, then unacknowledged-open, then resolved closures.
   - Within each band, the most recent change first.
   - `LIMIT DOWNLINK_MAX`.
   The number matches the smallest table on the path, and `docs/04` states that as the contract.
2. **The gateway mirrors the feed (C10).**
   - The watch set becomes "the vessels in the last feed, plus vessels heard in a T_SOS within 6 h".
   - Eviction is least recently changed, never slot 0.
   - Flash is written at most once a minute, and only when the set changes because of a T_SOS.
   - **Airtime budget:** at most 4 T_ETA frames per poll, oldest-sent first; anything left waits for the next poll.
   - Open, acknowledged incidents are re-sent every 10 min, so a boat that comes back into range still hears its answer.
3. **Buoy tracked table (C2).**
   `MAX_TRACKED` rises to 12, matching `DOWNLINK_MAX`; it costs about 130 bytes of RAM per slot.
   When full, it evicts resolved entries first, then the one least recently updated.
   Entries resolved more than 6 h ago are cleared on the next T_ETA.
4. **Warnings (H14).**
   The gateway rebroadcasts every active warning every 10 min.
   SEC-29's `rev` makes a repeated WARN a no-op on pods that already have it.
   Pods evict expired warnings first, then the lowest priority, then the oldest.
5. **Node identity (C1).**
   - `NODE_ID` defaults to the lower 32 bits of `ESP.getEfuseMac()`, and `NODE_NAME` to `POD-XXXX` from the same bits.
   - `#define AQONE_NODE_ID` stays as an optional override (useful for the shore).
   - The mesh frame counter starts at `esp_random()` at boot, so two fresh boards do not collide on seq.
6. **Relay discipline (H11, field-gated).**
   - Channel activity detection (RadioLib `scanChannel()`) runs before every TX.
   - The relay delay is random in `[0, 2 × getTimeOnAir(len)]`, not 200 to 600 ms.
   - **Counter suppression:** if the same `(src, seq, type)` is heard relayed during my backoff, my relay is cancelled.
   - Pods relay only T_SOS and T_ACK; relay buoys relay everything.
     This follows `docs/55` (pods direct to shore, `HOPS = 0`).
7. **Clocks (M4, M15, L6, N1).**
   - The shore calls `configTime` on every uplink reconnect, not just at boot.
     It does not stamp `now` into frames until `time(nullptr)` is after 2026-01-01.
   - Buoys adopt `now` only from shore-originated frame types (T_ACK, T_ETA, T_WARN, T_PING), never from T_CHAT.
     They re-adopt from each newer shore frame, so a wrong clock heals.
   - With a valid clock, frames whose `now` is more than 10 min in the past are dropped as replays.
8. **Pod queue fairness (H19).**
   Each WiFi client (station MAC) may hold at most 2 queued SOS; the queue total stays 12.
   The dashboard wording changes from "LoRa mesh via BUOY01" to **"Relayed by pod POD-1A2B - sender not verified"**.
9. **Gateway never deaf (H12).**
   - HTTPS work moves to a FreeRTOS task pinned to core 0, fed by a queue.
     The radio loop on core 1 never blocks.
   - Each downlink poll records the gateway's last-seen time on the backend.
   - The dashboard shows "Gateway last heard 14:02" and turns red after 3 missed polls.
10. **Firmware update safety (L10).**
    The pod exposes queue depth on `/v1/status`.
    The flashing procedure in `firmware/README.md` requires depth 0 first.
    A size mismatch at boot logs the number of entries lost, instead of dropping them silently.

**Where the policy lives.**
- Downlink selection lives in `app/incidents/downlink.py` (backend policy).
- The firmware eviction comparators, clock-adoption rule and replay window are small functions in `AqOneLoam.h`, shared by both sketches, so they stay byte-identical by construction.

**Contracts.**
- `docs/04`: downlink cap, order, selection and the gateway last-seen.
- `docs/02`: node ID derivation, relay rules, clock adoption, replay window, WARN rebroadcast cadence.
- `docs/03`: per-client queue cap.

**Addresses.**
- Closes C1, C2, C10, H14, M4, M15 and L6.
- Mitigates H11 (needs field measurement), H12 (a second gateway is D9), H19 and L10.
- Tests N1.

**Skipped.**
- Flash wear-levelling analysis: rate-limited writes remove the churn.
- A dynamic route table or any real routing protocol.
  Flooding with suppression is enough at this scale, and `docs/55` makes most traffic direct.

**Check left behind.**
- Backend: a downlink test with 30 open incidents returns exactly 12 in priority order.
- Firmware: a two-board bench script (flash two default builds, send an SOS from each, and assert two distinct `src_id` values and two backend rows).

---

### D6 - UTF-8 safe text at every layer

**Problem (R6).**
Buffers are counted in bytes in firmware and in UTF-16 units on the phone (`_clampNote` uses `substring`).
The shore cuts notes at 40 bytes with `String.substring`.
A split `ñ` or emoji then produces invalid UTF-8, and different layers fail differently:
- the backend may reject it
- the pod serves invalid JSON text
- the phone's WebSocket drops the connection (C8, L7)

**Design.**

1. **One firmware helper** in `AqOneLoam.h`: `size_t utf8Copy(char* dst, size_t dstSize, const char* src)`.
   It copies at most `dstSize - 1` bytes, backs off to the last complete character, replaces invalid sequences with `?`, and always null-terminates.
   Every `strncpy` of user or backend text in both sketches is replaced with it:
   - buoy queue fields, tracked fields, chat lines and warning fields
   - the shore note, which today is `String(note).substring(0, 40)`
2. **Phone:** `_clampNote` and the boat-name clamp count UTF-8 bytes (`utf8.encode(...).length`) and cut on a character boundary.
   `buoy_client.dart` decodes with `utf8.decode(bytes, allowMalformed: true)`, so older pod firmware cannot crash the parser.
3. **Backend:** `SosIn.note` and `SosIn.boat` are **truncated** on character boundaries to 64 and 32 bytes by a `BeforeValidator`, not rejected with 422.
   A distress call must never fail over a note's length.
   `AcknowledgeIn.responder_note` keeps its 40-byte validation (D3.6), because it is the dispatcher's input and they can fix it.

**Where the policy lives.**
One helper per language, each the single choke point for that layer.

**Contracts.**
`docs/02` and `docs/03`: "all text fields are UTF-8, and byte limits are enforced on character boundaries."
`docs/04`: truncation, not rejection.

**Addresses.**
Closes C8 and L7.
Supports M1.

**Skipped.**
Unicode normalisation (NFC) and grapheme-cluster-safe cutting.
Cutting on a code-point boundary keeps the text valid, which is what matters here; a split emoji modifier is only cosmetic.

**Check left behind.**
- A host-side C test of `utf8Copy`, compiled with the system `gcc` (`firmware/test/utf8_copy_test.c`), with cases `ñ` at the boundary, a 4-byte emoji, invalid input and an empty string.
- A Dart test for the byte clamp.
- A backend test: a 70-byte note containing `ñ` is accepted and stored as 64 valid bytes.

---

### D7 - Open intake, authenticated fan-out

**Problem (R7).**
- Anyone can post "MDRRMO" chat onto every phone at sea (C9) and read the fleet's chat (M12).
- The shared radio key lets any key holder fake ACKs, ETAs and warnings (C11).
- A fake pod swallows calls (C12).
- Prank calls through a pod look corroborated (H19).
- Rescuers can be baited (H20).
- Blank profile fields can be filled by anyone (H21).

**Design.**

1. **Mesh chat (C9, M12).**
   - `POST /api/mesh/chat` requires one of three credentials:
     - an operator session: sender is the account's display label, `origin=mdrrmo`
     - a vessel device bearer: sender is the vessel's boat name, `origin=app`
     - the gateway key: `origin=mesh`, sender as relayed
   - Anonymous posts get 401.
   - Reserved sender names (MDRRMO, Coast Guard, PCG, PAGASA, Admin; case-insensitive after stripping punctuation) are refused unless `origin=mdrrmo`.
   - Per-sender limit: 6 posts a minute, via an in-memory token bucket.
     A `ponytail:` comment notes the ceiling (single instance; move to Postgres if scaled out).
   - `GET /api/mesh/chat` requires the gateway key, an operator session or a vessel device bearer.
   - Only `origin=mdrrmo` lines render with the "Official" badge on phones and pods.
2. **Plausibility flags (H20), advisory only.**
   Pure `app/incidents/plausibility.py::flags(event, context)` returns zero or more of:
   - `position_on_land`
   - `position_beyond_radio_range`: a mesh-delivered position further from the gateway than the modelled maximum range in `docs/33`
   - `position_jump`: more than 20 km from the vessel's last contact within 1 h
   - `many_calls_same_vessel`
   - `position_conflict` (from D2)
   They are computed on read in `/active` and shown as small grey tags.
   They never block, delay or reorder a call.
   This is the "AI is advisory" rule applied to non-AI heuristics.
3. **Profile fields (H21).**
   Once a vessel has any active enrolled device (D8), *every* profile write needs that device's bearer, including filling blank fields.
   For vessels with no enrolled device, blank fills stay allowed, but each field records `set_by` (`device`, `anonymous`, or `operator`).
   The dashboard shows anonymous phone numbers as "unverified".
4. **Pod queue provenance (H19):** covered by D5.8.
5. **Radio authenticity (C11), roadmap and decision-gated.**
   This reopens the docs/59 deferral.
   - **Per-node derived keys.**
     `K_node = HMAC-SHA256(LOAM_MASTER, node_id)`.
     Pods are provisioned with only their own `K_node`; the gateway holds the master and derives any key.
     The pod signs SOS uplink with `K_node`, and the gateway signs the ACK for that pod with the same key.
     A stolen pod then only lets someone forge its own ACKs.
     Frames keep a short network tag under the shared key, so relays can still filter junk they cannot verify end to end.
   - **Signed broadcasts.**
     WARN, T_ETA and MDRRMO chat frames carry an ECDSA P-256 signature (64 bytes) made by the *backend*.
     The private key is a backend environment variable and never sits on the mast; the gateway only forwards it.
     Pods verify with a baked-in public key using mbedTLS, which is already linked for HMAC.
     The backend would need `cryptography` (a new dependency).
     The airtime cost is about +0.4 s per broadcast at SF10; broadcasts are rare.
   - This needs build step 3 to pass first, because crypto cannot be tested on radios that do not yet talk.
6. **Fake pods (C12).**
   The consequence is mitigated now by D1.
   The cause is fixed by pod pairing (D11.3).

**Where the policy lives.**
The chat authorisation rule, the reserved-name check and `plausibility.flags` are pure functions.
FastAPI dependencies only extract credentials.

**Contracts.**
- `docs/05`: chat auth, reserved names, plausibility flags.
- `docs/04`: gateway chat origin.
- `docs/02`: key derivation and broadcast signature, when approved.

**Addresses.**
- Closes C9 and M12.
- Mitigates H19, H20, H21, and C12 (via D1).
- C11 is designed but decision-gated.

**Skipped.**
- IP-based rate limiting on SOS intake: it conflicts with open intake, and D4.6 triage handles floods.
- CAPTCHA or proof of work.
- Encrypting chat over LoRa: fishermen share the airwaves, and privacy against radio listeners is out of scope.

**Check left behind.**
API tests: an anonymous chat post gets 401, a vessel posting as "MDRRMO" gets 422, and an operator post comes out as `origin=mdrrmo`.
A pure table test of `plausibility.flags`.

---

### D8 - Identity and verification that actually work

**Problem (R8).**
- A FishR badge keyed on free text would be forgeable, and no verification path is wired up (H10).
- A reinstall creates a new vessel (M2).
- Phones and boats do not map one to one (M3).
- The only phone number on file is the one at sea (M6).
- A phone without a profile cannot send an SOS (M13).
- Joke boat names label the call (L9, handled in D4).

**Design.**

1. **Verification is in-person enrolment, which already exists.**
   - An MDRRMO officer checks the FishR registration in person and issues a pairing code (`POST /api/vessel-auth/pairing-codes`).
   - A new app screen, "Enter the code from MDRRMO", calls the existing `enrollVesselDevice`.
   - A successful enrolment is the *only* thing that makes a vessel `phone_verified`.
     Responder confirmation (`POST /api/vessels/{id}/confirm`, operator, audited) is the only thing that makes it `confirmed_by_responder`.
   - `license_type` text never produces a badge.
2. **Badges.**
   - Show a positive "Verified by MDRRMO" badge only.
   - Unverified vessels get neutral grey text ("not yet verified"), never a yellow or red badge.
   - Card colour, sort order and alarm never depend on trust tier.
   - This is a UI/UX rule for Doreen Kay, stated in `docs/47_VISUAL_DESIGN_GUIDE.md`.
3. **Credential lifetime.**
   Today a device token lasts 24 h and refreshing it needs a valid token, so a phone offline for more than a day loses its credential for good.
   - `POST /api/vessel-auth/refresh` accepts tokens up to 30 days past expiry, provided the device row is not revoked; the device table is the real control.
   - The app refreshes on every start with internet.
4. **Reinstall (M2).**
   Android Auto Backup is enabled with `fullBackupContent` rules that include *only* the identity preferences (vessel ID and profile).
   The outbox database and credentials are excluded, and secure storage is keystore-bound anyway.
   After a restore, the app re-enrols; an operator can reset a device if the old one is lost.
   The SEC-32 signing switch is moot if release signing ships before any field rollout, which it will: there are no field users yet.
5. **Boat, not phone, as identity (M3), roadmap with D12.**
   When pods are provisioned with a vessel ID, the phone pairs with its boat's pod (D11.3) and takes the vessel ID from it.
   Until then, D2.8 groups same-vessel calls.
6. **Shore contact (M6).**
   Optional `shore_contact_name` and `shore_contact_phone` profile fields, stored on the vessel and shown in the incident drawer.
7. **SOS without a profile (M13).**
   - The vessel ID is generated on first launch, before any setup, and `raiseSos` needs only that.
   - A missing boat name is sent as an empty string, and the backend already falls back to the vessel ID.
   - The dashboard shows "Unregistered boat".
   - The SOS button also appears on the home page, not just the map page.

**Where the policy lives.**
Tier assignment is a pure function of enrolment and confirmation facts in `app/incidents/trust.py`.
The badge rule is in the design guide and the dashboard renderer.

**Contracts.**
- `docs/05`: the confirm route, refresh grace, shore contact fields, and the badge rule.
- `docs/22`: new strings.

**Addresses.**
Closes H10, M6 and M13.
Mitigates H21 (with D7.3), M2 and M3.

**Skipped.**
Automated FishR lookup: there is no API, and in-person checking is the MDRRMO's real process.
Multi-device vessels beyond what `vessel_devices` already allows.

**Check left behind.**
- A backend test: a profile with `license_type = "fishr"` and no enrolment stays `self_declared`.
- A refresh test with a token 3 days past expiry: accepted if the device is not revoked, 401 if it is.

---

### D9 - Hosting and gateway resilience

**Problem (R9).**
- The free database expires (C5).
- The free web service sleeps (M14).
- Nothing is scheduled (H6).
- One gateway sits on one mast, one power feed and one ISP (H12).

**Design.**

1. **C5 - do this week.**
   - Confirm the expiry date on the Render dashboard.
   - Upgrade `aqone-db` to a paid instance in place, or migrate it with `pg_dump`/`pg_restore`, **before 2026-10-08** (a one-week margin).
   - Turn on the plan's daily backups.
   - Update `render.yaml`, remove the "free plan" comment, and record the change in `docs/08`.
2. **M14.**
   Move the web service to a paid instance that does not sleep.
   While the gateway is online its 20 s chat poll keeps the service awake anyway, but the dangerous case is exactly the one where the gateway is down.
3. **Scheduler (H6, C6).**
   - An in-process periodic runner in the FastAPI lifespan (`app/scheduler.py`) runs:
     - the escalation watchdog every 30 s
     - anomaly evaluation every 5 min
     - mesh chat retention daily
   - Each job takes `pg_try_advisory_lock(job_id)`, so a second instance cannot double-run it.
     That is one line and correct from day one.
   - This needs a service that does not sleep, so it depends on D9.2.
4. **Gateway redundancy (H12).**
   - Short term: D5.9 (dual-core, so the radio is never deaf) and a UPS for the primary shore board.
   - Roadmap: a second gateway at a different site, with solar and battery power and LTE backhaul.
     Backend dedupe on `(vessel_id, nonce)` already makes double delivery harmless, and pods take the first valid ACK.

**Addresses.**
Closes C5 and M14.
Closes the scheduling part of H6.
Mitigates H12.

**Skipped.**
Multi-region hosting and managed queues.
One always-on instance plus a watchdog that reaches people directly is enough at this scale.

**Check left behind.**
A scheduler test in which two runners contend for the lock and only one executes.

---

### D10 - Honest anomaly detection

All of this is in `app/ai/` and remains advisory.

**Problem (R10).**
- There is no live input and the dashboard reads "No active vessel risk rows", which looks like calm (H6).
- Phone-based contacts confuse "phone missing" with "boat missing" (H7).
- New and solo fishermen are under-flagged (H8).
- Silent boats age out (H9).
- A "safe" check-in mutes the whole trip (H16).
- Midnight departure hours average to noon (L2).
- Distance is measured from the town centre (L3).
- Drift trusts a wrong phone clock (M17).

**Design.**

1. **Monitoring status (H6).**
   The anomaly endpoint returns `monitoring: "unavailable"` with a reason when no contact event arrived in the last 30 min.
   The dashboard renders "Not monitoring - no live contact source", the same honest pattern squall nowcasting already uses.
2. **Input source (H6, H7).**
   - The gateway posts a contact event (`/api/v1/contacts`) for every pod frame it hears (T_PING, T_STATUS, T_SOS).
   - **Superseded for the pod heartbeat (2026-09-26):** `docs/68_WEATHER_TIERED_CHECKINS_SPEC.md` makes the pod's periodic `STATUS` check-in the heartbeat, received by a dedicated check-in receiver and posted in batches (`docs/69` Phase 4). The gateway does not post a contact per frame.
   - Once pods are provisioned with a vessel ID (D12), the pod is the boat's heartbeat.
   - Phone-only contacts are tagged `source=handset`.
     They can support a pod-based finding but never raise "overdue" on their own.
   - Detecting a person overboard while the phone stays aboard needs a worn tag and is roadmap.
3. **Priors (H8).**
   - Remove the `0.9` damping for new profiles (`trip_profile.py:621`); new vessels use the fleet prior at full weight.
   - A trip with no contacts and no declared return becomes `check_needed` after the fleet's 90th-percentile trip length, instead of staying `normal` forever.
4. **Silence ages up, not out (H9).**
   Every vessel whose last contact was at sea within 72 h is evaluated, whether or not a trip record exists.
   This replaces the 12 h freshness fallback.
5. **Welfare decay (H16).**
   A `safe` check-in caps the overdue factor for 2 h after the check-in, not for the rest of the trip.
6. **Circular hours (L2).**
   The typical departure hour becomes a circular mean (`atan2` of mean sine and cosine), using only the standard library.
7. **Home landing (L3).**
   Distance is measured from the vessel's median first-contact position over completed trips, falling back to the municipal centre.
8. **Drift clock (M17).**
   Drift starts at `client_ts` only when it lies within `[created_at - 24 h, created_at + 5 min]`.
   Otherwise it uses `created_at` and sets `clock_suspect`, which the drift panel shows.

**Addresses.**
- Closes H8, H9, H16, L2, L3 and M17.
- Closes the honesty part of H6; the input part lands with D12.
- Mitigates H7.

**Skipped.**
A solo or group model: this needs crew-count data we do not collect, and it is revisited when trip records exist.

**Check left behind.**
One eval-style test per change in `backend/tests/test_trip_profile.py`: 23:30 and 00:30 average to about 00:00, a safe check-in 3 h earlier no longer caps, a new profile is not damped.

---

### D11 - The handset at sea

**Problem (R11).**
- Panic SOS calls often carry no GPS fix, and none is sent later (H1).
- The pod's WiFi fights the phone's internet (H3).
- There is no silent SOS (H22).
- The alarm uses the media stream (L4).
- Wet screens fight the cancel slide (L5).
- Some SOS-flow strings are English only (L1).

**Design.**

1. **GPS (H1).**
   - The location stream starts when the venture or map page opens and when a trip starts, so the fix is warm before any SOS.
   - The SOS goes out immediately with whatever fix exists.
   - If a fix arrives within 5 min, the phone re-sends the same SOS (same nonce) carrying the position.
     The backend's COALESCE and the pod's fill-if-empty (D2.6) record it.
   - A continuing position track (`sos_positions`) is roadmap.
2. **Background:** see D1.4.
3. **Pod WiFi without breaking the phone (H3, C12, M7), device-test-gated.**
   - The fisher pairs once with their boat's pod via Android `CompanionDeviceManager`, scanning the QR code on the pod (SSID, per-pod WPA2 passphrase, pod ID).
   - After that, the app reaches the pod through `WifiNetworkSpecifier` and `ConnectivityManager.requestNetwork`, binding only the app's pod sockets to that network.
     The pod never becomes the phone's default network, and cellular data keeps working for everything else.
     Companion association makes later connections silent.
   - The pod stops answering all DNS queries as itself and stops claiming internet.
   - The per-pod passphrase ends both SOS hitchhiking on a neighbour's pod (M7) and look-alike pods (C12).
   - Android 9 and older fall back to today's behaviour.
   - This needs about 60 lines of Kotlin behind a platform channel; there is no plugin.
   - Amended: plan 66 D3 (2026-09-25) dropped the per-pod passphrase and QR pairing, and docs/64 Section 2.5 (plan 65 Phase 5) joins the open pod network from inside the app, binding the whole app process while connected, a recorded ceiling compared with binding only the pod sockets.
4. **Silent SOS (H22).**
   - A settings toggle, "Silent SOS", and a gesture (hold the SOS button for 3 s) both send with no sound or vibration.
   - A duress cancel (a cancel gesture that looks normal but sends a `duress` flag) needs an MDRRMO procedure first, so it is roadmap.
   - Amended 2026-09-26 by `docs/64_FISHER_FRICTION_REDUCTION_SPEC.md` FFR-02 (plan 65 Phase 1, `7826488`): the 3 s hold was removed because a panicking fisher who presses hard got a silent SOS without knowing it; the settings toggle remains. A quick silent path for H22 is open decision D8 in docs/64.
5. **Alarm stream (L4).**
   `audioplayers` is configured with `AudioContext(android: AudioContextAndroid(usageType: AndroidUsageType.alarm, contentType: AndroidContentType.sonification))`.
6. **Wet hands (L5).**
   The countdown cancel becomes "hold 2 s to cancel", which ghost touches cannot trigger and which works through a pouch.
   This is a UI/UX call for Doreen Kay and needs a wet-screen test.
   Amended 2026-09-25 by docs/64 D3: plan 65 Phase 4 adds a large tap-to-cancel button beside the slide instead; the wet-screen test still applies.
7. **Localisation (L1).**
   Move `venture_page.dart:391`, `home_page.dart:448` and the rest of the literals the report found into `app_en.arb`, then `fil` and `akl` drafts.

**Addresses.**
- Closes L1 and L4.
- Mitigates H1 (fully closed only by pod GPS, D12), H3, H22 and L5.

**Check left behind.**
A widget test for the silent path (no alarm started).
Device tests for 3 and 5 recorded in `docs/08`.

---

### D12 - Hardware and field (Daniel)

1. **Pod button and GPS (C4).**
   - A recessed button needing a 3 s hold, so bumps do not trigger it, raises an SOS on the pod itself, using the pod's provisioned vessel ID and its own GPS fix.
   - It is queued and retried like any other SOS.
   - An LED pattern follows the delivery states:
     - `saved`: slow blink
     - `relayed`: fast blink
     - `delivered`: solid
     - `acknowledged`: double pulse
   - Pod GPS also fills a phone SOS that has no fix.
2. **Thermal safety (H23), before any sealed-pod test.**
   - The charger must have NTC temperature cutoff (JEITA-style), with no charging above 45 °C.
   - Use a pressure-equalising vent membrane and a light-coloured enclosure.
   - Bench test at 60 °C ambient.
   - This is a BOM check and has nothing to do with firmware.
3. **Field hazards (M5).**
   - Pods sit on boats, per docs/55, which reduces how many buoys are exposed.
   - Relay buoys get bird spikes, sacrificial anodes and conformal coating.
   - Each pod logs the RSSI of the shore beacon.
     If no beacon is heard for 30 min, the pod's LED shows "no shore" and the dashboard shows the pod as silent (D5.9).
4. **Band legality (M11), a phone call to make now.**
   - Ask the NTC which band applies.
     The Philippines is generally listed under AS923 (923 MHz); confirm this.
   - The band is one constant in `AqOneLoam.h`.
   - Buy only 863-928 MHz board variants.
5. **Brownout (M16), bench test.**
   - Read battery voltage before TX, and delay queued TX until it is above threshold.
   - Persist a brownout-reset counter; after 2 consecutive brownouts, transmit at reduced power.
   - Add a bulk capacitor near the radio.

**Addresses.**
Closes C4 and H23.
Mitigates M5, M11 and M16.

---

## 8. Traceability matrix (all 68)

Phase key:
- **P0**: now, date-driven or a phone call.
- **P1**: software only, no radio needed.
- **P2**: firmware, bench-testable, gated on build step 2.
- **P3**: field or device test.
- **P4**: roadmap, needs a decision.
- **Done**: already fixed on `0bad918`.

| ID | Design | Phase | Owner | Outcome |
| --- | --- | --- | --- | --- |
| C1 | D5.5 | P2 | Daniel | Closes |
| C2 | D5.1, D5.3 | P1 backend, P2 firmware | Lenard, Daniel | Closes |
| C3 | D1 | P1 | Jade | Closes |
| C4 | D12.1 | P4 | Daniel | Closes |
| C5 | D9.1 | **P0** | Lenard | Closes |
| C6 | D4.1 to D4.4 | P1 | Arnold, Lenard | Closes |
| C7 | D3.1 to D3.3, D4 | P1 | Arnold, Lenard | Closes |
| C8 | D6 | P1 phone and backend, P2 firmware | Jade, Lenard, Daniel | Closes |
| C9 | D7.1 | P1 | Lenard | Closes |
| C10 | D5.1, D5.2 | P1 backend, P2 gateway | Lenard, Arnold | Closes |
| C11 | D7.5 | P4 | Daniel, Lenard | Mitigates once approved; open until then |
| C12 | D1, D11.3 | P1, P4 | Jade | Mitigates (residual: fake pod plus no internet) |
| C13 | SEC-28 | Done | Arnold | Closes (hardware verification pending) |
| C14 | D2 | P1 backend and phone, P2 firmware | Lenard, Jade, Daniel | Closes (residual race is flagged) |
| H1 | D11.1, D2.6, D12.1 | P1, P2, P4 | Jade, Daniel | Mitigates |
| H2 | D1.4 | P1 | Jade | Closes (measure per OEM) |
| H3 | D11.3 | P3 | Jade, Daniel | Mitigates |
| H4 | D3.5 | P1 | Arnold | Closes |
| H5 | D2.6 | P2 | Daniel | Closes |
| H6 | D10.1, D10.2, D9.3 | P1 honesty and schedule, P4 input | Lenard | Closes honesty; input with D12 |
| H7 | D10.2 | P4 | Lenard, Daniel | Mitigates |
| H8 | D10.3 | P1 | Lenard | Closes |
| H9 | D10.4 | P1 | Lenard | Closes |
| H10 | D8.1, D8.2 | P1 | Lenard, Arnold, Jade, Doreen | Closes |
| H11 | D5.6 | P3 | Daniel | Mitigates |
| H12 | D5.9, D9.4 | P2, P4 | Arnold, Daniel | Mitigates |
| H13 | Phase 5 X-Api-Key | Done | Arnold | Closes (hardware verification pending) |
| H14 | D5.4 | P2 | Arnold | Closes |
| H15 | D1.5 | P1 | Jade, Arnold | Closes |
| H16 | D10.5 | P1 | Lenard | Closes |
| H17 | D2.5 | P1 phone, P2 firmware | Jade, Daniel | Closes |
| H18 | D4.6 | P1 | Lenard, Arnold | Mitigates |
| H19 | D5.8 | P2 | Daniel, Arnold | Mitigates |
| H20 | D7.2 | P1 | Lenard, Arnold | Mitigates (advisory flags) |
| H21 | D7.3, D8.1 | P1 | Lenard | Mitigates |
| H22 | D11.4 | P1 silent, P4 duress | Jade, Doreen | Mitigates |
| H23 | D12.2 | P2 (before any sealed test) | Daniel | Closes |
| M1 | D3.6 | P1 | Lenard, Arnold | Closes |
| M2 | D8.4 | P1 | Jade | Mitigates |
| M3 | D2.8, D8.5 | P1, P4 | Arnold, Jade | Mitigates |
| M4 | D5.7 | P2 | Arnold | Closes |
| M5 | D12.3 | P3 | Daniel | Mitigates |
| M6 | D8.6 | P1 | Lenard, Jade | Closes |
| M7 | D1, D11.3 | P1, P3 | Jade | Mitigates |
| M8 | D3.4 | P1 | Lenard, Arnold | Closes |
| M9 | D3.3, D3.7 | P1 | Lenard, Jade | Closes |
| M10 | D3.1 | P1 | Lenard | Closes |
| M11 | D12.4 | **P0** (NTC inquiry) | Daniel | Mitigates |
| M12 | D7.1 | P1 | Lenard | Closes |
| M13 | D8.7 | P1 | Jade | Closes |
| M14 | D9.2 | **P0** | Lenard | Closes |
| M15 | D5.7 | P2 | Daniel | Closes |
| M16 | D12.5 | P2 | Daniel | Mitigates |
| M17 | D10.8 | P1 | Lenard | Closes |
| M18 | SEC-12, D4.5 | Done, P1 | Lenard | Mitigates (7-day idle ceiling accepted) |
| L1 | D11.7 | P1 | Jade | Closes |
| L2 | D10.6 | P1 | Lenard | Closes |
| L3 | D10.7 | P1 | Lenard | Closes |
| L4 | D11.5 | P1 | Jade | Closes |
| L5 | D11.6 | P3 | Jade, Doreen | Mitigates |
| L6 | D5.7 | P2 | Daniel | Closes |
| L7 | D6 | P2 | Daniel | Closes |
| L8 | D2.7 | P1 | Lenard | Closes |
| L9 | D4.7 | P1 | Arnold | Closes |
| L10 | D5.10, D1 | P2 | Daniel | Mitigates |
| L11 | D4.7 | P1 | Arnold | Closes |
| L12 | - | - | - | **Accepts** (2106) |
| L13 | D2 | P1 | Lenard | Closes |
| N1 | D5.7 | P2 bench test | Arnold | Test first; D5.7 closes it either way |

Totals:

| Outcome | Count |
| --- | --- |
| Closes | 46, including C13 and H13 already fixed |
| Mitigates | 21 |
| Accepts | 1 (L12) |

C11 is counted as Mitigates, but it only becomes so once Len approves D7.5 (decision 3).

---

## 9. Phasing and gates

The phasing follows the CLAUDE.md build order: nothing on the radio is fixed before build step 2 proves two boards talk.

**P0 - This week (date-driven, no dependencies).**
- D9.1 database off the free plan before 2026-10-08.
- D9.2 web service to a tier that does not sleep.
- D12.4 NTC band inquiry.
- Gate: `/health/ready` green on the paid database, and `docs/08` entry written.

**P1 - Software only (backend, dashboard, phone).**
Can run in parallel with the security plan's Phase 6 and with teammates' features.
Per the standing agreement, it starts only once Len says in-flight features have landed.
Order within P1, most leverage first:
1. D1 delivery policy and foreground service (C3, H2, H15).
2. D3 and D4 dispatcher safety (C6, C7, H4, M8, M9, M10, M1, L9, L11).
3. D7.1 chat authentication (C9, M12).
4. D2 nonce: backend and phone halves, legacy branch kept (C14, H17, L8, L13).
5. D5.1 downlink cap (C10 and C2 backend half).
6. D6 phone and backend halves (C8).
7. D8 enrolment screen, badges, refresh grace, backup, M6, M13.
8. D9.3 scheduler and the D4.4 escalation watchdog, once P0 has landed.
9. D10 anomaly honesty and priors.
10. D11.1, D11.4, D11.5 and D11.7.

Gate: backend `pytest` and `ruff`, `flutter analyze` and `test`, and the web `node --test` suite all green.
Every finding in P1 has a red test written first that reproduces it (Section 14).

**P2 - Firmware on the bench (gated on build step 2 passing).**
- D5.2 to D5.5 and D5.7 to D5.10
- D6 in firmware
- D2 nonce in frames and the pod fill-if-empty
- D12.2 thermal BOM, D12.5 brownout
- N1 bench test

Gate: both sketches compile with no warnings, `AqOneLoam.h` copies byte-identical, and the two-board bench script passes (Section 14).

**P3 - Field and device (gated on build step 6, the range test).**
- D5.6 relay discipline, measured
- D11.3 pod WiFi binding on target Android versions
- D11.6 wet-screen test
- D12.3 field hazards

**P4 - Roadmap (each needs a decision in Section 12).**
- D7.5 per-node keys and signed broadcasts
- D12.1 pod button and GPS
- D8.5 pod-as-identity
- D10.2 pod contact input
- D9.4 second gateway
- D11.4 duress cancel

---

## 10. Contract changes (docs first, then code)

Each change below is made in its contract doc and announced to the affected owners before any code (CLAUDE.md, "Shared contracts").

| Doc | Change | Tell |
| --- | --- | --- |
| `docs/02_LOAM_PACKET_SPEC.md` | `nc` in SOS and ETA payloads; node ID from eFuse MAC; random mesh-seq start; UTF-8 rule; clock adoption from shore types only; 10 min replay window; relay CAD and suppression; pods relay only SOS and ACK; WARN rebroadcast every 10 min; later, per-node keys and broadcast signatures | Daniel, Arnold |
| `docs/03_PHONE_BUOY_WIFI.md` | Handoff `nonce`; duplicate handoff fills empty fields; per-client queue cap of 2; status returns `nonce`; `accepted` means queued, not delivered; later, pairing QR and per-pod passphrase | Daniel, Jade |
| `docs/04_INGEST_API.md` | `SosIn.nonce` and its merge key; truncation, not rejection, for text; `position_conflict`; downlink cap of 12, selection and order; gateway last-seen; gateway chat origin | Arnold, Lenard |
| `docs/05_PUBLIC_API.md` | Resolve `reason_code`; `/reopen`; `expected_version` and 409; `responder_note` of 40 bytes or less; `/active` `limit`, `total` and triage order; plausibility flags; chat authentication and reserved names; vessel confirm; token refresh; device refresh grace; shore contact; anomaly `monitoring` status; late-SOS rule | Arnold, Jade |
| `docs/06_DELIVERY_STATES.md` | `relayed` is not terminal; an incident can leave `resolved` | everyone |
| `docs/13_RESPONDER_LOOP.md` | Resolution reasons and the boat message per reason | Arnold, Doreen |
| `docs/22_LOCALIZATION_PLAN.md` | New strings: not-confirmed, late prompt, no-ETA, reopened, silent SOS, enrolment, closed-unconfirmed | Jade, Doreen |
| `docs/47_VISUAL_DESIGN_GUIDE.md` | Badge rule (positive only; never colour or priority by tier); plausibility tag style | Doreen, Arnold |
| `docs/16_QA_DISCLOSURES.md` | Accepted risks from Section 13 | everyone |

---

## 11. Module placement (Clean Architecture)

```text
backend/app/
  incidents/            NEW - pure policy: no fastapi, asyncpg, httpx imports
    lifecycle.py        states, transitions, ResolutionReason, boat_message, reopen window     (D3)
    delivery.py         delivery_state() moved here from sos.py                               (D3)
    downlink.py         DOWNLINK_MAX, selection rule, priority key                              (D5)
    triage.py           /active priority key, flood detection                                   (D4)
    escalation.py       due_for_escalation()                                                    (D4)
    plausibility.py     flags()                                                                 (D7)
    merge.py            position-conflict rule                                                  (D2)
    trust.py            tier from enrolment/confirmation facts                                  (D8)
  api/sos.py            adapter: parse -> policy -> SQL -> audit (gets shorter, not longer)
  api/mesh.py           adapter: credential extraction + chat policy
  scheduler.py          NEW - lifespan periodic runner with pg advisory locks                   (D9)
  notify.py             NEW - notify_oncall(text), one implementation, no interface             (D4)
  ai/                   anomaly/trip/drift changes stay here, advisory                          (D10)

mobile/lib/
  models/delivery_policy.dart   NEW - pure routesDue(record, now)                               (D1)
  services/sos_service.dart     adapter: runs the routes the policy returns
  services/pod_link.dart        NEW - platform channel to CompanionDeviceManager/WifiNetworkSpecifier (D11, P3)

firmware/
  AqOneLoam.h (both copies, byte-identical)
    utf8Copy(), eviction comparators, clock adoption rule, replay window, relay backoff        (D5, D6)
  test/utf8_copy_test.c         NEW - host-compiled assert test                                 (D6)

web/js/dashboard/
  dashboard-incidents.js        resolve dialog with reason + undo, ack dialog ETA buttons, 409 handling
  dashboard-alarm.js            first-load sync, audio-unlock banner, Notification API
  dashboard-live-sos.js         triage paging, late badge, plausibility tags, hemisphere formatting
```

**Enforcing the boundary.**
One test, `backend/tests/test_incidents_is_pure.py`, imports every module in `app/incidents/` and fails if `fastapi`, `asyncpg`, `httpx` or `app.db` appear among their imports.
There is no new tooling, just one small test.

**What we deliberately do not add.**
- Repository interfaces.
- A notifier interface (until a second channel exists).
- A domain-events bus.
- Moving SQL out of the adapters.

A second implementation or a measured pain point is what should trigger each of these.

---

## 12. Decisions needed from Len

| # | Decision | Recommendation | Deadline |
| --- | --- | --- | --- |
| 1 | Hosting spend: paid Postgres and a web tier that does not sleep | Yes; confirm current Render pricing and whether the free database can be upgraded in place | **2026-10-08** |
| 2 | Escalation channel and on-call roster for D4.4 | SMS through a Philippine SMS provider to the MDRRMO duty phone, with email as a second channel; the roster must come from MDRRMO | Before P1 item 8 |
| 3 | Reopen the docs/59 deferral: per-node keys and signed broadcasts (D7.5), adding `cryptography` to the backend | Approve the design now and build after step 3; update the frame spec once, together with D2's `nc` | After build step 3 |
| 4 | Foreground service: plugin (`flutter_foreground_task`) or a hand-written Kotlin service | The plugin; a hand-written service plus an isolate bridge is more code to own | Before P1 item 1 |
| 5 | Pod pairing and pod-as-vessel-identity (D11.3, D8.5) | Yes, as the long-term identity model; needs Daniel and Jade together | P3 planning |
| 6 | Resolution reason vocabulary and boat messages (D3.1) | Draft in Section 7, D3; validate with MDRRMO | Before P1 item 2 |
| 7 | LoRa band (M11) | NTC inquiry now; plan for AS923 | P0 |
| 8 | Duress cancel (D11.4) | Only with a written MDRRMO procedure; otherwise ship the silent SOS alone | P4 |

---

## 13. Accepted risks (to record in `docs/16_QA_DISCLOSURES.md`)

- **L12** - firmware timestamps wrap in 2106.
  Not worth a frame-format change.
- **C12 residual** - a fake pod combined with no internet for the entire emergency still captures the SOS until pod pairing (D11.3) ships.
- **C14 residual** - a holder of the shared radio key who races the gateway can attach a second position.
  It is flagged (`position_conflict`), not silent.
- **C11** - until D7.5 is approved and built, anyone holding the shared radio key (including from a stolen pod's flash) can forge ACKs, ETAs and warnings.
- **M18 residual** - an idle operator session lasts up to 7 days.
  It is revocable (SEC-12) and refreshed while active.
- **H7 residual** - a person overboard while the phone and pod stay aboard is not detected.
  This needs a worn tag, which is roadmap.
- **H20 residual** - plausibility flags are advisory.
  A determined decoy with a plausible position still pulls a rescue boat, and that is a dispatch judgement, not a software one.

---

## 14. Verification strategy

Following CLAUDE.md: reproduce every bug end to end, as close to real use as possible, before fixing it.

**P1 (software).**
For each finding, write the failing test first; per the standing workflow, Claude writes the spec and the red tests.
It must reproduce the finding through the real entry point:
- the API route with a disposable Postgres for backend findings (the existing `security_probes` pattern)
- `SosService` with fake transports for phone findings
- `node --test` with a DOM stub for dashboard findings

The test must fail on today's code and pass after the fix.
Then run the full gates in CLAUDE.md.
Dashboard changes also get a manual look at the real page, since pixel issues count.

**P2 (bench).**
One scripted two-board session, recorded in `docs/08`:
1. Flash two default builds; expect two distinct node IDs, and two SOS calls give two backend rows (C1).
2. Send an SOS whose note has `ñ` at byte 64, then a dispatcher note with `ñ` at byte 40; the phone shows both (C8, L7).
3. Create 20 open incidents; the gateway sends 12 or fewer ETA frames, at most 4 per poll, and nothing repeats after they settle (C10, C2).
4. Boot the shore with the router off, then start the router after 30 s; the clock syncs and HTTPS works (M4, N1).
5. Power the pod from a weak supply with an SOS queued; the frame completes, or TX power steps down (M16).
6. Hand off twice (first with no note, then with one); the backend row has the note (H5).
7. Reboot a pod mid-trip; it gets the active warning within 10 min (H14).

**P3 (field and device).**
- Record relay collision counts with 5 or more pods clustered (H11).
- Test pod WiFi binding on Android 10 to 14 on the team's actual phones, with mobile data on (H3).
- Measure how long the foreground service survives on the cheapest target phone with the screen off for 30 min (H2).
- Run the wet-screen cancel test (L5).

**Definition of done for this design.**
Every row in Section 8 is either closed with a test or bench record that is linked from `docs/08`, or recorded as accepted in `docs/16`.

---

## 15. Next step

This is a design, not an implementation plan.
Once Len approves it and confirms that teammates' in-flight features have landed, it becomes an implementation plan through the `implementation-plan` skill.
The findings get re-verified against the code at that moment, P0 runs first, and P1 is split into reviewable phases with red tests written first.
P0 (C5) should not wait for that approval cycle.
