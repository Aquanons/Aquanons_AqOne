from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BeforeValidator, Field, field_validator

from app.api.contacts import is_valid_gateway_key, require_gateway_key
from app.audit import record_audit_event
from app.auth import get_optional_vessel_device, require_responder_roles, require_user, require_vessel_device
from app.db import get_pool
from app.geo import SHORE_STATIONS, distance_km
from app.incidents.delivery import delivery_state
from app.incidents.downlink import OPEN_WINDOW, RESOLVED_WINDOW, select_downlink
from app.incidents.lifecycle import ResolutionCode, can_reopen, fisher_reply_reopens, resolution_code_from
from app.incidents.plausibility import PlausibilityContext
from app.incidents.plausibility import flags as plausibility_flags
from app.incidents.text import truncate_utf8
from app.incidents.triage import flood_status, triage_key
from app.incidents.trust import vessel_verified

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

CONFLICT_DEGREES = 0.009


@dataclass(frozen=True)
class SosProvenance:
    trust_tier: str
    buoy_id: str | None
    src_id: int | None
    seq: int | None
    delivered_direct: bool
    delivered_via_buoy: bool


def _truncate_text(value: Any, max_bytes: int) -> Any:
    return truncate_utf8(value, max_bytes) if isinstance(value, str) else value


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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

    `client_ts` is the legacy de-duplication key; newer handsets add a nonce.

    Note and boat are truncated to their byte-safe transport caps.
    `nonce` distinguishes modern incidents while `client_ts` remains the
    legacy merge key.
    """

    vessel_id: str = Field(min_length=1, max_length=32)
    client_ts: int = Field(description='Origin epoch seconds, from the handset')
    boat: Annotated[str, BeforeValidator(lambda value: _truncate_text(value, 32))] = ''
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    note: Annotated[str | None, BeforeValidator(lambda value: _truncate_text(value, 64))] = None
    nonce: int | None = Field(default=None, ge=0, le=4_294_967_295)
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
    trust_tier = 'self_declared'
    if (
        vessel_device is not None
        and vessel_device.get('vessel_id') == payload.vessel_id
        and payload.trust_tier == 'phone_verified'
    ):
        trust_tier = 'phone_verified'

    has_valid_gateway = is_valid_gateway_key(api_key)
    if has_valid_gateway and payload.source == 'buoy':
        provenance = SosProvenance(
            trust_tier, payload.buoy_id, payload.src_id, payload.seq, False, True,
        )
    else:
        provenance = SosProvenance(trust_tier, None, None, None, True, False)
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        row = await _upsert_sos(conn, payload, provenance)

    return {
        'id': row['id'],
        # False means this emergency was already known - the other transport
        # got here first. The client treats both as success.
        'created': bool(row['was_inserted']),
        'duplicate': not bool(row['was_inserted']),
        'vessel_id': row['vessel_id'],
        'client_ts': row['client_ts'],
        'nonce': row['nonce'],
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
            SELECT id, vessel_id, local_id, seq, client_ts, nonce, acknowledged_at,
                   acked_by, eta_at, responder_status, responder_note,
                   fisher_reply, fisher_replied_at, resolved_at,
                   resolution_code, version, reopened_at,
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
        'event': _event_json(row),
    }


def _event_json(row: Any, server_time: datetime | None = None) -> dict[str, object]:
    data = dict(row)
    for col, value in data.items():
        if isinstance(value, datetime):
            data[col] = value.isoformat()
    data['responder_status_label'] = RESPONDER_STATUS_LABELS.get(row['responder_status'])
    data['delivery_state'] = delivery_state(row)
    data.setdefault('nonce', None)
    if server_time is not None:
        data['server_time'] = server_time.isoformat()
    return data


def _version_conflict(row: Any) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'detail': 'version_conflict', 'current': _event_json(row)},
    )


@protected_router.get('/active')
async def active_sos(
    limit: int = Query(default=200, ge=1, le=1000),
    _: dict = Depends(require_user),
) -> dict[str, object]:
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
                   e.client_ts, e.nonce, e.delivered_direct, e.delivered_via_buoy,
                   e.buoy_id, e.created_at, e.acknowledged_at, e.acked_by,
                   e.eta_at, e.responder_status, e.responder_note,
                   e.fisher_reply, e.fisher_replied_at, e.resolved_at,
                   e.resolution_code, e.version, e.reopened_at,
                   e.is_synthetic, e.alt_latitude, e.alt_longitude,
                   COUNT(*) OVER (PARTITION BY e.vessel_id) AS open_calls_for_vessel,
                   EXISTS (SELECT 1 FROM vessel_trips t WHERE t.vessel_id = e.vessel_id) AS has_trip_history,
                   c.observed_at AS last_contact_at,
                   c.latitude AS last_contact_latitude, c.longitude AS last_contact_longitude,
                   v.skipper_name, v.license_type, v.license_number, v.phone,
                   v.phone_set_by, v.shore_contact_name, v.shore_contact_phone, v.confirmed_at,
                   EXISTS (SELECT 1 FROM vessel_devices d WHERE d.vessel_id = v.id
                           AND d.revoked_at IS NULL) AS has_active_device
            FROM sos_events e
            LEFT JOIN vessels v ON v.id = e.vessel_id
            LEFT JOIN LATERAL (
              SELECT bc.observed_at, bc.latitude, bc.longitude
              FROM buoy_contacts bc
              WHERE bc.vessel_id = e.vessel_id
                AND bc.source = 'live' AND bc.is_synthetic IS FALSE
                AND bc.observed_at >= NOW() - INTERVAL '1 hour'
              ORDER BY bc.observed_at DESC
              LIMIT 1
            ) c ON TRUE
            WHERE e.resolved_at IS NULL
            '''
        )

    now = datetime.now(UTC)
    events = [_enrich(row, now) for row in rows]
    flood = flood_status(events, now)
    events.sort(key=triage_key)
    for event in events:
        event.pop('has_trip_history', None)
        event.pop('corroborated', None)
    return {'events': events[:limit], 'total': len(events), 'flood': flood}


def _enrich(row: Any, now: datetime) -> dict[str, object]:
    event = _event_json(row)
    has_trip_history = bool(row.get('has_trip_history', False))
    open_calls = row.get('open_calls_for_vessel', 1)
    verified = vessel_verified(bool(row.get('has_active_device', False)), row.get('confirmed_at'))
    verified = verified or row['trust_tier'] in {'phone_verified', 'confirmed_by_responder'}
    event['created_at'] = row['created_at']
    pressed_at = datetime.fromtimestamp(row['client_ts'], UTC) if row['client_ts'] is not None else None
    event['pressed_at'] = pressed_at.isoformat() if pressed_at else None
    event['is_late'] = bool(
        pressed_at is not None
        and (row['created_at'] - pressed_at).total_seconds() > 30 * 60
    )
    event['open_calls_for_vessel'] = open_calls
    event['alt_latitude'] = row.get('alt_latitude')
    event['alt_longitude'] = row.get('alt_longitude')
    event['delivery_path'] = 'pod' if row['delivered_via_buoy'] else 'direct'
    event['vessel_verified'] = verified
    event['phone_set_by'] = row.get('phone_set_by')
    event['shore_contact_name'] = row.get('shore_contact_name')
    event['shore_contact_phone'] = row.get('shore_contact_phone')
    event['has_trip_history'] = has_trip_history
    event['corroborated'] = bool(row['delivered_via_buoy'] or verified or has_trip_history)
    if row['latitude'] is not None and row['longitude'] is not None:
        station = min(
            SHORE_STATIONS,
            key=lambda item: distance_km(row['latitude'], row['longitude'], item['lat'], item['lon']),
        )
    else:
        station = SHORE_STATIONS[0]
    context = PlausibilityContext(
        gateway_latitude=station['lat'],
        gateway_longitude=station['lon'],
        contact_at=row.get('last_contact_at'),
        contact_latitude=row.get('last_contact_latitude'),
        contact_longitude=row.get('last_contact_longitude'),
        open_calls_for_vessel=open_calls,
        now=now,
    )
    event['flags'] = plausibility_flags(event, context)
    return event


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
                   e.client_ts, e.nonce, e.delivered_direct, e.delivered_via_buoy,
                   e.buoy_id, e.created_at, e.acknowledged_at, e.acked_by,
                   e.eta_at, e.responder_status, e.responder_note,
                   e.fisher_reply, e.fisher_replied_at, e.resolved_at,
                   e.resolution_code, e.version, e.reopened_at,
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


@gateway_router.get('/downlink', dependencies=[Depends(require_gateway_key)])
async def sos_downlink() -> dict[str, object]:
    """Return one vessel's latest answer fields without dispatcher data."""
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        rows = await conn.fetch(
            '''
            SELECT DISTINCT ON (e.vessel_id)
                   e.id, e.vessel_id, e.seq, e.nonce, e.created_at, e.fisher_replied_at,
                   e.delivered_direct, e.delivered_via_buoy,
                   e.acknowledged_at, e.acked_by, e.eta_at,
                   e.responder_status, e.responder_note, e.resolved_at,
                   e.resolution_code, e.version, e.reopened_at
            FROM sos_events e
            WHERE e.is_synthetic IS FALSE
              AND (
                (e.resolved_at IS NULL AND GREATEST(
                  e.created_at, COALESCE(e.acknowledged_at, e.created_at),
                  COALESCE(e.reopened_at, e.created_at), COALESCE(e.fisher_replied_at, e.created_at)
                ) > NOW() - $1::INTERVAL)
                OR e.resolved_at > NOW() - $2::INTERVAL
              )
            ORDER BY e.vessel_id, e.created_at DESC
            ''',
            OPEN_WINDOW,
            RESOLVED_WINDOW,
        )
        await conn.execute(
            '''
            INSERT INTO gateway_status (gateway_key, last_poll_at)
            VALUES ('default', NOW())
            ON CONFLICT (gateway_key) DO UPDATE SET last_poll_at = EXCLUDED.last_poll_at
            '''
        )
        rows = select_downlink(rows, datetime.now(UTC))
    events = [_event_json(row) for row in rows]
    for event in events:
        event.pop('created_at', None)
    return {
        'events': events
    }


