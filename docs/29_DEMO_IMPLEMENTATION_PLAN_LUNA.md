# 29 — Demo Implementation Plan (for Luna)

> **Note (2026-09-25): barometer dropped.** The buoy barometer is no longer part of the
> architecture; squall alerts now come from the PAGASA weather API (PRD §5.1).
> References below to barometers, pressure readings or the pressure-based squall model
> describe that retired design and the code it left behind (`backend/app/ai/squall.py`,
> `barometric_readings`, `/api/v1/pressure-events`), which stays until it is removed.

**Audience: GPT 5.6 Luna, executing on branch `demo`.**

---

## 0. DIRECTIVE — READ BEFORE ANYTHING ELSE

**Follow this plan 100%. Do not deviate, improvise, redesign, or "improve" it.**

This plan was written after reading the actual repository — the migrations,
the model internals, the dashboard's fetch calls, the exact Open-Meteo request
shape the browser model expects. Every constant, table name, column name,
function signature and threshold in this document was verified against the
code on 2026-08-21. **Values you assume instead of reading will be wrong.**

Specifically:

- **Do not invent table or column names.** They are all listed in §3.
- **Do not invent a different demo architecture.** The one here is chosen
  because of a non-obvious constraint documented in §2.3.
- **Do not "simplify" by faking data at the UI layer.** That defeats the
  entire purpose — see §1.2.
- **Do not refactor existing files** beyond the exact edits named in §5.
- **Do not add features** not listed here. Not a login for the panel, not a
  websocket, not an ORM, not a settings UI.
- **Do not rename, move, or reformat existing code.**

**If something in this plan appears wrong, contradicts the code, or cannot be
implemented as written: STOP and report it to Lenard. Do not work around it
silently.** A wrong assumption discovered on day 2 is cheap. One discovered
during rehearsal on day 7 is not.

**Work only on branch `demo`.** Never commit to `master`.

---

## 1. Context — what you are building and why

### 1.1 What AqOne is

AqOne is an offline maritime safety network for municipal fishermen in New
Washington, Aklan, Philippines, who work in cellular dead zones. A phone hands
an SOS to an anchored LoRa buoy over local WiFi; the buoy relays to a shore
gateway; the gateway forwards to a FastAPI backend; the backend pushes it to an
MDRRMO (disaster-management office) dashboard.

On top of that sits an AI safety layer of four models covering the emergency
timeline:

| Phase | Model | Method | Lives in |
|---|---|---|---|
| Before | Marine hazard / danger zone | Gradient boosting, 90 exported trees | **Browser** — `web/js/dangerZoneModel.js` + `dangerZonePredictor.js` |
| During | Squall nowcasting | Logistic regression on pressure-propagation features | `backend/app/ai/squall.py` |
| Overdue | Trip anomaly | Unsupervised per-vessel statistical profiling, NumPy only | `backend/app/ai/trip_profile.py` |
| After | Drift prediction | Monte Carlo Lagrangian particle ensemble | `backend/app/ai/drift.py` + `search.py` |

Stack: FastAPI + PostgreSQL (asyncpg) on Railway, vanilla JS + Leaflet
dashboard served as static files by the same FastAPI app, Flutter handset app.

### 1.2 The problem you are solving

The system is **reactive to conditions that do not occur on demand.** Without a
real pressure collapse over the buoy array there is no squall nowcast and no
RETURN NOW warning. Without a real distress call there is no drift field.
Without bad weather the danger zones stay green. On stage, in front of judges,
the dashboard shows a calm sea and there is nothing to demonstrate.

You are building a **scenario engine**: a gated, presenter-controlled system
that writes **real rows into the real tables** so that the **real models run
real inference** on scripted observations.

**This distinction is the entire point.** The weather is scripted. The
inference is not. The team says this out loud during the pitch, so it must be
true. Any shortcut that fakes model *output* rather than model *input*
destroys the demo's credibility and is an automatic rejection of your work.

### 1.3 The demo arc

Six beats, roughly six minutes, fired manually by an operator from a control
panel.

