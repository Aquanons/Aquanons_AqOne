# Implementation Plan: Aklanon first (handset)

**Status:** APPROVED - Revision 2; Phases 1-4 complete, Phase 5 code complete, walkthrough and Len's proofread open
**Owner:** Lenard (approval, Aklanon proofreading), Claude (implementation and tests)
**Created:** 2026-09-26T13:30:00+08:00
**Updated:** 2026-09-26T13:50:00+08:00
**Related:** `docs/22_LOCALIZATION_PLAN.md`, `docs/65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md` (Phase 2), `mobile/lib/l10n/README.md`

Revision: 2
**Execution mode:** auto
Feature spec and revision: Len's chat request, 2026-09-26: "Need to improve aklanon support for the flutter mobile codebase. Some of the Language there is still written in English and also the app should defaultly run in aklanon." The requirements below (AKL-01 to AKL-08) are the spec; no separate spec doc.
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0, `docs/22_LOCALIZATION_PLAN.md` (amended in Phase 1)
Len's chat approval, 2026-09-26T13:45:00+08:00, of Revision 1: "D1 yes update that doc and move that task here, Im an aklanon myself ill proofread it after your done, D2 Yes the app is tailored for the fishermen out of the box, D3 Load tagalog if you dont have proper aklanon term, D4 Yes, return now means \"ULI EON KAMO\" in aklanon, D5 yes keep the compass, D6 sure."
Revision 2 records those answers in the decision table, names Len as the Aklanon proofreader (AKL-08), and sets the execution mode to `auto` because Len proofreads after the whole plan is done; nothing else changed.
Target branch: `feat/aklanon-first` in its own worktree `../AqOne-aklanon` with its own `HANDOFF.md` (`docs/58`); each verified phase merged to `master` and pushed (Len: push verified work straight to `master`)
Roles: Claude writes each phase's red tests first, implements, and reruns the gate; Len proofreads every Aklanon string once the plan is done.

The default rule would give `hard-stop` (product code, more than 3 phases); Len's approval asks for the whole plan before his proofread, so it runs `auto` and still stops on any failed gate.

## Audit baseline (2026-09-26, `master` at `537494e`)

What the scan of `mobile/` found, which this plan is built on:

- `app_akl.arb` already has all 268 keys of `app_en.arb`; nothing falls back to English through a missing key.
  `untranslated.json` and the generated `app_localizations*.dart` are older than the ARB files (22:02 on 09-25 against 09:31 on 09-26); the next `flutter pub get` regenerates them.
- The English a fisher sees in Aklanon mode comes from four places:
  1. About 70 hard-coded literals in `mobile/lib/ui` (the file list in plan 65 Phase 2, plus `app_shell.dart` and `main.dart` fallbacks), and the four long `InfoCopy` texts in `info_page.dart` (About, Help, Privacy, Terms).
  2. About 40 display strings produced below the UI, in `models/` and `services/`: hazard titles and messages (`hazard_alert.dart`), advisory priority labels (`advisory.dart`), forecast risk reasons (`safety_score.dart`, `daily_outlook.dart`), GPS failure messages (`location_service.dart`), the welcome advisory (`welcome_advisory.dart`), and the SOS "Last attempt" reason, which `sos_service.dart` and `backend_client.dart` build as English text and `outbox_store.dart` persists.
  3. Eight Aklanon ARB values identical to English: `navHome`, `navProfile`, `profileTitle`, `deliveryMetaBuoy`, `deliveryMetaResponder`, `wifiTitle`, `weatherLocationDefault`, and the four compass letters (a pending decision in `lib/l10n/README.md`).
  4. Flutter's own chrome (text-selection menu, back tooltip) and dates: the `akl` fallback delegates load English, `DateFormat('EEEE', 'akl')` throws and falls back to English, and `advisory_card.dart` and `daily_outlook.dart` hand-roll English month and weekday names.
- Default language: `LocaleController` follows the device when nothing is stored, and `resolveLocale` falls back to English, so a fresh install on an English or Filipino phone never shows Aklanon.
  `main.dart` `_activeL10n()` also falls back to `en` for the SOS foreground notification.
