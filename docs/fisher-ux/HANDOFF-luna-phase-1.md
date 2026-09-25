# Handoff for Luna: fisher friction plan, Phase 1

**Status:** ACTIVE
**Owner:** GPT 5.6 Luna (implementer), Claude Code (reviewer), Len (merge)
**Created:** 2026-09-25
**Updated:** 2026-09-25
**Related:** `docs/65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md` Phase 1, `docs/64_FISHER_FRICTION_REDUCTION_SPEC.md` Sections 2.4 and 5, `docs/06_DELIVERY_STATES.md`

## What you are doing

Implement Phase 1 of plan 65 and nothing else: an honest post-SOS sheet, no hidden silent SOS on a long press, one `FisherSosSituation` model, and one shared SOS flow.
The failing tests are already written; your job is to make them pass without changing them.
Plan 65 is `hard-stop`: when Phase 1 is verified and committed, stop and report.

Why it matters: right after an SOS, the app shows a green check and "SOS sent for {boat}" while the SOS is still only saved on the phone (spec 64 finding F1).
A fisher who reads that believes help is coming when nobody has the message.
That breaks the honesty rule in `docs/06`, the product's own definition of done.

## Where you work

| Item | Value |
|---|---|
| Worktree | `../AqOne-fisher-ux` (sibling of the main checkout); its own `HANDOFF.md` holds live state |
| Branch | `ux/fisher-friction`, rebased on `master`; never work on `master` |
| Allowed paths | `mobile/**`, `docs/fisher-ux/**`, plan 65 Phase 1 checkboxes, and the worktree `HANDOFF.md` |
| Not yours | `backend/`, `firmware/`, `web/`, other docs; `AqOne_Story_and_Data_Flow.md` (never stage it) |

Plan 66 (Critical edge cases) is running in the main checkout at the same time.
It does not touch the mobile files below, so the two do not collide; do not edit its files.

## Read first

1. `AGENTS.md` (localization rules, Ponytail rules, no em dashes, no agent co-author).
2. Plan 65 Phase 1 and spec 64 Sections 2.4 and 5 (FFR-01, FFR-02, FFR-03).
3. The four test files in the next section.

## The failing tests (do not edit them)

| Test file | What it pins down |
|---|---|
| `mobile/test/fisher_sos_situation_test.dart` | Mapping from `SosRecord` to situation, honesty invariants, distinct icons, non-empty distinct text in `en`, `fil`, `akl` |
| `mobile/test/sos_flow_honesty_test.dart` | The post-SOS sheet shows `notSentYet` with no check icon and no "SOS sent" or "gone out"; it follows a `ValueListenable<SosRecord>` while open; same in `fil` and `akl`; `DeliveryStateTile` shows `cancelled` and `cancelling` |
| `mobile/test/widget_test.dart` | `EmergencyDetailsSheet(record: ...)` comes from `ui/sos_flow.dart`; a 4 s press on SOS starts the alarm and opens `SosCountdownScreen` |
| `mobile/test/localization_test.dart` | No bare `Text('...')` literal in `venture_page.dart`, `home_page.dart` or `sos_flow.dart` |

Today they fail to load only because `lib/models/fisher_sos_situation.dart` and `lib/ui/sos_flow.dart` do not exist.
If a test looks wrong after you understand it, stop and write why in the worktree `HANDOFF.md`; do not change it.

## Tasks

1. **`mobile/lib/models/fisher_sos_situation.dart`** (pure, no Flutter widgets except `IconData` and `Color`):
   - `enum FisherSosSituation { notSentYet, podHasIt, podNotConfirmed, rescueCentreHasIt, helpComing, cancelling, cancelled, closed }` with final `icon` and `color` fields, one distinct icon each.
     `notSentYet`, `podHasIt` and `podNotConfirmed` must not use `AqColors.success` or any check or cloud-done icon.
   - `static FisherSosSituation of(SosRecord record, {DateTime? now})`, first match wins:
     `resolvedAt != null` gives `closed`; `fisherReply == 2 && fisherReplySynced` gives `cancelled`; `fisherReply == 2` gives `cancelling`; `etaAt != null` or `acknowledged` gives `helpComing`; `delivered` gives `rescueCentreHasIt`; `relayed` older than `podDeliveryDeadline` (from `delivery_policy.dart`, measured from `relayedAt`) gives `podNotConfirmed`; `relayed` gives `podHasIt`; `saved` gives `notSentYet`.
   - `extension FisherSosSituationL10n on FisherSosSituation` with `title(AppLocalizations t)` and `description(AppLocalizations t)`, reusing existing keys only (new wording is Phase 2):

     | Situation | title | description |
     |---|---|---|
     | notSentYet | `deliveryStateSavedTitle` | `deliveryStateSavedDescription` |
     | podHasIt | `deliveryStateRelayedTitle` | `deliveryStateRelayedDescription` |
     | podNotConfirmed | `deliveryStateRelayedTitle` | `sosPodNotConfirmed` |
     | rescueCentreHasIt | `deliveryStateDeliveredTitle` | `deliveryStateDeliveredDescription` |
     | helpComing | `deliveryStateAcknowledgedTitle` | `deliveryStateAcknowledgedDescription` |
     | cancelling | `standDownPendingTitle` | `standDownPendingDescription` |
     | cancelled | `standDownTitle` | `standDownDescription` |
     | closed | `resolvedTitle` | `resolvedDescription` |

