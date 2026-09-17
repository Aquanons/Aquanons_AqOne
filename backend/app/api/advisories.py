from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.audit import record_audit_event
from app.auth import require_responder_roles
from app.db import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/advisories', tags=['Advisories'])
public_router = APIRouter(prefix='/api/public/advisories', tags=['Advisories'])

VALID_PRIORITIES = {'Emergency', 'Warning', 'Information', 'Community'}
VALID_STATUSES = {'Draft', 'Published'}


class AdvisoryIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(default='Weather Advisory', max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    municipality: str = Field(default='All', max_length=80)
    priority: str = Field(default='Information')
    publish_date: date | None = None
    expiration_date: date | None = None
    cover_image: str | None = None
    status: str = Field(default='Published')


class DangerAlertPayload(BaseModel):
    id: str
    name: str
    score: int
    level: str
    trigger: str
    reasons: list[str]
    source: str
    observedAt: str


PHT = timezone(timedelta(hours=8))


def _today() -> date:
    return datetime.now(PHT).date()


def _normalise_payload(payload: AdvisoryIn) -> dict[str, Any]:
    priority = payload.priority.strip()
    status = payload.status.strip()
    if priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail='invalid advisory priority')
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail='invalid advisory status')
    if (
        payload.publish_date is not None
        and payload.expiration_date is not None
        and payload.expiration_date < payload.publish_date
    ):
        raise HTTPException(
            status_code=422,
            detail='expiration date cannot be before publish date',
        )

    return {
        'title': payload.title.strip(),
        'category': payload.category.strip() or 'Weather Advisory',
        'description': payload.description.strip(),
        'municipality': payload.municipality.strip() or 'All',
        'priority': priority,
        'publish_date': payload.publish_date or _today(),
        'expiration_date': payload.expiration_date,
        'cover_image': payload.cover_image,
        'status': status,
    }


def _serialise(row: Any) -> dict[str, Any]:
    return {
        'id': row['id'],
        'title': row['title'],
        'category': row['category'],
        'description': row['description'],
        'municipality': row['municipality'],
        'priority': row['priority'],
        'publish_date': row['publish_date'].isoformat(),
        'expiration_date': row['expiration_date'].isoformat()
        if row['expiration_date']
        else '',
        # The documented public field is `image_url` (docs/05_PUBLIC_API.md) -
        # `cover_image` is only the storage/operator-input name. Emitting one
        # canonical field here means the handset never has to guess which of
        # the two it will get.
        'image_url': row['cover_image'],
        'status': row['status'],
        'source': row['source'],
        'score': row['score'],
        'created_by': row['created_by'],
        'created_at': row['created_at'].isoformat(),
        'updated_at': row['updated_at'].isoformat(),
    }


