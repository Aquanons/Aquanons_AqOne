# 07 — Scope Out

Deliberate decisions **not** to build. These are scoped-out choices, not gaps,
and are presented that way in Q&A. Do not implement any of these unless this
doc is amended first.

> **Amended.** Several items below were scoped out during the original 15-hour
> build and have since been built. They are moved to "Amended — now in scope"
> at the end of this document rather than deleted, so the decision trail stays
> readable.
>
> This matters: an outside audit read the stale version of this file and the
> matching line in `AGENTS.md`, and concluded the project had built no AI and no
> backend. Both existed at the time. **A scope document that lies about the
> product is worse than no scope document.** The canonical scope is
> `Aqone_PRD (2).md` (v3.0), where unimplemented sections carry an explicit
> `[Roadmap — not implemented]` tag.

## Hardware / mesh

- No mesh routing protocol. Relay is TTL flooding with a per-node seen-set
  (`docs/02_LOAM_PACKET_SPEC.md`). Good enough for a bay.
- **Current architecture amendment:** Boat-mounted safety pods are now the
  primary phone access and SOS origin nodes. Stationary navigational buoys are
  retained as optional fixed sensor stations and LoRa relays. The decision is
  recorded in `docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`.
- No end-to-end encryption of SOS content in MVP. Frames are channel-signed
  (HMAC) for authenticity; content is plaintext JSON.
- No duplex return channel for ack delivery to the phone **over the mesh**.
  Still true for LoRa: `docs/13_RESPONDER_LOOP.md` specs frame type `0x04` for
  it, and nobody has implemented it. The phone does now learn
  `delivered`/`acknowledged` **and the responder's ETA** over the internet.
- MPU6050 tilt detection is optional and is not a deliverable.

## Product scope (existed in v1, cut for this build)

- **No photos.** SOS is text + optional GPS only; the LoRa channel is narrow.
  Still true.

Catch logging was cut here too, in the original build. It has since been
brought back - see "Amended — now in scope" below.

## Why (for Q&A)

We had ~15.5 build hours and a strict sequential path
(`docs/00_START_HERE.md`). Every item above is a separable product that would
consume the integration budget. The current demo story is: airplane-mode SOS →
boat pod → LoRa → gateway → dashboard → ack. Stationary buoys are added only
for fixed sensing, measured relay gaps, or redundancy.

## How to amend

If a scope-out item becomes essential, edit this doc to move it to
"in scope", then update `AGENTS.md` and `docs/00_START_HERE.md`, and re-check
the build order. Tell the owning workstream.

---

## Amended — now in scope

These were scoped out for the original build and have since been built. Each is
listed with where it now lives, so the claim can be checked against code rather
than taken on trust.

- **Advisories and weather.** Open-Meteo conditions in the app
  (`mobile/lib/services/venture_feeds.dart`), MDRRMO-declared sea condition
  (`backend/app/api/sea_condition.py`), and squall nowcasting with RETURN NOW
  alerts (`backend/app/ai/squall.py`).
  *Honesty note:* the app's wind indicator is a single 30 km/h threshold, shown
  with its source and an explicit "not a PAGASA warning" disclaimer. It is not a
  model and must never be presented as one.

- **Boat-mounted safety pods and hybrid transport.** The original decision to
  avoid boat hardware is amended. A pod provides local phone WiFi, a physical
  SOS path, flash-backed queueing, and direct LoRa to a tall shoreline gateway.
  Stationary navigational buoys remain valuable for fixed-position current and
  environmental data (no barometer; squall alerts come from the PAGASA weather
  API), optional LoRa relay coverage, and redundancy. See
  `docs/55_HYBRID_TRANSPORT_ARCHITECTURE_DECISION.md`.

- **Float-plan / "did not return" logic.** This is now a core AI component -
  learned per-vessel trip profiles, expected-next-contact prediction and a
  four-stage escalation ladder (`backend/app/ai/trip_profile.py`, PRD §5.2).

- **Accounts and passwords.** Dashboard operators have real accounts: bcrypt
  hashes, JWT sessions, and account creation gated behind a server-side setup
  key (`backend/app/auth.py`, `backend/app/api/auth.py`, migration `005_auth`).
  Fisherman identity is still a device-local id with no password, by design -
  a person in distress cannot be asked to log in.

- **LGU role.** `VALID_ROLES` is `mdrrmo`, `lgu`, `admin`. There is still no
  separate regulator dashboard, and fisheries-enforcement features remain out
  of scope deliberately: positioning a safety network as a surveillance network
  would undermine adoption by the people it protects.

- **AI models.** Three are built and measured - squall nowcasting, trip anomaly
  detection and Monte Carlo drift prediction - plus a gradient-boosted
  danger-zone model in `web/ml/`. All are calibrated on synthetic data except
  the danger-zone model, which is trained on real Open-Meteo history. See
  `docs/14_PRD_AUDIT.md` for what is genuinely built versus claimed.

- **Catch logging.** Cut in the original 15-hour build for the same reason
  every item at the top of this doc was: it is a separable product that would
  have consumed the integration budget, and the demo story was airplane-mode
  SOS end to end. With that budget no longer a constraint, it is back:
  species, quantity, method and notes, queued on-device
  (`mobile/lib/services/catch_service.dart`) and uploaded over plain HTTP -
  never LoRa, that airtime stays reserved for distress - to
  `POST /api/catch-logs` (`backend/app/api/catch.py`, migration
  `011_catch_logs`). Trust model is unchanged from SOS: `vessel_id` is trusted
  from the body, because the app still has no accounts for fishermen and there
  is nothing to authenticate against. This was flagged as a real gap in the
  original v1 implementation (`docs/guides/07_SECURITY.md`), but it is not a
  gap introduced by this feature specifically - it is the trust model the
  whole handset-facing API already runs on for SOS ingest, and fixing it
  properly means adding accounts for fishermen, which product scope
  deliberately rejects (see "Accounts and passwords" above).

- **Aggregated catch-activity heatmap.** Fish-hotspot prediction was removed
  from v3.0 and is now amended back into scope as a privacy-preserving recent
  activity surface, not a guaranteed-catch prediction. A catch contributes
  only after explicit per-entry consent. The public API returns coarse cells,
  never exact points or vessel ids, and withholds cells below the independent-
  reporter threshold. The contract is `GET /api/public/hotspots` in
  `docs/05_PUBLIC_API.md`; the backend implementation is
  `backend/app/api/hotspots.py` and the handset renderer is
  `mobile/lib/models/hotspot_cell.dart`.
