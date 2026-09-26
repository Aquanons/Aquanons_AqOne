# 64 - Fisher friction reduction (handset UX) spec

**Status:** APPROVED - Revision 4
**Owner:** Lenard (spec), Doreen Kay (UX and field test), Jade (Flutter)
**Created:** 2026-09-25
**Updated:** 2026-09-26
**Related:** `docs/65_FISHER_FRICTION_REDUCTION_IMPLEMENTATION_PLAN.md`, `docs/06_DELIVERY_STATES.md`, `docs/22_LOCALIZATION_PLAN.md`, `docs/47_VISUAL_DESIGN_GUIDE.md`

Revision: 4
Len's chat approval, 2026-09-25T17:00:00+08:00: go with the recommendations for D2, D3, D5 and D6; the team picks the terms itself (D1); add an in-app way to join the pod Wi-Fi (D4).
Revision 2 applies exactly those answers (Section 7) and records that the field session with fishermen and the MDRRMO waits until after the RSTW pitch, on a date Len sets.
Sequencing, Len, 2026-09-25T18:00:00+08:00: `docs/66_CRITICAL_EDGE_CASES_IMPLEMENTATION_PLAN.md` (the 14 Critical edge cases, approved Revision 2) runs before this plan.
The D2 dates below are superseded by that order; plan 65 carries the current order.
Revision 3, Len 2026-09-25T23:40:00+08:00: the At sea screen gets one summary card in place of its four top banners (Section 2.6, FFR-14, D7), shaped by a council review recorded in Section 2.6.
Revision 4, 2026-09-26: finding status after plan 65 Phases 1 and 3 (Section 3.1), and open decision D8 on the silent SOS gesture that Phase 1 removed.
Len, 2026-09-26: D8 decided - a visible "Silence" button on the SOS countdown (FFR-15, plan 65 Phase 4).

## 1. Purpose and success

Outside feedback (2026-09-25): the Flutter app may be too hard to navigate for fishermen who have little experience with modern phones.
This spec turns that feedback into a domain model, measured findings, and testable requirements.
It changes how the handset looks, reads and behaves.
It does not change any wire contract, delivery state value or transition, backend, firmware or dashboard behaviour.

The app exists for five jobs.
Everything else is secondary.

| Job | The fisher's question | Target (no coaching, current phone, 5 test users) |
|---|---|---|
| J1 Call for help | "How do I ask for rescue?" | 5 of 5 start an SOS within 10 s of seeing the unlocked app |
| J2 Know if help is coming | "Did anyone get my SOS?" | 5 of 5 give the correct answer for a `saved` and a `relayed` SOS; 0 of 5 believe help is coming when it is not |
| J3 Undo a mistake | "I pressed it by accident, how do I stop it?" | 4 of 5 cancel within 30 s |
| J4 Connect to the boat pod | "Is my phone talking to the box on my boat?" | 4 of 5 connect within 60 s |
| J5 Decide to go out | "Is it safe to fish today?" | 4 of 5 give the answer the MDRRMO sea condition gives |

J1 and J2 are safety targets and must reach 5 of 5.
J2's "0 of 5 believe help is coming" is the delivery-state honesty rule (`docs/06`) measured on people instead of code.

## 2. Domain model

### 2.1 Bounded context and context map

The handset is its own bounded context, **Fisher Handset**.
Its users are fishermen at sea, often on a moving boat, with wet hands, in bright sun, reading English, Tagalog or Aklanon at varying levels.

| Context | Relationship to Fisher Handset | What crosses the boundary |
|---|---|---|
| Boat pod (`docs/03`) | Upstream, Fisher Handset conforms | SOS hand-off, pod status, SSID `Aquan` |
| Backend public API (`docs/05`) | Upstream, Fisher Handset conforms | Reconciled state, ETA, resolution |
| Responder Console (dashboard) | Sibling, shares the Published Language only | The four delivery-state wire values |

The four delivery states (`saved`, `relayed`, `delivered`, `acknowledged`) are the **Published Language** between contexts.
Their values, order and honesty rules stay fixed.
Each context translates them into its own display language.
The dashboard keeps its responder wording; the handset gets fisher wording (Section 2.4).
This is the change that lets the app speak plainly without weakening the contract.

