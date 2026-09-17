from __future__ import annotations

import asyncio
import json
import math
import os
from typing import Any

import asyncpg

from app.ai.current_field import create_current_field_factory
from app.ai.drift import (
    ObjectClass,
    _synthetic_wind_series,
    contour_contains,
    predict_drift,
)
from app.ai.eval_store import write_section


def _incident_class(abnormal_reason: str) -> ObjectClass:
    if abnormal_reason in {'capsize', 'adverse_weather'}:
        return ObjectClass.swamped_banca
    return ObjectClass.intact_hull_adrift


async def _load_incidents(database_url: str) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch(
            '''
            SELECT id, vessel_id, last_contact_at, last_contact_lat, last_contact_lon,
                   abnormal_reason, true_track
            FROM incidents
            WHERE is_synthetic = TRUE
            ORDER BY id
            '''
        )
    finally:
        await conn.close()
    return list(rows)


async def main() -> None:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL is required')

    incidents = await _load_incidents(database_url)
    if not incidents:
        print('containment_rate: 0.000%')
        print('search_area_reduction_factor: 0.00x')
        print('prediction_runtime_ms: 0.000')
        return

    try:
        pool = await asyncpg.create_pool(database_url)
    except Exception:
        pool = None

    current_fn = None
    if pool is not None:
        try:
            current_fn = await create_current_field_factory(pool)
        except Exception:
            current_fn = None

    contained = 0
    excluded_low_quality = 0
    area_factors: list[float] = []
    runtimes: list[float] = []
    observation_fractions: list[float] = []
    for row in incidents:
        track = row['true_track']
        if isinstance(track, str):
            track = json.loads(track)
        if len(track) < 2:
            # A single-point track carries no drift distance to evaluate
            # containment or area reduction against - not evidence either
            # way, so it is excluded rather than silently dropped from the
            # denominator (docs/40 Phase 5 item 1 "excluded low-quality
            # runs").
            excluded_low_quality += 1
            continue

        forecast_hours = (len(track) - 1) * 0.5

        predict_kwargs: dict[str, object] = dict(
            last_lat=float(row['last_contact_lat']),
            last_lon=float(row['last_contact_lon']),
            observed_at=row['last_contact_at'],
            object_class=_incident_class(str(row['abnormal_reason'])),
            forecast_hours=forecast_hours,
            wind_provider=_synthetic_wind_series,
        )
        if current_fn is not None:
            predict_kwargs['current_vector_fn'] = current_fn

        prediction = predict_drift(**predict_kwargs)  # type: ignore[arg-type]
        runtimes.append(prediction.runtime_ms)
        true_point = track[-1]
        if contour_contains(prediction.contours[-1], float(true_point['lat']), float(true_point['lon'])):
            contained += 1
        area_factors.append(
            _area_reduction_factor(
                prediction,
                forecast_hours,
            )
        )
        if current_fn is not None:
            observation_fractions.append(getattr(current_fn, 'observation_fraction', 0.0))

    if pool is not None:
        await pool.close()

    evaluated = len(incidents) - excluded_low_quality
    if evaluated == 0:
        print('containment_rate: n/a (0 incidents cleared the minimum track length)')
        print(f'excluded_low_quality_runs: {excluded_low_quality}')
        return

    containment_rate = contained / evaluated
    reduction_factor = sum(area_factors) / len(area_factors)
    runtime_ms = sum(runtimes) / len(runtimes)
    avg_obs_fraction = sum(observation_fractions) / len(observation_fractions) if observation_fractions else 0.0
    print(f'containment_rate: {containment_rate:.3%}')
    print(f'search_area_reduction_factor: {reduction_factor:.2f}x')
    print(f'prediction_runtime_ms: {runtime_ms:.3f}')
    print(f'observation_fraction: {avg_obs_fraction:.3%}')
    print(f'excluded_low_quality_runs: {excluded_low_quality}')
    write_section(
        'drift',
        {
            'containment_rate': containment_rate,
            'search_area_reduction_factor': reduction_factor,
            'prediction_runtime_ms': runtime_ms,
            'incidents_evaluated': evaluated,
            'excluded_low_quality_runs': excluded_low_quality,
            'observation_fraction': avg_obs_fraction,
        },
    )


MAX_DRIFT_SPEED_MPS = 1.5  # Physical maximum coastal current+wind envelope (~3 knots)
EVAL_HORIZONS = [1.0, 3.0, 6.0, 12.0, 24.0]


def _independent_baseline_area_m2(forecast_hours: float) -> float:
    """Independently specified maximum-speed search envelope area (pi * (v_max * t)^2)."""
    radius_m = MAX_DRIFT_SPEED_MPS * (forecast_hours * 3600.0)
    return 3.141592653589793 * radius_m * radius_m


def _area_reduction_factor(prediction, forecast_hours: float) -> float:
    baseline_area = _independent_baseline_area_m2(forecast_hours)
    contour = prediction.contours[-1]['geometry']['coordinates'][0]
    area = abs(_polygon_area_m2(contour))
    if area <= 1e-9:
        return 1.0
    return baseline_area / area


def _polygon_area_m2(ring: list[list[float]]) -> float:
    if len(ring) < 4:
        return 0.0
    lon0, lat0 = ring[0]
    x = []
    y = []
    for lon, lat in ring:
        x.append((lon - lon0) * 111_320.0)
        y.append((lat - lat0) * 110_574.0)
    area = 0.0
    for i in range(len(ring) - 1):
        area += x[i] * y[i + 1] - x[i + 1] * y[i]
    return abs(area) / 2.0


def evaluate_drift_track(
    prediction: Any,
    true_track: list[dict[str, Any]],
    horizon_hours: float,
) -> dict[str, Any]:
    """Evaluate containment, area, and miss distance for a true track at horizon_hours."""
    if not true_track:
        return {
            'contained': False,
            'is_supported': False,
            'miss_distance_m': None,
            'area_m2': 0.0,
            'reduction_factor': 0.0,
        }

    supported_horizon = getattr(prediction, 'supported_horizon_hours', None)
    if supported_horizon is None and isinstance(prediction, dict):
        supported_horizon = prediction.get('supported_horizon_hours')

    is_supported = True
    if supported_horizon is not None and horizon_hours > float(supported_horizon):
        is_supported = False

    contours = getattr(prediction, 'contours', None)
    if contours is None and isinstance(prediction, dict):
        contours = prediction.get('contours', [])

    if not contours:
        return {
            'contained': False,
            'is_supported': is_supported,
            'miss_distance_m': None,
            'area_m2': 0.0,
            'reduction_factor': 0.0,
        }

    outer_contour = contours[-1]
    ring = outer_contour['geometry']['coordinates'][0]
    area_m2 = abs(_polygon_area_m2(ring))
    reduction = _independent_baseline_area_m2(horizon_hours) / area_m2 if area_m2 > 1e-9 else 1.0

    target_point = true_track[-1]
    t_lat = float(target_point['lat'])
    t_lon = float(target_point['lon'])

    contained = contour_contains(outer_contour, t_lat, t_lon) if is_supported else False

    miss_distance_m = 0.0
    if not contained:
        min_dist = float('inf')
        for lon, lat in ring:
            dx = (lon - t_lon) * 111_320.0 * math.cos(math.radians(t_lat))
            dy = (lat - t_lat) * 110_574.0
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
        miss_distance_m = min_dist

    return {
        'contained': contained,
        'is_supported': is_supported,
        'miss_distance_m': miss_distance_m,
        'area_m2': area_m2,
        'reduction_factor': reduction,
    }


if __name__ == '__main__':
    asyncio.run(main())