- Dead code carrying English that would otherwise be translated: the whole trip checklist (`checklist_page.dart`, `checklist_store.dart`, `checklist_item.dart`, threaded through `main.dart`, `app_shell.dart`, `venture_page.dart` and two tests, but no screen opens it since `d47273a` dropped it from Venture), `widgets/brand_header.dart` (no importer), `HotspotCell.ageLabel` (no caller), `LocaleController.hasExplicitChoice` (no caller).
- Overlap: plan 65 Phase 2 already owns "localise the remaining English literals" and "widen the bare-literal check", but it is blocked on the Phase 0a term study.
  Extraction does not need the term study: keys carry today's English wording, and Phase 2 later changes only ARB values.

## Requirements

| ID | Requirement | Observable acceptance |
|---|---|---|
| AKL-01 | A fresh install runs in Aklanon regardless of the phone's language; an explicit pick in the language picker still wins and survives a restart. | Widget test: empty preferences, device locale `en_US`, the app root renders the Aklanon `navAdvisories`; after `setLocale(en)` and a reload, English. |
| AKL-02 | The SOS foreground and ETA notifications use the same language as the app, Aklanon by default. | Unit test on the resolver used by `main.dart`: no stored choice gives the `akl` `sosPendingNotificationTitle`. |
| AKL-03 | No hard-coded user-facing English in `mobile/lib/ui`. | `localization_test.dart` bare-literal check covers every file under `lib/ui` for `Text('`, `title: '`, `label: '`, `labelText: '`, `hintText: '`, `tooltip: '`, `semanticLabel: '`; allowlist `AqOne`, `SOS`, `Aquan`. |
| AKL-04 | No display text produced in `models/` or `services/`; those layers return codes or enums, and the UI resolves text through `AppLocalizations` (the `docs/22` §4.1 pattern). Wire values sent to the backend or pod stay English. | Tests: each new `...L10n` extension gives distinct non-empty text in `en`, `fil`, `akl`; the emergency-type note sent to the MDRRMO is English whatever the app language; an old outbox row with English `last_error` text still displays. |
| AKL-05 | Every `app_en.arb` key has an Aklanon value, and an Aklanon value equal to English is allowed only from an explicit allowlist. | `localization_test.dart`: key sets equal; `akl != en` except the allowlist (brand names and placeholders-only values). |
| AKL-06 | Weekday and month names are Aklanon in Aklanon mode. | Widget test: in `akl`, the forecast strip and advisory date show `Lunes`-style names, not `Monday`. |
| AKL-07 | Dead code that only carried English is deleted, not translated. | The files in the audit baseline are gone; `flutter analyze` clean. |
| AKL-08 | Every new Aklanon string is a draft until Len proofreads it; `SAFETY CRITICAL` strings are marked for a second reader before the field session. | `docs/aklanon/REVIEW.md` lists every new or changed `akl` key with its English, the draft, and a reviewer column. |

## Decisions (answered by Len, 2026-09-26T13:45:00+08:00)

| # | Question | Answer |
|---|---|---|
| D1 | Move plan 65 Phase 2's literal extraction and bare-literal widening into this plan, and run this plan before plan 65 Phases 2, 4 and 4b? | Yes. Plan 65 Phase 2 is updated to point here; it keeps the glossary, the `docs/06` column and the fisher wording, which only change ARB values after this plan. `ux/p4b-tests` rebases onto this plan once. |
| D2 | Ignore the device language entirely (Aklanon until the fisher picks otherwise)? | Yes: "the app is tailored for the fishermen out of the box". `resolveLocale` and the `tl` mapping become dead and are deleted. |
| D3 | Flutter chrome in Aklanon mode? | Load Tagalog where there is no proper Aklanon term. Flutter ships no Aklanon chrome at all, so the fallback delegates load `fil`. |
| D4 | Draft `SAFETY CRITICAL` strings in Aklanon now? | Yes. "Return now" is "ULI EON KAMO" (Len). |
| D5 | Compass letters? | Keep N/E/S/W; they join the AKL-05 allowlist. |
| D6 | `fil` for the new keys? | Out of scope; new keys get `akl` only. |

