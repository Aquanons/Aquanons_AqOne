# Implementation Plan: Fisher friction reduction (handset UX)

**Status:** APPROVED - Revision 3; Phase 1 complete and merged 2026-09-26; next phase waits for Len
**Owner:** Lenard (plan, review), Jade (Flutter), Doreen Kay (UX, term study, field session)
**Created:** 2026-09-25
**Updated:** 2026-09-25
**Related:** `docs/64_FISHER_FRICTION_REDUCTION_SPEC.md`, `docs/06_DELIVERY_STATES.md`, `docs/22_LOCALIZATION_PLAN.md`

Revision: 3
**Execution mode:** hard-stop
Feature spec and revision: `docs/64_FISHER_FRICTION_REDUCTION_SPEC.md` Revision 3
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0, `docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`
Len's chat approval, 2026-09-25T17:00:00+08:00: recommendations accepted for D2, D3, D5 and D6; the team picks the terms itself (D1); joining the pod Wi-Fi happens inside the app (D4); the field session with fishermen and the MDRRMO is after the RSTW pitch, date to be set by Len.
Len, 2026-09-25T23:40:00+08:00: replace the four At sea top banners with one summary card (spec 64 Section 2.6, FFR-14, D7); added as Phase 4b so no later phase number changes.
Target branch: `ux/fisher-friction` from `master`, one commit per phase (Len may push phases straight to `master`)
Implementer: GPT 5.6 Luna in worktree `../AqOne-fisher-ux` on `ux/fisher-friction`, briefed by `docs/fisher-ux/HANDOFF-luna-phase-1.md` (Len, 2026-09-25T22:56:00+08:00); reviewer: Claude Code.

Success condition: the five jobs in spec 64 Section 1 meet their targets in the field session (Phase 0b).
Sequencing, Len, 2026-09-25T18:00:00+08:00: `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md` (the 14 Critical edge cases, approved Revision 2) runs before this plan.
Next hard stop: plan 66 reaches the point in the table below; then Phase 1 here starts and stops at its own verification.

Execution mode is `hard-stop` by the default rule: the plan changes product code, amends the shared contract `docs/06`, and has more than 3 phases.
`docs/62` remains the register's `ACTIVE` plan; its open items are human and gated work, so the two do not touch the same files.

## Scope

Requirements FFR-01 to FFR-13 from spec 64.
All code changes are inside `mobile/`; doc changes are `docs/06` (additive column), `docs/22` (glossary), `docs/08` (status entry) and the evidence folder `docs/fisher-ux/`.
Untracked `AqOne_Story_and_Data_Flow.md` at the repo root is not part of this work and must not be staged.

Order and timing (D2):

| When | Work |
|---|---|
| Now | Plan 66 (Critical edge cases) first. Phase 0a here runs in parallel because it is people work and touches no code. |
| 2026-10-01 to 03 | RSTW pitch; no merges to `master` that change the demo APK |
| After plan 66 Phase 5 | Phases 1, 2, 3, 4, 4b and 5 here, in order |
| After Phase 5 here | Phase 6 here |
| Date set by Len, after RSTW | Phase 0b field session, on whatever build is newest |

Plan 66 Phases 6 and 7 wait on hardware gates (build step 4, the charger heat test), so "plan 66 first" means up to its Phase 5; after that the two plans run side by side.
Since plan 66 Revision 2 (D3: no pod password), plan 66 no longer depends on this plan's Phase 5.

Standard mobile gate, run from `mobile/` for every code phase:

```bash
flutter analyze            # expect: No issues found!
flutter test               # expect: All tests passed!
```

## Phase 0a: Term study by the team (people, not agent work)

Requirements: D1, FFR-06 input
State: Approved, not started
Owner: Doreen Kay with Jade; Len signs off
Deadline: before Phase 2 starts (after 2026-10-03)

### Tasks

- [ ] Collect how New Washington fishermen and the MDRRMO name: the device on the boat, the rescue office, the map screen, calling off a rescue, the SOS history, a squall warning. Sources: the team's own Aklanon and Tagalog speakers, notes from the Mayor meeting (2026-09-18) and the DTI Aklan pitch (2026-09-22), MDRRMO and PAGASA advisories as broadcast locally.
- [ ] Choose one term per concept in English, Tagalog and Aklanon, using spec 64 Section 2.3 as the starting list.
- [ ] Record the choices and their sources in `docs/fisher-ux/TERM_STUDY.md`, each marked "team-chosen, not field-validated".

