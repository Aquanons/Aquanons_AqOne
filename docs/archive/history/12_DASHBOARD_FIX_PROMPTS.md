# 12 — Dashboard Fix Prompts

**Status:** COMPLETE
**Owner:** Jade / Dashboard Team
**Created:** 2026-08-04
**Updated:** 2026-09-19
**Related:** [`docs/11_DASHBOARD_AUDIT.md`](../11_DASHBOARD_AUDIT.md)

> **Historical document:** Prompts addressing findings from [`docs/11_DASHBOARD_AUDIT.md`](../11_DASHBOARD_AUDIT.md).
> All prompts were executed and verified in earlier sprints.

Prompts to hand to a coding agent, in order. Findings they address are in
`docs/11_DASHBOARD_AUDIT.md`.

**Run Prompt A first and verify it before starting B.** A is the only one that
changes whether the AI is visible at all.

---

## Prompt A — Connect the AI panels to the DOM (critical)

> **Context:** Repo `AIHackathon2026_Aquanons_AqOne`, branch `master`. The
> dashboard is `web/html/dashboard.html`, `web/js/dashboard.js`,
> `web/css/dashboard.css`.
>
> `dashboard.js` already contains a complete, correct integration with the
> FastAPI backend: it polls `/api/ai/anomaly/active`, `/api/ai/drift/incidents`,
> `/api/ai/drift/incident/{id}`, `/api/ai/squall/current` and
> `/api/ai/squall/buoy/{id}` every 60 seconds, with `Promise.allSettled`,
> per-endpoint failure isolation and empty states.
>
> **All of that data is currently discarded**, because every render function
> starts with a `getElementById` lookup that returns null and early-returns.
> These seven element IDs do not exist in `dashboard.html`:
>
> ```
> ai-risk-list        ai-risk-count      ai-squall-summary
> ai-drift-select     ai-drift-meta      ai-trace-chart      ai-trace-legend
> ```
>
> **Task: add those elements so the existing code has somewhere to write, and
> remove the mock renderers they replace.**
>
> **A1 — Squall card.** `#squall-body` currently holds a placeholder
> (`<div class="squall-loading">Reading buoy pressure field...</div>`) and is
> overwritten by `renderSquallCard()` using the hardcoded `squallData` object.
>
> Replace the contents of `#squall-body` with `ai-squall-summary`,
> `ai-trace-chart` and `ai-trace-legend` containers, so that
> `renderSquallWatch()` and `renderSquallChart()` can populate them. Read those
> two functions first to confirm the element types they expect — `ai-trace-chart`
> receives inline SVG built by `renderSquallChart()`, so it must be a container
> that accepts `innerHTML`.
>
> **A2 — Drift card.** `#drift-body` is overwritten by `renderDriftCard()` from
> the hardcoded `driftData` object.
>
> Replace its contents with a `<select id="ai-drift-select">` and a
> `<div id="ai-drift-meta">`. `renderDriftIncidentList()` populates the select
> with `<option>` elements and the existing change handler calls
> `loadDriftIncidentDetail()`, which draws the 50/75/95% contours and the
> ground-truth track on the Leaflet map. Style the select minimally to match the
> panel — `.ai-drift-select` is the only AI class with no existing CSS.
>
> **A3 — Vessel risk feed.** `renderRiskFeed()` writes `<details class="ai-risk-item">`
> rows into `#ai-risk-list` and a count into `#ai-risk-count`.
>
> Add `<div id="ai-risk-list">` inside the Vessels tab (`#tab-vessels`) and wire
> `#ai-risk-count` to the existing `#badge-vessels` badge, or add a count element
> beside it. Read `renderRiskFeed()` to confirm the markup it emits.
>
> **A4 — Delete the mocks that are now replaced.** Remove:
> - the `squallData` object (~line 89) and `renderSquallCard()` (~line 2440) plus its call site
> - the `driftData` object (~line 101) and `renderDriftCard()` (~line 2488) plus its call site
> - any now-unused helpers that only those two functions used
>
> Do **not** remove `initialBuoys`, `shoreStations`, `meshLinks`, `incidents`,
> `incidentDrawerData`, `vessels` or `alertData` in this prompt — other panels
> still depend on them and removing them here would break the map.
>
> **A5 — Remove the misleading legend condition.** `#ai-map-key` lists "95% /
> 75% / 50% search area, ground truth track, squall watch polygon". Once A2
> works these layers render, so the legend becomes correct — but it must hide
> itself when no contours are drawn. Show it only when `aiContoursLayer` or
> `aiSquallLayer` has layers.
>
> **Constraints:**
> - **Do not modify any `render*` function that reads from the backend**
>   (`renderRiskFeed`, `renderSquallWatch`, `renderSquallChart`,
>   `renderDriftContours`, `renderDriftIncidentList`, `loadDriftIncidentDetail`,
>   `loadSquallTrace`, `aiFetchJson`). They are correct. You are adding the DOM
>   they expect, not changing them. If one seems wrong, stop and report rather
>   than editing it.
> - Match the existing panel markup conventions (`panel-card`,
>   `panel-card-header`, `panel-card-body`).
> - These CSS classes already exist — use them, do not redefine:
>   `.ai-empty-state`, `.ai-risk-item`, `.ai-risk-main`, `.ai-risk-title`,
>   `.ai-squall-meta-row`, `.ai-map-key`, `.squall-hero`, `.drift-areas`,
>   `.drift-row`, `.sar-row`.
> - No new frontend framework, no build step. Plain HTML/JS, matching the file's
>   existing style (it uses `var` and ES5-style functions — match that).
>
> **Acceptance:**
> 1. With the backend running, the browser Network tab shows 200s for all five
>    AI endpoints.
> 2. The vessel risk list shows real vessel IDs, scores and status badges.
> 3. The drift selector lists real incident IDs; choosing one draws three
>    contour rings **and** the ground-truth track on the map.
> 4. The squall panel shows either real detections or "No active squall
>    detections at the moment."
> 5. Stop the backend, reload: every panel shows an empty state, zero uncaught
>    exceptions in the console.
> 6. `grep -n "squallData\|driftData\|renderSquallCard\|renderDriftCard" web/js/dashboard.js`
>    returns nothing.
>
> **Report:** `git diff --stat`, the new markup you added, and a screenshot or
> description of the drift contours rendering on the map. If you could not get
> contours to draw, say so explicitly — do not report success without seeing them.

