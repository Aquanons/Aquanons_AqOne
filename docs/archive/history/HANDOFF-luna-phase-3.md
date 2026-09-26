# Handoff for Luna: fisher friction plan, Phase 3 (readable in the sun)

**Status:** COMPLETE - merged to `master` 2026-09-26 as `186e231`; archived 2026-09-26 (completed handoff, kept as the delivery record)
**Owner:** GPT 5.6 Luna (implementer), Claude Code (reviewer), Len (merge)
**Created:** 2026-09-26
**Updated:** 2026-09-26
**Related:** `docs/65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md` Phase 3, `docs/64_FISHER_FRICTION_REDUCTION_SPEC.md` P3, P4, FFR-04, FFR-08, FFR-11, findings F5, F7, F8, `docs/47_VISUAL_DESIGN_GUIDE.md`

## What you are doing

Implement Phase 3 of plan 65 and nothing else: text and icons a fisher can read in bright sun, no text below 12 sp, an SOS status card on Home that is never cut short, and a bottom bar with four labelled destinations.
The failing tests are written; make them pass without changing them.
Plan 65 is `hard-stop`: when Phase 3 is verified and committed, stop and report.
Len moved Phase 3 ahead of Phase 2 on 2026-09-26, because it needs no new wording.

Why it matters: fishermen read the phone on a moving boat in direct sun.
Today the light theme's grey text is about 2.6:1 against white (the floor is 4.5:1), most SOS status icons are too faint on white, 39 text styles are below 12 px, the SOS status on the map is cut to one line, and two of the four destinations have no visible label.

## Where you work

| Item | Value |
|---|---|
| Worktree | `../AqOne-fisher-ux`; its own `HANDOFF.md` holds live state |
| Branch | `ux/fisher-friction`, fast-forwarded to `master`, with the Phase 3 failing tests cherry-picked on top |
| Allowed paths | `mobile/**`, `docs/fisher-ux/**`, `docs/47_VISUAL_DESIGN_GUIDE.md` (the rows for changed tokens), plan 65 Phase 3 checkboxes, the worktree `HANDOFF.md` |
| Not yours | `backend/`, `firmware/`, `web/`, other docs; `AqOne_Story_and_Data_Flow.md` and `docs/68_*` (never stage) |

## Read first

1. `AGENTS.md` (localization rules, Ponytail rules, no em dashes, no agent co-author).
2. Plan 65 Phase 3 and spec 64 Section 4 (P3, P4) and Section 5 (FFR-04, FFR-08, FFR-11).
3. The two test files below.

## The failing tests (do not edit them)

| Test file | What it pins down |
|---|---|
| `mobile/test/readability_tokens_test.dart` | In both `AqPalette.light` and `AqPalette.dark`: `primaryText`, `secondaryText` and `dimText` are at least 4.5:1 on `canvas` and on `surface`; `primaryText` is at least 7:1 on `surface`; every `FisherSosSituation.color` is at least 3:1 on `surface` |
| `mobile/test/readability_screens_test.dart` | No text below 12 sp (icons excluded) on Home, At sea, the SOS countdown, the post-SOS sheet, `DeliveryStateTile`, `BuoyStatusCard` and `SquallBanner`; on a 360 x 640 phone at 200% text, in light and dark: Home raises no overflow and shows one `SosStatusCard` whose title is at least 20 sp and whose description has no `maxLines` and no ellipsis; the countdown and the post-SOS sheet raise no overflow; `AppShell` shows the four labels `navHome`, `navVenture`, `navAdvisories` and `navProfile`, each at least 12 sp and at least 4.5:1 on the light `surface` |

Today they fail for exactly those reasons (`readability_screens_test.dart` also fails to load until `mobile/lib/ui/widgets/sos_status_card.dart` exists).
If a test looks wrong after you understand it, stop and write why in the worktree `HANDOFF.md`; do not change it.

## Tasks