| Beat | What the audience sees | What it exercises |
|---|---|---|
| 0 Baseline | Fleet at sea, buoys green, pressure nominal, zones calm | Establishes "before" |
| 1 Pressure falls | Outer buoys drop; squall probability climbs | Squall model |
| 2 Zones escalate | North sectors amber → red with reasons | Danger-zone model (browser) |
| 3 RETURN NOW | Threshold crossed; banner; advisory published; **handset alarms** | Squall → advisory → handset |
| 4 Boat overdue | A vessel flagged against its own profile | Trip anomaly |
| 5 SOS + drift | Capsize SOS lands; 50/75/95 contours render | SOS pipeline + drift |
| 6 Ack + re-task | Dispatcher ETA to handset; a searched sector returns negative; **contours visibly move** | Responder loop + Bayesian re-tasking |

Beat 6 is the most important moment in the demo. Do not cut corners on it.

---

## 2. Architecture — and the constraint that forces it

### 2.1 Deployment

The demo runs as a **separate Railway service from the same repo, with its own
Postgres database**. Production is untouched.

| Env var | Demo service | Production |
|---|---|---|
| `DEMO_MODE` | `true` | unset |
| `DEMO_CONTROL_KEY` | a random secret | unset |
| `DATABASE_URL` | separate demo DB | prod DB |
| `ALLOW_TRAINING` | `0` | `0` |
| `JWT_SECRET`, `ADMIN_SETUP_KEY` | set | set |

The demo router is registered **only when `DEMO_MODE` is truthy**. On
production the routes do not exist at all. A missing route is a stronger
guarantee than a disabled one.

### 2.2 Injection points

Four of the five demo features are already database-driven. That is why this
is a week of work and not a rewrite.

| Feature | Reads from | You inject by |
|---|---|---|
| Squall | `/api/ai/squall/current` → `barometric_readings WHERE is_synthetic = TRUE` | Writing pressure rows |
| Drift | `/api/ai/drift/incidents`, `/incident/{id}` → `incidents` | Writing an incident row |
| Anomaly | `/api/ai/anomaly/active` → `buoy_contacts WHERE is_synthetic = TRUE` | Writing contact rows |
| SOS | `POST /api/sos` — unauthenticated by design | Posting to it |
| **Danger zones** | **the browser, calling api.open-meteo.com directly** | **A weather proxy — see 2.3** |

### 2.3 THE NON-OBVIOUS CONSTRAINT — read this twice

`web/js/dangerZonePredictor.js` fetches Open-Meteo **directly from the
browser** (lines 4–5). It never touches the AqOne backend. **No amount of
database injection will move the danger zones.**

Therefore beat 2 requires a *shape-compatible Open-Meteo proxy* on the backend
plus a configurable endpoint base in the predictor. The exact request and
response contract is specified in §3.5. Get this wrong and beat 2 silently
shows green zones forever.

### 2.4 Demo time is compressed — critical design point

A squall takes ~45–90 minutes of pressure evolution to become detectable. The
demo has ~6 minutes. **You cannot write readings in real time.**

The squall model works like this (verified, see §3.3): it takes **all**
synthetic barometric readings, finds the single latest `observed_at` across all
of them, and evaluates a **90-minute lookback window at 5-minute steps** ending
at that instant.

So the design is:

> **On every beat, delete the demo's barometric rows and rewrite a complete
> fresh 90-minute window ending at `now()`, whose pressure field is evaluated
> at that beat's point in the squall's life.**

Beat 1 writes a window showing the squall 60 minutes out. Beat 3 writes a
window showing it 15 minutes out. Real elapsed time between beats is
irrelevant — the model always sees a coherent, complete, correctly-shaped
90-minute window. This also means beats are **idempotent and re-firable**,
which matters enormously during rehearsal.

**Do not append readings incrementally. Do not use real elapsed time. Rewrite
the window every beat.**

---

## 3. Verified repository facts — do not re-derive these

Everything in this section was read from the code. Trust it over your
assumptions.

