# 26 — Demo Build Plan

**Status:** SUPERSEDED (archived 2026-09-25). The scenario engine it proposed was built through the demo phases of `docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md` and `docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md` (`backend/app/demo/`); the current pitch plan is `docs/43_DTI_PITCH_IMPLEMENTATION_PLAN.md`.

**Problem.** The system is reactive to conditions that do not occur on demand.
Without a real pressure collapse over the buoy array there is no squall
nowcast, no RETURN NOW, no danger-zone escalation; without a real distress
call there is no drift field. On stage the dashboard shows a calm sea and
nothing to point at.

**Solution.** A backend scenario engine on a separate deployment that writes
real rows into the real tables on a real clock, driven from a presenter
control panel. **The models are not faked — the weather is.** Inference runs
for real against injected observations. That distinction is the demo's
credibility and it should be said out loud during the pitch.

Decisions taken: backend scenario engine, presenter-controlled, separate
Railway service, ~1 week.

---

## 1. Why this needs three injection layers

The five things to demo do not share a data path. This is the single most
important fact in the plan, and the reason a UI-level fake would have failed.

| Feature | Where its data comes from today | Demo injection point |
|---|---|---|
| Squall nowcast → RETURN NOW | `/api/ai/squall/current` → `barometric_readings WHERE is_synthetic = TRUE` | Append a pressure series across buoys on a tick. Model runs unchanged. |
| Drift prediction / search contours | `/api/ai/drift/incidents`, `/incident/{id}` → `incidents` table | Insert an incident row; `predict_drift` runs unchanged. |
| Overdue / trip anomaly | `/api/ai/anomaly/active` → trips | Insert a trip that departs from that vessel's own profile. |
| SOS pipeline | `POST /api/sos` (unauthenticated by design) | Control panel POSTs directly. No new backend work. |
| **Danger zones** | **`web/js/dangerZonePredictor.js` calls `api.open-meteo.com` from the browser** | **Cannot be driven from the DB.** Needs a weather proxy — see §3. |

Four of five are already DB-driven, which is why this is a week of work and
not a rewrite. `/api/ai/squall/current` derives `as_of` from
`max(observed_at)` of the readings rather than wall-clock time, so appending
rows advances the demo's clock for free.

---

## 2. Backend: scenario engine

New files:

```
backend/app/demo/__init__.py
backend/app/demo/scenarios.py     scenario definitions as data + the runner
backend/app/api/demo.py           /api/demo/* control routes
backend/migrations/015_demo.sql   demo_tag column + demo_state table
```

**Gating.** In `app/main.py`, register the demo router only when
`DEMO_MODE` is truthy. On production the routes do not exist at all — a
missing route is a stronger guarantee than a disabled one. Guard the router
with a `X-Demo-Key: $DEMO_CONTROL_KEY` header check rather than the operator
JWT, so the control panel works from a second device without a login on
stage but a judge poking at the URL cannot fire beats mid-pitch.

**Routes.**

| Route | Does |
|---|---|
| `GET /api/demo/state` | Current scenario, beat index, elapsed, what is armed |
| `POST /api/demo/scenario/{name}/start` | Arm a scenario, write its baseline |
| `POST /api/demo/beat/{n}` | Fire one beat |
| `POST /api/demo/advance` | Fire the next beat |
| `POST /api/demo/autoplay` | Start/pause the timed runner |
| `POST /api/demo/reset` | Roll back every demo row |

**Reset must be surgical, not `TRUNCATE`.** The 14-day baseline dataset from
`app.simulation.generator` is what the SAR metrics tab and the current field
depend on; wiping it empties the dashboard. Add a nullable `demo_tag TEXT`
to `barometric_readings`, `incidents`, `trips`, `squall_events`,
`search_sectors`, `sos_events`, and reset as
`DELETE ... WHERE demo_tag = $run_id`. Rehearsal is the main consumer of
this route — it will run twenty times before the demo runs once, and a reset
that half-works is how a rehearsed demo dies on stage.

Every injected row keeps `is_synthetic = TRUE`. The dashboard already
renders a `DEMO` badge (`dashboard.js:38`) — leave that visible.

---

## 3. The danger-zone problem

`dangerZonePredictor.js` hits Open-Meteo directly from the browser
(`WEATHER_ENDPOINT`, `MARINE_ENDPOINT`, lines 4–5). No backend involvement,
so no amount of DB injection moves it. Two changes:

1. Make both endpoints read from a configurable base
   (`window.AQONE_WEATHER_BASE`, defaulting to the current Open-Meteo URLs —
   production behaviour unchanged).
2. Add `GET /api/demo/weather/{forecast|marine}` returning an
   **Open-Meteo–shaped** payload from the active scenario. Shape-compatible,
   so the in-browser model parses it with zero changes and genuinely
   re-scores. On the demo deployment, `demo-control.html` sets the base to
   the proxy.

This also removes a live dependency on api.open-meteo.com from the venue
network, which is worth having regardless.

Same trick applies to the dashboard's own weather panel
(`dashboard.js:3727`, `3731`).

---

## 4. Scenario: "Squall over the Sibuyan fleet"

One arc, six beats, ~6 minutes, exercising all five features as a single
story rather than five disconnected button presses. Every beat is
individually firable so a judge's interruption cannot desynchronize you.