### Verification

- [ ] `docs/fisher-ux/TERM_STUDY.md` has every concept in spec 64 Section 2.3 in all three languages, with a source per term.

### Review and checkpoint

- [ ] Len signs off the terms in chat; the date goes in the file header.

Checkpoint message: `docs(ux): record team term study for fisher wording`

## Phase 0b: Field session with fishermen and the MDRRMO (people, not agent work)

Requirements: FFR-13
State: Approved, date not set (Len sets it when schedules align after RSTW)
Owner: Doreen Kay with Jade

### Tasks

- [ ] Build two APKs: the baseline from `a8d9676` (before any of this plan) and the newest phase build; record both commits.
- [ ] Write the five-job script (spec 64 Section 1) on one page in English, Tagalog and Aklanon: what to say, what not to help with, what to time.
- [ ] Run it with 5 fishermen, one at a time, no coaching, each using both APKs with the order alternating between participants; record time, success and the words they use.
- [ ] Ask whether the Phase 0a terms are the words they use; list replacements.
- [ ] Show the MDRRMO contact the SOS situations wording and ask what they want fishermen to read at each step.
- [ ] Record everything in `docs/fisher-ux/YYYY-MM-DD_FIELD_VERIFICATION.md` with phones used and limitations (sample size, learning effect between the two APKs).
- [ ] Add a dated entry to `docs/08_DEMO_AND_STATUS.md` with the numbers and limitations.

### Verification

- [ ] One row per participant per job per APK; J1 and J2 at 5 of 5 and J3 to J5 at 4 of 5 on the newest APK, or each miss written up as a new finding in spec 64.

### Review and checkpoint

- [ ] Len reviews; term replacements go into a spec 64 revision and the next phase; if every phase is done and targets are met, spec 64 and this plan move to `COMPLETE`.

Checkpoint message: `docs(ux): record field session with fishermen and MDRRMO`

## Phase 1: Honest and predictable SOS (no contract change)

Requirements: FFR-01, FFR-02, FFR-03
State: Complete - merged to `master` 2026-09-26 (`7826488`), with the frozen-countdown fix (`dd9fc7d`, docs/fisher-ux/HANDOFF-luna-countdown-freeze.md); implemented by Luna, reviewed by Claude; 341 tests pass.
Open: the device double-tap check for the countdown fix (`docs/fisher-ux/COUNTDOWN_FREEZE_VERIFICATION.md`).

Failing tests already in the tree (write code until they pass; do not weaken them):

| Test | Asserts |
|---|---|
| `mobile/test/fisher_sos_situation_test.dart` | The mapping table, the honesty invariants, distinct icons, non-empty distinct text in `en`, `fil`, `akl` |
| `mobile/test/sos_flow_honesty_test.dart` | The post-SOS sheet shows `notSentYet` with no check icon and no "SOS sent" or "gone out"; it follows a `ValueListenable<SosRecord>` while open; same in `fil` and `akl`; `DeliveryStateTile` shows `cancelled` and `cancelling` |
| `mobile/test/widget_test.dart` | `EmergencyDetailsSheet(record: ValueListenable<SosRecord>, ...)` is imported from `ui/sos_flow.dart`; a 4 s press on SOS starts the alarm and opens `SosCountdownScreen` (replaces the old hold-to-silent test) |
| `mobile/test/localization_test.dart` | No bare `Text('...')` literal in `venture_page.dart`, `home_page.dart` or `sos_flow.dart` |

On that branch, the suite runs 296 passing and 4 failing to load, all because `lib/models/fisher_sos_situation.dart` and `lib/ui/sos_flow.dart` do not exist yet.

### Tasks

