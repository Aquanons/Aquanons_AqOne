"""Monte Carlo leeway drift prediction for synthetic AqOne SAR cases.

Physical assumptions:
- Motion is shallow-water surface drift in a local tangent plane around the
  last known position.
- Each particle follows a Lagrangian path: current + leeway + diffusion.
- Current is supplied by the synthetic field used elsewhere in the backend.
- Wind is taken from Open-Meteo when available and cached in-process; if the
  API is unavailable, a deterministic synthetic wind field is substituted and
  the response is marked degraded.
- Leeway coefficients are rough approximations of published values chosen only
  to separate object classes, not to claim a calibrated operational model.
- Crosswind leeway is assigned left/right per particle at seeding so the search
  cone can bifurcate instead of collapsing into a single ellipse.
- Diffusion is isotropic and constant in time.
- Contours are approximated by convex hulls of cells covering the requested
  probability mass, which is GeoJSON-friendly and adequate for a demo.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from itertools import pairwise
from time import perf_counter

import httpx
import numpy as np

from app import geo

CENTER_LAT = 11.6892
CENTER_LON = 122.3667
MANILA_TZ = timezone(timedelta(hours=8))
WIND_CACHE_TTL_SECONDS = 20 * 60
KM_PER_DEG_LAT = 110_574.0

# Recorded on every persisted drift run snapshot (docs/40 Phase 2 item 3) so a
# later change to the particle model is visible in old runs' metadata rather
# than silently reinterpreting them. Bump on any change to predict_drift's
# physics (leeway coefficients, diffusion, current-bias sigma, boundaries).
MODEL_VERSION = 'aqone-drift-v2'


class ObjectClass(str, Enum):  # noqa: UP042
    person_in_water = 'person_in_water'
    swamped_banca = 'swamped_banca'
    intact_hull_adrift = 'intact_hull_adrift'


@dataclass(frozen=True)
class ObjectSpec:
    # Approximate, literature-inspired windage fractions. These are deliberately
    # broad and are used to distinguish classes, not to claim exact calibration.
    downwind: float
    crosswind: float


OBJECT_SPECS: dict[ObjectClass, ObjectSpec] = {
    ObjectClass.person_in_water: ObjectSpec(downwind=0.006, crosswind=0.002),
    ObjectClass.swamped_banca: ObjectSpec(downwind=0.012, crosswind=0.004),
    ObjectClass.intact_hull_adrift: ObjectSpec(downwind=0.020, crosswind=0.007),
}


@dataclass(frozen=True)
class WindSeries:
    times: list[datetime]
    u_mps: np.ndarray
    v_mps: np.ndarray
    source: str
    degraded: bool


@dataclass(frozen=True)
class DriftResult:
    grid: dict[str, object]
    contours: list[dict[str, object]]
    centroid_track: list[dict[str, object]]
    degraded: bool
    runtime_ms: float
    wind_source: str
    object_class: str
    stranded_count: int = 0
    support_lost_at: str | None = None
    trajectories: list[dict[str, object]] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'grid': self.grid,
            'contours': self.contours,
            'centroid_track': self.centroid_track,
            'degraded': self.degraded,
            'runtime_ms': round(self.runtime_ms, 3),
            'wind_source': self.wind_source,
            'object_class': self.object_class,
            'stranded_count': self.stranded_count,
            'support_lost_at': self.support_lost_at,
        }


def _points_in_water(
    lats: np.ndarray,
    lons: np.ndarray,
    polygon: tuple[tuple[float, float], ...] | None = None,
) -> np.ndarray:
    """Vectorized point-in-water check using ray casting against coastal boundary."""
    if polygon is None:
        polygon = geo.WATER_POLYGON
    inside = np.zeros(len(lats), dtype=bool)
    count = len(polygon)
    for i in range(count):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[(i - 1) % count]
        intersects = (lat_i > lats) != (lat_j > lats)
        denom = (lat_j - lat_i) if abs(lat_j - lat_i) > 1e-12 else 1e-12
        lon_at_lat = (lon_j - lon_i) * (lats - lat_i) / denom + lon_i
        crossing = intersects & (lons < lon_at_lat)
        inside ^= crossing
    return inside


def _km_per_deg_lon(lat: float) -> float:
    return 111_320.0 * math.cos(math.radians(lat))


def _to_xy(lat: np.ndarray, lon: np.ndarray, origin_lat: float, origin_lon: float) -> tuple[np.ndarray, np.ndarray]:
    x = (lon - origin_lon) * _km_per_deg_lon(origin_lat)
    y = (lat - origin_lat) * KM_PER_DEG_LAT
    return x, y


def _to_latlon(x_m: np.ndarray, y_m: np.ndarray, origin_lat: float, origin_lon: float) -> tuple[np.ndarray, np.ndarray]:
    lat = origin_lat + y_m / KM_PER_DEG_LAT
    lon = origin_lon + x_m / _km_per_deg_lon(origin_lat)
    return lat, lon


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(MANILA_TZ)


def _hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def _synthetic_current_vector(lat: np.ndarray, lon: np.ndarray, at: datetime) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic current field matching the shape of the generator's field."""

    hours = (at.astimezone(MANILA_TZ) - datetime(2026, 8, 1, tzinfo=MANILA_TZ)).total_seconds() / 3600.0
    tide = 2.0 * math.pi * hours / 12.42
    daily = 2.0 * math.pi * hours / 24.0
    weekly = 2.0 * math.pi * hours / (24.0 * 7.0)
    spatial_lat = (lat - CENTER_LAT) * 18.0
    spatial_lon = (lon - CENTER_LON) * 18.0
    u = (
        0.32
        + 0.20 * np.sin(tide + spatial_lat)
        + 0.10 * np.cos(daily + spatial_lon / 2.0)
        + 0.05 * np.sin(weekly + spatial_lat / 3.0)
    )
    v = (
        0.18
        + 0.16 * np.cos(tide * 0.9 + spatial_lon)
        + 0.08 * np.sin(daily + spatial_lat / 2.0)
        + 0.04 * np.cos(weekly - spatial_lon / 3.0)
    )
    speed = np.hypot(u, v)
    scale = np.where(speed > 1.5, 1.5 / speed, 1.0)
    return u * scale, v * scale


