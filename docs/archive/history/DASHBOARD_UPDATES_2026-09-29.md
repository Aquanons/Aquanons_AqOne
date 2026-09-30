> **Archived 2026-09-30.** Record of Jade's dashboard changes of 2026-09-28 and 2026-09-29, moved from the repository root. It is history, not current state.

# Dashboard Updates Summary (Jade-backup)

All changes below are on branch `Jade-backup`, which Render deploys as `aqone-backend`.
Each item lists what changed, why, and the commit.

## 1. Fullscreen expand button beside the retry icon

A new expand button sits directly beside the retry icon in the `Live near-shore danger scan` bar.
Tapping it puts the whole map card into fullscreen (with a CSS fallback when the Fullscreen API is blocked), and tapping again or pressing Esc exits.
The map calls `invalidateSize()` on every toggle so Leaflet tiles never render half-blank.
Files: `web/html/dashboard.html`, `web/css/dashboard.css`, `web/js/dashboard/dashboard-tools.js`.
Commits: `a451f03` (built on `Jade-branch`), ported to `Jade-backup` as `b6937a8`.

## 2. Resolved Incidents capped at 5 with a View-all toggle

The Resolved Incidents panel now shows only the 5 most recent entries instead of the full history.
A `View` button in the panel header expands to `View all (N)` and collapses back to `Show less`.
The button only appears when there are more than 5 resolved incidents, and the expanded state survives the 10-second auto-refresh.
Reopen behavior is unchanged.
Files: `web/html/dashboard.html`, `web/css/dashboard.css`, `web/js/dashboard/dashboard-buoy-health.js`.
Commit: `3fbb37d`.

## 3. Metric banner height fixed (104 → 118 → 96)

The three top metric cards were first enlarged to 118px so their content stopped overflowing, which exposed dead space inside the cards.
The banner was then shrunk to 96px so the cards fit snugly with no dead space, and the map below automatically grew ~22px taller because the page offset is computed from the same variable.
Ellipsis and shrink guards were added so long pills and the sparkline graph can no longer push the third card off-screen on narrow widths.
File: `web/css/dashboard.css`.
Commits: `113b3a0`, `f3cc127`.

## 4. Gap between metric cards and map reduced to 1px

The empty strip between the metric row and the `Live near-shore danger scan` bar went from ~20px to 1px.
Banner bottom padding is now 0 and both content columns use 1px top padding, kept symmetric left and right.
File: `web/css/dashboard.css`.
Commits: `3112e0a`, `2d0c873`, `a3d6fa8`.

## 5. APP USERS live metric card (4th card)

A fourth metric card, `APP USERS`, sits to the right of `LAST UPDATED`, and all four cards share equal width through a 4-column grid.
The big number is the live total of active operators plus active vessels, the pill shows `LIVE`/`OFFLINE`, and the caption breaks the count down.
It polls `GET /api/ops/presence` on load and every 30 seconds, and it never shows a fake number while offline.
New backend endpoint `GET /api/ops/presence` returns registered users, recently active operators, and recently active vessels with no database migration.
Files: `backend/app/api/ops_status.py`, `web/html/dashboard.html`, `web/css/dashboard.css`, `web/js/dashboard/dashboard-buoy-health.js`.
Commit: `7324290`.

## 6. Operator presence heartbeat

Dashboard sessions were invisible to the user counter because operator logins only stamped `last_login_at` once at login.
Migration `038` adds `users.last_seen_at`, and every presence poll re-stamps the caller's row, so any open dashboard counts as online.
Operators active in the last 2 minutes are included in the live total, and closing the tab drops out of the count within ~2 minutes.
Files: `backend/migrations/038_users_last_seen.sql`, `backend/app/api/ops_status.py`.
Commit: `1e2eba2`.

## 7. App Users roster page

Clicking the APP USERS card opens a new `users.html` page listing every fisherman vessel with name, registered (license) number, phone number, Active/Inactive status, sea status, and last GPS fix with time and source.
Filter pills narrow the list to All, Active, Inactive, or At sea, and blank or unverified data is labeled honestly (`Unregistered`, `NO SEA RECORD`) instead of hidden.
The page follows the dashboard dark-mode setting and guards the route back to login when the session is missing.
New backend endpoint `GET /api/ops/roster` serves the list in one query with no migration.
Sea status means: `AT SEA` for an open trip, `WENT TO SEA` when any GPS fix exists (SOS, buoy contact, catch log, or fishing spot), otherwise `NO SEA RECORD`.
GPS shown is the last known fix, not live tracking, because no continuous position feed exists.
Files: `backend/app/api/ops_status.py`, `web/html/users.html` (new), `web/js/users.js` (new), `web/html/dashboard.html`, `web/css/dashboard.css`, `web/js/dashboard/dashboard-buoy-health.js`.
Commit: `19bed23`.

## 8. Active means any backend contact in the last 15 minutes

Sending an SOS never marked a vessel Active because SOS ingest needs no login and only paired-device calls stamped the old flag.
Active now covers any backend contact in 15 minutes: paired-device heartbeat, a recent SOS, a live buoy contact, or a catch upload, shared as one predicate by the roster and presence endpoints.
The wording changed from handsets to vessels across the API and UI to match.
Files: `backend/app/api/ops_status.py`, `web/js/users.js`, `web/js/dashboard/dashboard-buoy-health.js`.
Commit: `48991c1`.

## Verification status

Backend `ruff` is clean, the FastAPI app imports with all three ops routes registered, frontend syntax checks pass, and `dashboard-runtime.test.js` passes 43/43.
The dashboard and roster layouts were also rendered in headless Edge and inspected visually.