### 2.2 Subdomains inside the handset

| Subdomain | Kind | Screens and code today | Design consequence |
|---|---|---|---|
| Getting Help (SOS lifecycle as the fisher lives it) | Core | SOS button, countdown, post-SOS sheet, status pill, ETA dialog | First and largest thing on screen; richest modelling; zero English-only text |
| Pod Link | Supporting | Buoy status card, Wi-Fi screen | One visible line plus one "Connect" button |
| Trip Readiness | Supporting | Squall banner, sea condition, weather card, advisories, checklist | One "safe to go out?" answer; details one tap away |
| Enrolment | Supporting | Onboarding, enrolment, profile edit | One question per screen |
| Personalisation | Generic | Theme, avatar, legal pages | Under "Me"; never on the SOS path |

### 2.3 Fisher Language (ubiquitous language glossary)

One concept, one term, on every screen, in every language.
Today the app uses several words for the same thing, which a new phone user reads as different things.

| Concept | Words used today | Fisher term (English draft) | Rule |
|---|---|---|---|
| The device on the boat | "buoy", "boat pod", "pod", "Buoy Wi-Fi", SSID `Aquan` | **boat pod** (placeholder until D1) | The stationary relay buoy is never named in the app; the fisher only ever deals with his own pod |
| The rescue authority | "MDRRMO", "rescue centre", "Responder", "dispatcher" | **rescue centre** | "MDRRMO" appears only on Info and legal pages |
| The at-sea map screen | "Venture mode" | **At sea** | Label always visible under the icon |
| The distress call | "SOS" | **SOS** | Kept in every language |
| Stand-down | "stand down", "call off the rescue" | **I am safe - cancel help** | Never "stand down" |
| SOS history | "Your messages" | **My SOS calls** | Chat messages are never called "messages" on Home |
| Squall RETURN NOW | "squall", "RETURN NOW" | **Storm coming - go back to shore** | Full-screen alert keeps its current behaviour |
| Advisories tab | "Advisories" | **News** | Page title can stay "Advisories" in the body |
| Profile tab | "Profile" | **Me** | Holds settings, language, logout |

The glossary becomes a section of `docs/22_LOCALIZATION_PLAN.md` so translators use the same terms.
The team picks the English, Tagalog and Aklanon terms from its own study of how New Washington fishermen and the MDRRMO talk (D1, plan Phase 0a).
They are marked "team-chosen, not field-validated" until the field session (plan Phase 0b) confirms or replaces them.

### 2.4 Fisher SOS situation (the one model every SOS screen reads)

Today the at-sea status pill (`venture_page.dart:884` `_buildSosStatus`), the history tile (`widgets/delivery_state_tile.dart`) and the post-SOS sheet each derive the SOS status on their own from `SosRecord`, and the SOS flow itself (`_handleSosTap`, countdown, details sheet) is duplicated in `home_page.dart` and `venture_page.dart`.
Wording and honesty drift between copies: F1 is one; another is that the tile calls a fisher's own stand-down "Resolved" while the pill calls it "Stood down".

The handset gets one read-only projection, `FisherSosSituation`, computed by a pure function from one `SosRecord`.
It is a view model, not a new aggregate: `SosRecord` and `DeliveryState` stay the source of truth, unchanged.
Each situation carries an icon, a colour, a short title and one "what to do now" line, with text through a `...L10n` extension (AGENTS.md: no display text on enums).

| Situation | Derived from | Title (EN draft) | What to do now (EN draft) |
|---|---|---|---|
| `notSentYet` | `saved` | Not sent yet | Keep the app open near your boat pod. It sends by itself. |
| `podHasIt` | `relayed` | Boat pod has your SOS | Sending to shore. Nobody has confirmed it yet. |
| `podNotConfirmed` | `relayed` for longer than `podDeliveryDeadline` (10 min) | Boat pod has your SOS | Shore has not confirmed it yet. Still trying. |
| `rescueCentreHasIt` | `delivered` | Rescue centre received it | Stay with your boat. Wait for their answer. |
| `helpComing` | `acknowledged`, or ETA present, and not resolved | Help is coming | Stay with your boat. Keep the phone on. |
| `cancelling` | stand-down requested, not yet synced | Cancelling your SOS | Rescue centre has not seen this yet. |
| `cancelled` | stood down | You cancelled this SOS | Press SOS again if you need help. |
| `closed` | resolved by the rescue centre | Closed by the rescue centre | Existing `sosClosed*` wording stays |