def _synthetic_wind_series(
    lat: float,
    lon: float,
    start_at: datetime,
    horizon_hours: float,
    step_hours: float = 1.0,
) -> WindSeries:
    times = []
    u_values = []
    v_values = []
    total_steps = max(2, math.ceil(horizon_hours / step_hours) + 1)
    for index in range(total_steps):
        at = start_at + timedelta(hours=index * step_hours)
        times.append(at)
        hours = _hours_between(datetime(2026, 8, 1, tzinfo=MANILA_TZ), at)
        daily = 2.0 * math.pi * hours / 24.0
        weekly = 2.0 * math.pi * hours / (24.0 * 7.0)
        spatial = (lat - CENTER_LAT) * 0.6 + (lon - CENTER_LON) * 0.4
        speed = 7.0 + 1.9 * math.sin(daily + spatial) + 0.7 * math.cos(weekly - spatial / 2.0)
        speed = float(np.clip(speed, 2.5, 14.0))
        direction_from_deg = 65.0 + 28.0 * math.sin(weekly + spatial) + 12.0 * math.cos(daily / 2.0)
        direction_to_deg = (direction_from_deg + 180.0) % 360.0
        rad = math.radians(direction_to_deg)
        u_values.append(speed * math.sin(rad))
        v_values.append(speed * math.cos(rad))
    return WindSeries(
        times=times,
        u_mps=np.array(u_values, dtype=float),
        v_mps=np.array(v_values, dtype=float),
        source='synthetic',
        degraded=True,
    )


def _open_meteo_key(lat: float, lon: float, start_at: datetime) -> tuple[float, float, str]:
    hour = start_at.astimezone(MANILA_TZ).replace(minute=0, second=0, microsecond=0)
    return round(lat, 2), round(lon, 2), hour.isoformat()


_wind_cache: dict[tuple[float, float, str], tuple[float, WindSeries]] = {}