- [x] Add `mobile/lib/models/fisher_sos_situation.dart`: `enum FisherSosSituation { notSentYet, podHasIt, podNotConfirmed, rescueCentreHasIt, helpComing, cancelling, cancelled, closed }` with `icon` and `color` fields, `static FisherSosSituation of(SosRecord record, {DateTime? now})` (priority: resolved, then safe-now reply synced, then safe-now reply pending, then ETA or `acknowledged`, then state; `podNotConfirmed` uses `podDeliveryDeadline` from `delivery_policy.dart`), and `extension FisherSosSituationL10n` with `title(t)` and `description(t)`.
- [x] The extension reuses existing ARB keys in this phase (`deliveryState*`, `sosPodNotConfirmed`, `standDownPending*`, `standDown*`, `resolved*`); fisher wording changes come in Phase 2.
- [x] Create `mobile/lib/ui/sos_flow.dart` and move into it `SosCountdownScreen`, `EmergencyDetailsSheet`, `_SlideToAction` and `_EmergencyType` from `venture_page.dart`, plus one shared function for tap, countdown, `raiseSos` and the sheet that both `HomePage` and `VenturePage` call.
- [x] `EmergencyDetailsSheet` takes `ValueListenable<SosRecord> record` instead of `boat`; the header shows the situation's icon, colour and title, and the boat name; the shared flow feeds it from `SosService.changes`.
- [x] Replace `sosSentForBoat` and `sosWhatsWrongNotice` with honest keys (for example "What's wrong? Optional. This is added to your SOS."), with `@` descriptions and `fil` and `akl` drafts; delete the two old keys if nothing else uses them.
- [x] Remove `onHold` from `ActionPill` and both call sites; delete the "hold the SOS button for 3 seconds" sentence from `settingsSilentSosDescription` in all three ARB files.
- [x] `_buildSosStatus` in `venture_page.dart` and `DeliveryStateTile` take title, description, icon and colour from `FisherSosSituation`.

### Verification

- [x] The four test files above pass unchanged.
- [x] `grep -rn "_handleSosTap" mobile/lib` shows exactly one definition (it is now the public `handleSosTap` in `sos_flow.dart`).
- [x] `grep -rn "onHold" mobile/lib` returns nothing.
- [x] Standard mobile gate passes.
- [x] Evidence in `docs/fisher-ux/PHASE_1_VERIFICATION.md`: commands with pass counts, and an emulator screenshot of the sheet with the pod unreachable.

### Review and checkpoint

- [x] Claude reviews correctness, scope, dependencies, and unrelated changes, and reruns the gate.
- [x] Update plan, evidence, and current handoff.
- [x] Stage only reviewed phase-related paths and verify the staged diff.
- [x] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `fix(mobile): honest post-SOS sheet, no hidden silent hold, one SOS situation model`
Stop for Len's go-ahead (hard-stop).

## Phase 2: Fisher language

Requirements: FFR-05, FFR-06
State: Approved; starts after Phase 1
Depends on: Phase 0a terms

### Tasks

- [ ] Amend `docs/06_DELIVERY_STATES.md` first: add a "Fisher handset wording" column beside the existing display conventions; responder wording unchanged; tell Arnold (dashboard unaffected) and Jade.
- [ ] Add the glossary (spec 64 Section 2.3 with the Phase 0a terms) to `docs/22_LOCALIZATION_PLAN.md`.
- [ ] Give `FisherSosSituationL10n` its own ARB keys with the spec 64 Section 2.4 wording; rewrite the other affected `app_en.arb` values to the glossary; draft `app_fil.arb` and `app_akl.arb`, marked unreviewed.
- [ ] Localise the remaining English literals: `buoy_status_card.dart`, the emergency types (enum keeps only the icon; text through an `...L10n` extension), the safety dialog in `venture_page.dart`, `info_page.dart`, `chathubb.dart`, `advisories_page.dart`, `squall_banner.dart`, `weather_card.dart`, `sea_condition_banner.dart`, `offline_map_banner.dart`, `advisory_card.dart`, `squall_alert_page.dart`, `enrolment_page.dart`, the avatar semantics label in `home_page.dart`.
- [ ] The post-SOS sheet shows the situation's description under its title, not only the title (Phase 1 review, 2026-09-26: the sheet reads just "Saved", and the line that says it is not sent yet appears only on the status pill behind the sheet).
- [ ] "Sent by mistake?" above the call-off control becomes wording that is true for an SOS that has not left the phone.
- [ ] The pod card stops promising delivery: "Your SOS will reach the rescue centre now" becomes wording that matches `podHasIt`.
- [ ] Update `delivery_state_test.dart` to assert the ARB against the new `docs/06` column.
- [ ] Widen the `localization_test.dart` bare-literal check to every file in `mobile/lib/ui` (allowlist: `AqOne`, `SOS`).

### Verification

