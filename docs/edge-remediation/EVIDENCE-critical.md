# Evidence: Critical edge cases (plan 66)

Plan: `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md`.
Each phase appends a dated section.
Record row counts, IDs and log excerpts only; never keys, phone numbers or URLs with credentials.

## Phase 1 - D2 toolchain (2026-09-25)

Installed PlatformIO Core with `python -m pip install -U platformio`.
Installed WinLibs POSIX UCRT with WinGet package `BrechtSanders.WinLibs.POSIX.UCRT`.

| Tool | Version | Location |
| --- | --- | --- |
| PlatformIO Core | 6.2.0 | `C:\Users\User\AppData\Local\Programs\Python\Python311\Scripts\pio.exe` |
| Host `g++` | 16.1.0 (WinLibs POSIX UCRT 16.1.0-14.0.0-r4) | `C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\g++.exe` |

In a new PowerShell process with the updated user PATH, `pio --version` and `g++ --version` both succeeded.

Firmware build: `pio run -d firmware` exited 0.

| Environment | Result | Warnings |
| --- | --- | --- |
| buoy | SUCCESS (12.80 s) | 0 |
| shore | SUCCESS (13.94 s) | 0 |

The build used temporary random scratch `AqOneSecrets.h` files in both sketch folders.
Both files were removed after the build.
No `AqOneSecrets.h` remains under `firmware/`, and `git status --short` shows no firmware changes.

Host compile: `g++ -std=c++17 -Wall -Wextra -Werror` on `int main(){return 0;}` compiled with exit 0 and ran with exit 0.
The temporary source and executable were removed.

Limit: shells opened before the install do not see `g++` until they are restarted.
No secret values were recorded.
Claude re-ran the firmware build and the host compile independently the same day with the same results (buoy 37.6 s, shore 16.1 s, 0 warnings).

## Phase 1 - C6 SMS escalation: not configured (2026-09-25)

Len confirmed that neither `SEMAPHORE_API_KEY` nor `ONCALL_SMS_NUMBERS` is set on Render.
With either unset, `app/notify.py` reports "not configured" instead of sending (`docs/18_BACKEND_STRUCTURE.md`).
C6 is not closed on the SMS half.

To do (Len):

- [ ] Create a Semaphore account and API key; set `SEMAPHORE_API_KEY` in the Render dashboard (`render.yaml` declares it with `sync: false`).
- [ ] Set `ONCALL_SMS_NUMBERS` (comma-separated duty phones) and, optionally, `SEMAPHORE_SENDER_NAME` in the Render dashboard.
- [ ] Re-run the C6 SMS check: leave a test SOS unanswered past the escalation window and record the SMS arriving on the duty phone (no phone numbers in this file).

## Phase 1 - C9 deployed half (2026-09-25T21:53+08:00)

Against the deployed backend (`/health/ready` commit `a0f8284`), with no credential:

| Request | Result |
| --- | --- |
| `POST /api/mesh/chat` sender `MDRRMO` | 422 `sender_reserved` |
| `POST /api/mesh/chat` sender `M.D.R.R.M.0` | 422 `sender_reserved` |
| `POST /api/mesh/chat` sender `MDRRMO` with body `origin = "mdrrmo"` | 422 `sender_reserved` (the body origin is ignored) |
| `POST /api/mesh/chat` sender `coast guard` | 422 `sender_reserved` |
| `GET /api/mesh/chat` | 401 `chat credential required` |
| `GET /api/mesh/chat` with a wrong `X-Api-Key` | 401 `chat credential required` |

Refused posts insert nothing (the check runs before the insert, `backend/app/api/mesh.py`).
The shore half of C9 (the reflashed gateway reads chat with `X-Api-Key`) is task 4.

## Phase 1 - C3 phone keeps trying past `relayed` (2026-09-25T22:17-22:25+08:00)

