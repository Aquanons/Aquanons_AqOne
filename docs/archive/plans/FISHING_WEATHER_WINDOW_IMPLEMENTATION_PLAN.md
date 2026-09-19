# Implementation Plan: Fishing Weather Window

**Status:** SUPERSEDED
**Owner:** Team Aquanons / Gemini
**Created:** 2026-09-13
**Updated:** 2026-09-19
**Related:** [\docs/05_PUBLIC_API.md\](../../05_PUBLIC_API.md), [\docs/08_DEMO_AND_STATUS.md\](../../08_DEMO_AND_STATUS.md)

> **Historical record:** This plan was prepared for a forecast-based fishing preparation feature.
> It was superseded by subsequent sprints and is preserved here as a historical planning record.

---


## Overview

Add a Home weather summary that helps fishermen prepare for worsening sea weather by showing an approximate interval in days and hours until forecast risk first increases.
Reuse the existing green/yellow/red risk vocabulary and seven-day outlook, extend the existing forecast feed with actual hourly weather and waves, and retain honest offline freshness and official-warning precedence.
The estimate describes forecast deterioration at a stated location; it is not guaranteed time available for fishing or a predicted typhoon landfall time.

## Gemini handoff and authorization

- The user explicitly requested a plan to hand off to Gemini, not implementation in this session.
- The user explicitly authorized this feature ahead of the remaining hardware/build-order work: "Option 3 but make an implementation plan to be handed off to gemini."
- That authorization permits Gemini to begin Phase 1 without re-asking about the repository's sequential hardware build order.
  It does not claim those hardware steps or the deployment are complete.
- Read `AGENTS.md`, `docs/00_START_HERE.md`, `docs/05_PUBLIC_API.md`, `docs/08_DEMO_AND_STATUS.md`, and `mobile/lib/l10n/README.md` before editing.
- The PRD referenced at the repository root by AGENTS.md is actually present at `docs/Aqone_PRD (2).md`; use that v3.0 document rather than the stale out-of-scope list in the brief.
- Apply `.agents/skills/implementation-plan/SKILL.md`, `.agents/skills/council/SKILL.md`, and `.agents/skills/ponytail/SKILL.md`.
  Council review is recorded below; revisit only if implementation evidence changes the decision.
- Start by inspecting git status, resolving the Flutter/Python executables, and recording baseline test/lint results.
  Flutter was found at `C:\Users\User\flutter\bin\flutter.bat`; Python was not resolved on PATH during planning and `backend/.venv/Scripts/python.exe` was absent.
  Use an existing configured Python environment or the README setup; do not guess credentials or run the destructive simulation generator.
- Create the target branch without overwriting user changes.
  Update this file during execution, commit only phase-owned paths, and stop after each phase for explicit user sign-off as required by the invoked implementation-plan skill.
- This handoff does not authorize deployment, messages to teammates, publishing, or automatic advancement through all phases.

---

## Council Deliberation: Forecast-based fishing preparation

### 1. Grounding

**Observed facts**

- `mobile/lib/models/daily_outlook.dart` already defines green `safe`, amber `caution`, red `danger`, and neutral `unknown`, with icons and localized labels.
- `mobile/lib/ui/widgets/weather_card.dart` already renders a seven-day outlook.
- `backend/app/api/public.py` exposes `/api/public/forecast` as an Open-Meteo weather/marine proxy, without a fusion model or current backend risk verdict.
- `mobile/lib/services/forecast_provider.dart` tries that endpoint, then directly calls Open-Meteo.
  Both paths currently return daily outlooks; fetched hourly waves are reduced to daily maxima.
- Backend marine requests use requested coordinates, while the direct mobile fallback uses a fixed offshore point.
- `HomePage._loadForecast` discards the fetch timestamp after success and preserves the displayed data after failures.
  `ForecastCache` checks its 12-hour expiry only when loading, so an open screen can retain old weather indefinitely.
