"""Replaying a stored synthetic incident.

The drift evaluator (`drift_eval.py`) and the dashboard's synthetic replay
(`GET /api/ai/drift/incident/{id}` without a stored run) call this one
function, so the rings a presenter shows are the rings that were scored: the
same horizon, the truth track's own span, and the same synthetic wind the
simulator generated the track with (docs/71 RND-07).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.ai.drift import DriftResult, ObjectClass, _synthetic_wind_series, predict_drift

# The simulator samples a truth track every 30 minutes (TRACK_STEP in
# app/simulation/generator.py); used only for points without timestamps.
TRACK_STEP_HOURS = 0.5


def resolved_object_class(object_class: str | None, abnormal_reason: str | None) -> ObjectClass:
    """A stored object class wins; rows predating that column fall back to
    the old heuristic from the abnormal reason."""
    if object_class:
        return ObjectClass(object_class)
    if str(abnormal_reason) in {'capsize', 'adverse_weather'}:
        return ObjectClass.swamped_banca
    return ObjectClass.intact_hull_adrift


def replay_horizon_hours(true_track: list[dict[str, Any]] | None) -> float | None:
    """How long the truth track runs, in hours; None when it has no length."""
    if not true_track or len(true_track) < 2:
        return None
    first, last = true_track[0].get('observed_at'), true_track[-1].get('observed_at')
    if first and last:
        return (_at(last) - _at(first)).total_seconds() / 3600.0
    return (len(true_track) - 1) * TRACK_STEP_HOURS


def replay_prediction(
    *,
    last_lat: float,
    last_lon: float,
    observed_at: datetime,
    object_class: ObjectClass,
    true_track: list[dict[str, Any]] | None,
    current_vector_fn: Callable | None = None,
) -> tuple[DriftResult, float] | None:
    """The prediction for a synthetic incident at its truth track's horizon,
    with the horizon used; None when the track is too short to evaluate."""
    horizon = replay_horizon_hours(true_track)
    if horizon is None or horizon <= 0:
        return None
    kwargs: dict[str, Any] = dict(
        last_lat=last_lat,
        last_lon=last_lon,
        observed_at=observed_at,
        object_class=object_class,
        forecast_hours=horizon,
        wind_provider=_synthetic_wind_series,
    )
    if current_vector_fn is not None:
        kwargs['current_vector_fn'] = current_vector_fn
    return predict_drift(**kwargs), horizon


def _at(value: Any) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
