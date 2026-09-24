from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.auth import (
    RESPONDER_ROLES,
    bearer_scheme,
    decode_token,
    get_vessel_device_from_token,
    require_user,
)
from app.db import get_pool

router = APIRouter(prefix='/api/v1/trips', tags=['trips'])


class TripCreateIn(BaseModel):
    """Explicit vessel trip initiation or registration.

    Supports both pre-departure registration and fishermen already at sea
    (where departure_at is unknown/None).
    """

    trip_id: str = Field(min_length=1, max_length=64)
    vessel_id: str = Field(min_length=1, max_length=32)
    departure_at: datetime | None = None
    expected_return_at: datetime | None = None
    expected_checkin_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: Literal['open', 'completed', 'overdue', 'unresolved', 'cancelled'] = 'open'
    welfare_status: Literal['normal', 'safe', 'distress', 'unknown'] = 'unknown'
    reported_at: datetime | None = None
    reporter_id: str | None = Field(default=None, max_length=64)
    reporter_type: Literal['handset', 'gateway', 'responder', 'system'] = 'handset'
    vessel_type: str = Field(default='banca', max_length=32)
    vessel_length_m: float | None = Field(default=6.0, ge=1.0, le=50.0)
    vessel_draft_m: float | None = Field(default=0.4, ge=0.05, le=10.0)


class TripUpdateIn(BaseModel):
    """Voluntary trip amendment, welfare status change, or completion."""

    status: Literal['open', 'completed', 'overdue', 'unresolved', 'cancelled'] | None = None
    welfare_status: Literal['normal', 'safe', 'distress', 'unknown'] | None = None
    expected_return_at: datetime | None = None
    expected_checkin_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    reported_at: datetime | None = None
    amendment_note: str | None = Field(default=None, max_length=240)
    reporter_id: str | None = Field(default=None, max_length=64)
    reporter_type: Literal['handset', 'gateway', 'responder', 'system'] | None = None


def _serialise_trip(row: asyncpg.Record) -> dict[str, Any]:
    amendments = row['amendments']
    if isinstance(amendments, str):
        try:
            amendments = json.loads(amendments)
        except Exception:
            amendments = []
    return {
        'id': row['id'],
        'trip_id': row['trip_id'],
        'vessel_id': row['vessel_id'],
        'departure_at': row['departure_at'].isoformat() if row['departure_at'] else None,
        'expected_return_at': (
            row['expected_return_at'].isoformat() if row['expected_return_at'] else None
        ),
        'expected_checkin_interval_minutes': row['expected_checkin_interval_minutes'],
        'status': row['status'],
        'welfare_status': row['welfare_status'],
        'welfare_updated_at': row.get('welfare_updated_at').isoformat()
        if row.get('welfare_updated_at') else None,
        'reported_at': row['reported_at'].isoformat() if row['reported_at'] else None,
        'synced_at': row['synced_at'].isoformat(),
        'reporter_id': row['reporter_id'],
        'reporter_type': row['reporter_type'],
        'vessel_type': row['vessel_type'],
        'vessel_length_m': row['vessel_length_m'],
        'vessel_draft_m': row['vessel_draft_m'],
        'amendments': amendments if isinstance(amendments, list) else [],
        'created_at': row['created_at'].isoformat(),
        'updated_at': row['updated_at'].isoformat(),
    }


