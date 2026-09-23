from __future__ import annotations

from datetime import datetime
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.contacts import (
    reject_future_clock_skew,
    require_gateway_key,
    require_synthetic_demo_gate,
)
from app.db import get_pool

router = APIRouter(prefix='/api/v1', tags=['current-events'])

# Physical-plausibility guard on current speeds (up to 5 m/s)
_MAX_CURRENT_SPEED_MPS = 5.0


class CurrentEventIn(BaseModel):
    """One buoy current observation, from the gateway only.

    event_id is the idempotency key - a retried submission must return the
    original reading, never create a second one.
    """

    v: int = 1
    event_id: str = Field(min_length=1, max_length=128)
    buoy_id: str = Field(min_length=1, max_length=32)
    observed_at: datetime
    observed_u_mps: float = Field(ge=-_MAX_CURRENT_SPEED_MPS, le=_MAX_CURRENT_SPEED_MPS)
    observed_v_mps: float = Field(ge=-_MAX_CURRENT_SPEED_MPS, le=_MAX_CURRENT_SPEED_MPS)
    depth_m: float = Field(default=1.0, ge=0.0, le=100.0)
    source: Literal['live', 'synthetic']
    calibration_status: Literal['qualified', 'uncalibrated', 'synthetic'] = 'uncalibrated'

    @field_validator('observed_at')
    @classmethod
    def _reject_future_clock_skew(cls, value: datetime) -> datetime:
        return reject_future_clock_skew(value)


@router.post('/current-events', dependencies=[Depends(require_gateway_key)], status_code=200)
async def ingest_current_event(
    payload: CurrentEventIn,
    x_demo_key: str | None = Header(default=None, alias='X-Demo-Key'),
) -> dict[str, object]:
    """Accept one physical or synthetic current reading. Idempotent on event_id.

    Preserves occurrence time (observed_at) and marks created_at as receipt time.
    """
    if payload.source == 'synthetic':
        await require_synthetic_demo_gate(x_demo_key, 'current')

    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                '''
                INSERT INTO current_observations (
                  event_id, buoy_id, observed_at, observed_u_mps, observed_v_mps,
                  depth_m, source, calibration_status, is_synthetic
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (event_id) WHERE event_id IS NOT NULL DO NOTHING
                RETURNING id, event_id, buoy_id, source, calibration_status
                ''',
                payload.event_id,
                payload.buoy_id,
                payload.observed_at,
                payload.observed_u_mps,
                payload.observed_v_mps,
                payload.depth_m,
                payload.source,
                payload.calibration_status,
                payload.source == 'synthetic',
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(status_code=400, detail='unknown buoy_id') from exc

        deduped = row is None
        if row is None:
            row = await conn.fetchrow(
                '''
                SELECT id, event_id, buoy_id, source, calibration_status
                FROM current_observations
                WHERE event_id = $1
                ''',
                payload.event_id,
            )

    return {
        'accepted': True,
        'event_id': row['event_id'],
        'deduped': deduped,
        'observation_id': row['id'],
        'buoy_id': row['buoy_id'],
        'source': row['source'],
        'calibration_status': row['calibration_status'],
    }
