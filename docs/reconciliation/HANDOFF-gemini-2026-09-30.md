# Brief for Gemini: fix the issues found on 2026-09-30

**Status:** COMPLETED - implemented by Gemini, reviewed and merged by Claude Code on 2026-10-01
**Written by:** Claude Code (spec author and reviewer), for Len
**Created:** 2026-10-01T00:40:00+08:00
**Branch:** `fix/reconcile-2026-09-30` (already created from `master` at `abc9093`; the commit that adds this file also adds the acceptance tests)
**Execution mode:** auto. Do all nine tasks in order without stopping for approval; stop only if the rules below make a task impossible.

## 1. What you are fixing and the sources you must follow

| Task | What | Source of truth |
|---|---|---|
| T1 | Restore the vessel-profile 409 rule that `e32c085` removed | `docs/05_PUBLIC_API.md`, "Profile overwrite rule" and its 2026-09-30 note |
| T2 | Nearby broadcast backend: savepoints and logging (G6, G12), cancel (G4), audit (G7), radius (G8) | `docs/73_SOS_NEARBY_BROADCAST_SPEC.md` Section 14.1 |
| T3 | Dashboard broadcast button and state line (G4, G11) | `docs/73` Section 14.2 |
| T4 | Put the SOS button back on Home (spec 64 D10) | `docs/64_FISHER_FRICTION_REDUCTION_SPEC.md` P1, FFR-07, D10 and Section 3.2 |
| T5 | Tell the fisher when the server refused a profile edit | Section 4 of this brief |
| T6 | Localized distance text, no "MDRRMO" in the notification (G9) | `docs/73` Section 14.3 "Wording" |
| T7 | Seen store, app-wide watcher, Home and Advisories banner (G2, G3) | `docs/73` Section 14.3 |
| T8 | Notification tap opens At sea (G10) | `docs/73` Section 14.3 "Notification tap" |
| T9 | Evidence and docs | Section 6 of this brief |

Read `AGENTS.md`, `CLAUDE.md`, the sources above and `docs/22_LOCALIZATION_PLAN.md` before editing.
Where a source and this brief disagree, stop and write the disagreement into `docs/reconciliation/EVIDENCE.md`; do not pick one yourself.
Out of scope: G1 (access rule of `GET /api/public/sos-nearby`), G5 (rate limit), plan 65 Phase 4 (the Home reorder), firmware, and anything not listed above.

## 2. Rules that decide whether your work is accepted

The reviewer (Claude Code) re-runs every command below on your final commit and compares the output with what you wrote.
One mismatch between your evidence and the re-run rejects the whole branch.

**Protected tests.** These files were written by the spec author before any code and are the acceptance criteria.
Do not edit, rename, move or delete them, and do not add skips to them:

- `backend/tests/test_sos_broadcast_pg.py`
- `backend/tests/test_vessel_profile_pg.py`
- `backend/tests/test_vessel_profile.py`
- `web/test/dashboard-broadcast-states.test.js`
- `mobile/test/nearby_sos_test.dart`
- `mobile/test/seen_broadcast_store_test.dart`
- `mobile/test/nearby_sos_watcher_test.dart`
- `mobile/test/nearby_help_banner_test.dart`
- `mobile/test/eta_notifier_payload_test.dart`
- `mobile/test/profile_push_result_test.dart`
- `mobile/test/home_sos_restore_test.dart`

The handoff commit is the one that added this file: `git log --diff-filter=A --format=%h -- docs/reconciliation/HANDOFF-gemini-2026-09-30.md`.
The reviewer checks the protected tests with `git diff <handoff commit> HEAD -- <each file>`, which must print nothing.
If you believe a protected test is wrong, leave it failing, finish everything else, and explain it in the evidence file with the exact failure output.
A red test honestly reported is acceptable; a test edited to go green is not.

