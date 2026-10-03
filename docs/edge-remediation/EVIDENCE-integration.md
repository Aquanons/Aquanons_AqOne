# Evidence: Integration walkthrough (Phase I)

Plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` Phase I.
Walkthrough steps C3, C6, C7 and C9 were moved to plan 66 and are recorded in [`EVIDENCE-critical.md`](EVIDENCE-critical.md); they are not repeated here.
Observed results only; no data, URLs or credentials.

## 2026-10-03 - Suite gates

Commit: `b7bf4a8` (`origin/staging`, which is `master` `396b982` plus the shore firmware fixes of PR #89), in the worktree `../AqOne-edge-integration`.
`AQONE_PROBE_PG_ADMIN_URL` pointed at a disposable PostgreSQL 18 cluster on port 55432.

| Gate | Result |
| --- | --- |
| Backend `python -m ruff check .` | `All checks passed!` |
| Backend `python -m pytest -q` | `674 passed, 5 skipped, 1 xfailed in 147.48s` |
| Web `node --test test/*.test.js` | `tests 218`, `pass 218`, `fail 0` |
| Web `node --check` on every `.js` in `web/js` and `web/test` | 40 files, 0 failures |
| Mobile `flutter analyze` | `No issues found!` |
| Mobile `flutter test` | `+426: All tests passed!` |

Not run: the firmware gate (`pio run -d firmware`).
Plan 62 Phase I does not list it, and firmware evidence belongs to plan 66.

## 2026-10-03T19:01-19:04+08:00 - Walkthrough of M8, M9, H15 and H18

Environment: the backend from this worktree (`uvicorn` on port 8765) against an empty, freshly migrated database (migrations up to 040) on the disposable cluster, with one operator account created through `POST /api/admin-signup`.
The dashboard (`/html/dashboard.html`) ran in headless Microsoft Edge at 1280 x 900, driven by `playwright-core` with real clicks and `--autoplay-policy=document-user-activation-required` (the normal browser rule).
An init script counted `OscillatorNode.start()` and `stop()` calls, so "rings" is measured, not assumed.
Every SOS was sent to the real `POST /api/sos` with no credential, as a phone on the direct path does.
All vessel names are test names (`PHI-*`, `ANON-*`).

No phone or emulator took part.
The fisher's side of M9 was sent as the two HTTP requests the handset makes, not tapped in the app.

### H15 - an old SOS arrives late

An SOS with `client_ts` 3 days 4 hours 10 minutes in the past was posted.

- `GET /api/sos/active` returned it with `is_late = true` and `pressed_at` equal to the press time, not the arrival time.
- The Alerts row showed the badge "LATE - pressed 3 d 4 h ago" and the time "76 hours 10 minutes ago" ([screenshot](integration/h15-late-badge-light.png)).
- The call was listed as ACTIVE; it was not dropped.

Result: pass.

### M8 - two tabs acknowledge the same call

Two dashboard tabs opened the acknowledge dialog for the same incident while it was at `version` 0.

| Step | HTTP | Incident after |
| --- | --- | --- |
| Tab A confirms with a 25 minute ETA | 200 | `version` 1, ETA 25 min |
| Tab B confirms with a 60 minute ETA | 409 | unchanged: `version` 1, ETA 25 min |
| Tab B presses "Confirm again" | 200 | `version` 2, ETA 60 min |

After the 409, tab B kept its dialog open, showed "Answered by (operator) at (time): Rescue boat on the way, ETA (time). Review and confirm again." and renamed the button to "Confirm again" ([screenshot](integration/m8-conflict-prompt-light.png)).
The first answer was not overwritten silently.

Result: pass.

### M9 - a fisher stands down by mistake, then undoes it

Run on an empty feed, with the alarm sound unlocked, so the siren state is unambiguous.

| Moment | Oscillator starts | Oscillator stops | In the live feed |
| --- | --- | --- | --- |
| Empty feed | 0 | 0 | no |
| SOS arrives | 1 | 0 | yes |
| `SAFE_NOW` (`reply = 2`) on `POST /api/sos/reply/{local_id}` | 1 | 1 | no |
| `STILL_IN_DANGER` (`reply = 1`), 5 s later | 2 | 1 | yes |

- After `SAFE_NOW`, `GET /api/sos/recent` showed the incident with `resolution_code = stood_down_by_fisher`.
- After `STILL_IN_DANGER`, `GET /api/sos/active` showed `resolved_at = null`, `resolution_code = null` and a new `reopened_at`.
- The dashboard rang again, showed an "SOS received" toast, changed the tab title to `SOS - PHI-M9`, and marked the row "Fisher reports: STILL IN DANGER" ([screenshot](integration/m9-reopened-realarm-light.png)).
- The audit table holds one `sos.reopen` row with `{"reopened_by": "fisher"}`.

Result: pass for the backend and the dashboard.
`Pending - Len: on a phone or emulator, raise an SOS, tap "I am safe", then tap the undo, and confirm the dashboard rings again.`
The handset's undo is covered only by the widget test "undo stand-down".

### H18 - 500 anonymous calls, one known vessel

One vessel was given trip history through `POST /api/v1/trips` and raised an SOS.
Then 500 SOS from 500 unknown vessel IDs were posted in 1.5 s (all 500 returned `created = true`).

- `GET /api/sos/active?limit=200` returned `total = 504`, 200 events, and `flood = {"unknown_vessels_last_minute": 503, "active": true}`.
  The 503 is the 500 flood calls plus the three unknown test vessels from the steps above, all inside the same minute.
- The known vessel was `events[0]`, above every flood call, although its call was older.
- The dashboard showed the banner "High call volume - 503 calls from unknown vessels in the last minute.", the known vessel as the first row, 200 rows, and "+304 more" under the list ([light](integration/h18-flood-known-on-top-light.png), [dark](integration/h18-flood-known-on-top-dark.png)).

Result: pass.

### Browser console

One console entry in the whole run: the browser's own "Failed to load resource: 409" line for tab B in M8, which is the expected conflict.
No script error.

## Deployed checks

- `https://aqone-backend.onrender.com/health/ready` returned `status: ok` on commit `396b982` (2026-10-03).
- `GET /api/ops/status` needs an operator session, and the agent holds no production credential, so the deployed half was not read.
  On the local stack it returned `sms_configured: false`, `db_days_left: null` (`DB_EXPIRES_AT` unset locally) and both scheduler jobs with a last-run time.
  `Pending - Len: sign in to the deployed dashboard and confirm /api/ops/status shows db_days_left and the SMS status.`
- Escalation SMS: not configured, as already recorded in `EVIDENCE-critical.md` (2026-09-25); no SMS was sent.
- `Pending - Len: build a release APK and run the M2 foreground-service device test (EVIDENCE-mobile.md, line "release build on target phone").`

## UI defects seen (owner Arnold, dashboard)

None of these were changed; this branch holds documents only.

1. **The Live SOS count stops at 200 during a flood.**
   With 504 open calls, the "LIVE SOS" card, its "200 UNACKNOWLEDGED SOS" pill and the Alerts tab badge all showed 200.
   The true figure appears only as "+304 more" under a 200-row list, which a dispatcher has to scroll to find.
   The feed already returns `total`.
2. **The M8 conflict prompt prints raw UTC timestamps** ("at 2026-10-03T11:01:48.698071+00:00 ... ETA 2026-10-03T11:26:48.698071+00:00") instead of local time.
   This is the same class as defect 2 in `EVIDENCE-critical.md`.
3. **The "SOS received" toast is green**, the colour of a success message, for a distress call.
