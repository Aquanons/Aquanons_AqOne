# Handoff for Luna: the SOS countdown that froze

**Status:** ACTIVE
**Owner:** GPT 5.6 Luna (implementer), Claude Code (reviewer), Len (merge)
**Created:** 2026-09-26
**Updated:** 2026-09-26
**Related:** `docs/edge-remediation/EVIDENCE-critical.md` (C3 run, 22:08 on 2026-09-25), `mobile/lib/ui/sos_flow.dart`, `mobile/test/sos_countdown_freeze_test.dart`

## What went wrong

On 2026-09-25 the SOS countdown froze at "1" on an emulator and never sent anything.
The countdown's own state said it had finished (`_resolved = true`, timer cancelled), yet its route was still on top and idle, the outbox was empty, and the slide-to-cancel did nothing.
A fisher in that state is stuck on "Sending SOS" with nothing sent.

## Root cause (reproduced in widget tests, 2026-09-26)

Both defects are in `mobile/lib/ui/sos_flow.dart` and were already in the older copies on `master`.

1. **The countdown closes the wrong screen.**
   `_SosCountdownScreenState._finish` calls `Navigator.of(context).pop(dispatch)`, which closes whatever route is on top, not the countdown itself.
   If anything opens above the countdown during its 5 seconds (the RETURN NOW squall page, the rescue ETA dialog or the unsent-SOS prompt, all pushed by `AppShell` on the root navigator), that route is closed instead.
   The countdown stays on screen with `_resolved = true`, its `showGeneralDialog` future never completes, and no SOS is raised.
2. **Two quick taps open two countdowns.**
   `handleSosTap` checks `isSending`, then awaits `SharedPreferences.getInstance()`, and only then calls `setSending(true)`.
   A second tap that lands before that await returns starts a second countdown.
   When the first countdown finishes it closes the second one (defect 1), the second flow goes on to raise the SOS, and the first countdown is left frozen on top.

Which of the two happened on 2026-09-25 is not known; each produces exactly the recorded state.
The emulator run was not repeated (memory was short), so the fix is proven by the widget tests below and one device check.

## The failing tests (do not edit them)

`mobile/test/sos_countdown_freeze_test.dart`:

| Test | Asserts |
|---|---|
| a route opened on top of the countdown does not stop the SOS and is not closed by it | After 5 s the countdown's future completes with `true`, the countdown is gone, and the dialog opened on top is still there |
| two quick taps on SOS open one countdown, not two | Two taps delivered before the app gets a turn produce exactly one `SosCountdownScreen` |

Both fail today for the reasons above.

## What to change

- `_finish` removes its own route, whatever is above it: take `ModalRoute.of(context)` and pop it if it is current, otherwise remove that route with the result (`Navigator.removeRoute`).
  Keep the single-use guard, so a second call does nothing.
- `handleSosTap` marks itself as sending before its first `await` (set the flag, then read the silent setting), so a second tap sees it and returns.
  Keep every other behaviour of the flow identical.
- No new dependency, no change to the four Phase 1 test files, no wording changes.

## Done when

- [ ] `cd mobile && flutter test test/sos_countdown_freeze_test.dart` passes unedited.
- [ ] `cd mobile && flutter analyze` prints "No issues found!" and `flutter test` passes in full.
- [ ] Device or emulator check, recorded in `docs/fisher-ux/COUNTDOWN_FREEZE_VERIFICATION.md`: a fast double tap on SOS shows one countdown and sends one SOS; the result and the build commit are noted.
- [ ] One commit on `ux/fisher-friction`: `fix(mobile): SOS countdown closes only itself and ignores a second tap`, no agent co-author line; do not push or merge.
- [ ] Worktree `HANDOFF.md` updated, then stop.