- [ ] `grep -rnE "Text\('[A-Za-z]" mobile/lib/ui` returns nothing outside the allowlist.
- [ ] Emulator walkthrough in `fil` and `akl`: Home, SOS countdown, post-SOS sheet and pod screen show no English except "SOS" and "AqOne"; screenshots in `docs/fisher-ux/PHASE_2_VERIFICATION.md`.
- [ ] A Tagalog and an Aklanon reader on the team review the SOS-path strings; corrections are applied or listed as open.
- [ ] Standard mobile gate passes.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): fisher wording and full localisation of the SOS path`
Stop for Len's go-ahead (hard-stop).

## Phase 3: Readable in the sun

Requirements: FFR-04, FFR-08, FFR-11
Failing tests: written 2026-09-26 on local branch `ux/p3-tests` (`b834687`): `mobile/test/readability_tokens_test.dart` and `mobile/test/readability_screens_test.dart`; cherry-pick onto `ux/fisher-friction` when the phase starts.
Phase 3 needs no wording from the term study, so it may run before Phase 2 if Len agrees.
State: Approved

### Tasks

- [ ] `core/tokens.dart`: light `dimText` and `secondaryText` raised to at least 4.5:1 on `canvas` and `surface`; check dark tokens the same way; update `docs/47_VISUAL_DESIGN_GUIDE.md` rows to match.
- [ ] `FisherSosSituation` icon colours reach at least 3:1 on `surface` in both themes (non-text contrast; today every situation except `rescueCentreHasIt` and `cancelled` fails on white).
- [ ] The SOS countdown and the post-SOS sheet fit a 360 x 640 phone at 200% text (today the sheet overflows by 164 px at the bottom).
- [ ] Raise every `fontSize` below 12 in `mobile/lib/ui` to at least 12; body text 16.
- [ ] Active SOS status card on Home (At sea shows the same situation inside the Phase 4b summary card) built from `FisherSosSituation`: title at least 20 sp, description wraps, no `maxLines: 1` on either.
- [ ] Dock: four labelled items (Home, At sea, News, Me), label at least 12 sp in a 4.5:1 colour, visible label under the raised At sea button, active item marked by weight and an indicator, not colour alone; Profile becomes a dock item and keeps the avatar shortcut.
- [ ] Replace fixed heights that clip at large text (`ActionPill` 176 x 50, dock `barHeight`) with minimum sizes.

### Verification

- [ ] Token test: every text token is at least 4.5:1 on `canvas` and `surface` in both themes, `primaryText` is at least 7:1 on `surface` (the SOS status title), and every situation icon colour is at least 3:1 on `surface`.
- [ ] `grep -rnE "fontSize: ([0-9]|1[01])(\.[0-9]+)?[,)]" mobile/lib/ui` returns nothing.
- [ ] Widget tests at `TextScaler.linear(2.0)` on 360 x 640: Home, the status card, the dock and the countdown raise no overflow errors and show the full status text.
- [ ] Dock widget test finds four visible labels.
- [ ] Emulator screenshots, light and dark, largest system font, in `docs/fisher-ux/PHASE_3_VERIFICATION.md`.
- [ ] Standard mobile gate passes.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): sun-readable tokens, font floor, labelled dock`
Stop for Len's go-ahead (hard-stop).

## Phase 4: SOS-first Home and plain controls

Requirements: FFR-07, FFR-10
State: Approved (D3: yes)

### Tasks

