# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## One-line project

Offline SOS mesh for small-scale fishermen in New Washington, Aklan: phones hand an SOS to anchored LoRa buoys over WiFi, buoys relay over LoRa to a gateway with internet, the gateway forwards to a FastAPI backend, and the backend pushes the SOS to an MDRRMO dashboard over SSE.

## Agent handoff

Follow the Agent handoff section in `AGENTS.md`: read root `HANDOFF.md` on arrival and update it after every verified step.

## Build order — strictly sequential

Do NOT start a step until the previous one demonstrably works. Do NOT skip steps.

1. Deployed skeleton — FastAPI on Render, green `/health/ready`, migrations run
2. Two radios talk — raw LoRa packet between two ESP32s, no protocol
3. Buoy → gateway → backend — button press on a buoy creates a real SOS row
4. Phone → buoy → backend — phone in airplane mode, SOS lands
5. Dashboard live feed + acknowledge — full path visible, ack persists
6. Range test outdoors — record actual metres in `docs/08_DEMO_AND_STATUS.md`
7. Freeze, rehearse x3, record screencast

The canonical project brief is `docs/00_START_HERE.md`. The product scope is `docs/Aqone_PRD (2).md` (v3.0).

## Shared contracts — do not diverge

All workstreams interoperate through these documents. If a contract needs to change, update the doc first and tell the affected owners.

| Contract | Doc | Who consumes |
|---|---|---|
| LoRa binary frame | `docs/02_LOAM_PACKET_SPEC.md` | firmware (Daniel), gateway (Arnold) |
| Phone ↔ buoy WiFi HTTP | `docs/03_PHONE_BUOY_WIFI.md` | firmware (Daniel), mobile (Jade/Doreen) |
| Gateway → backend HTTPS | `docs/04_INGEST_API.md` | gateway (Arnold), backend (Lenard) |
| Public REST + SSE | `docs/05_PUBLIC_API.md` | backend (Lenard), dashboard (Arnold) |
| Delivery states | `docs/06_DELIVERY_STATES.md` | all — the four states are the product language |
| Mobile UI strings | `docs/22_LOCALIZATION_PLAN.md` | mobile (Jade/Doreen Kay) |

## Architecture

Three layers:

```
app/ai/          ← the thinking          (the models)
app/api/         ← the doors             (the URLs the app + dashboard call)
everything else  ← the plumbing          (database, startup, auth, geography)
```

**The core principle:** `app/ai/` thinks. `app/api/` answers the phone. The brain is separate from the mouth. This split lets you test models without starting a web server or database.

### Backend structure

- **`app/api/sos.py`** — the most important file. Receiving SOS, de-duplicating, the live feed, acknowledging with ETA (358 lines).
- **`app/ai/drift.py`** — drift prediction (500 lines). Where does someone in the water end up?
- **`app/ai/squall.py`** — storm nowcasting from buoy pressure. The trained classifier lives here.
- **`app/ai/trip_profile.py`** — learns each boat's habits, flags overdue vessels.
- **`app/ai/search.py`** — Bayesian re-tasking: "we searched here and found nothing," update the map.
- **`app/geo.py`** — single source of truth for "where is New Washington." The water polygon, shore stations, and the "is this point at sea?" check.
- **`app/simulation/generator.py`** — makes all the fake data (1,254 lines).
- **`migrations/`** — database schema, run in numerical order, never edit old ones.
- **`*_eval.py` files** — NOT part of the running system. Measure model performance manually and write results to `models/eval_results.json`.

### Firmware structure

Two sketches:

| Sketch | Flash to | Role |
|---|---|---|
| `firmware/buoy/AqOneBuoy/` | Boat safety pod or optional stationary relay buoy | WiFi AP only + LoRa |
| `firmware/shore/AqOneShore/` | Board on the mast with internet | LoRa + WiFi station only |

**Critical:** Both sketches include `AqOneLoam.h`. The file exists in both folders and **the two copies must stay byte-identical**. A mismatch behaves exactly like being out of range. After editing either copy:

```bash
diff firmware/buoy/AqOneBuoy/AqOneLoam.h firmware/shore/AqOneShore/AqOneLoam.h
```