Invariant, tested as a table over every combination: a situation is never later than the evidence on the record.
`notSentYet` and `podHasIt` never use green, a check mark, or the words "sent", "received" or "help".

### 2.5 Joining the pod Wi-Fi from inside the app (D4)

The pod is an open access point with the fixed SSID `Aquan` (`docs/03`), so the app knows exactly what to join.

| Android | Mechanism | What the fisher sees |
|---|---|---|
| 10 and newer | `ConnectivityManager.requestNetwork` with a `WifiNetworkSpecifier` for SSID `Aquan`, internet capability not required, 30 s timeout | One system prompt drawn over the app: "Connect to Aquan?" |
| 9 and older | `WifiManager` adds and enables an open network for `Aquan` | Nothing; the phone joins |

When the network is available, the app binds its process to it (`bindProcessToNetwork`), because Android does not route ordinary sockets to an app-requested Wi-Fi network that has no internet.
When the network is lost, the app unbinds.
Known trade-off: while bound to the pod, the app's own direct-to-backend route cannot use mobile data, so an SOS goes through the pod route only.
At sea there is no mobile data anyway; near shore the pod route still delivers.
The code carries a `ponytail:` note naming this ceiling and the upgrade path (send backend calls over the default network from Kotlin).

The existing "join in Wi-Fi settings" hint stays as the fallback when the fisher declines the prompt or no pod is in range.
The pod stays an open "Aquan" network: Len ruled out a pod password on 2026-09-25 (plan 66 D3), and plan 66 Phase 6 checks the pod's identity inside the SOS reply instead, so this channel takes only the SSID.
Starting a connect attempt automatically when an SOS is saved and no pod is reachable is a possible follow-up, not part of this revision.

### 2.6 One summary card on the At sea screen (D7)

Today the top of the At sea map stacks up to four separately styled banners, 8 dp apart, over the map (F13).
They become one card, the **At sea summary card**, so the fisher reads one place, in one style, and sees more map.

**What goes in.**
The card reads four inputs the screen already has and adds no new fetch:

| Input | Source today | Card part |
|---|---|---|
| The newest SOS | `_latestSos`, read through `FisherSosSituation` (Section 2.4) | SOS row |
| Squall watch and its acknowledgement | `SquallWatch` from `AppShell` (source-agnostic, so it survives the move to PAGASA alerts) | Storm row or storm chip |
| Weather at the fisher's position | `WeatherSnapshot` and `_weatherFailed` | Weather chip |
| Age of the cached map layers | `MapSnapshotStore.ages()` | Map chip |

**Shape.**
- A headline area of at most two rows, each an icon, a title of 8 words or fewer (at least 18 sp) and one "what to do" line that wraps and is never cut with "...".
- Below it, one line of three chips, always present: weather (icon, word, temperature), storm (icon and word), map (icon and age).
  Each chip is an icon plus a word, never colour alone, at least 14 sp and 48 dp tall.
- A visible "Details" label with a chevron; tapping anywhere on the card opens a details sheet.
- The details sheet holds the full existing content, reused rather than rewritten: the squall banner, the offline-map explanation, the weather safety text and its Open-Meteo and "not a PAGASA warning" note, and the SOS status with its time and position.
  It closes with a large button and with Back.

**What reaches the headline (first two that apply, in this order).**

