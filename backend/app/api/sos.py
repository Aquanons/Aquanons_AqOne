from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.contacts import is_valid_gateway_key, require_gateway_key
from app.audit import record_audit_event
from app.auth import get_optional_vessel_device, require_responder_roles, require_user, require_vessel_device
from app.db import get_pool

# Responder status vocabulary. One byte, so it survives a 64-byte LoRa frame in
# phase 2 and stays consistent between dispatchers under pressure. The canonical
# table lives in docs/13_RESPONDER_LOOP.md; the dashboard and the Flutter app
# mirror these values.
RESPONDER_RECEIVED = 1
RESPONDER_DISPATCHED = 2
RESPONDER_COAST_GUARD = 3
RESPONDER_NEAREST_VESSEL = 4
RESPONDER_DELAYED = 5

RESPONDER_STATUS_LABELS: dict[int, str] = {
    RESPONDER_RECEIVED: 'MDRRMO has your call',
    RESPONDER_DISPATCHED: 'Rescue boat on the way',
    RESPONDER_COAST_GUARD: 'Coast Guard notified',
    RESPONDER_NEAREST_VESSEL: 'Nearby boats alerted',
    RESPONDER_DELAYED: 'Delayed - still coming',
}

REPLY_STILL_IN_DANGER = 1
REPLY_SAFE_NOW = 2


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _delivery_state(row: Any) -> str:
    """Collapse the stored flags into the four states the app speaks.

    Mirrors docs/06_DELIVERY_STATES.md. The handset merges this with whatever
    it already knows, so a state can only ever move forward.
    """
    if row['resolved_at'] is not None:
        return 'acknowledged'
    if row['acknowledged_at'] is not None:
        return 'acknowledged'
    if row['delivered_direct'] or row['delivered_via_buoy']:
        return 'delivered'
    return 'relayed'

# Deliberately NOT behind require_user.
#
# This is a distress endpoint. A fisherman in trouble has no account, no token
# and no way to obtain one at sea, and the LoRa gateway forwards frames from
# handsets it cannot authenticate. Requiring a bearer token here would mean
# rejecting the exact call the product exists to deliver.
#
# The trust model is already explicit about this: every vessel identity is
# self-declared until a responder confirms it (see TrustTier in the mobile app),
# and the dashboard shows that tier next to each incident. Abuse is handled by
# the confidence scoring and by dispatchers, not by blocking the call.
router = APIRouter(prefix='/api/sos', tags=['sos'])

# The read side stays protected - that is dispatcher data.
protected_router = APIRouter(prefix='/api/sos', tags=['sos'])

# The downlink read side. Same prefix, different guard: the LoRa shore gateway
# holds GATEWAY_API_KEY, never an operator login, and needs exactly one thing
# from this file - the responder's answer to a call it already relayed, so it
# can put that answer back on the radio. See sos_downlink() for why this is
# not simply GATEWAY_API_KEY access to /active.
gateway_router = APIRouter(prefix='/api/sos', tags=['sos'])


VALID_TRUST_TIERS = {'self_declared', 'phone_verified', 'confirmed_by_responder'}


