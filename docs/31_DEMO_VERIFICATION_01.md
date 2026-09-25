# 31 — Demo Verification 01: independent review of the `demo` branch

> **Note (2026-09-25): barometer dropped.** The buoy barometer is no longer part of the
> architecture; squall alerts now come from the PAGASA weather API (PRD §5.1).
> References below to barometers, pressure readings or the pressure-based squall model
> describe that retired design and the code it left behind (`backend/app/ai/squall.py`,
> `barometric_readings`, `/api/v1/pressure-events`), which stays until it is removed.

Reviewed 2026-08-21 against commits `a54e301 … 4989a59`. Luna reported the
implementation complete with `pytest`, `ruff`, migrations and **model
calibration unverified** because its environment lacked dependencies and a
database.

I ran ruff and the real squall model here. **The branch does not work as
committed.** Two blocking issues, one design flaw I introduced, and several
risks.

Scope discipline was good: no changes to `dashboard.js`, `trip_profile.py`, or
any model. The three permitted file edits are minimal and correct in shape.

---

## BLOCKER 1 — every beat raises `NameError`

`backend/app/demo/scenarios.py:462-464`

```python
    _beat(index)                                              # return discarded
    pool = get_pool()
    await _write_pressure_window(pool, state.run_id, beat, state.scenario)
                                                   # ^^^^ undefined
```

`beat` is never assigned. `ruff check --select F` confirms:

```
F821 Undefined name `beat`
   --> app/demo/scenarios.py:464:54
```

**`fire_beat()` raises `NameError` on every call. Not one beat can fire.**

This is precisely why "Python compilation passed" is not evidence — a bare name
lookup compiles fine and fails at runtime.

**Fix:** `beat = _beat(index)`.

---

## BLOCKER 2 — the pressure beats were never calibrated, and the committed values fail

Plan 29 Task 2 required empirical calibration before writing the beats.
Commit `92f1bdf` ("tune pressure beats") was made without ever running the
model.

I ran the committed staging against the real bundle
(`app/ai/models/squall.pkl`, threshold 0.55), reproducing
`_write_pressure_window` exactly, sampled across 72 hourly run-times because
the baseline field depends on wall-clock:

| Beat | `event_age_minutes` | Fired | Probability range | Intended |
|---|---|---|---|---|
| 0 Baseline | 0 | **3 / 72** | 0.768 – 0.789 | never |
| 1 Pressure falls | 60 | **27 / 72** | 0.553 – 0.843 | never |
| 2 Zones escalate | 75 | **72 / 72** | 0.742 – 0.996 | never |
| 3 RETURN NOW | 90 | 72 / 72 | 0.935 – 1.000 | always ✅ |

Only beat 3 behaves as designed.

- **Beat 0 shows a confident RETURN NOW on a calm baseline 4% of the time.**
  The demo can open with the warning already on screen.
- **Beat 2 always fires**, so the RETURN NOW arrives a beat early and steps on
  beat 3's reveal.
- Behaviour depends on the hour the demo runs — you can rehearse clean at 2pm
  and break at 4pm.

### Root cause

The front crosses the whole array almost instantly. Origin 18 km at 28 kph is a
~38-minute transit, and the array spans only a few km, so arrival times barely
differ between buoys. Visible drop goes `0.00 → 0.69 → 4.03 hPa` across 30
minutes — a step, not a build-up. Measured:

| `event_age_minutes` | 0–50 | 55 | 60 | 90 |
|---|---|---|---|---|
| Fired / 72 | 0 | 1 | 22 | 71 |
| Mean visible drop | 0.00 hPa | 0.24 | 0.69 | 4.03 |

There is no age at which pressure is visibly falling but the model reliably
stays quiet. Beats 1 and 2 have nowhere to sit.

### What does work

Slowing the front and moving it further out spreads the arrival times and gives
a gradual build-up. With `speed_kph=12`, `origin_km=30`, `rise_minutes=90`
(sampled over 24 run-times):

| `event_age_minutes` | 150 | 185 | 200 | 215 | 230 | 245 |
|---|---|---|---|---|---|---|
| Fired / 24 | 1 | 1 | 10 | 21 | **24** | **24** |
| Mean drop (hPa) | 0.00 | 0.19 | 0.81 | 1.64 | 2.47 | 3.31 |

A usable schedule: **beat 1 = 185, beat 2 = 200, beat 3 = 235.** Beat 3 is
solid. Beat 1 shows an early fall without warning. Beat 2 remains partly
unreliable — but **beat 2 is the danger-zone beat, and that path is fully
deterministic through the weather proxy**, so squall firing early there is
cosmetic, not structural.

