# Implementation Plan: dashboard tutorial (demo) mode

**Status:** COMPLETE - Revision 2, built and verified 2026-09-27
**Owner:** Lenard (approval); implemented by Claude Code on `master`
**Created:** 2026-09-26T23:05:00+08:00
**Updated:** 2026-09-27T16:15:00+08:00
**Related:** `docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md`, `docs/audits/DASHBOARD_DRIFT_TRIP_RENDER_AUDIT_2026-09-26.md`, `docs/05_PUBLIC_API.md`, `docs/53_EXTERNAL_DEADLINES.md`, `docs/demo-mode/EVIDENCE.md`, `tools/render-check/README.md`

Revision: 2
**Execution mode:** auto (Len: "We will finish this demo today lets just update the docs after we're done")
Feature spec and revision: Len's chat request of 2026-09-26 (Revision 1) and Len's answers of 2026-09-27 to the second council (Revision 2, below).
Approved baseline and architecture revisions: `docs/Aqone_PRD (2).md` v3.0; `docs/05_PUBLIC_API.md` as amended by this plan.
Len's chat approval: 2026-09-27, answers to Q1-Q6 of the second council deliberation, recorded under "Revision 2 decisions".
Target branch: `master` (Len's push-direct rule).

Success condition: a presenter or responder can open the dashboard as a set of short, skippable lessons filled with data recorded from the real backend, on the deployed site or with no network, never mistake it for live operations, and return to a live dashboard that shows only what the backend reports.

## Why

Plan 71 removed the hard-coded sample vessels because they were shown as real, under the LIVE badge, next to real rows.
Sample data is still valuable for pitches, training and venues without a signal (`docs/53`: RSTW 2026-10-01 to 10-03, Enactus 2026-10-09 to 10-10 in Manila).
The honest form of it is a mode the viewer chooses and can always see, that never mixes with live data.

## Council deliberation, first pass (2026-09-26)

The first council recommended one demo data source behind the dashboard's fetch seam, all-demo or all-live per tab, no `/api/*` calls in demo mode, an always-visible banner, and deleting every scattered sample literal.
Its full text is in this file's git history (Revision 1).

## Council deliberation, second pass (2026-09-27)

Checked against `master` after Plan 71, the second council found:

- The live dashboard still invented figures: `Math.max(4, ...)` buoys online, coverage `68 + 4n %`, a fixed `45 min` lead time, five hard-coded buoys and a sample squall incident, and a "Displaying sample data" note beside live numbers.
- `GET /api/public/buoys` placed every registered buoy at one of two invented positions, and returned an invented mesh when the table was empty.
- Four data paths bypass `authFetch` (hotspots, advisories, two Open-Meteo calls), so a swap at `authFetch` alone would leak live data into demo mode.
- `aqoneDemoBypassActive` already meant three things; demo mode needed its own key.
- Without a network the basemap tiles fail and the map is a grey box.
- The backend scenario engine already scripts a seven-beat story; recording it beats hand-writing fixtures.

It recommended fixing the live honesty problems first, one data-source seam covering every path, a new mode key, recorded rather than authored fixtures, and replayed rather than re-implemented actions.

## Revision 2 decisions (Len, 2026-09-27)

| # | Question | Len's answer |
|---|---|---|
| Q1 | Where is demo mode entered? | A button in the profile section, as a tutorial that teaches how to use the console and what it can do, split into lessons that can be skipped and replayed one at a time, never one forced tour. |
| Q2 | Record fixtures from the scenario engine's beats? | Yes. |
| Q3 | Split into a pre-RSTW honesty fix and a later demo mode? | No: finish it today and update the docs afterwards. |
| Q4 | Laptop-only backend scenario for RSTW? | No: it must work live on the Render site too. |
| Q5 | Offline map: water-polygon fallback or grey basemap? | Polygon fallback. |
| Q6 | Enactus date and `DEMO_MODE` on Render | Enactus is 9-10 October in Manila; `DEMO_MODE` is set on Render. |

Consequences:

- A signed-in responder can enter the tutorial from the profile page, so a real SOS must still be announced there.
  The tutorial therefore keeps one read-only request to the real SOS feed (below, DEMO-02).
- The login page's offline-demo button now opens the tutorial without an account.

## Requirements

| ID | Requirement | Observable acceptance |
|---|---|---|
| DEMO-01 | The tutorial is entered from the profile page's Learn AqOne tab (any lesson) or the login page (no account); it lasts for the tab session under its own key `aqoneDashboardMode`, and a URL alone cannot switch it on. Exit returns a signed-in user to the live dashboard and a guest to the login page. | Web test on `activeLesson`; flow check: guest and signed-in entry and exit. |
| DEMO-02 | In the tutorial every request is answered from the lesson's recording; nothing reaches `/api/*`, except, for a signed-in user, a read-only poll of the real `/api/sos/active` that announces a waiting real SOS. | Flow check: no `/api/` request on the network for a guest; the real-SOS bar appears for a real unacknowledged SOS. |
| DEMO-03 | A banner and a watermark above every panel say TUTORIAL for the whole time; the feed status reads TUTORIAL, never LIVE. | Web test on script order and z-index; screenshots. |
| DEMO-04 | Lessons cover the console, squall nowcast, warning the fleet, trip checks, receiving an SOS, drift and search, and closing a case, each on its own recording, each startable directly, each step skippable. | Web test: every panel route recorded; lesson walkthrough of all seven. |
| DEMO-05 | The actions a lesson teaches (sea condition; trip check acknowledge and escalate; SOS acknowledge; drift open, searched area, rerun; SOS resolve) replay what the real backend answered; an action a lesson did not record is refused with a note and nothing is sent. | Web tests on the source; walkthrough of every action. |
| DEMO-06 | Recordings are made from the running backend by `tools/render-check/record_tutorial.mjs`, and their timestamps shift to the moment a lesson opens. | Web test on `shiftTimes`; recorder run. |
| DEMO-07 | Outside the tutorial no sample content exists in the dashboard source; the buoy network, coverage and overview figures come from the backend or read `--`. | Web source check; render check RND-04. |
| DEMO-08 | Recordings contain no real person's contact details. | Web test over the recordings. |
| DEMO-09 | When basemap tiles fail, the map draws the service-area water polygon on a plain land colour and says so. | Offline walkthrough screenshot. |

## Phases (all complete on 2026-09-27)

| Phase | Outcome | Commit |
|---|---|---|
| 1 | Live honesty: real buoy positions, radii, provenance and last-heard time from `/api/public/buoys`; the map, mesh, coverage and Buoy Network panel from that feed; measured overview figures; white-on-white metric values fixed. | `00527a3` |
| 2 | Tutorial source: `web/js/tutorial/tutorial-source.js` swaps `window.fetch` first, replays phases, shifts times, refuses unrecorded actions. | `11a0434` |
| 3 | Recorder and recordings: `record_tutorial.mjs`, `seed_tutorial.sql`, `/api/demo/squall/buoy/{id}`, seven recordings in `web/data/tutorial/`. | `11a0434` |
| 4 | Lessons and coach: `tutorial-lessons.js`, `tutorial-coach.js`, `css/tutorial.css`; Learn AqOne tab; login entry; real-SOS bar. | `11a0434` |
| 5 | Offline map fallback, the SAR tab reading the metrics envelope, resolved-call times, and the evidence walkthrough, including the deployed Render site. | `11a0434` |

Evidence: [`demo-mode/EVIDENCE.md`](demo-mode/EVIDENCE.md).

## Known limits

- The recorded SOS was pressed three hours before it arrived and came in directly, not through a buoy: that is how the presenter scenario writes it.
- A searched area the learner draws is replaced by the one the recorder drew; the lesson says so.
- The recordings follow today's API shapes; re-record with `record_tutorial.mjs` when a route the dashboard reads changes (the lesson tests catch a missing target or action, not a changed field).
- The handset's `PITCH_MODE` does not use these recordings.
