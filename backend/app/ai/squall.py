from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MANILA_TZ = timezone(timedelta(hours=8))
CENTER_LAT = 11.6892
CENTER_LON = 122.3667
MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'squall.pkl'
CALIBRATION = 'synthetic'
LOOKBACK_MINUTES = 90
STEP_MINUTES = 5
DEFAULT_THRESHOLD = 0.55

# Telemetry-quality policy for live squall arrays
# (docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md Phase 2), approved
# 2026-08-29. Governs assess_array_quality() only - it decides which buoys
# are trustworthy enough to feed a live nowcast, and is deliberately
# separate from PressureEventIn's ingest-time sanity check
# (app/api/pressure_events.py), which only rejects physically impossible
# readings at write time. QUALITY_PRESSURE_MIN/MAX_HPA happen to match that
# ingest bound exactly, by policy choice, not by code sharing.
QUALITY_SAMPLE_INTERVAL_MINUTES = 5
QUALITY_MAX_READING_AGE_MINUTES = 10
QUALITY_MAX_GAP_MINUTES = 10
QUALITY_MIN_BUOYS = 3
QUALITY_PRESSURE_MIN_HPA = 850.0
QUALITY_PRESSURE_MAX_HPA = 1100.0

FEATURE_NAMES = [
    'mean_tendency_30',
    'min_tendency_30',
    'std_tendency_30',
    'mean_tendency_60',
    'min_tendency_60',
    'std_tendency_60',
    'mean_second_derivative',
    'min_second_derivative',
    'std_second_derivative',
    'mean_deviation',
    'min_deviation',
    'std_deviation',
    'array_drop_hpa',
    'anomaly_energy',
    'propagation_speed_mps',
    'propagation_bearing_sin',
    'propagation_bearing_cos',
    'propagation_r2',
    'propagation_residual_minutes',
    'onset_coverage',
    'onset_span_minutes',
]


@dataclass(frozen=True)
class BuoyMeta:
    buoy_id: str
    lat: float
    lon: float
    contact_radius_m: int | None = None


@dataclass(frozen=True)
class PressureReading:
    buoy_id: str
    observed_at: datetime
    pressure_hpa: float


@dataclass(frozen=True)
class BuoyFeatureRow:
    buoy_id: str
    pressure_tendency_30: float
    pressure_tendency_60: float
    second_derivative: float
    deviation_from_mean: float
    onset_time: datetime | None


@dataclass(frozen=True)
class ArrayQuality:
    """Whether a pressure array is trustworthy enough to nowcast from.

    Produced by assess_array_quality(), which must run before
    extract_pressure_features() on any array that might reach a live
    detection - an insufficient array must report insufficient_data, never a
    fabricated calm baseline (docs/39 Phase 2).
    """

    ok: bool
    reason: str | None
    newest_observed_at: datetime | None
    qualifying_buoy_ids: list[str]


@dataclass(frozen=True)
class PropagationEstimate:
    bearing_deg: float
    speed_mps: float
    r2: float
    residual_minutes: float
    onset_coverage: float
    onset_span_minutes: float
    origin_lat: float
    origin_lon: float
    onset_anchor: datetime | None
    geometry_degenerate: bool
    fit_intercept_minutes: float = 0.0


@dataclass(frozen=True)
class SquallFeatureBundle:
    as_of: datetime
    feature_names: list[str]
    values: list[float]
    buoy_rows: list[BuoyFeatureRow]
    propagation: PropagationEstimate
    array_mean_pressure: float
    array_mean_trace: list[dict[str, object]]
    pressure_trace: dict[str, list[dict[str, object]]]

    def to_features(self) -> dict[str, float]:
        return dict(zip(self.feature_names, self.values, strict=True))


@dataclass(frozen=True)
class TrainingSample:
    features: list[float]
    label: int
    group_id: str
    lead_minutes: int | None


@dataclass(frozen=True)
class SquallModelBundle:
    pipeline: Pipeline
    feature_names: list[str]
    threshold: float
    calibration: str
    trained_at: str
    top_features: list[dict[str, object]]
    evaluation: dict[str, float]


