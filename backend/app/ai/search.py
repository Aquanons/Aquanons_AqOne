"""Bayesian search allocation: update the posterior probability grid.

When a sector is searched and the target is not found, the probability mass
in that sector is reduced by the detection probability and the grid is
renormalised.  This is the standard Bayesian update used in operational SAR
(SAROPS, COSTAS).

The grid is the state — the particle simulation is not re-run on each update.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

from app.ai.drift import _contour_polygon, _to_latlon, _to_xy


def _normalize_dt(dt: datetime | str) -> datetime:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    return dt.astimezone(UTC)


def _grid_from_dict(grid_dict: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Deserialize a DensityGrid dict into numpy arrays.

    Returns (values, x_edges, y_edges, origin_lat, origin_lon).
    """
    values = np.array(grid_dict['values'], dtype=float)
    x_edges = np.array(grid_dict['x_edges_m'], dtype=float)
    y_edges = np.array(grid_dict['y_edges_m'], dtype=float)
    origin = grid_dict['origin']
    return values, x_edges, y_edges, float(origin['lat']), float(origin['lon'])


def _grid_to_dict(
    values: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    origin_lat: float,
    origin_lon: float,
) -> dict[str, Any]:
    """Serialize a grid back to a DensityGrid dict."""
    return {
        'type': 'DensityGrid',
        'origin': {'lat': origin_lat, 'lon': origin_lon},
        'x_edges_m': [float(v) for v in x_edges.tolist()],
        'y_edges_m': [float(v) for v in y_edges.tolist()],
        'values': values.tolist(),
    }