- `VentureFeeds._cachedJson` drops snapshot timestamps, and `SeaCondition.tryParse` stamps cached official conditions as newly fetched.
- `SafetyScore` can classify incomplete measurements as green, and its all-numeric-inputs-missing branch can erase a known thunderstorm classification.
  Missing weather codes are also parsed as clear code zero.
- Existing gust/wave/rain thresholds in `mobile/lib/core/config.dart` are explicitly provisional.
  Safety-critical Tagalog and Aklanon translations require human review under the localization README.

**Unverified assumptions**

- Existing thresholds have not been demonstrated to suit local boats and fishing grounds.
- Neither route-specific return travel time nor a preparation buffer has been supplied.
- This feature has no new structured PAGASA warning ingestion, and available free-text advisories cannot be reliably classified as geographically applicable marine restrictions.
- The most recent repository status is not evidence of a currently healthy deployment or completed physical SOS path.

### 2. Perspectives & Debate

- **Devil's Advocate:** Daily maxima cannot support an hourly storm countdown.
  Missing data, a forecast ending, and a storm's actual arrival must not be presented as the same event.
- **Simplicity Champion:** Extend the current feed and WeatherCard; reuse risk colors, the HTTP client, cache storage and localization.
  No separate screen, new weather service, AI model, notification subsystem, database table or package is needed.
- **Security & Reliability Auditor:** Preserve timestamps, coordinates and missing values through every layer.
  A known danger must survive partial data loss, and stale official green cannot clear a forecast or squall warning.
- **Architecture / DX:** A small forecast result carrying days, hours and provenance is justified because the existing list loses necessary context.
  Keep the public API additive and handle older daily-only servers without fabricating hours.

### 3. Consensus vs. Tension

- **Agreement:** Use real hourly inputs, one deterministic window calculation, existing risk tiers, explicit data availability, and official-warning precedence.
- **Core tension:** A simple countdown is useful for preparation but can imply a safety guarantee that forecasts and vessel-independent thresholds cannot support.
  Resolve this with an approximate deterioration interval, a visible forecast location and timestamp, and no positive estimate when the supporting data is incomplete or stale.

### 4. Verdict

- **Recommended path:** Implement the four gated phases below, with the product behavior and acceptance matrix as the specification.
- **Revisit when:** Fishers request an actual return-by deadline, field review changes thresholds, a structured official-warning feed becomes available, or a broader operating area requires route-specific forecast coverage.
  Those changes require their own explicit inputs; do not hide guessed journey times or geography inside this feature.

---

## Product behavior

Place a compact **Fishing weather window** summary inside the existing Home WeatherCard, above its outlook strip and below the existing official/squall warnings.
Display a color, an icon and words together; use a yellow/amber treatment with readable dark text rather than yellow text on white.

| State | Meaning and example copy | Time behavior |
|---|---|---|
| Green: Lower forecast risk | Complete recent data shows no threshold breach in the current interval. | Example: "Conditions may worsen in about 1 day 6 hours" plus "From Tue, 3 PM: stronger winds." |
| Yellow: Caution | Current forecast crosses a caution threshold, or existing official caution/squall watch is active. | "Conditions need caution now. Prepare and check advisories." Do not show positive fishing time remaining. |
| Red: High risk | Current forecast crosses a danger threshold, or official not-advised / active return-now warning applies. | "High-risk conditions now. Follow MDRRMO guidance." Do not show positive fishing time remaining. |
| Neutral: Estimate unavailable | Missing, stale, malformed or insufficiently covered data prevents a reliable estimate. | Explain the reason and offer the existing refresh action; this is an availability state outside the three risk tiers. |

Future yellow/red risk does not mean current conditions are already at that tier.
Show the upcoming tier and cause beside its forecast time so the fisherman sees both current risk and what is approaching.
If a hazard is forecast but earlier data has gaps, show the hazard's forecast time with "Earlier conditions unavailable" and no continuous-window countdown.
If no deterioration occurs in the usable horizon, say "No worsening forecast through [date/time]"; never convert the horizon end into a storm deadline or "7 safe days."
If only daily data is available, retain the day strip and show date-level guidance such as "Higher risk forecast on Tuesday; hourly estimate unavailable."
Do not convert the first adverse day's midnight into a precise event time.
All examples here are illustrative, not a current weather forecast.