## Dependencies and order

| Phase | Outcome | Can start when |
|---|---|---|
| 1 | Aklanon by default | Plan approved |
| 2 | Dead English deleted | Phase 1 |
| 3 | UI literals localized | Phase 2 |
| 4 | Text below the UI localized | Phase 3 |
| 5 | Last English values, chrome and dates, walkthrough | Phase 4 |

## Phase 1: Aklanon by default

Requirements: AKL-01, AKL-02
State: Complete - 2026-09-26, evidence `docs/aklanon/EVIDENCE.md`

### Tasks

- [x] Amend `docs/22_LOCALIZATION_PLAN.md` first: Aklanon is the default and the device language is not consulted (D2); record D3 and D5; mark the §2 "fallback and source of truth" line as English being the ARB template only.
- [x] Red tests in `test/localization_test.dart`: AKL-01 (fresh preferences, `tester.platformDispatcher.localeTestValue = Locale('en', 'US')`, pump `AqOneApp`, expect Aklanon) and AKL-02.
- [x] `lib/core/l10n_fallback.dart`: add `const Locale kDefaultLocale = Locale('akl')`; list `akl` first in `kSupportedLocales` so the pickers show it first; delete `resolveLocale` and its three tests. The fallback delegates load `fil` chrome here rather than in Phase 5 (one line, D3).
- [x] `lib/core/locale_controller.dart`: `locale` returns `_override ?? kDefaultLocale`; delete `effectiveLocale` (callers in `language_picker.dart` read `controller.locale`) and `hasExplicitChoice`; rewrite the class comment (two states, not three).
- [x] `lib/main.dart`: `MaterialApp.locale` and `_activeL10n()` use `_locale?.locale ?? kDefaultLocale`.
- [x] `lib/l10n/README.md`: delete the stale "Waiting on a translator" section (all keys are drafted in `akl`) and say Aklanon is the default.

### Verification