These numbers come from scikit-learn 1.8.0 unpickling a 1.9.0 bundle (the
version pinned in `requirements.txt` was unavailable here). Coefficients load
cleanly and the ranking is stable, but **re-run the harness on the demo service
before trusting the exact figures.**

### The residual false positive is the model, not the code

Roughly 1-in-24 baseline windows detect with no event at all. That is the
published precision of 0.286 showing through. It cannot be tuned away in the
demo layer.

**Recommendation:** have the control panel display the live squall probability
from `/api/ai/squall/current`, so the operator can confirm beat 0 is quiet
before presenting and re-start the scenario (which re-anchors `as_of`) if it
is not.

---

## DESIGN FLAW — the fleet clock is mine, and it is under-specified

`anomaly.py` now does what decision 30 authorised:

```python
dataset_now = max((row['observed_at'] for row in rows), default=None)
as_of = dataset_now or contacts[-1].observed_at
```

The change is faithful. **My recommendation was wrong in an important way.**

`dataset_now` is a single fleet-wide maximum. Beat 4 writes contacts at *now*,
days after the generator dataset was seeded. Every other synthetic vessel's
last contact is then days behind `dataset_now`, so `overdue_factor` saturates
at ~1.0 and, at weight 0.85, **the entire generator fleet scores ≈ 0.85 and
alerts.** The target vessel will not stand out — the dashboard will be a wall
of alerts.

This is the same failure mode I attributed to `datetime.now()` when I rejected
it. The dataset-relative clock does not avoid it; the demo's own writes push
the clock forward.

**The missing concept is trip completion.** A vessel that finished its trip and
went home is not overdue — it is done. Scoring must consider only *open* trips.

Options, in preference order:

1. **Freshness guard.** Score only trips whose last contact is within a
   configurable window of `dataset_now` (a few hours). Semantically right and
   still small.
2. **Per-vessel clock with a cap** — bounds the overdue term so a stale vessel
   cannot saturate.
3. Revert to per-vessel last contact and drive beat 4 another way.

**This needs deciding and then testing against a seeded database.** Do not
assume option 1 works because it sounds right — that assumption is what
produced this flaw.

---

## Risks worth fixing

**The weather override persists in `localStorage`.** `dangerZonePredictor.js`
reads `AQONE_WEATHER_BASE` from `localStorage`, so a browser used for the demo
keeps hitting the demo proxy **forever**, including against production. A
dispatcher's dashboard could silently show demo weather. Prefer a URL query
parameter or `sessionStorage`, or have the panel clear the keys on reset.

**`app/api/demo.py` is imported unconditionally** in `main.py`, so
`app/demo/scenarios.py` loads in production even with `DEMO_MODE` off. It only
defines routes today, but an import-time error there would break production.
Move the import inside the `if`.

**A stray binary was committed.** `Module_2_Worksheets_AqOne_Completed.docx`
(20 KB) landed in the branch and is unrelated to the demo.

**Beat 4's 180-minute gap is a guess.** Never calibrated against a real
profile, and its correctness depends on the fleet-clock decision above.

**`_write_anomaly_contacts` writes one contact per vessel**, all on the same
buoy with `sequence_no = 1`. A single-contact trip is a thin basis for
`expected_next_contact`. Verify against a real profile.

---

## Still unverified — needs a database

Nothing below can be checked without Postgres and the seeded dataset:

- `python migrate.py` applying `015_demo.sql`
- Full `pytest` (the 89-pass baseline) and `ruff check .` across the repo
- Every DB path in `scenarios.py` — the SQL, the `executemany` tuples, the
  reset ordering, the `ON CONFLICT` on advisories
- `_write_incident`'s direct calls into `ingest_sos` and `record_searched_sector`
- Whether reset truly leaves the generator dataset intact

---

## Order of work

1. Fix `beat = _beat(index)` — one line, unblocks everything
2. Decide the fleet-clock question (needs Lenard)
3. Stand up the demo service and seed it — nothing further is verifiable without it
4. Re-run the calibration harness there; adopt the slow-front parameters
5. Run `pytest` and `ruff check .`
6. Fix the localStorage persistence and the unconditional import
7. Calibrate beat 4 against a real profile
8. Only then: the eval fix from decision 30 §4

---

## Note on process

Two of these — the `NameError` and the uncalibrated beats — would have been
caught by running the code once. Neither is a subtle bug. The plan named
calibration the highest-risk task and required it *before* the beats were
written; it was committed as "tuned" without being run.

**The environment gap is the real problem.** An agent that cannot execute what
it writes cannot verify it, and "compilation passed" reads as confidence it has
not earned. Whoever continues this work needs a database and the dependencies
installed first — not as a later verification step, but as a precondition.