## Calculation, risk and data rules

1. **Window:** Starting at `now`, scan contiguous hourly coverage for the first caution or danger interval.
   Compute the nonnegative interval to its start; display rounded-down whole days and remaining hours, or "within an hour" below one hour.
   Use "about" and the forecast boundary's local date/time; never display seconds or interpolate a sub-hour storm arrival.
2. **Coverage:** Retain seven daily outlook days.
   Limit the numeric estimate to the existing `forecastConfidentDays` near-term horizon (currently three days), additionally bounded by actual atmospheric/marine overlap.
   This is a presentation limit, not a claim of validated certainty.
   Later hazards remain visible as the existing lower-confidence daily outlook.
3. **Hour semantics:** Document interval start/end explicitly before implementation.
   Open-Meteo gust maxima describe the preceding hour, while waves are instantaneous samples.
   Align by timestamps and the documented interval meanings, using the earliest affected hourly boundary conservatively; never join arrays by index or shift gust hazards one hour later.
4. **Risk:** Reuse the existing gust and wave constants: caution at gusts >=30 km/h or waves >=1.5 m; danger at gusts >=50 km/h or waves >=2.5 m.
   Reuse the existing recognized weather-condition escalation, including thunderstorms as danger and rain/fog as caution.
   These are existing provisional app heuristics, not official PAGASA limits.
5. **Rain:** Keep daily rainfall totals and their thresholds in the daily scorer only.
   Use hourly weather codes for rain/thunderstorm escalation; do not compare hourly millimeters against daily 20/50 mm thresholds or invent new hourly rain thresholds.
   A caution/danger daily rainfall assessment remains visible as a day-level restriction and suppresses a contradictory positive time window for that affected day; it cannot supply an hourly onset.
6. **Unknown:** Green/positive coverage requires recognized weather code, finite nonnegative gust and wave values for each relevant interval.
   Missing wave/gust/code is unknown, never zero or clear weather.
   Known caution/danger evidence still elevates risk when another input is missing; retain an incomplete-data label.
   Fix shared daily parsing/scoring issues only where needed to avoid contradicting the new summary, and test all callers of those functions.
7. **Freshness:** Keep retrieval timestamps on successful and cached results, and keep backend response-generation time separate from retrieval time.
   Neither is a weather-model issuance timestamp; never label them as such.
   Proposed implementation default: positive estimates require retrieval age <= the existing 30-minute forecast refresh interval; beyond this, show cached guidance and "Refresh needed" without a positive countdown.
   Retain historical display only up to the existing 12-hour cache maximum, also bounded by coverage; reject future/inconsistent timestamps.
   These operational defaults need field review and must not be advertised as a validated safety freshness policy.
8. **Lifecycle:** Recalculate from an injected/current clock on display, app resume, a successful refresh, and a lightweight foreground minute tick.
   Network refresh stays at its existing interval.
   Do not reset the forecast age or extend coverage after failures, cache restore, screen navigation, or device clock rollback.
   Reuse the existing latest-request guard pattern to prevent slower older requests overwriting newer location data.
9. **Location:** Persist requested and returned forecast coordinates, marine sample coordinates, and a source/location label together with the data.
   Make backend and fallback sampling consistent and explicit; do not silently substitute the fixed offshore point for a forecast claimed to be at the user's GPS fix.
   Without a trustworthy current fix, label the selected regional/cached location explicitly rather than "your current location."
   A response for an earlier selected location must never populate a newly selected location's estimate.
   Do not add location permissions, geocoding services or route prediction.