- [x] `cd mobile && flutter pub get && flutter analyze && flutter test`: analyze clean, all tests pass (baseline 379 on `master`).
- [ ] Emulator, fresh install, device language English: onboarding and Home show Aklanon; switch to English in Profile, force-stop, relaunch: English. Folded into the Phase 5 walkthrough; the widget tests cover the same two launches.
- [x] Results and screenshots in `docs/aklanon/EVIDENCE.md`.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): Aklanon is the default language`
Continue automatically to the next phase (auto).

## Phase 2: Dead English deleted

Requirements: AKL-07
State: Complete - 2026-09-26, evidence `docs/aklanon/EVIDENCE.md`

### Tasks

- [x] Delete `lib/ui/checklist_page.dart`, `lib/data/checklist_store.dart`, `lib/models/checklist_item.dart`, and the `checklist` parameter from `main.dart`, `AppShell`, `VenturePage`, `test/pitch_mode_test.dart` and `test/readability_screens_test.dart`.
  Leave the `checklist_items` table in `app_database.dart`: dropping it needs a schema version bump for no user benefit.
- [x] Delete `lib/ui/widgets/brand_header.dart` and `HotspotSurface.ageLabel` (and its test group).
- [x] Delete the 12 ARB keys only the checklist and an old buoy snackbar used (`checklist*`, `tripChecklistTooltip`, `buoyConnectSnack`, `buoyDisconnectSnack`). Kept, although unused today: `sosReopened` (a `docs/22` M4 key) and `hotspotLegend*` (the activity heatmap is in scope again).

### Verification

- [x] Standard mobile gate: `flutter analyze` clean, `flutter test` passes.
- [x] `grep -rn "Checklist\|BrandHeader\|ageLabel" mobile/lib mobile/test` prints nothing except the table DDL.

### Review and checkpoint

- [x] Same four gates as Phase 1.

Checkpoint message: `refactor(mobile): delete the unreachable checklist and brand header`
Continue automatically to the next phase (auto).

## Phase 3: UI literals localized

Requirements: AKL-03, AKL-05, AKL-08
State: Complete - 2026-09-26, evidence `docs/aklanon/EVIDENCE.md`

### Tasks

- [x] Red tests: widen the bare-literal check in `localization_test.dart` to every file under `lib/ui` with the AKL-03 patterns and allowlist; add the AKL-05 key-parity test.
- [x] Move every flagged literal into `app_en.arb` with an `@key` description (screen context, and `SAFETY CRITICAL` where it is) and an `app_akl.arb` draft.
  Files: `advisories_page.dart`, `app_shell.dart` (the `$hours hour` fragment becomes an ICU plural), `chathubb.dart`, `enrolment_page.dart`, `home_page.dart` (avatar semantics), `info_page.dart`, `sos_flow.dart`, `squall_alert_page.dart`, `venture_page.dart` (safety dialog), and under `widgets/`: `advisory_card.dart`, `buoy_status_card.dart`, `offline_map_banner.dart`, `responder_eta_dialog.dart`, `sea_condition_banner.dart`, `squall_banner.dart`, `weather_card.dart`.
- [x] `InfoCopy` becomes four ARB keys (`infoAbout`, `infoHelp`, `infoPrivacy`, `infoTerms`); `InfoPage` takes the resolved text as today.
- [x] Emergency types in `sos_flow.dart`: the enum keeps the icon and an English `wire` note; display text through an `...L10n` extension (AKL-04 test: the note sent to the MDRRMO stays English in `akl`).
- [x] The three hand-rolled "N min ago" formatters (`offline_map_banner.dart`, `sea_condition_banner.dart`, `squall_banner.dart`) become one ICU key set used by all three.
- [x] Start `docs/aklanon/REVIEW.md` (AKL-08) with every key added in this phase.
- [x] Pulled forward from Phase 5: the seven Aklanon values that were still English (the AKL-05 parity test needed them), and nine earlier drafts that used Tagalog or Cebuano function words (ang, kung, ug, kaysa), all listed in `REVIEW.md`.

### Verification

- [x] Standard mobile gate.
- [x] `grep -rnE "(Text|title:|label:|labelText:|hintText:|tooltip:|semanticLabel:)\s*\(?\s*'[A-Za-z]" mobile/lib/ui` prints nothing outside the allowlist.

### Review and checkpoint

- [x] Same four gates as Phase 1.

Checkpoint message: `feat(mobile): localize the remaining screen text with Aklanon drafts`
Continue automatically to the next phase (auto).

## Phase 4: Text below the UI localized

Requirements: AKL-04, AKL-08
State: Complete - 2026-09-26, evidence `docs/aklanon/EVIDENCE.md`

### Tasks

- [x] Red tests for each item below, behavioural (drive the model or service, render in `akl`), not source greps.
- [x] `hazard_alert.dart`: drop `title` and `message(count)` from `HazardKind`; `HazardKindL10n` with an ICU plural for the buoy count.
- [x] `advisory.dart`: drop `label` from `AdvisoryPriority`; `AdvisoryPriorityL10n`. `venture_feeds.dart` snapshots write `priority.name` instead of `priority.label` (`fromWire` already lower-cases, so old snapshots still parse). The `'All'` municipality default becomes null and the UI shows the localized "All".
- [x] `safety_score.dart` and `daily_outlook.dart`: device verdicts carry `RiskAssessment.factors` (`RiskFactorKind` plus the number where there is one, cached as `swell:2.1`-style strings); `reason` stays for the backend's own English text (`docs/22` §10); the sentence is built by `RiskAssessmentL10n.reasonText`. Reuse the existing `DeteriorationReason` labels where they match.
- [x] `location_service.dart`: `LocationResult.message` moves to `LocationFailureL10n`; `venture_page.dart` resolves it.
- [x] SOS "Last attempt": `backend_client.dart` and `sos_service.dart` record short codes (`no_signal`, `no_internet`, `tls`, `unreachable`, `buoy_not_connected`, `no_buoy`, `buoy_rejected`, `buoy_invalid`), joined with `,`, in `last_error`; `delivery_state_tile.dart` maps each code to text and shows an unknown value verbatim (rows written before this change).
- [x] `welcome_advisory.dart`: title and body come from ARB keys, resolved in `advisory_card.dart` for the welcome advisory's id.
- [x] `sos_foreground.dart` fallbacks: drop the English defaults; the resolvers are always passed.
- [x] Add every new key to `docs/aklanon/REVIEW.md`.
- [x] `describeBuoyError` deleted: it only existed to make exception text fisher-readable for the old "Last attempt" line; the exception reason is diagnostics now.

### Verification

- [x] Standard mobile gate.
- [ ] Emulator in `akl`, backend unreachable, no pod: send an SOS; the "Last attempt" line on the status tile is Aklanon. Folded into the Phase 5 walkthrough; `aklanon_below_ui_test.dart` covers the codes and the legacy rows.

### Review and checkpoint

- [x] Same four gates as Phase 1.

Checkpoint message: `feat(mobile): models and services return codes, the UI speaks Aklanon`
Continue automatically to the next phase (auto).

## Phase 5: Last English values, chrome and dates, walkthrough

Requirements: AKL-05, AKL-06, AKL-08
State: Code complete - 2026-09-26; the emulator walkthrough is blocked (see evidence)

### Tasks

- [x] Red tests: AKL-05 allowlist shrinks to brand names, placeholders-only values and the D5 compass letters; AKL-06 weekday and month names.
- [x] Aklanon drafts for `navHome`, `navProfile`, `profileTitle`, `deliveryMetaResponder`, `wifiTitle`, `weatherLocationDefault`; done in Phase 3. `deliveryMetaBuoy` stays "Buoy", the word the rest of the Aklanon file uses, and joins the allowlist.
- [x] `l10n_fallback.dart`: the fallback delegates load `fil` (D3); done in Phase 1.
- [x] One `dateLocaleFor(Locale)` helper (`akl` maps to `fil`: the Spanish-derived day and month names are the same words) used by `weather_card.dart`; `daily_outlook.shortWeekday` and the month table in `advisory_card.dart` are replaced by `DateFormat('E')` and `DateFormat('d MMM')` through it.

### Verification

- [x] Standard mobile gate.
- [ ] Emulator walkthrough, fresh install, device in English: onboarding, Home, SOS countdown, post-SOS sheet, pod screen, Venture, advisories, forecast, chat, profile, About/Help/Privacy/Terms.
  No English except `AqOne`, `SOS`, `MDRRMO`, `LoRa`, `GPS`, `PAGASA`, buoy ids, and the Aquanons welcome photo caption.
  Screenshots in `docs/aklanon/`.
- [ ] `REVIEW.md` handed to Len for proofreading; corrections applied or listed as open. `SAFETY CRITICAL` rows need a second reader before the field session.

### Review and checkpoint

- [ ] Same four gates as Phase 1. Done early: plan 65 Phase 2's moved tasks point here, the dated `docs/08` entry, and the `docs/SPEC_INDEX.md` and `docs/README.md` rows.

Checkpoint message: `feat(mobile): Aklanon dates, chrome and the last English labels`
Stop for Len (plan complete).

## Out of scope

- Fisher wording and the glossary: plan 65 Phase 2, after the term study; it changes ARB values only.
- Tagalog for the new keys (D6).
- Android notification channel names ("AqOne SOS Delivery", "Rescue alerts"): the OS shows them only in system settings, and a channel's name is fixed at creation on some Android versions.
- `lib/ui/widgets/closure_text.dart` has no caller in `lib/` since plan 65 Phase 1; delete or re-wire it in plan 65, not here.
- Backend and dashboard text: `docs/22` keeps them English.

## Recovery

Follow project `AGENTS.md` for the three-attempt limit and immediate blockers.
Record unresolved work and attempt counts in the worktree `HANDOFF.md`.
Interrupted or failing work remains uncommitted and the phase remains incomplete.

## Requirement cross-check

| Requirement | Phase |
|---|---|
| AKL-01, AKL-02 | 1 |
| AKL-07 | 2 |
| AKL-03 | 3 |
| AKL-04 | 3 (emergency types), 4 |
| AKL-05 | 3 (parity), 5 (allowlist) |
| AKL-06 | 5 |
| AKL-08 | 3, 4, 5 |
