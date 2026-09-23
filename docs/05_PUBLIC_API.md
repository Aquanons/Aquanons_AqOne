# 05 — Public API (REST + SSE)

The read/ack surface for the MDRRMO dashboard (Jade) and the mobile app's
status view (Jade, Doreen Kay). Implemented by the FastAPI backend (Lenard).

## Scope

- Live SOS feed over SSE.
- SOS list and acknowledge over REST.
- Delivery-state reporting.

Out of scope: ingest (`docs/04_INGEST_API.md`) and the radio hops.

## Transport

- HTTPS. Base URL is `https://aihackathon2026aquanonsaqone-production.up.railway.app`.
- Dashboard requests are authenticated by API key (`X-Api-Key`); the mobile
  app's safety feeds remain unauthenticated, but per-vessel normal-operation
  reads and writes now require a vessel-device bearer token issued by the
  backend. SOS ingest itself stays unauthenticated.
- JSON bodies; `charset=utf-8`.

## Vessel-device credential flow (Option A)

Routine per-vessel reads and writes are no longer authorized by a client-
supplied `vessel_id` alone. The backend now issues a revocable handset
credential that is bound to one vessel.

### `POST /api/vessel-auth/pairing-codes`

Operator-authenticated, device-admin roles only (`lgu` / `admin` — see
[Roles](#roles)). Issues a short-lived pairing code for one vessel. Body:

```json
{
  "vessel_id": "NW-001",
  "boat": "NW-001"
}
```

Response `200`:

```json
{
  "vessel_id": "NW-001",
  "pairing_code": "K7Q4M9PX",
  "expires_at": "2026-08-16T05:15:00Z"
}
```

Rules:

- The code is one-time use.
- The code expires after 15 minutes.
- A lost/replaced handset gets a new code; old devices are revoked.

### `POST /api/vessel-auth/enroll`

Consumes the one-time code and returns a vessel-device bearer token. Body:

```json
{
  "vessel_id": "NW-001",
  "pairing_code": "K7Q4M9PX",
  "device_label": "Jade's Android"
}
```

Response `200`:

```json
{
  "token": "eyJ...",
  "expires_at": "2026-08-17T05:00:00Z",
  "device": {
    "id": 12,
    "vessel_id": "NW-001",
    "label": "Jade's Android",
    "paired_at": "2026-08-16T05:00:00Z"
  }
}
```

Rules:

- Token lifetime is 24 hours.
- The token binds one device record to one vessel.
- The backend treats the token's vessel as authoritative. A body/path
  `vessel_id` may be checked for consistency, but never trusted as ownership.

### `POST /api/vessel-auth/refresh`

Requires the current vessel-device bearer token. Returns a fresh token for the
same device/vessel pair and the new expiry time.

### `POST /api/vessel-auth/devices/{device_id}/revoke`

Operator-authenticated, device-admin roles only (`lgu` / `admin` — see
[Roles](#roles)). Revokes a lost or replaced handset. Body:

```json
{
  "reason": "lost device"
}
```

Once revoked, the device token must no longer authorize any per-vessel read or
write. SOS ingest remains available without it.

## Operator authentication and sessions

Operator endpoints (the MDRRMO/LGU dashboard) authenticate using bearer tokens.

### `POST /api/login`

Accepts `email` and `password`.
Performs constant-timing password verification (evaluating bcrypt regardless of whether the email exists).
Returns a signed JWT bearer token with claims `sub`, `email`, `role`, and `ver` (current token version).

### `POST /api/logout`

Operator-authenticated (`require_user`).
Increments the operator's `token_version` in the database, instantly revoking all active tokens issued for this user.
The dashboard calls this endpoint best-effort on logout before clearing client storage.
Returns `200` with `{"message": "Logged out."}`.

### Session revocation rules

- The dependency `require_user` loads `id`, `email`, `role`, and `token_version` from `users` for the token `sub`.
- If the user no longer exists in the database, the request is rejected with HTTP 401.
- If the token's `role` claim does not match the stored user's role, the request is rejected with HTTP 401.
- If the token's `ver` claim does not match the stored `token_version` (or `ver` is missing), the request is rejected with HTTP 401.

## Endpoints

### `GET /healthz`

Liveness used by the platform and by demos. Returns `200`:

```json
{ "status": "ok" }
```

### `GET /api/v1/sos`

List SOS events, newest first.

| Query | Default | Meaning |
|---|---|---|
| `status` | `open` | `open` \| `acknowledged` \| `all` |
| `limit` | 50 | Max rows (≤ 200). |
| `vessel_id` | — | Filter to one vessel UUID. |

Response `200`:

```json
{
  "sos": [
    {
      "id": "evt_1234",
      "vessel_id": "8f7b2c41-...",
      "boat": "BG-123",
      "status": "open",
      "delivery_state": "delivered",
      "lat": 11.6050,
      "lon": 122.3125,
      "note": "engine down",
      "created_at": "2026-08-03T22:15:00Z",
      "acknowledged_at": null,
      "acked_by": null
    }
  ]
}
```

`delivery_state` is one of the four states (`docs/06_DELIVERY_STATES.md`); on
the dashboard it is always `delivered` or `acknowledged` — the radio hops
before the backend are out of its view.

### `POST /api/v1/sos/{id}/ack`

Acknowledge an SOS (MDRRMO action). Body:

```json
{
  "v": 1,
  "responder": "ranger-01"
}
```

`responder` is the operator id (free text, ≤ 32 chars). Returns `200`:

```json
{
  "id": "evt_1234",
  "status": "acknowledged",
  "acknowledged_at": "2026-08-03T22:20:00Z",
  "acked_by": "ranger-01"
}
```

The ack is persisted and idempotent — re-acking the same id returns the same
result (`acked_by` unchanged). A reload must show the ack (`docs/00_START_HERE.md`
definition of done).

### `GET /api/sos/active` — dashboard poll (what the dashboard actually uses)

Operator-authenticated (bearer token, `require_user`). The dashboard polls
this rather than the SSE feed below (`web/js/dashboard/dashboard-live-sos.js`).

Returns **every unresolved SOS event**, newest first - including one a
dispatcher has already acknowledged.
The feed is untruncated (no arbitrary row limit), guaranteeing that an influx of
simultaneous incidents cannot crowd genuine active calls out of the dispatcher view.
An acknowledged event stays in this feed
until a dispatcher calls `POST /api/sos/{id}/resolve` or the fisher replies
`SAFE_NOW` (`POST /api/sos/{id}/reply`, `docs/13_RESPONDER_LOOP.md`); dropping
it as soon as it is acknowledged - the previous behaviour - hid the fisher's
subsequent reply from the dispatcher.
Each row carries `acknowledged_at`,
`acked_by`, `eta_at`, `responder_status`, `responder_status_label`,
`responder_note`, `fisher_reply`, `fisher_replied_at`, `resolved_at`
(always `null` here, since a resolved row has left the feed), and `is_synthetic`
(boolean, `true` for scripted/demo scenario events and `false` for genuine distress
calls) alongside the fields `GET /api/v1/sos` documents above.
Each event also
carries the vessel's declared owner identity from `POST /api/vessel-profile`
below when one is on file: `skipper_name`, `license_type`, `license_number`
and `phone` (empty strings / `none` when the fleet has not registered that
vessel yet - never fabricated).
Clients must derive
display provenance (e.g. DEMO vs LIVE badges) from `is_synthetic` rather than
assuming every event returned by `/api/sos/active` is live, while keeping operational
acknowledgement and resolution actions available against real event IDs.

### `POST /api/vessel-profile` - declare a vessel's owner identity

Unauthenticated for initial registration, for the same reason SOS ingest is (`POST /api/sos`): a
fisherman at sea has no account to hold, and this is the same self-declared
identity as the distress call itself.
The read side - `GET /api/sos/active`
above - stays dispatcher-gated, so an unauthenticated write only ever
describes the one vessel its caller claims to be.

The handset (`mobile/lib/data/identity_store.dart` `toRegistrationPayload()`)
pushes this once when onboarding completes, again at startup for a remembered
skipper, and again on every profile edit (`mobile/lib/main.dart`, best-effort
and never blocking an SOS).
It is an idempotent upsert keyed on `vessel_id`, so
retries converge and the vessel may already exist as the skeleton an SOS made.

**Profile overwrite rule**: An unauthenticated request can create a new vessel profile
or populate blank/null fields on an existing skeleton.
However, modifying any existing non-blank identity field (`skipper_name`, `license_type`,
`license_number`, `phone`, `boat`) requires device authentication via a valid vessel-device
bearer token bound to that `vessel_id`.
If an unauthenticated caller attempts to overwrite non-blank identity fields, the server
rejects the request with `409 Conflict` and discards all changes.

```
POST /api/vessel-profile
{
  "vessel_id": "V001",                // 1..32 chars, the same id the SOS uses
  "boat": "NW-001",                   // 0..32 chars
  "skipper_name": "Juan Dela Cruz",   // 0..64 chars
  "license_type": "boatr",            // boatr | fishr | cfvgl | none
  "license_number": "NWB-2026-08412", // 0..24 chars
  "phone": "+639171234567"            // 0..20 chars
}
```

`trust_tier` is deliberately not accepted here: the trusted-status model
(`docs/16_QA_DISCLOSURES.md`) only lets a responder/verification path upgrade
a vessel, and an unauthenticated claim cannot confirm itself.
The SOS ingest
snapshots the tier on the incident itself, which is what the dashboard shows.
Length caps mirror the handset's own (`mobile/lib/core/config.dart`); anything
beyond them is rejected with 422 before any DB write.

```json
{
  "vessel_id": "V001",
  "boat": "NW-001",
  "skipper_name": "Juan Dela Cruz",
  "license_type": "boatr",
  "license_number": "NWB-2026-08412",
  "phone": "+639171234567",
  "profile_updated_at": "2026-08-03T22:20:00Z"
}
```

### `POST /api/sos/{id}/acknowledge` and `POST /api/sos/{id}/resolve`

Operator-authenticated, responder roles (`mdrrmo` / `lgu` / `admin` — see
[Roles](#roles)). `acknowledge` accepts `eta_minutes` (converted
server-side to an absolute `eta_at`, never trusting the browser's clock),
`responder_status` (the code table in `docs/13_RESPONDER_LOOP.md`) and an
optional `responder_note`. `resolve` marks the incident resolved, removing it
from `GET /api/sos/active` on the next poll, and accepts an optional
`reason` — persisted as distinct `resolved_by`/`resolved_reason` columns
(docs/41 Phase 3; previously `resolve` reused `acked_by`, conflating the
acknowledger with the resolver). Both are idempotent — re-calling either
after it already applied returns the same result rather than erroring;
`acknowledge` is additionally re-callable with a new `responder_status` to
report progress, which is a real transition each time, not a duplicate.

### `GET /api/v1/sos/stream` — SSE live feed

Server-Sent Events, `text/event-stream`. On connect the server sends the
current open SOS list as one snapshot event, then pushes every new event.

```
event: snapshot
data: {"sos": [ ...open SOS events... ]}

event: sos
data: {"event": "created", "sos": { ... }}

event: sos
data: {"event": "acknowledged", "sos": { ... }}
```

- Reconnect after network drop: client reconnects and receives a fresh
  snapshot; the snapshot is the source of truth, events are deltas.
- Event types: `created`, `acknowledged`. (`delivery_state` changes from the
  mesh are not pushed to the dashboard; see `docs/06_DELIVERY_STATES.md`.)

## Delivery-state reporting for the app

The phone learns nothing beyond its serving boat pod (`docs/03_PHONE_BUOY_WIFI.md`) unless
it has internet. If it does, it can reconcile its outbox:

### `GET /api/sos/ack/{local_id}`

The read-back that answers a **direct-path, un-enrolled handset**.

`POST /api/sos` sends a call with no credentials (`docs/05`'s trust note on
safety information under a distress call), but until this endpoint existed the
*answer* to that call was credential-gated: `GET /api/sos/vessel/{vessel_id}`
below requires a vessel-device token, and nothing in the app issues one (no
enrolment UI). A phone could call for help over plain internet but could never
learn the MDRRMO had answered. This endpoint mirrors the unauthenticated
ingest: the packet a handset sent without a credential must not be answered
only to handsets holding one.

- **No bearer token.** The lookup is keyed on `local_id`, the id the handset
  generated and sent with the SOS, which also keys the app's own outbox - so
  only the raising phone knows it.
- Returns **one incident's acknowledgement** (delivery state, `acked_by`,
  `eta_at`, `responder_status`, `responder_note`, `fisher_reply`,
  `resolved_at`, and the backend `id` the phone needs to post a reply).
- **404 until the id exists** on the backend, so a poll before then reads as
  "not yet acknowledged"; a `200` with `delivery_state: "delivered"` means the
  call reached the backend but no responder has answered yet.
- Reveals no coordinates, no note, and no other vessel's rows.

```json
{
  "vessel_id": "6b59...1",
  "server_time": "2026-09-15T12:00:00+00:00",
  "event": {
    "id": 4,
    "local_id": "1789406852548-9a5f31da",
    "delivery_state": "acknowledged",
    "eta_at": "2026-09-15T12:20:00+00:00",
    "responder_status": 2,
    "responder_status_label": "Rescue boat on the way",
    "responder_note": "On the way"
  }
}
```

The app polls this per outstanding direct-path record during `reconcile()` in
place of the credentialed vessel feed when it has no device credential
(`mobile/lib/services/sos_service.dart`).

### `GET /api/sos/vessel/{vessel_id}`

Returns that vessel's SOS rows, newest first. The app matches by
`(local_id, seq)` to mark a message `acknowledged` when an MDRRMO responder
has acked it.

Requires a vessel-device bearer token. The token's vessel must match the path
vessel id; the backend queries by the verified token vessel, not by trusting
the path as ownership.

### `POST /api/sos/{event_id}/reply`

The fisher's reply to a responder acknowledgement.

```json
{
  "reply": 1
}
```

- `1` = still in danger
- `2` = safe now

Requires a vessel-device bearer token. The backend updates the event only when
it belongs to that token's vessel.

### `POST /api/sos/reply/{local_id}`

The same fisher reply, keyed on `local_id` instead of a device token — the
mirror of `GET /api/sos/ack/{local_id}`'s trust model. An un-enrolled handset
cannot obtain a vessel-device token (there is no enrolment UI), yet it can
still raise an SOS and must still be able to answer an acknowledgement; the
high-entropy `local_id` only that phone generated and sent with the SOS is a
sufficient scope key, exactly as it is for the ack read-back.

```json
{
  "reply": 2
}
```

- `1` = still in danger
- `2` = safe now (also resolves the incident)

204/404 semantics match the credentialed variant: the event is updated once,
retries are safe, and a `SAFE_NOW` reply freezes the reply fields.

### `POST /api/catch-logs`

Creates or deduplicates one catch log upload from the handset.

Requires a vessel-device bearer token. The backend derives the owning vessel
from the token and rejects a mismatched body `vessel_id`.

### `POST /api/catch-logs/{catch_log_id}/confirm-weight`

Confirms the real reweighed catch figure.

Requires a vessel-device bearer token. The backend updates the row only when it
belongs to that token's vessel.

## Nearby-boat group chat — **implemented**

### `POST /api/mesh/chat`

Relays one chat line from a handset (via the Heltec WiFi hub, or straight
from the phone when it has internet) into the durable store the MDRRMO
dashboard and other handsets read from. Unauthenticated — fishermen have no
account, and neither does the hub.

This is **nearby-boat group messaging**, not private or family messaging.
`sender`, `text`, and `origin` are public group-chat metadata delivered to
every listener of this endpoint; there is no recipient field, no consent
model, and no private downlink. Do not build or document a "message to
family" feature on top of this contract — that needs a new one.

Body:

```json
{ "sender": "Maria Gracia", "text": "heading back, engine trouble", "origin": "app" }
```

| Field | Limit | Notes |
|---|---|---|
| `sender` | 1–64 chars | Self-declared boat/skipper name, not verified. |
| `text` | 1–256 chars | Backend/hub-origin ceiling. The handset's own compose box enforces a tighter 50-character limit before a line is ever sent — see `ChatService.maxMessageLength` in `mobile/lib/ui/chathubb.dart`. |
| `origin` | ≤16 chars, default `app` | Which leg the message arrived on (`app` or `hub`); lets the hub avoid rebroadcasting its own uplink back to the boats that just sent it. |

Returns **`201` only once the row is committed** — this is the one fact a
handset may treat as "cloud relay stored". A timeout, a non-`201` status, or
no internet at all means the backend's state is simply unknown; the handset
must not infer cloud delivery from network reachability alone, and must keep
the line queued for retry rather than drop it.

### `GET /api/mesh/chat?since_id=`

Returns ordered nearby-group messages, unauthenticated. `since_id` (default
`0`) returns messages with `id > since_id` in ascending order — "the next N
after since_id" — so a hub or handset that was offline catches up in order
instead of skipping a gap. Omitting `since_id` returns the most recent
`limit` messages (default 50, max 200), oldest first.

```json
{
  "messages": [
    {
      "id": 42,
      "sender": "Maria Gracia",
      "text": "heading back, engine trouble",
      "origin": "app",
      "created_at": "2026-08-16T04:00:00Z"
    }
  ]
}
```

No cross-hop de-duplication is applied server-side or on the handset. The
buoy firmware does not forward a stable message ID, so at-least-once
delivery (a line possibly appearing twice across hub broadcast and cloud
relay) is a known, accepted limitation, not a bug to mask with a text/time
heuristic that could hide a real repeated distress call.

## Official advisories — **implemented**

### `GET /api/public/advisories`

Published, currently-active advisories only, unauthenticated. "Active" means
`status = Published` **and** the advisory has started (`publish_date <=
today`) **and** has not expired (`expiration_date` is null or `>= today`) —
filtered server-side, not left to the handset's own client-side check.

```json
{
  "advisories": [
    {
      "id": 42,
      "title": "Not advised to go out",
      "category": "Weather Advisory",
      "description": "Habagat surge expected through Thursday.",
      "municipality": "New Washington",
      "priority": "Warning",
      "publish_date": "2026-08-14",
      "expiration_date": "2026-08-16",
      "image_url": "https://.../pier.jpg",
      "status": "Published",
      "source": "LGU",
      "created_at": "2026-08-14T04:00:00Z",
      "updated_at": "2026-08-14T04:00:00Z"
    }
  ]
}
```

Field notes:

- `image_url` is the one public field name for the advisory's photo. The
  operator-facing create/update body still accepts `cover_image` (see
  below) — the backend stores it under that column and always serialises it
  back out as `image_url`. A handset must not need to read both names.
- `publish_date`/`expiration_date` are ISO `YYYY-MM-DD`; `expiration_date` is
  `""` when the advisory does not expire.
- `priority` is one of `Emergency` \| `Warning` \| `Information` \| `Community`.
- `source` identifies the issuer (`LGU` by default). This is a human-authored
  official notice — it is never AqOne's own copy; compare
  `data/welcome_advisory.dart` on the handset, which is marked unofficial and
  never comes from this endpoint.

### `GET /api/advisories`, `POST /api/advisories`, `PUT /api/advisories/{id}`, `DELETE /api/advisories/{id}`

Operator-authenticated, responder roles (`mdrrmo` / `lgu` / `admin` — see
[Roles](#roles)), via `require_roles`. The list read here is **not**
filtered by active/expired — an operator managing
notices needs to see and edit drafts and past advisories too; only the
public route above filters. Create/update accept `cover_image` as the
write-side field name; the response echoes it back as `image_url` like every
other advisory read.

### `GET /api/advisories/{id}/deliveries` - warning delivery tracking

Operator-authenticated (`require_user`).
Returns the chronological hop-by-hop delivery records and reached states for the specified advisory.
Anonymous callers receive HTTP 401.

## Sea condition — **implemented**

### `GET /api/sea-condition`, `GET /api/sea-condition/history`

Operator-authenticated (`require_user`); read-only. Returns the current
declared status plus buoy telemetry, or a bounded history.

### `POST /api/sea-condition`

Operator-authenticated, responder roles (`mdrrmo` / `lgu` / `admin` - see
[Roles](#roles)). Declares the current sea condition (`status`, `reason`).
The stored `set_by_user_id`/`set_by_name` are always derived from the
authenticated token server-side - the request body cannot set or override
them; a body containing those fields is silently ignored.

### `GET /api/public/sea-condition`

Unauthenticated endpoint consumed by mobile handsets.
Returns the current sea condition status, reason, and buoy telemetry.
To protect operator privacy, user accounts are never disclosed to anonymous clients.
The response returns `set_by_label` (`users.full_name` when set, otherwise `"MDRRMO"`).
The fields `set_by_user_id` and `set_by_name` are excluded from the public response.

## Squall nowcast — **implemented**

### `GET /api/public/squall`

Squall alarm state for the handset, unauthenticated, live pressure
telemetry only (`docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md` Phase
3). The protected dashboard route (`GET /api/ai/squall/current`) shares
this exact response shape, and a demo-only `GET /api/demo/squall`
(gateway-key-free, `X-Demo-Key`-gated) carries the identical shape with
`source: "synthetic"` for presenter use — the synthetic scenario never
reaches either production route.

`level` is one of:

- `unknown` — telemetry is missing, stale, invalid, or an insufficiently
  distributed array; never downgraded to `clear`.
- `clear` — a fresh, quality-passing live array with no detection.
- `watch` — an eligible model candidate. Visible everywhere, never sounds
  a handset alarm (`return_now` is the only alarming state).
- `return_now` — the RETURN NOW alarm condition. For `source: "live"` this
  requires the `SQUALL_RETURN_NOW_ENABLED` deployment flag to be enabled
  (default off, `backend/.env.example`), which itself requires a completed
  field-validation log (template: `docs/08_DEMO_AND_STATUS.md` "Squall
  field-validation log") reviewed and signed off by a named MDRRMO approver
  (Phase 4's release gate); until both exist, a live detection that crosses
  the model's threshold reports `watch` instead. `source: "synthetic"` has
  no such restriction, since only the demo route ever reports it.

Before any detection runs, the response is quality-gated
(`assess_array_quality()`, Phase 2): a missing, stale (>10 minutes old),
too-few-buoy (<3), or geometrically degenerate array reports `unknown`
with `status_reason` explaining why and `observed_at` set to the last real
reading this backend has ever seen — never a fabricated calm baseline.

```json
{
  "source": "live",
  "calibration": "synthetic",
  "observed_at": null,
  "generated_at": "2026-08-29T02:00:00Z",
  "data_age_seconds": null,
  "status_reason": "only 0 of 3 required buoys have fresh (<= 10min old), gap-free, in-range readings",
  "level": "unknown",
  "return_now": false,
  "detections": [],
  "threshold": null,
  "triggered_buoys": [],
  "lead_minutes": null
}
```

| Field | Notes |
|---|---|
| `source` | `"live"` or `"synthetic"` — which table this response was computed from. Never mixed. |
| `calibration` | Always `"synthetic"` today: the *model* is trained on simulated pressure fields regardless of the input's `source`. Not a PAGASA warning — the handset must keep saying so. |
| `observed_at` | The newest real pressure reading this backend has seen, across every buoy, whether or not the array currently qualifies. `null` only when there has never been any reading at all. |
| `generated_at` | Server clock time this response was computed — always present, used to derive `data_age_seconds` rather than trusting a client clock. |
| `data_age_seconds` | `generated_at - observed_at`, or `null` if `observed_at` is `null`. |
| `status_reason` | Why `level` is `"unknown"` (or why the model didn't run). `null` whenever `level` is `clear`/`watch`/`return_now` — a successful evaluation needs no explanation. |
| `level` / `return_now` | See above. `return_now` is redundant with `level == "return_now"`, kept for a client-side cross-check. |
| `detections`, `threshold`, `triggered_buoys`, `lead_minutes` | Only populated once quality passes; empty/`null` otherwise. |

`calibration: "synthetic"` is carried on every response while the model is
trained on simulated pressure fields rather than observed squalls - this is
not a PAGASA warning, and the handset must keep saying so.

### `POST /api/ai/squall/train`

Restricted to administrator operators (`require_admin_role`).
Additionally requires the server-side deployment flag `ALLOW_TRAINING=true`.
Non-admin operators (`mdrrmo`, `lgu`) receive HTTP 403 even when training is enabled.
Re-trains the squall detector model from stored synthetic readings and squall events, then persists the resulting artifact.
An empty dataset returns HTTP 400.

## Daily and hourly forecast for the app — **implemented as a transparent proxy**

### `GET /api/public/forecast`

The seven-day daily outlook behind Home's forecast strip and the hourly forecast coverage behind the fishing weather window.

**Stakeholder Coordination (Phase 1 contract update):**
- **Affected Owners:** Lenard (backend / proxy implementation), Arnold (integration & gateway), Jade / Doreen Kay (mobile UI & forecast window consumer).
- **Scope of Change:** Purely additive. Exposes hourly atmospheric and marine conditions alongside existing daily outlooks, with explicit units, timezone metadata, and sampling provenance. Existing clients consuming only `days` continue to work without modification.

**No server-side fusion model exists yet.** What is implemented today is a
transparent Open-Meteo weather and marine proxy: the backend fetches both
atmospheric and marine endpoints, applies an upstream timeout (5.0s), aligns
hourly and daily records, and returns them in this shape. `source` is
`"open-meteo"`, not `"aqone-fusion"`, and the daily `risk` block below
remains omitted until server-side fusion is built — the handset scores risk
itself, exactly as if this endpoint had 404'd
(`mobile/lib/services/forecast_provider.dart`'s `AqOneForecastProvider`
already implements this precedence and its Open-Meteo fallback).

| Query | Default | Meaning |
|---|---|---|
| `lat` | — | Position to forecast for. Required, `-90..90`. |
| `lon` | — | Position to forecast for. Required, `-180..180`. |
| `days` | 7 | Days requested, `1..7`. Maximum 7 days. |

An out-of-range `lat`/`lon`/`days`, or an upstream provider timeout/error,
returns `422`/`502` respectively — never a `200` with an empty or invented
forecast. A `502` here is what lets the handset's own fallback take over on
its next attempt.

Response `200`:

```json
{
  "source": "open-meteo",
  "generated_at": "2026-08-16T04:00:00Z",
  "latitude": 11.68,
  "longitude": 122.41,
  "timezone": "Asia/Manila",
  "timezone_abbreviation": "PST",
  "utc_offset_seconds": 28800,
  "units": {
    "time": "iso8601",
    "temperature": "celsius",
    "wind_speed": "km/h",
    "wind_gusts": "km/h",
    "precipitation": "mm",
    "wave_height": "m"
  },
  "days": [
    {
      "date": "2026-08-16",
      "weather_code": 95,
      "temp_max": 31.2,
      "temp_min": 25.8,
      "wind_kph": 24.0,
      "gust_kph": 41.0,
      "precip_mm": 18.4,
      "wave_m": 2.1
    }
  ],
  "hours": [
    {
      "time": "2026-08-16T00:00",
      "weather_code": 95,
      "temp_c": 26.5,
      "wind_kph": 22.0,
      "gust_kph": 38.0,
      "precip_mm": 2.1,
      "wave_m": 1.8
    }
  ]
}
```

A future fusion model would additionally attach a `risk` block per day:

```json
      "risk": {
        "level": "danger",
        "score": 0.81,
        "reason": "Gusts 41 km/h, 2.1 m swell at Buoy B",
        "inputs": ["buoy:buoy-b", "open-meteo"]
      }
```

#### Hourly Schema and Interval Semantics

- **`hours` Array**: An ordered sequence of hourly forecast intervals covering the requested horizon (up to `days * 24` hours). If upstream hourly atmospheric data is unavailable or malformed, `hours` may be omitted or empty while preserving `days`.
- **`time`**: ISO local date-time string (`"YYYY-MM-DDTHH:MM"`) in the forecast's declared local timezone (`timezone`).
- **Interval Semantics & Timing**:
  - `gust_kph`: Open-Meteo's `wind_gusts_10m` records the maximum wind gust during the **preceding 1-hour interval** ending at `time` (i.e. `[time - 1h, time]`).
  - `precip_mm`: Cumulative precipitation over the preceding 1-hour interval ending at `time`.
  - `wave_m`: Instantaneous significant wave height sampled at `time`. Nullable (see Missing Data below).
  - `wind_kph`: Instantaneous / 10m wind speed at `time`.
  - `temp_c`: Temperature in degrees Celsius at `time`.
  - `weather_code`: WMO 4677 weather code describing conditions for the interval.
- **Risk Alignment Rule**: When calculating deterioration or window intervals, because a gust reported at `T + 1h` occurred between `T` and `T + 1h`, any threshold crossing at `T + 1h` indicates adverse conditions during that hour. Downstream window logic aligns by actual timestamps and treats the earliest affected boundary conservatively; gust hazards must never be shifted one hour later or indexed blindly.

#### Timezones and Provenance

- **`timezone` & `utc_offset_seconds`**: Open-Meteo resolves timezone automatically from coordinates (`timezone=auto`). The daily calendar day partition uses this local timezone (`Asia/Manila` in Panay/Aklan), ensuring daily dates remain consistent with local day boundaries.
- **`generated_at`**: ISO 8601 UTC timestamp of response generation by the backend. It indicates backend query time, **not** upstream weather model issuance time.
- **`latitude` / `longitude`**: Echo the coordinate position of the weather forecast.

#### Missing-Data & Degradation Rules

- **`wave_m` is Nullable**: Nearshore coastal cells often lack wave model coverage in Open-Meteo Marine. When marine data is missing for a given hour or day, `wave_m` is `null`. It is **never** sent as `0.0` (which would falsely indicate flat calm and dangerously paint high-risk days green).
- **Marine Failure Degradation**: If the marine API fails (HTTP error, timeout, or empty response), the forecast returns HTTP 200 with all `wave_m` set to `null`, preserving atmospheric forecast data.
- **Atmospheric Failure**: If the primary atmospheric API fails or times out, the endpoint raises HTTP 502 (`detail: "upstream weather provider unavailable"`), triggering client-side fallback.
- **No Index Joining**: Atmospheric and marine hourly series must be joined strictly by matching `time` timestamps. If an hourly marine sample is missing for an atmospheric hour, `wave_m` for that hour is `null`.
- **Validation**: Non-finite (`NaN`, `inf`), negative speeds/heights/precip, or corrupted values are sanitized to `null` or excluded; never coerced to calm/zero.

Field notes, all of them load-bearing:

- `weather_code` is **WMO 4677**, the same vocabulary Open-Meteo uses, so one
  icon mapping on the handset serves every provider.
- `wave_m` is significant wave height in metres, and is **nullable**. Null
  means unknown. It must never be sent as `0.0` to mean "we didn't measure" —
  that reads as flat calm and paints a dangerous day green.
- `risk` is **optional**. Omit it (or send `null`) and the handset scores the
  day itself and labels the verdict as device-derived. This is what lets the
  backend serve weather before the fusion model is ready.
- `risk.level` is one of `safe` \| `caution` \| `danger` \| `unknown`.
- `risk.inputs` is how the app knows whether sea state was considered. An
  entry starting `buoy:` or the literal `wave` counts as sea state; without
  one, the card tells the user the verdict came from wind and rain only.
- `risk.score` is 0–1, most dangerous at 1. Advisory, for future tuning — the
  UI buckets on `level`.

Parsing and every one of these rules is pinned by
`mobile/test/daily_outlook_test.dart`.

## Catch-activity heatmap — **implemented**

### `GET /api/public/hotspots`

The server-side recent catch-activity surface (§6.2), built only from catch
logs whose owner explicitly opted in. This first operational version scores
coarse cells from recent independent reporters and observation density. It is
not an environmental prediction or a guarantee of catching fish.

Response `200`:

```json
{
  "generated_at": "2026-08-16T02:00:00Z",
  "model_version": "catch-density-v1",
  "min_reporters": 3,
  "cells": [
    {
      "center_lat": 11.72,
      "center_lon": 122.36,
      "cell_size_degrees": 0.05,
      "score": 0.82,
      "observations": 34
    }
  ]
}
```

Rules the shape enforces, all of them deliberate:

- **Cells, never points.** §6.2 requires binning that protects an
  individual's exact productive location. There is no field in which a
  precise coordinate could be expressed, so the privacy property belongs to
  the contract rather than to whatever renders it.
- `score` is relative recent activity 0–1, **not** a probability of catching
  anything. §6.2 forbids implying guaranteed catch, and the client renders it
  as opacity of a single hue — never a red-to-green ramp, which reads as a
  safety verdict.
- `observations` and `min_reporters` are shown in the map legend. §6.3's
  minimum-reporter rule stops one prolific fisher becoming "the model", and a
  cell resting on two reports must not look like one resting on two hundred.
- `generated_at` drives a visible staleness label, per §3.4.
- Cells should be withheld server-side when they fall below the reporter
  threshold. The client cannot tell a withheld cell from an empty sea, which
  is the intended asymmetry.

Parsing is pinned by `mobile/test/hotspot_cell_test.dart`.

### `POST /api/spots` — **removed**

Manual pin-drop fishing spots pipeline has been removed from backend and handset.
It published exact coordinates, attributed to a vessel, with no consent gate - the direct
opposite of §6.2's binning requirement and §6.1's separate opt-in. Aggregated catch-activity
heatmap is served through `/api/public/hotspots`. Historical database migration 013 is preserved.

### PAGASA

When a data-sharing agreement exists, PAGASA replaces the **atmospheric half
only**. Their TenDay API is keyed by municipality rather than coordinates and
carries no sea state, so wave height keeps coming from the marine model or
from our own buoys. The call should live behind this endpoint rather than in
the handset, so attribution and rate terms are honoured in one place and no
credential ships on a phone.

## Trip-anomaly review queue — **implemented**

The responder-facing side of `docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`.
A case here is a review candidate produced by confidence-scored trip
evaluation (`docs/04_INGEST_API.md` "Contact events" is its only trustworthy
input) — **never an SOS, and never an automatic dispatch.** All routes are
operator-authenticated (`require_user`); a public or handset caller cannot
read or mutate this queue. The four case-mutating routes below
(`acknowledge`/`dismiss`/`escalate`/`resolve`) additionally require a
responder role (`mdrrmo` / `lgu` / `admin` — see [Roles](#roles)).

### `GET /api/ai/anomaly/active`

Read-only. Never triggers evaluation or writes — dashboard polling cannot
rebuild the underlying tables. Each row carries `source` (`live` \|
`synthetic`), `evaluated_at`, and `data_age_seconds` alongside the score, so
the dashboard can say plainly how current a result is.

### `GET /api/ai/anomaly/cases/open`

The persistent "Trip checks" queue: every unresolved case, newest first.
Read-only, same guarantee as `GET /active`. Response `200`:

```json
[
  {
    "id": 42,
    "vessel_id": "NW-001",
    "trip_id": "trip-2026-08-29-01",
    "case_type": "responder_attention",
    "score": 0.82,
    "status": "alert",
    "reasons": [{"code": "overdue", "weight": 0.85, "contribution": 0.78, "description": "Late beyond the expected-contact window."}],
    "source": "live",
    "score_evaluated_at": "2026-08-29T05:10:00Z",
    "last_contact_at": "2026-08-29T02:00:00Z",
    "data_age_seconds": 11400,
    "is_synthetic": false,
    "created_at": "2026-08-29T05:10:00Z",
    "updated_at": "2026-08-29T09:10:00Z",
    "acknowledged_at": null,
    "acknowledged_by": null,
    "dismissed_at": null,
    "dismissed_by": null,
    "dismissed_reason": null,
    "escalated_at": null,
    "escalated_by": null,
    "escalated_reason": null,
    "resolved_at": null,
    "resolved_by": null
  }
]
```

`case_type` is `verification` for a low-confidence (cold-start) vessel
profile, or `responder_attention` for a high-confidence one — never a
severity label. A case is created or refreshed only while its underlying
trip still scores non-`normal`; a periodic re-evaluation updates `score`,
`status`, `reasons` and the two timestamps but never touches the
acknowledged/dismissed/escalated/resolved columns, so a responder's decision
survives every later refresh.

### `POST /api/ai/anomaly/cases/{id}/acknowledge`

Marks the case seen. Idempotent — a retry keeps the first `acknowledged_by`
and `acknowledged_at`. No body required.

### `POST /api/ai/anomaly/cases/{id}/dismiss`

Marks the case a false or expected positive. Requires a short reason:

```json
{ "reason": "known route deviation, confirmed safe by radio" }
```

Idempotent — a retry keeps the original `dismissed_reason` rather than
overwriting it.

### `POST /api/ai/anomaly/cases/{id}/escalate`

Hands the case to real-world handling — a human decision; this call never
dispatches anything itself. Same `{ "reason": "..." }` body and idempotency
as dismiss.

### `POST /api/ai/anomaly/cases/{id}/resolve`

Closes the case; it drops out of `GET /cases/open` on the next poll.
Idempotent, no body required. Because evaluation never writes `resolved_at`,
a later score refresh can never reopen a case a responder closed.

## Drift prediction and search re-tasking — **implemented (Phases 1-3: case lifecycle, quality-gated runs, search re-tasking)**

The responder-facing side of
`docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md`. A case
here is a drift/search effort opened for one specific vessel, reusing the
existing `incidents` table (prior/posterior grid, `search_sectors`) rather
than a second incident system.

**Non-goals — this API never does any of the following:** open a case on its
own initiative, dispatch or assign an asset, plot a navigation route, declare
a person found, or replace SAR command judgement. Every write here is a
human responder's action; every read is decision *support*.

**Protected source only.** A case can be opened only from a source the
responder has already confirmed:

- a Manual SOS event (`docs/36_MANUAL_SOS_RESPONDER_LOOP_IMPLEMENTATION_PLAN.md`)
  that a dispatcher has **acknowledged** (`POST /api/sos/{id}/acknowledge`)
  and that is not yet resolved; or
- an automatic-distress anomaly case (`docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md`)
  that a responder has **escalated** (`POST /api/ai/anomaly/cases/{id}/escalate`)
  and that is not yet resolved.

A new anomaly score, an arbitrary client-supplied position, or a public
caller can never open a case. All routes below require a bearer token
(`require_user`); there is no unauthenticated drift endpoint. The
case-mutating routes (open/rerun/resolve/cancel a case, report a searched
sector) additionally require a responder role (`mdrrmo` / `lgu` / `admin` —
see [Roles](#roles)).

### Production environmental-input quality policy (Phase 2)

A real case's drift run may only use observed currents and a non-degraded
wind source — never the synthetic current equation or the simulator's
`true_*` columns. When the inputs don't clear the bar below, the run is
persisted as `insufficient_environmental_data` (with the diagnostic snapshot
that follows) instead of a contour.

Approved by the project owner (Lenard — see `AGENTS.md` Ownership) on
2026-08-30. These are safety thresholds: do not change them to make a demo
or a specific case work — that changes which real cases get a search field.
Re-approval is required before adjusting any of them.

| Policy | Value | Rationale |
|---|---|---|
| Minimum field geometry | ≥ 2 distinct buoys with a fresh reading within range of the last-known position | One buoy gives a point value, not a spatial gradient — two is the minimum to interpolate a direction. |
| Maximum current-observation age | 60 minutes | Matches the pre-existing interpolation cutoff (`current_field.MAX_AGE_SECONDS`) rather than adding a second, looser number. |
| Maximum wind-forecast age | 60 minutes | Structurally enforced tighter already: the wind cache TTL is 20 minutes, so a non-degraded fetch is always well under this. A *degraded* fetch (Open-Meteo unreachable, synthetic wind substituted) is rejected outright regardless of age. |
| Minimum observed-current coverage | ≥ 50% of the particle field driven by real observations, not the synthetic fallback | A zero (or near-zero) observation fraction is not sufficient evidence for a production search map (docs/40 "Current findings"). |

With no buoys deployed yet, every real case today is `insufficient_field_geometry`
until the buoy/current hardware is in the water — this is the honest, intended
state, not a bug (docs/40 "Purpose and delivery rule").

### `POST /api/ai/drift/cases` — open a case

```json
{ "source_type": "sos", "source_id": 42, "object_class": "person_in_water", "forecast_hours": 24 }
```

`source_type` is `"sos"` or `"anomaly"`; `object_class` is one of
`person_in_water`, `swamped_banca`, `intact_hull_adrift` and is always an
explicit responder choice — it is never inferred from the source's own
reason text. `forecast_hours` defaults to 24 (max 72). The last-known
position and time come from the source itself (the SOS's own lat/lon, or the
vessel's most recent position fix for an escalated anomaly) — the caller
cannot supply an arbitrary position.

Fails with `404` if the source doesn't exist, `409` if the source is not yet
confirmed (not acknowledged / not escalated), already resolved, or already
has a case open (one case per source — a retry does not fork a second search
effort), and `422` if the source has no recorded position yet.

Opening a case immediately computes and persists **run 1** against the
quality policy above — this is the only time a real case's prediction is
computed except for an explicit rerun (below). Response `200`:

```json
{ "id": 101, "vessel_id": "NW-001", "object_class": "person_in_water", "case_state": "confirmed", "source_type": "sos", "run_number": 1, "environmental_status": "ok", "insufficiency_reason": null }
```

### `GET /api/ai/drift/incidents`

Every case, newest last-contact first — real and demo/synthetic alike, each
labelled. `case_state` is `confirmed`, `resolved`, or `cancelled`.

### `GET /api/ai/drift/incident/{id}`

Reads the **stored** current run — it never recomputes on a `GET`, so a
displayed prediction and its posterior always belong to the same
environmental inputs. Response shape for a real case:

```json
{
  "incident": { "id": 101, "vessel_id": "NW-001", "case_state": "confirmed", "source_type": "sos", "is_synthetic": false, "...": "..." },
  "run_number": 1,
  "model_version": "aqone-drift-v1",
  "computed_at": "2026-08-30T05:10:00Z",
  "environmental_status": "ok",
  "insufficiency_reason": null,
  "nearby_buoy_count": 3,
  "observation_fraction": 0.71,
  "prediction": { "object_class": "person_in_water", "wind_source": "open-meteo", "degraded": false },
  "posterior_grid": { "...": "DensityGrid" },
  "contours": [ "...": "50/75/95% GeoJSON polygons" ],
  "next_area": { "label": "recommendation for responder review", "bounds": { "...": "..." }, "centroid": { "...": "..." }, "remaining_mass": 0.71 },
  "search_sectors": [ "..." ]
}
```

When `environmental_status` is `insufficient_environmental_data`,
`prediction`/`posterior_grid` are `null` and `contours` is `[]` — never a
contour inferred from the synthetic fallback. **`ground_truth_track` is
present only when the incident is synthetic** — a real case's response never
contains a ground-truth field at all (not even `null`). A synthetic replay's
ground truth is otherwise only available from the demo-gated route below.

A legacy/demo-fixture incident (created by the simulator or the demo
scenario engine, never by `POST /cases`) has no stored run and keeps the
pre-Phase-2 behaviour: `prediction` is a live-recomputed `DriftResult`, not a
stored run snapshot.

### `POST /api/ai/drift/cases/{id}/rerun` — explicit new drift run (Phase 2)

The only way a case's prediction is ever recomputed after it opens — always
a deliberate responder action, never automatic. Appends **run *N*+1**; the
previous run and every search sector already recorded against the case are
left untouched, so a crew already acting on the current contours is never
silently redirected mid-search. Fails `409` if the case is resolved/
cancelled, or has no run yet (a demo/synthetic case has none — `rerun` only
applies to a real case). Response shape matches `POST /cases`' tail:

```json
{ "id": 101, "run_number": 2, "environmental_status": "ok", "insufficiency_reason": null }
```

### `POST /api/ai/drift/incident/{id}/searched` — report a searched sector (Phase 3)

Real cases only — a case with no drift run (demo/synthetic, or a case that
predates Phase 2) cannot report through this route. The responder specifies the
geodetic footprint (`south`, `west`, `north`, `east`) and optional search occurrence
timing (`searched_at` or `search_start_at`/`search_end_at`):

```json
{
  "run_number": 1,
  "south": 11.65,
  "west": 122.30,
  "north": 11.68,
  "east": 122.34,
  "method": "moderate",
  "searched_at": "2026-08-29T10:00:00Z",
  "search_start_at": null,
  "search_end_at": null,
  "detection_probability": null,
  "dependent": false,
  "idempotency_key": "b1e2c3-...",
  "notes": "surface pattern, calm seas"
}
```

`run_number` is whatever the client last saw from `GET /incident/{id}` — a
report against a run that has since been superseded by a rerun is rejected.
`method` is one of the responder-approved detection-probability presets
(docs/05 table below) or an operational label; optional explicit `detection_probability`
is accepted for illustrative testing or calibrated instruments (0.0 to 1.0).
`searched_at` or `search_start_at`/`search_end_at` specify the search occurrence
time; if omitted or outside the modeled trajectory interval, the report is recorded
as unassimilated (`is_unassimilated: true`) rather than substituted with the latest step.
`dependent` indicates correlated repeat sweeps and discounts effective probability.
`idempotency_key` is client-generated (e.g. a UUID); a retry with the same key
against the same case is a no-op, returning the current state (`"duplicate": true`)
rather than applying the negative evidence twice. `notes` is optional, ≤ 280 characters.

**Detection-method presets** — policy approximations for responder review:

| `method` | Probability | Meaning |
|---|---|---|
| `poor` | 0.3 | Poor visibility / air search only |
| `moderate` | 0.6 | Daylight surface vessel search |
| `good` | 0.9 | Good conditions, multi-asset close pattern |

No preset reaches 1.0 — a search is never perfect.

Atomic: locks the case and its current run, rejects a stale/superseded run,
deduplicates the idempotency key, applies the time-aligned trajectory update,
saves the new posterior and trajectory weights, and appends the audit record
(`reported_by`, `method`, `notes`, `idempotency_key`, `searched_at`) — all in one transaction.
Rejects with `409` if the case is `resolved`/`cancelled`, the run is stale, the
current run is `insufficient_environmental_data` (no field to search), or the
run lacks trajectory state, and `422` for a reversed/degenerate rectangle or invalid probability.
Response `200`:

```json
{
  "posterior_grid": { "...": "updated DensityGrid" },
  "contours": [ "...": "50/75/95% GeoJSON polygons" ],
  "next_area": {
    "label": "recommendation for responder review",
    "bounds": { "south": 11.66, "west": 122.31, "north": 11.665, "east": 122.315 },
    "centroid": { "lat": 11.6625, "lon": 122.3125 },
    "remaining_mass": 0.34
  },
  "search_sectors": [ "..." ],
  "duplicate": false
}
```

`next_area` is the single highest remaining-mass grid cell — **a
recommendation for responder review, never an asset assignment, route, or
automatic re-tasking.** It never plots a course or names a crew.

### `POST /api/ai/drift/cases/{id}/resolve`

Closes the case (the search effort itself, independent of the source SOS/
anomaly's own state). Idempotent, no body required.

### `POST /api/ai/drift/cases/{id}/cancel`

```json
{ "reason": "false alarm, vessel found at dock" }
```

Idempotent — a retry keeps the original `cancelled_reason`.

### `GET /api/demo/drift/incident/{id}` — demo-only, ground truth

Returns `{ "ground_truth_track": [...] }` for a synthetic replay incident.
Gated by `DEMO_MODE` (the route is only mounted when it is set) plus
`X-Demo-Key`, and additionally `404`s on any incident that isn't synthetic —
a demo key alone can never unlock a real case's data.

## Operations audit — **implemented**

docs/41 Phase 2 wired one append-only `operations_audit_events` ledger into
every high-impact write above. Phase 3 exposes it through two read paths;
neither ever returns a raw domain row, only the redacted columns
(`id, occurred_at, actor_*, action, resource_type, resource_id, outcome,
correlation_key, is_demo, metadata`).

### `GET /api/ops/cases/{resource_type}/{resource_id}/timeline`

Operator-authenticated, responder roles (`mdrrmo` / `lgu` / `admin` — see
[Roles](#roles)). `resource_type` is one of `sos_event`, `anomaly_case`,
`drift_incident`; anything else is `422`. Returns up to 200 events for
that one case, newest first — never a bulk cross-case listing. Recording
the view itself is deduplicated: at most one `ops.case_view` access event
per actor/case per rolling 15 minutes, so re-polling or re-opening the
same case tab doesn't turn into an event storm.

### `GET /api/ops/audit` and `GET /api/ops/audit/export`

Administrator-only (`admin` — **not** `lgu`; see [Roles](#roles)). Filters:
`actor_email`, `action`, `resource_type`, `resource_id`,
`date_from`/`date_to` (bounded to a 90-day span, defaults to the last 7
days if both are omitted). `/audit` is opaque-cursor-paginated
(`limit`, default 50, max 100; `cursor` is a base64 token for the last row
of the previous page — a malformed cursor is `400`), newest-first and
stable. `/audit/export` takes the same filters plus `format=csv|json`
(default `csv`) and returns one `Content-Disposition: attachment`
response capped at 5000 rows, stamped with `generated_at`, the applied
filters, and whether the cap truncated the result. Each call to either
route records its own `ops.audit_search`/`ops.audit_export` access event
(not deduplicated — an admin's own deliberate query is not polling).

## Vessel trips (/api/v1/trips)

Vessel trip registration, tracking, and voluntary amendments.

### `GET /api/v1/trips`, `GET /api/v1/trips/{trip_id}`

Operator-authenticated (`require_user`).
Returns trips matching optional filters or a single trip by identifier.
Anonymous callers receive HTTP 401.

### `POST /api/v1/trips`, `PATCH /api/v1/trips/{trip_id}`

Restricted to authorized actors.
Requires either:
- An operator token with a responder role (`mdrrmo`, `lgu`, `admin`).
- A vessel device bearer token whose bound `vessel_id` matches the trip's `vessel_id`.
Anonymous callers receive HTTP 401.
Non-responder operators or mismatching vessel devices receive HTTP 403.

## Roles

Approved action matrix (docs/41_OPERATIONS_CONSOLE_AUDITABILITY_IMPLEMENTATION_PLAN.md
Phases 1 and 3). Enforced server-side by `app.auth.require_roles(...)`, not
by hiding dashboard controls — a role never gets an action merely because
the dashboard shows it a panel.

| Action category | Routes | `mdrrmo` | `lgu` | `admin` |
|---|---|---|---|---|
| Responder incident actions | `POST /api/sos/{id}/acknowledge`, `.../resolve`; `POST /api/ai/anomaly/cases/{id}/acknowledge`, `.../dismiss`, `.../escalate`, `.../resolve`; `POST /api/ai/drift/cases`, `.../cases/{id}/rerun`, `.../resolve`, `.../cancel`, `.../incident/{id}/searched` | Yes | Yes | Yes |
| Advisory / sea-condition publication | `GET/POST/PUT/DELETE /api/advisories`, `POST /api/advisories/alert`, `POST /api/sea-condition` | Yes | Yes | Yes |
| Vessel-device pairing & revocation | `POST /api/vessel-auth/pairing-codes`, `POST /api/vessel-auth/devices/{id}/revoke` | No | Yes | Yes |
| Operator-account setup | `POST /api/admin-signup` | Gated by `ADMIN_SETUP_KEY` (not a role check) |||
| Case timeline (one case) | `GET /api/ops/cases/{resource_type}/{resource_id}/timeline` | Yes | Yes | Yes |
| Global audit search / export | `GET /api/ops/audit`, `GET /api/ops/audit/export` | No | **No** | Yes |
| Squall model training | `POST /api/ai/squall/train` | No | No | Yes |

`lgu` has the same permissions as `admin` for every action above **except**
global audit search/export and squall model training (owner decision, 2026-08-30 for operational
rows; squall training restricted to admin to prevent unauthorized model replacement) -
seeing every operator's action history across every case is a different
kind of privilege than the operational writes above. `admin`'s only other
distinct capability outside this table is back-office API-key revocation,
not documented here. `mdrrmo` cannot pair or revoke vessel devices — a
narrowing from previous behaviour, where any authenticated operator role
could — but no dashboard UI exists yet for those two actions, so this is a
backend-only guard for now.

`fisherman` reads safety feeds without auth, but per-vessel status / reply /
catch routes now require a paired vessel-device credential.

`POST /api/catch-logs/{id}/confirm-weight` is a fisher/dispatcher-shared
action that doesn't fit the categories above cleanly; it stays on plain
`require_user` (any authenticated user, not role-restricted) pending
classification in a later phase.

## Conventions

- Timestamps are RFC 3339 UTC.
- All list/stream shapes are stable once `v` (where present) is fixed; bump
  the payload version before changing a field.
- Update this doc first, then tell Jade.