### 3.1 Database schema (relevant tables only)

```sql
vessels (
  id TEXT PRIMARY KEY, boat_name TEXT NOT NULL, created_at TIMESTAMPTZ,
  home_buoy_id TEXT, preferred_heading_deg DOUBLE PRECISION,
  typical_departure_local TEXT, typical_return_local TEXT,
  cruising_speed_kph DOUBLE PRECISION,
  route_buoy_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)

buoys (
  id TEXT PRIMARY KEY, vessel_id TEXT, label TEXT NOT NULL, created_at TIMESTAMPTZ,
  lat DOUBLE PRECISION, lon DOUBLE PRECISION, contact_radius_m INTEGER,
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)
-- migration 006 adds lora_radius_m / is_gateway_linked; check it before use.

barometric_readings (
  id BIGSERIAL PRIMARY KEY,
  buoy_id TEXT NOT NULL REFERENCES buoys(id) ON DELETE CASCADE,
  observed_at TIMESTAMPTZ NOT NULL,
  pressure_hpa DOUBLE PRECISION NOT NULL,
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)

squall_events (
  id BIGSERIAL PRIMARY KEY, started_at, peak_at, ended_at TIMESTAMPTZ NOT NULL,
  center_lat, center_lon, front_origin_lat, front_origin_lon,
  bearing_deg, speed_kph, pressure_drop_hpa DOUBLE PRECISION NOT NULL,
  rise_minutes INTEGER NOT NULL, hold_minutes INTEGER NOT NULL,
  observed_buoy_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)

buoy_contacts (
  id BIGSERIAL PRIMARY KEY, buoy_id TEXT NOT NULL REFERENCES buoys(id),
  contact_type TEXT NOT NULL, contact_value TEXT NOT NULL, created_at TIMESTAMPTZ,
  vessel_id TEXT, trip_id TEXT, sequence_no INTEGER, observed_at TIMESTAMPTZ,
  latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)

incidents (
  id BIGSERIAL PRIMARY KEY,
  vessel_id TEXT NOT NULL REFERENCES vessels(id) ON DELETE CASCADE,
  last_contact_at TIMESTAMPTZ NOT NULL,
  last_contact_buoy_id TEXT REFERENCES buoys(id),
  last_contact_lat DOUBLE PRECISION NOT NULL,
  last_contact_lon DOUBLE PRECISION NOT NULL,
  reported_missing_at TIMESTAMPTZ NOT NULL,
  abnormal_reason TEXT NOT NULL,
  true_track JSONB NOT NULL,
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
  prior_grid JSONB, posterior_grid JSONB
)

search_sectors (
  id BIGSERIAL PRIMARY KEY,
  incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  x_min_m, x_max_m, y_min_m, y_max_m DOUBLE PRECISION NOT NULL,
  detection_probability DOUBLE PRECISION NOT NULL,
  searched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)

sos_events (
  id BIGSERIAL PRIMARY KEY, vessel_id TEXT NOT NULL REFERENCES vessels(id),
  buoy_id TEXT, latitude, longitude DOUBLE PRECISION, note TEXT,
  created_at TIMESTAMPTZ, is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
)
-- migration 007 adds dedup + delivery-state columns. READ IT before inserting.

advisories (
  id BIGSERIAL PRIMARY KEY, source_key TEXT UNIQUE, title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'Weather Advisory', description TEXT NOT NULL,
  municipality TEXT NOT NULL DEFAULT 'All', priority TEXT NOT NULL DEFAULT 'Information',
  publish_date DATE NOT NULL DEFAULT CURRENT_DATE, expiration_date DATE,
  cover_image TEXT, status TEXT NOT NULL DEFAULT 'Published',
  source TEXT NOT NULL DEFAULT 'LGU', score INTEGER, created_by TEXT,
  created_at, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

vessel_profiles, vessel_anomaly_scores  -- DERIVED. See §3.4 warning.
```