class SosIn(BaseModel):
    """An SOS as delivered by either transport.

    `client_ts` is mandatory: with `vessel_id` it forms the de-duplication key
    that lets the direct and buoy routes deliver the same emergency without
    creating two incidents.

    This endpoint is deliberately unauthenticated (see the router comment
    below), so it is also the only untrusted-input boundary in this file.
    Length limits mirror the caps already enforced on the handset
    (`mobile/lib/core/config.dart`: maxVesselIdLength/maxBoatLength = 32,
    maxNoteLength = 64) and on the buoy firmware, which truncates into fixed
    C buffers of the same sizes (`firmware/buoy/AqOneBuoy/AqOneBuoy.ino`
    `SosItem`: `vesselId[33]`, `boat[32]`, `note[64]`). A real client can
    never exceed these; something that does is not a distress call this
    endpoint needs to accept as-is. Rejecting it with 422 does not drop a
    real SOS - it is Pydantic validation ahead of any DB write, so nothing
    is silently discarded, and a caller within these limits is unaffected.
    """

    vessel_id: str = Field(min_length=1, max_length=32)
    client_ts: int = Field(description='Origin epoch seconds, from the handset')
    boat: str = Field(default='', max_length=32)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    note: str | None = Field(default=None, max_length=64)
    trust_tier: str = 'self_declared'

    # Direct path only - the LoRa frame has no room for a UUID. Generous cap:
    # the handset's own _newLocalId() produces roughly 22 characters.
    local_id: str | None = Field(default=None, max_length=64)

    # Buoy path only - taken from the LoRa frame header. Matches the
    # firmware's BUOY_ID convention (e.g. "BUOY01").
    buoy_id: str | None = Field(default=None, max_length=32)
    src_id: int | None = None
    seq: int | None = None

    source: Literal['direct', 'buoy'] = 'direct'

    @field_validator('trust_tier')
    @classmethod
    def _normalise_trust_tier(cls, value: str) -> str:
        # Corroboration metadata only - it is never used to decide whether an
        # SOS is relayed (see the router comment below), so an unexpected
        # value is normalised rather than used as a reason to 422 a distress
        # call over a field that does not affect delivery.
        return value if value in VALID_TRUST_TIERS else 'self_declared'


@router.post('', status_code=200)
async def ingest_sos(
    payload: SosIn,
    api_key: str | None = Header(default=None, alias='X-Api-Key'),
    vessel_device: dict[str, Any] | None = Depends(get_optional_vessel_device),
) -> dict[str, object]:
    """Accept an SOS from either transport. Idempotent.

    First arrival creates the incident. A second arrival of the same emergency
    by the other route updates the existing row rather than inserting: it fills
    in whatever that route knows and the other did not (the direct path has
    local_id, the buoy path has buoy/seq), and records that the route delivered.

    Always returns the same event id, so a client retrying - or both transports
    succeeding - is safe.
    """
    # SEC-06: Store trust_tier='self_declared' unless the request carries a valid
    # vessel device bearer for the same vessel_id; then allow phone_verified.
    # Never accept confirmed_by_responder from ingest.
    trust_tier = 'self_declared'
    if (
        vessel_device is not None
        and vessel_device.get('vessel_id') == payload.vessel_id
        and payload.trust_tier == 'phone_verified'
    ):
        trust_tier = 'phone_verified'

    # SEC-06: Accept source='buoy', buoy_id, src_id, seq only with a valid X-Api-Key.
    # Without it, store the SOS as a direct delivery and drop the buoy fields,
    # so no buoy row is auto-registered.
    has_valid_gateway = is_valid_gateway_key(api_key)

    if has_valid_gateway and payload.source == 'buoy':
        buoy_id = payload.buoy_id
        src_id = payload.src_id
        seq = payload.seq
        delivered_direct = False
        delivered_via_buoy = True
    else:
        buoy_id = None
        src_id = None
        seq = None
        delivered_direct = True
        delivered_via_buoy = False

    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        # The vessel may be unknown: a handset can raise an SOS before it
        # has ever been seen by the backend. Refusing on a missing foreign
        # key would drop a distress call.
        await conn.execute(
            '''
                INSERT INTO vessels (id, boat_name)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
                ''',
            payload.vessel_id,
            payload.boat or payload.vessel_id,
        )

        # Same reasoning for the relaying buoy. sos_events.buoy_id is a foreign
        # key into buoys, and a gateway reports whatever id its board was
        # flashed with - often one no one has registered. Without this, the
        # insert fails, the gateway never acks, and the SOS never lands.
        if buoy_id:
            await conn.execute(
                '''
                    INSERT INTO buoys (id, label)
                    VALUES ($1, $1)
                    ON CONFLICT (id) DO NOTHING
                    ''',
                buoy_id,
            )

        row = await conn.fetchrow(
            '''
                INSERT INTO sos_events (
                  vessel_id, client_ts, boat, latitude, longitude, note,
                  trust_tier, local_id, buoy_id, src_id, seq,
                  delivered_direct, delivered_via_buoy
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (vessel_id, client_ts) DO UPDATE SET
                  -- COALESCE keeps whatever we already knew and fills the gaps
                  -- from this delivery. Neither route can erase the other's data.
                  latitude   = COALESCE(sos_events.latitude,  EXCLUDED.latitude),
                  longitude  = COALESCE(sos_events.longitude, EXCLUDED.longitude),
                  note       = COALESCE(NULLIF(sos_events.note, ''), EXCLUDED.note),
                  local_id   = COALESCE(sos_events.local_id,  EXCLUDED.local_id),
                  buoy_id    = COALESCE(sos_events.buoy_id,   EXCLUDED.buoy_id),
                  src_id     = COALESCE(sos_events.src_id,    EXCLUDED.src_id),
                  seq        = COALESCE(sos_events.seq,       EXCLUDED.seq),
                  boat       = COALESCE(NULLIF(sos_events.boat, ''), EXCLUDED.boat),
                  delivered_direct   = sos_events.delivered_direct   OR EXCLUDED.delivered_direct,
                  delivered_via_buoy = sos_events.delivered_via_buoy OR EXCLUDED.delivered_via_buoy
                RETURNING *, (xmax = 0) AS was_inserted
                ''',
            payload.vessel_id,
            payload.client_ts,
            payload.boat,
            payload.lat,
            payload.lon,
            payload.note,
            trust_tier,
            payload.local_id,
            buoy_id,
            src_id,
            seq,
            delivered_direct,
            delivered_via_buoy,
        )

    return {
        'id': row['id'],
        # False means this emergency was already known - the other transport
        # got here first. The client treats both as success.
        'created': bool(row['was_inserted']),
        'duplicate': not bool(row['was_inserted']),
        'vessel_id': row['vessel_id'],
        'client_ts': row['client_ts'],
        'delivered_direct': row['delivered_direct'],
        'delivered_via_buoy': row['delivered_via_buoy'],
        'acknowledged_at': row['acknowledged_at'].isoformat() if row['acknowledged_at'] else None,
    }