Environment: Android emulator (API 37, Google Play image), debug APK from `master` `a0f8284` built with `--dart-define=PITCH_MODE=true`, default endpoints (pod `http://192.168.4.1`, backend `https://aqone-backend.onrender.com`).
The emulator ran with `-http-proxy` to a local harness that answers 192.168.4.1 as a stub pod (`POST /v1/sos` returns `{"accepted": true, "buoy_id": "STUB01", ...}`, `/v1/sos/status` returns `{"events": []}`, `/v1/status` reports `uplink: false`) and tunnels every other host.
The harness refuses the backend's IPs until a switch file exists, so the direct route can be turned off and on without touching the app.
GPS was set to 11.66 N, 122.48 E (inside `app/geo.py`'s water polygon).
States below are read from the app's own SQLite outbox (`aqone_outbox.db`) and from the "Your messages" card.

Run 1 - backend reachable (the check as written):

| Time | Event |
| --- | --- |
| 22:17:23 | Stub pod accepted the SOS (seq 1) |
| 22:17:25 | Outbox `relayed_at` and `delivered_at` both set; state `delivered`; backend incident id 429 |

Run 2 - backend refused, then restored:

| Time | Event |
| --- | --- |
| 22:19:39 | Stub pod accepted the SOS; direct post refused; state `relayed` ([screenshot](critical/c3-relayed.png)) |
| 22:20:17 | Third attempt, still `relayed`: the phone kept retrying the direct route after `relayed` |
| 22:21:08 | Backend restored |
| 22:25:17 | State `delivered` ([screenshot](critical/c3-delivered.png)); backend incident id 430 |

Result: C3 closes.
The phone no longer stops at `relayed`: with the backend reachable it reaches `delivered` within 2 s, and while the backend is down it keeps retrying.
Limit: after the backend returns, delivery waits for the next retry, and the direct-route backoff (`mobile/lib/models/delivery_policy.dart`: 20 s, 60 s, then every 5 min) put it at 4 min 9 s here, not 60 s.
That timing is by design, not a regression, but it is the figure to quote.

Incidents 429 and 430 (boat `TEST-C3`) are test rows on production; they are the waiting SOS for the C6 check and get resolved with a test reason afterwards.
A third SOS from a fresh install stayed `relayed` with the backend refused and was discarded with the app data; it never reached the backend.

Observed once, not reproduced (open, owner Jade):
On the very first SOS after registration (22:08:21, straight after the "run in background" system dialog), the countdown froze at "1" and never sent.
Through the VM service: `_SosCountdownScreenState` had `_resolved = true`, `_timer` cancelled and `_remaining = 100 ms`, yet the `RawDialogRoute` was still current and idle with no local history, the outbox was empty, and nothing reached the stub pod.
Because `_resolved` was already true, the slide-to-cancel did nothing either, so a fisher would be stuck on "Sending SOS" with nothing sent.
No exception was logged.
Two further attempts (after a force-stop, and on a fresh install) counted down and sent normally.

Follow-up, 2026-09-26 (Claude, widget tests on `ux/fisher-friction`):
Two defects each produce exactly this state, and both are reproduced by `mobile/test/sos_countdown_freeze_test.dart` (commit `cee0ece`).
1. The countdown's `_finish` calls `Navigator.pop`, which closes whatever route is on top; a squall page, ETA dialog or unsent-SOS prompt opened during the 5 seconds is closed instead, and the finished countdown stays on screen.
2. `handleSosTap` (and the older `_handleSosTap` copies on `master`) sets its sending flag only after awaiting `SharedPreferences`, so a quick double tap opens two countdowns; the first closes the second, and the first is left frozen.
Which one happened at 22:08 is not known.
The fix is handed to Luna in `docs/fisher-ux/HANDOFF-luna-countdown-freeze.md` on that branch; the emulator run was not repeated because memory was short.

UI defect seen on the way (owner Jade): the floating SOS button covers the text of the second "Your messages" card ("Received by the MDRRMO dashboard" in `c3-relayed.png`).

## Phase 1 - C6 browser half and C7 (2026-09-25T22:38-22:45+08:00)

Environment: the deployed dashboard (`/html/dashboard.html`, commit `a0f8284`) in headless Microsoft Edge at 1280 x 900, driven over the DevTools protocol with real mouse events, `--autoplay-policy=document-user-activation-required` (the normal browser rule), logged in through `login.html` as the shared demo operator account.
An init script counted `AudioContext` states and `OscillatorNode.start()` calls so "rings" is measured, not assumed.
The waiting SOS were incidents 429 and 430 from the C3 run; the dashboard had not been opened since they arrived.

C6 - alarm on first load:

| Moment | Alarm armed | AudioContext | Siren oscillator starts | Banner |
| --- | --- | --- | --- | --- |
| First load, no click | yes | `suspended` (browser rule) | 0 | "Alarm sound is OFF - click to enable" ([light](critical/c6-first-load-light.png)) |
| After one click on the banner | yes | `running` | 1 | hidden; tab title flashes `SOS - <vessel>` ([light](critical/c6-after-unlock-light.png), [dark](critical/c6-after-unlock-dark.png)) |
| After Undo reopened incident 430 | yes | `running` | 2 | the reopened call rang again, with an "SOS received" toast |
| After both test incidents were resolved | no | - | - | siren stopped; only an acknowledged incident remained |

Result: C6 closes on the browser half.
The SMS half stays open (see the SMS section above).

C7 - resolve, undo, reopen:

- Resolve on incident 429 opens a modal that names the vessel and boat, lists five reasons, and keeps "Confirm resolution" disabled until a reason is chosen ([screenshot](critical/c7-resolve-modal-light.png)).
- Confirming removed 429 from the live feed and showed "Incident resolved - You can reopen this call for 10 seconds" with Undo ([screenshot](critical/c7-resolved-undo-toast-light.png)).
- On incident 430, Undo within the window put it back in the live feed ([screenshot](critical/c7-after-undo-light.png)); `/api/sos/active` then returned 430 with `resolved_at = null` and `reopened_at = 2026-09-25T14:41:34Z`.
- Both test incidents were then resolved as "Closed without reaching the boat"; after a reload the live feed no longer held them.

Result: C7 closes, with two limits.
The Undo toast lasts 10 s, and on the first try it had expired before the click, so a slow dispatcher falls back to Reopen in the Resolved Incidents panel.
The boat's own vessel feed (`GET /api/sos/vessel/{id}`) accepts only that vessel's device token (an operator token gets 401), and the emulator that raised 429/430 had been wiped, so the "vessel feed shows it active" half rests on `/api/sos/active` plus the backend tests, not a device read.
No dark-theme C7 screenshot: both test incidents were closed before it was taken, and the only other open incident belongs to a teammate.

Screenshots with a teammate's name and phone number were redacted before saving.

UI defects seen (owner Arnold, dashboard):

1. The "Gateway stale - last heard never" and "SMS escalation not configured" pills sit on top of the first KPI card's title and the calibration notice.
2. The resolve modal and the Resolved Incidents list print raw UTC ISO times ("Pressed 2026-09-25T14:17:23+00:00", "Resolved 2026-09-25T14:40:40.368420+00:00") instead of local time.
3. After Undo, the reopened incident shows in both the live feed and the Resolved Incidents list until the page reloads.