**Every row you insert sets `is_synthetic = TRUE`.** The AI endpoints filter on
it; a row without it is invisible to the models and dishonest in the data.

### 3.2 Buoy identity

`app/simulation/generator.py::_build_buoys` creates between 8 and 12 buoys with
ids `B01`, `B02`, … `B{n:02d}`, label `Buoy {n:02d}`, `is_synthetic = TRUE`.
The count is drawn from the seeded RNG, so with `--seed 42` it is deterministic
but **you must query it, not hardcode it**:

```sql
SELECT id, lat, lon, contact_radius_m FROM buoys WHERE is_synthetic = TRUE ORDER BY id
```

The dashboard's hardcoded markers (`buoy-echo` etc. in `dashboard.js`) are a
**separate, unrelated** display list. Do not touch them and do not try to
reconcile them. That is Jade's file.

### 3.3 Squall model — exact behaviour

From `backend/app/ai/squall.py`:

```python
LOOKBACK_MINUTES = 90
STEP_MINUTES     = 5
DEFAULT_THRESHOLD = 0.55
CENTER_LAT, CENTER_LON = 11.6892, 122.3667
MODEL_PATH = app/ai/models/squall.pkl
CALIBRATION = 'synthetic'
```

- `build_history(rows)` → `{buoy_id: [PressureReading, …]}`
- `build_buoys(rows)` → `{buoy_id: BuoyMeta}` from `id/lat/lon/contact_radius_m`
- `current_detection(rows, buoys, bundle)` — takes `max(observed_at)` across
  **all** buoys, then `extract_pressure_features(history, buoys, latest)`,
  then `detect_squall(...)`. Returns `[]` or `[SquallDetection]`.
- `event_detection_summary(bundle, detections)` → the API response body.
- 21 features (`FEATURE_NAMES`), including **propagation features**:
  `propagation_speed_mps`, `propagation_bearing_sin/cos`, `propagation_r2`,
  `propagation_residual_minutes`, `onset_coverage`, `onset_span_minutes`.

**Consequence:** onset times must differ across buoys in a way consistent with
a front crossing the array. A uniform pressure drop applied to every buoy at
once will produce degenerate propagation features and will not detect. The
front geometry is not decoration — it is what the model keys on.

The API layer at `app/api/squall.py` reads readings, squall events and buoys
all filtered `WHERE is_synthetic = TRUE`, and requires the model bundle at
`app/ai/models/squall.pkl` (already committed).

### 3.4 Anomaly endpoint — DESTRUCTIVE, handle with care

`app/api/anomaly.py::_rebuild_and_score` executes:

```sql
TRUNCATE TABLE vessel_profiles, vessel_anomaly_scores
```

every time it runs, then rebuilds from `buoy_contacts WHERE is_synthetic = TRUE`.

Two consequences:
1. `vessel_profiles` and `vessel_anomaly_scores` are **derived**. Do not give
   them a `demo_tag` and do not clean them in reset — they regenerate.
2. Beat 4 works by inserting `buoy_contacts` rows for the demo vessel that
   break its established pattern, then letting the endpoint rebuild. **Do not
   write anomaly scores directly.** That would be faking model output.

The demo vessel needs prior trips in `buoy_contacts` for a profile to exist —
the 14-day generator dataset provides these for its own vessels. Beat 4 should
target **an existing generator vessel**, not a newly invented one, so it has
history to be anomalous against.

### 3.5 Weather proxy contract — exact, from `dangerZonePredictor.js`

**Request** built by `endpointUrl()`:

```
GET <base>/v1/forecast
    ?latitude=<csv of all sector lats>
    &longitude=<csv of all sector lngs>
    &current=wind_speed_10m,wind_gusts_10m,precipitation,weather_code
    &forecast_hours=1
    &timezone=UTC
    &cell_selection=sea

GET <marine base>/v1/marine
    ?latitude=<csv>&longitude=<csv>
    &current=wave_height,wave_period
    &forecast_hours=1&timezone=UTC
```

**Response** — a JSON **array**, one object per requested coordinate, **in the
same order as the CSV**:

