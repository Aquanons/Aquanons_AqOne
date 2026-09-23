# AqOne security architecture

## Audit identity and constraints

- Target: `AIHackathon2026_Aquanons_AqOne`
- Source: commit `c5312b8711cb48ba89a0f014d060b62ccd5d9a5f`; worktree clean. The source advanced during reconnaissance from `3d73232696863a3cae271157635fbeda314c789f`; the delta only added an endorsement PDF and changed the SOS alarm WAV, with no reviewed code/configuration changes. The binary assets received metadata/provenance-only review and were not parsed or executed.
- Profile and scope: standard, whole repository
- Prior evidence: no compatible earlier security-audit run was found
- Evidence policy: source inspection only. This Windows workspace cannot enforce the audit skill's complete execution sandbox: empty allowlisted environment, isolated no-network namespace, read-only target and toolchain, scratch-only process writes, strict CPU/memory/process/file/disk limits, and race-safe artifact promotion. Target-controlled tests, builds, services, firmware, browsers, and fixtures were therefore not executed.

## Product and principals

AqOne is an offline maritime safety system. A fisher's phone may submit an SOS directly over HTTPS or hand it to a boat pod over an intentionally open local Wi-Fi access point. The pod persists and relays the SOS over a custom LoRa mesh to a shore gateway. The gateway forwards data to a FastAPI/PostgreSQL backend. MDRRMO/LGU operators use a same-origin browser dashboard; the backend pushes changes using REST and SSE. AI features are decision support, not autonomous response authority.

Principals are anonymous Internet callers, fishers and vessel handsets, nearby Wi-Fi/radio peers, boat pods and relays, shore gateways, authenticated MDRRMO/LGU/admin operators, the backend process, PostgreSQL, build/release operators, and deployment providers.

## Stack, entry points, and deployment

- Backend: Python 3.11, FastAPI, Uvicorn, asyncpg/PostgreSQL, Pydantic, bcrypt, HS256 JWT, NumPy/scikit-learn/joblib. Entry point: `backend/app/main.py`; migrations: `backend/migrate.py` and `backend/migrations/`.
- Dashboard: static HTML/CSS/JavaScript served by the backend from `web/`; bearer JWTs are kept in `sessionStorage`.
- Mobile: Flutter/Dart with SQLite, platform secure storage, AES-GCM field protection, HTTPS backend transport, and fixed local pod HTTP/WebSocket transport.
- Firmware: Arduino C++ for ESP32-S3/Heltec devices. `firmware/buoy/` hosts the open phone-facing AP and persistent queue. `firmware/shore/` bridges LoRa and Internet. Both use duplicated `AqOneLoam.h` codecs with truncated HMAC-SHA256.
- Deployment: Docker starts migrations and Uvicorn; `render.yaml` describes a Render web service and managed PostgreSQL. Live provider controls are not visible in source.

## Trust boundaries

1. Anonymous Internet to public backend routes: SOS, vessel profiles, mesh chat, trips, warning-delivery state, public forecasts/hotspots, login, setup-key signup, and vessel enrollment.
2. Vessel device to protected per-vessel routes: typed JWTs bind a registered device to one vessel and are checked against revocation on each request.
3. Operator browser to protected response and administration routes: signed user JWT plus role checks; operator tokens are not revalidated against mutable account state.
4. Phone to pod: unauthenticated cleartext HTTP/WebSocket on an open AP at a fixed address, by deliberate offline design.
5. LoRa peer to mesh: source identifiers and an eight-byte HMAC tag; current source uses one compiled development key for buoy and shore.
6. Shore gateway to backend: some telemetry routes use one shared API key, while SOS/chat/warning delivery are anonymous. The gateway can also hold broad operator credentials for downlink polling.
7. Backend to database: one source-visible `DATABASE_URL` is used for runtime queries and startup migrations; database-provider controls are external.
8. Source/dependency/build to shipped Docker image, APK, and firmware: several ecosystems, mutable resolution points, and a tracked APK. Actual signer, firmware provisioning, and deployment state are external facts.

## Source-visible security invariants

- Emergency availability permits anonymous SOS submission, but a caller must not self-grant responder-confirmed provenance or impersonate gateway transport.
- Vessel-device operations must derive vessel ownership from the validated token, not a caller-selected body/path identifier.
- Operator-only actions must be enforced server-side by current identity and role.
- Warning delivery states must be accepted only from the component authoritative for each transition.
- Public aggregated fishing activity must exclude identities, require explicit consent, and meet the documented minimum cohort.
- LoRa authenticity depends on secret, correctly scoped key material and replay/duplicate handling.
- A shore gateway must authenticate the backend TLS peer before sending incident or operator data.
- The pod's bounded persistent queue must preserve capacity for a real emergency despite unauthenticated nearby input.

## Selected companion guidance

The audit selected client-side, cloud/deployment, data isolation/lifecycle, desktop/mobile/local IPC, memory safety/binary, protocols/RPC/messaging, resource exhaustion/availability, supply chain/release, and web protocol/auth guidance. AI/LLM guidance was excluded because the repository contains conventional decision-support models but no LLM, prompt, agent, retrieval, or tool-execution trust boundary.

## Deployment-dependent facts requiring owner validation

Live reachability, proxy limits and security headers, Render blueprint use, actual secrets and rotation, database privileges/backups/networking, firmware-flashed keys and credentials, gateway network exposure, real radio range, APK signing/provenance, and physical device behavior were not inferred from source.