---

## Prompt B — Real SAR metrics and the missing endpoint

> **Context:** Repo `AIHackathon2026_Aquanons_AqOne`, branch `master`, after
> Prompt A. Two data problems remain in the dashboard.
>
> **B1 — `/api/sea-condition` does not exist.** `web/js/dashboard.js` calls
> `GET /api/sea-condition` (~line 2813) and `POST /api/sea-condition` (~line 2860).
> Neither is implemented in `backend/`, so both 404.
>
> Implement them in a new router following the style of
> `backend/app/api/anomaly.py`. Add migration `004_dashboard.sql` creating a
> `sea_conditions` table (id, condition, note, set_by, created_at). GET returns
> the most recent row; POST inserts a new one. **Never update in place** — the
> history is the audit trail. **Do not modify existing migrations**; they are
> already applied on Railway.
>
> Read the two call sites first and match the JSON shape the frontend already
> expects. Do not change the frontend to fit a shape you invented.
>
> **B2 — The SAR Metrics tab shows invented numbers.** `sarMetrics` (~line 1211
> in `dashboard.js`) is a hardcoded array. These are the figures we will put in
> front of judges, so they must come from the real evaluation scripts.
>
> `backend/app/ai/drift_eval.py`, `squall_eval.py` and `trip_profile_eval.py`
> already compute containment rate, search-area reduction, detection latency,
> false alarm rate, precision, recall and mean lead time — but only print them.
>
> Change all three to **also** write their results to
> `backend/app/ai/models/eval_results.json`, merging rather than overwriting so
> running one script does not erase another's results. Include a
> `generated_at` timestamp and a `calibration: "synthetic"` field.
>
> Add `GET /api/ai/metrics` returning that file's contents, with a clear 404 and
> message if it has not been generated yet. Then replace the `sarMetrics` mock
> with a fetch of that endpoint, falling back to an empty state — **not** to
> fabricated numbers — when unavailable.
>
> Keep the existing "sample data for demonstration" footer text, but make it
> read from the `calibration` field so it states the models are calibrated on
> synthetic observations rather than implying the metrics themselves are fake.
>
> **Constraints:** Do not change any model logic or any eval computation. You
> are adding persistence and an endpoint, nothing else. No invented fallback
> numbers anywhere.
>
> **Acceptance:** `pytest` passes with tests for both new endpoint groups;
> `ruff check` clean; running the three eval scripts produces a merged
> `eval_results.json`; the SAR tab renders those real values; with the file
> absent the tab shows an empty state rather than numbers.
>
> **Report:** the contents of `eval_results.json` after running all three evals,
> and the JSON shape of `/api/sea-condition`.

