# 11 — Dashboard Audit (master branch)

**Status:** SUPERSEDED (archived 2026-09-25). It audits the single-file `web/js/dashboard.js`, which was later split into `web/js/dashboard/*.js` (`docs/archive/plans/46_DASHBOARD_JS_MODULARIZATION_IMPLEMENTATION_PLAN.md`). Kept as history only.

Audit of `web/` on `master`. Files: `html/dashboard.html` (846 lines),
`js/dashboard.js` (2,915), `css/dashboard.css` (4,287).

---

## Headline finding

**The dashboard fetches live AI data from the backend every 60 seconds and
throws 100% of it away.**

Every AI render function begins with a DOM lookup and early-returns when the
element is absent:

```js
function renderSquallWatch(payload, traceSeries) {
  var summary = document.getElementById('ai-squall-summary');
  if (!summary) return;          // ← always taken
```

All seven elements the AI code requires are **missing from
`dashboard.html`**:

| Element ID | Required by | Present |
|---|---|---|
| `ai-risk-list` | `renderRiskFeed()` | **No** |
| `ai-risk-count` | `renderRiskFeed()` | **No** |
| `ai-squall-summary` | `renderSquallWatch()` | **No** |
| `ai-drift-select` | drift incident picker | **No** |
| `ai-drift-meta` | drift status line | **No** |
| `ai-trace-chart` | pressure trace chart | **No** |
| `ai-trace-legend` | pressure trace legend | **No** |

**Nothing reaches the map either.** `renderSquallWatch()` returns *before*
`clearAiSquallLayers()`, so no squall polygon is drawn. `renderDriftContours()`
is only reachable via `loadDriftIncidentDetail()`, which is only called when
`ai-drift-select` has a value — and that element does not exist, so drift
contours are never rendered.

The one AI artifact that *is* in the HTML is a legend:

```html
<div class="ai-map-key" id="ai-map-key">
  <div class="ai-map-key-title">Drift map key</div>
  ... 95% search area / 75% / 50% / Ground truth track / Squall watch polygon
```

A colour key for layers that never appear. This is worse than nothing — it
advertises capability that isn't on screen, and a judge who looks for those
contours won't find them.

---

## What is actually driving the visible UI

Every panel renders from hardcoded arrays at the top of `dashboard.js`:

| Mock data | Line | Feeds |
|---|---|---|
| `shoreStations` | 49 | Map gateway markers |
| `initialBuoys` | 56 | Buoy markers, buoy health card |
| `meshLinks` | 64 | Mesh link polylines |
| `incidents` | 75 | Map incident markers |
| `squallData` | 89 | `renderSquallCard()` → `#squall-body` |
| `driftData` | 101 | `renderDriftCard()` → `#drift-body` |
| `incidentDrawerData` | 428 | Incident drawer, SAR badge count |
| `vessels` | 1022 | Vessels tab |
| `alertData` | 1136 | Alerts tab |
| `sarMetrics` | 1211 | SAR Metrics tab |

So there are **two parallel systems** in one file: a complete mock dashboard
that is visible, and a complete backend integration that is invisible. They
never touch.

---

## Backend reality check

Backend source **is** present on master and all nine endpoints match what the
JS calls — the integration was written correctly:

```
GET  /api/ai/anomaly/active          ← called, discarded
GET  /api/ai/anomaly/vessel/{id}
POST /api/ai/anomaly/evaluate
POST /api/ai/drift/predict
GET  /api/ai/drift/incidents         ← called, discarded
GET  /api/ai/drift/incident/{id}     ← called, discarded
GET  /api/ai/squall/current          ← called, discarded
GET  /api/ai/squall/buoy/{id}        ← called, discarded
POST /api/ai/squall/train
```

**One endpoint mismatch:** `dashboard.js` lines 2813 and 2860 call
`GET`/`POST /api/sea-condition`. That endpoint does not exist in the backend.
Both calls 404.

---

## Fish hotspot status

**Effectively clean.** `dashboard.js` and `dashboard.html` have zero
references. The only remnant is one dead CSS block:

```
css/dashboard.css:3465-3498   /* AI FISH HOTSPOT PREDICTION */
  .hotspot-circle, @keyframes hotspot-fade-in, .hotspot-tooltip,
  .hotspot-tip, .hotspot-tip-pct, .hotspot-tip-label
```

Delete lines 3465–3498. Nothing references them.

---

## BFAR references — keep most of them

Five references, and they are **not** all regulatory. Do not blanket-delete.

| Location | Reference | Verdict |
|---|---|---|
| `dashboard.html:740` | `<option value="BFAR Notice">` | **Remove** — regulatory framing |
| `dashboard.html:489` | "Shore gateway / BFAR station" legend | **Keep** — mesh architecture |
| `dashboard.js:48-51` | `BFAR New Washington` shore gateway | **Keep** — mesh exit point |
| `dashboard.js:1214` | "distributed via BFAR FishR registration" | **Keep** — distribution channel, in the PRD |

BFAR hosting shore gateways and FishR as a distribution channel are both
product strengths. Removing them to fix a naming concern would delete real
capability.

---

## What is good

Worth stating, because the remaining work is smaller than it looks:

- The AI integration code is **correct and complete** — `Promise.allSettled`,
  per-endpoint failure isolation, empty states on failure, a 60-second refresh
  timer, and a drift incident selector with change handling. It only lacks a
  DOM to write into.
- Error handling already meets the "degrade gracefully" requirement.
- The CSS for the AI panels already exists (the PRD V2 block: `.squall-hero`,
  `.drift-areas`, `.sar-row`, `.incident-feed-row`, `.aq-conf-*`).
- Hotspot is gone from the logic.

---

## Fix list, in priority order

| # | Task | Effort | Why |
|---|---|---|---|
| 1 | Add the seven `ai-*` elements to `dashboard.html` | ~30 min | **Unblocks every AI feature.** Nothing else matters until this is done. |
| 2 | Replace `renderSquallCard()` / `renderDriftCard()` mock output with the real render functions, or point both at the new elements | ~45 min | Removes the contradiction of mock and live data on one screen |
| 3 | Implement `GET/POST /api/sea-condition` in the backend | ~20 min | Two calls currently 404 |
| 4 | Replace `sarMetrics` mock with real eval figures | ~20 min | These are your pitch numbers; showing invented ones is a risk |
| 5 | Delete dead hotspot CSS (3465–3498) | 2 min | Tidiness |
| 6 | Remove the `BFAR Notice` advisory option | 1 min | Narrative focus |
| 7 | Serve `web/` from FastAPI (doc 10, Prompt 2) | ~30 min | One Railway origin, one demo URL |

**Item 1 is the whole ballgame.** Until those elements exist, the backend, the
models, the synthetic data and the eval scripts are all invisible to anyone
looking at the screen.

---

## Verification after the fix

Open the dashboard with the backend running and confirm:

1. Network tab shows 200s for `/api/ai/anomaly/active`, `/api/ai/drift/incidents`,
   `/api/ai/squall/current`.
2. The vessel risk list populates with real vessel IDs and scores.
3. The drift selector lists real incident IDs, and selecting one draws the
   50/75/95% contours **and** the ground-truth track on the map.
4. The squall polygon appears when a detection is active.
5. Stop the backend and reload — every panel shows an empty state, no
   uncaught exceptions in the console.
6. `grep -rn "hotspot" web/` returns nothing.
