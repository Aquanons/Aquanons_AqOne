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

## Phase 2: Dead English deleted (2026-09-26)

- Deleted `checklist_page.dart`, `checklist_store.dart`, `checklist_item.dart`, `brand_header.dart`, `HotspotSurface.ageLabel`, the `checklist` parameter chain and 12 unused ARB keys.
- `flutter analyze`: No issues found.
- `flutter test`: 380 passed (381 minus the `ageLabel` test).
- `grep -rn "Checklist\|BrandHeader\|ageLabel" mobile/lib mobile/test` outside `lib/l10n`: only `_createChecklistItems` in `app_database.dart`, kept on purpose (the table stays).
- Found and left alone: `VentureFeeds.hotspots()` has no caller since the legend chip was removed (`d26f49e`); the heatmap is back in scope, so that is a product call, not dead code to cut here.

## Phase 3: UI literals localized (2026-09-26)

- Red first: the widened bare-literal check in `localization_test.dart` listed 30 literals across `lib/ui`, and the new key-parity check failed on seven Aklanon values still in English.
- 79 new keys in `app_en.arb` (each with an `@` description; 15 tagged SAFETY CRITICAL) and `app_akl.arb`; the four `InfoCopy` texts are now ARB keys; `InfoCopy` is gone.
- One shared age helper (`lib/ui/widgets/age_text.dart`) replaces the three hand-rolled "N min ago" formatters; the offline map banner now says "4h ago" instead of "4h old".
- Emergency-type chips are Aklanon; the note sent to the MDRRMO stays English (`sos_flow_honesty_test.dart`: tapping "Guba ro makina" sends "Engine failure").
- `squall_alert_test.dart`: in `akl` the alarm reads "ULI EON KAMO" and "20 ka minuto".
- `flutter analyze`: No issues found.
- `flutter test`: 383 passed.
- Residual scan of `lib/ui` string literals: only brand names, the Tagalog slogan, the buoy/seq identifier line a responder reads back, the language names in the picker, and the month table that Phase 5 replaces.

## Phase 4: Text below the UI localized (2026-09-26)

- Red first: `test/aklanon_below_ui_test.dart` (9 behavioural tests) failed to compile with 70 errors against the old APIs.
- 35 new keys (5 SAFETY CRITICAL).
- `HazardKind`, `AdvisoryPriority`, `LocationFailure` lost their English fields; each has an `...L10n` extension (the repo's `docs/22` §4.1 pattern). Advisory snapshots now store `priority.name`; `fromWire` already accepted it.
- Device forecast verdicts carry `RiskFactor` data instead of an English sentence; the cache stores them as codes, and a backend verdict keeps its own text.
- The SOS "Last attempt" value is stored as `DeliveryFailure` codes (`buoy_not_connected,no_internet`); rows written before this change still show their English text.
- The welcome note and the "All" municipality render from the ARB files.
- `SosForeground` resolvers are required; the English fallbacks are gone.
- `flutter analyze`: No issues found.
- `flutter test`: 392 passed.
- Left English on purpose: exception `reason`/`toString` text (diagnostics only), wire values (`All`, `Fisher handset`, sea-condition aliases, MDRRMO notes), Android notification channel names, and backend-generated text (`responder_status_label`, backend risk `reason`), which `docs/22` §10 defers to a backend contract change.