@dataclass(frozen=True)
class SquallDetection:
    probability: float
    confidence: float
    affected_polygon: dict[str, object]
    arrival_by_buoy: list[dict[str, object]]
    propagation: dict[str, object]
    features: dict[str, float]
    calibration: str
    as_of: str
    classifier_probability: float | None = None
    pattern_score: float | None = None


def _ensure_tz(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=MANILA_TZ)
    return ts.astimezone(MANILA_TZ)


def _km_per_deg_lon(lat: float) -> float:
    return 111.320 * math.cos(math.radians(lat))


def _to_xy(lat: np.ndarray, lon: np.ndarray, origin_lat: float, origin_lon: float) -> tuple[np.ndarray, np.ndarray]:
    x = (lon - origin_lon) * _km_per_deg_lon(origin_lat) * 1000.0
    y = (lat - origin_lat) * 110.574 * 1000.0
    return x, y


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = lat2_r - lat1_r
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


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
    return np.vstack((lower[:-1], upper[:-1]))


def _close_ring(coords: list[list[float]]) -> list[list[float]]:
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def _as_rows(rows: list[dict[str, Any]]) -> list[PressureReading]:
    return [
        PressureReading(
            buoy_id=str(row['buoy_id']),
            observed_at=_ensure_tz(row['observed_at']),
            pressure_hpa=float(row['pressure_hpa']),
        )
        for row in rows
    ]


def build_history(rows: list[dict[str, Any]]) -> dict[str, list[PressureReading]]:
    history: dict[str, list[PressureReading]] = {}
    for reading in _as_rows(rows):
        history.setdefault(reading.buoy_id, []).append(reading)
    for series in history.values():
        series.sort(key=lambda item: item.observed_at)
    return history


def build_buoys(rows: list[dict[str, Any]]) -> dict[str, BuoyMeta]:
    buoys: dict[str, BuoyMeta] = {}
    for row in rows:
        buoys[str(row['id'])] = BuoyMeta(
            buoy_id=str(row['id']),
            lat=float(row['lat']),
            lon=float(row['lon']),
            contact_radius_m=int(row['contact_radius_m']) if row.get('contact_radius_m') is not None else None,
        )
    return buoys


def _latest_before(series: list[PressureReading], target: datetime) -> float:
    target = _ensure_tz(target)
    if not series:
        return 1013.25
    for reading in reversed(series):
        if reading.observed_at <= target:
            return reading.pressure_hpa
    return series[0].pressure_hpa


def _window_times(as_of: datetime, lookback_minutes: int) -> list[datetime]:
    return [_ensure_tz(as_of - timedelta(minutes=minutes)) for minutes in range(lookback_minutes, -1, -STEP_MINUTES)]


def _geometry_degenerate(x: np.ndarray, y: np.ndarray) -> bool:
    """SVD-based collinearity test on a set of local (x, y) positions.

    Shared by estimate_propagation_vector (below) and
    assess_array_quality's geometry check - the plan requires reusing this
    exact test rather than inventing a separate distance threshold for the
    quality gate (docs/39 Phase 2).
    """
    centered = np.column_stack((x - float(np.mean(x)), y - float(np.mean(y))))
    singular_values = np.linalg.svd(centered, compute_uv=False)
    return bool(
        len(singular_values) < 2
        or singular_values[-1] <= 1e-6
        or (singular_values[0] / max(singular_values[-1], 1e-9)) >= 100.0
    )