@router.get('/ack/{local_id}')
async def ack_by_local_id(local_id: str) -> dict[str, object]:
    """The unauthenticated read-back that answers a direct-path handset.

    `POST /api/sos` deliberately requires no credentials (see its docstring):
    a fisherman at sea has no account to hold and no way to obtain one. The
    acknowledgement of a call a handset raised that way is the same safety
    information as the call itself, so its read-back is not gated either -
    demanding a vessel-device token here would silently strand exactly the
    un-enrolled phones the direct path exists for.

    The lookup is keyed on `local_id`, the id the handset itself generated and
    sent with the SOS (it is also the app's outbox key, so only that phone
    knows it). The response reveals one thing only - what happened to that one
    incident: no other vessel's rows, no coordinates, no note. 404 until the
    id exists on the backend, so a poll before then simply reads as "not yet".

    Returns the same single-event shape as
    `GET /api/sos/vessel/{vessel_id}`, so the phone parses an ack from both
    sources through one code path.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT id, vessel_id, local_id, seq, client_ts, acknowledged_at,
                   acked_by, eta_at, responder_status, responder_note,
                   fisher_reply, resolved_at,
                   delivered_direct, delivered_via_buoy
            FROM sos_events
            WHERE local_id = $1
            LIMIT 1
            ''',
            local_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail='no such SOS event')
    return {
        'vessel_id': row['vessel_id'],
        'server_time': datetime.now(UTC).isoformat(),
        'event': {
            'id': row['id'],
            'local_id': row['local_id'],
            'seq': row['seq'],
            'client_ts': row['client_ts'],
            'delivery_state': _delivery_state(row),
            'acknowledged_at': _iso(row['acknowledged_at']),
            'acked_by': row['acked_by'],
            'eta_at': _iso(row['eta_at']),
            'responder_status': row['responder_status'],
            'responder_status_label': RESPONDER_STATUS_LABELS.get(row['responder_status']),
            'responder_note': row['responder_note'],
            'fisher_reply': row['fisher_reply'],
            'resolved_at': _iso(row['resolved_at']),
        },
    }


def _event_json(row: Any) -> dict[str, object]:
    timestamp_columns = (
        'created_at', 'acknowledged_at', 'eta_at', 'fisher_replied_at', 'resolved_at',
    )
    data = dict(row)
    for col in timestamp_columns:
        data[col] = _iso(row[col])
    data['responder_status_label'] = RESPONDER_STATUS_LABELS.get(row['responder_status'])
    return data


@protected_router.get('/active')
async def active_sos(_: dict = Depends(require_user)) -> dict[str, object]:
    """Every unresolved SOS event, newest first. Dispatcher view.

    Includes acknowledged-but-unresolved incidents, not just brand-new ones -
    otherwise an acknowledgement makes the incident disappear before the
    dispatcher can see the fisher's reply to it. An incident leaves this feed
    only once a dispatcher resolves it or the fisher sends SAFE_NOW.

    Each event carries the vessel's declared owner identity
    (`POST /api/vessel-profile`) alongside its snapshot fields, so a
    dispatcher can see who raised the call. That identity includes the owner's
    contact number and license info. The
    trust tier that sits on the incident is the same self-declared claim,
    shown next to it (docs/16).
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT e.id, e.vessel_id, e.boat, e.latitude, e.longitude, e.note,
                   e.trust_tier,
                   e.client_ts, e.delivered_direct, e.delivered_via_buoy,
                   e.buoy_id, e.created_at, e.acknowledged_at, e.acked_by,
                   e.eta_at, e.responder_status, e.responder_note,
                   e.fisher_reply, e.fisher_replied_at, e.resolved_at,
                   e.is_synthetic,
                   v.skipper_name, v.license_type, v.license_number, v.phone
            FROM sos_events e
            LEFT JOIN vessels v ON v.id = e.vessel_id
            WHERE e.resolved_at IS NULL
            ORDER BY e.created_at DESC
            '''
        )

    return {'events': [_event_json(row) for row in rows]}


@protected_router.get('/recent')
async def recent_sos(_: dict = Depends(require_user)) -> dict[str, object]:
    """Resolved SOS events, newest first. Dispatcher history view.

    `/active` drops an incident the moment it is resolved, so without this
    the dashboard has no record of who was resolved or what the fisher's
    last report on it was. Same shape as `/active`, including the vessel
    profile join, so the history rows render with sender and reply intact.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT e.id, e.vessel_id, e.boat, e.latitude, e.longitude, e.note,
                   e.trust_tier,
                   e.client_ts, e.delivered_direct, e.delivered_via_buoy,
                   e.buoy_id, e.created_at, e.acknowledged_at, e.acked_by,
                   e.eta_at, e.responder_status, e.responder_note,
                   e.fisher_reply, e.fisher_replied_at, e.resolved_at,
                   e.is_synthetic,
                   v.skipper_name, v.license_type, v.license_number, v.phone
            FROM sos_events e
            LEFT JOIN vessels v ON v.id = e.vessel_id
            WHERE e.resolved_at IS NOT NULL
            ORDER BY e.resolved_at DESC
            LIMIT 20
            '''
        )

    return {'events': [_event_json(row) for row in rows]}