**One exception.** `backend/tests/test_sos_broadcast.py` uses a fake database that matches SQL text, so your new SQL may break it.
You may change only its `_FakeConn` and `_FakePool` classes; every `def test_` function and every `assert` in it must stay byte-identical.

**Never:**

- Add `pytest.mark.skip`, `xfail`, `skip:` in Dart, `test.skip` or `todo` to any test, or delete or weaken an existing assertion anywhere.
- Run the final gate with `-k`, `--deselect`, a file list or `--lf`; the final gate is the whole suite.
- Make a test pass with code that only exists for the test: a `catch` that hides the real error, a branch keyed on a test value, dead code that satisfies a text match.
- Write a number you did not read from the terminal. Copy the summary lines; never retype or round them.
- Write "passed", "verified" or "works" for anything you did not run. Device-only checks you could not do are written `NOT VERIFIED - no device`.
- Push to `master`, merge, rebase published history, or force-push. Commit to `fix/reconcile-2026-09-30` only.
- Add an AI co-author line to a commit (`CLAUDE.md`).
- Use the em dash character in any file.

## 3. Setup and the red run (do this before changing any code)

The backend's database tests need the throwaway Postgres 18 cluster the reviewer created at `C:\pgprobe55432` (trust auth, port 55432).
If `pg_isready -h localhost -p 55432` says it is not accepting connections, start it:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D C:\pgprobe55432 -o "-p 55432" -l C:\pgprobe55432\server.log start
```

Run all five commands, each from the directory shown, and paste their final summary lines into `docs/reconciliation/EVIDENCE.md` under "Red run", with the output of `git rev-parse HEAD`:

```powershell
# backend/
$env:AQONE_PROBE_PG_ADMIN_URL = 'postgresql://postgres@localhost:55432/postgres'
python -m ruff check .
python -m pytest -q -p no:cacheprovider
# web/
node --test test/*.test.js
# mobile/
flutter gen-l10n
flutter analyze
flutter test
```

The red run must match the reviewer's red run of 2026-09-30 on this branch:

| Suite | Reviewer's red run |
|---|---|
| Backend ruff | `All checks passed!` |
| Backend pytest (with the probe URL) | `10 failed, 661 passed, 5 skipped, 1 xfailed`; the 10 are 8 in `test_sos_broadcast_pg.py`, `test_vessel_profile.py::test_register_rejects_overwrite_of_non_blank_identity_without_auth`, and `test_vessel_profile_pg.py::test_anonymous_overwrite_of_identity_is_rejected_and_nothing_changes` |
| Web | `tests 216`, `pass 213`, `fail 3` (all in `dashboard-broadcast-states.test.js`) |
| Mobile analyze | `51 issues found`, every one inside the seven new or changed test files, because the APIs they name do not exist yet |
| Mobile test | `+397 -7`; the 7 are the seven test files failing to load for the same reason |

If your red run differs, record the difference and stop; do not start T1.

## 4. The tasks

Commit once per task with the message given, after that task's own tests pass.
After each commit, add a dated entry to `EVIDENCE.md`: the commit hash, the exact commands you ran for that task, and their verbatim summary lines.

### T1 - restore the 409 rule

`git show e32c085 -- backend/app/api/vessel_profile.py | git apply -R` reverses the removal cleanly and keeps `touch_vessel` (it came from another commit); check the result reads correctly rather than trusting the patch.
Green when: `test_vessel_profile.py` and `test_vessel_profile_pg.py` pass.
Commit: `fix(backend): restore the vessel-profile overwrite rule (docs/05)`

### T2 - broadcast backend (docs/73 Section 14.1)

In `backend/app/api/sos.py` and `backend/app/api/public.py`:

- Wrap every `sos_broadcasts` statement in `async with conn.transaction():` (a savepoint inside the request's transaction) and on failure `logger.exception(...)` with `logger = logging.getLogger(__name__)`, then continue without the broadcast.
- Replace the bare `except Exception: return ...` blocks around the broadcast code and the two feed lookups with the same log-then-continue pattern.
- `AcknowledgeIn.broadcast_radius_km`: only 5, 10 or 20, else 422.
- `broadcast_enabled: false` cancels an active broadcast; reopen revives only `expired`; audit actions exactly as Section 14.1 names them.
- `GET /api/sos/active`: `broadcast_state` is the row's state or `off`.
- No new migration is needed (`state` is `TEXT`); if you conclude one is, add `041_...sql` and never edit an old migration.

Green when: all of `test_sos_broadcast_pg.py`, `test_sos_broadcast.py` and the rest of the backend suite pass, and ruff is clean.
Commit: `fix(backend): savepoint, log, cancel and audit nearby broadcasts (docs/73 G4 G6-G8 G12)`

### T3 - dashboard (docs/73 Section 14.2)

In `web/js/dashboard/dashboard-incidents.js`: implement the table in Section 14.2 exactly, including the button texts and state lines, and stop blanking `sos-broadcast-msg` after `renderBroadcastButton` in `openIncidentDrawer`.
The click sends `broadcast_enabled`, `responder_status`, `expected_version` and, for enabling, `broadcast_radius_km: 10`, and never `eta_minutes`.
Green when: `node --test test/*.test.js` passes with 0 failures and every `.js` under `web/js` and `web/test` passes `node --check`.
Commit: `fix(web): stop and show cancelled nearby broadcasts in the SOS drawer (docs/73 G4 G11)`

### T4 - SOS back on Home (spec 64 D10)

`git show 546a38c -- mobile/lib/ui/home_page.dart | git apply -R` restores the Home SOS control, its `sosAlarm` parameter and its flow; it applies cleanly on this branch.
Keep the At sea SOS and Jade's Venture tests; SOS must work from both screens.
Green when: `home_sos_restore_test.dart` and the existing `widget_test.dart` pass.
Commit: `fix(mobile): restore the SOS button on Home (docs/64 D10)`

### T5 - refused profile edits

This is the handset half of Len's 2026-09-30 decision in `docs/05`.

- In `mobile/lib/services/backend_client.dart` add `enum ProfilePushResult { accepted, needsPairing, failed }`.
  `registerVesselProfile` returns it and never throws: `200` is `accepted`; `409` and `401` are `needsPairing`; any other status, a timeout or an exception is `failed`.
- `mobile/lib/ui/profile_page.dart` `_save` awaits the result.
  On `needsPairing` it shows a SnackBar with the new ARB key `profileSavedOnPhoneOnly` (English: `Saved on this phone only. The rescue centre still has your old details. Pair this phone to update them.`) and an action `profilePairPhone` (`Pair`) that opens the same `EnrolmentPage` route as the settings tile.
  Otherwise it keeps today's `profileUpdated` message.
- The other two callers (`main.dart`, `sos_service.dart`) stay fire-and-forget and ignore the result.
- Add both keys to `app_en.arb` with `@` descriptions and draft `fil` and `akl` entries (drafts are unreviewed, `docs/22`).
- Write your own widget test `mobile/test/profile_pairing_prompt_test.dart`: a `MockClient` answering 409 makes the SnackBar text and the `Pair` action appear after Save; a 200 does not.

Green when: `profile_push_result_test.dart` and your new test pass.
Commit: `fix(mobile): tell the fisher when the server kept the old profile`

### T6 - wording (docs/73 G9)

`NearbySos.distanceText(double? km, AppLocalizations t)`; new ARB keys for metres and kilometres; update every caller so "away" is added once by `nearbyHelpAway`; reword `nearbyHelpNotifTitle` and `nearbyHelpNotifBody` in `en`, `fil` and `akl` without "MDRRMO".
Green when: `nearby_sos_test.dart` passes.
Commit: `fix(mobile): localize nearby distance and drop MDRRMO from the alert (docs/73 G9)`

### T7 - seen store, watcher and banner (docs/73 G2, G3)

Build `SeenBroadcastStore` (database version 16), `NearbySosWatcher` and `NearbyHelpBanner` with exactly the signatures in Section 14.3.
Move nearby polling, the alarm, the notification and the first-sighting dialog out of `venture_page.dart` into the watcher and the shell (`app_shell.dart`), so they run before At sea is ever opened.
At sea keeps its container and markers, reading the watcher.
Give `HomePage` and `AdvisoriesPage` the `nearby` and `onOpenNearby` parameters and the banner.
Green when: `seen_broadcast_store_test.dart`, `nearby_sos_watcher_test.dart` and `nearby_help_banner_test.dart` pass, and no other mobile test regresses.
Commit: `feat(mobile): app-wide nearby watcher, seen store and Home banner (docs/73 G2 G3)`

### T8 - notification tap (docs/73 G10)

Add the `EtaNotifier` members named in Section 14.3, pass the payload in `showNearbyHelp`, call `handleNotificationPayload` from `onDidReceiveNotificationResponse` and from the launch details, and make the shell open At sea centred on the broadcast.
Green when: `eta_notifier_payload_test.dart` passes.
Device check (only if you have an Android device or emulator with the backend): trigger a broadcast, put the app in the background, tap the notification, and save a screenshot of At sea centred on the red marker as `docs/reconciliation/g10-notification-tap.png`.
Without one, write `G10 device check: NOT VERIFIED - no device`.
Commit: `feat(mobile): nearby notification tap opens At sea (docs/73 G10)`

### T9 - evidence and docs

- Tick in `docs/74_SOS_NEARBY_BROADCAST_IMPLEMENTATION_PLAN.md` Phase 1b only the items whose tests pass in your final gate.
- In `docs/05_PUBLIC_API.md`, change each "Approved 2026-10-01, not built yet" note that you built to "Built 2026-10-01 (`<commit>`)".
- Add a dated entry at the top of `docs/08_DEMO_AND_STATUS.md` with the final gate lines and the NOT VERIFIED list.
- In `docs/README.md` Current Register, update the "2026-09-30 reconciliation" and "Plan 74" rows to what is now true, naming your branch and final commit.
- Update the root `HANDOFF.md` (template `.agents/templates/docs/HANDOFF.md`): Status `ACTIVE`, the Baton "Claude reviews `fix/reconcile-2026-09-30` at `<commit>`".
Commit: `docs: record the 2026-09-30 reconciliation fixes`

## 5. Final gate

Run the five commands from Section 3 again on your last commit, plus:

```powershell
# repository root
git diff --stat abc9093 HEAD
git status --short
# web/
Get-ChildItem js, test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

Accepted only when: ruff clean; backend pytest `0 failed` with the probe URL set; web `fail 0`; `flutter analyze` `No issues found!`; `flutter test` `All tests passed!`; `git status --short` empty.
Skipped and xfailed counts must equal the red run (5 skipped, 1 xfailed); if they changed, explain why.

## 6. The evidence file

`docs/reconciliation/EVIDENCE.md`, newest entry last, one entry per task plus "Red run" and "Final gate".
Each entry has: the timestamp with `+08:00`, `git rev-parse HEAD`, each command exactly as run, and its summary lines copied verbatim in a code block.
End the file with a "Not verified" list: every device-only check you did not do, and anything you left red with its reason.
Your closing message to Len is a copy of the "Final gate" and "Not verified" sections, nothing more optimistic.

## 7. What the reviewer will do

1. Confirm `git diff <handoff commit> HEAD` is empty for every protected test, and that `test_sos_broadcast.py` changed only inside its fake classes.
2. Re-run Section 5 and compare every summary line with `EVIDENCE.md`.
3. Read the diff for test-only code paths, swallowed errors, and behaviour that differs from `docs/73` Section 14 or this brief.
4. Merge to `master` only after all three pass.
