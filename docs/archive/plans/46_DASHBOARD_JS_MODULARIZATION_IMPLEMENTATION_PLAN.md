# dashboard.js modularization - implementation plan for Luna

**Status:** COMPLETE (archived 2026-09-25). `web/js/dashboard.js` is split into `web/js/dashboard/*.js`, loaded as plain scripts from `web/html/dashboard.html`.

## Context

`web/js/dashboard.js` is 4,165 lines / 181 KB, all inside a single `(function () { 'use strict'; ... })()` IIFE, loaded by `web/html/dashboard.html` only (confirmed: no other HTML file references it — `Systemprofile.html` loads `profile.js`, not this file). Runtime performance is fine as-is; the problem is maintainability. The site has no bundler and no build step — pages just include plain `<script src="...">` tags in order. **Preserve that.** Do not introduce webpack/vite/esbuild/ES module `type="module"` imports unless Lenard explicitly asks for that later. The output of this work is still plain scripts loaded in sequence, just many small files instead of one 4,165-line file.

Goal: split `dashboard.js` into focused files under a new `web/js/dashboard/` directory, wired together through one shared namespace object, with zero behavior change to the running dashboard.

## Non-negotiable rules

1. **Commit after every single extraction step**, not one commit at the end. Each commit should be small enough that `git diff` for it is easy to review, and the working tree must be in a runnable state after every commit (dashboard.html loads without console errors). Use conventional commit-ish messages, e.g. `refactor(dashboard): extract map/markers into dashboard-markers.js`.
2. **No behavior changes** except the two specific dead-code cleanups called out in "Known issues" below — and even those get their own dedicated commit with an explicit message, never silently folded into a move.
3. **Do not change script loading order semantics** — later files can rely on globals set up by earlier files, exactly like the current file relies on top-to-bottom execution order within the IIFE.
4. **Do not touch** `dashboard-utils.js`, `advisoryService.js`, `dangerZoneModel.js`, `dangerZonePredictor.js`, or any HTML/CSS file's content beyond the `<script>` tags needed to include the new files, unless a step below says otherwise.
5. If at any point you're not sure whether a function/variable is used outside the section you're extracting, **grep the whole original file for it before moving it** (see "Extraction procedure" step 2). Do not guess.
6. Work on a branch: `git checkout -b refactor/dashboard-js-modules` before the first commit. Do not merge into main/master yourself — Lenard will review and merge.

## Target layout

```
web/js/dashboard/
  dashboard-core.js            (helpers, config, auth, current user, sample data, map init, layer groups)
  dashboard-markers.js         (marker creation, gateway/buoy markers, coverage circles, mesh network, incident markers, boundary)
  dashboard-tools.js           (pin tool, measure tool, layer switcher, rail panel system, toolbox scroll, toggle layers)
  dashboard-panels.js          (stats panel, legend, tab switching)
  dashboard-vessels-alerts.js  (vessel data, alert data)
  dashboard-live-sos.js        (live SOS feed, feed freshness)
  dashboard-sar.js             (SAR metrics tab)
  dashboard-incidents.js       (incident drawer, acknowledge-with-ETA, incident feed)
  dashboard-buoy-health.js     (buoy health monitor, viewport stats, coordinates, home/recenter, fullscreen, center-on-region, export)
  dashboard-ai-ops.js          (AI operations: drift contours, squall watch, risk feed — the big one, ~580 lines)
  dashboard-profile-pill.js    (user profile pill, theme toggle, language translations, in-dashboard profile-tab UI)
  dashboard-shortcuts-weather.js (keyboard shortcuts, weather)
  dashboard-emergency-advisory.js (emergency contacts modal, advisory panel)
```

`dashboard.js` itself goes away once every section has been extracted and `dashboard.html` points at the new files instead.

The line numbers below are from the *current* file, as a map to the section comments (`// ===== SECTION NAME =====`) already in the code — they will drift after your first extraction, so **always locate sections by their comment header, never by line number, after step 1.**

| Target file | Section headers to move (in order) |
|---|---|
| dashboard-core.js | SHARED HELPERS, CONFIG, API + AUTH, CURRENT USER, USER COLOR HASH, SAMPLE DATA, MAP INIT, LAYER GROUPS |
| dashboard-markers.js | MARKER CREATION, GATEWAY MARKERS, BUOY MARKERS, COVERAGE CIRCLES, MESH NETWORK, INCIDENT MARKERS, BOUNDARY |
| dashboard-tools.js | PIN TOOL, MEASURE TOOL, LAYER SWITCHER, RAIL PANEL SYSTEM, TOOLBOX SCROLL OVERFLOW, TOGGLE LAYERS |
| dashboard-panels.js | STATS PANEL, LEGEND, TAB SWITCHING |
| dashboard-vessels-alerts.js | VESSEL DATA (phone–buoy contact events), ALERT DATA (confidence-scored, escalation ladder) |
| dashboard-live-sos.js | LIVE SOS FEED, FEED FRESHNESS (LIVE / STALE / OFFLINE) |
| dashboard-sar.js | SAR METRICS TAB |
| dashboard-incidents.js | INCIDENT DRAWER, ACKNOWLEDGE WITH ETA |
| dashboard-buoy-health.js | INCIDENT FEED, BUOY HEALTH MONITOR, VIEWPORT-BASED STATS, COORDINATES, HOME / RECENTER, FULLSCREEN, CENTER ON REGION, EXPORT |
| dashboard-ai-ops.js | AI OPERATIONS, EXIT LOADING (first occurrence) |
| dashboard-profile-pill.js | USER PROFILE PILL, EXPORT (2nd occurrence), EXIT LOADING (2nd occurrence), THEME TOGGLE, LANGUAGE TRANSLATIONS, PROFILE PAGE (tabs/save/logout) |
| dashboard-shortcuts-weather.js | KEYBOARD SHORTCUTS, WEATHER |
| dashboard-emergency-advisory.js | EMERGENCY CONTACTS MODAL, ADVISORY PANEL |