```json
[ { "current": { "time": "2026-08-21T06:00", "wind_speed_10m": 12.4,
                 "wind_gusts_10m": 21.0, "precipitation": 0.0,
                 "weather_code": 1 } }, … ]
```

Marine likewise with `wave_height`, `wave_period`.

**Hard requirement:** `predictionsFromPayloads` throws
`'Live data did not return every configured offshore scan cell'` if
`weatherLocations.length !== sectors.length`. Your proxy **must** return
exactly one entry per requested coordinate, in order.

Sector count = `model.sectors` (from `dangerZoneModel.js`) **plus** the 5
hardcoded `NEW_WASHINGTON_COVERAGE` entries in the predictor, deduplicated by
`id`. Query it at runtime; do not hardcode a count.

**Scoring thresholds you must hit** (from `predictionsFromPayloads`):

| Outcome | Condition |
|---|---|
| **danger** (score ≥ 65, red) | `wave_height >= 2` **AND** (`wind_gusts_10m >= 40` **OR** `wind_speed_10m >= 30`) |
| **watch** (score 40–64, amber) | `wave_height >= 1.4` **OR** `gusts >= 30` **OR** `wind >= 24` **OR** `precipitation >= 5` **OR** `weather_code >= 95` |
| **low** (≤ 39, green) | none of the above, and model probability < 40 |

Beat 0 must produce values under all watch thresholds. Beat 2 must cross the
danger condition for the northern sectors only.

### 3.6 Drift and search

`app/api/drift.py`:

- `GET /api/ai/drift/incidents` — lists all incidents.
- `GET /api/ai/drift/incident/{id}?forecast_hours=24` — runs `predict_drift`,
  returns `{incident, prediction, ground_truth_track, posterior_grid,
  contours, search_sectors, observation_fraction}`.
- `POST /api/ai/drift/incident/{id}/searched` — body
  `{x_min_m, x_max_m, y_min_m, y_max_m, detection_probability}` — updates the
  posterior, inserts a `search_sectors` row, returns updated contours.
  **This is beat 6.** It already works. Do not reimplement it.

`abnormal_reason` mapping (`_incident_class`): `'capsize'` or
`'adverse_weather'` → `ObjectClass.swamped_banca`; anything else →
`ObjectClass.intact_hull_adrift`. Beat 5 uses `'capsize'`.

`true_track` is `JSONB NOT NULL` — you must supply it. Reuse
`generator.py::_simulate_drift_track` rather than inventing a track.

### 3.7 Advisories — beat 3

`POST /api/advisories/alert`, body `DangerAlertPayload`:

```python
{ "id": str, "name": str, "score": int, "level": str,
  "trigger": str, "reasons": [str], "source": str, "observedAt": str }
```

`priority` becomes `'Warning'` if `level == 'watch'`, else `'Emergency'`.
**Requires `Depends(require_user)`** — an operator JWT, not the demo key. The
demo engine must therefore either call it with a stored operator token or
insert the advisory row directly. **Confirm with Lenard which — do not
choose alone.** The handset polls the public advisory feed, so the row must
end up visible via `GET /api/public/advisories`.

### 3.8 Existing infrastructure to reuse, not rebuild

- `app/db.py` — `get_pool()` returns an `asyncpg.Pool`, raising
  `HTTPException(503)` when the DB is not ready. Use `async with pool.acquire()`.
- `app/auth.py` — `HTTPBearer`, `require_user`. Mirror its style for the
  demo-key dependency; do **not** modify this file.