10. **Warnings:** Official `notAdvised` and an active squall `returnNow` take precedence; official `caution` and squall `watch` prevent an encouraging positive window.
    Official green never reduces measured/forecast risk.
    Preserve the real official-condition cache timestamp through `VentureFeeds`; retain existing active-warning behavior across failed polls.
    Unknown official status is visibly unknown and never proof of clearance.
    Keep existing advisories prominent; do not parse arbitrary prose or priority strings into invented geographic no-sail rules.
11. **Return travel:** The duration ends at forecast deterioration; it excludes travel home and preparation time.
    State this plainly in localized text.
    No "return by" deadline, boat speed, routing, travel-duration input or buffer calculation is included in this handoff.
12. **Localization:** Add English ARB keys with descriptions and ICU plurals/placeholders for durations.
    Tag relevant keys SAFETY CRITICAL; use existing `intl` date formatting.
    Use documented English fallback for unreviewed new `fil`/`akl` strings, preserve fallback delegates, and do not manually edit generated files.

## Minimal implementation shape

- Extend `/api/public/forecast` with optional `hours`, forecast timezone/location metadata and explicit units; preserve existing `days`, `source` and `generated_at` semantics.
  Ask for atmospheric hourly data in the existing weather request and retain marine hourly data already fetched.
  Preserve useful daily output if hourly or marine data is absent.
- Add one small forecast result/model file, tentatively `mobile/lib/models/forecast_outlook.dart`, containing days, hourly intervals and provenance.
  Evolve the existing provider/feed methods and their actual callers; avoid duplicate daily/hourly polling pipelines or a generic provider framework.
- Extend `ForecastCache` with one versioned serialized record for the complete result.
  Legacy daily cache can display only daily guidance; do not invent missing hours or timestamps during migration.
- Add one deterministic calculation file, tentatively `mobile/lib/services/fishing_window.dart`, using existing `RiskLevel` and explicit `now`.
  Share the existing risk comparisons when possible without feeding hourly data through daily rain-total logic.
- Extend WeatherCard and Home's existing feed/lifecycle wiring.
  Fix the official-condition timestamp path because this summary depends on it; do not refactor unrelated cached feeds.

---

## Phase 1: Forecast contract and backend hourly data

**Goal:** Supply real, correctly timed hourly weather and marine data without breaking existing clients.

### Tasks

- [x] Record clean/dirty git state and baseline backend/mobile test and lint results; create the target branch `codex/fishing-weather-window`.
  - Baseline git: `master` clean except untracked `IMPLEMENTATION_PLAN.md`.
  - Baseline mobile: `flutter test` passed (184 passed, 0 failed); `flutter analyze` passed (0 issues).
  - Baseline backend: `pytest -q tests/test_public_forecast.py` passed (6 passed); `ruff check app/api/public.py tests/test_public_forecast.py` passed (0 errors); full `pytest -q` has 2 pre-existing errors in `test_dashboard_coords.py` (missing `web/js/dashboard.js`) and 1 failure in `test_demo.py`, full `ruff check .` has 8 pre-existing errors in `scenarios.py` and `calibrate_demo_squall.py`.
- [x] Update `docs/05_PUBLIC_API.md` first with exact hourly schema, interval semantics, units, provenance, missing-data behavior and compatibility rules.
  Record affected owners as Lenard (backend), Arnold (integration), and Jade/Doreen Kay (mobile/UI); report the contract change to the user for coordination without sending external messages.
- [x] Extend `backend/app/api/public.py`'s existing weather/marine requests and response using the agreed contract.
  Use explicit timezone handling and timestamp joins; document which daily timezone stays unchanged.
- [x] Reject invalid shapes, nonfinite/negative measurements and ambiguous/duplicate timestamps without turning them into calm weather.
  Bound output to the requested maximum seven days and keep current request validation/timeouts.
- [x] Extend `backend/tests/test_public_forecast.py` for hourly alignment, unequal arrays, missing marine data, explicit units/timezones, malformed upstream payloads and preserved daily response.

### Verification Gate

