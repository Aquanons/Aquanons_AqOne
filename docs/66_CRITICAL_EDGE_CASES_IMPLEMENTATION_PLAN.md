# Implementation Plan: Close the 14 Critical edge cases

**Status:** APPROVED - Revision 2, except Phase 6 (redesigned after D3, needs Len's look before it starts); Phase 1 next
**Owner:** Lenard (plan, review, ops), Daniel (bench, hardware), Jade (mobile, Phase 6)
**Created:** 2026-09-25T17:50:00+08:00
**Updated:** 2026-09-25T18:05:00+08:00
**Related:** `docs/60_EXTREME_EDGE_CASE_REPORT.md` (findings C1-C14), `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md` (design D1-D12), `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` and tracks `62A` to `62D`

Revision: 2
**Execution mode:** hard-stop
Feature spec and revision: `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md` (the approved design for docs/60), Critical rows C1-C14 only
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`, docs/61 Section 4.3 and Section 11 (Clean Architecture placement)
Len's chat decisions, 2026-09-25T18:03:00+08:00, on Revision 1: D1 second byte-identical header; D2 yes, handed to Gemini; D3 no pod password, reduce friction; D4 yes; D6 yes, `TinyGPSPlus`; D7 deal with the database when it expires, not a top concern (RSTW is 2026-10-01 to 03, Enactus 2026-10-09 to 10). D5 not answered yet.
Revision 2 records those answers, drops the database rotation from Phase 1, and replaces Phase 6's pod password with a check the fisher never sees.
Len's chat approval: Revision 2 Phases 1-5 and 7 treated as approved by the decisions above; Phase 6 needs explicit approval.
Target branch: `edge/critical` from `master`, one commit per phase; Len may push verified phases straight to `master`
Implementer: the agent named in the root `HANDOFF.md`; reviewer: Claude Code; every bench and field step: Daniel; every flash and Render step: Len.

Execution mode is `hard-stop` by the default rule: the plan changes firmware, shared contracts (`docs/02`, `docs/03`), backend code and deployment, and has more than 3 phases.

## Why this plan exists

PR #79 (`9630553`) fixed every Critical finding that software above the radio could fix.
What is left is spread across three plans (`62` Phase I, `62D` F0/F1/F4/F5, `62B` M7) and mixed with non-Critical rows.
This plan pulls out only the Critical work, orders it by the build-order gates, and adds the one architectural piece the firmware track is missing: a hardware-free policy boundary that host tests can reach.

On approval, this plan supersedes, for the Critical rows only:
- `docs/62` Phase I walkthrough steps C3, C6, C7 and C9;
- `docs/62D` F0 and F1 for C1, C2, C8, C10 and C14, all of F4 (C11), and F5 item C4;
- `docs/62B` M7 for the C12 cause.

The non-Critical rows of `62D` F1 (H5, H14, H17, H19, L6, L10, M4, M15, N1) stay in `62D` and run after Phase 4 here, on top of the policy header Phase 3 creates.
`docs/65` (fisher friction) runs after this plan's Phase 5 (Len, 2026-09-25T18:00:00+08:00).
With D3 the pod stays an open network, so Phase 6 here no longer touches `docs/65` Phase 5's Wi-Fi channel.

## Where each Critical stands today (2026-09-25)

| ID | Finding | Done so far | Left | Phase | Outcome |
| --- | --- | --- | --- | --- | --- |
| C1 | Every pod is `BUOY01` | Nothing | eFuse-derived node ID and name, random seq start | 4 | Closes |
| C2 | Pod remembers 8 acks | Backend caps and orders the downlink (B3) | Pod table: 12 slots, evict resolved then least recent, age out | 4 | Closes |
| C3 | Phone stops at `relayed` | Retry policy fixed (M1) | Emulator check against a pod stub that never delivers | 1 | Closes (verified) |
| C4 | No pod button or GPS | Nothing | Contract, button, GPS, LED states | 7 | Closes |
| C5 | Free database expires | Runbook, rehearsal, `db_days_left` (0a, B6) | Deferred by Len (D7): rotate or upgrade when it expires, around 2026-10-15, after both events | - | Mitigated by the ready runbook; recurs every 30 days until a paid plan |
| C6 | Waiting SOS never rings | First-load alarm (W1), SMS watchdog (B6) | Browser check; SMS configured or recorded as not | 1 | Closes (verified) |
| C7 | One-click resolve | Reason, confirm, undo, reopen (B1, W2) | Browser check | 1 | Closes (verified) |
| C8 | Split UTF-8 | Backend (B2) and phone (M3) | Pod and shore still `strncpy` | 4 | Closes |
| C9 | Anyone posts "MDRRMO" | Backend refuses reserved names (B5); shore code sends `X-Api-Key` | Shore not reflashed, so chat to boats is down | 1 | Closes (verified) |
| C10 | Gateway jams past 12 | Backend caps the feed (B3) | Shore watch set evicts slot 0 and rebroadcasts; no per-poll limit | 4 | Closes |
| C11 | Shared radio key | Key out of the repo (SEC-27) | Per-node keys, backend-signed broadcasts | 5 | Mitigates: a stolen pod forges only its own ACKs |
| C12 | Fake "Aquan" pod | Consequence gone (M1: `relayed` is not final) | The phone checks a signed proof in the pod's "accepted" reply; no password, nothing for the fisher to do | 6 | Closes; residual is a stolen real pod's key, until it is revoked |
| C13 | MITM on gateway WiFi | Verified TLS in code (SEC-28) | Hardware check on the reflashed shore | 1 | Closes (verified) |
| C14 | Pre-made rows capture SOS | Closed on the direct path (B2 nonce + M3) | Mesh path has no `nc`, so it still uses the guessable legacy key | 4 | Closes; legacy branch removal is decision D4 |

Five of the fourteen (C3, C6, C7, C9, C13) need evidence and operations, not code; C5 is deferred by Len.
Seven (C1, C2, C4, C8, C10, C11, C14) need firmware.
One (C12) needs firmware and mobile together.

## Clean Architecture applied

The backend and mobile already follow docs/61 Section 4.3: pure policy in `backend/app/incidents/` and `mobile/lib/models/`, humble adapters around it, and `tests/test_incidents_is_pure.py` enforcing the direction.
The firmware does not, and every remaining firmware Critical is a policy decision buried in a radio or WiFi handler:

| Critical | Policy decision | Buried in today |
| --- | --- | --- |
| C1, C11 | Does this ACK delete this queued SOS? | `onMeshFrame` T_ACK case, `AqOneBuoy.ino:867-889` |
| C2 | Which tracked vessel is evicted? | `trackVessel()`, `AqOneBuoy.ino:313-325` (returns null when full) |
| C8 | How much of this text fits? | `strncpy` at 18 sites across both sketches |
| C10 | Which watched vessel is evicted, how many T_ETA per poll, when to write flash? | `watchVessel()`, `AqOneShore.ino:393-410` (always slot 0), poll loop |
| C4, C14 | Is this handoff or button press a new SOS, a duplicate, or a fill? | `/v1/sos` handler, `AqOneBuoy.ino:489-530` |

`AqOneLoam.h` cannot be the home for that policy, because it includes `Arduino.h`, `RadioLib.h`, `Preferences.h` and mbedTLS, so no host compiler can include it.
`docs/62D` planned a host-compiled `utf8_copy_test.c` against a function in that header; as written, that test cannot compile.

### Module placement

```text
firmware/
  buoy/AqOneBuoy/AqOnePolicy.h     NEW, byte-identical copy in shore/AqOneShore/
                                   includes only <stdint.h> <stddef.h> <string.h> <stdbool.h>
                                   plain structs and free functions; time is a parameter, never read
    utf8Copy()                     C8
    nodeIdFromMac(), nodeNameFromId()                          C1
    ackMatchesQueued()             C1, C11 (node tag result passed in as a bool)
    trackEvictionVictim(), trackExpired()                      C2
    watchEvictionVictim(), downlinkDue(), persistDue()         C10
    handoffDecision()              C4, C14: new | duplicate-fill | queue-full
    acceptanceMessage()            C12: the exact bytes a pod signs for the phone
    holdTriggered()                C4
  buoy/AqOneBuoy/AqOneLoam.h       adapter: radio, frame codec, HMAC, NVS; includes AqOnePolicy.h
  *.ino                            adapters: parse JSON/GPIO/NMEA -> call policy -> radio, flash, HTTP
  test/policy_test.cpp             NEW, assert-based host test, no framework

backend/app/
  incidents/downlink.py            pure: canonical broadcast bytes (C11)
  radio_signing.py                 NEW adapter: Ed25519 via `cryptography`, key from env at startup;
                                   signs broadcasts (C11) and pod certificates (C12)
  api/sos.py, api/advisories.py    adapters: add `sig` to what the gateway reads
  api/pods.py                      NEW adapter: operator-only pod certification (C12)

mobile/lib/
  models/pod_attestation.dart      NEW pure: challenge bytes, and "is this acceptance proven?" using the
                                   pure-Dart Ed25519 in the already-installed `cryptography` package (C12)
  services/buoy_client.dart        adapter: sends the challenge, hands the reply to pod_attestation (C12)
```

**One signature algorithm everywhere: Ed25519.**
The phone must verify pod proofs, and the installed Dart `cryptography` 2.9.0 implements Ed25519 in pure Dart but throws `UnimplementedError` for ECDSA outside the browser.
So Revision 2 moves docs/61 D7.5's broadcast signatures from ECDSA P-256 to Ed25519 as well: one key type on the backend, one verify routine on the pod, and the same 64-byte signature size.

### How the boundary is enforced

- `backend/tests/test_security_regressions.py` already asserts the two `AqOneLoam.h` copies are byte-identical; Phase 3 extends the same test to `AqOnePolicy.h`.
- A new assertion in that test fails if `AqOnePolicy.h` includes anything outside the four allowed headers, or contains `millis(`, `time(`, `Serial`, `ESP.`, `WiFi`, `radio.` or `prefs.`.
- `firmware/test/policy_test.cpp` compiles with `-Wall -Wextra -Werror` and runs on the host; it is the red test for every firmware Critical.
- `tests/test_incidents_is_pure.py` keeps `cryptography` and `os.environ` out of `app/incidents/`.

### What we deliberately do not add

- No hardware abstraction layer, virtual classes or function-pointer ports for the radio, WiFi, GPS or flash: each has exactly one implementation, so the `.ino` adapter calls it directly.
- No repository or signer interface on the backend: `radio_signing.py` is the only signer.
- No unit test framework (Unity, GoogleTest): `assert` in one `.cpp` file is enough.
- No behaviour moves in Phase 3 except what later phases change; the rest of the sketches stay as they are.

A second implementation or a measured pain point is what should trigger any of these.

## Decisions

| # | Decision | Len's answer (2026-09-25) | Applies to |
| --- | --- | --- | --- |
| D1 | Home for firmware policy | A second byte-identical header, `AqOnePolicy.h`, guarded by the existing identity test. A PlatformIO `lib/` folder was rejected because it breaks the Arduino IDE setup in `firmware/README.md`. | Phase 3 |
| D2 | Toolchain on Len's machine | Yes: PlatformIO Core and a host `g++`, installed by Gemini from the root `HANDOFF.md`. | Phase 1 |
| D3 | Pod password (C12) | No password: reduce friction. The pod stays an open "Aquan" network; Phase 6 proves the pod's identity to the phone instead, with nothing for the fisher to do. | Phase 6 |
| D4 | Remove the legacy `(vessel_id, client_ts)` merge branch (C14 residual) | Yes. It runs at the end of Phase 4, after the bench shows mesh SOS carry `nc`; removing it earlier would reject every mesh SOS with 422 and leave pods retrying forever. | Phase 4 |
| D5 | Pod as vessel identity (docs/61 decision 5) | **Open.** Recommendation: a pod is provisioned with the vessel ID it belongs to at enrolment. | Phase 7 |
| D6 | GPS parsing on the pod | `TinyGPSPlus`, pinned, behind the `.ino` adapter. | Phase 7 |
| D7 | Free database expiry (C5) | Deal with it when it expires, around 2026-10-15; not a top concern. The rotation runbook and `db_days_left` are ready. | Outside this plan |

## Timing and gates

Len's events: RSTW 2026-10-01 to 03, Enactus 2026-10-09 to 10.
No merge that changes the demo firmware, APK or backend during either event (as `docs/64` D2 already says for the APK).

| Phase | Gate to start | Hard date |
| --- | --- | --- |
| 1 Evidence and operations | Approval (given) | Before RSTW if possible, so the demo has chat to the boats (C9) |
| 2 Build step 2 recorded | Daniel has two boards | None; gates every firmware phase |
| 3 Firmware policy boundary | Phase 2 | None |
| 4 Firmware Criticals C1, C2, C8, C10, C14 | Phase 3 | None |
| 5 Radio authenticity C11 | Phase 4 and build step 3 recorded in `docs/08` | None |
| 6 Pod proof C12 | Phase 5 (its signing key and provisioning tool), build step 4 recorded, Len approves Phase 6 | None |
| 7 Pod button and GPS C4 | Phase 4, D5, H23 thermal check passed | None |

`docs/65` Phase 1 starts after Phase 5 here (Len, 2026-09-25T18:00:00+08:00).
Phases 6 and 7 can run in parallel once their gates open; both touch `AqOneBuoy.ino`, so merge them one at a time and re-run the Phase 4 bench after each.

## Gate commands

Run from the repository root.
Every phase that touches firmware runs all of the firmware gates; every phase runs the gates for the layers it touches.

```powershell
# Firmware (needs a scratch AqOneSecrets.h from each .example, deleted afterwards)
pio run -d firmware
git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
git diff --no-index firmware/buoy/AqOneBuoy/AqOnePolicy.h firmware/shore/AqOneShore/AqOnePolicy.h
g++ -std=c++17 -Wall -Wextra -Werror -I firmware/buoy/AqOneBuoy firmware/test/policy_test.cpp -o $env:TEMP/policy_test.exe; & $env:TEMP/policy_test.exe

# Backend (includes the firmware static and identity tests)
cd backend; python -m ruff check .; python -m pytest -q
$env:AQONE_SECURITY_PROBES = "1"; python -m pytest -q tests/security_probes/test_probe_repo_static.py

# Mobile
cd mobile; flutter analyze; flutter test

# Web
node --test web/test/*.test.js
```

Both firmware builds must succeed with no new warnings; both `git diff --no-index` lines must print nothing; the security probe must stay at its recorded baseline.
Evidence for every phase goes in `docs/edge-remediation/EVIDENCE-critical.md` (row counts, IDs and log excerpts only; never keys, phone numbers or URLs with credentials).

---

## Phase 1: Evidence for the software-complete Criticals

Requirements: C3, C6, C7, C9, C13
State: Approved; toolchain install handed to Gemini (root `HANDOFF.md`)
Owner: Gemini installs the toolchain; Claude runs the local and deployed checks; Len flashes the shore.

The code for these five is merged and live.
This phase proves it end to end and fixes whatever the proof finds (red test first, per `CLAUDE.md`).
C5 is out of this phase by D7.

### Tasks

- [ ] Create `docs/edge-remediation/EVIDENCE-critical.md` with one section per Critical.
- [ ] D2 (Gemini): install PlatformIO Core and a host `g++`, prove both with a firmware build and a host compile, and record `pio --version` and `g++ --version`.
- [ ] **C9 and C13 - shore reflash.**
  Len: `pio run -d firmware -e shore -t upload` from `master`.
  Record from the serial log: a verified TLS connection (no `setInsecure`), a successful `GET /api/mesh/chat` with `X-Api-Key`, and a dashboard chat line that reaches a phone on a pod.
  Then, against the deployed backend: `POST /api/mesh/chat` with no credential and `sender = "MDRRMO"` returns 422 `sender_reserved` (docs/05 line 1430).
- [ ] **C6 - dashboard with a waiting SOS.**
  With the dashboard closed, post a test SOS; open the dashboard in a browser; the alarm rings on first load (or the audio-unlock banner shows and rings on one click).
  Record whether `SEMAPHORE_API_KEY` and `ONCALL_SMS_NUMBERS` are set on Render (names only), and if they are, let the test SOS go unanswered past the escalation window and record the SMS arriving on the duty phone.
  If they are not set, record "SMS escalation not configured" as an open item for Len; do not mark C6 closed on the SMS half.
- [ ] **C7 - resolve.**
  In the browser: Resolve asks for a reason and confirmation; Undo reopens; the boat's vessel feed shows the reopened incident as active.
- [ ] **C3 - phone keeps trying.**
  Emulator with the backend reachable and the buoy client pointed at a stub that answers `{"accepted": true}` and never delivers.
  The record goes `saved`, `relayed`, then `delivered` within 60 s (the `Pending - Len` item in `EVIDENCE-mobile.md`).
- [ ] Any check that fails: write the failing test in the owning layer first, fix the root cause, and re-run the check.

### Verification

- [ ] Every task above has a dated result in `EVIDENCE-critical.md`, with screenshots for C6 and C7 at 1280 px in light and dark themes.
- [ ] `/health/ready` on the deployed backend reports the current `master` commit.
- [ ] Gate commands for any layer changed by a fix.

### Review and checkpoint

- [ ] Review the evidence for secrets and personal data.
- [ ] Update this plan, `docs/08_DEMO_AND_STATUS.md` (dated entry) and the handoff.
- [ ] Stage only the evidence, status and any fix paths; verify the staged diff.
- [ ] Commit and verify Git reports success.

Checkpoint message: `docs(critical): evidence for C3, C6, C7, C9 and C13`
Stop for Len's go-ahead (hard-stop).

---

## Phase 2: Build step 2 recorded on today's firmware

Requirements: gate for C1, C2, C4, C8, C10, C11, C12, C14 (build order step 2)
State: Approved
Owner: Daniel runs it; Claude records it.

`docs/08` says the current firmware has never run on hardware.
No firmware change lands until two boards on `master` demonstrably talk; this run is also the baseline Phase 3 must not change.

### Tasks

- [ ] Flash `master` to one pod (`-e buoy`, with `AQONE_NODE_ID` overridden to a unique value) and one shore.
- [ ] A phone hands off an SOS to the pod; record from both serial logs the T_SOS, the T_ACK, and the backend row (ID, `buoy_id`, `seq`).
- [ ] Record RSSI and SNR for 10 frames at bench distance.
- [ ] Reproduce C1 while the boards are on the bench: flash a second pod with the default ID and record that the two pods do not relay each other (the "before" for Phase 4).

### Verification

- [ ] A dated build-step-2 entry in `docs/08` with the log excerpts, and the status table updated.

### Review and checkpoint

- [ ] Update this plan, `docs/08` and the handoff; commit.

Checkpoint message: `docs(status): build step 2 recorded on current firmware`
Stop for Len's go-ahead (hard-stop).

---

## Phase 3: A firmware policy boundary the host can test

Requirements: architecture for C1, C2, C4, C8, C10, C11, C14 (no behaviour change)
State: Approved
Depends on: Phase 2

Extract only the decisions later phases change, pinned by characterization tests, so every later Critical fix starts with a red host test.

### Tasks

- [ ] Create `firmware/buoy/AqOneBuoy/AqOnePolicy.h` and its byte-identical copy in `firmware/shore/AqOneShore/`, included from `AqOneLoam.h`.
- [ ] Move into it, unchanged in behaviour, as free functions over plain structs:
  - the queued-SOS ACK match from the T_ACK case (`ackMatchesQueued(const SosSeqs*, uint16_t ackSeq)`);
  - the tracked-table lookup and slot choice from `trackFind()`/`trackVessel()` (returns -1 when full, as today);
  - the shore watch-set slot choice from `watchVessel()` (slot 0 when full, as today);
  - `iso8601ToEpoch()` and `daysFromCivil()`, which are already pure.
  The `.ino` keeps the arrays, flash, radio and JSON; it calls the policy with values it read.
- [ ] Write `firmware/test/policy_test.cpp`: characterization tests for each moved function, including the current full-table behaviour (these are the tests Phase 4 flips).
- [ ] Extend `backend/tests/test_security_regressions.py`: byte-identity for `AqOnePolicy.h`, and the include and forbidden-token check from "How the boundary is enforced".
- [ ] `firmware/README.md`: one paragraph on the two shared headers, the host test command, and why policy never reads a clock.

### Verification

- [ ] Gate commands green.
- [ ] Daniel repeats the Phase 2 bench on the refactored build; the logs match the Phase 2 baseline frame for frame (same types, same ACK, one backend row).

### Review and checkpoint

- [ ] Review that no behaviour changed, the diff only moves code, and the `.ino` handlers got shorter.
- [ ] Update this plan, evidence and handoff; commit.

Checkpoint message: `refactor(firmware): host-testable policy header shared by pod and shore`
Stop for Len's go-ahead (hard-stop).

---

## Phase 4: Firmware Criticals C1, C2, C8, C10 and the mesh half of C14

Requirements: C1, C2, C8, C10, C14
State: Approved
Depends on: Phase 3

### Contract first

- [ ] `docs/02_LOAM_PACKET_SPEC.md`:
  - node ID: lower 32 bits of the eFuse MAC, never `0`, `0xFFFFFFFF` or the shore ID; `AQONE_NODE_ID` stays an override; default name `AQ-` plus 8 hex digits;
  - mesh `seq` starts at a random value on first boot;
  - SOS payload `nc` (incident nonce, above the retry-time shedding of `boat` and `n`); T_ETA payload `nc` replaces `sq`, plus `rc` (resolution code);
  - gateway downlink pacing: at most `DOWNLINK_TX_PER_POLL = 4` T_ETA frames per poll, resend every 10 min only for open acknowledged incidents.
- [ ] `docs/03_PHONE_BUOY_WIFI.md`: pod `/v1/sos/status` returns `nonce` and `resolution_code`; the tracked-table ageing rule.
- [ ] `docs/04_INGEST_API.md`: the gateway forwards `nonce` from `nc` (the field already exists in E4.1).
- [ ] Notify Daniel and Arnold with the diff.

### Red tests first (`firmware/test/policy_test.cpp`)

- [ ] C8 `utf8Copy`: ASCII; `ñ` straddling the limit; a 4-byte emoji straddling the limit; invalid bytes become `?`; empty source; `dstSize` of 1; the result is always valid UTF-8 and NUL-terminated.
- [ ] C1 `nodeIdFromMac`: two MACs differing only in the low bytes give different IDs; reserved values are remapped; `nodeNameFromId` formats `AQ-XXXXXXXX`.
- [ ] C2 `trackEvictionVictim`: with 12 slots full, a resolved entry is chosen before an open one, then the least recently updated; `trackExpired` drops entries resolved more than 6 h ago; the 13th vessel always gets a slot.
- [ ] C10 `watchEvictionVictim`: least recently changed, never slot 0 by default; `downlinkDue` sends at most 4 per poll and repeats an unchanged acknowledged incident only after 10 min; `persistDue` allows one flash write per minute.
- [ ] C14 `handoffDecision`: same `(vessel_id, nonce)` is a duplicate; a different nonce in the same second is new; no nonce falls back to the legacy key.
- [ ] Flip the Phase 3 characterization tests whose behaviour this phase changes, one at a time, each with its reason.
- [ ] Backend static probes: no `strncpy` of user or backend text remains in either sketch; `NODE_ID` defaults from `ESP.getEfuseMac()`.

### Adapters

- [ ] Both sketches: every text `strncpy` becomes `utf8Copy`; the shore note uses it at 40 bytes.
- [ ] Pod: `MAX_TRACKED = 12` using `trackEvictionVictim`; `SosItem` gains `nonce`; `buildSosPayload` sends `nc`; T_ETA handling keys by vessel and `nc`; `/v1/sos/status` returns `nonce` and `resolution_code`.
- [ ] Shore: the watch set uses `watchEvictionVictim` and `persistDue`; the poll loop uses `downlinkDue`; T_ETA carries `nc` and `rc`; the SOS forward includes `nonce`.
- [ ] Both: `meshSeqInit()` seeds from `esp_random()` when no checkpoint exists.

### Verification

- [ ] Gate commands green.
- [ ] Bench (Daniel), each recorded with log excerpts:
  1. Two default builds get distinct node IDs, relay each other, and two SOS give two backend rows (C1, against the Phase 2 "before").
  2. An SOS note with `ñ` at byte 64 and a dispatcher note with `ñ` at byte 40 both show correctly on the phone (C8).
  3. 20 open incidents on the backend: the gateway sends at most 4 T_ETA per poll, tracks 12 vessels, and after settling repeats only on the 10 min resend; a pod shows the acknowledgement for the 13th vessel (C2, C10).
  4. A mesh SOS lands with its `nonce`; 60 pre-created legacy rows for that vessel's next 60 seconds do not capture it (C14).
- [ ] D4 (approved): a new migration drops the legacy `(vessel_id, client_ts)` branch and `sos.py` rejects an SOS without `nonce` with 422; red test first in `backend/tests/`.

### Review and checkpoint

- [ ] Review cross-layer field names (`nc`, `rc`, `nonce`, `resolution_code`) against the contract docs; that is where the last review found its bugs.
- [ ] Update this plan, evidence, `docs/08` and handoff; commit.

Checkpoint message: `fix(firmware): unique node ids, bounded radio tables, byte-safe text, mesh nonce`
Stop for Len's go-ahead (hard-stop).

---

## Phase 5: Per-node radio keys and signed broadcasts (C11)

Requirements: C11
State: Approved (gated)
Depends on: Phase 4, build step 3 recorded in `docs/08`

Design: docs/61 D7.5, with Ed25519 instead of ECDSA P-256 (see "One signature algorithm everywhere").
The frame version changes, so every board must be reflashed in one session; a board on the old version hears nothing, which is exactly the "out of range" failure.

### Contract first

- [ ] Confirm the pod's Ed25519 source before writing the contract: `crypto_sign_verify_detached` from `sodium.h` in the ESP32 Arduino core, built for `heltec_wifi_lora_32_V3`; if it does not build, `rweather/Crypto` pinned in `platformio.ini`. Record which in the evidence.
- [ ] `docs/02`: `LOAM_VERSION = 0x02`; the two-tag frame (4-byte network tag under the shared key for relay filtering, 8-byte node tag under `K_node` on SOS uplink and ACK downlink); `K_node = HMAC-SHA256(LOAM_MASTER, node_id)`; the broadcast signature field (64-byte Ed25519) on T_WARN, T_ETA and official T_CHAT; the canonical signed bytes.
- [ ] `docs/04` and `docs/05`: `sig` (base64) on downlink events and on the warning and chat feeds the gateway reads.

### Backend (red tests first)

- [ ] Move `cryptography` from `requirements-dev.txt` to `requirements.txt` (approved in docs/62 Section 1).
- [ ] `app/incidents/downlink.py`: `broadcast_bytes(event) -> bytes`, pure, matching the docs/02 canonical form.
- [ ] `app/radio_signing.py`: `sign(data: bytes) -> bytes` (Ed25519); the key is read once from `AQONE_AUTHORITY_SIGNING_KEY` (PEM, set in Render, never in the repo) at startup; with no key set, feeds omit `sig` and `/api/ops/status` says so.
- [ ] The downlink, warning and chat feed adapters add `sig`.
- [ ] Tests: sign-and-verify round trip; a flipped byte fails; `broadcast_bytes` matches a golden vector in `fixtures/loam/broadcast_vectors.json`; `test_incidents_is_pure.py` still passes.

### Firmware (red tests first)

- [ ] `firmware/tools/provision_pod.py` (standard library plus `cryptography`, run from the backend virtual environment): derives `K_node`, writes a per-pod `AqOneSecrets.h` holding only `K_node` and the authority public key, never the master; a test checks it against `fixtures/loam/node_key_vectors.json`.
- [ ] `policy_test.cpp`: `ackMatchesQueued` now also requires the node-tag result; an ACK for our ID and seq with a bad node tag is rejected.
- [ ] `AqOneLoam.h`: encode and check both tags; the gateway derives `K_node` from the master; pods verify broadcast signatures and drop unsigned or invalid ones; a frame with an unknown `LOAM_VERSION` logs one line per minute instead of vanishing silently.
- [ ] Turn `test_loam_signature_key_is_selected_per_source_id` from red to green.

### Verification

- [ ] Gate commands green.
- [ ] Bench: an ACK signed with another pod's key does not delete the queued SOS; a WARN with a flipped byte is ignored; a valid WARN, ETA and official chat line are shown; airtime per broadcast measured and recorded.

### Review and checkpoint

- [ ] Security review of the diff (`/security-review`); confirm no key value appears in the repo, the evidence or the logs.
- [ ] Update this plan, evidence, `docs/16_QA_DISCLOSURES.md` (C11 residual) and handoff; commit.

Checkpoint message: `feat(security): per-node radio keys and backend-signed broadcasts`
Stop for Len's go-ahead (hard-stop).

---

## Phase 6: The phone checks that a pod is real (C12)

Requirements: C12 (cause)
State: Redesigned in Revision 2 after D3; needs Len's approval before it starts (gated)
Depends on: Phase 5 (authority key, Ed25519 on the pod, provisioning tool), build step 4 recorded

D3 rules out a pod password, so the pod stays an open "Aquan" network and the fisher does nothing new.
Instead the pod proves who it is inside the reply the phone already waits for:

1. At provisioning, each pod gets its own Ed25519 key pair, and the backend signs a certificate over the pod's node ID and public key.
2. The phone sends a random challenge with every handoff.
3. The pod's "accepted" reply carries its certificate and a signature over the challenge, the incident nonce and the vessel ID.
4. The phone checks both against the authority public key built into the app, with no network needed.

A look-alike board cannot produce that proof, so its "accepted" no longer counts: the record stays `saved` and the phone keeps trying other pods and the direct path.
This is the delivery-state rule applied to pods: no `relayed` without evidence.

### Contract first

- [ ] `docs/03`: `POST /v1/sos` request adds `challenge` (16 random bytes, base64); the reply adds `pod_id`, `pod_key`, `pod_cert` and `proof`; the exact signed bytes (`AQPOD1 || node_id || pod_key` for the certificate, `AQACC1 || challenge || nonce || vessel_id` for the proof).
- [ ] `docs/06`: a pod reply counts as `relayed` only with a valid proof.
- [ ] `docs/05`: `POST /api/pods/certify` (operator only), body `{node_id, public_key}`, returns the certificate and records the pod.

### Tasks (red tests first)

- [ ] Backend: `api/pods.py` signs certificates with `radio_signing.sign`; a new numbered migration stores each pod's public key and a `revoked_at`; tests for operator-only access, a round trip, and refusing a revoked node ID.
- [ ] `provision_pod.py`: generates the pod key pair locally, calls `certify` with an operator credential, and writes the private key and certificate to that pod's `AqOneSecrets.h` only.
- [ ] `policy_test.cpp`: `acceptanceMessage` builds exactly the docs/03 bytes (golden vector shared with the phone in `fixtures/loam/pod_proof_vectors.json`).
- [ ] Pod: the `/v1/sos` handler signs `acceptanceMessage` and adds the four fields.
- [ ] `mobile/test/pod_attestation_test.dart`: a valid proof passes; a wrong challenge, nonce or vessel ID, a certificate from another key, and a missing field each fail; the golden vector matches.
- [ ] `mobile/lib/models/pod_attestation.dart` (pure) and `BuoyClient`: send the challenge, and treat an unproven "accepted" as not accepted.
- [ ] The authority public key is a constant in `mobile/lib/core/config.dart` (it is public; rotating it needs an app update, recorded as an accepted limit).

### Verification

- [ ] Gate commands green.
- [ ] Device test (Len): a second board flashed as a fake "Aquan" pod that replies `{"accepted": true}`; the phone stays at `saved` and hands off to the real pod as soon as it is in range; the fisher sees no new step.
- [ ] Device test: a real provisioned pod still takes an SOS to `relayed` in airplane mode.

### Review and checkpoint

- [ ] Security review of the diff; no private key in the repo, evidence or logs.
- [ ] Update this plan, evidence, `docs/16` (C12 residual: a stolen real pod's key works until it is revoked, and offline phones do not learn revocations) and handoff; commit.

Checkpoint message: `feat(pod): phones only trust pods that can prove who they are`
Stop for Len's go-ahead (hard-stop).

---

## Phase 7: Pod SOS button and GPS (C4)

Requirements: C4
State: Approved (gated on D5)
Depends on: Phase 4, D5, and the H23 charger thermal check passed (docs/62D F5)
Owner: Daniel (hardware and bench), agent (firmware and contract)

Design: docs/61 D12.1.
Clean Architecture point: a button press and a phone handoff are two adapters for one use case, so both go through `handoffDecision` and the same queue.

### Contract first

- [ ] `docs/02` and `docs/03`: a pod-originated SOS carries the provisioned vessel ID, a pod-generated `nc`, the pod's GPS fix, and `src = pod_button`; LED patterns for the four delivery states; pod GPS fills a phone SOS that has no fix.
- [ ] `docs/04`: `source` value `pod_button`, shown on the dashboard.

### Tasks (red tests first)

- [ ] `policy_test.cpp`: `holdTriggered` fires after 3 s of continuous press and not on bounces; `handoffDecision` treats a second press during an open SOS as a duplicate; a phone SOS without a fix is filled from the pod fix.
- [ ] Pod adapters: button GPIO with debounce feeding `holdTriggered`; GPS via `TinyGPSPlus` feeding the latest valid fix; LED driver for the four states.
- [ ] `provision_pod.py` writes the vessel ID into the pod's secrets header.

### Verification

- [ ] Gate commands green.
- [ ] Bench (Daniel): a 3 s hold with the phone switched off raises an SOS that lands on the dashboard with the pod's position; short taps do nothing; the LED follows `saved`, `relayed`, `delivered`, `acknowledged`.
- [ ] Outdoor record of time to first fix, from cold.

### Review and checkpoint

- [ ] Update this plan, evidence, `docs/08` and handoff; commit.

Checkpoint message: `feat(pod): SOS button and GPS on the boat pod`
Stop for Len's go-ahead (hard-stop).

---

## Done when

- [ ] Every row of "Where each Critical stands today" has its outcome evidenced in `docs/edge-remediation/EVIDENCE-critical.md`.
- [ ] The docs/60 Critical table shows each ID as Closed or Mitigated, with the residual recorded in `docs/16_QA_DISCLOSURES.md`.
- [ ] `docs/08` status table reflects it.

## Recovery

Follow project `AGENTS.md` for the three-attempt limit.
Record unresolved work and attempt counts in the current `HANDOFF.md`.
Interrupted or failing work remains uncommitted and the phase remains incomplete.