It must print nothing.

### Mobile

Flutter handset with offline SQLite outbox. Three languages: English, Tagalog (fil), Aklanon (akl). **New user-facing text goes in `mobile/lib/l10n/app_en.arb`** with an `@key` description, then is read via `AppLocalizations.of(context).yourKey`. Do not add bare `Text('...')` literals to `mobile/lib/`. Log messages, SQL, and wire values stay as literals — those are not UI. Never put display text on an enum.

## Commands

### Backend

```bash
cd backend

# Setup
python -m venv .venv
# Activate .venv using the command for your shell
python -m pip install -r requirements.txt

# Database
export DATABASE_URL=postgresql://user:pass@localhost/aqone_dev
python migrate.py

# Run server
python -m uvicorn app.main:app --reload

# Test and lint
python -m pip install -r requirements-dev.txt
python -m pytest -q                    # Run all tests
python -m pytest tests/test_sos.py -v # Run single test file
python -m ruff check .                 # Lint
python -m ruff check . --fix           # Fix linting issues

# Check health
curl http://localhost:8000/healthz
```

**Note:** Use a disposable database for tests because migrations modify schema and data.

### Firmware

```bash
cd firmware

# Build and flash (requires Arduino IDE or platformio CLI)
# Edit board config at top of .ino: AQONE_NODE_ID, AQONE_NODE_NAME
# Edit shared config in AqOneLoam.h: LORA_FREQ_MHZ, LORA_SF, LOAM_KEY, etc.
# Verify the two AqOneLoam.h files are identical

# Check with platformio
platformio run -e esp32s3  # Build
platformio run -t upload   # Flash to board
```

### Mobile

```bash
cd mobile
flutter pub get
flutter analyze                        # Check code
flutter test                           # Run tests
flutter build apk --release \
  --dart-define=PITCH_MODE=true \
  --dart-define=BACKEND_BASE_URL=https://aqone-backend.onrender.com
```

### Web (dashboard)