- `app/simulation/generator.py`:
  - `_event_pressure_at(event, buoy, observed_at) -> float` — **reuse this**.
    Returns the pressure delta in hPa for one buoy at one instant given a
    squall event with `front_origin_lat/lon`, `bearing_deg`, `speed_kph`,
    `rise_minutes`, `hold_minutes`, `pressure_drop_hpa`, `started_at`.
    It handles the front geometry, arrival time and Gaussian cross-track
    falloff that the propagation features depend on.
  - The baseline field, from `_build_barometric_readings`:
    ```
    pressure = 1011.4
             + 1.15 * sin(2π·t_h/24    + phase)
             + 0.35 * sin(2π·t_h/12.42 + phase/2.5)
             + 0.28 * sin(2π·t_h/(24·7)+ phase/3.0)
             + N(0, 0.16)
    clipped to [998.5, 1016.5], rounded to 2dp
    ```
  - `_simulate_drift_track(...)` for `true_track`.
- `app/main.py` — routers are registered **before** the static mount at `/`.
  Registration order matters; mounting `/` first would shadow every API path.

### 3.9 Repo conventions (`AGENTS.md`)

- No code comments unless the decision is genuinely non-obvious; prefer
  self-documenting names. Match the surrounding file's style.
- No secrets in the repo. `.env.example` gets new keys with placeholder values.
- Verification before completion: `pytest` and `ruff check .` from `backend/`.
  Baseline is **89 passing, 1 expected failure**. You must not reduce that.

---

## 4. What you are building

```
backend/app/demo/__init__.py
backend/app/demo/scenarios.py      scenario definitions (data) + beat runner
backend/app/demo/weather.py        Open-Meteo-shaped payload builder
backend/app/api/demo.py            /api/demo/* routes, DEMO_MODE-gated
backend/migrations/015_demo.sql    demo_tag columns
backend/tests/test_demo.py         tests
web/html/demo-control.html         presenter panel
web/js/demo-control.js             panel logic
```

Edits to existing files — **these three only, minimally**:

| File | Edit |
|---|---|
| `backend/app/main.py` | Conditionally include the demo router when `DEMO_MODE` is truthy. Registered **before** the static mount. |
| `web/js/dangerZonePredictor.js` | Replace the two hardcoded endpoint constants with a configurable base, defaulting to the current Open-Meteo URLs. |
| `backend/.env.example` | Document `DEMO_MODE` and `DEMO_CONTROL_KEY`. |

**Touch nothing else.** In particular `web/js/dashboard.js`,
`web/html/dashboard.html` and `web/css/dashboard.css` belong to another team
member this sprint and are off limits.

### 4.1 API surface