That failsafe `window.addEventListener('error', ...)` block at the very top of the current file (before the `SHARED HELPERS` comment) goes into `dashboard-core.js` too, first thing, unchanged — it must stay the very first thing that executes.

## Shared namespace pattern

Every extracted file wraps itself in its own IIFE and reads/writes a single shared object, `window.AqOneDashboard`, for anything another file needs. Everything else — locals, helper functions only used within that one section — stays a closure-local `var`/`const`/`function`, exactly as today. Do not put things on the shared namespace "just in case"; only put things there that step 2 of the extraction procedure actually finds a cross-file reference for.

Pattern for every file after `dashboard-core.js`:

```js
(function (ns) {
  'use strict';

  // destructure what this file needs from earlier files
  var map = ns.map;
  var layers = ns.layers; // e.g. { gatewayLayer, incidentLayer, buoyLayer, ... }
  var authFetch = ns.authFetch;
  var escapeHtml = ns.escapeHtml;
  // ...only what this file actually uses

  // ...section code goes here, unchanged from the original...

  // if anything in this file is called from a later file, attach it:
  ns.renderAlerts = renderAlerts;

})(window.AqOneDashboard = window.AqOneDashboard || {});
```

`dashboard-core.js` is the one file that *creates* `window.AqOneDashboard` and seeds it with the foundational shared state: `map`, the layer groups object, `dashboardUtils`/`escapeHtml`/`classifyFreshness`/`freshnessLabel`/`alertBadge`, `authFetch`/`getToken`/`clearSession`/`redirectToLogin`, `CURRENT_USER`/`CURRENT_USER_COLOR`, `API_BASE`, and the sample-data arrays (`shoreStations`, `initialBuoys`, `incidents`, `meshLinks`, `opsBoundary`) since multiple later sections read these.

## Extraction procedure (repeat for each target file, in the order listed above)