def _fetch_wind_series(lat: float, lon: float, start_at: datetime, horizon_hours: float) -> WindSeries:
    key = _open_meteo_key(lat, lon, start_at)
    cached = _wind_cache.get(key)
    now = datetime.now(UTC).timestamp()
    if cached and now - cached[0] < WIND_CACHE_TTL_SECONDS:
        return cached[1]

    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': lat,
        'longitude': lon,
        'hourly': 'wind_speed_10m,wind_direction_10m',
        'wind_speed_unit': 'ms',
        'forecast_days': 3,
        'timezone': 'Asia/Manila',
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        hourly = payload.get('hourly') or {}
        times_raw = hourly.get('time') or []
        speed_raw = hourly.get('wind_speed_10m') or []
        direction_raw = hourly.get('wind_direction_10m') or []
        times = [datetime.fromisoformat(item) for item in times_raw]
        if not times or len(times) != len(speed_raw) or len(speed_raw) != len(direction_raw):
            raise ValueError('invalid Open-Meteo payload')
        u_values = []
        v_values = []
        for speed, direction_from_deg in zip(speed_raw, direction_raw, strict=True):
            direction_to_deg = (float(direction_from_deg) + 180.0) % 360.0
            rad = math.radians(direction_to_deg)
            u_values.append(float(speed) * math.sin(rad))
            v_values.append(float(speed) * math.cos(rad))
        series = WindSeries(
            times=times,
            u_mps=np.array(u_values, dtype=float),
            v_mps=np.array(v_values, dtype=float),
            source='open-meteo',
            degraded=False,
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        series = _synthetic_wind_series(lat, lon, start_at, horizon_hours)

    _wind_cache[key] = (now, series)
    return series


def _interpolate_series(series: WindSeries, at: datetime) -> tuple[float, float]:
    u_arr = np.asarray(series.u_mps)
    v_arr = np.asarray(series.v_mps)
    if not np.all(np.isfinite(u_arr)) or not np.all(np.isfinite(v_arr)):
        raise ValueError("Wind series contains NaN or nonfinite values")

    if len(series.times) == 1:
        return float(u_arr[0]), float(v_arr[0])

    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    target = at.timestamp()

    times = []
    for item in series.times:
        if item.tzinfo is None:
            item = item.replace(tzinfo=UTC)
        times.append(item.timestamp())
    times = np.array(times, dtype=float)

    if target <= times[0]:
        return float(u_arr[0]), float(v_arr[0])
    if target >= times[-1]:
        return float(u_arr[-1]), float(v_arr[-1])
    index = int(np.searchsorted(times, target))
    t0 = times[index - 1]
    t1 = times[index]
    alpha = (target - t0) / (t1 - t0) if t1 != t0 else 0.0
    u = float(u_arr[index - 1] * (1.0 - alpha) + u_arr[index] * alpha)
    v = float(v_arr[index - 1] * (1.0 - alpha) + v_arr[index] * alpha)
    return u, v


def _class_spec(object_class: ObjectClass) -> ObjectSpec:
    return OBJECT_SPECS[object_class]


def _point_in_polygon(point_lon: float, point_lat: float, ring: list[list[float]]) -> bool:
    inside = False
    x = point_lon
    y = point_lat
    for (x1, y1), (x2, y2) in pairwise(ring):
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1):
            inside = not inside
    return inside


def _convex_hull(points: np.ndarray) -> np.ndarray:
    points = np.unique(points, axis=0)
    if len(points) <= 2:
        return points
    points = points[np.lexsort((points[:, 1], points[:, 0]))]

    def cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[np.ndarray] = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[np.ndarray] = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = np.vstack((lower[:-1], upper[:-1]))
    return hull


def _ensure_ring_closed(coords: list[list[float]]) -> list[list[float]]:
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def _contour_polygon(
    x_centers: np.ndarray,
    y_centers: np.ndarray,
    values: np.ndarray,
    mass_target: float,
    origin_lat: float,
    origin_lon: float,
) -> dict[str, object]:
    flat = values.ravel()
    order = np.argsort(flat)[::-1]
    cumulative = np.cumsum(flat[order])
    if not len(order):
        ring = [
            [origin_lon - 0.001, origin_lat - 0.001],
            [origin_lon + 0.001, origin_lat - 0.001],
            [origin_lon + 0.001, origin_lat + 0.001],
            [origin_lon - 0.001, origin_lat + 0.001],
            [origin_lon - 0.001, origin_lat - 0.001],
        ]
        return {
            'type': 'Feature',
            'geometry': {'type': 'Polygon', 'coordinates': [ring]},
            'properties': {'mass': mass_target},
        }
    cutoff = flat[order[np.searchsorted(cumulative, mass_target, side='left')]]
    selected = np.argwhere(values >= cutoff)
    if len(selected) < 3:
        idx = int(order[0])
        row = idx // values.shape[1]
        col = idx % values.shape[1]
        x0 = float(x_centers[min(col, len(x_centers) - 1)])
        y0 = float(y_centers[min(row, len(y_centers) - 1)])
        half_x = (float(np.diff(x_centers).mean()) if len(x_centers) > 1 else 500.0) / 2.0
        half_y = (float(np.diff(y_centers).mean()) if len(y_centers) > 1 else 500.0) / 2.0
        coords_m = np.array(
            [
                [x0 - half_x, y0 - half_y],
                [x0 + half_x, y0 - half_y],
                [x0 + half_x, y0 + half_y],
                [x0 - half_x, y0 + half_y],
            ]
        )
    else:
        coords_m = np.column_stack((x_centers[selected[:, 1]], y_centers[selected[:, 0]]))
    hull = _convex_hull(coords_m)
    if len(hull) < 3:
        xs = coords_m[:, 0]
        ys = coords_m[:, 1]
        hull = np.array(
            [
                [xs.min(), ys.min()],
                [xs.max(), ys.min()],
                [xs.max(), ys.max()],
                [xs.min(), ys.max()],
            ]
        )
    lat, lon = _to_latlon(hull[:, 0], hull[:, 1], origin_lat, origin_lon)
    ring = _ensure_ring_closed([[float(lon[i]), float(lat[i])] for i in range(len(lat))])
    return {
        'type': 'Feature',
        'geometry': {'type': 'Polygon', 'coordinates': [ring]},
        'properties': {'mass': mass_target},
    }