All routes require header `X-Demo-Key: <DEMO_CONTROL_KEY>` except the weather
proxy, which the browser calls without custom headers.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/demo/state` | Active scenario, beat index, what has fired, run id |
| POST | `/api/demo/scenario/{name}/start` | Arm a scenario, write baseline, return run id |
| POST | `/api/demo/beat/{n}` | Fire beat n (idempotent) |
| POST | `/api/demo/advance` | Fire the next unfired beat |
| POST | `/api/demo/reset` | Delete every row tagged with the active run id |
| GET | `/api/demo/weather/forecast` | Open-Meteo-shaped forecast for the active beat |
| GET | `/api/demo/weather/marine` | Open-Meteo-shaped marine for the active beat |

Scenarios: `squall-fleet` (the six-beat arc) and `clear-day` (baseline only,
used as the reset target and as the false-alarm contrast case).

### 4.2 Reset must be surgical

**Never `TRUNCATE`.** The 14-day generator dataset is what the SAR metrics tab,
the current field, and the anomaly baseline profiles depend on. Wiping it
empties the dashboard and cannot be recovered without a reseed.

Migration `015_demo.sql` adds a nullable `demo_tag TEXT` to:
`barometric_readings`, `squall_events`, `incidents`, `search_sectors`,
`buoy_contacts`, `sos_events`, `vessels`, `advisories`.

Reset is `DELETE FROM <table> WHERE demo_tag = $1` for each, in
foreign-key-safe order (children before parents). Rehearsal will run this
twenty times before the demo runs once; a reset that half-works is how a
rehearsed demo dies on stage.

---

## 5. Tasks in order

Do these **in this sequence**. Each has an acceptance check. Do not start a
task until the previous one passes its check.

### Task 1 — Migration and reset

1. Write `backend/migrations/015_demo.sql` adding `demo_tag TEXT` (nullable, no
   default) to the eight tables in §4.2, with an index on `demo_tag` for each.
   Use `ALTER TABLE … ADD COLUMN IF NOT EXISTS`, matching the existing
   migrations' style.
2. Create `app/demo/__init__.py` and `app/demo/scenarios.py` with a `reset(pool,
   run_id)` that deletes tagged rows in FK-safe order.
3. Create `app/api/demo.py` with `/state` and `/reset` only, plus the
   `X-Demo-Key` dependency.
4. Gate the router in `main.py`.

**Check:** `python migrate.py` applies cleanly against a fresh DB. With
`DEMO_MODE` unset, `GET /api/demo/state` returns 404. With it set and a valid
key, it returns 200. `pytest` still 89 pass / 1 expected fail. `ruff check .`
clean.

**Reset is built before anything writes rows. This ordering is deliberate.**

### Task 2 — Calibrate the squall series (offline, before writing beats)

**This is the highest-risk task in the plan. Do it early.**

Measured squall recall is **0.133** — the model misses most squalls. A pressure
series that does not cross `DEFAULT_THRESHOLD = 0.55` produces a beat 3 where
nothing happens and a handset that never alarms.

1. Write a throwaway script (do **not** commit it) that: loads the real buoys
   from the demo DB, constructs a candidate `squall_events`-shaped dict, renders
   a 90-minute window with `_event_pressure_at` plus the baseline field from
   §3.8, and runs `build_history` → `build_buoys` →
   `extract_pressure_features` → `detect_squall` with the committed bundle.
2. Tune `pressure_drop_hpa`, `speed_kph`, `bearing_deg`, `front_origin_*`,
   `rise_minutes`, `hold_minutes` and the beat offsets until:
   - beat 0 and 1 → **no detection**
   - beat 2 → detection probability climbing but still below threshold
   - beat 3 → **probability ≥ 0.55, deterministically, every run**
3. Record the final parameters and the achieved probabilities.

**Check:** run the harness 10 times; beat 3 detects 10/10 and beat 0 detects
0/10.

**If you cannot achieve deterministic detection with physically plausible
parameters, STOP and report to Lenard.** There is an agreed fallback — a
`SQUALL_DEMO_THRESHOLD` env var lowering the threshold on the demo service only
— but **it is Lenard's decision to invoke, not yours.** Do not silently lower a
threshold on a life-safety model.

Physical plausibility is a hard constraint: a pressure drop that could not occur
in nature invites exactly the question the team does not want.

### Task 3 — Beats 0 and 1

Implement the scenario data structure and the window-rewrite runner from §2.4:
delete this run's `barometric_readings`, then insert a full 90-minute,
5-minute-step window for **every** synthetic buoy, evaluated at the beat's
squall offset. Insert the `squall_events` row too (tagged), since the API reads
that table.

**Check:** fire beat 0 → `GET /api/ai/squall/current` returns `detections: []`.
Fire beat 1 → still `[]`, but `/api/ai/squall/buoy/{id}` shows a falling trace
on the outer buoys. Fire beat 0 again → back to flat. Reset → the generator's
original readings are intact and the demo rows are gone.

### Task 4 — Weather proxy and beat 2

1. `app/demo/weather.py` builds Open-Meteo-shaped payloads per §3.5 for a given
   beat, driven by per-sector target conditions in the scenario definition.
2. `/api/demo/weather/forecast` and `/marine` parse the `latitude`/`longitude`
   CSVs and return **exactly one entry per coordinate, in request order**.
3. In `dangerZonePredictor.js`, replace lines 4–5 with a configurable base —
   e.g. `window.AQONE_WEATHER_BASE` / `AQONE_MARINE_BASE`, defaulting to the
   existing Open-Meteo URLs so production behaviour is byte-identical.

**Check:** with the panel's base override active, beat 0 → all sectors green;
beat 2 → the northern sectors red, the rest unchanged, with real reasons in the
popups. Without the override, the dashboard still hits Open-Meteo exactly as
before. Verify with `node --check web/js/dangerZonePredictor.js`.

### Task 5 — Beat 3

Advance the pressure window to detection. Publish the advisory (per §3.7 —
**ask Lenard about the auth path before implementing**).

**Check:** `/api/ai/squall/current` returns a detection with probability ≥
threshold; `GET /api/public/advisories` includes the new advisory; the handset
(with mobile's help) alarms.

### Task 6 — Beats 4, 5, 6

- **Beat 4:** insert `buoy_contacts` rows for an existing generator vessel that
  break its pattern. Let `/api/ai/anomaly/active` rebuild. Do not write scores.
- **Beat 5:** `POST /api/sos` for that vessel, then insert a tagged `incidents`
  row with `abnormal_reason = 'capsize'` and a `true_track` from
  `_simulate_drift_track`.
- **Beat 6:** call the **existing** `POST /api/ai/drift/incident/{id}/searched`
  with a sector deliberately placed over a high-probability region so the
  posterior shifts visibly.

**Check:** beat 4 → the vessel appears in `/api/ai/anomaly/active`. Beat 5 →
the incident appears in `/api/ai/drift/incidents` and `/incident/{id}` returns
three contour levels. Beat 6 → contours returned after the call differ
measurably from before. Reset → all gone, generator data intact.

### Task 7 — Control panel

`web/html/demo-control.html` + `web/js/demo-control.js`. Not linked from any
nav. Contents:

- One row per beat: label, fire button, fired/pending state
- Run-arc control with pause / step / skip-to-beat
- **Reset — large, unmissable, no confirmation dialog**
- Live state readout polled from `/api/demo/state`
- A connection indicator, so a dead panel is obvious *before* the operator
  presses a button and nothing happens
- The `X-Demo-Key` entered once and held in memory

It runs on a phone or second laptop under stage lighting, operated by someone
who is nervous. **Contrast and target size over polish.** No animations.

**Check:** the full arc can be driven end to end, out of order, and reset,
without touching a terminal.

### Task 8 — Tests

`backend/tests/test_demo.py`, matching the style of the existing suite:

- demo routes are absent when `DEMO_MODE` is unset
- a wrong or missing `X-Demo-Key` is rejected
- reset removes exactly the tagged rows and nothing else
- the weather proxy returns one entry per requested coordinate, in order
- firing the same beat twice is idempotent

**Check:** `pytest` — 89 + your new tests passing, 1 expected failure. `ruff
check .` clean.

---

## 6. Definition of done

- [ ] All eight tasks pass their checks
- [ ] `pytest`: 89 existing + new tests pass, 1 expected failure, no regressions
- [ ] `ruff check .` clean
- [ ] `node --check` clean on both touched/created JS files
- [ ] With `DEMO_MODE` unset, the app is byte-for-byte behaviourally identical
      to master — no demo routes, Open-Meteo called directly
- [ ] Reset run 5 times in a row leaves the generator dataset intact
- [ ] Every injected row has `is_synthetic = TRUE` and a `demo_tag`
- [ ] The full arc runs end to end from the panel
- [ ] Committed on `demo`, never on `master`

---

## 7. Explicitly out of scope

Do not build: auto-playing timers beyond the simple arc runner; a login for the
panel; websockets or SSE for panel state (polling is fine); moving vessel
positions; a scenario editor UI; changes to any model; changes to
`dashboard.js`/`.html`/`.css`; changes to the Flutter app; anything in
`firmware/` or `gateway/`; retraining anything.

---

## 8. When to stop and ask

Stop and ask Lenard — do not decide alone — if:

- The squall series will not detect deterministically with plausible parameters
  (Task 2)
- The advisory auth path is ambiguous (§3.7)
- Any fact in §3 contradicts what you find in the code
- A task requires editing a file not listed in §4
- `pytest` drops below the 89-pass baseline for a reason you cannot fix
- You believe a different architecture would be better

**That last one especially. This plan is not a starting point for your own
design. Follow it 100%.**