```bash
cd web

# Run tests (Node.js 18+ required)
node --test test/*.test.js

# Verify all .js syntax
Get-ChildItem js, test -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

## Delivery states

The app must never display a later state without observing evidence for it.

```
saved -> relayed -> delivered -> acknowledged
```

Defined in `docs/06_DELIVERY_STATES.md`.

## Key constraints and limitations

- The manual SOS path must work independently of every model — AI is advisory only.
- No foundation model or external LLM inference API runs inside the product.
- Drift output is a probability distribution, not a location guarantee.
- The phone never needs cellular signal; it works in airplane mode.
- Two boards with different radio settings behave exactly like two boards out of range: no error, no log line, nothing arrives.
- `LOAM_KEY` in firmware: **anyone with this repository can inject a distress call into the mesh** until you change it.
- No range has been measured outdoors yet — every RF figure is modelled.

## Localization

- English, Tagalog (fil), Aklanon (akl)
- Tagalog locale code is `fil`, not `tl`
- Aklanon has no Flutter localizations — `mobile/lib/core/l10n_fallback.dart` handles the fallback
- Translations in `app_fil.arb` and `app_akl.arb` are unreviewed drafts

## Team ownership

| Person | Owns |
|---|---|
| Lenard | Backend, architecture, deployment |
| Arnold | Website Dashboard, ingest pipeline, gateway |
| Daniel | Hardware/firmware — boat pod, sensor buoy. Critical path. |
| Jade | Flutter Application |
| Doreen Kay | UI/UX, pitch deck |

## Development principles

This project follows the **"ponytail" lazy senior developer** approach: efficiently reuse existing patterns and defer unnecessary work.

### Verification requirements

Before completing any change:
- **Backend:** `python -m pytest -q` and `python -m ruff check .`
- **Firmware:** Code compiles, no warnings; `diff` the two `AqOneLoam.h` files
- **Mobile:** `flutter analyze` and `flutter test` pass
- **Web:** `node --test web/test/*.test.js` passes, all `.js` syntax valid

### Scope and focus

- Do not add code comments unless the WHY is non-obvious (a hidden constraint, subtle invariant, or workaround).
- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Bug fix = root cause, not symptom. Grep every caller and fix once rather than patching each caller.

### Code quality and standards

- Never use the em dash "-". Use plain dash "-" instead.
- When writing commit messages, NEVER auto-add your agent name as co-author.
- Never manually modify CHANGELOG.md files or any files marked as auto-generated.
- When writing or substantially editing long Markdown files, put each full sentence on its own line. Preserve normal Markdown structure, but avoid wrapping multiple sentences onto one physical line.
- When making technical decisions, do not give much weight to development cost. Instead, prefer quality, simplicity, robustness, scalability, and long term maintainability.
- When doing bug fixes, always start with reproducing the bug in an E2E setting as closely aligned with how an end user would use it. This makes sure you find the real problem so your fix will actually solve it.
- When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel perfection. If something clearly looks off, even if it is not directly related to what you are doing, try to get it fixed along.
- Apply that same high standard to engineering excellence: lint, test failures, and test flakiness. If you see one, even if it is not caused by what you are working on right now, still get it fixed.

### Database and migrations

- **Never edit an old migration** — always add a new numbered file.
- Migrations run in numerical order on every deploy.
- Use a disposable test database; `python -m app.simulation.generator` truncates operational tables.

### Secrets and configuration

- No secrets in the repo. Use `.env` locally (gitignored) and platform env vars in deployment.
- `*.env.example` files are allowed.
- Update the firmware's `LOAM_KEY` before deploying to production.
- The gateway needs an operator bearer token to push acknowledgements back down the mesh.

## Important docs to read first

| If you need to... | Read... |
|---|---|
| Understand current status and evidence | `docs/08_DEMO_AND_STATUS.md` and README.md |
| Understand backend architecture | `docs/18_BACKEND_STRUCTURE.md` |
| Understand AI models and evidence | `docs/17_AI_EXPLAINED_SIMPLY.md` and `docs/16_QA_DISCLOSURES.md` |
| Understand the LoRa frame format | `docs/02_LOAM_PACKET_SPEC.md` |
| Understand phone ↔ boat-pod WiFi | `docs/03_PHONE_BUOY_WIFI.md` and `docs/21_WEEK1_CONTRACT_FIXTURES.md` |
| Understand delivery states | `docs/06_DELIVERY_STATES.md` |
| Understand mobile localization | `mobile/lib/l10n/README.md` and `docs/22_LOCALIZATION_PLAN.md` |
| Understand firmware setup | `firmware/README.md` and `docs/19_HELTEC_DATA_FLOW.md` |

## Repository layout

```
backend/       FastAPI, PostgreSQL migrations, AI services, tests
firmware/      ESP32-S3 firmware: buoy/ (boat pod & buoy) and shore/ (gateway)
mobile/        Flutter handset application
web/           MDRRMO dashboard and browser hazard model
docs/          Contracts, references, decisions, plans, verification records
fixtures/      Shared contract fixtures
```

## Definition of done (whole build)

- [ ] Phone in airplane mode sends an SOS that reaches the dashboard
- [ ] Dashboard acknowledge persists across a reload
- [ ] The four delivery states are visible and honest in the app
- [ ] Deployed, healthcheck green, demo URL reachable from outside the venue
- [ ] Repo public, no secrets, README with setup instructions
- [ ] Screencast recorded
- [ ] `docs/08_DEMO_AND_STATUS.md` status table reflects reality

## External resources

- **Deployed backend:** `https://aqone-backend.onrender.com` (green healthcheck at `/health/ready`)
- **Mobile pod address:** `http://192.168.4.1` (local WiFi only, airplane mode OK)
- **Status and evidence:** `docs/08_DEMO_AND_STATUS.md` (newest dated entry first)
- **Product scope (canonical):** `docs/Aqone_PRD (2).md` (v3.0) — roadmap items marked `[Roadmap — not implemented]`

## Deliberately NOT building

See `docs/07_SCOPE_OUT.md` for the full list and amendments. Still out: no photos, no fisheries-enforcement or surveillance features, no LoRa downlink to the handset. Catch logging and activity heatmap are now in scope — see `docs/07_SCOPE_OUT.md`.