def estimate_propagation_vector(onset_times: dict[str, datetime], buoys: dict[str, BuoyMeta]) -> PropagationEstimate:
    if len(onset_times) < 3:
        coverage = len(onset_times) / max(1, len(buoys))
        return PropagationEstimate(0.0, 0.0, 0.0, 0.0, coverage, 0.0, CENTER_LAT, CENTER_LON, None, True)

    ordered_ids = [buoy_id for buoy_id in onset_times if buoy_id in buoys]
    lat = np.asarray([buoys[buoy_id].lat for buoy_id in ordered_ids], dtype=float)
    lon = np.asarray([buoys[buoy_id].lon for buoy_id in ordered_ids], dtype=float)
    origin_lat = float(lat.mean())
    origin_lon = float(lon.mean())
    x, y = _to_xy(lat, lon, origin_lat, origin_lon)
    anchor = min(onset_times[buoy_id] for buoy_id in ordered_ids)
    offsets = np.asarray(
        [(onset_times[buoy_id] - anchor).total_seconds() / 60.0 for buoy_id in ordered_ids],
        dtype=float,
    )
    geometry_degenerate = _geometry_degenerate(x, y)

    best_r2 = -1.0
    best_speed = float('inf') if geometry_degenerate else 0.0
    best_bearing = 0.0
    best_residual = float('inf')
    best_intercept = 0.0
    for bearing_deg in range(0, 360, 5):
        theta = math.radians(bearing_deg)
        along = x * math.sin(theta) + y * math.cos(theta)
        if np.allclose(along, along[0]):
            continue
        slope, intercept = np.polyfit(along, offsets, deg=1)
        if slope <= 0:
            continue
        predicted = slope * along + intercept
        ss_tot = float(np.sum((offsets - offsets.mean()) ** 2))
        ss_res = float(np.sum((offsets - predicted) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        residual = float(np.sqrt(np.mean((offsets - predicted) ** 2)))
        speed = 1.0 / (slope * 60.0)
        should_replace = r2 > best_r2 or (
            math.isclose(r2, best_r2)
            and (
                (geometry_degenerate and speed < best_speed)
                or (not geometry_degenerate and residual < best_residual)
            )
        )
        if should_replace:
            best_r2 = r2
            best_speed = speed
            best_bearing = float(bearing_deg)
            best_residual = residual
            best_intercept = float(intercept)

    if best_r2 < 0.0:
        coverage = len(onset_times) / max(1, len(buoys))
        return PropagationEstimate(
            0.0, 0.0, 0.0, 0.0, coverage, 0.0, origin_lat, origin_lon, anchor, geometry_degenerate, 0.0
        )

    if geometry_degenerate:
        best_r2 = 0.0
        best_residual = max(best_residual, 999.0)
        if not math.isfinite(best_speed):
            best_speed = 0.0

    return PropagationEstimate(
        bearing_deg=best_bearing,
        speed_mps=best_speed,
        r2=max(0.0, best_r2),
        residual_minutes=max(0.0, best_residual),
        onset_coverage=len(onset_times) / max(1, len(buoys)),
        onset_span_minutes=float((max(onset_times.values()) - min(onset_times.values())).total_seconds() / 60.0),
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        onset_anchor=anchor,
        geometry_degenerate=geometry_degenerate,
        fit_intercept_minutes=best_intercept,
    )


def _buoy_readings_are_sane(readings: list[PressureReading]) -> bool:
    return all(
        math.isfinite(reading.pressure_hpa)
        and QUALITY_PRESSURE_MIN_HPA <= reading.pressure_hpa <= QUALITY_PRESSURE_MAX_HPA
        for reading in readings
    )


def assess_array_quality(
    history: dict[str, list[PressureReading]],
    buoys: dict[str, BuoyMeta],
    as_of: datetime,
    lookback_minutes: int = LOOKBACK_MINUTES,
) -> ArrayQuality:
    """Decide whether the array is trustworthy enough to nowcast from.

    Must run before extract_pressure_features() on any array that might
    reach a live detection (docs/39 Phase 2). A buoy only qualifies if its
    latest reading is fresh, its readings covering the lookback window have
    no gap wider than the approved tolerance, and every value in that window
    is a finite, physically-sane pressure. At least QUALITY_MIN_BUOYS must
    qualify, and their locations must be non-degenerate (reusing
    _geometry_degenerate - the same test estimate_propagation_vector uses,
    per the plan's instruction not to invent a separate distance threshold).
    """
    as_of = _ensure_tz(as_of)
    window_start = as_of - timedelta(minutes=lookback_minutes)
    max_gap = timedelta(minutes=QUALITY_MAX_GAP_MINUTES)
    max_age = timedelta(minutes=QUALITY_MAX_READING_AGE_MINUTES)
    # A reading up to one gap-tolerance before window_start still covers the
    # start of the lookback window, the same way _latest_before() carries a
    # prior reading forward to a grid point - it just must not be older.
    anchor_cutoff = window_start - max_gap

    newest_observed_at: datetime | None = None
    qualifying_buoy_ids: list[str] = []

    for buoy_id in buoys:
        series = history.get(buoy_id, [])  # build_history() sorts ascending
        if not series:
            continue
        latest = series[-1].observed_at
        if newest_observed_at is None or latest > newest_observed_at:
            newest_observed_at = latest
        if as_of - latest > max_age:
            continue  # stale

        windowed = [r for r in series if anchor_cutoff <= r.observed_at <= as_of]
        if not windowed or not _buoy_readings_are_sane(windowed):
            continue
        if windowed[0].observed_at - window_start > max_gap:
            continue  # no reading close enough to cover the start of the window
        if any(b.observed_at - a.observed_at > max_gap for a, b in zip(windowed, windowed[1:], strict=False)):
            continue  # a mid-window gap wider than tolerated

        qualifying_buoy_ids.append(buoy_id)

    if len(qualifying_buoy_ids) < QUALITY_MIN_BUOYS:
        return ArrayQuality(
            ok=False,
            reason=(
                f'only {len(qualifying_buoy_ids)} of {QUALITY_MIN_BUOYS} required buoys have '
                f'fresh (<= {QUALITY_MAX_READING_AGE_MINUTES}min old), gap-free, in-range readings'
            ),
            newest_observed_at=newest_observed_at,
            qualifying_buoy_ids=qualifying_buoy_ids,
        )

    lat = np.asarray([buoys[buoy_id].lat for buoy_id in qualifying_buoy_ids], dtype=float)
    lon = np.asarray([buoys[buoy_id].lon for buoy_id in qualifying_buoy_ids], dtype=float)
    x, y = _to_xy(lat, lon, float(lat.mean()), float(lon.mean()))
    if _geometry_degenerate(x, y):
        return ArrayQuality(
            ok=False,
            reason='qualifying buoy locations are collinear/degenerate - cannot estimate propagation',
            newest_observed_at=newest_observed_at,
            qualifying_buoy_ids=qualifying_buoy_ids,
        )

    return ArrayQuality(
        ok=True, reason=None, newest_observed_at=newest_observed_at, qualifying_buoy_ids=qualifying_buoy_ids
    )


def extract_pressure_features(
    history: dict[str, list[PressureReading]],
    buoys: dict[str, BuoyMeta],
    as_of: datetime,
    lookback_minutes: int = LOOKBACK_MINUTES,
) -> SquallFeatureBundle:
    as_of = _ensure_tz(as_of)
    window_times = _window_times(as_of, lookback_minutes)
    pressure_trace: dict[str, list[dict[str, object]]] = {buoy_id: [] for buoy_id in buoys}
    array_mean_trace: list[dict[str, object]] = []
    latest_values: dict[str, float] = {}
    per_buoy_series: dict[str, list[float]] = {}

    for buoy_id in buoys:
        series = history.get(buoy_id, [])
        values: list[float] = []
        for ts in window_times:
            pressure = _latest_before(series, ts)
            values.append(pressure)
            pressure_trace[buoy_id].append({'at': ts.isoformat(), 'pressure_hpa': pressure})
        per_buoy_series[buoy_id] = values
        latest_values[buoy_id] = values[-1]

    for index, ts in enumerate(window_times):
        mean_pressure = float(np.mean([per_buoy_series[buoy_id][index] for buoy_id in buoys]))
        array_mean_trace.append({'at': ts.isoformat(), 'mean_pressure_hpa': mean_pressure})

    latest_mean = float(np.mean(list(latest_values.values())))
    tendencies_30: list[float] = []
    tendencies_60: list[float] = []
    second_derivatives: list[float] = []
    deviations: list[float] = []
    abs_drops: list[float] = []
    buoy_rows: list[BuoyFeatureRow] = []
    onset_times: dict[str, datetime] = {}

    for buoy_id in buoys:
        series = history.get(buoy_id, [])
        p0 = _latest_before(series, as_of)
        p30 = _latest_before(series, as_of - timedelta(minutes=30))
        p60 = _latest_before(series, as_of - timedelta(minutes=60))
        tendency_30 = p0 - p30
        tendency_60 = p0 - p60
        second_derivative = p0 - 2.0 * p30 + p60
        deviation = p0 - latest_mean
        tendencies_30.append(tendency_30)
        tendencies_60.append(tendency_60)
        second_derivatives.append(second_derivative)
        deviations.append(deviation)
        abs_drops.append(max(0.0, -deviation))

        onset: datetime | None = None
        for index, ts in enumerate(window_times):
            deviation_from_mean = per_buoy_series[buoy_id][index] - float(array_mean_trace[index]['mean_pressure_hpa'])
            tendency = (
                per_buoy_series[buoy_id][index] - per_buoy_series[buoy_id][index - 6] if index >= 6 else 0.0
            )
            if deviation_from_mean <= -0.5 and tendency <= -0.4:
                onset = ts
                break
        if onset is not None:
            onset_times[buoy_id] = onset

        buoy_rows.append(
            BuoyFeatureRow(
                buoy_id=buoy_id,
                pressure_tendency_30=tendency_30,
                pressure_tendency_60=tendency_60,
                second_derivative=second_derivative,
                deviation_from_mean=deviation,
                onset_time=onset,
            )
        )

    propagation = estimate_propagation_vector(onset_times, buoys)
    values = [
        float(np.mean(tendencies_30)),
        float(np.min(tendencies_30)),
        float(np.std(tendencies_30)),
        float(np.mean(tendencies_60)),
        float(np.min(tendencies_60)),
        float(np.std(tendencies_60)),
        float(np.mean(second_derivatives)),
        float(np.min(second_derivatives)),
        float(np.std(second_derivatives)),
        float(np.mean(deviations)),
        float(np.min(deviations)),
        float(np.std(deviations)),
        float(np.max(abs_drops)),
        float(np.mean(np.square(abs_drops))),
        float(propagation.speed_mps),
        float(math.sin(math.radians(propagation.bearing_deg))),
        float(math.cos(math.radians(propagation.bearing_deg))),
        float(propagation.r2),
        float(propagation.residual_minutes),
        float(propagation.onset_coverage),
        float(propagation.onset_span_minutes),
    ]

    return SquallFeatureBundle(
        as_of=as_of,
        feature_names=list(FEATURE_NAMES),
        values=values,
        buoy_rows=buoy_rows,
        propagation=propagation,
        array_mean_pressure=latest_mean,
        array_mean_trace=array_mean_trace,
        pressure_trace=pressure_trace,
    )


def _polygon_from_buoys(items: list[dict[str, object]]) -> dict[str, object]:
    coords = np.asarray([[float(item['lon']), float(item['lat'])] for item in items], dtype=float)
    if len(coords) >= 3:
        hull = _convex_hull(coords)
    else:
        lon0, lat0 = coords[0]
        hull = np.asarray(
            [
                [lon0 - 0.01, lat0 - 0.01],
                [lon0 + 0.01, lat0 - 0.01],
                [lon0 + 0.01, lat0 + 0.01],
                [lon0 - 0.01, lat0 + 0.01],
            ],
            dtype=float,
        )
    ring = _close_ring([[float(lon), float(lat)] for lon, lat in hull])
    return {
        'type': 'Feature',
        'geometry': {'type': 'Polygon', 'coordinates': [ring]},
        'properties': {'calibration': CALIBRATION},
    }


def _arrival_projection(feature_bundle: SquallFeatureBundle, buoys: dict[str, BuoyMeta]) -> list[dict[str, object]]:
    propagation = feature_bundle.propagation
    if (
        propagation.speed_mps <= 1e-9
        or propagation.onset_anchor is None
        or propagation.geometry_degenerate
        or propagation.r2 < 0.20
    ):
        return []

    theta = math.radians(propagation.bearing_deg)
    origin_lat = propagation.origin_lat
    origin_lon = propagation.origin_lon
    slope = 1.0 / (propagation.speed_mps * 60.0)
    uncertainty = max(5.0, propagation.residual_minutes * 1.5)
    results: list[dict[str, object]] = []
    for buoy_id, buoy in buoys.items():
        x, y = _to_xy(np.asarray([buoy.lat], dtype=float), np.asarray([buoy.lon], dtype=float), origin_lat, origin_lon)
        along_m = float(x[0] * math.sin(theta) + y[0] * math.cos(theta))
        arrival_offset_minutes = slope * along_m + propagation.fit_intercept_minutes
        arrival_dt = propagation.onset_anchor + timedelta(minutes=arrival_offset_minutes)
        delay_minutes = max(0.0, (arrival_dt - feature_bundle.as_of).total_seconds() / 60.0)
        results.append(
            {
                'buoy_id': buoy_id,
                'arrival_minutes': round(delay_minutes, 1),
                'arrival_at': arrival_dt.isoformat(),
                'arrival_window_min_minutes': max(0.0, round(delay_minutes - uncertainty, 1)),
                'arrival_window_max_minutes': round(delay_minutes + uncertainty, 1),
                'lat': buoy.lat,
                'lon': buoy.lon,
            }
        )
    return sorted(results, key=lambda item: (float(item['arrival_minutes']), str(item['buoy_id'])))


def _window_score(feature_bundle: SquallFeatureBundle) -> float:
    features = feature_bundle.to_features()
    base = min(1.0, max(0.0, features['array_drop_hpa'] / 3.0))
    coherence = min(1.0, max(0.0, features['propagation_r2'] + features['onset_coverage'] / 2.0))
    return 0.4 * base + 0.6 * coherence


def detect_squall(
    feature_bundle: SquallFeatureBundle,
    buoys: dict[str, BuoyMeta],
    bundle: SquallModelBundle,
) -> SquallDetection | None:
    probability = float(bundle.pipeline.predict_proba([feature_bundle.values])[0, 1])
    rule_score = _window_score(feature_bundle)
    alert_score = max(probability, rule_score)
    if alert_score < bundle.threshold:
        return None

    arrival_by_buoy = _arrival_projection(feature_bundle, buoys)
    selected = [item for item in arrival_by_buoy if item['arrival_minutes'] <= 90.0]
    if len(selected) < 3 and arrival_by_buoy:
        selected = arrival_by_buoy[: max(3, len(arrival_by_buoy))]
    if not selected:
        selected = [
            {
                'buoy_id': buoy_id,
                'arrival_minutes': 0.0,
                'arrival_at': feature_bundle.as_of.isoformat(),
                'arrival_window_min_minutes': 0.0,
                'arrival_window_max_minutes': 0.0,
                'lat': buoy.lat,
                'lon': buoy.lon,
            }
            for buoy_id, buoy in list(buoys.items())[:3]
        ]
    polygon = _polygon_from_buoys(selected)
    return SquallDetection(
        probability=alert_score,
        confidence=alert_score * (0.35 if feature_bundle.propagation.geometry_degenerate else 1.0),
        affected_polygon=polygon,
        arrival_by_buoy=arrival_by_buoy if arrival_by_buoy else selected,
        propagation={
            'bearing_deg': feature_bundle.propagation.bearing_deg,
            'speed_mps': feature_bundle.propagation.speed_mps,
            'r2': feature_bundle.propagation.r2,
            'residual_minutes': feature_bundle.propagation.residual_minutes,
            'onset_coverage': feature_bundle.propagation.onset_coverage,
            'onset_span_minutes': feature_bundle.propagation.onset_span_minutes,
            'geometry_degenerate': feature_bundle.propagation.geometry_degenerate,
            'fit_intercept_minutes': feature_bundle.propagation.fit_intercept_minutes,
            'onset_anchor': (
                feature_bundle.propagation.onset_anchor.isoformat()
                if feature_bundle.propagation.onset_anchor
                else None
            ),
        },
        features=feature_bundle.to_features(),
        calibration=CALIBRATION,
        as_of=feature_bundle.as_of.isoformat(),
        classifier_probability=probability,
        pattern_score=rule_score,
    )


def _train_pipeline(x_train: np.ndarray, y_train: np.ndarray, seed: int) -> Pipeline:
    pipeline = Pipeline(
        [
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=seed)),
        ]
    )
    pipeline.fit(x_train, y_train)
    return pipeline


