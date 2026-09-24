# Track W - Web dashboard (edge-case remediation)

Master plan: `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md` (read Sections 1 to 4 first).
Design: `docs/61_EDGE_CASE_REMEDIATION_DESIGN.md`.
**Execution mode:** hard-stop
Branch and worktree: `edge/web`, `../AqOne-edge-web`
Owns: `web/**`.
Approved: with the master plan, Revision 1, 2026-09-24.
Evidence: `docs/edge-remediation/EVIDENCE-web.md`.
State: Awaiting approval

## Rules for this track

- **Architecture.**
  The dashboard renders what the backend decides.
  It never re-implements triage order, lifecycle rules, trust tiers or plausibility; it shows the fields in master plan Section 3.
  Any pure display helper (coordinate formatting, byte counting, relative time) goes in `web/js/dashboard-utils.js`, which the tests already load with `require`.
- **Clean code.**
  - One function per UI behaviour.
  - Handlers read top-down: collect input, call the API, render the result.
  - Delete dead fallbacks instead of commenting them out, such as `|| 20` in `dashboard-incidents.js:304`.
- **Visual rules** come from `docs/47_VISUAL_DESIGN_GUIDE.md`, updated in Phase 0.
  Look at every changed screen in a real browser, in light and dark, at 1280 px and 1920 px wide.
  Fix anything that looks off, even outside the phase, and note it in the evidence file.
- **Tests first.**
  Write each phase's tests with the existing `vm` and stub-element harness (see `web/test/dashboard-alarm.test.js`), and record the red run in the evidence file before changing `web/js/`.
- **Merge after.**
  Before opening a PR, confirm that the listed backend phases are merged on `master`.
  The dashboard and API deploy together from one Render service.
- **Gate commands** (every phase), run from the repository root:

  ```powershell
  node --test web/test/*.test.js
  Get-ChildItem web/js, web/test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
  ```

---

## Phase W1: Alarm that rings for waiting calls, and honest display

Requirements: EC-C6 (dashboard), EC-L9, EC-L11 (formatting)
Merge after: Phase 0 (no backend dependency)
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `web/test/dashboard-alarm.test.js` additions:
    - `first load rings when any event is unacknowledged`
    - `first load stays silent when every event is acknowledged`
    - `audio-locked state shows the enable-sound banner until a click resumes audio`
    - `a new SOS raises a browser Notification when permission is granted` (stub `Notification`)
    - `document title flashes while an unacknowledged SOS exists`
  - `web/test/dashboard-utils.test.js` additions: `formatLatLon` produces `11.7000° N, 122.4000° E`, `11.7000° S, 122.4000° W` for negative values, and `unknown position` for null.
  - `web/test/dashboard-reaudit.test.js` addition: `SOS title uses vessel id with the boat name quoted, never the boat name alone`.
- [ ] `dashboard-live-sos.js`:
  - On first load, call `ns.sosAlarm.sync(events)`, and start the alarm when any event is unacknowledged.
    Keep the toast gating for events that are truly new.
  - Replace the inline `'° N'` and `'° E'` string with `formatLatLon`, and grep for any other coordinate strings in `web/js`.
  - The title is `SOS - <vessel id>`, with `"<boat>"` as a subtitle.
- [ ] `dashboard-alarm.js`: track whether an `AudioContext` has been resumed.
  Until then, show a persistent `#alarm-sound-banner` ("Alarm sound is OFF - click to enable").
  On a new call, flash `document.title` and, if permission is granted, create a `Notification`.
  Ask for Notification permission from the banner click, never on load.
- [ ] `web/html/dashboard.html` and CSS: the banner markup, styled as an error state per docs/47.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Browser check, with screenshots referenced in the evidence file:
  - load the dashboard with an unacknowledged SOS in the feed; the banner shows and the alarm starts after one click
  - put the tab in the background; a desktop notification appears for a new SOS

### Review and checkpoint

- [ ] Update this file, the evidence file and `HANDOFF.md`; stage only `web/**` and this track's docs; commit; open the PR.

Checkpoint message: `fix(dashboard): ring for waiting SOS on load and show honest coordinates`

---

## Phase W2: Resolve and acknowledge dialogs that cannot misfire

Requirements: EC-C7, EC-H4, EC-M8, EC-M1, EC-M9 (dispatcher visibility)
Merge after: W1 and B1
State: Awaiting approval

### Tasks

- [ ] Write red tests in a new `web/test/dashboard-incidents.test.js`:
  - `resolve needs a reason and a confirmation`
  - `resolve posts reason_code and expected_version for the event the dialog opened on, even if the list re-renders`
  - `resolve success shows Undo for 10 seconds, and Undo posts reopen`
  - `ack defaults to no ETA`
  - `ETA quick buttons set eta_minutes and preview the arrival clock time`
  - `note over 40 UTF-8 bytes disables Send and shows the counter in error`
  - `409 shows the current answer and requires a second confirmation`
  - `a reopened incident rings again`
  - `utf8ByteLength("ñ") === 2` in `dashboard-utils.test.js`
- [ ] `web/html/dashboard.html`:
  - Add a resolve dialog with a radio group of the five codes from `docs/13_RESPONDER_LOOP.md`.
    The labels are dashboard copy; the values are the codes.
    Include the event's vessel, boat and pressed time, and a Confirm button that stays disabled until a reason is chosen.
  - In the acknowledge dialog, add a "No ETA yet" chip, selected by default, and replace the `value="20"` default.
    Quick chips are 15, 30, 45, 60, 90 and 120 minutes.
    Add a preview line ("arrives about 14:35") and a byte counter under the note.