---

## Prompt C — Cleanup and single-origin deployment

> **Context:** Repo `AIHackathon2026_Aquanons_AqOne`, branch `master`, after
> Prompts A and B. Final cleanup, then serve the dashboard and API from one
> Railway service.
>
> **C1 — Delete dead hotspot CSS.** `web/css/dashboard.css` lines 3465–3498
> contain an orphaned `/* AI FISH HOTSPOT PREDICTION */` block
> (`.hotspot-circle`, `@keyframes hotspot-fade-in`, `.hotspot-tooltip`,
> `.hotspot-tip`, `.hotspot-tip-pct`, `.hotspot-tip-label`). Nothing references
> them. Delete the block. Verify with `grep -rn "hotspot" web/` returning nothing.
>
> **C2 — Remove one regulatory reference.** In `web/html/dashboard.html` around
> line 740, remove `<option value="BFAR Notice">BFAR Notice</option>` from the
> advisory type dropdown.
>
> **Leave every other BFAR reference alone.** They are infrastructure, not
> regulation: the "Shore gateway / BFAR station" map legend, the
> `BFAR New Washington` shore gateway in `dashboard.js`, and the "distributed via
> BFAR FishR registration" adoption metric. These describe where the LoRa mesh
> reaches land and how the app is distributed. Removing them would delete real
> capability.
>
> **C3 — Serve `web/` from FastAPI.** The backend deploys to Railway from the
> root `Dockerfile`. The dashboard is not served at all. Serve both from one
> origin on one port.
>
> Mount `fastapi.staticfiles.StaticFiles` in `backend/app/main.py`. **Register
> all API routers first and mount static files last** — Starlette matches routes
> in registration order, so a mount at `/` registered early shadows every API
> route including `/health/ready`, which silently breaks the Railway healthcheck.
>
> Serve `web/index.html` at `/` with the rest of the tree beneath it, so
> `web/html/dashboard.html` is reachable at `/html/dashboard.html` and existing
> relative asset paths keep resolving. Do not rewrite paths in the HTML.
>
> Resolve the web directory from `__file__`, checking both the container layout
> and a local checkout. If neither exists, **log a warning naming the paths
> tried** — do not crash and do not fail silently. A missing directory that
> silently skips the mount produces 404s with no obvious cause.
>
> Update the root `Dockerfile` to copy `web/` into the image. While there, copy
> `requirements.txt` and run `pip install` **before** copying application code,
> so editing a Python file does not reinstall scikit-learn on every deploy.
>
> **Constraints:** No nginx, no second service, no separate frontend deploy. Do
> not add CORS middleware — same origin makes it unnecessary. Do not change
> `API_BASE` in `dashboard.js`; `''` is correct for same-origin.
>
> **Acceptance:**
> - `pytest` passes, including a **new test asserting `/health/ready` returns
>   JSON and not HTML** — this is the most likely way this change breaks
>   production.
> - A new test asserting `/` returns the dashboard HTML.
> - `ruff check` clean.
> - The Docker image builds; run locally with a Postgres URL it serves the
>   dashboard at `/` and the API at `/api/ai/...` on the same port.
> - Editing a `.py` file and rebuilding does not reinstall pip packages.
>
> **Report:** the final `Dockerfile`, the mount code, and the output of
> `curl -s localhost:8000/health/ready`.

---

## After all three

1. Push; let Railway rebuild.
2. Seed once: `railway run python -m app.simulation.generator --days 14 --seed 42`
3. Run the three eval scripts on Railway so `eval_results.json` exists.
4. Open the deployed dashboard. Click every panel. Then redeploy and reload
   mid-restart to confirm the empty states behave.
5. Record the eval numbers for the pitch. **Do not present a number you have
   not personally seen printed.**
