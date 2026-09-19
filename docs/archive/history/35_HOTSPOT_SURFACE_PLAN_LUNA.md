# 35 — Fish Hotspot Surface: Mount + Dashboard Layer (for Luna)

**Status:** COMPLETE
**Owner:** GPT Luna / Jade
**Created:** 2026-08-25
**Updated:** 2026-09-19
**Related:** [`docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](../56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md)

> **Historical document:** Plan executed on 2026-08-25 for mounting fish hotspot surfaces and dashboard layer.
> Live architecture and endpoints are documented in [`docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](../56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md).

**Audience: GPT Luna, executing on a dedicated branch cut from `dj`.**
**Scope: mount an existing backend router, reconcile two constants, and build
the dispatcher dashboard's hotspot layer. No mobile changes. No firmware. No
new model.**

Written 2026-08-25. Every file path, line number, constant and endpoint fact
below was verified by reading this repository on that date, on branch `dj` at
`1bd0e91`.

---

## 0. DIRECTIVE — READ BEFORE ANYTHING ELSE

**Follow this plan exactly. Do not deviate, improvise, redesign, or "improve"
it.** The investigation is already done. Do not re-derive it.

- **Do not touch any file not named in this plan.** Nothing under `mobile/`,
  `firmware/`, `gateway/`, `arduino/`. No backend file except the two named in
  §4. No CSS file except the one named in §6.4.
- **Do not run `git` write commands.** Not `commit`, not `checkout -b`, not
  `merge`, not `reset`. Lenard runs those. You prepare the changes and tell him
  the exact commit message from §9.
- **Do not port anything from the old `AqOne` repo.** That repo's version of
  this feature is the weaker one — exact vessel-attributed coordinates and six
  hardcoded fake zones. It is not the source of truth here and must not be
  copied. See §2 for why.
- **Do not modify `aggregate_hotspots()`.** Its scoring has known defects,
  listed in §8. They are deliberately deferred to a separate pass. Changing that
  function in this branch invalidates `backend/tests/test_hotspots.py` and mixes
  two reviews into one.
- **Do not invent hotspot data.** No hardcoded zone array, no seeded demo
  cells, no placeholder percentages on the dashboard. If the endpoint returns
  zero cells, the map draws nothing and the status line says so. A dispatcher
  vectoring a boat toward a fabricated cell is the specific harm this guards
  against.
- **Do not put the hotspot router behind `_protected`.** It is public by
  design, for the same reason as `public_router`. See §4.2.
- **STOP conditions are real.** Where this plan says STOP, stop and report to
  Lenard. Do not proceed on your own judgement.

**If a line number is off or the code does not match what is described here:
STOP and report it.** Do not silently adapt.

---

## 1. BRANCH SITUATION

