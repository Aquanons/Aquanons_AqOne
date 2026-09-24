from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app.ai.anomaly_service import demo_evaluation_enabled, evaluate_and_persist
from app.db import get_pool

router = APIRouter(prefix='/api/ai/anomaly', tags=['anomaly'])

_SCORE_COLUMNS = '''
    vessel_id, trip_id, observed_at, last_contact_at, score, status,
    factors, expected_next_buoy_id, expected_window_start,
    expected_window_end, is_active, low_confidence, updated_at, is_synthetic
'''


def _score_response(row: Any, *, now: datetime) -> dict[str, object]:
    """Add the source/evaluated-at/data-age honesty metadata docs/38 Phase 2
    item 4 requires, without a schema change - is_synthetic and the two
    stored timestamps already carry everything needed.
    """
    data = dict(row)
    is_synthetic = data.pop('is_synthetic')
    data['source'] = 'synthetic' if is_synthetic else 'live'
    data['evaluated_at'] = data['observed_at']
    data['data_age_seconds'] = max(0.0, (now - data['last_contact_at']).total_seconds())
    data['monitoring'] = 'active' if data['data_age_seconds'] < 30 * 60 else 'unavailable'
    data['monitoring_reason'] = (
        None if data['monitoring'] == 'active' else 'No vessel contact in the last 30 minutes.'
    )
    return data


@router.get('/active')
async def active() -> list[dict[str, object]]:
    """Read-only (docs/38 Phase 2 / acceptance boundary): never evaluates or
    writes. Scoring happens only through POST /evaluate or the scheduled job
    (app/ai/run_anomaly_evaluation.py); this route just reads whatever the
    most recent evaluation persisted, so dashboard polling can never trigger
    a rebuild.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f'''
            SELECT {_SCORE_COLUMNS}
            FROM vessel_anomaly_scores
            WHERE is_active = TRUE
            ORDER BY score DESC, last_contact_at DESC
            '''
        )
    now = datetime.now(UTC)
    return [_score_response(row, now=now) for row in rows]


@router.get('/vessel/{vessel_id}')
async def vessel_detail(vessel_id: str) -> dict[str, object]:
    """Read-only, same as GET /active - see docs/38 Phase 2."""
    pool = get_pool()
    async with pool.acquire() as conn:
        profile_row = await conn.fetchrow(
            'SELECT profile_json, trip_count, low_confidence, rebuilt_at FROM vessel_profiles WHERE vessel_id = $1',
            vessel_id,
        )
        score_row = await conn.fetchrow(
            f'''
            SELECT {_SCORE_COLUMNS}
            FROM vessel_anomaly_scores
            WHERE vessel_id = $1
            ORDER BY updated_at DESC
            LIMIT 1
            ''',
            vessel_id,
        )
    if profile_row is None or score_row is None:
        raise HTTPException(status_code=404, detail='vessel not found')
    return {'profile': dict(profile_row), 'score': _score_response(score_row, now=datetime.now(UTC))}


@router.post('/evaluate')
async def evaluate() -> dict[str, object]:
    """The explicit write operation docs/38 Phase 2 item 4 calls for. Uses
    the server clock, never a client-supplied one - a dashboard operator can
    trigger a fresh evaluation, not choose what "now" means.
    """
    pool = get_pool()
    as_of = datetime.now(UTC)
    include_synthetic = demo_evaluation_enabled()
    async with pool.acquire() as conn:
        rows = await evaluate_and_persist(conn, as_of=as_of, include_synthetic=include_synthetic)
    return {
        'recomputed': len(rows),
        'statuses': sorted({row['status'] for row in rows}),
        'evaluated_at': as_of.isoformat(),
    }
