"""Buoy-measured current-field estimator for drift prediction.

Loads the most recent ``current_observations`` from the database once, then
returns a synchronous callable that interpolates the observed current at any
particle position and time.  Particles outside the buoy array fall back to the
synthetic current field so the model never pretends the array covers the whole
ocean.

Interpolation is inverse-distance weighting in space and linear interpolation
in time between the two bracketing observations for each buoy.  The factory
reports the fraction of particle-steps that used real observations versus
fallback so the dashboard can surface how much of the prediction was
array-driven.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import asyncpg
import numpy as np

from app.ai.drift import _synthetic_current_vector

IDW_POWER = 2.0
MAX_RADIUS_M = 111_000.0
MAX_AGE_SECONDS = 3600.0


def _haversine_m(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    """Vectorised haversine distance in metres from arrays to a single point."""
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat1_rad - lat2_rad
    dlon = lon1_rad - lon2_rad
    a = np.sin(dlat / 2.0) ** 2 + math.cos(lat2_rad) * np.cos(lat1_rad) * np.sin(dlon / 2.0) ** 2
    return 6_371_000.0 * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


async def _load_buoy_observations(
    conn: asyncpg.Connection,
    include_synthetic: bool = False,
    as_of: datetime | None = None,
    max_depth_m: float = 2.5,
) -> dict[str, dict[str, Any]]:
    """Load buoy positions and their observation time-series from the DB.

    Only ``observed_u_mps`` / ``observed_v_mps`` are loaded.  The ``true_*``
    columns are never selected.
    Synthetic rows are excluded unless ``include_synthetic=True``.
    Uncalibrated and deep currents are excluded for surface drift.
    Observations arriving or observed after ``as_of`` are excluded to prevent future leakage in replay.
    """
    conditions = ["b.lat IS NOT NULL", "b.lon IS NOT NULL"]
    args: list[Any] = []
    if not include_synthetic:
        conditions.append("(co.is_synthetic = FALSE AND (co.source IS NULL OR co.source = 'live'))")
        conditions.append("(co.calibration_status IS NULL OR co.calibration_status = 'qualified')")
    if max_depth_m is not None:
        conditions.append(f"(co.depth_m IS NULL OR co.depth_m <= {float(max_depth_m)})")
    if as_of is not None:
        args.append(as_of)
        conditions.append(f"co.observed_at <= ${len(args)}")
        args.append(as_of)
        conditions.append(f"(co.created_at IS NULL OR co.created_at <= ${len(args)})")

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT b.id AS buoy_id,
               b.lat AS buoy_lat,
               b.lon AS buoy_lon,
               co.observed_at,
               co.observed_u_mps,
               co.observed_v_mps,
               co.depth_m,
               co.source,
               co.calibration_status,
               co.created_at
        FROM current_observations co
        JOIN buoys b ON b.id = co.buoy_id
        WHERE {where_clause}
        ORDER BY co.observed_at
    """
    rows = await conn.fetch(query, *args)
    buoys: dict[str, dict[str, Any]] = {}
    for row in rows:
        r = dict(row)
        depth = r.get('depth_m')
        if max_depth_m is not None and depth is not None and float(depth) > max_depth_m:
            continue

        if not include_synthetic:
            if r.get('is_synthetic') is True or r.get('source') == 'synthetic':
                continue
            if r.get('calibration_status') is not None and r.get('calibration_status') != 'qualified':
                continue

        if as_of is not None:
            created_at = r.get('created_at')
            if created_at is not None and created_at > as_of:
                continue
            observed_at = r.get('observed_at')
            if observed_at is not None and observed_at > as_of:
                continue

        bid = r['buoy_id']
        if bid not in buoys:
            buoys[bid] = {
                'lat': float(r['buoy_lat']),
                'lon': float(r['buoy_lon']),
                'times': [],
                'u': [],
                'v': [],
            }
        obs_at = r['observed_at']
        if hasattr(obs_at, 'timestamp'):
            buoys[bid]['times'].append(obs_at.timestamp())
        else:
            buoys[bid]['times'].append(float(obs_at))
        buoys[bid]['u'].append(float(r['observed_u_mps']))
        buoys[bid]['v'].append(float(r['observed_v_mps']))
    for buoy in buoys.values():
        buoy['times'] = np.array(buoy['times'], dtype=float)
        buoy['u'] = np.array(buoy['u'], dtype=float)
        buoy['v'] = np.array(buoy['v'], dtype=float)
    return buoys