| Beat | On screen | Exercises |
|---|---|---|
| **0 — Baseline** | Fleet at sea, buoys green, pressure nominal, zones calm | Sets the "before", makes the change legible |
| **1 — Pressure falls** | Outer buoys drop; squall probability climbs; watch marker | Squall model, buoy telemetry |
| **2 — Zones escalate** | North sectors amber → red with reasons in the popup | Danger-zone model via weather proxy |
| **3 — RETURN NOW** | Threshold crossed; banner; advisory published; handset alarm | Squall → advisory → handset path, ~45 min lead |
| **4 — One boat doesn't answer** | `BANCA-7` flagged overdue against its own profile | Trip anomaly |
| **5 — SOS + drift** | Capsize SOS lands; 50/75/95 contours render | SOS pipeline, drift ensemble |
| **6 — Acknowledge + re-task** | Dispatcher ETA to handset; sector searched, negative; posterior shifts, contours move | Responder loop, Bayesian re-tasking |

Beat 6 is the strongest thing in the build — a search area that visibly
*changes shape* because a sector came back empty is the moment judges
remember. Do not cut it for time.

**Risk to calibrate first.** Measured squall recall is 0.133 — the model
misses most squalls. A scripted pressure series that does not cross the
decision threshold produces a beat 3 where nothing happens. Before writing
the control panel, run the candidate series through `app.ai.squall` offline
and tune it until detection is deterministic. Fallback if it stays
marginal: `SQUALL_DEMO_THRESHOLD` env var lowering the threshold on the demo
service only — which is the direction the README already says the model
should move for a life-safety system anyway. Disclose it if asked.

Keep a second short scenario, **"Clear day"**, as the reset target and as the
contrast case for the false-alarm claim.

---

## 5. Control panel

`web/html/demo-control.html` + `web/js/demo-control.js`. Not linked from any
nav; reachable by URL on the demo deployment only.

- One row per beat: label, fire button, fired/pending state
- **Run arc** with pause / step / skip-to-beat
- **Reset** — large, unmissable, confirm-free
- Live state readout polled from `/api/demo/state`
- Connection indicator, so a dead control panel is obvious before you press
  a button and nothing happens

Runs on a phone or second laptop while the projector shows the dashboard.

---

## 6. Dashboard gaps to close first

You flagged drift UI, tracking, and squall forecasting as not properly
implemented. The wiring exists — `dashboard.js` already calls
`/api/ai/drift/incidents`, `/api/ai/drift/incident/{id}`,
`/api/ai/squall/current`, `/api/ai/anomaly/active`, and has
`driftLayer` / `squallLayer` / `aiSquallLayer` / `aiTrackPane` created. So
this is finishing, not building. Audit needed before estimating; the demo
scenarios are what will actually exercise these paths, so build the engine
first and let it drive the UI work rather than the reverse.

Specifically to verify against a running scenario:

- Drift contours render at all three probability levels and update after
  `POST /incident/{id}/searched`
- Vessel track layer draws `ground_truth_track` / last-known trail
- Squall trace and legend appear from `/api/ai/squall/current` and clear
  correctly when detections drop to zero
- Layer toggles (`toggle-drift`, `toggle-squall`, `toggle-danger-zones`)
  all work in both directions

---

## 7. Deployment

Second Railway service, same repo, own Postgres.

| Env | Demo service | Production |
|---|---|---|
| `DEMO_MODE` | `true` | unset |
| `DEMO_CONTROL_KEY` | set | unset |
| `ALLOW_TRAINING` | `0` | `0` |
| `DATABASE_URL` | separate DB | prod DB |

Provisioning: `python migrate.py` → `python -m app.simulation.generator
--days 14 --seed 42` → the three `*_eval.py` scripts, so the SAR metrics tab
is populated rather than showing its empty state.

Production is untouched and cannot serve a demo route.

---

## 8. Sequencing

| Day | Work |
|---|---|
| 1 | Migration `015_demo.sql`, `app/demo/` skeleton, gated router, `/state` + `/reset`. Reset working before anything writes rows. |
| 2 | Calibrate the pressure series offline until squall detection is deterministic. Beats 0–1. |
| 3 | Weather proxy + `dangerZonePredictor` endpoint indirection. Beats 2–3. |
| 4 | Beats 4–6 (anomaly, SOS, drift, re-tasking). |
| 5 | Control panel. Second Railway service provisioned and seeded. |
| 6 | Dashboard gaps (§6), driven by the live scenarios. |
| 7 | Rehearse ×3 end to end. Record the screencast during rehearsal — it is both a deliverable and the insurance policy if venue wifi fails. |

---

## 9. Honesty constraints

Non-negotiable, and consistent with what the README already commits to:

- Demo rows stay `is_synthetic = TRUE`; the `DEMO` badge stays visible
- The pitch says the weather is scripted and the inference is real
- Injected conditions are physically plausible — a pressure drop that could
  not occur invites exactly the question you do not want
- No demo route reachable on production
- If `SQUALL_DEMO_THRESHOLD` is used, it is disclosed as a threshold change,
  not presented as the model's shipped calibration

---

## 10. Open questions

1. Does the handset need to be in the loop on stage (a real phone alarming
   at beat 3), or is the dashboard the whole demo? Affects whether beat 3
   needs a paired device and a rehearsed handset.
2. Vessel positions during the arc — static markers, or a moving fleet? A
   moving fleet is more convincing and is a `vessel_positions` ticker on the
   same beat clock; it is also the most likely thing to cut for time.
3. Who drives the control panel while Lenard presents?