def _top_features(pipeline: Pipeline, feature_names: list[str], top_n: int = 8) -> list[dict[str, object]]:
    weights = np.asarray(pipeline.named_steps['classifier'].coef_[0], dtype=float)
    order = np.argsort(np.abs(weights))[::-1][:top_n]
    return [
        {'name': feature_names[index], 'weight': float(weights[index]), 'importance': float(abs(weights[index]))}
        for index in order
    ]


def _score_holdout(
    samples: list[TrainingSample],
    test_idx: np.ndarray,
    y_pred: np.ndarray,
) -> tuple[float, float, float]:
    test_samples = [samples[index] for index in test_idx]
    tp = sum(1 for sample, pred in zip(test_samples, y_pred, strict=True) if sample.label == 1 and pred == 1)
    fp = sum(1 for sample, pred in zip(test_samples, y_pred, strict=True) if sample.label == 0 and pred == 1)
    fn = sum(1 for sample, pred in zip(test_samples, y_pred, strict=True) if sample.label == 1 and pred == 0)
    hit_leads = [
        sample.lead_minutes
        for sample, pred in zip(test_samples, y_pred, strict=True)
        if sample.label == 1 and pred == 1 and sample.lead_minutes is not None
    ]
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    mean_lead_time = float(np.mean(hit_leads)) if hit_leads else 0.0
    return float(precision), float(recall), mean_lead_time