2. **`mobile/lib/ui/sos_flow.dart`**: move `SosCountdownScreen`, `EmergencyDetailsSheet`, `_SlideToAction` and `_EmergencyType` out of `venture_page.dart`, and add one shared function for the tap, countdown, `raiseSos` and sheet sequence that `HomePage` and `VenturePage` both call.
   Today that sequence is copied in `home_page.dart` (`_handleSosTap`, `_runSosCountdown`, `_showEmergencyDetailsSheet`) and `venture_page.dart`; afterwards `_handleSosTap` exists once in `mobile/lib`.
   Keep behaviour otherwise identical: silent setting, alarm start and stop, "SOS cancelled" snackbar, `StateError` snackbar, stand-down snackbar with Undo, Venture's `_latestSos` update.
3. **`EmergencyDetailsSheet`** takes `required ValueListenable<SosRecord> record` instead of `boat`.
   Its header shows the situation's icon, colour and title, plus the boat name from the record, and rebuilds when the listenable changes.
   The shared flow feeds it: a `ValueNotifier<SosRecord>` updated from `SosService.changes` (re-read the record by `localId`), disposed when the sheet closes.
4. **Honest keys**: stop using `sosSentForBoat` and `sosWhatsWrongNotice`.
   Add a key for the optional note line that is true in every state (for example "What's wrong? Optional. This is added to your SOS."), with an `@` description in `app_en.arb` and drafts in `app_fil.arb` and `app_akl.arb`; delete the two old keys from all three files if nothing else uses them; regenerate with `flutter gen-l10n`.
5. **No silent hold**: remove `onHold` and its timer from `ActionPill` and both call sites, and delete the "hold the SOS button for 3 seconds" sentence from `settingsSilentSosDescription` in all three ARB files.
   Silent SOS stays a Profile setting.
6. **One status model on screen**: `_buildSosStatus` in `venture_page.dart` and `DeliveryStateTile` take title, description, icon and colour from `FisherSosSituation` instead of deriving them.
   Keep the tile's existing extras (position, buoy hop, note, responder, ETA countdown, last attempt, "Still in danger?" line).

## Rules

- `mobile/lib` UI text goes through `AppLocalizations`; no bare `Text('...')`; no display text on enums.
- No new dependency; no comments unless the why is not obvious; no em dashes in code, ARB or docs.
- Do not touch `docs/06` or any delivery-state wording in Phase 1.
- Slides stay as they are; replacing them is Phase 4.
- Three-attempt limit from `AGENTS.md`: after three failed fixes of the same problem, stop and write it up.

## Setup gotchas

- Run `flutter pub get` in `mobile/` first; the worktree starts without `.dart_tool`.
- If `flutter gen-l10n` or `flutter build` refuses to write into `mobile/lib/l10n`, the Windows read-only attribute is set: `attrib -R mobile\lib\l10n` (and on any other `mobile\lib` folder it complains about).

## Done when

- [ ] `cd mobile && flutter analyze` prints "No issues found!".
- [ ] `cd mobile && flutter test` passes in full, including the four files above, unedited (`git log master..HEAD --format=%s -- mobile/test` lists only `test(mobile): failing tests for plan 65 Phase 1`).
- [ ] `grep -rn "_handleSosTap" mobile/lib` shows one definition; `grep -rn "onHold" mobile/lib` shows nothing.
- [ ] `docs/fisher-ux/PHASE_1_VERIFICATION.md` has the commands and pass counts, and one emulator screenshot of the post-SOS sheet raised with no pod reachable (`docs/fisher-ux/phase-1/`).
- [ ] Plan 65 Phase 1 task and verification boxes ticked.
- [ ] One commit on `ux/fisher-friction`: `fix(mobile): honest post-SOS sheet, no hidden silent hold, one SOS situation model`, no agent co-author line.
      Do not push, do not merge; Len merges after Claude's review, and not during RSTW (2026-10-01 to 03).
- [ ] Worktree `HANDOFF.md` set to COMPLETED with the evidence; then stop (hard-stop, no Phase 2).