async def count_nearby_fresh_buoys(
    pool: asyncpg.Pool,
    lat: float,
    lon: float,
    at: datetime,
    include_synthetic: bool = False,
    max_depth_m: float = 2.5,
    min_separation_m: float = 0.0,
) -> int:
    """How many distinct buoys have a qualified surface observation within
    ``MAX_RADIUS_M`` of ``(lat, lon)`` and within ``MAX_AGE_SECONDS`` of
    ``at``.

    The field-geometry half of the docs/40 Phase 2 production quality gate.
    One buoy gives a single point value, not a spatial gradient - a
    production run needs more than one to interpolate a direction rather
    than extrapolate blindly from a lone reading. Co-located buoys (within
    ``min_separation_m``) are deduplicated so they do not falsely masquerade
    as 2D spatial support.
    Observations after ``at`` are excluded.
    """
    async with pool.acquire() as conn:
        buoys = await _load_buoy_observations(
            conn, include_synthetic=include_synthetic, as_of=at, max_depth_m=max_depth_m,
        )

    target_time = at.astimezone(UTC).timestamp()
    qualifying: list[dict[str, Any]] = []
    for buoy in buoys.values():
        if len(buoy['times']) == 0:
            continue
        dist_m = _haversine_m(np.array([lat]), np.array([lon]), buoy['lat'], buoy['lon'])[0]
        if dist_m >= MAX_RADIUS_M:
            continue
        nearest_age = float(np.min(np.abs(buoy['times'] - target_time)))
        if nearest_age <= MAX_AGE_SECONDS:
            qualifying.append(buoy)

    if min_separation_m <= 0.0:
        return len(qualifying)

    retained: list[dict[str, Any]] = []
    for candidate in qualifying:
        c_lat = candidate['lat']
        c_lon = candidate['lon']
        is_colocated = False
        for r in retained:
            sep_m = _haversine_m(np.array([c_lat]), np.array([c_lon]), r['lat'], r['lon'])[0]
            if sep_m < min_separation_m:
                is_colocated = True
                break
        if not is_colocated:
            retained.append(candidate)
    return len(retained)