# How long a resolved incident keeps appearing in the downlink feed.
#
# /active drops an incident the moment a dispatcher resolves it, which is
# correct for a dashboard - the case is closed and the operator should stop
# looking at it. It is wrong for the radio: the shore gateway polls on a 45 s
# cycle, so an incident acknowledged and then resolved between two polls would
# leave the mesh without the closure ever going out, and the handset would
# count down an ETA for a rescue that already finished. Holding resolved
# incidents in this feed for a while gives the gateway room to see the final
# state and send it down. Six hours is far longer than it needs and still
# bounded, so the feed cannot grow without limit.
DOWNLINK_RESOLVED_WINDOW_HOURS = 6


@gateway_router.get('/downlink', dependencies=[Depends(require_gateway_key)])
async def sos_downlink() -> dict[str, object]:
    """The responder's answer to each live call, for the LoRa shore gateway.

    This is deliberately NOT `GATEWAY_API_KEY` access to `/active`.
    `app/main.py` states the rule this endpoint has to satisfy - a gateway key
    must not read dispatcher data - and `/active` is dispatcher data: it
    carries position, the fisher's own distress note, boat name, trust tier
    and the vessel owner's name, licence and phone number. A gateway is a
    radio relay bolted to a mast; it has no business holding any of that, and
    a key that ships hardcoded in firmware is the last credential that should
    unlock it.

    So this returns only what travels back DOWN the radio anyway: the
    acknowledgement, the ETA, the responder's status and note, and the
    closure. Every field here is something the gateway is about to broadcast
    to the boat in clear. Nothing is disclosed that the fisher is not already
    being told.

    One row per vessel, its newest call. Unlike `/active`, which lists every
    incident because a dispatcher needs the whole board, everything consuming
    this feed is keyed by VESSEL and not by incident: the gateway's downlink
    signature, and the buoy cache that answers the handset. Returning a boat's
    older calls alongside its current one made each of them overwrite the
    newer, and the fisher was finally told about the oldest - an expired ETA
    carrying a seq the handset no longer held. It also multiplied radio
    airtime by the number of calls that boat had ever made.

    `delivery_state` is collapsed here rather than left to the caller. The
    gateway used to recompute it from `delivered_direct`/`delivered_via_buoy`,
    which meant `_delivery_state()` had a second implementation living in
    firmware that only a reflash could correct if the two ever drifted.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT DISTINCT ON (e.vessel_id)
                   e.id, e.vessel_id, e.seq,
                   e.delivered_direct, e.delivered_via_buoy,
                   e.acknowledged_at, e.acked_by, e.eta_at,
                   e.responder_status, e.responder_note, e.resolved_at
            FROM sos_events e
            WHERE e.resolved_at IS NULL
               OR e.resolved_at > NOW() - make_interval(hours => $1)
            ORDER BY e.vessel_id, e.created_at DESC
            LIMIT 100
            ''',
            DOWNLINK_RESOLVED_WINDOW_HOURS,
        )
    return {
        'events': [
            {
                'id': row['id'],
                'vessel_id': row['vessel_id'],
                'seq': row['seq'],
                'delivery_state': _delivery_state(row),
                'acknowledged_at': _iso(row['acknowledged_at']),
                'acked_by': row['acked_by'],
                'eta_at': _iso(row['eta_at']),
                'responder_status': row['responder_status'],
                'responder_note': row['responder_note'],
                'resolved_at': _iso(row['resolved_at']),
            }
            for row in rows
        ]
    }


class AcknowledgeIn(BaseModel):
    """A dispatcher's answer to a distress call.

    `eta_minutes` is what the dispatcher types; the server converts it to an
    absolute `eta_at` so the clock is authoritative and not the browser's, and
    so the handset's countdown stays correct however long delivery takes.
    """

    eta_minutes: int | None = Field(default=None, ge=1, le=720)
    responder_status: int = Field(default=RESPONDER_RECEIVED, ge=1, le=5)
    responder_note: str | None = None


@protected_router.post('/{event_id}/acknowledge')
async def acknowledge(
    event_id: int,
    payload: AcknowledgeIn | None = None,
    user: dict = require_responder_roles,
) -> dict[str, object]:
    body = payload or AcknowledgeIn()
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET acknowledged_at  = COALESCE(acknowledged_at, NOW()),
                   acked_by         = $2,
                   responder_status = $3,
                   responder_note   = COALESCE($4, responder_note),
                   -- NULL eta_minutes leaves any existing ETA untouched, so a
                   -- dispatcher can update the status without wiping the time.
                   eta_at = CASE
                              WHEN $5::INT IS NULL THEN eta_at
                              ELSE NOW() + ($5::INT * INTERVAL '1 minute')
                            END
             WHERE id = $1
            RETURNING id, acknowledged_at, acked_by, eta_at,
                      responder_status, responder_note, is_synthetic
            ''',
            event_id,
            user.get('email') or 'unknown',
            body.responder_status,
            body.responder_note,
            body.eta_minutes,
        )
        if row is None:
            raise HTTPException(status_code=404, detail='no such SOS event')
        # Every call is a real event, not a retry to deduplicate: a
        # dispatcher legitimately re-calls this with a new responder_status
        # to report progress (RECEIVED -> DISPATCHED -> ...), so each one is
        # its own audit-worthy transition (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='sos.acknowledge',
            resource_type='sos_event',
            resource_id=row['id'],
            outcome='applied',
            is_demo=row['is_synthetic'],
            metadata={'responder_status': row['responder_status']},
        )
    return {
        'ok': True,
        'id': row['id'],
        'acknowledged_at': row['acknowledged_at'].isoformat(),
        'acked_by': row['acked_by'],
        'eta_at': row['eta_at'].isoformat() if row['eta_at'] else None,
        'responder_status': row['responder_status'],
        'responder_status_label': RESPONDER_STATUS_LABELS.get(row['responder_status']),
        'responder_note': row['responder_note'],
    }


class ResolveIn(BaseModel):
    """An optional resolver note - never required, since a fisher's own
    SAFE_NOW reply also resolves the incident with no dispatcher involved.
    """

    reason: str | None = Field(default=None, max_length=280)


@protected_router.post('/{event_id}/resolve')
async def resolve_sos(
    event_id: int,
    payload: ResolveIn | None = None,
    user: dict = require_responder_roles,
) -> dict[str, object]:
    body = payload or ResolveIn()
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT resolved_at FROM sos_events WHERE id = $1 FOR UPDATE', event_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such SOS event')
        was_already_resolved = prior['resolved_at'] is not None

        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET resolved_at = COALESCE(resolved_at, NOW()),
                   resolved_by = COALESCE(resolved_by, $2),
                   resolved_reason = COALESCE(resolved_reason, $3)
             WHERE id = $1
            RETURNING id, resolved_at, resolved_by, resolved_reason, acked_by, is_synthetic
            ''',
            event_id,
            user.get('email') or 'unknown',
            body.reason,
        )
        # resolved_reason is free text and never logged (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='sos.resolve',
            resource_type='sos_event',
            resource_id=row['id'],
            outcome='no_change' if was_already_resolved else 'updated',
            is_demo=row['is_synthetic'],
        )
    return {
        'ok': True,
        'id': row['id'],
        'resolved_at': _iso(row['resolved_at']),
        'resolved_by': row['resolved_by'],
        'resolved_reason': row['resolved_reason'],
        'acked_by': row['acked_by'],
    }


@protected_router.post('/{event_id}/reopen')
async def reopen_sos(
    event_id: int,
    user: dict = require_responder_roles,
) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT resolved_at FROM sos_events WHERE id = $1', event_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such SOS event')
        if prior['resolved_at'] is None:
            raise HTTPException(status_code=409, detail='SOS event is not resolved')
        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET resolved_at = NULL,
                   resolved_by = NULL,
                   resolved_reason = NULL
             WHERE id = $1
            RETURNING id, resolved_at, is_synthetic
            ''',
            event_id,
        )
        await record_audit_event(
            conn,
            actor=user,
            action='sos.reopen',
            resource_type='sos_event',
            resource_id=row['id'],
            outcome='updated',
            is_demo=row['is_synthetic'],
        )
    return {'ok': True, 'id': row['id'], 'resolved_at': None}


@router.get('/vessel/{vessel_id}')
async def vessel_sos(
    vessel_id: str,
    device: dict[str, object] = Depends(require_vessel_device),
) -> dict[str, object]:
    """What the handset polls to learn whether anyone answered.

    Protected under Option A. The backend derives vessel ownership from the
    verified device credential, not from the path; the path value is only a
    consistency check so a mismatched client cannot read another vessel's data.
    """
    owned_vessel_id = str(device['vessel_id'])
    if vessel_id != owned_vessel_id:
        raise HTTPException(status_code=403, detail='device is not paired for that vessel')

    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT id, local_id, seq, client_ts, acknowledged_at, acked_by,
                   eta_at, responder_status, responder_note,
                   fisher_reply, resolved_at,
                   delivered_direct, delivered_via_buoy
            FROM sos_events
            WHERE vessel_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            ''',
            owned_vessel_id,
        )

    return {
        'vessel_id': owned_vessel_id,
        # Server time, so the handset can correct for clock drift before
        # rendering a countdown against eta_at.
        'server_time': datetime.now(UTC).isoformat(),
        'events': [
            {
                'id': row['id'],
                'local_id': row['local_id'],
                'seq': row['seq'],
                'client_ts': row['client_ts'],
                'delivery_state': _delivery_state(row),
                'acknowledged_at': _iso(row['acknowledged_at']),
                'acked_by': row['acked_by'],
                'eta_at': _iso(row['eta_at']),
                'responder_status': row['responder_status'],
                'responder_status_label': RESPONDER_STATUS_LABELS.get(row['responder_status']),
                'responder_note': row['responder_note'],
                'fisher_reply': row['fisher_reply'],
                'resolved_at': _iso(row['resolved_at']),
            }
            for row in rows
        ],
    }


class ReplyIn(BaseModel):
    """The fisher's one-tap answer to an acknowledgement."""

    reply: int = Field(ge=1, le=2, description='1 STILL_IN_DANGER, 2 SAFE_NOW')