| Rank | Condition | Headline row |
|---|---|---|
| 1 | Squall `returnNow`, not acknowledged | Storm coming - go back to shore, with a large "I understand" button that calls the existing acknowledge |
| 2 | An SOS whose situation is not `closed` or `cancelled` | The `FisherSosSituation` title and description |
| 3 | Squall `returnNow` already acknowledged, or `watch` | The squall message, no button |
| 4 | A `closed` SOS whose `resolvedAt` is less than 15 minutes old; a `cancelled` SOS leaves the headline at once, since the fisher cancelled it and the record keeps no time for it | The situation title and description |
| 5 | Map layers 3 hours old or more (today's severe threshold) | Map is old - hazards may have changed |
| 6 | Weather unsafe or wind above the threshold | The existing safety title |
| 7 | Nothing above | The weather condition and temperature |

Rows ranked 1 and 2 are never pushed out: when both apply they are the two rows, and everything else stays in the chips and the sheet.

**Honesty rules (the council's non-negotiables).**
- Unknown is never calm: a failed or stale squall fetch reads "Storm check unavailable" in a neutral colour, a failed weather fetch reads "Weather unavailable", and neither ever uses green or a check mark.
- The card has no "all clear" state; the calmest it gets is a plain weather summary.
- Map age is always visible in its chip whenever the oldest layer is 2 minutes old or more, as the banner does today (system design Section 3.4, data age visible wherever a feed drives a decision).
- The full-screen RETURN NOW alert from `AppShell` stays exactly as it is; the card is the reminder after it, not a replacement.
- In pitch mode the storm row and storm chip are hidden, as the squall banner is today.

**Where the logic lives.**
The ranking is a pure function in `mobile/lib/models/` (next to `FisherSosSituation`) that takes the four inputs and a clock and returns the ordered rows and chip states.
The card is a humble widget that draws what that function returns.
This keeps the rules testable without a map, a network or a device, the same boundary docs/61 Section 4.3 uses for SOS policy.

**Council review (2026-09-25).**
- Devil's advocate: merging hides warnings.
  Answer: ranks 1 and 2 can never be displaced, the three chips are always on screen, and the sheet holds every detail.
- Simplicity: no banner framework or plugin registry; one pure function, one card, and the old widgets reused inside the sheet.
- Reliability: unknown states must not collapse into calm, and map age must stay visible; both are rules above.
- Architecture: a pure read model that draws on Getting Help (SOS), Trip Readiness (squall, weather) and map data, with the widget kept thin.

## 3. Findings (code reading, 2026-09-25)

Not yet field-tested; the field session (plan Phase 0b) measures them on real users.
Severity is by effect on J1 to J5.

| ID | Severity | Finding | Evidence | Job |
|---|---|---|---|---|
| F1 | High | Right after SOS, the sheet shows a green check and "SOS sent for {boat}", and says "the alert has already gone out", while the record is still `saved` (no pod reached). This breaks the honesty rule at the most important moment. | `ui/venture_page.dart:1409-1426`; `raiseSos` returns `DeliveryState.saved` (`services/sos_service.dart:96`) | J2 |
| F2 | High | Holding the SOS button for 3 s silently switches to a silent SOS (no siren). A panicking user who presses hard and long gets unexpected behaviour, and nothing on screen tells anyone this exists. | `ui/widgets/action_pill.dart:36-44`, `ui/home_page.dart:409`, `ui/venture_page.dart:878` | J1 |
| F3 | High | Connecting to the pod means leaving the app for Android Wi-Fi settings and coming back ("Join a buoy network in the phone's Wi-Fi settings, then return here"). The entry point is an unlabelled tap on the buoy card. | `ui/home_page.dart:276,567,767` | J4 |
| F4 | High | English-only text on the SOS path, which the l10n rule forbids: pod status card, emergency types, the safety dialog, Info page (25 strings), chat. | `ui/widgets/buoy_status_card.dart:20-37`, `ui/venture_page.dart:49-53,490-506`, `ui/info_page.dart` | J1, J2, J4 |
| F5 | High | On the at-sea screen the SOS status is a 13.5 px title and a 10.5 px line, both cut to one line with "...". On Home it sits at the bottom of a long scroll under "Your messages". | `ui/venture_page.dart:884-990`, `ui/home_page.dart:575-592` | J2 |
| F6 | Medium | Home stacks seven blocks (squall, sea condition, weather with 7-day strip, advisory, pod card, SOS history). SOS is a 176 x 50 floating pill that competes with them. | `ui/home_page.dart:400-592`, `ui/widgets/action_pill.dart:4-5` | J1, J5 |
| F7 | Medium | Navigation: the centre "Venture mode" button has no visible label; dock labels are 10.5 px in `#94A3B8` on white (about 2.6:1, below 4.5:1); Profile is reachable only through the avatar. | `ui/app_shell.dart:708,782,795` | all |
| F8 | Medium | The light-theme `dimText` token `#94A3B8` (about 2.6:1 on white) is used for body copy such as "No SOS sent yet"; 39 text styles are below 12 px, mostly in `weather_card.dart` (10) and `advisory_card.dart` (6). Sun glare at sea makes both worse. | `core/tokens.dart:14,85`, `ui/home_page.dart:586` | J2, J5 |
| F9 | Medium | Cancelling the countdown and calling off an SOS are slide gestures only, with no hint of direction and no button alternative (WCAG 2.5.7). Calling off stacks a slide and a confirm dialog. | `ui/venture_page.dart:1255,1490,1508` | J3 |
| F10 | Medium | Enrolment is one long form: five fields, a dropdown, remember-me, legal links, then a technical battery-optimisation dialog. | `ui/onboarding_page.dart:286-570,154` | first run |
| F11 | Low | SOS status and SOS flow are duplicated (Section 2.4), so wording and honesty drift between screens. | `ui/venture_page.dart:884`, `ui/widgets/delivery_state_tile.dart:16-30,65`, `ui/home_page.dart:285` | J2 |
| F12 | Low | Terminology drift: docs say "boat pod", the app says "buoy", the SSID is `Aquan`; "MDRRMO" and "rescue centre" are mixed. | `docs/06`, `l10n/app_en.arb` | all |
| F13 | Medium | The At sea screen stacks up to four differently styled banners over the top of the map (weather capsule, squall banner, offline-map banner, SOS status pill), 8 dp apart; the locating pill is pinned at 90 dp from the top and draws over the second banner; the weather capsule shows a bare English "Loading…". | `ui/venture_page.dart:589-615,646-651,767-770` | J2, J5 |

### 3.1 Status on 2026-09-26

| Finding | Status |
|---|---|
| F1, F2, F11 | Fixed by plan 65 Phase 1 (`7826488`): the post-SOS sheet reads its state from `FisherSosSituation`, a long press behaves like a tap, and one SOS flow lives in `mobile/lib/ui/sos_flow.dart` |
| F5 | Fixed on Home by Phase 3 (`186e231`, `SosStatusCard`); At sea still cuts its SOS line until Phase 4b |
| F7 | Partly fixed by Phase 3: four labelled destinations at 12 sp or more; the "Venture mode" wording waits for Phase 2 |
| F8 | Fixed by Phase 3: text tokens reach 4.5:1 in both themes, status icons 3:1, and no text is below 12 sp |
| F3, F4, F6, F9, F10, F12, F13 | Open: Phases 5, 2, 4, 4, 6, 2 and 4b |

Found while working on Phase 1 and fixed with it (`dd9fc7d`): the SOS countdown could freeze at "1" and send nothing, either because it closed a screen opened above it instead of itself, or because a quick double tap opened two countdowns (`docs/edge-remediation/EVIDENCE-critical.md`).
Its on-device double-tap check is still open (`docs/fisher-ux/COUNTDOWN_FREEZE_VERIFICATION.md`).

## 4. Design principles

Derived from the ui-ux-pro-max rules (Emergency SOS and Safety product profile: accessible, flat, high contrast), tightened for this audience.

- **P1 One screen, one job.** SOS is the biggest control on Home and At sea, and reachable in one tap from both.
- **P2 Icon + word + colour.** Never colour alone, never an icon alone. Titles of 8 words or fewer, then one "what to do now" line.
- **P3 Big targets.** Primary actions at least 56 dp tall (above the 48 dp minimum, for wet hands on a moving boat), at least 8 dp apart. The SOS button at least 96 dp tall.
- **P4 Readable in sun.** Body text at least 16 sp, nothing below 12 sp, contrast at least 4.5:1 in both themes and 7:1 for SOS status text. Layouts survive 200% system font size without clipping.
- **P5 No hidden gestures.** No long-press meanings. Every slide has a button alternative.
- **P6 Say what to do, not how the system works.** No "mesh", "relayed", "MDRRMO", "LoRa" on the core path.
- **P7 Stay in the app.** Anything the fisher needs, including joining the pod Wi-Fi, happens inside the app; system settings are only a fallback.
- **P8 Same words everywhere.** The glossary in Section 2.3 is the only source of terms.
- **P9 Design for no training.** No tutorial carousel; each screen must work for someone who skipped every explanation.

## 5. Requirements and acceptance criteria

| ID | Required behaviour | Observable pass/fail criterion | Finding |
|---|---|---|---|
| FFR-01 | The post-SOS sheet title, icon and colour come from `FisherSosSituation`. | Widget test: raise an SOS with no pod reachable; the sheet shows "Not sent yet" wording, no `Icons.check_circle*`, no green, and not the strings "sent" or "gone out". | F1 |
| FFR-02 | Holding SOS behaves exactly like tapping it. Silent SOS stays a Profile setting only. | Widget test: a 4 s press on the SOS button starts the normal countdown and the alarm starts; `ActionPill` has no `onHold`. | F2 |
| FFR-03 | One pure `FisherSosSituation` projection and one shared SOS flow replace the copies. | `test/fisher_sos_situation_test.dart` covers every `DeliveryState` x resolved x stood-down x stand-down-pending x ETA x pod-deadline combination; `_buildSosStatus`, `DeliveryStateTile` and `EmergencyDetailsSheet` read it; `_handleSosTap` exists once in `mobile/lib`. | F11, F5 |
| FFR-04 | An active SOS shows as a status card at the top of Home and At sea: title at least 20 sp, "what to do" line wraps (no ellipsis). | Widget test at `TextScaler.linear(2.0)` on a 360 x 640 screen: no overflow error, full text present. | F5 |
| FFR-05 | Every user-facing string in `mobile/lib/ui` comes from `AppLocalizations`, except the brand "AqOne" and "SOS". | `grep -rnE "Text\('[A-Za-z]" mobile/lib/ui` and the check in plan Phase 2 return nothing; emergency types use a `...L10n` extension. | F4 |
| FFR-06 | Fisher wording (Sections 2.3 and 2.4) in `app_en.arb`; `docs/06` gains a "Fisher handset wording" column; responder wording unchanged. | `delivery_state_test.dart` asserts the ARB against the new `docs/06` column; `fil` and `akl` drafts exist and are marked unreviewed. | F12 |
| FFR-07 | Home order: SOS button or active SOS status, then one pod line, then one "safe to go out today?" answer, then one advisory line; weather detail and SOS history behind one tap each. | Widget test finds the SOS control above the first weather widget; SOS button at least 96 dp tall and full width. | F6 |
| FFR-08 | Dock: four labelled destinations (Home, At sea, News, Me), labels at least 12 sp and 4.5:1 contrast, active item marked by more than colour. | Widget test finds four visible labels; contrast of label tokens checked in the test. | F7 |
| FFR-09 | A "Connect to boat pod" screen joins the pod's open Wi-Fi (SSID `Aquan`, `docs/03`) from inside the app, with no trip to Android settings and no new dependency (Section 2.5). | Device test on one Android 10+ phone in airplane mode with Wi-Fi on and a powered pod: one tap on "Connect", one tap on the system "Connect" prompt, then "Connected to boat pod" and a pod status poll succeeds, without leaving the app. Widget test covers not connected, connecting, connected, declined and not found. | F3 |
| FFR-10 | Countdown gets a large "Cancel - do not send" button beside the slide; calling off uses a normal button plus the existing confirm dialog, no slide. | Widget tests: tapping the cancel button sends nothing; calling off needs button then confirm. | F9 |
| FFR-11 | Tokens: light `dimText` at least 4.5:1 on its surfaces; no `fontSize` below 12 in `mobile/lib/ui`; body 16 sp. | Token contrast test; `grep -rnE "fontSize: ([0-9]|1[01])(\.[0-9]+)?[,)]" mobile/lib/ui` returns nothing. | F8 |
| FFR-12 | Guided enrolment: one question per screen, big Next, number keypad for phone, registration type as large choice cards, plain-words battery explanation. Same validators, same `IdentityStore.ensure` call. | `enrolment_page_test.dart` and a new onboarding test walk every step; validators unchanged in the diff. | F10 |
| FFR-13 | Field verification of the five jobs with fishermen and the MDRRMO, once schedules allow after the RSTW pitch. The unchanged build (`a8d9676`) and the newest build are both tested in the same session, in alternating order, so one session gives a before and an after. | Results recorded in `docs/fisher-ux/` against Section 1 targets. | all |
| FFR-14 | The At sea screen shows one summary card in place of the four top banners, ranked and worded as Section 2.6 sets out. | Table test on the pure ranking function: every combination of SOS situation, squall level and acknowledgement, weather state and map age gives the Section 2.6 rows; ranks 1 and 2 are never displaced; unknown squall or weather never yields a success colour or check mark. Widget tests: at most one card and no `SquallBanner`, `OfflineMapBanner` or separate SOS pill at the top of At sea; tapping opens the details sheet with all four sections; no overflow at `TextScaler.linear(2.0)` on 360 x 640. | F13 |
| FFR-15 | While the SOS alarm is ringing, the countdown shows a large, labelled "Silence" button (icon and word, at least 56 dp). One tap stops the siren and vibration for this SOS, the countdown keeps running and the SOS still sends; the alarm does not restart on the post-SOS sheet. With the silent setting on, no alarm rings and the button is not shown. | Widget tests: tapping Silence calls `SosAlarm.stop` once, the countdown still completes and the SOS is raised, no "cancelled" message appears, and the button then reads as silenced and cannot be tapped again; with `silent_sos` on, the button is absent. | H22, D8 |

## 6. Non-goals

- No change to `docs/02` to `docs/05`, the delivery-state values or transitions, backend, firmware or dashboard.
- No new dependency: joining the pod Wi-Fi uses a small platform channel in the existing Android activity.
- iOS keeps today's "join in Settings" instructions; joining from inside an iOS app needs Apple's Hotspot Configuration entitlement, and the pitch and field phones are Android.
- No new theme mode; contrast is fixed in the existing light and dark tokens.
- No tutorial or walkthrough screens (P9).
- No chat redesign and no weather-card redesign beyond the font floor; both are supporting and can follow the field session results.
- Recorded voice prompts are not in this spec unless Len approves D5.

## 7. Decisions (Len, 2026-09-25)

| ID | Question | Decision |
|---|---|---|
| D1 | Fisher terms for the device on the boat, the rescue centre and the map screen (English, Tagalog, Aklanon). | The team decides from its own study (plan Phase 0a); the field session validates later. "boat pod" stays the placeholder until then. |
| D2 | Timing against the RSTW pitch (2026-10-01 to 03) and other work. | Superseded 2026-09-25T18:00:00+08:00: plan 66 (Critical edge cases) runs first, then this plan's code phases; no merge that changes the demo APK during RSTW. The field session is after RSTW, on a date Len sets. |
| D3 | Replace slide-only controls (FFR-10). | Yes: calling off uses a button plus the existing confirm; the countdown gets a large cancel button beside the slide. |
| D4 | How the fisher joins the pod Wi-Fi. | From inside the app (Section 2.5, FFR-09). |
| D5 | Recorded voice prompts. | Out of this plan; revisit after the field session. |
| D6 | Remove "Remember me" from enrolment. | Yes: always remember; logout stays in Me behind a confirm. |
| D7 | Four banners at the top of At sea. | One summary card (Len, 2026-09-25T23:40:00+08:00), designed in Section 2.6 after a council review. The 15-minute linger for a closed or cancelled SOS is a proposed default; Len may change it. |
| D8 | Phase 1 removed the 3 s hold on SOS (FFR-02). That hold was also the quick silent SOS that `docs/61` D11.4 designed for a robbery at sea (finding H22); only the settings toggle was left, which a fisher under threat cannot reach in time. | Decided by Len, 2026-09-26: a visible "Silence" button on the SOS countdown that stops the siren and vibration without cancelling (FFR-15), built in plan 65 Phase 4 with the other countdown controls. The red countdown screen itself stays visible, and a duress cancel is still roadmap (docs/61 D11.4). |

## 8. Open questions and readiness

- The field session needs five fishermen from New Washington, an MDRRMO contact, and one Tagalog and one Aklanon reader; Len sets the date when schedules align after RSTW.
- Until then every J1 to J5 target is unmeasured, and the Phase 0a terms are team-chosen.
