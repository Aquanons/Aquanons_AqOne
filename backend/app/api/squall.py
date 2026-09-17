from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException

from app.ai.squall import (
    CALIBRATION,
    assess_array_quality,
    build_buoys,
    build_history,
    buoy_detail,
    current_detection,
    event_detection_summary,
    load_bundle,
    save_bundle,
    train_from_rows,
)
from app.db import get_pool

router = APIRouter(prefix='/api/ai/squall', tags=['squall'])

_TRUTHY = {'1', 'true', 'TRUE', 'yes', 'YES'}


async def _load_rows(
    conn, *, live: bool
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    is_synthetic = not live
    readings = await conn.fetch(
        '''
        SELECT buoy_id, observed_at, pressure_hpa
        FROM barometric_readings
        WHERE is_synthetic = $1
        ORDER BY observed_at, buoy_id
        ''',
        is_synthetic,
    )
    squalls = await conn.fetch(
        '''
        SELECT id, started_at, peak_at, ended_at, center_lat, center_lon,
               front_origin_lat, front_origin_lon, bearing_deg, speed_kph,
               pressure_drop_hpa, rise_minutes, hold_minutes, observed_buoy_ids
        FROM squall_events
        WHERE is_synthetic = $1
        ORDER BY started_at
        ''',
        is_synthetic,
    )
    buoys = await conn.fetch(
        '''
        SELECT id, lat, lon, contact_radius_m
        FROM buoys
        WHERE is_synthetic = $1
        ORDER BY id
        ''',
        is_synthetic,
    )
    return [dict(row) for row in readings], [dict(row) for row in squalls], [dict(row) for row in buoys]


def _return_now_enabled() -> bool:
    """Global safety clamp (docs/39 Phase 3), not yet the full Phase 4 gate.

    A live-sourced detection must not be able to alarm a handset before any
    field validation has happened. Phase 4 owns the actual approval process
    (named MDRRMO approver, recorded field-validation set) around this flag;
    this only needs the flag to exist and default off. Does not apply to the
    synthetic/demo route, which cannot reach a real handset.
    """
    return os.environ.get('SQUALL_RETURN_NOW_ENABLED') in _TRUTHY


def build_squall_status(
    readings: list[dict[str, object]],
    buoy_rows: list[dict[str, object]],
    *,
    source: Literal['live', 'synthetic'],
    allow_return_now: bool,
) -> dict[str, object]:
    """The one shared response shape for the dashboard, public, and demo
    squall routes (docs/39 Phase 3 item 1).

    Runs assess_array_quality() before any detection: an insufficient array
    (missing, stale, too few buoys, degenerate geometry) always reports
    `unknown` with a reason and the last real observation time, never a
    fabricated `clear` or an invented detection.
    """
    now = datetime.now(UTC)
    buoys = build_buoys(buoy_rows)
    history = build_history(readings)
    quality = assess_array_quality(history, buoys, now)

    data_age_seconds = (
        (now - quality.newest_observed_at).total_seconds() if quality.newest_observed_at is not None else None
    )
    base: dict[str, object] = {
        'source': source,
        'calibration': CALIBRATION,
        'observed_at': quality.newest_observed_at.isoformat() if quality.newest_observed_at else None,
        'generated_at': now.isoformat(),
        'data_age_seconds': data_age_seconds,
        'status_reason': quality.reason,
        'level': 'unknown',
        'return_now': False,
        'detections': [],
        'threshold': None,
        'triggered_buoys': [],
        'lead_minutes': None,
        'top_features': [],
        'evaluation': {},
    }

    if not quality.ok:
        return base

    try:
        model = load_bundle()
    except FileNotFoundError:
        return base | {'status_reason': 'squall model is not available'}

    qualifying_ids = set(quality.qualifying_buoy_ids)
    filtered_readings = [row for row in readings if str(row['buoy_id']) in qualifying_ids]
    filtered_buoy_rows = [row for row in buoy_rows if str(row['id']) in qualifying_ids]
    filtered_buoys = build_buoys(filtered_buoy_rows)

    detections = current_detection(filtered_readings, filtered_buoys, model)
    summary = event_detection_summary(model, detections)
    threshold = summary.get('threshold')
    detection_rows = summary.get('detections') or []

    triggered = [
        row
        for row in detection_rows
        if isinstance(threshold, (int, float)) and float(row.get('probability') or 0.0) >= float(threshold)
    ]

    status_reason = None
    if triggered:
        # Phase 4 Task 4.2 / Scenario C1:
        # Live detector cannot promote itself to an operational calibrated return instruction
        # if the model bundle is synthetic or unvalidated.
        bundle_calibration = getattr(model, 'calibration', None) or summary.get('calibration')
        is_synthetic_bundle = bundle_calibration == 'synthetic'
        if source == 'live' and is_synthetic_bundle:
            level = 'watch'
            status_reason = 'live squall capped at watch: empirical field validation pending'
        else:
            level = 'return_now' if allow_return_now else 'watch'
    elif detection_rows:
        level = 'watch'
    else:
        level = 'clear'

    triggered_buoys: list[str] = []
    lead_minutes: float | None = None
    for row in triggered:
        for arrival in row.get('arrival_by_buoy') or []:
            buoy_id = arrival.get('buoy_id')
            if buoy_id and buoy_id not in triggered_buoys:
                triggered_buoys.append(buoy_id)
            eta = arrival.get('arrival_minutes')
            if isinstance(eta, (int, float)):
                lead_minutes = eta if lead_minutes is None else min(lead_minutes, eta)

    return base | {
        'status_reason': status_reason,
        'level': level,
        'return_now': level == 'return_now',
        'detections': detection_rows,
        'threshold': threshold,
        'triggered_buoys': triggered_buoys,
        'lead_minutes': round(lead_minutes) if lead_minutes is not None else None,
        'top_features': summary.get('top_features') or [],
        'evaluation': summary.get('evaluation') or {},
    }


@router.get('/current')
async def current() -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        readings, _, buoy_rows = await _load_rows(conn, live=True)
    return build_squall_status(readings, buoy_rows, source='live', allow_return_now=_return_now_enabled())


@router.get('/buoy/{buoy_id}')
async def buoy(buoy_id: str) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        readings, _, buoy_rows = await _load_rows(conn, live=True)
    if not readings:
        raise HTTPException(status_code=404, detail='no pressure readings available')

    buoys = build_buoys(buoy_rows)
    if buoy_id not in buoys:
        raise HTTPException(status_code=404, detail='buoy not found')
    return buoy_detail(readings, buoy_id, buoys)


@router.post('/train')
async def train() -> dict[str, object]:
    if os.environ.get('ALLOW_TRAINING') not in _TRUTHY:
        raise HTTPException(status_code=403, detail='training disabled')

    pool = get_pool()
    async with pool.acquire() as conn:
        readings, squalls, buoy_rows = await _load_rows(conn, live=False)
    if not readings or not squalls:
        raise HTTPException(status_code=400, detail='insufficient synthetic data')

    model, evaluation = train_from_rows(readings, squalls, build_buoys(buoy_rows))
    save_bundle(model)
    return {'calibration': model.calibration, 'evaluation': evaluation, 'top_features': model.top_features}
