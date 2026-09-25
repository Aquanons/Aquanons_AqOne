# 09 — AI Implementation Plan

> **Note (2026-09-25): barometer dropped.** The buoy barometer is no longer part of the
> architecture; squall alerts now come from the PAGASA weather API (PRD §5.1).
> References below to barometers, pressure readings or the pressure-based squall model
> describe that retired design and the code it left behind (`backend/app/ai/squall.py`,
> `barometric_readings`, `/api/v1/pressure-events`), which stays until it is removed.

**Status:** SUPERSEDED
**Owner:** Lenard / Backend Team
**Created:** 2026-08-04
**Updated:** 2026-09-19
**Related:** [`docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](../56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md)

> **Historical document:** This document records early scaffold prompts for the backend AI layer.
> The AI models are now implemented in `backend/app/routers/ai.py` and documented in [`docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md`](../56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md).

Backend AI layer for AqOne, deployed to Railway. Written as a sequence of
prompts to hand to AI coding assistants, in strict order.

**This document supersedes the "no AI model" line in `AGENTS.md` and
`07_SCOPE_OUT.md`.** Update both when you start Prompt 1.

---

## Reality check — read before starting

`backend/` currently contains three `.gitkeep` files. Build-order step 1
("FastAPI on Railway, green healthz, migrations run") is **not done**.
Deliverables may be due 5:00 pm today.

Therefore this plan is ordered so that **stopping at any prompt still leaves a
working demo**. Do not jump ahead to the interesting models before the
skeleton deploys — an undeployed brilliant model scores zero.

| Prompt | Outcome if you stop here | Est. |
|---|---|---|
| 0 | Backend live on Railway, healthcheck green | 45 min |
| 1 | Hotspot stripped, app matches the PRD story | 30 min |
| 2 | Synthetic data exists — every model below is now testable | 45 min |
| 3 | **Drift prediction live** — the demo centrepiece | 90 min |
| 4 | Trip anomaly / overdue detection live | 60 min |
| 5 | Squall nowcasting live | 60 min |
| 6 | Dashboard shows drift cone on a map | 60 min |

**If you only have time for three: 0, 2, 3.** Drift prediction is the most
visually compelling, the most defensible as real AI, and the only one that
demos well as a static screenshot.

### Honest framing for the pitch

You have no real incident data and no time to train on real data. All three
models are **physics-informed and calibrated on synthetic data**, with a
documented path to learning from live observations. Say this openly. Judges
punish overclaiming far harder than they punish a stated limitation.

Never describe these as "trained on real fisher data." They are not.

---

## Prompt 0 — Deploy the backend skeleton to Railway

> **Context:** Repo `AIHackathon2026_Aquanons_AqOne`. `backend/` is empty
> except for `.gitkeep` files in `app/`, `migrations/`, and `tests/`. We need
> a FastAPI + PostgreSQL service deployed on Railway before anything else.
> The previous version of this project (not in this repo) used a root
> `Dockerfile` and `railway.json` with a `DOCKERFILE` builder — reuse that
> shape.
>
> **Task:** Scaffold and deploy a minimal FastAPI backend.
>
> Create:
> - `backend/requirements.txt` — fastapi, uvicorn[standard], asyncpg,
>   pydantic, numpy, pandas, python-dotenv, httpx, scikit-learn, joblib.
>   Dev-only tools (pytest, ruff) live in `backend/requirements-dev.txt` and
>   are not installed in the production image.
>   Do not add xgboost or torch.
> - `backend/app/main.py` — FastAPI app with `/healthz` (liveness, no DB) and
>   `/health/ready` (checks a real DB connection).
> - `backend/app/db.py` — asyncpg connection pool created on startup from
>   `DATABASE_URL`, closed on shutdown. Fail loudly if the variable is missing.
> - `backend/migrations/001_init.sql` — tables `vessels`, `buoys`,
>   `buoy_contacts`, `sos_events`. Keep columns minimal; later prompts add more.
> - `backend/migrate.py` — applies any `migrations/*.sql` not yet recorded in a
>   `schema_migrations` table, in filename order. Idempotent.
> - Root `Dockerfile` — python:3.11-slim, install requirements, copy `backend/`,
>   run `python migrate.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
> - Root `railway.json` — DOCKERFILE builder, healthcheckPath `/health/ready`,
>   restartPolicyType ON_FAILURE with 3 retries.
> - `backend/.env.example` documenting `DATABASE_URL`.
> - `backend/tests/test_health.py` — `/healthz` returns 200.
>
> **Constraints:** No authentication yet. No secrets in the repo. Do not
> invent endpoints beyond those listed.
>
> **Acceptance:** `pytest` passes, `ruff check` is clean, the Docker image
> builds locally, and `/health/ready` returns 200 against a real Postgres.
>
> **Report:** the files you created and the exact Railway environment
> variables I must set.

---

## Prompt 1 — Strip fish hotspot from the mobile app

> **Context:** Flutter app in `mobile/`. AqOne is now a life-safety product
> only. Fish hotspot prediction and catch logging are out of scope and must be
> removed so the codebase matches the product story.
>
> **Task:** Remove all catch-logging and fish-spot functionality.
>
> Delete:
> - `lib/data/catch_store.dart`
> - `lib/models/catch_record.dart`
> - `lib/models/fish_spot.dart`
> - `lib/services/catch_service.dart`
> - `lib/ui/widgets/ripple_fish_spot.dart`
>
> Then remove every reference to them. Known referencing files:
> `lib/core/config.dart`, `lib/data/app_database.dart`, `lib/main.dart`,
> `lib/services/backend_client.dart`, `lib/services/buoy_client.dart`,
> `lib/services/venture_feeds.dart`, `lib/ui/app_shell.dart`,
> `lib/ui/onboarding_page.dart`, `lib/ui/venture_page.dart`.
> Search for `catch`, `Catch`, `spot`, `Spot`, `fish`, `Fish` and verify —
> do not trust this list alone.
>
> In `lib/core/config.dart` remove `spotsPath`, `publicSpotsPath`,
> `catchLogsPath`, and `maxCatchNoteLength`.
>
> **Database — important.** `lib/data/app_database.dart` is at schema
> version 3. Do **not** renumber or rewrite history. Add a **version 4**
> migration that drops `catch_outbox`, bump `version` to 4, and leave the
> existing `onCreate` and v2/v3 upgrade paths untouched so installed builds
> upgrade cleanly. New installs should not create `catch_outbox` at all.
>
> Remove any now-dead navigation entry so the app has no orphaned tab or
> route. If removing a tab leaves the shell with an awkward layout, fix the
> layout — do not leave a disabled stub.
>
> **Constraints:** Do not touch SOS, identity, buoy, advisory, weather, or
> sea-condition code. Do not refactor anything unrelated.
>
> **Acceptance:** `flutter analyze` clean, `flutter test` passes,
> `flutter run -d edge` launches and the SOS flow still works end to end.
> `grep -ri "catch\|fishspot\|fish_spot" lib/` returns only unrelated matches
> such as `try/catch`.
>
> **Report:** `git diff --stat`, and list anything you removed that was not on
> my list.

---

## Prompt 2 — Synthetic data generator

> **Context:** AqOne backend, FastAPI + Postgres, deployed on Railway. We have
> zero real observations and cannot collect any before the demo. Every AI
> endpoint that follows needs plausible input data.
>
> **Task:** Build a synthetic data generator that populates the database with
> realistic buoy and vessel activity for New Washington, Aklan
> (approximately 11.69 N, 122.37 E).
>
> Create `backend/app/simulation/generator.py` producing:
>
> 1. **Buoy array** — 8 to 12 moored buoys at fixed, plausible coordinates
>    across municipal waters out to roughly 25 km offshore. Each has an id,
>    lat, lon, and a nominal WiFi contact radius.
> 2. **Barometric time series** — per buoy, one reading every 5 minutes for
>    14 days. Base diurnal pressure cycle plus noise. Inject 6 to 10 discrete
>    squall events: a localised pressure drop of 3 to 6 hPa developing over
>    30 to 60 minutes and propagating across the array at 20 to 40 km/h from a
>    random bearing. Label these events in a separate `squall_events` table so
>    the detector in Prompt 5 can be scored.
> 3. **Current field** — a slowly varying 2D current vector field over the
>    area, plus per-buoy "observed" current derived from it with noise. This
>    stands in for mooring-tilt measurements.
> 4. **Vessel trips** — 30 to 50 synthetic vessels, each with a habitual
>    pattern: departure time, typical heading, typical buoy contact sequence,
>    typical return time, with realistic day-to-day variance. Generate 14 days
>    of trips as rows in `buoy_contacts`.
> 5. **Incidents** — 5 to 8 trips that terminate abnormally: contacts stop
>    mid-trip and the vessel never returns. Record ground truth in an
>    `incidents` table (vessel, last contact, true position over time under
>    the generated current field) so Prompts 3 and 4 can be scored.
>
> Add migration `002_simulation.sql` for `barometric_readings`,
> `squall_events`, `current_observations`, `incidents`. Extend `buoy_contacts`
> if needed.
>
> Expose it as `python -m app.simulation.generator --days 14 --seed 42`,
> idempotent (truncate-and-regenerate), and safe to run on Railway.
>
> **Constraints:** Deterministic given a seed. Values must be physically
> plausible — pressure in hPa around 1005–1015, currents 0–1.5 m/s. Clearly
> mark every generated row as synthetic with an `is_synthetic` boolean so no
> one can ever mistake it for real observations.
>
> **Acceptance:** Running the generator twice yields identical data. A test
> asserts row counts and that pressure and current values fall in plausible
> ranges. `ruff check` clean.
>
> **Report:** row counts per table and one example squall event with the
> buoys that observed it.

---

## Prompt 3 — Drift prediction (the centrepiece)

> **Context:** AqOne backend with synthetic data from Prompt 2. This is the
> flagship AI feature: given a vessel's last known position and time, predict
> where it has drifted, as a probability field, so search effort can be
> focused.
>
> **Task:** Implement Monte Carlo leeway drift prediction.
>
> Create `backend/app/ai/drift.py` implementing a **Lagrangian particle
> model**, the same approach used by NOAA's SAROPS and the open-source
> OpenDrift Leeway model. Do not attempt to install OpenDrift — implement the
> core method directly with numpy.
>
> Method:
> 1. Seed N particles (default 2000) at the last known position, with initial
>    spread reflecting position uncertainty.
> 2. Step forward in time (default 10-minute steps). Each particle advects by
>    `current_vector + leeway_coefficient * wind_vector`, plus a random
>    turbulent diffusion term.
> 3. **Leeway must depend on object class.** Implement at least three classes
>    with distinct downwind and crosswind coefficients: `person_in_water`,
>    `swamped_banca`, `intact_hull_adrift`. A person in water has very low
>    windage; a floating hull has high windage. Cite your coefficient choices
>    in comments as approximations of published leeway values — do not
>    fabricate precise figures.
> 4. Crosswind leeway must be able to go either way (left or right divergence),
>    assigned per particle at seeding — this is what makes the real cone
>    bimodal rather than a simple ellipse.
> 5. Output a probability density: bin particles onto a grid, normalise, and
>    return both the grid and contour polygons enclosing 50%, 75%, and 95% of
>    probability mass.
>
> Current and wind inputs: use the synthetic current field from Prompt 2, and
> fetch wind from the Open-Meteo marine/forecast API (already used by the
> mobile app — see `AqOneConfig.openMeteoBase`). Cache API responses. If the
> API is unreachable, fall back to the synthetic field and mark the response
> `degraded: true`.
>
> Endpoints in `backend/app/api/drift.py`:
> - `POST /api/ai/drift/predict` — body: last known lat, lon, ISO timestamp,
>   object class, forecast horizon hours. Returns the probability grid,
>   contour polygons, and the centroid track.
> - `GET /api/ai/drift/incident/{incident_id}` — runs the prediction for a
>   synthetic incident and **also returns the ground-truth track** so the
>   demo can show predicted versus actual.
>
> **Scoring — required.** Add `backend/app/ai/drift_eval.py` that runs the
> model against every synthetic incident and reports: containment rate (was
> the true position inside the 95% contour?) and search-area reduction versus
> a naive "circle expanding at max drift speed" baseline. **Print these
> numbers.** They are the strongest thing you can put on a slide.
>
> **Constraints:** numpy only for the model — no torch, no sklearn. A
> 2000-particle, 24-hour prediction must complete in under 3 seconds on
> Railway's smallest instance. Document every physical assumption in a
> docstring.
>
> **Acceptance:** pytest covers a known-current sanity case (uniform 1 m/s
> eastward current with no wind moves the centroid the expected distance);
> the eval script runs and prints containment and area-reduction figures;
> `ruff check` clean; endpoints return valid GeoJSON-compatible polygons.
>
> **Report:** the containment rate, the search-area reduction factor, and the
> runtime for a 24-hour prediction.

---

## Prompt 4 — Trip anomaly and overdue detection

> **Context:** AqOne backend with synthetic vessel trips and labelled
> incidents from Prompt 2. Today a missing boat is noticed when family reports
> it. We want the system to notice first.
>
> **Task:** Learn per-vessel trip patterns and flag anomalies.
>
> Create `backend/app/ai/trip_profile.py`:
> 1. **Profile builder** — for each vessel, from historical `buoy_contacts`,
>    learn: typical departure hour, typical buoy contact sequence, typical
>    inter-contact interval distribution, typical trip duration, typical
>    maximum distance offshore. Store as a JSON profile in a `vessel_profiles`
>    table, rebuildable on demand.
> 2. **Expected next contact** — given a vessel's contacts so far today,
>    predict which buoy it should hit next and by when, as a time window
>    rather than a point estimate.
> 3. **Anomaly scoring** — score an in-progress trip 0 to 1 on: overdue
>    against the expected-contact window, deviation from the habitual buoy
>    sequence, unusual distance offshore, and adverse weather at last known
>    position. Combine into one confidence score with the contributing factors
>    itemised in the response — a dispatcher must see *why*.
>
> **Escalation ladder** (mirror `06_DELIVERY_STATES.md` in spirit):
> `normal` → `watch` → `overdue` → `alert`. Thresholds must live in one
> config block, not scattered as magic numbers.
>
> Endpoints in `backend/app/api/anomaly.py`:
> - `GET /api/ai/anomaly/active` — all vessels currently at sea with scores
>   and status, sorted by score descending. This is the dashboard's main feed.
> - `GET /api/ai/anomaly/vessel/{vessel_id}` — detail with factor breakdown
>   and the learned profile.
> - `POST /api/ai/anomaly/evaluate` — recompute all scores. Idempotent.
>
> **Scoring — required.** Add an eval that runs against the labelled
> synthetic incidents and reports **detection latency** (minutes from last
> contact to reaching `alert`) and **false alarm rate** on normal trips.
> Report both. A model that catches every incident by alerting constantly is
> worthless, and you should be able to prove yours does not.
>
> **Constraints:** No heavyweight ML libraries — this is statistical profiling
> over per-vessel history, and it must stay explainable because a dispatcher
> has to act on it. Handle the cold-start case (a vessel with fewer than 3
> historical trips) by falling back to fleet-wide averages and marking the
> profile `low_confidence`.
>
> **Acceptance:** pytest covers profile building, a clearly-overdue vessel
> scoring high, and a normal vessel scoring low; eval prints detection latency
> and false alarm rate; `ruff check` clean.
>
> **Report:** median detection latency, false alarm rate, and the factor
> breakdown for one detected incident.

---

## Prompt 5 — Squall nowcasting

> **Context:** AqOne backend with synthetic barometric time series and
> labelled squall events from Prompt 2. Buoys form a fixed offshore pressure
> observation array at a density PAGASA does not have.
>
> **Task:** Detect developing squalls from the buoy pressure array and issue
> targeted warnings.
>
> Create `backend/app/ai/squall.py`:
> 1. **Feature extraction** per buoy: pressure tendency over 30 and 60 minutes,
>    second derivative, and deviation from the array-wide mean (which removes
>    the synoptic background and isolates local events).
> 2. **Spatial coherence** — a real squall shows a coherent, propagating
>    anomaly across neighbouring buoys, not one noisy sensor. Estimate the
>    propagation vector by cross-correlating anomaly onset times against buoy
>    positions. **This is the core discriminator; a single-buoy threshold
>    detector is not acceptable.**
> 3. **Classifier** — gradient-boosted trees or logistic regression over those
>    features, trained on the labelled synthetic events, predicting squall
>    onset within a 30–90 minute horizon. Add scikit-learn to requirements
>    only at this point. Persist the model with joblib to
>    `backend/app/ai/models/squall.pkl` and commit it, so Railway does not
>    train at boot.
> 4. **Affected area** — project the propagation vector forward to produce the
>    polygon that should receive a RETURN NOW warning, with an estimated
>    arrival time per buoy.
>
> Endpoints in `backend/app/api/squall.py`:
> - `GET /api/ai/squall/current` — active detections with affected polygon,
>   confidence, and estimated arrival time.
> - `GET /api/ai/squall/buoy/{buoy_id}` — that buoy's pressure trace and
>   current anomaly features, for the dashboard chart.
> - `POST /api/ai/squall/train` — retrain from stored data. Guard behind an
>   env-var flag so it cannot be hit accidentally in the demo.
>
> **Scoring — required.** Report precision, recall, and **mean lead time**
> (minutes between alert and squall arrival) on a held-out split of the
> synthetic events. Lead time is the number that matters — a perfectly
> accurate warning issued one minute early saves nobody.
>
> **Constraints:** Training must be reproducible from a seed. Never train at
> request time. Be explicit in the API response that this model is calibrated
> on synthetic data (`"calibration": "synthetic"`).
>
> **Acceptance:** pytest covers feature extraction and the propagation-vector
> estimate; the model file exists and loads; eval prints precision, recall,
> and mean lead time; `ruff check` clean.
>
> **Report:** precision, recall, mean lead time, and the top features by
> importance.

---

## Prompt 6 — Dashboard wiring

> **Context:** AqOne backend exposes `/api/ai/drift/*`, `/api/ai/anomaly/*`,
> and `/api/ai/squall/*`. The MDRRMO dashboard lives in `web/`. Judges will
> see this screen — it carries the demo.
>
> **Task:** Add an AI operations view to the dashboard.
>
> Three panels:
> 1. **Active vessel risk** — the `/api/ai/anomaly/active` feed as a sorted
>    list, colour-coded by escalation status, with the factor breakdown
>    expandable per vessel.
> 2. **Drift search map** — for a selected incident, render the 50/75/95%
>    drift contours over a Leaflet map with OpenStreetMap tiles (attribution
>    required: `© OpenStreetMap contributors`). Overlay the ground-truth
>    track for synthetic incidents in a visually distinct style, clearly
>    labelled as ground truth. **This is the screenshot that wins or loses
>    the pitch — make it clear and uncluttered.**
> 3. **Squall watch** — affected-area polygon on the same map plus a pressure
>    trace chart for the buoys involved.
>
> Add a visible banner: "Demonstration data — models calibrated on synthetic
> observations." Non-negotiable. It is both honest and disarms the obvious
> judge question before it is asked.
>
> **Constraints:** Match the dashboard's existing styling and stack — do not
> introduce a new framework. Every panel must degrade gracefully to an empty
> state rather than erroring if its endpoint is unavailable.
>
> **Acceptance:** all three panels render against the live Railway backend;
> the map draws real contour polygons; no console errors; empty states work
> when the backend is stopped.
>
> **Report:** a screenshot of the drift map with contours and ground truth.

---

## Deployment notes

Railway variables required:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Provided by the Railway Postgres service |
| `PORT` | Set by Railway; the Dockerfile CMD already reads it |
| `ALLOW_TRAINING` | Guards `POST /api/ai/squall/train`. Leave unset in the demo. |

The container runs `python migrate.py` before uvicorn, so `DATABASE_URL` must
be present at runtime, not just build time.

Seed synthetic data once after the first deploy:

```
railway run python -m app.simulation.generator --days 14 --seed 42
```

Commit `backend/app/ai/models/squall.pkl` — Railway must not train at boot.

---

## What to say to judges

- **Do say:** "physics-informed models, calibrated on synthetic observations,
  with a documented path to learning from live buoy data."
- **Do say:** the containment rate, search-area reduction, detection latency,
  and lead-time figures. Concrete numbers beat adjectives.
- **Do say:** the buoy array is the moat — the training data cannot exist
  without the hardware network.
- **Do not say:** "trained on real fisher data." It is not true.
- **Do not hide** the synthetic calibration. State it first, before anyone
  asks. It reads as rigour rather than as a gap.