async def _authorize_mutation(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> tuple[str, dict[str, Any] | None]:
    """Authorize trip mutation by responder operator or vessel device.

    Returns (kind, device_dict_if_vessel). Raises 401 or 403 on authorization failure.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail='authentication required')

    claims = decode_token(credentials.credentials)
    kind = claims.get('kind', 'user')
    if kind == 'user':
        role = claims.get('role')
        if role not in RESPONDER_ROLES:
            raise HTTPException(status_code=403, detail='responder role required')
        return ('user', None)

    if kind == 'vessel_device':
        device = await get_vessel_device_from_token(credentials.credentials)
        if device is None:
            raise HTTPException(status_code=401, detail='device credential invalid or revoked')
        return ('vessel_device', device)

    raise HTTPException(status_code=401, detail='invalid token')


@router.post('', status_code=200)
async def create_or_register_trip(
    payload: TripCreateIn,
    auth: tuple[str, dict[str, Any] | None] = Depends(_authorize_mutation),
) -> dict[str, Any]:
    """Register or record an open/active vessel trip.

    Idempotent on trip_id: retries return existing record without overwriting.
    Allows departure_at to be NULL for fishers already at sea upon first upload.
    """
    kind, device = auth
    if (
        kind == 'vessel_device'
        and device is not None
        and device['vessel_id'] != payload.vessel_id
    ):
        raise HTTPException(
            status_code=403,
            detail='vessel device does not match trip vessel',
        )

    now = datetime.now(UTC)
    reported_at = payload.reported_at or now

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO vessels (id, boat_name)
            VALUES ($1, $1)
            ON CONFLICT (id) DO NOTHING
            """,
            payload.vessel_id,
        )

        row = await conn.fetchrow(
            """
            INSERT INTO vessel_trips (
              trip_id, vessel_id, departure_at, expected_return_at,
              expected_checkin_interval_minutes, status, welfare_status,
              welfare_updated_at, reported_at, synced_at, reporter_id, reporter_type,
              vessel_type, vessel_length_m, vessel_draft_m
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8,
                    $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (trip_id) DO NOTHING
            RETURNING *
            """,
            payload.trip_id,
            payload.vessel_id,
            payload.departure_at,
            payload.expected_return_at,
            payload.expected_checkin_interval_minutes,
            payload.status,
            payload.welfare_status,
            now if payload.welfare_status != 'unknown' else None,
            reported_at,
            now,
            payload.reporter_id,
            payload.reporter_type,
            payload.vessel_type,
            payload.vessel_length_m,
            payload.vessel_draft_m,
        )

        created = True
        if row is None:
            created = False
            row = await conn.fetchrow(
                'SELECT * FROM vessel_trips WHERE trip_id = $1', payload.trip_id
            )
            if row is None:
                raise HTTPException(status_code=500, detail='failed to create or retrieve trip')

    return {'created': created, 'trip': _serialise_trip(row)}


@router.patch('/{trip_id}', status_code=200)
async def update_trip(
    trip_id: str,
    payload: TripUpdateIn,
    auth: tuple[str, dict[str, Any] | None] = Depends(_authorize_mutation),
) -> dict[str, Any]:
    """Apply voluntary amendments, welfare status update, or completion to a trip."""
    kind, device = auth

    now = datetime.now(UTC)
    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow('SELECT * FROM vessel_trips WHERE trip_id = $1', trip_id)
        if existing is None:
            raise HTTPException(status_code=404, detail='trip not found')

        if (
            kind == 'vessel_device'
            and device is not None
            and device['vessel_id'] != existing['vessel_id']
        ):
            raise HTTPException(
                status_code=403,
                detail='vessel device does not match trip vessel',
            )

        # Build amendments entry if note supplied
        new_amendments = existing['amendments']
        if isinstance(new_amendments, str):
            try:
                new_amendments = json.loads(new_amendments)
            except Exception:
                new_amendments = []
        elif not isinstance(new_amendments, list):
            new_amendments = []

        if payload.amendment_note:
            new_amendments.append(
                {
                    'recorded_at': now.isoformat(),
                    'reported_at': (payload.reported_at or now).isoformat(),
                    'note': payload.amendment_note,
                    'reporter_id': payload.reporter_id,
                    'reporter_type': payload.reporter_type,
                }
            )

        updated_row = await conn.fetchrow(
            """
            UPDATE vessel_trips
               SET status = COALESCE($2, status),
                   welfare_status = COALESCE($3, welfare_status),
                   welfare_updated_at = CASE WHEN $3 IS NOT NULL THEN $7 ELSE welfare_updated_at END,
                   expected_return_at = COALESCE($4, expected_return_at),
                   expected_checkin_interval_minutes = COALESCE($5, expected_checkin_interval_minutes),
                   reported_at = COALESCE($6, reported_at),
                   synced_at = $7,
                   amendments = $8::jsonb,
                   updated_at = $7
             WHERE trip_id = $1
            RETURNING *
            """,
            trip_id,
            payload.status,
            payload.welfare_status,
            payload.expected_return_at,
            payload.expected_checkin_interval_minutes,
            payload.reported_at,
            now,
            json.dumps(new_amendments),
        )

    return {'trip': _serialise_trip(updated_row)}


@router.get('/{trip_id}', status_code=200)
async def get_trip(
    trip_id: str,
    _: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    """Get single trip by trip_id."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM vessel_trips WHERE trip_id = $1', trip_id)
        if row is None:
            raise HTTPException(status_code=404, detail='trip not found')
    return {'trip': _serialise_trip(row)}


@router.get('', status_code=200)
async def list_trips(
    vessel_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    """List trips with optional filtering by vessel_id or status."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
              FROM vessel_trips
             WHERE ($1::TEXT IS NULL OR vessel_id = $1)
               AND ($2::TEXT IS NULL OR status = $2)
             ORDER BY COALESCE(departure_at, created_at) DESC, id DESC
             LIMIT $3
            """,
            vessel_id,
            status,
            limit,
        )
    return {'trips': [_serialise_trip(r) for r in rows]}