def _samples_from_rows(
    rows: list[dict[str, Any]],
    squalls: list[dict[str, Any]],
    buoys: dict[str, BuoyMeta],
    seed: int,
) -> list[TrainingSample]:
    history = build_history(rows)
    rng = np.random.default_rng(seed)
    samples: list[TrainingSample] = []
    protected_ranges: list[tuple[datetime, datetime]] = []

    for event in squalls:
        has_peak = event.get('peak_at') is not None and event.get('is_synthetic')
        raw_target = event['peak_at'] if has_peak else event['started_at']
        target_at = _ensure_tz(raw_target)
        protected_ranges.append((target_at - timedelta(minutes=LOOKBACK_MINUTES), target_at + timedelta(minutes=180)))
        for lead in (30, 45, 60, 75, 90):
            as_of = target_at - timedelta(minutes=lead)
            features = extract_pressure_features(history, buoys, as_of).values
            samples.append(TrainingSample(features, 1, f'event-{event["id"]}', lead))

    all_times = sorted({reading.observed_at for series in history.values() for reading in series})
    negatives = [ts for ts in all_times if not any(start <= ts <= end for start, end in protected_ranges)]
    rng.shuffle(negatives)
    negative_target = max(1, len(samples))
    for index, as_of in enumerate(negatives[:negative_target]):
        samples.append(TrainingSample(extract_pressure_features(history, buoys, as_of).values, 0, f'neg-{index}', None))
    return samples