async def _fetch_advisories(
    status: str | None = None,
    municipality: str | None = None,
    *,
    only_active: bool = False,
) -> list[dict[str, Any]]:
    """`only_active` additionally requires the advisory to have started and
    not yet expired. Used by the public route so an expired or future-dated
    notice can never reach the handset - see docs/05_PUBLIC_API.md.
    """
    pool = get_pool()
    today = _today()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT *
            FROM advisories
            WHERE ($1::TEXT IS NULL OR status = $1)
              AND (
                $2::TEXT IS NULL
                OR $2 = 'All'
                OR municipality = 'All'
                OR municipality = $2
              )
              AND (NOT $3::BOOLEAN OR publish_date <= $4)
              AND (NOT $3::BOOLEAN OR expiration_date IS NULL OR expiration_date >= $4)
            ORDER BY publish_date DESC, created_at DESC, id DESC
            LIMIT 100
            ''',
            status,
            municipality,
            only_active,
            today,
        )
    return [_serialise(row) for row in rows]


@router.get('')
async def get_advisories(
    status: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    _: Any = require_responder_roles,
) -> dict[str, list[dict[str, Any]]]:
    return {'advisories': await _fetch_advisories(status, municipality)}


@public_router.get('')
async def get_public_advisories(
    municipality: str | None = Query(default=None),
) -> dict[str, list[dict[str, Any]]]:
    return {
        'advisories': await _fetch_advisories(
            'Published', municipality, only_active=True
        )
    }


@router.get('/{advisory_id}')
async def get_advisory(
    advisory_id: int,
    _: Any = require_responder_roles,
) -> dict[str, dict[str, Any]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM advisories WHERE id = $1', advisory_id)
    if row is None:
        raise HTTPException(status_code=404, detail='advisory not found')
    return {'advisory': _serialise(row)}


@router.post('', status_code=201)
async def create_advisory(
    payload: AdvisoryIn,
    user: Any = require_responder_roles,
) -> dict[str, dict[str, Any]]:
    values = _normalise_payload(payload)
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            '''
            INSERT INTO advisories (
              title, category, description, municipality, priority,
              publish_date, expiration_date, cover_image, status,
              source, created_by
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'LGU',$10)
            RETURNING *
            ''',
            values['title'],
            values['category'],
            values['description'],
            values['municipality'],
            values['priority'],
            values['publish_date'],
            values['expiration_date'],
            values['cover_image'],
            values['status'],
            user.get('email') or user.get('id') or 'LGU',
        )
        # title/description are free text and never logged (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='advisory.create',
            resource_type='advisory',
            resource_id=row['id'],
            outcome='created',
            is_demo=row['demo_tag'] is not None,
            metadata={'status': values['status'], 'priority': values['priority']},
        )
    return {'advisory': _serialise(row)}


@router.put('/{advisory_id}')
async def update_advisory(
    advisory_id: int,
    payload: AdvisoryIn,
    user: Any = require_responder_roles,
) -> dict[str, dict[str, Any]]:
    values = _normalise_payload(payload)
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            '''
            UPDATE advisories
               SET title = $2,
                   category = $3,
                   description = $4,
                   municipality = $5,
                   priority = $6,
                   publish_date = $7,
                   expiration_date = $8,
                   cover_image = $9,
                   status = $10,
                   updated_at = NOW()
             WHERE id = $1
            RETURNING *
            ''',
            advisory_id,
            values['title'],
            values['category'],
            values['description'],
            values['municipality'],
            values['priority'],
            values['publish_date'],
            values['expiration_date'],
            values['cover_image'],
            values['status'],
        )
        if row is None:
            raise HTTPException(status_code=404, detail='advisory not found')
        # Unconditionally overwritten every call - a real edit each time,
        # not a retry to deduplicate (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='advisory.update',
            resource_type='advisory',
            resource_id=row['id'],
            outcome='updated',
            is_demo=row['demo_tag'] is not None,
            metadata={'status': values['status'], 'priority': values['priority']},
        )
    return {'advisory': _serialise(row)}


@router.delete('/{advisory_id}', status_code=204)
async def delete_advisory(
    advisory_id: int,
    user: Any = require_responder_roles,
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            'DELETE FROM advisories WHERE id = $1 RETURNING id, demo_tag', advisory_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail='advisory not found')
        await record_audit_event(
            conn,
            actor=user,
            action='advisory.delete',
            resource_type='advisory',
            resource_id=row['id'],
            outcome='deleted',
            is_demo=row['demo_tag'] is not None,
        )
    return None


@router.post('/alert')
async def trigger_danger_alert(
    payload: DangerAlertPayload,
    user: Any = require_responder_roles,
) -> dict[str, Any]:
    """Publish (or update) a danger-zone advisory. Dispatcher-authenticated.

    This previously had no auth dependency at all - not even `require_user` -
    despite publishing directly to `status: 'Published'`, which every
    unauthenticated caller of `GET /api/public/advisories` can see. Week 1
    Phase 4 audit (docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md)
    found no caller anywhere in this repo - not `web/js/dangerZonePredictor.js`
    (GET-only, talks to Open-Meteo, never posts here), not
    `web/js/advisoryService.js` (posts to `/api/advisories`, not `/alert`),
    nor any backend script. It was a live, unauthenticated
    publish-to-the-public-dashboard endpoint with no known legitimate caller.
    Gated behind `require_responder_roles` like every other write in
    this router (docs/41 Phase 1 action matrix); if a specific automated
    evaluator needs to call this without a dispatcher logged in, that needs
    its own documented service-account design, not an open endpoint.
    """
    try:
        observed_date = date.fromisoformat(payload.observedAt[:10])
    except ValueError:
        observed_date = _today()

    advisory_item = {
        'title': f'Alert: {payload.name}',
        'category': 'Weather Advisory',
        'description': f"{payload.trigger}. Reasons: {', '.join(payload.reasons)}",
        'municipality': 'All',
        'priority': 'Warning' if payload.level == 'watch' else 'Emergency',
        'publish_date': observed_date,
        'expiration_date': None,
        'cover_image': None,
        'status': 'Published',
        'source': payload.source,
        'score': payload.score,
        'source_key': f'danger-zone:{payload.id}',
    }

    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            '''
            INSERT INTO advisories (
              source_key, title, category, description, municipality, priority,
              publish_date, expiration_date, cover_image, status, source, score
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ON CONFLICT (source_key) DO UPDATE SET
              title = EXCLUDED.title,
              description = EXCLUDED.description,
              priority = EXCLUDED.priority,
              publish_date = EXCLUDED.publish_date,
              status = EXCLUDED.status,
              source = EXCLUDED.source,
              score = EXCLUDED.score,
              updated_at = NOW()
            RETURNING *, (xmax = 0) AS was_inserted
            ''',
            advisory_item['source_key'],
            advisory_item['title'],
            advisory_item['category'],
            advisory_item['description'],
            advisory_item['municipality'],
            advisory_item['priority'],
            advisory_item['publish_date'],
            advisory_item['expiration_date'],
            advisory_item['cover_image'],
            advisory_item['status'],
            advisory_item['source'],
            advisory_item['score'],
        )
        await record_audit_event(
            conn,
            actor=user,
            action='advisory.alert',
            resource_type='advisory',
            resource_id=row['id'],
            outcome='created' if row['was_inserted'] else 'updated',
            is_demo=row['demo_tag'] is not None,
            metadata={'level': payload.level, 'score': payload.score},
        )

    logger.warning(
        '[DANGER ALERT] %s scored %s/100 (%s)',
        payload.name,
        payload.score,
        payload.level,
    )

    return {'status': 'success', 'advisory': _serialise(row)}


class WarningDeliveryIn(BaseModel):
    """A delivery-state transition event for a warning (Task 2.5).

    States: generated -> gateway_accepted -> buoy_received -> phone_received -> user_acknowledged.
    """

    warning_id: int
    delivery_state: Literal[
        'generated',
        'gateway_accepted',
        'buoy_received',
        'phone_received',
        'user_acknowledged',
    ]
    vessel_id: str | None = None
    buoy_id: str | None = None
    occurred_at: datetime | None = None
    details: dict[str, Any] = {}

    @model_validator(mode='after')
    def validate_vessel_for_ack(self) -> WarningDeliveryIn:
        if self.delivery_state == 'user_acknowledged' and not self.vessel_id:
            raise ValueError('vessel_id is required for user_acknowledged delivery state')
        return self


@router.post('/delivery', status_code=200)
async def record_warning_delivery(payload: WarningDeliveryIn) -> dict[str, Any]:
    """Record a hop or acknowledgement event in the warning delivery lifecycle."""
    occurred_at = payload.occurred_at or datetime.now(UTC)
    pool = get_pool()
    async with pool.acquire() as conn:
        adv = await conn.fetchrow('SELECT id FROM advisories WHERE id = $1', payload.warning_id)
        if adv is None:
            raise HTTPException(status_code=404, detail='warning/advisory not found')

        # Check for duplicate delivery event (idempotency)
        existing = await conn.fetchrow(
            '''
            SELECT id, warning_id, delivery_state, occurred_at, recorded_at
              FROM warning_delivery_events
             WHERE warning_id = $1
               AND delivery_state = $2
               AND vessel_id IS NOT DISTINCT FROM $3
               AND buoy_id IS NOT DISTINCT FROM $4
            ''',
            payload.warning_id,
            payload.delivery_state,
            payload.vessel_id,
            payload.buoy_id,
        )
        if existing is not None:
            return {
                'accepted': True,
                'deduped': True,
                'delivery_id': existing['id'],
                'warning_id': existing['warning_id'],
                'delivery_state': existing['delivery_state'],
                'occurred_at': existing['occurred_at'].isoformat(),
                'recorded_at': existing['recorded_at'].isoformat(),
            }

        row = await conn.fetchrow(
            '''
            INSERT INTO warning_delivery_events (
              warning_id, vessel_id, buoy_id, delivery_state, occurred_at, details
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING id, warning_id, delivery_state, occurred_at, recorded_at
            ''',
            payload.warning_id,
            payload.vessel_id,
            payload.buoy_id,
            payload.delivery_state,
            occurred_at,
            json.dumps(payload.details),
        )

    return {
        'accepted': True,
        'deduped': False,
        'delivery_id': row['id'],
        'warning_id': row['warning_id'],
        'delivery_state': row['delivery_state'],
        'occurred_at': row['occurred_at'].isoformat(),
        'recorded_at': row['recorded_at'].isoformat(),
    }


@router.get('/{advisory_id}/deliveries', status_code=200)
async def get_warning_deliveries(advisory_id: int) -> dict[str, Any]:
    """Fetch the delivery events and reached states for a warning."""
    pool = get_pool()
    async with pool.acquire() as conn:
        adv = await conn.fetchrow('SELECT id FROM advisories WHERE id = $1', advisory_id)
        if adv is None:
            raise HTTPException(status_code=404, detail='advisory not found')

        rows = await conn.fetch(
            '''
            SELECT id, warning_id, vessel_id, buoy_id, delivery_state, occurred_at, recorded_at, details
              FROM warning_delivery_events
             WHERE warning_id = $1
             ORDER BY occurred_at ASC, id ASC
            ''',
            advisory_id,
        )

    events = [
        {
            'id': r['id'],
            'warning_id': r['warning_id'],
            'vessel_id': r['vessel_id'],
            'buoy_id': r['buoy_id'],
            'delivery_state': r['delivery_state'],
            'occurred_at': r['occurred_at'].isoformat(),
            'recorded_at': r['recorded_at'].isoformat(),
            'details': r['details'] if isinstance(r['details'], dict) else {},
        }
        for r in rows
    ]
    return {'warning_id': advisory_id, 'deliveries': events}