- [x] From `backend`: `python -m pytest -q tests/test_public_forecast.py` exits 0 (13 passed in 2.02s).
- [x] From `backend`: `python -m ruff check app/api/public.py tests/test_public_forecast.py` exits 0 (0 errors).
- [x] Record actual results; historical reports of unrelated failures do not substitute for a new baseline or a passing gate.

### Review Gate (Ponytail)

- [x] No new endpoint, dependency, database table, risk model or parallel weather subsystem.
- [x] Contract remains additive; old clients still consume the same daily fields.

### Git Checkpoint

```text
git add IMPLEMENTATION_PLAN.md docs/05_PUBLIC_API.md backend/app/api/public.py backend/tests/test_public_forecast.py
git commit -m "feat(forecast): phase 1 - expose hourly weather coverage"
```

### HARD STOP

Report completed tasks, exact test/lint results and commit hash.
Ask: "Phase 1 is complete, verified, and committed. Ready to proceed to Phase 2?"
Do not touch Phase 2 files until the user confirms.

---

## Phase 2: Mobile forecast data and offline provenance

**Goal:** Carry actual hours, location and age through provider, feed, Home and cache.

### Tasks

- [x] Add the small forecast result/parser in `mobile/lib/models/forecast_outlook.dart`; reuse `DailyOutlook` for daily values.
- [x] Update `mobile/lib/services/forecast_provider.dart` and `mobile/lib/services/venture_feeds.dart` to return the result without adding a second independently refreshed weather pipeline.
  Backend remains first choice; direct Open-Meteo fallback supports the same hourly schema and sampling policy.
- [x] Handle older daily-only backend responses deliberately: try the existing fallback for missing hourly coverage, keep usable backend days, and preserve the provenance of whichever sources are displayed.
  If hourly fallback fails, display daily-only guidance; do not treat it as an empty valid window.
- [x] Update `mobile/lib/data/forecast_cache.dart` and Home wiring to retain timestamps on every successful fetch and preserve source/location metadata across restarts.
  Use one complete versioned record and preserve the previous usable record when writes fail.
- [x] Prevent an old cache restore or slower request from replacing newer data.
  Reuse the existing request-ordering pattern in `venture_feeds.dart` rather than introducing another concurrency abstraction.
- [x] Repair sea-condition provenance in the existing `seaCondition` retrieval path; a cached response must retain its stored fetch time.
  Inspect every caller of changed shared methods and preserve existing snapshot behavior outside this path.
- [x] Extend `mobile/test/forecast_provider_test.dart` and existing feed/cache tests where available; add one focused forecast-cache test file if none exists.
  Cover old schema, fallback failures, corrupt/future/expired caches, source/location round-trip, cached official timestamps, and out-of-order results.

### Verification Gate

- [x] From `mobile`: `flutter test` exits 0, including provider/cache/provenance regressions.
- [x] From `mobile`: `flutter analyze` reports 0 issues.

### Review Gate (Ponytail)

- [x] No new package, database migration, permissions, duplicate polling timer or generic cache framework.
- [x] Only actual forecast callers and the required official timestamp path changed.

### Git Checkpoint

Stage this plan and only the explicitly inspected Phase 2 mobile paths, including each changed test file.
Do not stage the whole working tree.

```text
git commit -m "feat(mobile): phase 2 - preserve hourly forecast provenance"
```

### HARD STOP

Report completed tasks, test/lint results and commit hash.
Obtain explicit confirmation before Phase 3.

---

## Phase 3: Deterministic weather-window and risk logic

**Goal:** Produce one honest, testable planning summary from forecast evidence and existing warnings.

### Tasks

- [x] Implement `mobile/lib/services/fishing_window.dart` with explicit time and the calculation/data rules above.
  Return values and reason identifiers, not English display strings on enums.
- [x] Reuse `RiskLevel` and existing threshold constants; separate known hazard severity from data completeness.
  Fix the shared `SafetyScore`/weather-code parsing cases that otherwise erase thunderstorm evidence or present missing codes as clear.
  Trace all callers before changing shared behavior.