Work from `dj`, which is the current tip (`1bd0e91`, "Merge branch 'master'
into dj", 2026-08-23). **Do not use `demo`** — per `docs/34_...`, `demo` is 69
commits behind and still carries the pre-modularization dashboard monolith.
Every dashboard path in §6 assumes the modular `web/js/dashboard/*.js` layout
that only exists on `dj`.

Ask Lenard to run, in his own terminal (not through you):

```
git checkout dj
git pull
git checkout -b feat/hotspot-surface
```

**STOP 1 — Do not start until Lenard confirms `feat/hotspot-surface` exists and
`git log -1` on it shows `1bd0e91` or later.**

> **Git through the desktop bridge is unreliable on this repo** — it reports
> phantom staged changes because it cannot refresh `.git/index`. Verify any
> suspicious git state with `git show HEAD:<path>` against the file content
> before raising an alarm, and never run git writes through it.

---

## 2. WHAT ALREADY EXISTS — READ THIS BEFORE ASSUMING ANYTHING IS MISSING

This feature is roughly 80% built. The request that produced this document was
"add fishing hotspots to the new repo," which is the wrong frame: almost all of
it is already here, on `dj`, and better than the version it would be ported
from.

| Piece | Location | State |
|---|---|---|
| Aggregation logic | `backend/app/api/hotspots.py` | **Written, tested, never mounted** |
| Consent column | `backend/migrations/015_catch_hotspot_consent.sql` | Applied |
| Consent write path | `backend/app/api/catch.py` lines 46, 93, 104, 116 | Working |
| Community pin ingest/read | `backend/app/api/spots.py`, migration `013` | Mounted, working |
| Aggregation tests | `backend/tests/test_hotspots.py` | Present, **one test currently failing** |
| Mobile wire model | `mobile/lib/models/hotspot_cell.dart` | Complete |
| Mobile fetch | `mobile/lib/services/venture_feeds.dart:136` | Complete |
| Mobile render + legend | `mobile/lib/ui/venture_page.dart:664, 699, 902` | Complete |
| **Dispatcher dashboard layer** | — | **Does not exist** |

### 2.1 The endpoint is dead

`backend/app/api/hotspots.py:13` declares
`APIRouter(prefix='/api/public/hotspots', tags=['public'])`. That router is
**never imported and never included** in `backend/app/main.py`. Verified:

```
grep -rn "api.hotspots\|hotspots_router\|public/hotspots" backend/app backend/tests --include=*.py
  app/api/hotspots.py:13     (the declaration)
  tests/test_hotspots.py:3   (imports the pure function)
  tests/test_hotspots.py:12  (asserts the route is registered)
```

So `GET /api/public/hotspots` returns **404** in every environment today.

### 2.2 There is a red test proving it

`backend/tests/test_hotspots.py:11`:

```python
def test_public_hotspot_route_is_registered() -> None:
    assert '/api/public/hotspots' in app.openapi()['paths']
```

This asserts exactly the thing §2.1 says is false. It should be failing right
now. `docs/demo` notes record a test baseline of "89 passing, 1 expected
failure" — **confirm in Phase 0 whether this is that failure.** If it is, the
baseline description is stale and should say so after this branch lands.

### 2.3 What the 404 does downstream

`mobile/lib/ui/venture_page.dart` lines 290–293, verbatim:

```
/// A 404 (the current state - the model is Phase 3) leaves _hotspots null
/// and the map draws nothing. There is no fallback by design: the honest
/// answer to "where are the fish" is silence until something has actually
/// been modelled.
```

So the handset's hotspot layer is silent today, by documented intent.
`mobile/lib/data/demo_hotspots.dart` exists but **is referenced from nowhere** —
its docstring claims it is "served only when the endpoint is absent," and that
wiring was never built. It is dead code. Leave it alone; it is out of scope.

**Mounting the router in §4 will switch the mobile layer on.** That is a
user-visible mobile behaviour change produced by a backend-only edit. It is
covered by STOP 2 below.

---

## 3. THE GAP THIS BRANCH CLOSES

Three things, in order:

1. Mount `hotspots_router` so `/api/public/hotspots` answers (§4).
2. Reconcile the reporter-threshold mismatch between backend and mobile (§5).
3. Build the dashboard hotspot layer against that endpoint (§6).

Everything else — the scoring defects, the missing time decay, the ML training
path — is explicitly deferred. See §8.

---

## 4. PHASE 1 — MOUNT THE ROUTER

**One file: `backend/app/main.py`. Two edits. Nothing else in this phase.**

### 4.1 Import

The import block is alphabetical by module (lines 11–27). `from app.api.drift
import router as drift_router` is at line 18, `from app.api.mesh import router
as mesh_router` at line 19. Insert between them:

```python
from app.api.hotspots import router as hotspots_router
```

### 4.2 Registration

`app/main.py` registers unauthenticated routers first (lines 49–86), then
declares `_protected = [Depends(require_user)]` at line 90 and registers
everything else behind it.

**The hotspot router goes in the unauthenticated block, above line 90.** It is
public for the same reason `public_router` is: the handset has no account by
design, and this is the surface fishermen read. Putting it under `_protected`
would 401 every handset and is the wrong direction to fail.

Register it immediately after `app.include_router(public_router)` (line 75),
with this comment:

```python
# The aggregated catch-activity surface. Public for the same reason
# public_router is - the handset has no account. Its privacy property is in
# the response shape, not in auth: app/api/hotspots.py emits binned cells
# with a minimum reporter count and never a vessel id or an exact point, so
# there is nothing here that authentication would be protecting.
app.include_router(hotspots_router)
```

### 4.3 Verify before going further

```
cd backend
python -m pytest tests/test_hotspots.py -v
ruff check .
```

Expected: all five tests in that file pass, including
`test_public_hotspot_route_is_registered`, and `ruff` is clean.

**STOP 2 — Report to Lenard before Phase 2.** Two things need his decision:

1. Mounting this endpoint turns on the mobile hotspot layer for any handset
   pointed at the deployed backend (§2.3). Confirm he wants that live now, or
   whether the mount should be gated behind an env flag for this branch.
2. Report whether `test_public_hotspot_route_is_registered` was the "1 expected
   failure" in the test baseline, and the exact pass/fail counts before and
   after your edit.

---

## 5. PHASE 2 — RECONCILE THE REPORTER THRESHOLD

There are two different reporter minimums in this repo and they disagree:

| Location | Value |
|---|---|
| `backend/app/api/hotspots.py:16` — `MIN_REPORTERS` | **3** |
| `mobile/lib/data/demo_hotspots.dart:30` — `minReporters:` | **5** |

The backend value is authoritative: it is the one that actually gates
publication, it is what the response's `min_reporters` field carries, and it is
what `mobile/lib/ui/venture_page.dart:868` renders in the legend ("min N
reporters"). The `5` in `demo_hotspots.dart` is a label on dead, never-rendered
data (§2.3).

**Do not edit either file.** Do not "fix" the 3 to a 5 or vice versa. Whether 3
independent reporters is a sufficient privacy threshold for publishing a
0.02°-binned cell is a judgement call about real fishermen's productive
grounds, and it is Lenard's call, not the implementer's.

**STOP 3 — Report the mismatch to Lenard and ask which value is correct.** Then:

- If he says **3 stands**: no code change. Note in your report that
  `demo_hotspots.dart` carries a contradicting `5` on dead code, as a cleanup
  item for a later pass.
- If he says **5** (or any other number): change `MIN_REPORTERS` in
  `backend/app/api/hotspots.py:16` only. `tests/test_hotspots.py` reads
  `MIN_REPORTERS` symbolically (line 3, 16), so the tests follow automatically —
  confirm by re-running them.

Whatever the value, the dashboard in §6 must render `min_reporters` from the
**response payload**, never a hardcoded number.

---

## 6. PHASE 3 — THE DASHBOARD HOTSPOT LAYER

The dashboard has no hotspot code at all. It was dropped during the
DangerzoneFeature merge — see the surviving scar comment at
`web/js/dashboard/dashboard-vessels-alerts.js` lines 251–255. **Do not try to
restore what was deleted there.** That was the old six-hardcoded-zone system.
You are building a new layer against the real endpoint.

### 6.0 What it renders — the contract

`GET /api/public/hotspots` returns:

```json
{
  "generated_at": "2026-08-25T...Z",
  "model_version": "catch-density-v1",
  "min_reporters": 3,
  "window_days": 30,
  "cells": [
    {"center_lat": 11.69, "center_lon": 122.43,
     "cell_size_degrees": 0.02, "score": 0.87, "observations": 14}
  ]
}
```

Rules for rendering, all non-negotiable:

- **Cells, never points.** Draw each cell as a square (`L.rectangle`) sized
  from `cell_size_degrees`, not a circle around `center_lat/lon`. A circle
  reads as "the fish are at the centre" and re-implies the precision the
  binning exists to destroy. Half-edge = `cell_size_degrees / 2` in degrees,
  applied to both lat and lon bounds.
- **`cell_size_degrees` is per-cell and comes from the payload.** Do not
  hardcode 0.02. The backend is free to coarsen the grid where reporting is
  sparse; `hotspot_cell.dart`'s doc comment states this explicitly and the
  dashboard must honour the same contract.
- **`score` is not a probability.** Never render it as "% chance of catching."
  Label it "relative recent activity." It is 0–1, relative to the busiest cell
  in this response.
- **`observations` is always displayed**, in the tooltip and the popup. A cell
  resting on 4 reports and one resting on 200 must not look alike.
- **Never render vessel identity.** The payload contains none; do not join it
  in from `/api/spots`.
- **No hotspot cell may be drawn from any source but this endpoint.**

### 6.1 `web/js/dashboard/dashboard-core.js` — declare the layer

The layer-group block is lines 262–271. Add after `driftLayer` (line 270):

```javascript
  const hotspotLayer   = L.layerGroup();
```

Then export it in the `ns.` block. `ns.driftLayer = driftLayer;` is at line 339
and `ns.dangerZoneLayer = dangerZoneLayer;` at line 340. Add after line 340:

```javascript
  ns.hotspotLayer = hotspotLayer;
```

### 6.2 New file: `web/js/dashboard/dashboard-hotspots.js`

Create it. Follow the module pattern used by every other file in that
directory — see `dashboard-markers.js` lines 1–21:

```javascript
(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var map = ns.map;
  var hotspotLayer = ns.hotspotLayer;
  var API_BASE = ns.API_BASE;
  var escapeHtml = ns.escapeHtml;
  // ... module body ...
}(window.AqOneDashboard = window.AqOneDashboard || {}));
```

Confirm the exact IIFE header and namespace name by reading the top and bottom
of `dashboard-markers.js` before writing yours. **Match it exactly.**

The module must contain:

**A `HOTSPOT_POLL_MS` constant, set to `300000` (5 minutes).** The underlying
data is a 30-day catch-log window; it does not move in seconds. Compare
`LIVE_SOS_POLL_MS` in `dashboard-live-sos.js:231` — that is a life-safety feed
and this is not.

**`fetchHotspots()`** — plain `fetch(API_BASE + '/api/public/hotspots')`, **not
`authFetch`**. The endpoint is unauthenticated; sending a bearer token to it is
harmless but misleading about the contract. Wrap in try/catch. On any failure,
call `renderHotspots(null)` and `console.warn('[AqOne] Hotspot surface
unavailable:', error.message)` — mirror the phrasing at
`dashboard-markers.js:412`.

**`renderHotspots(payload)`** —

- `hotspotLayer.clearLayers()` first, always.
- `payload === null` → clear, set status text to "Hotspot surface unavailable",
  return. Draw nothing.
- `payload.cells.length === 0` → clear, set status text to
  `'No cells meet the ' + payload.min_reporters + '-reporter threshold in the
  last ' + payload.window_days + ' days'`, return. **This is a normal state,
  not an error.** Do not style it as one.
- Otherwise, for each cell, build an `L.rectangle` with bounds
  `[[lat - h, lon - h], [lat + h, lon + h]]` where
  `h = cell.cell_size_degrees / 2`.

**Colour by score**, using a single-hue ramp so it cannot be confused with the
danger-zone red/amber/green semantics already on this map:

| `score` | fill | fillOpacity |
|---|---|---|
| `< 0.25` | `#1e3a5f` | 0.15 |
| `0.25–0.50` | `#2563eb` | 0.22 |
| `0.50–0.75` | `#38bdf8` | 0.30 |
| `> 0.75` | `#7dd3fc` | 0.38 |

`weight: 1`, `color` same as fill, `className: 'hotspot-cell'`.

**Tooltip** (`direction: 'top'`, `sticky: true`):
`'Relative activity ' + Math.round(cell.score * 100) + '% · ' +
cell.observations + ' catch reports'`

**Popup** — follow the `popup-row` markup convention at
`dashboard-markers.js:330–345`. Rows: Relative activity, Catch reports, Cell
centre (3 decimals), Cell size (`(cell_size_degrees * 111).toFixed(1) + ' km'`),
then a divider, then the provenance footer:

```
payload.model_version + ' · ' + payload.window_days + '-day window · min ' +
payload.min_reporters + ' reporters · generated ' + <formatted generated_at>
```

and this badge, verbatim:

```html
<span class="popup-badge badge-warn">RELATIVE ACTIVITY · NOT A CATCH PREDICTION</span>
```

**Every string interpolated into popup or tooltip HTML must go through
`escapeHtml`** (exported at `dashboard-core.js:311`), including
`model_version` and `generated_at`. They come from the server. Same reasoning
as the toast escaping at `dashboard-core.js:290–292`.

At the end of the module: `hotspotLayer.addTo(map);`, one immediate
`fetchHotspots()`, and `setInterval(fetchHotspots, HOTSPOT_POLL_MS)`.

### 6.3 Wire the toggle and the script tag

**`web/js/dashboard/dashboard-tools.js`** — the toggle block is lines 488–506.
Add `var hotspotLayer = ns.hotspotLayer;` to the header vars (alongside
`var dangerZoneLayer = ns.dangerZoneLayer;` at line 19), then add after
`toggleLayer('toggle-pins', pinLayer);` (line 506):

```javascript
  toggleLayer('toggle-hotspots', hotspotLayer);
```

**`web/html/dashboard.html`** — the toggle rows are lines 284–331, each a
`<label class="toggle-row">`. Add one after the `toggle-drift` row (lines
324–327), matching the surrounding indentation exactly:

```html
              <label class="toggle-row">
                <input type="checkbox" id="toggle-hotspots" checked />
                <span class="toggle-label">Fish Activity Cells <small>Consented catch logs</small></span>
              </label>
```

The `<small>` follows the precedent set by `toggle-danger-zones` (line 301,
`<small>Real data</small>`).

**Script tag** — the block is lines 1013–1031. Add after the
`dashboard-markers.js` line (1020):

```html
  <script src="../js/dashboard/dashboard-hotspots.js"></script>
```

It must come after `dashboard-core.js` (it reads `ns.hotspotLayer`) and before
`dashboard-tools.js` (which wires the toggle). Between markers and tools
satisfies both.

### 6.4 CSS

**`web/css/dashboard.css` only.** Add a `.hotspot-cell` rule with a hover
treatment consistent with the existing `.danger-zone-circle` rules — find those
first and match their structure. Do not restyle anything that already exists.
Do not add a new stylesheet.

---

## 7. PHASE 4 — VERIFICATION

Run all of these and report the output.

**Backend:**

```
cd backend
python -m pytest -q
ruff check .
```

Report exact pass/fail counts, and how they differ from the pre-branch baseline
you recorded at STOP 2.

**Endpoint, against a running instance:**

```
curl -s localhost:8000/api/public/hotspots | head -c 400
```

Expect a 200 with the §6.0 shape. An empty `cells: []` on a dev database with
no consented catch logs is **correct**, not a failure.

**Dashboard, by hand:**

1. Serve `web/` and open `web/html/dashboard.html`.
2. Confirm "Fish Activity Cells" appears in the layer list and toggles the
   squares on and off.
3. With the endpoint returning cells: confirm squares (not circles), tooltip
   shows relative activity + report count, popup carries the RELATIVE ACTIVITY
   badge.
4. With the backend stopped: confirm the map draws no cells, logs the warning,
   and **does not** throw or break any other layer.
5. With the endpoint returning `cells: []`: confirm the empty-state text names
   the threshold and the window, and is not styled as an error.
6. Confirm the other layers (danger zones, buoys, coverage, drift, squall)
   render exactly as before this branch.

**Screenshot steps 3, 4 and 5 and attach them to your report.**

---

## 8. KNOWN DEFECTS — DELIBERATELY NOT FIXED HERE

These are real and Lenard knows about them. They are scheduled for a separate
pass. **Do not fix them in this branch.** Listed so you do not "discover" them
mid-task and go off-plan.

1. **The top cell is always ≈1.0 by construction.**
   `hotspots.py:52–56` normalizes both terms against the maximum across
   eligible cells, so the busiest cell scores 1.0 in every response regardless
   of whether it rests on 4 reports or 400. `score` is therefore only
   meaningful *within* one response and cannot be compared across days. §6.0's
   "relative recent activity" wording is chosen to be honest about exactly this.
2. **No time decay inside the window.** A catch 29 days ago counts the same as
   one this morning (`WINDOW_DAYS = 30`, flat).
3. **`MAX_CELLS = 40`** truncates silently — the response carries no indication
   that cells were dropped.
4. **The reporter threshold disagreement** in §5, if Lenard leaves it at 3.
5. **`mobile/lib/data/demo_hotspots.dart` is dead code** whose docstring
   describes wiring that does not exist.
6. **The old `AqOne` repo's `backend/train.py`** has a label leak —
   `zone_total_volume` is both an input feature and the sole basis of the
   `is_hotspot` target, so any accuracy it prints is a tautology. It is not
   being ported and must not be. Noted here only so nobody resurrects it.

---

## 9. COMMIT

Do not run this. Give it to Lenard.

```
feat(hotspots): mount public hotspot endpoint and add dashboard cell layer

/api/public/hotspots was written and tested but never registered in
main.py, so it 404'd everywhere and tests/test_hotspots.py's
route-registration assertion was red. Mount it in the unauthenticated
block - it is public for the same reason public_router is, and its
privacy property lives in the binned response shape, not in auth.

Adds the dispatcher dashboard's hotspot layer against that endpoint:
binned squares sized from the payload's cell_size_degrees, labelled
relative activity rather than catch probability, with observation
counts always visible. No hardcoded zones - the old six-zone array
removed in the DangerzoneFeature merge is not coming back.

Scoring defects (score normalized to the per-response maximum, no time
decay) are documented in docs/35 and deferred.
```

---

## 10. REPORT BACK

When done, give Lenard:

- Test counts before and after, and the STOP 2 answer about the baseline.
- The STOP 3 decision on `MIN_REPORTERS` and what you did with it.
- The three screenshots from §7.
- Any line number in this document that did not match the code.