def update_trajectory_weights(
    trajectory_lats: np.ndarray,
    trajectory_lons: np.ndarray,
    step_times: list[datetime | str],
    sectors: list[dict[str, Any]],
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """Apply Bayesian likelihood updates to particle trajectory weights (Task 3.3).

    trajectory_lats and trajectory_lons have shape (n_steps, n_particles).
    For each sector, applies (1 - detection_probability) only to particles that were
    within the searched footprint during the search time or interval.

    A moving target that was outside the sector at search time but drifts into that
    location at a later horizon is NOT attenuated, preserving unrelated present mass.
    """
    n_steps, n_particles = trajectory_lats.shape
    w = np.ones(n_particles, dtype=float) / n_particles if weights is None else np.array(weights, dtype=float).copy()
    norm_step_times = [_normalize_dt(t) for t in step_times]

    for sector in sectors:
        if sector.get('is_unassimilated', False):
            continue

        raw_dp = sector.get('detection_probability')
        if raw_dp is None:
            raw_dp = 0.0
        dp = float(raw_dp)
        if not np.isfinite(dp) or dp < 0.0 or dp > 1.0:
            raise ValueError("detection_probability must be between 0.0 and 1.0")
        if dp == 0.0:
            continue

        effective_dp = dp * 0.25 if sector.get('dependent', False) else dp

        # Determine active steps
        searched_at = sector.get('searched_at')
        start_at = sector.get('search_start_at')
        end_at = sector.get('search_end_at')

        if start_at is not None and end_at is not None:
            start_dt = _normalize_dt(start_at)
            end_dt = _normalize_dt(end_at)
            if end_dt < start_dt:
                raise ValueError("search_end_at must be >= search_start_at")
            if start_dt > norm_step_times[-1] or end_dt < norm_step_times[0]:
                raise ValueError("searched interval is outside trajectory time range")
            active_steps = [
                i for i, t in enumerate(norm_step_times)
                if (start_dt <= t <= end_dt) or (i > 0 and norm_step_times[i - 1] <= end_dt and t >= start_dt)
            ]
            if not active_steps:
                active_steps = [int(np.argmin([abs((t - start_dt).total_seconds()) for t in norm_step_times]))]
        elif searched_at is not None:
            s_dt = _normalize_dt(searched_at)
            if s_dt < norm_step_times[0] - timedelta(seconds=1) or s_dt > norm_step_times[-1] + timedelta(seconds=1):
                raise ValueError("searched_at is outside trajectory time range")
            diffs = [abs((t - s_dt).total_seconds()) for t in norm_step_times]
            active_steps = [int(np.argmin(diffs))]
        else:
            raise ValueError("search occurrence time (searched_at or search_start_at/end_at) is required")

        in_sector = np.zeros(n_particles, dtype=bool)
        if 'south' in sector and 'north' in sector:
            for step_idx in active_steps:
                step_lats = trajectory_lats[step_idx]
                step_lons = trajectory_lons[step_idx]
                in_step = (
                    (step_lats >= sector['south']) & (step_lats <= sector['north']) &
                    (step_lons >= sector['west']) & (step_lons <= sector['east'])
                )
                in_sector |= in_step
        elif 'x_min_m' in sector and 'x_max_m' in sector:
            # Metre bounding box against origin if provided
            origin_lat = float(sector.get('origin_lat', norm_step_times[0]))
            origin_lon = float(sector.get('origin_lon', norm_step_times[0]))
            for step_idx in active_steps:
                xs, ys = _to_xy(trajectory_lats[step_idx], trajectory_lons[step_idx], origin_lat, origin_lon)
                in_step = (
                    (xs >= sector['x_min_m']) & (xs <= sector['x_max_m']) &
                    (ys >= sector['y_min_m']) & (ys <= sector['y_max_m'])
                )
                in_sector |= in_step

        w[in_sector] *= 1.0 - effective_dp

    total = float(w.sum())
    if not np.isfinite(total) or total <= 1e-12:
        raise ValueError("All particle mass rejected by search evidence")
    w /= total
    return w


def grid_from_trajectories(
    trajectory_lats: np.ndarray,
    trajectory_lons: np.ndarray,
    weights: np.ndarray,
    origin_lat: float,
    origin_lon: float,
    grid_resolution_m: float = 500.0,
    reference_grid: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a DensityGrid dict from final particle positions and their posterior weights."""
    final_lats = trajectory_lats[-1]
    final_lons = trajectory_lons[-1]
    if reference_grid is not None:
        _, x_edges, y_edges, origin_lat, origin_lon = _grid_from_dict(reference_grid)
    else:
        x, y = _to_xy(final_lats, final_lons, origin_lat, origin_lon)
        x_min = float(np.min(x)) - grid_resolution_m
        x_max = float(np.max(x)) + grid_resolution_m
        y_min = float(np.min(y)) - grid_resolution_m
        y_max = float(np.max(y)) + grid_resolution_m
        x_edges = np.arange(x_min, x_max + grid_resolution_m, grid_resolution_m)
        y_edges = np.arange(y_min, y_max + grid_resolution_m, grid_resolution_m)

    x, y = _to_xy(final_lats, final_lons, origin_lat, origin_lon)
    hist, y_edges, x_edges = np.histogram2d(y, x, bins=[y_edges, x_edges], weights=weights)
    if hist.sum() > 0:
        hist = hist / hist.sum()

    return _grid_to_dict(hist, x_edges, y_edges, origin_lat, origin_lon)


def update_posterior(
    grid_dict: dict[str, Any],
    sectors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply Bayesian updates for all searched sectors to the prior grid.

    Each sector is a dict with keys: x_min_m, x_max_m, y_min_m, y_max_m,
    detection_probability. Cells whose centres fall inside the sector bounding
    box are multiplied by (1 - detection_probability), then the grid is
    renormalised to sum to 1.
    If detection_probability <= 0.0, the prior is left quantitatively unchanged.

    Returns the updated grid dict (the posterior).
    """
    values, x_edges, y_edges, origin_lat, origin_lon = _grid_from_dict(grid_dict)
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0

    xx, yy = np.meshgrid(x_centers, y_centers)

    for sector in sectors:
        dp = float(sector.get('detection_probability', 0.0))
        if dp <= 0.0:
            continue
        if sector.get('dependent', False):
            dp = dp * 0.25

        mask = (
            (xx >= sector['x_min_m'])
            & (xx <= sector['x_max_m'])
            & (yy >= sector['y_min_m'])
            & (yy <= sector['y_max_m'])
        )
        values[mask] *= 1.0 - dp

    total = values.sum()
    if total > 0:
        values /= total

    return _grid_to_dict(values, x_edges, y_edges, origin_lat, origin_lon)


def contours_from_grid(
    grid_dict: dict[str, Any],
    mass_targets: tuple[float, ...] = (0.50, 0.75, 0.95),
) -> list[dict[str, Any]]:
    """Recompute contours from a (possibly updated) grid.

    Uses the same logic as predict_drift but works on any grid dict.
    """
    values, x_edges, y_edges, origin_lat, origin_lon = _grid_from_dict(grid_dict)
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0
    return [
        _contour_polygon(x_centers, y_centers, values, mass, origin_lat, origin_lon)
        for mass in mass_targets
    ]


def recommend_next_area(grid_dict: dict[str, Any]) -> dict[str, Any]:
    """The single highest remaining-mass cell of the posterior, as a
    geographic rectangle/centroid plus its probability mass (docs/40 Phase 3
    item 5). An advisory recommendation for responder review - never an automatic
    tasking, asset assignment, or forced re-routing.
    """
    values, x_edges, y_edges, origin_lat, origin_lon = _grid_from_dict(grid_dict)
    label = 'recommendation for responder review'
    advisory_note = 'advisory recommendation for responder review, not an automatic tasking'
    if values.size == 0 or float(values.sum()) <= 0.0:
        return {
            'label': label,
            'advisory_note': advisory_note,
            'is_advisory': True,
            'bounds': None,
            'centroid': None,
            'remaining_mass': 0.0,
        }

    row, col = (int(i) for i in np.unravel_index(np.argmax(values), values.shape))
    x0, x1 = float(x_edges[col]), float(x_edges[col + 1])
    y0, y1 = float(y_edges[row]), float(y_edges[row + 1])

    xs = np.array([x0, x1, (x0 + x1) / 2.0])
    ys = np.array([y0, y1, (y0 + y1) / 2.0])
    lat, lon = _to_latlon(xs, ys, origin_lat, origin_lon)

    return {
        'label': label,
        'advisory_note': advisory_note,
        'is_advisory': True,
        'bounds': {
            'south': float(lat[0]), 'west': float(lon[0]),
            'north': float(lat[1]), 'east': float(lon[1]),
        },
        'centroid': {'lat': float(lat[2]), 'lon': float(lon[2])},
        'remaining_mass': float(values[row, col]),
    }


def contour_area_km2(contour: dict[str, Any]) -> float:
    """Compute the area of a GeoJSON Polygon contour in km²."""
    ring = contour['geometry']['coordinates'][0]
    if len(ring) < 4:
        return 0.0
    n = len(ring) - 1
    area_deg2 = 0.0
    for i in range(n):
        lon_i, lat_i = ring[i]
        lon_j, lat_j = ring[(i + 1) % n]
        area_deg2 += lon_i * lat_j - lon_j * lat_i
    return abs(area_deg2 / 2.0) * 111.320 * 110.574