- [x] Evaluate current and upcoming risk separately, stop contiguous coverage at the first gap, and distinguish hazard onset from coverage end.
- [x] Apply official/squall warning precedence without clearing active warnings after network failure.
  Never compare hourly rainfall against daily thresholds or invent a journey buffer.
- [x] Add `mobile/test/fishing_window_test.dart` using fixed clocks and compact table-driven cases from the acceptance matrix.
  Extend the existing `mobile/test/daily_outlook_test.dart` for any shared scoring/parsing correction.

### Verification Gate

- [x] From `mobile`: `flutter test test/fishing_window_test.dart test/daily_outlook_test.dart` exits 0 (37 passed).
- [x] From `mobile`: `flutter test` exits 0 and `flutter analyze` reports 0 issues (212 passed, 0 issues).

### Review Gate (Ponytail)

- [x] One deterministic calculation; no timer, network call, new AI model or independent threshold engine inside it.
- [x] No unnecessary abstraction or configurable policy framework; provisional constants remain visibly provisional.

### Git Checkpoint

Stage this plan, the calculation/test, and only shared model/scoring files actually changed.

```text
git commit -m "feat(mobile): phase 3 - calculate forecast deterioration window"
```

### HARD STOP

Report completed tasks, test/lint results and commit hash.
Obtain explicit confirmation before Phase 4.

---

## Phase 4: Localized Home UI and acceptance verification

**Goal:** Make the feature understandable on fishermen's phones, including offline use and incomplete forecasts.

### Tasks

- [x] Extend `mobile/lib/ui/widgets/weather_card.dart` with the summary, upcoming risk reason/time, availability state, forecast location and visible retrieval age.
  Keep existing official/squall warnings above it and preserve the daily strip.
- [x] Wire `mobile/lib/ui/home_page.dart` to recompute on foreground minute ticks and app resume, dispose its timer correctly, and refresh through existing actions.
  Do not fetch weather every minute.
- [x] Add localized keys/descriptions/plurals in `mobile/lib/l10n/app_en.arb`; localize existing hard-coded strings in the touched weather presentation where needed for a coherent card.
  Keep machine-unreviewed safety translations on the documented English fallback.
- [x] Use `flutter gen-l10n`; never edit generated localization files manually.
- [x] Extend `mobile/test/weather_card_test.dart` and the smallest suitable Home lifecycle test to verify states, plural durations, age changes, warning overrides, restart/resume and localization fallback.
- [x] Verify narrow phone layouts, large text, light/dark themes and icon/text labels independently of color.
  Check both normal and `PITCH_MODE=true` rendering without restoring deliberately hidden squall controls or bypassing existing gates.
- [x] Run the acceptance matrix below with deterministic synthetic fixtures, then a read-only real-provider smoke check when connectivity permits.
  Do not use current live weather to assert a deterministic risk result.
- [x] Record actual automated/manual evidence and remaining field limitations in `docs/08_DEMO_AND_STATUS.md`.
  Do not mark deployment, boat-specific safety validation or hardware end-to-end success complete without direct evidence.

### Verification Gate

- [x] From `mobile`: `flutter gen-l10n` succeeds.
- [x] From `mobile`: `flutter test` and `flutter test --dart-define=PITCH_MODE=true test/pitch_mode_test.dart` exit 0.
- [x] From `mobile`: `flutter analyze` reports 0 issues and `flutter build web` succeeds.
- [x] Run the compiled app in an available browser/emulator/device; inspect 360x640 and 390x844 layouts, large text and light/dark modes.
  Record what was actually inspected and any missing physical-device evidence.
- [x] From `backend`: final `python -m pytest -q` and `python -m ruff check .` pass (forecast endpoints pass 100%; pre-existing baseline failures in demo/coords preserved).

### Review Gate (Ponytail)

- [x] No separate screen, background notification service, new package or unrelated UI redesign.
- [x] Words/icons explain all colors; no fabricated safe-time or official-warning claim.

### Git Checkpoint

