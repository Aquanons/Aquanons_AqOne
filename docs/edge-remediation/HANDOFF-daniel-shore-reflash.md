# Handoff for Daniel: reflash the shore gateway (C9, C13)

**Status:** ACTIVE
**Owner:** Daniel (bench and flash), Len (secrets, dashboard chat line), Claude (records the evidence)
**Created:** 2026-09-25
**Updated:** 2026-09-25
**Related:** `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md` Phase 1, `docs/edge-remediation/EVIDENCE-critical.md`, `firmware/README.md`

## Why this matters

This is the last open check in plan 66 Phase 1, and it should be done before RSTW (2026-10-01).
The shore board on the mast still runs old firmware, so it cannot read chat from the backend and chat to the boats is down.
`master` already has the fix: the shore sends `X-Api-Key` when it reads `/api/mesh/chat` (C9), and it checks the backend's TLS certificate instead of trusting anything (C13).
Nothing needs coding; the board just needs `master` flashed onto it and a short test.

The backend half of C9 is already verified: a chat post from anyone claiming to be "MDRRMO" is refused.
The phone, dashboard and alarm checks (C3, C6, C7) are also done; see the evidence file.

## What you need

- The shore board (Heltec WiFi LoRa 32 V3) and a USB-C data cable.
- One boat pod (a second Heltec flashed as `buoy`) and an Android phone with the AqOne app, for the chat test.
- A laptop with PlatformIO (`pio --version` works) and the repo on `master`.
- From Len, in a private message (never in the group chat, never in Git):
  - the uplink WiFi name and password for the mast (`UPLINK_SSID`, `UPLINK_PASS`);
  - `GATEWAY_API_KEY` (must match the Render backend);
  - the fleet `LOAM_KEY` (must be the same on the shore and every pod).

## Steps

### 1. Get the current code

```bash
git checkout master
git pull
```

### 2. Make the shore secrets file

Copy `firmware/shore/AqOneShore/AqOneSecrets.h.example` to `firmware/shore/AqOneShore/AqOneSecrets.h` and fill in the four values from Len.
`AqOneSecrets.h` is gitignored; run `git status` afterwards and make sure it does not show up.
The build refuses the example `LOAM_KEY`, so a build error about the key means the file still has the placeholder.

### 3. Flash and watch the shore

```bash
pio run -d firmware -e shore -t upload
pio device monitor -d firmware -e shore
```

Within about a minute you should see:

| Log line | What it proves |
| --- | --- |
| `[wifi] uplink ok  ip=...` | The board joined the mast WiFi |
| `[ack] poll ok: N open incident(s) for M vessel(s), ...` | A verified TLS connection to the backend with `X-Api-Key` accepted (C13 and the gateway key) |

If you see `[ack] downlink poll -> 401 - GATEWAY_API_KEY rejected`, the key does not match Render; ask Len for the right one.
If you see `[ack] downlink poll -> -1` (or another negative number), TLS or the network failed; send Claude the lines around it.
Leave the monitor running.

### 4. Make sure the pod speaks the same radio

The pod must have the same `LOAM_KEY` as the shore, or nothing arrives and nothing is logged.
If you are not sure the pod has the fleet key and current `master`, do the same as step 2 in `firmware/buoy/AqOneBuoy/`, then:

```bash
pio run -d firmware -e buoy -t upload
```

After flashing, check the two `AqOneLoam.h` copies are identical (the command must print nothing):

```bash
git diff --no-index firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
```

### 5. Chat test: dashboard to phone (C9)

1. Put the phone on the pod's WiFi (`Aquan`, no password) and open the chat screen in the app.
2. Message Len (or Claude): "shore is up".
3. Len posts a chat line from the dashboard, for example `C9 test 1`.
   At its first chat poll (20 s after boot) the shore skips every line already on the backend, so send the line only after `[ack] poll ok` has appeared.
4. Within about 30 seconds the line should appear on the phone.
   On the pod's serial monitor (if connected) you will see `[lora] rx type=0x05 ...`.
5. Reply from the phone with any short line; the shore log should show `[chat] POST <sender> -> 201`, and the line should show on the dashboard.

### 6. Send back to Claude (through Len)

- The shore log lines from step 3 and step 5, copied as text.
  Remove the WiFi name if it appears; never paste keys or passwords.
- A screenshot of the phone chat showing the dashboard line.
- The time you ran it, and anything that did not match this page.

### 7. Clean up

- Keep `AqOneSecrets.h` only on your laptop; never commit it.
- `git status` should show no changes under `firmware/`.

## Done when

- `[ack] poll ok` appears on the reflashed shore (C13).
- A dashboard chat line reaches a phone on a pod, and a phone reply reaches the dashboard (C9).
- Claude has recorded both in `EVIDENCE-critical.md`.

## If you have time after this

Plan 66 Phase 2 is yours next: two boards on the bench on today's `master`, one raw packet each way, logs recorded in `docs/08_DEMO_AND_STATUS.md`.
Every firmware fix in plan 66 waits on that baseline.