async def create_current_field_factory(
    pool: asyncpg.Pool,
    include_synthetic: bool = False,
    allow_synthetic: bool = True,
    as_of: datetime | None = None,
    max_depth_m: float = 2.5,
) -> Callable[[np.ndarray, np.ndarray, datetime], tuple[np.ndarray, np.ndarray]]:
    """Load observations once and return a vectorised current-field callable.

    The returned callable matches the contract expected by
    :func:`app.ai.drift.predict_drift`'s ``current_vector_fn`` parameter:
    ``(lat_array, lon_array, timestamp) -> (u_mps, v_mps)``.

    If ``allow_synthetic=False`` (for real-case production runs), particles without
    qualifying observations receive zero velocity and are counted as unobserved,
    ensuring synthetic fallback never masquerades as observation-driven drift.
    Whole-run observation fraction is tracked across all particle steps.
    """
    async with pool.acquire() as conn:
        buoys = await _load_buoy_observations(
            conn, include_synthetic=include_synthetic, as_of=as_of, max_depth_m=max_depth_m,
        )

    buoy_list = list(buoys.values())
    n_buoys = len(buoy_list)

    if n_buoys == 0:
        if allow_synthetic:
            def _empty_field(
                lat: np.ndarray, lon: np.ndarray, at: datetime,
            ) -> tuple[np.ndarray, np.ndarray]:
                return _synthetic_current_vector(lat, lon, at)
            _empty_field.observation_fraction = 0.0  # type: ignore[attr-defined]
            _empty_field.support_lost_at = None  # type: ignore[attr-defined]
            return _empty_field
        else:
            def _zero_field(
                lat: np.ndarray, lon: np.ndarray, at: datetime,
            ) -> tuple[np.ndarray, np.ndarray]:
                n = len(lat)
                return np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            _zero_field.observation_fraction = 0.0  # type: ignore[attr-defined]
            _zero_field.support_lost_at = None  # type: ignore[attr-defined]
            return _zero_field

    buoy_lats = np.array([b['lat'] for b in buoy_list], dtype=float)
    buoy_lons = np.array([b['lon'] for b in buoy_list], dtype=float)
    buoy_times = [b['times'] for b in buoy_list]
    buoy_u = [b['u'] for b in buoy_list]
    buoy_v = [b['v'] for b in buoy_list]

    total_particles = 0
    total_observed = 0

    def _estimated_field(
        lat: np.ndarray, lon: np.ndarray, at: datetime,
    ) -> tuple[np.ndarray, np.ndarray]:
        nonlocal total_particles, total_observed
        n = len(lat)
        target_time = at.astimezone(UTC).timestamp()
        u_out = np.zeros(n, dtype=float)
        v_out = np.zeros(n, dtype=float)
        weights = np.zeros(n, dtype=float)

        for i in range(n_buoys):
            dist_m = _haversine_m(lat, lon, buoy_lats[i], buoy_lons[i])
            in_range = dist_m < MAX_RADIUS_M
            if not np.any(in_range):
                continue

            spatial_w = np.where(
                in_range,
                1.0 / np.power(np.maximum(dist_m, 1.0), IDW_POWER),
                0.0,
            )

            times_i = buoy_times[i]
            diffs = np.abs(times_i - target_time)
            nearest_idx = int(np.argmin(diffs))
            nearest_age = diffs[nearest_idx]

            if nearest_age > MAX_AGE_SECONDS:
                continue

            if len(times_i) >= 2:
                sorted_idx = int(np.searchsorted(times_i, target_time))
                if sorted_idx == 0:
                    obs_u = buoy_u[i][0]
                    obs_v = buoy_v[i][0]
                elif sorted_idx >= len(times_i):
                    obs_u = buoy_u[i][-1]
                    obs_v = buoy_v[i][-1]
                else:
                    t0 = times_i[sorted_idx - 1]
                    t1 = times_i[sorted_idx]
                    alpha = (target_time - t0) / (t1 - t0) if t1 != t0 else 0.0
                    obs_u = buoy_u[i][sorted_idx - 1] * (1.0 - alpha) + buoy_u[i][sorted_idx] * alpha
                    obs_v = buoy_v[i][sorted_idx - 1] * (1.0 - alpha) + buoy_v[i][sorted_idx] * alpha
            else:
                obs_u = buoy_u[i][0]
                obs_v = buoy_v[i][0]

            temporal_w = max(0.0, 1.0 - nearest_age / MAX_AGE_SECONDS)
            combined = spatial_w * temporal_w

            u_out += combined * obs_u
            v_out += combined * obs_v
            weights += combined

        has_obs = weights > 0.0
        n_observed = int(np.sum(has_obs))
        u_out[has_obs] /= weights[has_obs]
        v_out[has_obs] /= weights[has_obs]

        if n_observed < n:
            if allow_synthetic:
                synthetic_u, synthetic_v = _synthetic_current_vector(lat[~has_obs], lon[~has_obs], at)
                u_out[~has_obs] = synthetic_u
                v_out[~has_obs] = synthetic_v
            else:
                u_out[~has_obs] = 0.0
                v_out[~has_obs] = 0.0

        if n > 0 and n_observed == 0 and _estimated_field.support_lost_at is None:
            _estimated_field.support_lost_at = at

        total_particles += n
        total_observed += n_observed
        _estimated_field.observation_fraction = (
            total_observed / total_particles if total_particles > 0 else 0.0
        )  # type: ignore[attr-defined]
        return u_out, v_out

    _estimated_field.support_lost_at = None  # type: ignore[attr-defined]
    _estimated_field.observation_fraction = 0.0  # type: ignore[attr-defined]
    return _estimated_field