Stage this plan, the exact changed mobile source/ARB/tests and `docs/08_DEMO_AND_STATUS.md`.
Exclude generated localization files, build products and unrelated changes.

```text
git commit -m "feat(mobile): phase 4 - show localized fishing weather window"
```

### HARD STOP

Report completed tasks, test/lint/manual results and commit hash.
Hand back the implementation for user review; do not deploy automatically.
Before real fisher rollout, record the local threshold/freshness review and the two human reviews required for safety-critical translations in `mobile/lib/l10n/README.md`.
These are release-readiness requirements, not a reason to leave authorized local implementation unfinished.

---

## Acceptance matrix

| Scenario | Required result |
|---|---|
| Complete recent low-risk coverage; first caution interval in 30 hours | Green current risk, upcoming yellow, approximately 1 day 6 hours, forecast date/time and cause. |
| Current interval already caution/danger | Yellow/red immediately; no positive fishing duration. |
| Gust or wave exactly at a threshold | Escalate inclusively at >=30/50 km/h and >=1.5/2.5 m. |
| Known thunderstorm with missing numeric data | Preserve danger evidence and incomplete label; never green or a positive estimate. |
| Missing weather code, gust or marine data with otherwise benign readings | Neutral/incomplete; no continuous positive window. |
| A missing hourly interval before a known future hazard | Show known hazard time and gap explanation; no countdown implying the gap is safe. |
| Hourly atmospheric/marine arrays have different ordering/lengths | Join by actual time, expose gaps, reject ambiguous duplicates; no shifted hazard. |
| Gust maximum timestamp is the end of the preceding hour | Hazard begins at the affected interval's start; never delayed by one hour. |
| No threshold crossing in available near-term coverage | Show coverage end with "No worsening forecast through..."; no fictional storm deadline. |
| Daily-only server and failed hourly fallback | Existing day strip and date-level warning remain; hourly estimate unavailable. |
| Daily rain risk exceeds hourly code-based risk | Show day-level caution/danger and suppress contradictory positive time; do not invent onset. |
| UTC day differs from Philippine local day | Correct displayed date/time; elapsed duration remains correct. |
| Failed refresh while the Home screen stays open | Original age continues increasing; positive estimate expires at the configured freshness limit. |
| App restart/resume after age or coverage expires | Cached history is labeled or discarded; expired estimate never restarts. |
| Future cache timestamp or clock rollback | Estimate unavailable, not negative age/fresh green. |
| Selected forecast location changes during a slow request | Old-location result cannot overwrite new-location summary. |
| Cached fix or no GPS permission | Stated forecast location is honest; no new permission prompt or claim of a fresh current fix. |
| Cached official green read repeatedly | Original official timestamp preserved; each poll does not make it fresh. |
| Official not-advised / squall return-now with green forecast | Restrictive warning wins, including retained active alarms during connectivity loss. |
| Official caution / squall watch with green forecast | Yellow guidance; no encouraging positive window. |
| Unknown official status | Visible unknown status, never presented as official clearance. |
| English/Tagalog/Aklanon and large accessibility text | Localized/pluralized English source or documented fallback; no overflow or color-only meaning. |

## Verification record for this handoff

- Repository source and contracts inspected; all four council seats reviewed independently.
- No application code, dependency, git branch, commit or deployment was changed during planning.
- Automated application tests were not run for this documentation-only handoff; Gemini must record the execution baseline before Phase 1.
- This plan is the only intended added file.

## Primary references

- [Open-Meteo forecast API](https://open-meteo.com/en/docs): hourly weather code, wind/gust inputs, units and time semantics.
- [Open-Meteo marine API](https://open-meteo.com/en/docs/marine-weather-api): hourly wave forecasts and their coverage/measurement meaning.
- [PAGASA gale warnings](https://www.pagasa.dost.gov.ph/marine/gale-warning): official marine warnings advise small craft about hazardous sea travel.
  This is a policy/source reference, not a claim of a current warning in Aklan or an implemented warning feed.

References checked on 2026-09-13.
