# Track F - Firmware (edge-case remediation, gated)

Master plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` (read Sections 1 to 4 first).
Design: `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md` D5, D6, D7.5, D12.
**Execution mode:** hard-stop
Branch and worktree: `edge/firmware`, `../AqOne-edge-firmware`
Owns: `firmware/**`, and for F4 only, the backend signing files listed there.
Evidence: `docs/edge-remediation/EVIDENCE-firmware.md`.
State: Blocked until build step 2 ("two radios talk") is recorded in `docs/08`.
Assignment: whichever of the three agents finishes its track first.
Daniel runs every bench and field step, because agents cannot flash or observe radios.

## Rules for this track

- **Shared policy lives in `AqOneLoam.h`.**
  This covers UTF-8 copy, eviction comparators, clock adoption, the replay window and relay backoff.
  After every edit:
  `git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h` must print nothing.
- **Clean code in C++.**
  - Small functions named for what they decide (`trackEvictionVictim()`, `adoptClockFrom(frame)`), not for how they loop.
  - Replace magic numbers with the named constants the contract uses (`DOWNLINK_MAX`, `REPLAY_WINDOW_S`).
  - Comments only for radio or hardware constraints.
- **Contract first.**
  Phase F0 writes the relay, clock and key rules into `docs/02_LOAM_PACKET_SPEC.md` before any code.
- **Secrets** stay in the ignored `AqOneSecrets.h`; never write key values anywhere.
- **Gate commands** (every phase), run from `firmware/`:

  ```powershell
  $env:PLATFORMIO_SRC_DIR = "buoy/AqOneBuoy"; pio run -d . -e buoy
  $env:PLATFORMIO_SRC_DIR = "shore/AqOneShore"; pio run -d . -e shore
  git diff --no-index buoy/AqOneBuoy/AqOneLoam.h shore/AqOneShore/AqOneLoam.h
  gcc -std=c11 -Wall -Werror test/utf8_copy_test.c -o $env:TEMP/utf8_copy_test.exe; & $env:TEMP/utf8_copy_test.exe
  ```

  Both builds must succeed with no new warnings, which needs a scratch `AqOneSecrets.h` from the `.example` files, deleted afterwards.
  `cd backend; python -m pytest -q tests/security_probes/test_probe_repo_static.py` with `AQONE_SECURITY_PROBES=1` must stay at its Phase 6 result.

## Two-board bench script (Daniel)

This is referenced by the phases below.
Record each step's result in the evidence file with the serial log excerpt.

1. Flash two default builds.
   Expect two distinct node IDs, and two SOS calls give two backend rows (C1).
2. Send an SOS whose note has `ñ` at byte 64, then a dispatcher note with `ñ` at byte 40.
   The phone shows both, and the WebSocket stays connected (C8, L7).
3. Create 20 open incidents on the backend.
   The gateway sends at most 4 T_ETA frames per poll and 12 vessels in total, and after settling repeats only on the 10 min resend (C10, C2).
4. Boot the shore with the router off and start the router after 30 s.
   NTP syncs, and verified HTTPS posts succeed (M4, N1).
   The same run confirms the security fixes on hardware: TLS verification is on (C13), and a mesh SOS lands with its `seq` and `buoy_id` (H13).
5. Power a pod from a weak supply with an SOS queued.
   The frame completes, or TX power steps down after 2 brownouts (M16).
6. Hand off the same `(vessel_id, nonce)` twice, first with no note and then with one.
   The backend row has the note (H5).
7. Reboot a pod while a warning is active.
   The pod has the warning again within 10 min (H14).
8. Connect 3 phones to one pod and hand off 3 SOS from one of them.
   The third returns "queue full for this phone", and the other phones can still queue (H19).

---

## Phase F0: Firmware contract (Claude)

Requirements: the docs/02 parts of EC-C1, EC-H11, EC-M15, EC-L6, EC-H14 and EC-C11
State: Blocked (gated)

### Tasks

- [ ] `docs/02_LOAM_PACKET_SPEC.md`:
  - Node ID derivation (the lower 32 bits of the eFuse MAC; `AQONE_NODE_ID` is an override), and a random mesh-seq start.
  - Clock adoption from shore-originated types only, re-adoption from each newer shore frame, and `REPLAY_WINDOW_S = 600`.
  - Relay rules: CAD before TX, backoff in `[0, 2 × time-on-air]`, counter suppression, and pods relaying only T_SOS and T_ACK.
  - WARN rebroadcast every 10 min, and T_ETA resend every 10 min for open, acknowledged incidents.
  - `rc` values: 1 rescued, 2 safe_confirmed, 3 stood_down_by_fisher, 4 duplicate, 5 closed_unconfirmed, 6 unspecified.
  - An F4 section: the per-node key derivation and the broadcast signature field (written now, implemented in F4).
- [ ] `docs/03_PHONE_BUOY_WIFI.md`: the per-client queue cap wording and error body, and `/v1/status` `queue_depth`.
- [ ] Notify Daniel and Arnold.

Checkpoint message: `docs(loam): relay, clock, identity and signature rules for edge remediation`

---

## Phase F1: Bench-safe firmware fixes

Requirements: EC-C1, EC-C2, EC-C8, EC-C10, EC-C13 (hardware check), EC-H13 (hardware check), EC-C14, EC-H5, EC-H14, EC-H17, EC-H19, EC-L6, EC-L7, EC-L10, EC-M4, EC-M15, EC-N1
Merge after: F0, B2 and B5
State: Blocked (gated)

### Tasks

- [ ] Write red tests first:
  - `firmware/test/utf8_copy_test.c`, an assert-based host test of `utf8Copy`:
    - ASCII
    - `ñ` straddling the limit
    - a 4-byte emoji straddling the limit
    - invalid bytes become `?`
    - an empty source
    - a `dstSize` of 1
  - Add static probes to `backend/tests/security_probes/test_probe_repo_static.py`, the existing pattern for firmware assertions:
    - no bare `strncpy` of user or backend text remains in either sketch
    - `NODE_ID` defaults from `ESP.getEfuseMac()`
    - the shore sends `X-Api-Key` on both chat requests
    - `MAX_TRACKED >= 12`

    This test file sits under `backend/`, but it is a firmware acceptance probe.
    Coordinate with the Track B agent before merging to avoid conflicts.
- [ ] `AqOneLoam.h` (both copies):
  - `size_t utf8Copy(char* dst, size_t dstSize, const char* src)`
  - `REPLAY_WINDOW_S`
  - `adoptClockFrom(type, now)`, which accepts only shore types and always re-adopts newer shore time
  - `NODE_ID` and `NODE_NAME` defaults from the eFuse MAC
  - a random `meshSeq` start from `esp_random()`
- [ ] `AqOneBuoy.ino`:
  - Replace every text `strncpy` with `utf8Copy`.
  - Add `nonce` to `SosItem`, and send `nc` in `buildSosPayload`, above the shedding ladder.
  - A duplicate handoff on `(vessel_id, nonce)` fills an empty `note`, `lat` or `lon`, and falls back to the legacy key when there is no nonce.
  - Per-client cap of 2 by station MAC.
  - `MAX_TRACKED = 12`, with eviction via `trackEvictionVictim()` (resolved first, then least recently updated), and clearing entries resolved more than 6 h ago.
  - T_ETA parses `nc` and `rc`, keyed by vessel and nonce.
  - `/v1/sos/status` returns `nonce` and `resolution_code`.
  - `/v1/status` returns `queue_depth`.
  - Warning eviction order: expired, then lowest priority, then oldest.
  - A queue struct mismatch at boot logs the number of entries lost.
- [ ] `AqOneShore.ino`:
  - The note uses `utf8Copy` at 40 bytes.
  - The watch set mirrors the downlink feed plus vessels heard in a T_SOS within 6 h, with least-recently-changed eviction and flash writes rate-limited to once a minute.
  - At most 4 T_ETA frames per poll, and a 10 min resend for open, acknowledged incidents.
  - T_ETA carries `nc` and `rc`.
  - Every active warning is rebroadcast every 10 min.
  - `configTime` runs on every uplink reconnect.
  - `now` is not stamped into frames before the clock is valid.
  - `X-Api-Key` is sent on `pollChat` and the chat POST.
- [ ] `firmware/README.md`: the flashing procedure requires `queue_depth == 0` first.

### Verification

- [ ] Gate commands green.
- [ ] Bench script steps 1 to 4 and 6 to 8 pass (step 5 belongs to F5), recorded by Daniel.

Checkpoint message: `fix(firmware): unique node ids, bounded radio tables, byte-safe text, and clock hygiene`

---

## Phase F2: Gateway never deaf

Requirements: EC-H12 (firmware part)
Merge after: F1
State: Blocked (gated)

### Tasks

- [ ] Move all HTTPS work in `AqOneShore.ino` into a FreeRTOS task pinned to core 0, fed by a `QueueHandle_t` of work items.
  Results come back to the radio loop on core 1 through a second queue.
  The radio loop never calls `https.*`.
- [ ] Add a static probe: no `https.` call is reachable from `loop()` or `radioService()`.

### Verification

- [ ] Gate commands green.
- [ ] Bench: while the uplink is throttled to 12 s responses, 5 SOS frames from a second board arrive within 10 s, and all 5 are received and forwarded with no pod retry needed.

Checkpoint message: `perf(shore): keep the radio listening during HTTPS calls`

---

## Phase F3: Relay discipline (field-gated, P3)

Requirements: EC-H11
Merge after: F2, and build step 6 (outdoor range test) recorded in `docs/08`
State: Blocked (gated)

### Tasks

- [ ] `AqOneLoam.h`: `scanChannel()` channel activity detection before each TX, a relay backoff of `random(0, 2 * radio.getTimeOnAir(len) / 1000)` ms, and cancelling a pending relay when the same `(src, seq, type)` is heard relayed during the backoff.
- [ ] Pods (`NODE_ROLE_POD`) relay only T_SOS and T_ACK; relay buoys relay everything.
- [ ] Update the comment at `AqOneLoam.h:545-548` with measured airtime.

### Verification

- [ ] Gate commands green.
- [ ] Field record: 5 or more pods clustered within 20 m, 10 simultaneous SOS; the delivered count and gateway duplicates are recorded before and after.

Checkpoint message: `feat(loam): listen-before-talk relays with duplicate suppression`

---

## Phase F4: Per-node keys and signed broadcasts (gated after build step 3)

Requirements: EC-C11
Merge after: F1, and build step 3 recorded in `docs/08`
State: Blocked (gated)

### Tasks - backend part (runs in the Track B worktree as B8)

- [ ] Add `cryptography` (approved by Len) to `backend/requirements.txt`.
- [ ] `app/radio_signing.py`: `sign_broadcast(payload_bytes) -> bytes` using ECDSA P-256 over SHA-256, returning the raw 64-byte `r||s`.
  The key comes from env `LOAM_BROADCAST_PRIVATE_KEY` (PEM, set in Render, never in the repo).
- [ ] `/api/sos/downlink` events and the warning feed the gateway reads each add `sig` (base64) over the exact payload bytes the gateway will transmit.
  The payload canonicalisation is defined in docs/02 F0.
- [ ] Tests: sign-and-verify round trip; a tampered payload fails.
  The public key is exported to `firmware/tools/broadcast_pubkey.pem` for flashing.

### Tasks - firmware part

- [ ] `firmware/tools/provision_pod.py` (stdlib only): `K_node = hmac.new(LOAM_MASTER, node_id_bytes, sha256).digest()`.
  It writes a per-pod `AqOneSecrets.h` holding only `K_node` and the broadcast public key, and never the master.
- [ ] `AqOneLoam.h`:
  - A two-tag frame: the network tag (shared key, 4 bytes, for relay filtering) plus the node tag (`K_node`, 8 bytes) on SOS uplink and ACK downlink.
  - The gateway derives `K_node` from the master.
  - Pods verify the backend's broadcast signature on T_WARN, T_ETA and official T_CHAT using mbedTLS ECDSA.
  - Unsigned or invalid broadcasts are dropped.
- [ ] Turn `test_loam_signature_key_is_selected_per_source_id` from red to green.

### Verification

- [ ] Gate commands green.
- [ ] Bench:
  - an ACK signed with another pod's key does not delete the queued SOS
  - a WARN with a flipped byte is ignored
  - a valid WARN is shown
- [ ] Airtime per broadcast measured and recorded.

Checkpoint message: `feat(security): per-node radio keys and backend-signed broadcasts`

---

## Phase F5: Hardware (Daniel, not agent work)

Requirements: EC-C4, EC-H23, EC-M5, EC-M11, EC-M16
State: Blocked (gated per item)

- [ ] **H23, before any sealed-pod test.**
  The charger BOM has NTC cutoff with no charging above 45 °C, plus a vent membrane.
  Bench at 60 °C ambient, and record cell temperature.
- [ ] **M11.**
  Record the NTC answer.
  If AS923 applies, change the one `LORA_FREQ_MHZ` constant (F0 contract first), and buy only 863-928 MHz boards.
- [ ] **M16.**
  Battery voltage check before TX, a persisted brownout counter that steps TX power down after 2, and a bulk capacitor.
  Run bench step 5.
- [ ] **C4.**
  A 3 s hold SOS button and a GPS module on the pod.
  The pod raises an SOS with its provisioned vessel ID and fix, and the LED patterns follow docs/61 D12.1.
  This needs its own docs/03 and docs/02 contract step first.
- [ ] **M5.**
  Relay-buoy hardening (bird spikes, anode, conformal coat) and "no shore beacon for 30 min" on the pod's LED.
  Field record.

## Recovery

Follow project `AGENTS.md` for the three-attempt limit.
Record unresolved work and attempt counts in this worktree's `HANDOFF.md`.