- [ ] Reorder Home: full-width SOS button (at least 96 dp) or the active SOS status card; one pod line with a "Connect" action (opens the Phase 5 screen once it exists, today's pod screen until then); one "Safe to go out today?" answer from the MDRRMO sea condition and squall watch; one advisory line; "More weather" opens the existing `WeatherCard`; "My SOS calls" opens the history list.
- [ ] Squall banner and its acknowledge button keep their place above everything else when a squall is showing.
- [ ] The floating SOS pill no longer covers the last "My SOS calls" card (seen in `docs/edge-remediation/critical/c3-relayed.png`); the full-width button above removes the floating pill, and the history list keeps bottom padding for the dock.
- [ ] Countdown: add a large "Cancel - do not send" button beside the slide.
- [ ] Calling off: replace the slide in `EmergencyDetailsSheet` with a normal danger button that opens the existing confirm dialog; delete `_SlideToAction` if nothing else uses it; update the "stand-down needs confirmation" test in `widget_test.dart` from a drag to a tap.

### Verification

- [ ] Widget test: the SOS control sits above the first weather widget on Home and is at least 96 dp tall.
- [ ] Widget test: tapping the countdown cancel button pops `false`, nothing is inserted in the outbox, the "Nothing was sent" snackbar shows.
- [ ] Widget test: calling off needs the button and then the confirm; cancelling the confirm leaves the SOS active.
- [ ] Existing squall, weather-card and pitch-mode tests still pass.
- [ ] Standard mobile gate passes; screenshots in `docs/fisher-ux/PHASE_4_VERIFICATION.md`.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): SOS-first home and button alternatives to slides`
Stop for Len's go-ahead (hard-stop).

## Phase 4b: One summary card on the At sea screen

Requirements: FFR-14 (spec 64 Section 2.6)
State: Approved (D7)
Depends on: Phase 1 (`FisherSosSituation`), Phase 2 (wording and localisation), Phase 3 (tokens and font floor)
Failing tests: written 2026-09-26 on local branch `ux/p4b-tests` (`f454e24`): `mobile/test/at_sea_summary_test.dart` (ranking table) and `mobile/test/at_sea_summary_card_test.dart` (At sea widget tests; the RETURN NOW button carries `Key('at_sea_acknowledge_squall')`).

### Tasks

- [x] Write the failing tests first (the reviewer writes them, as for Phase 1):
  a table test for the ranking function covering every SOS situation, squall level with and without acknowledgement, weather loaded, failed and unsafe, and map ages below 2 minutes, between 2 minutes and 3 hours, and 3 hours or more; and the widget tests listed under Verification.
- [ ] Add the pure ranking function in `mobile/lib/models/` (for example `at_sea_summary.dart`): inputs are the newest `SosRecord` (or none), `SquallWatch` and its acknowledgement, the weather snapshot or failure, the map layer ages, pitch mode and a clock; output is up to two headline rows and the three chip states, in the order and with the rules of spec 64 Section 2.6.
- [ ] Add the card widget (for example `mobile/lib/ui/widgets/at_sea_summary_card.dart`) that only draws that output: headline rows, the chip line, the "Details" label, and the "I understand" button on a rank 1 row wired to the existing squall acknowledge.
- [ ] Add the details sheet, reusing `SquallBanner`, the offline-map explanation from `OfflineMapBanner`, the weather safety text now in `_showSafetyDialog`, and the SOS status from `FisherSosSituation`; one large close button; Back closes it.
- [ ] In `venture_page.dart`, replace the top `Column` (weather capsule, squall banner, offline-map banner, SOS status pill) with the one card; delete `_buildWeatherCapsule` and `_buildSosStatus`, and fold `_showSafetyDialog` into the sheet.
- [ ] Move the "locating" pill so it no longer draws over the card (inside the card's chip line or directly under the card).
- [ ] Delete `OfflineMapBanner` if nothing else uses it after the move; keep `SquallBanner` (Home still uses it).
- [ ] New strings go in `app_en.arb` with `@` descriptions and `fil` and `akl` drafts; use the Phase 0a terms; no bare literals (the old "Loading…" goes too).
- [ ] Update `docs/47_VISUAL_DESIGN_GUIDE.md` for the card and remove the rows for the three retired banners.

### Verification

- [ ] The ranking table test passes, including: ranks 1 and 2 both present means both are the headline; unknown squall and failed weather never give a success colour or a check mark; pitch mode never shows a storm row or chip.
- [ ] Widget test: the At sea screen shows exactly one summary card at the top and no `OfflineMapBanner`, no top `SquallBanner` and no separate SOS pill.
- [ ] Widget test: tapping the card opens the sheet with all four sections, and the close button and Back both close it.
- [ ] Widget test: with a RETURN NOW squall not acknowledged, the card's "I understand" button calls the acknowledge callback once and the row drops to rank 3.
- [ ] Widget test at `TextScaler.linear(2.0)` on 360 x 640, light and dark, with an active SOS and a squall watch at the same time: no overflow, full text of both headline rows present.
- [ ] Existing squall alert, pitch-mode and offline-map age tests still pass or are moved to the ranking test with the same assertions.
- [ ] Emulator screenshots of four cases (calm, squall watch, active SOS plus RETURN NOW, old map) in `docs/fisher-ux/PHASE_4B_VERIFICATION.md`.
- [ ] Standard mobile gate passes.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): one at-sea summary card replaces the four top banners`
Stop for Len's go-ahead (hard-stop).

## Phase 5: Join the boat pod Wi-Fi from inside the app

Requirements: FFR-09 (spec 64 Section 2.5)
State: Approved (D4: in-app join)

### Tasks

