# 18 — The Backend Folder, Explained

For the team. Companion to `17_AI_EXPLAINED_SIMPLY.md`, which covers what the AI
*does*. This one covers where everything *lives*.

Updated 2026-09-25 for the edge-case remediation (PR #79): the new
`app/incidents/` policy layer, the scheduler, SMS escalation and operations status.

---

## The one idea that makes the whole folder make sense

There are two files called `drift.py`. Two called `squall.py`. This is not a
mistake — it's the core organising rule:

> **`app/ai/` thinks. `app/api/` answers the phone.**

- `app/ai/drift.py` — the actual drift model. Knows about physics and
  probability. Knows **nothing** about the web.
- `app/api/drift.py` — the doorway. Knows about URLs and JSON. Knows **nothing**
  about physics. It just fetches data, calls the model, and hands back the answer.

Once you see that split, the rest is obvious. The brain is separate from the
mouth.

**Why we did it that way:** you can test the drift model without starting a web
server or a database. That's why the test suite runs in 14 seconds.

---

## The four layers

```
app/ai/          ← the thinking          (the models)
app/incidents/   ← the rules             (pure SOS policy: no web, no database)
app/api/         ← the doors             (the URLs the app + dashboard call)
everything else  ← the plumbing          (database, startup, auth, geography, jobs)
```

`app/incidents/` is the same idea as `app/ai/`, applied to the SOS rules
themselves: which incidents go down the radio, what order the dispatcher sees,
when a fisher's reply reopens a call. The functions there take plain values and
return plain values, so they are tested without a server or a database.
`tests/test_incidents_is_pure.py` fails if any of them imports `fastapi`,
`asyncpg`, `httpx` or `app.db`.

---

## `app/incidents/` - the rules

| File | What it decides |
|---|---|
| `lifecycle.py` | Resolution codes (`rescued`, `stood_down_by_fisher`, ...) and the 2-hour window in which a fisher's "still in danger" reopens a closed call. |
| `delivery.py` | The four delivery states (`docs/06_DELIVERY_STATES.md`) from the stored flags. |
| `downlink.py` | Which 12 incidents the shore gateway sends back down the radio, and in what order. |
| `triage.py` | The dispatcher's order (waiting before answered, corroborated before not) and flood detection. |
| `plausibility.py` | Advisory flags such as `position_on_land`; they never block or reorder a call. |
| `escalation.py` | Which unanswered calls are due for an SMS, and the message text. |
| `trust.py` | Whether a vessel counts as verified. |
| `text.py` | Cutting text to a byte limit without splitting a character. |

`app/mesh/chat_policy.py` does the same for mesh chat: reserved sender names and
the per-sender rate limit.

---

## `app/ai/` — the thinking

The models and the scripts that score them.

| File | What it is |
|---|---|
| `drift.py` | Drift prediction. Where does someone in the water end up? **Biggest single model file (500 lines).** |
| `squall.py` | Storm nowcasting from buoy pressure. The trained classifier lives here. |
| `trip_profile.py` | Learns each boat's habits, flags overdue vessels. |
| `search.py` | Bayesian re-tasking — "we searched here and found nothing," update the map. |
| `current_field.py` | Turns real buoy current readings into a current map the drift model can use. Falls back to simulated data when there are no readings. |
| `coverage.py` | Works out how much water the buoy array actually covers. **Built but not yet connected to any URL.** |
| `eval_store.py` | Saves and loads the measured performance numbers. |
| `models/squall.pkl` | The saved, trained squall model. The only trained-model file in the backend. |

**The `*_eval.py` files** (`drift_eval`, `squall_eval`, `trip_profile_eval`,
`coverage_eval`) are **not** part of the running system. They're the report
cards — you run them manually to measure how well each model performs, and they
write the results to `models/eval_results.json`.


---

## `app/api/` — the doors

Every URL the mobile app or dashboard can call. These files are thin on purpose.

| File | What it handles |
|---|---|
| `sos.py` | **The most important file in the backend.** Receiving SOS, de-duplicating (by incident nonce, or `client_ts` for old phones), the triage-ordered live feed, acknowledge / resolve / reopen with version checks, the radio downlink, and the fisherman's reply. About 860 lines. |
| `mesh.py` | Nearby-boat chat. Anyone may post; who you are decides the `origin`. Reading needs a credential. |
| `vessel_profile.py` | A boat's declared owner identity, and the responder "Confirm vessel" route. |
| `vessel_auth.py` | Pairing codes, device enrolment and token refresh for handsets. |
| `ops_status.py` | Gateway last-heard, SMS configured, database expiry, scheduler last run. |
| `contacts.py`, `pressure_events.py`, `current_events.py` | Buoy telemetry from the gateway. |
| `drift.py` | Search maps, incident list, recording a searched sector. |
| `squall.py` | Current storm status, per-buoy status, retraining. |
| `anomaly.py`, `anomaly_cases.py` | Overdue vessels, the fleet-wide "monitoring" flag, and the trip-check review queue. |
| `advisories.py`, `public.py` | Official warnings and the unauthenticated safety feeds for the app. |
| `auth.py` | Login, logout, token refresh, and admin account creation. |
| `sea_condition.py` | The MDRRMO's human "Safe to Go Out / Not Advised" declaration. **Not AI** — a person sets this. |
| `catch.py`, `trips.py`, `hotspots.py` | Catch logs, vessel trips, and the catch-activity heatmap. |
| `ops_audit.py` | The append-only operations audit log and its admin export. |
| `demo.py` | Demo-only routes, off unless `DEMO_MODE` is set. |
| `metrics.py` | Serves the eval numbers. Returns 404 rather than fake numbers when they don't exist. |

---

## The plumbing

| File | Purpose |
|---|---|
| `app/main.py` | **Start here if you're lost.** Wires every door onto the app and sets which ones need a login. |
| `app/db.py` | Opens the database connection pool at startup, closes it at shutdown. |
| `app/auth.py` | Password hashing and login tokens. The security guts. |
| `app/geo.py` | **The single source of truth for "where is New Washington."** The water polygon, shore stations, the "is this point at sea?" check and `distance_km`. If a boat ever appears on land, the bug is here. |
| `app/audit.py` | Writes one row to the operations audit log inside the caller's transaction. |
| `app/scheduler.py` | Background jobs started with the app: SOS escalation every 30 s and anomaly evaluation every 5 min. A Postgres advisory lock keeps two copies of the app from running the same job twice. Set `AQONE_SCHEDULER=0` to switch it off. |
| `app/notify.py` | Sends the escalation SMS through Semaphore. With no `SEMAPHORE_API_KEY` or `ONCALL_SMS_NUMBERS` it reports "not configured" instead of failing. |
| `app/demo/` | The demo scenario engine (synthetic squall and drift). |
| `app/simulation/generator.py` | Makes all the fake data — buoys, weather, boats, trips. **The biggest file in the backend at 1,254 lines.** |
| `migrate.py` | Runs the database migrations in order on every deploy. |

---

## `migrations/` — the database, in order

Each file adds to the database. They run in numerical order and only once. **Never
edit an old one** — always add a new numbered file.

| File | What it added |
|---|---|
| `001_init.sql` | Core tables: vessels, buoys, SOS events |
| `002_simulation.sql` | Tables for the synthetic data |
| `003_anomaly.sql` | Trip profiles and incidents |
| `004_dashboard.sql` | Dashboard support |
| `005_auth.sql` | Operator accounts |
| `006_mesh_radii.sql` | LoRa range per buoy |
| `007_sos_ingest.sql` | The de-duplication keys |
| `008_responder_loop.sql` | ETA, responder status, fisherman's reply |
| `009_search_sectors.sql` | Searched sectors, for the Bayesian update |
| `010` to `031` | Advisories, mesh chat, catch logs, device credentials, buoy contacts and pressure/current telemetry, anomaly and drift cases, the operations audit log, vessel trips and identity profiles, operator token versions (read the file names in `migrations/`) |
| `032_incident_lifecycle.sql` | Incident `version`, `resolution_code`, reopen columns |
| `033_sos_nonce.sql` | Incident nonce and the two de-duplication keys; the conflicting second position |
| `034_gateway_status.sql` | When the shore gateway last polled |
| `035_vessel_identity_provenance.sql` | Who set each profile field, shore contact, responder confirmation |
| `036_escalation_and_jobs.sql` | `escalated_at` and the scheduler's last-run table |
| `037_contact_via_and_welfare_time.sql` | Which device made a buoy contact; when a trip's welfare was last updated |

---

## `tests/` - run them all before you push

Run `python -m pytest -q` from inside `backend/` (about 570 tests on 2026-09-25).
The `test_edge_*_pg.py` files and the security probes need a throwaway Postgres:
set `AQONE_PROBE_PG_ADMIN_URL` (see `docs/62_EDGE_CASE_REMEDIATION_IMPLEMENTATION_PLAN.md`
Section 4.1); without it they are skipped, not failed.

The useful thing to know: `test_geo.py` and `test_mesh.py` are the ones that stop
boats appearing on land and buoys drifting out of radio range of each other.
Those two catch the embarrassing bugs.

---

## Config files

| File | Purpose |
|---|---|
| `requirements.txt` | What gets installed in production |
| `requirements-dev.txt` | Test tools only — not shipped |
| `pyproject.toml` | Linter settings |
| `.env.example` | Which environment variables you need. **No real secrets** - those live in Render's environment settings. |

---

## "I want to change X — where do I go?"

| I want to… | Go to |
|---|---|
| Change how the drift model behaves | `app/ai/drift.py` |
| Add a new URL | `app/api/` + register it in `app/main.py` |
| Fix a boat showing up on land | `app/geo.py` |
| Change the fake demo data | `app/simulation/generator.py` |
| Add a database column | New file in `migrations/` — never edit an old one |
| Change an SOS rule (ordering, reopen window, radio cap) | `app/incidents/` |
| Refresh the model performance numbers | Run the `*_eval.py` scripts |
| Understand the SOS flow | `app/api/sos.py` |

---

## Known gap

**`coverage.py` is orphaned.** It works and has tests, but nothing calls it —
no URL, nothing on the dashboard. It's a library waiting to be plugged in.
