from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from app.ai.anomaly_service import demo_evaluation_enabled, evaluate_and_persist
from app.db import get_pool

router = APIRouter(prefix='/api/ai/anomaly', tags=['anomaly'])
MONITORING_WINDOW = timedelta(minutes=30)

_SCORE_COLUMNS = '''
    vessel_id, trip_id, observed_at, last_contact_at, score, status,
    factors, expected_next_buoy_id, expected_window_start,
    expected_window_end, is_active, low_confidence, updated_at, is_synthetic
'''


# The model stores each factor as {name, explanation, ...}; docs/05 "Factor
# object" names them {code, description, ...}. Mapped here, at the boundary, so
# the stored rows and app/ai keep their own vocabulary.
_CONTRACT_KEYS = {'name': 'code', 'explanation': 'description'}


def contract_factors(stored: Any) -> list[dict[str, object]]:
    """A stored factor list (asyncpg returns jsonb as text) as docs/05 factor objects."""
    factors = json.loads(stored) if isinstance(stored, str) else stored
    return [{_CONTRACT_KEYS.get(key, key): value for key, value in factor.items()} for factor in factors or []]


def _score_response(row: Any, *, now: datetime) -> dict[str, object]:
    """Add the source/evaluated-at/data-age honesty metadata docs/38 Phase 2
    item 4 requires, without a schema change - is_synthetic and the two
    stored timestamps already carry everything needed.
    """
    data = dict(row)
    is_synthetic = data.pop('is_synthetic')
    data['source'] = 'synthetic' if is_synthetic else 'live'
    data['factors'] = contract_factors(data['factors'])
    data['evaluated_at'] = data['observed_at']
    data['data_age_seconds'] = max(0.0, (now - data['last_contact_at']).total_seconds())
    return data


@router.get('/active')
async def active() -> dict[str, object]:
    """Read-only (docs/38 Phase 2 / acceptance boundary): never evaluates or
    writes. Scoring happens only through POST /evaluate or the scheduled job
    (app/ai/run_anomaly_evaluation.py); this route just reads whatever the
    most recent evaluation persisted, so dashboard polling can never trigger
    a rebuild.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        has_live_contact = await conn.fetchval(
            '''
            SELECT EXISTS (
                SELECT 1
                FROM buoy_contacts
                WHERE source = 'live'
                  AND is_synthetic IS FALSE
                  AND contact_via <> 'handset'
                  AND observed_at >= NOW() - $1::interval
            )
            ''',
            MONITORING_WINDOW,
        )
        rows = await conn.fetch(
            f'''
            SELECT {_SCORE_COLUMNS}
            FROM vessel_anomaly_scores
            WHERE is_active = TRUE
            ORDER BY score DESC, last_contact_at DESC
            '''
        )
    now = datetime.now(UTC)
    return {
        'rows': [_score_response(row, now=now) for row in rows],
        'monitoring': 'active' if has_live_contact else 'unavailable',
        'monitoring_reason': None if has_live_contact else 'No live vessel contact in the last 30 minutes.',
    }


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