class AcknowledgeIn(BaseModel):
    """Dispatcher response fields; ETA minutes become server-time timestamps."""

    eta_minutes: int | None = Field(default=None, ge=1, le=720)
    responder_status: int = Field(default=RESPONDER_RECEIVED, ge=1, le=5)
    responder_note: str | None = None
    expected_version: int | None = Field(default=None, ge=0)

    @field_validator('responder_note')
    @classmethod
    def _limit_responder_note_bytes(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode('utf-8')) > 40:
            raise HTTPException(status_code=422, detail='responder_note_too_long')
        return value


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
                   version          = version + 1,
                   -- NULL eta_minutes leaves any existing ETA untouched, so a
                   -- dispatcher can update the status without wiping the time.
                   eta_at = CASE
                              WHEN $5::INT IS NULL THEN eta_at
                              ELSE NOW() + ($5::INT * INTERVAL '1 minute')
                            END
             WHERE id = $1 AND ($6::INT IS NULL OR version = $6)
            RETURNING id, acknowledged_at, acked_by, eta_at,
                      responder_status, responder_note, is_synthetic, version
            ''',
            event_id,
            user.get('email') or 'unknown',
            body.responder_status,
            body.responder_note,
            body.eta_minutes,
            body.expected_version,
        )
        if row is None:
            current = await conn.fetchrow('SELECT * FROM sos_events WHERE id = $1', event_id)
            if current is None:
                raise HTTPException(status_code=404, detail='no such SOS event')
            return _version_conflict(current)
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
        'version': row['version'],
    }


async def _upsert_sos(conn: Any, payload: SosIn, provenance: SosProvenance) -> Any:
    await conn.execute(
        '''
        INSERT INTO vessels (id, boat_name) VALUES ($1, $2)
        ON CONFLICT (id) DO NOTHING
        ''',
        payload.vessel_id,
        payload.boat or payload.vessel_id,
    )
    if provenance.buoy_id:
        await conn.execute(
            'INSERT INTO buoys (id, label) VALUES ($1, $1) ON CONFLICT (id) DO NOTHING',
            provenance.buoy_id,
        )

    conflict = (
        'ON CONFLICT (vessel_id, nonce) WHERE nonce IS NOT NULL'
        if payload.nonce is not None
        else 'ON CONFLICT (vessel_id, client_ts) WHERE nonce IS NULL'
    )
    # ponytail: this box is about 1 km at 11 degrees N; use haversine if operations move far from the equator.
    row = await conn.fetchrow(
        f'''
        INSERT INTO sos_events (
          vessel_id, client_ts, nonce, boat, latitude, longitude, note,
          trust_tier, local_id, buoy_id, src_id, seq,
          delivered_direct, delivered_via_buoy
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        {conflict} DO UPDATE SET
          latitude = COALESCE(sos_events.latitude, EXCLUDED.latitude),
          longitude = COALESCE(sos_events.longitude, EXCLUDED.longitude),
          alt_latitude = CASE
            WHEN sos_events.alt_latitude IS NULL
             AND sos_events.latitude IS NOT NULL AND EXCLUDED.latitude IS NOT NULL
             AND sos_events.longitude IS NOT NULL AND EXCLUDED.longitude IS NOT NULL
             AND (abs(sos_events.latitude - EXCLUDED.latitude) > {CONFLICT_DEGREES}
               OR abs(sos_events.longitude - EXCLUDED.longitude) > {CONFLICT_DEGREES})
            THEN EXCLUDED.latitude ELSE sos_events.alt_latitude END,
          alt_longitude = CASE
            WHEN sos_events.alt_latitude IS NULL
             AND sos_events.latitude IS NOT NULL AND EXCLUDED.latitude IS NOT NULL
             AND sos_events.longitude IS NOT NULL AND EXCLUDED.longitude IS NOT NULL
             AND (abs(sos_events.latitude - EXCLUDED.latitude) > {CONFLICT_DEGREES}
               OR abs(sos_events.longitude - EXCLUDED.longitude) > {CONFLICT_DEGREES})
            THEN EXCLUDED.longitude ELSE sos_events.alt_longitude END,
          note = COALESCE(NULLIF(sos_events.note, ''), EXCLUDED.note),
          local_id = COALESCE(sos_events.local_id, EXCLUDED.local_id),
          buoy_id = COALESCE(sos_events.buoy_id, EXCLUDED.buoy_id),
          src_id = COALESCE(sos_events.src_id, EXCLUDED.src_id),
          seq = COALESCE(sos_events.seq, EXCLUDED.seq),
          boat = COALESCE(NULLIF(sos_events.boat, ''), EXCLUDED.boat),
          delivered_direct = sos_events.delivered_direct OR EXCLUDED.delivered_direct,
          delivered_via_buoy = sos_events.delivered_via_buoy OR EXCLUDED.delivered_via_buoy
        RETURNING *, (xmax = 0) AS was_inserted
        ''',
        payload.vessel_id, payload.client_ts, payload.nonce, payload.boat,
        payload.lat, payload.lon, payload.note, provenance.trust_tier,
        payload.local_id, provenance.buoy_id, provenance.src_id, provenance.seq,
        provenance.delivered_direct, provenance.delivered_via_buoy,
    )
    return row


class ResolveIn(BaseModel):
    """An optional resolver note - never required, since a fisher's own
    SAFE_NOW reply also resolves the incident with no dispatcher involved.
    """

    reason: str | None = Field(default=None, max_length=280)
    reason_code: ResolutionCode | None = None
    expected_version: int | None = Field(default=None, ge=0)


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
            'SELECT * FROM sos_events WHERE id = $1 FOR UPDATE', event_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such SOS event')
        was_already_resolved = prior['resolved_at'] is not None
        if body.expected_version is not None and body.expected_version != prior['version']:
            return _version_conflict(prior)

        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET resolved_at = COALESCE(resolved_at, NOW()),
                   resolved_by = COALESCE(resolved_by, $2),
                   resolved_reason = COALESCE(resolved_reason, $3),
                   resolution_code = COALESCE(resolution_code, $4),
                   version = version + 1
             WHERE id = $1
            RETURNING id, resolved_at, resolved_by, resolved_reason, acked_by, is_synthetic,
                      resolution_code, version
            ''',
            event_id,
            user.get('email') or 'unknown',
            body.reason,
            resolution_code_from(body.reason_code).value,
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
        'resolution_code': row['resolution_code'],
        'version': row['version'],
    }