- [ ] `mobile/lib/core/config.dart`: `podSsid = 'Aquan'` (from `docs/03`), overridable with `--dart-define` like `buoyBaseUrl`.
- [ ] `mobile/android/app/src/main/kotlin/ph/aqone/app/MainActivity.kt`: a `MethodChannel` `aqone/pod_wifi` with `connect(ssid)` (the pod stays open, plan 66 D3) returning `connected`, `declined`, `notFound` or `unsupported`, and `disconnect()`.
  Android 10+: `ConnectivityManager.requestNetwork` with a `WifiNetworkSpecifier` for the SSID, `NET_CAPABILITY_INTERNET` removed, 30 s timeout; `onAvailable` binds the process to the network, `onLost` and `disconnect()` unbind and release the request.
  Android 9 and older: `WifiManager` adds and enables an open network for the SSID.
- [ ] `AndroidManifest.xml`: add `CHANGE_WIFI_STATE` and `CHANGE_NETWORK_STATE`.
- [ ] `mobile/lib/services/pod_wifi.dart`: a thin Dart wrapper over the channel that returns an enum; no state of its own.
- [ ] Replace `_WiFiSelectionScreen` in `home_page.dart` with a "Connect to boat pod" screen: one big "Connect" button; states not connected, connecting, connected (pod status shown), declined (offer to try again), not found (move closer to the pod, check it is switched on); the "join in Wi-Fi settings" hint stays only as the fallback line.
- [ ] After `connected`, call `SosService.pollBuoy()` and `retryPending()` so a saved SOS leaves at once.
- [ ] `ponytail:` comment at the bind call naming the ceiling (no direct-to-backend route over mobile data while bound) and the upgrade path.
- [ ] iOS: unchanged, the settings hint stays.

### Verification

- [ ] Widget test with the channel mocked: each of the five screen states renders its fisher wording, and `connected` triggers one `pollBuoy` and one `retryPending`.
- [ ] Device test on one Android 10+ phone in airplane mode with Wi-Fi on and a powered pod: Home, "Connect", tap "Connect" on the system prompt, "Connected to boat pod" with the pod id, all without leaving the app; phone model, Android version and elapsed time in `docs/fisher-ux/PHASE_5_VERIFICATION.md`.
- [ ] Same phone: raise an SOS while not connected, then connect from the new screen; the SOS reaches `relayed` without leaving the app.
- [ ] Same phone: decline the prompt once; the screen shows the declined state and "Connect" works on the second try.
- [ ] If an Android 9 or older phone is available, repeat the first device test on it; otherwise record "not tested on Android 9 or older".
- [ ] Standard mobile gate passes; `flutter build apk --release --dart-define=PITCH_MODE=true --dart-define=BACKEND_BASE_URL=https://aqone-backend.onrender.com` succeeds.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): join the boat pod Wi-Fi from inside the app`
Stop for Len's go-ahead (hard-stop).

## Phase 6: Guided enrolment

Requirements: FFR-12
State: Approved (D6: remove remember-me)

### Tasks

- [ ] Split `OnboardingPage` into one question per screen: language, name, boat, registration type (large choice cards with icons instead of the dropdown), registration number when needed, mobile number (phone keypad), then a review screen.
- [ ] Keep `Validators.*` and the single `IdentityStore.ensure(...)` call exactly as they are.
- [ ] Remove the remember-me row and always remember; logout stays in Me behind its confirm.
- [ ] Rewrite the battery-optimisation dialog in fisher words with the reason first ("So your SOS keeps sending when the screen is off").
- [ ] Help, About, privacy and terms links move to the review screen footer.

### Verification

- [ ] New onboarding widget test walks every step for a new and a returning user and asserts the same `ensure` arguments as today.
- [ ] `enrolment_page_test.dart` and `identity_store_encryption_test.dart` pass unchanged.
- [ ] `git diff master -- mobile/lib/core/validators.dart` is empty.
- [ ] Standard mobile gate passes; screenshots in `docs/fisher-ux/PHASE_6_VERIFICATION.md`.

### Review and checkpoint

- [ ] Review correctness, scope, dependencies, and unrelated changes.
- [ ] Update plan, evidence, and current handoff.
- [ ] Stage only reviewed phase-related paths and verify the staged diff.
- [ ] Commit with a unique phase message and verify Git reports success.

Checkpoint message: `feat(mobile): one-question-per-screen enrolment`
Stop for Len's go-ahead (hard-stop).

## Recovery

Follow project `AGENTS.md` for the three-attempt limit and immediate blockers.
Record unresolved work and attempt counts in the current handoff.
Interrupted or failing work remains uncommitted and the phase remains incomplete.