@router.post('/{event_id}/reply')
async def fisher_reply(
    event_id: int,
    payload: ReplyIn,
    device: dict[str, object] = Depends(require_vessel_device),
) -> dict[str, object]:
    """Record the fisher's reply on that vessel's own incident (credentialed).

    SAFE_NOW resolves the incident, which is what lets a dispatcher release
    assets to somebody else. Once resolved, the reply is frozen: a later
    retry - of the same reply or a different one - can neither reopen the
    incident nor replace what was recorded, so retrying is always safe.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET fisher_reply      = CASE WHEN resolved_at IS NULL THEN $2 ELSE fisher_reply END,
                   fisher_replied_at = CASE WHEN resolved_at IS NULL THEN NOW() ELSE fisher_replied_at END,
                   resolved_at       = CASE WHEN resolved_at IS NULL AND $2 = $3 THEN NOW() ELSE resolved_at END
             WHERE id = $1
               AND vessel_id = $4
            RETURNING id, fisher_reply, fisher_replied_at, resolved_at
            ''',
            event_id,
            payload.reply,
            REPLY_SAFE_NOW,
            device['vessel_id'],
        )
    if row is None:
        raise HTTPException(status_code=404, detail='no such SOS event')
    return {
        'ok': True,
        'id': row['id'],
        'fisher_reply': row['fisher_reply'],
        'fisher_replied_at': _iso(row['fisher_replied_at']),
        'resolved_at': _iso(row['resolved_at']),
    }


@router.post('/reply/{local_id}')
async def fisher_reply_by_local_id(
    local_id: str,
    payload: ReplyIn,
) -> dict[str, object]:
    """Record the fisher's reply without a device credential.

    Mirrors ``GET /api/sos/ack/{local_id}``'s trust model: the SOS ingest
    deliberately requires no credentials (see ``post_sos`` docstring), and the
    acknowledgement read-back follows the same rule.  The fisher's reply is
    the same safety-class information and the same self-declared vessel
    identity, so it too can be keyed on ``local_id`` - the high-entropy id
    only the raising handset knows.

    An attacker who learns the local_id could mark SAFE_NOW, but that same
    local_id already grants read access to the ack.  The local_id is a
    per-SOS random string generated by the handset and is never broadcast.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET fisher_reply      = CASE WHEN resolved_at IS NULL THEN $2 ELSE fisher_reply END,
                   fisher_replied_at = CASE WHEN resolved_at IS NULL THEN NOW() ELSE fisher_replied_at END,
                   resolved_at       = CASE WHEN resolved_at IS NULL AND $2 = $3 THEN NOW() ELSE resolved_at END
             WHERE local_id = $1
            RETURNING id, fisher_reply, fisher_replied_at, resolved_at
            ''',
            local_id,
            payload.reply,
            REPLY_SAFE_NOW,
        )
    if row is None:
        raise HTTPException(status_code=404, detail='no such SOS event')
    return {
        'ok': True,
        'id': row['id'],
        'fisher_reply': row['fisher_reply'],
        'fisher_replied_at': _iso(row['fisher_replied_at']),
        'resolved_at': _iso(row['resolved_at']),
    }
