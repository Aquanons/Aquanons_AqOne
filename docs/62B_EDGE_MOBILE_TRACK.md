# Track M - Mobile (edge-case remediation)

Master plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` (read Sections 1 to 4 first).
Design: `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md`.
**Execution mode:** hard-stop
Branch and worktree: `edge/mobile`, `../AqOne-edge-mobile`
Owns: `mobile/**`.
Approved: with the master plan, Revision 1, 2026-09-24.
Evidence: `docs/edge-remediation/EVIDENCE-mobile.md`.
State: Awaiting approval

## Rules for this track

- **Architecture.**
  Decisions go in `mobile/lib/models/` as pure Dart: no plugins, no `BuildContext`, and the current time is injected as a `DateTime now` argument.
  `SosService`, `OutboxStore` and the UI are adapters that carry those decisions out.
- **Clean code.**
  - Names match the contract in master plan Section 3 (`nonce`, `resolutionCode`, `version`).
  - Split any function that mixes deciding with doing.
  - No boolean mode parameters: use a small enum, or two functions.
- **Localisation (CLAUDE.md).**
  - Every new user-facing string goes in `lib/l10n/app_en.arb` with an `@key` description.
  - Add drafts in `app_fil.arb` and `app_akl.arb`, marked unreviewed.
  - Read strings through `AppLocalizations.of(context)`.
  - No bare `Text('...')`, and no display text on an enum.
- **Delivery-state honesty (docs/06).**
  The UI never shows a later state than the evidence supports.
- **Tests first.**
  Write each phase's tests, run `flutter test`, and record the red run in the evidence file before changing `lib/`.
- **Gate commands** (every phase), run from `mobile/`:

  ```powershell
  flutter gen-l10n
  flutter analyze
  flutter test
  flutter test test_security_probes
  ```

  `flutter analyze` must report 0 issues.
  The security probes must stay green (6 passed).

---

## Phase M1: Delivery policy - `relayed` is not terminal

Requirements: EC-C3, EC-H15 (phone), and the silent-loss consequences of EC-C12, EC-M7 and EC-L10
Merge after: Phase 0
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `test/delivery_policy_test.dart`, a table test of `routesDue(record, now)`:
    - `saved` gives `{pod, direct}`
    - `relayed` inside the current backoff step gives `{}`
    - `relayed` after 20 s, then 60 s, then 5 min backoff gives `{direct}`
    - `relayed` with no delivery 10 min after `relayedAt` gives `{direct, pod}`
    - `delivered` and `acknowledged` give `{}`

    Also `isStale(record, now)`: `saved` and older than 12 h is true; `relayed` or newer is false.
  - `test/sos_service_test.dart` additions:
    - `relayed record retries direct`: the fake buoy accepts, and the fake backend fails, then succeeds on a later tick; the record ends `delivered`.
    - `delivered record is never retried`.
    - `stale unsent record is reported, not dropped`.
- [ ] Bump `AppDatabase` to schema v15: add `outbox.nonce INTEGER` (used in M3) and `outbox.last_attempt_at INTEGER`.
  Follow the existing migration style in `app_database.dart`.
- [ ] Create `lib/models/delivery_policy.dart` containing:
  - `enum SosRoute { pod, direct }`
  - `const directBackoff = [Duration(seconds: 20), Duration(seconds: 60), Duration(minutes: 5)]`
  - `const podDeliveryDeadline = Duration(minutes: 10)`
  - `const staleAfter = Duration(hours: 12)`
  - `Set<SosRoute> routesDue(SosRecord record, DateTime now)`
  - `bool isStale(SosRecord record, DateTime now)`
- [ ] `OutboxStore`:
  - Rename `awaitingRelay()` to `awaitingDelivery()`, returning `state IN (saved, relayed)`, oldest first.
  - Add `recordAttempt(localId, now)`.
  - Add `deleteUnsent(localId)`, which deletes only while the state is still `saved`.
  - Update every caller (grep).
- [ ] `SosService`:
  - `retryPending()` asks `routesDue` for each record.
  - `_attemptRelay` takes the route set, so it tries only what the policy says, then records the attempt.
  - Split the reason-building block at the end of `_attemptRelay` into `_failureReason(buoyResult)`.
- [ ] UI:
  - `delivery_state_tile.dart` shows the `sosPodNotConfirmed` string once a `relayed` record is past the deadline.
  - On app start, `app_shell.dart` checks `isStale` and shows a dialog (`sosStalePromptTitle`, `sosStalePromptBody`, `sosStalePromptSend`, `sosStalePromptCancel`).
    It sends automatically after 60 s with no answer; Cancel calls `deleteUnsent`.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Manual (emulator): point the buoy client at a stub that accepts and never delivers, with the backend reachable.
  The record goes `saved`, then `relayed`, then `delivered` within 60 s.

### Review and checkpoint

- [ ] Diff review: policy has no plugin imports, and `SosService` got simpler.
- [ ] Update this file, the evidence file and `HANDOFF.md`; stage only `mobile/**` and this track's docs; commit; open the PR.

Checkpoint message: `fix(mobile): keep delivering an SOS until the backend confirms it`

---

## Phase M2: Foreground service while an SOS is pending

Requirements: EC-H2
Merge after: M1
State: Awaiting approval

### Tasks

- [ ] Spike, time-boxed to 30 min, recorded in the evidence file.
  Pin the current `flutter_foreground_task`, and confirm from its docs whether its `TaskHandler` runs in the main isolate for that version.
  - If it does, the service only keeps the process alive, and the existing `SosService` timers keep running.
  - If it does not, the handler's repeat event builds its own `OutboxStore` and `SosService` and calls `retryPending()`, and only while the UI isolate is detached.
    This keeps one writer at a time to sqflite.
  Record which case applies.
- [ ] Write red tests: `test/foreground_policy_test.dart` for `shouldRunForeground(records)`.
  It is true while any record is `saved` or `relayed`, and false once all are `delivered` or later.
- [ ] Add `flutter_foreground_task` (approved by Len) to `pubspec.yaml`.
- [ ] Create `lib/models/foreground_policy.dart` (pure) and `lib/services/sos_foreground.dart` (the adapter).
  The adapter starts the service when the policy says run, stops it when not, and is re-evaluated on every `SosService.changes` event.
- [ ] `AndroidManifest.xml`: the service declaration with `foregroundServiceType="location"`, justified by the late GPS fill in M3, plus the matching `FOREGROUND_SERVICE` and `FOREGROUND_SERVICE_LOCATION` permissions.
  Check the rules for Android 14 and 15 and record them.
- [ ] Onboarding: request battery-optimisation exemption with the plugin's helper, explaining why with the `onboardingBatteryWhy` string.
- [ ] Notification text: `sosPendingNotificationTitle` and `sosPendingNotificationBody`.

### Verification

- [ ] Gate commands green.
- [ ] Device test (recorded, not a CI gate): release build on the cheapest target phone, SOS pressed with pod and internet off, screen off for 30 min, then internet turned on.
  The SOS lands without opening the app.

### Review and checkpoint

As in M1.
Checkpoint message: `feat(mobile): foreground service keeps SOS delivery alive in the background`

---

## Phase M3: Incident nonce, byte-safe text and late GPS fill

Requirements: EC-C14 (phone), EC-H17, EC-C8 (phone), EC-L7 (phone), EC-H1
Merge after: M1 (the backend ignores `nonce` until B2 merges, see master plan 1.2)
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `test/text_clamp_test.dart`, for `clampUtf8(text, maxBytes)`:
    - ASCII is unchanged
    - `ñ` at the boundary is dropped whole
    - an emoji at the boundary is dropped whole
    - the result's `utf8.encode` length is at most `maxBytes`
  - `test/sos_service_test.dart` additions:
    - `raiseSos assigns a 32-bit nonce and sends it on both routes`
    - `same seq, different nonce matches the right record`
    - `match order is localId, then nonce, then seq`
    - `late fix re-posts same nonce with position`
    - `no fix after 5 minutes sends nothing more`
  - `test/buoy_client_test.dart`: `malformed UTF-8 body does not throw`.
- [ ] `SosRecord`: add `nonce` (also in `toRow`, `fromRow`, `toBuoyPayload` and the backend JSON).
  `raiseSos` generates it with `Random.secure().nextInt(1 << 32)`.
- [ ] `lib/models/text_clamp.dart`: `clampUtf8(String text, int maxBytes)`.
  Use it for the note (64 bytes) and boat name (32 bytes), replacing `_clampNote`'s `substring`.
  Rename the config constants to `maxNoteBytes` and `maxBoatBytes`.
- [ ] `RemoteSos`: parse `nonce`, `version`, `resolution_code` and `reopened_at`.
  `_applyRemote` builds a `byNonce` map and matches on `local_id`, then `nonce`, then `seq`.
- [ ] `buoy_client.dart`: decode with `utf8.decode(bytes, allowMalformed: true)`.
- [ ] GPS:
  - `LocationService` gains `warmUp()`, called when the venture page opens and when a trip starts.
  - When a record has no fix, `SosService` waits up to 5 min for the first fix, then `OutboxStore.fillPosition(localId, lat, lon)` (only if still null), then re-sends direct and pod with the same nonce.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] After B2 merges: an emulator SOS appears once in `/active` with its `nonce`, and a second press in the same second creates a second row.

### Review and checkpoint

As in M1.
Checkpoint message: `feat(mobile): incident nonce, byte-safe SOS text, and late position fill`

---

## Phase M4: Stand-down safety, closure text and reopen

Requirements: EC-M9, EC-M10, EC-H4 (phone)
Merge after: M3 (it works without B1, falling back to `unspecified`; full behaviour after B1)
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `test/closure_text_test.dart`, for `closureMessage(l10n, code)`:
    - `rescued`, `safe_confirmed` and `stood_down_by_fisher` give `sosClosedByMdrrmo`
    - `closed_unconfirmed`, `unspecified` and null give `sosClosedUnconfirmed`
    - `duplicate` gives `sosClosedDuplicate`
  - `test/widget_test.dart` additions:
    - `stand-down needs confirmation`
    - `undo within 2 minutes sends still-in-danger`
    - `no ETA copy when acknowledged without eta`
    - `reopened incident clears resolved card`
  - `test/sos_service_test.dart`: `closed record keeps reconciling for 2 hours to catch a reopen`.
- [ ] `lib/ui/widgets/closure_text.dart`: `closureMessage(AppLocalizations l, String? code)`.
  This mapping lives in the UI layer because it produces display text.
- [ ] `SosService`:
  - `_closedIncidents` excludes a record only once 2 h have passed since `resolvedAt`.
  - When a remote row has `reopened_at` later than the local `resolvedAt`, clear it with a new `OutboxStore.clearResolved(localId)`, which also resets the stand-down.
    Today `saveResponder` never clears.
- [ ] `venture_page.dart`: the stand-down slide opens a confirmation (`sosStandDownConfirmTitle`, `sosStandDownConfirmBody`).
  After sending, show an Undo bar for 2 min (`sosStandDownUndo`) that calls `replyToSos(localId, 1)`.
- [ ] `responder_eta_dialog.dart`: when acknowledged with a null ETA, show `sosNoEtaYet` ("Help is being arranged - no arrival time yet").

### Verification

Gate commands green, with red and green runs recorded.

### Review and checkpoint

As in M1.
Checkpoint message: `feat(mobile): confirmed stand-down with undo and honest closure messages`

---

## Phase M5: Identity - enrolment, SOS without profile, reinstall, shore contact

Requirements: EC-H10 (phone), EC-M13, EC-M2, EC-M6 (phone)
Merge after: M4, and B5 for token refresh grace
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `test/enrolment_page_test.dart`:
    - a valid code calls `enrollVesselDevice` and shows `enrolVerified`
    - a 401 shows `enrolCodeInvalid`
    - no internet shows `enrolNeedsInternet`
  - `test/sos_service_test.dart`:
    - `SOS without boat name is raised with vessel id only`
    - `vessel id exists from first launch`
  - `test/backend_client_vessel_auth_test.dart`: `refresh is attempted on start when a credential exists`.
  - `test/backup_rules_test.dart`: parses `android/app/src/main/res/xml/backup_rules.xml` and `data_extraction_rules.xml`, and asserts that only the `aqone_identity_backup` shared-prefs file is included.
- [ ] Create `lib/ui/enrolment_page.dart` ("Enter the code from MDRRMO"), reachable from the profile page.
  It uses the existing `BackendClient.enrollVesselDevice` and `SecureCredentialStore`.
- [ ] On app start with internet, call `/api/vessel-auth/refresh` when a credential exists.
- [ ] `IdentityStore`:
  - The vessel ID is generated at first launch, before onboarding.
  - `isComplete` is no longer required to raise an SOS.
  - Write the plaintext vessel ID (not the encrypted profile) into a `SharedPreferences` file named `aqone_identity_backup`.
  - On first launch, restore the vessel ID from that file if it exists.
  - The vessel ID is not secret: it travels in clear over LoRa.
- [ ] `AndroidManifest.xml`:
  - `android:allowBackup="true"`
  - `android:fullBackupContent="@xml/backup_rules"` and `android:dataExtractionRules="@xml/data_extraction_rules"`, both including only `aqone_identity_backup`
- [ ] `SosService.raiseSos` needs only the vessel ID; the boat name may be empty.
  Put the SOS button widget on `home_page.dart` too, reusing the venture page's widget (extract it if needed).
- [ ] The profile page gains `shore_contact_name` and `shore_contact_phone` (strings `profileShoreContactName` and `profileShoreContactPhone`), sent by `registerVesselProfile`.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Device test (recorded): install, note the vessel ID, uninstall with backup on, reinstall.
  The same vessel ID comes back.

### Review and checkpoint

As in M1.
Checkpoint message: `feat(mobile): MDRRMO enrolment, SOS before setup, and recoverable vessel identity`

---

## Phase M6: Silent SOS, alarm stream and remaining strings

Requirements: EC-H22 (silent part), EC-L4, EC-L1
Merge after: M5
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `test/widget_test.dart`: `silent SOS starts no alarm` (toggle on), and `holding SOS for 3 seconds sends silently`.
  - `test/sos_alarm_test.dart`: the alarm player is configured with `AndroidUsageType.alarm` and `AndroidContentType.sonification`.
  - `test/localization_test.dart`: the new keys exist in all three ARB files, and no bare `Text('` literal remains in `venture_page.dart` or `home_page.dart` (grep-style test).
- [ ] Add a settings toggle `silentSos` (profile page, string `settingsSilentSos` with its description), stored in preferences.
- [ ] The SOS button: a 3 s hold raises a silent SOS.
  `raiseSos` itself is unchanged; the UI skips `SosAlarm.start()`.
- [ ] `sos_alarm.dart`: `setAudioContext(AudioContext(android: AudioContextAndroid(usageType: AndroidUsageType.alarm, contentType: AndroidContentType.sonification)))` before playing.
- [ ] Move the English literals found in docs/60 L1 (`venture_page.dart:391` "SOS stood down.", `home_page.dart:448` "No SOS sent yet.", and any others the grep finds on the SOS path) into ARB keys.

### Verification

Gate commands green, with red and green runs recorded.

### Review and checkpoint

As in M1.
Checkpoint message: `feat(mobile): silent SOS, alarm-stream siren, and localised SOS flow`

---

## Phase M7: Pod link and wet-hand cancel (gated, P3)

Requirements: EC-H3, EC-C12 (cause), EC-M7 (cause), EC-L5
Merge after: M6, plus F1 (per-pod passphrase and QR) and build step 4 recorded in `docs/08`
State: Blocked (gated)

### Tasks

- [ ] Write red tests:
  - `test/pod_pairing_test.dart`: the pure parser for the pod QR payload (SSID, passphrase, pod ID, version) rejects malformed input.
  - `test/widget_test.dart`: `hold 2 seconds to cancel; a tap does not cancel`.
- [ ] Add `lib/services/pod_link.dart` plus about 60 lines of Kotlin behind a `MethodChannel`:
  - `CompanionDeviceManager` association from the QR code
  - then `WifiNetworkSpecifier` plus `ConnectivityManager.requestNetwork`
  - bind only the pod HTTP client's sockets to that `Network`

  Android 9 and older fall back to the current behaviour.
  There is no new plugin.
- [ ] `BuoyClient` prefers the paired pod's network, and never hands off to an unpaired SSID once a pairing exists.
- [ ] Replace the countdown's cancel slide with "hold 2 s to cancel" (`sosHoldToCancel`); confirm the design with Doreen Kay.

### Verification

- [ ] Gate commands green.
- [ ] Device tests on Android 10, 12, 13 and 14 (the team's phones) with mobile data on:
  - Messenger works while the app talks to the pod
  - no "no internet" prompt
  - an SOS reaches the pod
- [ ] Wet-screen test: 20 wet taps in a pouch cause no accidental cancel.

Checkpoint message: `feat(mobile): paired pod link that leaves the phone's internet alone`

## Recovery

Follow project `AGENTS.md` for the three-attempt limit.
Record unresolved work and attempt counts in this worktree's `HANDOFF.md`.