def train_from_rows(
    rows: list[dict[str, Any]],
    squalls: list[dict[str, Any]],
    buoys: dict[str, BuoyMeta],
    *,
    seed: int = 42,
) -> tuple[SquallModelBundle, dict[str, float]]:
    samples = _samples_from_rows(rows, squalls, buoys, seed)
    x = np.asarray([sample.features for sample in samples], dtype=float)
    y = np.asarray([sample.label for sample in samples], dtype=int)
    groups = np.asarray([sample.group_id for sample in samples])
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed)
    train_idx, test_idx = next(splitter.split(x, y, groups=groups))
    pipeline = _train_pipeline(x[train_idx], y[train_idx], seed)
    y_pred = pipeline.predict(x[test_idx])
    precision, recall, mean_lead_time = _score_holdout(samples, test_idx, y_pred)
    bundle = SquallModelBundle(
        pipeline=pipeline,
        feature_names=list(FEATURE_NAMES),
        threshold=DEFAULT_THRESHOLD,
        calibration=CALIBRATION,
        trained_at=_ensure_tz(datetime.now(MANILA_TZ)).isoformat(),
        top_features=_top_features(pipeline, list(FEATURE_NAMES)),
        evaluation={'precision': precision, 'recall': recall, 'mean_lead_time': mean_lead_time},
    )
    return bundle, bundle.evaluation


