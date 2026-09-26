# Plan 70 evidence: Aklanon first

Plan: `docs/70_AKLANON_FIRST_IMPLEMENTATION_PLAN.md` Revision 2.
Branch `feat/aklanon-first`, worktree `../AqOne-aklanon`.
Baseline on `886c3df`: `flutter analyze` clean, `flutter test` 379 passed.

## Phase 1: Aklanon by default (2026-09-26)

- Red first: `test/aklanon_default_test.dart` failed to compile against the old `Locale? locale`.
- The new launch test found a real layout bug: in Aklanon the onboarding "remember this device" row overflowed its 420 px card by 9.5 px (`RenderFlex overflowed`), because the label had no `Flexible`. Fixed in `onboarding_page.dart`.
- `flutter test test/aklanon_default_test.dart test/localization_test.dart`: 12 passed.
- `flutter analyze`: No issues found.
- `flutter test`: 381 passed (379, minus the three deleted `resolveLocale` tests, plus the five new ones).
- What the tests prove: with no stored choice and the device set to `en_US`, `AqOneApp` builds onboarding in `akl`; a stored `en` launches in English; the SOS notification text resolves to the `akl` ARB value; Flutter chrome in `akl` is the Tagalog `cancelButtonLabel`.
- Not yet done: the emulator check is folded into the Phase 5 walkthrough, which starts from a fresh install on an English-language emulator.
