from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user, require_vessel_device
from app.db import get_pool

# Routes stay on their own router rather than under the blanket operator auth
# in main.py because these writes are now protected by a vessel-bound device
# credential, not by an MDRRMO operator token.
router = APIRouter(prefix='/api/catch-logs', tags=['catch'])

# The read side is dispatcher/reporting data and stays protected.
protected_router = APIRouter(prefix='/api/catch-logs', tags=['catch'])


class CatchLogIn(BaseModel):
    """A catch log as queued and uploaded by the handset.

    Carries only the quick estimate tapped at the moment of catching, never
    a confirmed weight - see `mobile/lib/models/catch_record.dart`'s doc
    comment. The real figure, once reweighed, arrives later through
    `ConfirmWeightIn` below, so this model has no `quantity_kg` field at all.

    `local_id` doubles as an idempotency key (mobile/lib/services/catch_service.dart
    retries an unconfirmed upload on the next sync tick), so a retried POST
    for the same local_id must not create a second row.

    Length caps mirror the handset's own clamps
    (`mobile/lib/models/catch_record.dart`: `maxCatchNoteLength = 240`) plus
    reasonable limits for the fields the mobile app never itself bounded.
    """

    vessel_id: str = Field(min_length=1, max_length=32)
    local_id: str | None = Field(default=None, max_length=64)
    species_name: str | None = Field(default=None, max_length=64)
    estimated_quantity_kg: float = Field(gt=0, le=100_000)
    catch_date: date
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    method: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=240)
    share_for_hotspots: bool = False


class ConfirmWeightIn(BaseModel):
    """A reweighed, confirmed figure for a catch already on file.

    Separate endpoint rather than a field on `CatchLogIn`, on purpose: the
    initial ingest above must never wait on or imply a firm weight, and a
    retried initial POST must never be able to clobber a confirmation that
    already landed - two different write paths keeps that impossible by
    construction rather than by convention.
    """

    quantity_kg: float = Field(gt=0, le=100_000)


@router.post('', status_code=200)
async def ingest_catch_log(
    payload: CatchLogIn,
    device: dict[str, object] = Depends(require_vessel_device),
) -> dict[str, object]:
    """Accept a catch log from the handset. Idempotent on local_id.

    Protected under Option A. The backend derives the owning vessel from the
    verified device credential and rejects a mismatched client-supplied
    vessel_id instead of trusting it.
    """
    owned_vessel_id = str(device['vessel_id'])
    if payload.vessel_id != owned_vessel_id:
        raise HTTPException(status_code=403, detail='device is not paired for that vessel')

    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            '''
                INSERT INTO vessels (id, boat_name)
                VALUES ($1, $1)
                ON CONFLICT (id) DO NOTHING
                ''',
            owned_vessel_id,
        )

        row = await conn.fetchrow(
            '''
                INSERT INTO catch_logs (
                  vessel_id, local_id, species_name, estimated_quantity_kg,
                  catch_date, latitude, longitude, method, notes,
                  share_for_hotspots
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (vessel_id, local_id) WHERE local_id IS NOT NULL DO UPDATE SET
                  -- A retried upload of the same local_id fills in whatever
                  -- was missing rather than overwriting what already landed.
                  -- Never touches quantity_kg/quantity_confirmed - those are
                  -- only ever written by confirm_weight below.
                  species_name = COALESCE(catch_logs.species_name, EXCLUDED.species_name),
                  method       = COALESCE(catch_logs.method, EXCLUDED.method),
                  notes        = COALESCE(catch_logs.notes, EXCLUDED.notes),
                  share_for_hotspots = EXCLUDED.share_for_hotspots
                RETURNING id, created_at, (xmax = 0) AS was_inserted
                ''',
            owned_vessel_id,
            payload.local_id,
            payload.species_name,
            payload.estimated_quantity_kg,
            payload.catch_date,
            payload.latitude,
            payload.longitude,
            payload.method,
            payload.notes,
            payload.share_for_hotspots,
        )

    return {
        'catch_log': {
            'id': row['id'],
            'created': bool(row['was_inserted']),
            'duplicate': not bool(row['was_inserted']),
            'created_at': row['created_at'].isoformat(),
        }
    }


@router.post('/{catch_log_id}/confirm-weight')
async def confirm_weight(
    catch_log_id: int,
    payload: ConfirmWeightIn,
    device: dict[str, object] = Depends(require_vessel_device),
) -> dict[str, object]:
    """Records the real, reweighed figure for a catch already on file.

    Protected under Option A, and restricted to the token's own vessel rows.
    Idempotent by construction: confirming the same catch again just
    overwrites with whatever the handset now believes is correct.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            UPDATE catch_logs
               SET quantity_kg           = $2,
                   quantity_confirmed    = TRUE,
                   quantity_confirmed_at = NOW()
             WHERE id = $1
               AND vessel_id = $3
            RETURNING id, quantity_kg, quantity_confirmed, quantity_confirmed_at
            ''',
            catch_log_id,
            payload.quantity_kg,
            device['vessel_id'],
        )
    if row is None:
        raise HTTPException(status_code=404, detail='no such catch log')
    return {
        'catch_log': {
            'id': row['id'],
            'quantity_kg': row['quantity_kg'],
            'quantity_confirmed': row['quantity_confirmed'],
            'quantity_confirmed_at': row['quantity_confirmed_at'].isoformat(),
        }
    }


@protected_router.get('')
async def list_catch_logs(
    vessel_id: str | None = None,
    limit: int = 100,
    _: dict = Depends(require_user),
) -> dict[str, object]:
    """Dispatcher/reporting view. Optionally filtered to one vessel."""
    pool = get_pool()
    capped_limit = max(1, min(limit, 500))
    columns = '''id, vessel_id, species_name, estimated_quantity_kg, quantity_kg,
                 quantity_confirmed, catch_date, latitude, longitude, method,
                 notes, created_at'''
    async with pool.acquire() as conn:
        if vessel_id:
            rows = await conn.fetch(
                f'''
                SELECT {columns}
                FROM catch_logs
                WHERE vessel_id = $1
                ORDER BY catch_date DESC, created_at DESC
                LIMIT $2
                ''',
                vessel_id,
                capped_limit,
            )
        else:
            rows = await conn.fetch(
                f'''
                SELECT {columns}
                FROM catch_logs
                ORDER BY catch_date DESC, created_at DESC
                LIMIT $1
                ''',
                capped_limit,
            )
    return {
        'catch_logs': [
            {
                **{k: v for k, v in dict(row).items() if k not in ('catch_date', 'created_at')},
                'catch_date': row['catch_date'].isoformat(),
                'created_at': row['created_at'].isoformat(),
            }
            for row in rows
        ]
    }