- [ ] `dashboard-incidents.js`:
  - The resolve handler opens the dialog bound to a snapshot of the event (`id` and `version`).
    It posts `{reason_code, expected_version}`, then shows an Undo toast that posts `/reopen`.
  - The acknowledge handler sends `eta_minutes: null` for "No ETA yet", `expected_version`, and a note of 40 bytes or fewer.
    Remove the `|| 20` fallback.
  - On 409, render `current` ("Answered by <acked_by> at <time>: <status>, ETA <time or none>") and require the dispatcher to re-confirm.
- [ ] `dashboard-live-sos.js`: an event whose `reopened_at` is newer than the last seen value counts as new for the alarm and toast.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Browser check against a local backend with B1:
  - resolve with a reason, then undo
  - two tabs acknowledge the same event, and the second shows the conflict
  - a 45-byte note is blocked

### Review and checkpoint

As in W1.
Checkpoint message: `feat(dashboard): reasoned resolve with undo, honest ETA, and conflict-safe acknowledgements`

---

## Phase W3: Triage view, flags, late calls and flood handling

Requirements: EC-H18, EC-H20, EC-H15 (dashboard), EC-M3, EC-H19 (wording)
Merge after: W2, B2 and B4
State: Awaiting approval

### Tasks

- [ ] Write red tests in `web/test/dashboard-live-sos.test.js` (new):
  - `renders events in the order received and never re-sorts`
  - `shows +N more when total exceeds the rendered count`
  - `flood banner appears when flood.active`
  - `alarm starts once per burst, not once per row, while flood.active`
  - `late badge shows "LATE - pressed 3 d 4 h ago" from pressed_at`
  - `flags render as neutral tags with the docs/47 labels`
  - `alt position renders a second marker labelled "conflicting position"`
  - `open_calls_for_vessel > 1 shows "2 calls from this vessel"`
  - `pod delivery reads "Relayed by pod <id> - sender not verified"`
- [ ] `dashboard-live-sos.js`:
  - Request `/api/sos/active?limit=200`.
  - Render in the order received.
  - Show a footer with `total - events.length` more.
  - Show the flood banner.
  - While `flood.active`, start the alarm only when the burst begins.
- [ ] Add rendering helpers in `dashboard-utils.js`: `lateLabel(pressedAt, now)`, `flagLabel(flag)` and `deliveryLabel(event)`.
- [ ] `dashboard-markers.js`: a second, hollow marker for `alt_latitude` and `alt_longitude`, with a tooltip.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Browser check against a local backend with B4: post 500 anonymous calls with a script, plus one from a vessel with trip history.
  The dashboard stays responsive (record the frame rate or subjective lag), the known vessel is first, the flood banner shows, and the alarm does not stutter.

### Review and checkpoint

As in W1.
Checkpoint message: `feat(dashboard): triage-ordered SOS list with flags, late badges, and flood control`

---

## Phase W4: Trust badges, operations status, sessions and AI honesty

Requirements: EC-H10 (dashboard), EC-M6 (dashboard), EC-M18, EC-H12 (visibility), EC-C5 (banner), EC-H6 (dashboard), EC-M17 (dashboard)
Merge after: W3, B3, B5, B6 and B7
State: Awaiting approval

### Tasks

- [ ] Write red tests:
  - `dashboard-live-sos.test.js` additions:
    - `verified vessel shows "Verified by MDRRMO"`
    - `unverified vessel shows neutral grey text and no coloured badge, and does not change card colour`
    - `anonymous phone shows "unverified number"`
    - `shore contact renders in the drawer`
    - `Confirm vessel posts /api/vessels/{id}/confirm`
  - `dashboard-runtime.test.js` additions:
    - `ops status shows gateway last heard and turns red when stale`
    - `SMS not configured banner`
    - `DB expiry banner at 7 days or fewer`
    - `token refresh is called when less than 24 h remain and the session is active`
    - `expiry warning 1 h before`
  - `dashboard-ai-ops` test (in `dashboard-runtime.test.js`):
    - `monitoring unavailable renders "Not monitoring - no live contact source" instead of the empty-state text`
    - `check_needed status renders`
    - `drift clock_suspect shows the note`
- [ ] `dashboard-live-sos.js`:
  - Remove the licence-derived display, and never show an "unregistered" or yellow badge.
  - Render `vessel_verified`, `phone_set_by`, the shore contact, and a "Confirm vessel" action (responder roles only; hide it for the viewer role).
- [ ] Create a small new module `web/js/dashboard/dashboard-ops-status.js`, loaded like the others in `dashboard.html`.
  It polls `/api/ops/status` every 60 s and renders the gateway indicator, the SMS banner and the DB-expiry banner.
- [ ] `dashboard-core.js`: call `/api/token/refresh` from the existing auth flow when the token's `exp` is less than 24 h away and the page is in use.
  Show an expiry banner 1 h before.
- [ ] `dashboard-ai-ops.js`: handle `monitoring` and `monitoring_reason` (around `:628`), the `check_needed` status, and a `clock_suspect` note on the drift panel.

### Verification

- [ ] Gate commands green, with red and green runs recorded.
- [ ] Browser check against a local backend with B3 to B7, with `DB_EXPIRES_AT` set 5 days ahead and no SMS credentials.
  Both banners show; stopping the downlink poller turns the gateway indicator red after about 2 min 15 s.

### Review and checkpoint

As in W1.
Checkpoint message: `feat(dashboard): positive-only trust badges, operations status, and honest AI states`

## Recovery

Follow project `AGENTS.md` for the three-attempt limit.
Record unresolved work and attempt counts in this worktree's `HANDOFF.md`.