1. **Tokens** (`mobile/lib/core/tokens.dart`):
   - Light `dimText` and `secondaryText`, and dark `dimText`, reach 4.5:1 on their `canvas` and `surface`.
   - The status colours used by `FisherSosSituation` (`AqColors.warning`, `connectivity`, `success`, or new ones) reach 3:1 on both the white and the dark `surface`.
     A colour passes on both only if its relative luminance sits roughly between 0.17 and 0.30 (for example amber `#D97706`, cyan `#0891B2`, green `#16A34A`).
   - Keep one set of tokens; no new theme mode.
   - Update the matching rows in `docs/47_VISUAL_DESIGN_GUIDE.md`.
2. **Font floor**: raise every `fontSize` below 12 in `mobile/lib/ui` to at least 12, and body text to 16 where it is body text.
   The test walks the screens it can build; also clear the ones it cannot reach (`weather_card.dart` has 10, `advisory_card.dart` 6, `chathubb.dart` 5), checked by the grep under "Done when".
3. **SOS status card** (`mobile/lib/ui/widgets/sos_status_card.dart`, class `SosStatusCard`):
   - Takes one `SosRecord` and draws the `FisherSosSituation` icon, colour, title (at least 20 sp) and description (wraps, never cut), in `primaryText` on `surface`.
   - Home shows it near the top, under the squall banner, whenever the newest SOS is open (its situation is neither `closed` nor `cancelled`).
   - Keep "Your messages" and `DeliveryStateTile` as they are; At sea keeps its pill until Phase 4b replaces it.
4. **Labelled dock** (`mobile/lib/ui/app_shell.dart`, `_MobileDock` and `_DockItem`):
   - Four destinations with icon and visible label: Home, the raised At sea button (label under it), Advisories, Profile (the avatar shortcut on Home stays).
   - Labels at least 12 sp, inactive colour at least 4.5:1 on the dock background, active item marked by weight or an indicator as well as colour.
   - The wide-screen sidebar already has all four; leave it.
5. **Large text**: replace fixed sizes that clip at 200% text with minimum sizes (`ActionPill` 176 x 50, dock `barHeight`), and make the SOS countdown and the post-SOS sheet fit a 360 x 640 phone at 200% (the sheet overflows by 164 px today; scrolling is fine).
6. **Wording stays**: no ARB value changes in this phase (Phase 2 owns wording); new text, if any, goes in `app_en.arb` with an `@` description and `fil` and `akl` drafts.

## Rules

- No new dependency; no comments unless the why is not obvious; no em dashes.
- UI text only through `AppLocalizations`; no display text on enums.
- Every existing test keeps passing, including `pitch_mode_test.dart`, `weather_card_test.dart` and the Phase 1 and countdown tests.
- Three-attempt limit from `AGENTS.md`.

## Setup notes

- Run `flutter pub get` in `mobile/` if `.dart_tool` is missing.
- The worktree's `mobile` folders had the Windows read-only attribute; it was cleared on 2026-09-26. If `flutter build` fails deleting `mergeDebugAssets`, clear it again (`attrib -R`).
- The Android SDK is at `%LOCALAPPDATA%\Android\Sdk` (not on PATH): `emulator\emulator.exe -avd Medium_Phone` and `platform-tools\adb.exe`. The emulator needs about 3 GB of free memory; if it is not available, say so in the evidence file.

## Done when

- [ ] `cd mobile && flutter analyze` prints "No issues found!".
- [ ] `cd mobile && flutter test` passes in full, with the two Phase 3 test files unedited (`git log master..HEAD --format=%s -- mobile/test` lists only `test(mobile): failing tests for plan 65 Phase 3 (readable in the sun)`).
- [ ] `grep -rnE "fontSize: ([0-9]|1[01])(\.[0-9]+)?[,)]" mobile/lib/ui` returns nothing.
- [ ] `docs/fisher-ux/PHASE_3_VERIFICATION.md` has the commands and pass counts, and emulator screenshots of Home with an open SOS and of At sea, light and dark, at the largest system font (`docs/fisher-ux/phase-3/`), or a note saying why screenshots could not be taken.
- [ ] Plan 65 Phase 3 task and verification boxes ticked.
- [ ] One commit on `ux/fisher-friction`: `feat(mobile): sun-readable tokens, font floor, labelled dock`, no agent co-author line. Do not push or merge.
- [ ] Worktree `HANDOFF.md` set to COMPLETED with the evidence; then stop (hard-stop).