1. Open the current `dashboard.js` (or whatever's left of it) and locate the section(s) for this target file by their `// ===== ... =====` header comments.
2. **Before cutting anything**, grep the *entire remaining file* (not just this section) for every function name and every top-level `var`/`let`/`const` name declared in this section. For each one that has a call/reference site outside the section you're extracting, note it — it needs to go on `window.AqOneDashboard` (or, if the *caller* is in a section you haven't extracted yet, note the dependency and come back to wire it once both sides are extracted).
3. Cut the section's code into the new file, in the shared-namespace IIFE pattern shown above. Keep code otherwise byte-for-byte identical — same logic, same comments, same variable names. This is a move, not a rewrite.
4. For every name identified in step 2 as cross-referenced, expose it via `ns.<name> = <name>;` in the file that defines it, and read it as `var <name> = ns.<name>;` in the file(s) that consume it.
5. Delete the moved code from `dashboard.js`.
6. Add the new file's `<script src="../js/dashboard/dashboard-xxx.js"></script>` tag to `web/html/dashboard.html`, in the same relative position the original code executed (i.e., new files load in the same left-to-right order the sections originally ran in, and always after `dashboard-core.js`). Leave the existing `dashboard.js` script tag in place until it's empty at the very end, so the page keeps working after every single step.
7. Sanity-check: open `dashboard.html` (or ask Lenard/the team to) and confirm no new console errors, and that the feature(s) in the moved section still work (map loads, markers render, panel opens, etc. — whatever's relevant to that section). If you don't have a way to load the page yourself, at minimum verify with `node --check` (or a browser-less JS parser) that both the new file and the shrunk `dashboard.js` are syntactically valid, and grep to confirm no leftover references to now-moved identifiers remain in `dashboard.js`.
8. Commit: `git add -A && git commit -m "refactor(dashboard): extract <section names> into dashboard-<name>.js"`.

Do not batch multiple target files into one commit, and do not move on to the next file until the current one is committed and step 7's check is clean.

## Known issues to handle explicitly while you're in there

These are two things I found by inspection. Handle them as their own commits, separate from the pure code-move commits, so they're easy to revert individually if Lenard disagrees:

1. **Dead duplicate `relativeTime`.** There are two functions named `relativeTime` in the current file: one at the top of the PIN TOOL area (takes a `date` object, `Date.now() - date`) and one in the LIVE SOS FEED area (takes an ISO string). Grep confirms the first one (the PIN TOOL version) has **zero call sites anywhere in the file** — it's dead code. When you extract PIN TOOL into `dashboard-tools.js`, drop that unused `relativeTime` function entirely and say so in the commit message (e.g. `refactor(dashboard): extract pin/measure tools into dashboard-tools.js; drop unused relativeTime(date) — zero call sites`). Keep the LIVE SOS FEED version (it's actively used) when you extract `dashboard-live-sos.js`.
2. **Duplicate `EXPORT` and `EXIT LOADING` section headers.** There are two sections each named `EXPORT` and `EXIT LOADING` (one pair around AI OPERATIONS, one pair around USER PROFILE PILL/THEME TOGGLE). Before extracting `dashboard-ai-ops.js` and `dashboard-profile-pill.js`, read both `EXPORT` sections and both `EXIT LOADING` sections in full and confirm whether they're genuinely different code (e.g. one exports incident data, the other exports something else; one hides the loading overlay on the AI-ops path, the other on the general init path) or an actual accidental duplicate. If they do different things, keep both, one in each target file, and note in the commit message what each does. If either pair turns out to be a true copy-paste duplicate doing the same thing, keep the one that's actually reachable/called and flag the other for Lenard rather than silently deleting it — leave a `// TODO(luna): possible duplicate of dashboard-ai-ops.js:<fn> — confirm with Lenard before removing` comment instead of removing it yourself.
3. **The in-file "PROFILE PAGE: TABS, SAVE HANDLERS, LOGOUT (from profile.html)" section.** This code lives inside `dashboard.js` but `dashboard.html` is the only page that loads `dashboard.js` — the actual profile page (`Systemprofile.html`) loads a separate `profile.js`, not this file. So this section is either (a) dead code that should never have been copy-pasted into `dashboard.js`, or (b) powers some profile-related UI embedded directly in the dashboard page (e.g. a settings tab inside the dashboard rather than the full profile page). Check `dashboard.html` for the DOM elements this section's `document.getElementById(...)` calls reference (tab buttons, save handlers, logout button) — if they exist in `dashboard.html`'s markup, it's live and belongs in `dashboard-profile-pill.js` as planned. If those DOM IDs don't exist anywhere in `dashboard.html`, it's dead code: move it into `dashboard-profile-pill.js` anyway (don't delete it — that's a bigger call than this refactor should make on its own) but add a `// TODO(luna): no matching DOM elements found in dashboard.html — appears unreachable, confirm with Lenard` comment above it, and call this out explicitly to Lenard when you report progress.

## Order of operations

1. Branch: `git checkout -b refactor/dashboard-js-modules`.
2. `dashboard-core.js` first, always — everything else depends on it.
3. Then `dashboard-markers.js` (depends only on core).
4. Then `dashboard-tools.js`, `dashboard-panels.js` (mostly self-contained, low risk — good to bank early wins and catch pattern issues before the bigger files).
5. Then `dashboard-vessels-alerts.js`, `dashboard-live-sos.js`, `dashboard-sar.js`, `dashboard-incidents.js`, `dashboard-buoy-health.js` — these reference each other somewhat (e.g. alert rendering, SOS markers, incident drawer all touch overlapping data), so extract them in this order and double-check step 2 (the cross-reference grep) carefully for this cluster.
6. Then `dashboard-ai-ops.js` (large, mostly self-contained feature — do it after the smaller ones so you've got the pattern down).
7. Then `dashboard-profile-pill.js`, `dashboard-shortcuts-weather.js`, `dashboard-emergency-advisory.js` to finish.
8. Once `dashboard.js` is empty, delete it, remove its now-unused `<script>` tag from `dashboard.html`, and commit: `refactor(dashboard): remove now-empty dashboard.js`.
9. Final pass (its own commit): re-read every new file's top-of-file `var ... = ns....` destructuring block and delete any that turned out to be unused after the moves (this will happen — some things you thought were cross-referenced won't be once code shifts around). Re-run the console-error check on `dashboard.html` one more time.

## Definition of done

- `web/js/dashboard.js` no longer exists.
- `web/js/dashboard/` contains the 13 files listed above, each under ~600 lines.
- `dashboard.html` loads all 13 files (plus the pre-existing `advisoryService.js`, `dangerZoneModel.js`, `dangerZonePredictor.js`, `dashboard-utils.js`) in an order that reproduces current behavior exactly.
- No console errors on load; every panel/tool/tab you can exercise still works the same as before the refactor.
- Every commit is scoped to one file extraction or one flagged cleanup — `git log` on the branch reads as a clean, reviewable sequence, not one giant squash.
- The two TODO comments (if either duplicate/dead-code question resolves to "flag, don't delete") are visible in the diff for Lenard to review, called out by name in your final summary to him.
