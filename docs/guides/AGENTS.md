# AGENTS.md — AqOne v2

> Place this file at the **repository root**. Place the numbered docs in `docs/`.
> Read this file completely before writing any code.

## What this project is

AqOne is a maritime safety system for small-scale fishermen in New Washington,
Aklan, Philippines. Field interviews established that **the entire fishing
ground is a cellular dead zone** — every fisherman loses signal while working.

The product is a **LoRa mesh of anchored buoys** that carries an SOS from an
offline phone to a regulator dashboard on shore. Everything else is supporting
material.

## The one sentence that defines success

> **An SOS from a phone in airplane mode, over real radio, appearing on the
> regulator dashboard.**

If a change does not serve that sentence, it is out of scope.

## Hard scope — do not exceed

**BUILD:**
- Buoy → gateway LoRa hop
- Phone → buoy WiFi SoftAP handoff
- Signed message envelope + idempotent ingest
- Backend: auth, ingest, SOS list, SOS acknowledge
- Dashboard: live SOS feed + acknowledge button
- Four delivery states, visible in the app
- Deployed with a working healthcheck

**DO NOT BUILD** (these are deliberate cuts, not oversights):
- AI/ML model of any kind, hotspot heatmap, catch-decline detection
- Photo upload, advisories CRUD, sea-condition control
- Overdue/float-plan check-in, profile pages, settings, terms pages
- Anything not named in the BUILD list

Catch logging was on this list too; it is back in scope - see
`docs/07_SCOPE_OUT.md`'s "Amended — now in scope" and `backend/app/api/catch.py`.
(The rest of this list has drifted stale in other ways beyond catch logging -
AI models, advisories CRUD, profile pages, settings and terms pages are all
built - left uncorrected here since it wasn't asked for.)

If you think something in the DO NOT BUILD list is needed, **stop and ask**.
Do not implement it speculatively.

## Non-negotiable rules

These come from a previous build where each one caused a production bug.

1. **Schema lives only in `migrations/`.** Never put `CREATE TABLE` in
   application code. (v1 had schema in three places; a fix applied to one was a
   bug preserved in another.)
2. **Enums on the wire, labels in the UI.** Never send a display string like
   `"Safe to Go Out"` as an API value. (v1 did; every request 422'd.)
3. **One response envelope, everywhere.** See `docs/01_CONTRACTS.md`. Never
   invent a new response shape. (v1 mixed shapes; pins silently never rendered.)
4. **Clients never reimplement permissions.** The server returns the permission
   list; clients render from it. (v1 duplicated role logic and it drifted — the
   only authorised role had the control hidden from it.)
5. **Every table must have a writer.** If nothing inserts into it, don't create
   it. (v1 had three orphan tables; one broke the vessel panel for weeks.)
6. **Escape everything server-supplied before rendering.** (v1 had two stored
   XSS paths.)
7. **No file over ~400 lines.** Split it. (v1's 2,454-line `main.py` and
   3,731-line `dashboard.js` are where every hard bug hid.)
8. **No secrets in the repo, ever.** The repo will be public. A live credential
   in a public repo, in a competition judging cybersecurity, is fatal.
9. **Health checks must be verified against the real schema.** (v1's health
   check referenced a table that never existed and failed the deploy of a
   perfectly healthy app.)
10. **Nothing merges without being run end to end once.**

## Read order

| Doc | When to read |
|---|---|
| `docs/00_START_HERE.md` | Context, architecture, ownership. Read first. |
| `docs/01_CONTRACTS.md` | **Before writing any client or server code.** The shared contract. |
| `docs/02_DATA_MODEL.md` | Before touching the database. |
| `docs/03_BACKEND.md` | Working on FastAPI. |
| `docs/04_FIRMWARE.md` | Working on the ESP32 buoy. |
| `docs/05_FLUTTER.md` | Working on the mobile app. |
| `docs/06_DASHBOARD.md` | Working on the regulator web dashboard. |
| `docs/07_SECURITY.md` | Before any auth, signing, or ingest work. Judged criterion. |
| `docs/08_DEMO_AND_STATUS.md` | Demo script, contingency, Q&A, honesty table. |

`DESIGN.md` (UI layout and colours) is authored by the team — do not generate
or overwrite it.

## Working constraints

- External event deadlines are maintained in [`docs/53_EXTERNAL_DEADLINES.md`](../53_EXTERNAL_DEADLINES.md).
- Do not infer implementation deadlines from external events; keep code work
  aligned with the active implementation plan and current status evidence.
- Stack is fixed: FastAPI + PostgreSQL/PostGIS on Railway · Flutter (native
  Android) · plain HTML/CSS/JS dashboard · ESP32-S3 + SX1262 via Arduino IDE +
  RadioLib.
- Prefer boring, working code over clever code. There is no time to debug
  cleverness.

## When you are unsure

Ask. Do not guess at a contract, a schema, or a scope boundary. Guessing at
contracts is precisely what broke the previous build.