def predict_drift(
    *,
    last_lat: float,
    last_lon: float,
    observed_at: datetime,
    object_class: ObjectClass | str,
    forecast_hours: float = 24.0,
    particle_count: int = 2000,
    step_minutes: int = 10,
    current_vector_fn: Callable[
        [np.ndarray, np.ndarray, datetime], tuple[np.ndarray, np.ndarray]
    ] = _synthetic_current_vector,
    wind_provider: Callable[[float, float, datetime, float], WindSeries] | None = None,
    rng: np.random.Generator | None = None,
    initial_spread_m: float = 250.0,
    diffusivity_m2_s: float = 0.75,
    # Per-particle uncertainty in the forecast current and in the object's
    # windage. Turbulent diffusion alone spreads the ensemble only a few hundred
    # metres over a full day, while the dominant real error is that the forecast
    # current is wrong by some roughly constant amount for the whole drift.
    # Operational SAR ensembles (SAROPS) perturb the current and wind fields the
    # same way.
    #
    # Calibrated against 19 synthetic incidents across three seeds. The 95%
    # contour should contain the true position about 95% of the time - no more,
    # no less. Too tight and the search area is confidently wrong; too wide and
    # it is larger than simply drawing a circle at maximum drift speed:
    #
    #   sigma   containment   area vs naive baseline
    #   0.04        89.5%          4.14x   under-covers
    #   0.06        94.7%          1.92x   <- calibrated
    #   0.10       100.0%          0.81x   worse than the baseline
    current_bias_sigma_ms: float = 0.06,
    leeway_scale_sigma: float = 0.25,
    grid_resolution_m: float = 500.0,
    boundary_polygon: tuple[tuple[float, float], ...] | None = None,
    enable_stranding: bool = False,
    record_trajectories: bool = False,
) -> DriftResult:
    start = perf_counter()
    observed_at = _ensure_timezone(observed_at)
    object_class = ObjectClass(object_class)
    spec = _class_spec(object_class)
    rng = rng or np.random.default_rng(12345)
    horizon_steps = max(1, math.ceil(forecast_hours * 60.0 / step_minutes))
    dt_seconds = step_minutes * 60.0
    wind_provider = wind_provider or _fetch_wind_series
    wind_series = wind_provider(last_lat, last_lon, observed_at, forecast_hours)

    x = rng.normal(0.0, initial_spread_m, size=particle_count)
    y = rng.normal(0.0, initial_spread_m, size=particle_count)
    cross_sign = rng.choice(np.array([-1.0, 1.0]), size=particle_count)
    diffusion_sigma = math.sqrt(2.0 * diffusivity_m2_s * dt_seconds)

    # Drawn once per particle and held for the whole run: each ensemble member
    # represents one plausible version of "what the current actually was" and
    # "how much windage this object really had", rather than resampling the
    # error every step, which would average it away.
    current_bias_u = rng.normal(0.0, current_bias_sigma_ms, size=particle_count)
    current_bias_v = rng.normal(0.0, current_bias_sigma_ms, size=particle_count)
    leeway_scale = np.clip(rng.normal(1.0, leeway_scale_sigma, size=particle_count), 0.3, 2.0)
    stranded = np.zeros(particle_count, dtype=bool)
    centroid_track: list[dict[str, object]] = []
    traj_records: list[dict[str, object]] | None = [] if record_trajectories else None

    for step in range(horizon_steps + 1):
        at = observed_at + timedelta(minutes=step * step_minutes)
        lat, lon = _to_latlon(x, y, last_lat, last_lon)
        centroid_lat = float(np.mean(lat))
        centroid_lon = float(np.mean(lon))
        centroid_track.append({'at': at.isoformat(), 'lat': centroid_lat, 'lon': centroid_lon})
        if record_trajectories and traj_records is not None:
            traj_records.append({'at': at.isoformat(), 'lat': lat.copy(), 'lon': lon.copy()})
        if step == horizon_steps:
            break

        active_idx = np.where(~stranded)[0]
        if len(active_idx) > 0:
            current_u, current_v = current_vector_fn(lat[active_idx], lon[active_idx], at)
            wind_u, wind_v = _interpolate_series(wind_series, at)
            wind_speed = math.hypot(wind_u, wind_v)
            if wind_speed < 1e-6:
                wind_perp_u = 0.0
                wind_perp_v = 0.0
            else:
                wind_perp_u = -wind_v
                wind_perp_v = wind_u
            leeway_u = leeway_scale[active_idx] * (
                spec.downwind * wind_u + cross_sign[active_idx] * spec.crosswind * wind_perp_u
            )
            leeway_v = leeway_scale[active_idx] * (
                spec.downwind * wind_v + cross_sign[active_idx] * spec.crosswind * wind_perp_v
            )
            diffusion_u = rng.normal(0.0, diffusion_sigma, size=len(active_idx))
            diffusion_v = rng.normal(0.0, diffusion_sigma, size=len(active_idx))

            cand_x = x[active_idx] + (current_u + current_bias_u[active_idx] + leeway_u) * dt_seconds + diffusion_u
            cand_y = y[active_idx] + (current_v + current_bias_v[active_idx] + leeway_v) * dt_seconds + diffusion_v
            cand_lat, cand_lon = _to_latlon(cand_x, cand_y, last_lat, last_lon)

            if enable_stranding and boundary_polygon is not None:
                in_water = _points_in_water(cand_lat, cand_lon, boundary_polygon)
                stranded_now = ~in_water
                x[active_idx[in_water]] = cand_x[in_water]
                y[active_idx[in_water]] = cand_y[in_water]
                stranded[active_idx[stranded_now]] = True
            else:
                x[active_idx] = cand_x
                y[active_idx] = cand_y

    x_min = float(np.min(x)) - grid_resolution_m
    x_max = float(np.max(x)) + grid_resolution_m
    y_min = float(np.min(y)) - grid_resolution_m
    y_max = float(np.max(y)) + grid_resolution_m
    x_edges = np.arange(x_min, x_max + grid_resolution_m, grid_resolution_m)
    y_edges = np.arange(y_min, y_max + grid_resolution_m, grid_resolution_m)
    hist, y_edges, x_edges = np.histogram2d(y, x, bins=[y_edges, x_edges])
    if hist.sum() > 0:
        hist = hist / hist.sum()
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2.0

    contours = [
        _contour_polygon(x_centers, y_centers, hist, mass, last_lat, last_lon)
        for mass in (0.50, 0.75, 0.95)
    ]

    grid = {
        'type': 'DensityGrid',
        'origin': {'lat': last_lat, 'lon': last_lon},
        'x_edges_m': [float(value) for value in x_edges.tolist()],
        'y_edges_m': [float(value) for value in y_edges.tolist()],
        'values': hist.tolist(),
    }
    runtime_ms = (perf_counter() - start) * 1000.0
    support_lost_at_val = getattr(current_vector_fn, 'support_lost_at', None)
    support_lost_str = (
        support_lost_at_val.isoformat()
        if hasattr(support_lost_at_val, 'isoformat')
        else (str(support_lost_at_val) if support_lost_at_val else None)
    )
    return DriftResult(
        grid=grid,
        contours=contours,
        centroid_track=centroid_track,
        degraded=wind_series.degraded,
        runtime_ms=runtime_ms,
        wind_source=wind_series.source,
        object_class=object_class.value,
        stranded_count=int(np.sum(stranded)),
        support_lost_at=support_lost_str,
        trajectories=traj_records,
    )


def contour_contains(contour: dict[str, object], lat: float, lon: float) -> bool:
    geometry = contour['geometry']
    ring = geometry['coordinates'][0]
    return _point_in_polygon(lon, lat, ring)