class ReopenIn(BaseModel):
    reason: str | None = Field(default=None, max_length=280)
    expected_version: int | None = Field(default=None, ge=0)


@protected_router.post('/{event_id}/reopen')
async def reopen_sos(
    event_id: int,
    payload: ReopenIn | None = None,
    user: dict = require_responder_roles,
) -> dict[str, object]:
    body = payload or ReopenIn()
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow('SELECT * FROM sos_events WHERE id = $1 FOR UPDATE', event_id)
        if prior is None:
            raise HTTPException(status_code=404, detail='no such SOS event')
        if body.expected_version is not None and body.expected_version != prior['version']:
            return _version_conflict(prior)
        if not can_reopen(prior['resolved_at']):
            return {'ok': True, 'id': event_id, 'outcome': 'no_change', 'version': prior['version']}
        row = await conn.fetchrow(
            '''
            UPDATE sos_events
               SET resolved_at = NULL, resolved_by = NULL, resolved_reason = NULL,
                   resolution_code = NULL, reopened_at = NOW(), reopened_by = $2,
                   version = version + 1
             WHERE id = $1
            RETURNING id, version, is_synthetic
            ''',
            event_id,
            user.get('email') or 'unknown',
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
    return {'ok': True, 'id': row['id'], 'outcome': 'updated', 'version': row['version']}


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
            SELECT id, vessel_id, local_id, seq, client_ts, nonce, created_at, acknowledged_at, acked_by,
                   eta_at, responder_status, responder_note,
                   fisher_reply, fisher_replied_at, resolved_at, resolution_code, version, reopened_at,
                   delivered_direct, delivered_via_buoy
            FROM sos_events
            WHERE vessel_id = $1
              AND (resolved_at IS NULL OR id IN (
                  SELECT id FROM sos_events WHERE vessel_id = $1 AND resolved_at IS NOT NULL
                  ORDER BY created_at DESC LIMIT 20
              ))
            ORDER BY created_at DESC
            ''',
            owned_vessel_id,
        )

    return {
        'vessel_id': owned_vessel_id,
        # Server time, so the handset can correct for clock drift before
        # rendering a countdown against eta_at.
        'server_time': datetime.now(UTC).isoformat(),
        'events': [_event_json(row) for row in rows],
    }


class ReplyIn(BaseModel):
    """The fisher's one-tap answer to an acknowledgement."""

    reply: int = Field(ge=1, le=2, description='1 STILL_IN_DANGER, 2 SAFE_NOW')


async def _apply_fisher_reply(conn: Any, row: Any, reply: int) -> Any:
    now = datetime.now(UTC)
    reopen = fisher_reply_reopens(row['resolved_at'], reply, now)
    if row['resolved_at'] is not None and not reopen:
        return row
    updated = await conn.fetchrow(
        '''
        UPDATE sos_events
           SET fisher_reply = $2::SMALLINT,
               fisher_replied_at = NOW(),
               resolved_at = CASE WHEN $2::SMALLINT = $3::SMALLINT THEN NOW() ELSE NULL END,
               resolution_code = CASE WHEN $2::SMALLINT = $3::SMALLINT THEN $5 ELSE NULL END,
               reopened_at = CASE WHEN $4::BOOLEAN THEN NOW() ELSE reopened_at END,
               reopened_by = CASE WHEN $4::BOOLEAN THEN 'fisher' ELSE reopened_by END,
               version = version + 1
         WHERE id = $1
        RETURNING id, fisher_reply, fisher_replied_at, resolved_at, resolution_code,
                  version, reopened_at, reopened_by
        ''',
        row['id'],
        reply,
        REPLY_SAFE_NOW,
        reopen,
        ResolutionCode.STOOD_DOWN_BY_FISHER.value,
    )
    if reopen:
        await record_audit_event(
            conn,
            actor=None,
            action='sos.reopen',
            resource_type='sos_event',
            resource_id=row['id'],
            outcome='updated',
            metadata={'reopened_by': 'fisher'},
            is_demo=row['is_synthetic'],
        )
    return updated


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
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT * FROM sos_events WHERE id = $1 AND vessel_id = $2 FOR UPDATE',
            event_id,
            device['vessel_id'],
        )
        row = await _apply_fisher_reply(conn, prior, payload.reply) if prior is not None else None
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
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow('SELECT * FROM sos_events WHERE local_id = $1 FOR UPDATE', local_id)
        row = await _apply_fisher_reply(conn, prior, payload.reply) if prior is not None else None
    if row is None:
        raise HTTPException(status_code=404, detail='no such SOS event')
    return {
        'ok': True,
        'id': row['id'],
        'fisher_reply': row['fisher_reply'],
        'fisher_replied_at': _iso(row['fisher_replied_at']),
        'resolved_at': _iso(row['resolved_at']),
    }