def save_bundle(bundle: SquallModelBundle, path: Path | None = None) -> Path:
    path = path or MODEL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


def load_bundle(path: Path | None = None) -> SquallModelBundle:
    path = path or MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(f'squall model not found at {path}')
    payload = joblib.load(path)
    if isinstance(payload, SquallModelBundle):
        return payload
    return SquallModelBundle(**payload)


def current_detection(
    rows: list[dict[str, Any]],
    buoys: dict[str, BuoyMeta],
    bundle: SquallModelBundle,
) -> list[SquallDetection]:
    history = build_history(rows)
    latest = max(reading.observed_at for series in history.values() for reading in series)
    feature_bundle = extract_pressure_features(history, buoys, latest)
    detection = detect_squall(feature_bundle, buoys, bundle)
    return [detection] if detection is not None else []


def buoy_detail(rows: list[dict[str, Any]], buoy_id: str, buoys: dict[str, BuoyMeta]) -> dict[str, object]:
    history = build_history(rows)
    if buoy_id not in history:
        raise KeyError(buoy_id)
    as_of = history[buoy_id][-1].observed_at
    feature_bundle = extract_pressure_features(history, buoys, as_of)
    row = next(item for item in feature_bundle.buoy_rows if item.buoy_id == buoy_id)
    return {
        'calibration': CALIBRATION,
        'buoy': {'id': buoy_id, 'lat': buoys[buoy_id].lat, 'lon': buoys[buoy_id].lon},
        'as_of': as_of.isoformat(),
        'trace': feature_bundle.pressure_trace[buoy_id],
        'features': {
            'pressure_tendency_30': row.pressure_tendency_30,
            'pressure_tendency_60': row.pressure_tendency_60,
            'second_derivative': row.second_derivative,
            'deviation_from_mean': row.deviation_from_mean,
            'onset_time': row.onset_time.isoformat() if row.onset_time else None,
        },
        'propagation': {
            'bearing_deg': feature_bundle.propagation.bearing_deg,
            'speed_mps': feature_bundle.propagation.speed_mps,
            'r2': feature_bundle.propagation.r2,
            'residual_minutes': feature_bundle.propagation.residual_minutes,
            'onset_coverage': feature_bundle.propagation.onset_coverage,
            'onset_span_minutes': feature_bundle.propagation.onset_span_minutes,
            'geometry_degenerate': feature_bundle.propagation.geometry_degenerate,
        },
    }


def event_detection_summary(bundle: SquallModelBundle, detections: list[SquallDetection]) -> dict[str, object]:
    return {
        'calibration': CALIBRATION,
        'threshold': bundle.threshold,
        'detections': [
            {
                'probability': detection.probability,
                'classifier_probability': detection.classifier_probability,
                'pattern_score': detection.pattern_score,
                'confidence': detection.confidence,
                'affected_polygon': detection.affected_polygon,
                'arrival_by_buoy': detection.arrival_by_buoy,
                'propagation': detection.propagation,
                'features': detection.features,
                'as_of': detection.as_of,
            }
            for detection in detections
        ],
        'top_features': bundle.top_features,
        'evaluation': bundle.evaluation,
    }
