"""Squall nowcast evaluation - a report card, not part of the running system
(docs/18_BACKEND_STRUCTURE.md). Writes to models/eval_results.json via
eval_store.write_section(), read back by GET /api/ai/metrics for the
dashboard's SAR tab. Never trains or saves the deployed model - that is
POST /api/ai/squall/train's job alone (app/api/squall.py), gated by
ALLOW_TRAINING. This script fits its own throwaway pipeline purely to score
it on held-out data, and discards it.

Repairs the evaluation protocol docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md
Phase 4 flags: the previous version's "evaluation" was nothing but
train_from_rows()'s internal random GroupShuffleSplit, exposed as a side
effect of training - no time separation, no location separation, no
calibration/false-alert reporting, and no accounting for low-quality windows
(which extract_pressure_features() would have silently filled with a nominal
1013.25 hPa baseline and scored as calm). This version:

  - Splits *events* by time, training on the earlier half and scoring only
    the later half - a model must never see a "future" event during
    training. The synthetic generator (app/simulation/generator.py) assigns
    each event's front origin independently of its start time, so this also
    incidentally scatters test events across different locations; forcing an
    explicit joint time+location partition on top of that would fragment an
    already-small event count for a demo dataset, so location separation
    here is opportunistic, not engineered.
  - Runs assess_array_quality() (app/ai/squall.py, Phase 2) on every
    candidate window before scoring it. A quality-failing window is counted
    as excluded, never scored as calm.
  - Compares the trained model against a fixed, untuned pressure-tendency
    baseline. Per the plan: if the model does not beat it on the held-out
    split, the simpler baseline is the recommendation.

Retained as explicitly labelled synthetic demo evidence, not field
validation - see the `note` field in every section this script writes, and
docs/08_DEMO_AND_STATUS.md's field-validation log template for what
validation actually requires.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import asyncpg
import numpy as np

from app.ai.eval_store import write_section
from app.ai.squall import (
    DEFAULT_THRESHOLD,
    FEATURE_NAMES,
    LOOKBACK_MINUTES,
    PressureReading,
    _ensure_tz,
    _top_features,
    _train_pipeline,
    _window_score,
    assess_array_quality,
    build_buoys,
    build_history,
    extract_pressure_features,
)

LEAD_TIMES_MINUTES = (30, 45, 60, 75, 90)

# A fixed, untuned threshold on the array's pressure drop across the
# lookback window (feature 'array_drop_hpa') - the simplest rule a human can
# audit without any ML background. Not fit to any split, so it carries no
# leakage risk on its own (docs/39 Phase 4 item 2: "transparent
# pressure-tendency baseline"). 1.5 hPa is a round, physically-motivated
# figure well inside the generator's simulated event drops (3-6 hPa over an
# event, see app/simulation/generator.py) without being so loose it fires on
# ordinary diurnal pressure variation.
BASELINE_ARRAY_DROP_THRESHOLD_HPA = 1.5


@dataclass(frozen=True)
class EvalWindow:
    as_of: datetime
    label: int
    group_id: str
    lead_minutes: int | None
    split: str  # 'train' | 'test'


def _build_windows(
    history: dict[str, list[PressureReading]],
    squalls: list[dict[str, Any]],
    *,
    seed: int,
) -> list[EvalWindow]:
    events = sorted(squalls, key=lambda event: _ensure_tz(event['started_at']))
    if len(events) < 2:
        raise ValueError(
            f'time-split evaluation needs at least 2 events to separate train from test, got {len(events)}'
        )
    split_index = max(1, len(events) // 2)
    train_events, test_events = events[:split_index], events[split_index:]
    cutoff = _ensure_tz(test_events[0]['started_at'])

    windows: list[EvalWindow] = []
    protected_ranges: list[tuple[datetime, datetime]] = []
    for split, group in (('train', train_events), ('test', test_events)):
        for event in group:
            has_peak = event.get('peak_at') is not None and event.get('is_synthetic')
            raw_target = event['peak_at'] if has_peak else event['started_at']
            target_at = _ensure_tz(raw_target)
            protected_ranges.append(
                (target_at - timedelta(minutes=LOOKBACK_MINUTES), target_at + timedelta(minutes=180))
            )
            for lead in LEAD_TIMES_MINUTES:
                windows.append(EvalWindow(target_at - timedelta(minutes=lead), 1, f'event-{event["id"]}', lead, split))

    all_times = sorted({reading.observed_at for series in history.values() for reading in series})
    rng = np.random.default_rng(seed)
    negatives = [ts for ts in all_times if not any(start <= ts <= end for start, end in protected_ranges)]
    rng.shuffle(negatives)
    positive_count = max(1, sum(1 for w in windows))
    for index, ts in enumerate(negatives[:positive_count]):
        split = 'train' if ts < cutoff else 'test'
        windows.append(EvalWindow(ts, 0, f'neg-{index}', None, split))
    return windows


def _metrics(
    labels: list[int], probabilities: list[float], leads: list[int | None], *, threshold: float
) -> dict[str, float]:
    predictions = [1 if p >= threshold else 0 for p in probabilities]
    tp = sum(1 for label, pred in zip(labels, predictions, strict=True) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions, strict=True) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions, strict=True) if label == 1 and pred == 0)
    tn = sum(1 for label, pred in zip(labels, predictions, strict=True) if label == 0 and pred == 0)
    hit_leads = [
        lead
        for label, pred, lead in zip(labels, predictions, leads, strict=True)
        if label == 1 and pred == 1 and lead is not None
    ]
    return {
        'precision': tp / max(1, tp + fp),
        'recall': tp / max(1, tp + fn),
        'mean_lead_time_minutes': float(np.mean(hit_leads)) if hit_leads else 0.0,
        'false_alert_rate': fp / max(1, fp + tn),
        # A hard 0/1 baseline decision degenerates the Brier score to a
        # misclassification rate - expected, and still a valid comparison
        # point against the model's calibrated probabilities.
        'brier_score': float(np.mean([(prob - label) ** 2 for prob, label in zip(probabilities, labels, strict=True)])),
    }


def evaluate(
    rows: list[dict[str, Any]],
    squalls: list[dict[str, Any]],
    buoy_rows: list[dict[str, Any]],
    *,
    seed: int = 42,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, object]:
    """Pure aggregate-metrics computation - no I/O, so this can be exercised
    by regression tests without a database (mirrors trip_profile_eval.py's
    evaluate())."""
    buoys = build_buoys(buoy_rows)
    history = build_history(rows)
    windows = _build_windows(history, squalls, seed=seed)

    train_x: list[list[float]] = []
    train_y: list[int] = []
    test_labels: list[int] = []
    test_leads: list[int | None] = []
    test_drops: list[float] = []
    test_features: list[list[float]] = []
    test_bundles: list[Any] = []
    excluded = {'train': 0, 'test': 0}

    for window in windows:
        quality = assess_array_quality(history, buoys, window.as_of)
        if not quality.ok:
            excluded[window.split] += 1
            continue

        qualifying_ids = set(quality.qualifying_buoy_ids)
        filtered_history = {buoy_id: series for buoy_id, series in history.items() if buoy_id in qualifying_ids}
        filtered_buoys = {buoy_id: meta for buoy_id, meta in buoys.items() if buoy_id in qualifying_ids}
        bundle = extract_pressure_features(filtered_history, filtered_buoys, window.as_of)

        if window.split == 'train':
            train_x.append(bundle.values)
            train_y.append(window.label)
        else:
            test_labels.append(window.label)
            test_leads.append(window.lead_minutes)
            test_drops.append(bundle.to_features()['array_drop_hpa'])
            test_features.append(bundle.values)
            test_bundles.append(bundle)

    if not train_x or not test_features:
        raise ValueError('not enough quality-passing windows on one or both sides of the time split to evaluate')

    pipeline = _train_pipeline(np.asarray(train_x), np.asarray(train_y), seed)
    raw_probabilities = pipeline.predict_proba(np.asarray(test_features))[:, 1].tolist()
    composed_probabilities = [
        max(p, _window_score(b))
        for p, b in zip(raw_probabilities, test_bundles, strict=True)
    ]
    baseline_probabilities = [1.0 if drop >= BASELINE_ARRAY_DROP_THRESHOLD_HPA else 0.0 for drop in test_drops]

    model_metrics = _metrics(test_labels, composed_probabilities, test_leads, threshold=threshold)
    baseline_metrics = _metrics(test_labels, baseline_probabilities, test_leads, threshold=0.5)

    # Simple dominance rule: the model only replaces the transparent
    # baseline as the recommendation if it is at least as good on both
    # axes - a model that trades recall for precision (or vice versa) has
    # not "improved" the baseline, it has just moved the tradeoff.
    model_wins = (
        model_metrics['precision'] >= baseline_metrics['precision']
        and model_metrics['recall'] >= baseline_metrics['recall']
    )

    return {
        'note': 'synthetic demo evidence only - not field validation',
        'train_events': len({w.group_id for w in windows if w.split == 'train' and w.label == 1}),
        'test_events': len({w.group_id for w in windows if w.split == 'test' and w.label == 1}),
        'excluded_low_quality_windows_train': excluded['train'],
        'excluded_low_quality_windows_test': excluded['test'],
        # Top-level precision/recall/mean_lead_time_minutes are the model's
        # held-out test-split numbers, kept at this flat shape (rather than
        # nested) for backward compatibility with web/js/dashboard/
        # dashboard-sar.js, which already reads results.squall.<key> - and
        # are proper time-separated figures now, not the old random split's.
        'precision': model_metrics['precision'],
        'recall': model_metrics['recall'],
        'mean_lead_time_minutes': model_metrics['mean_lead_time_minutes'],
        'false_alert_rate': model_metrics['false_alert_rate'],
        'brier_score': model_metrics['brier_score'],
        'baseline_precision': baseline_metrics['precision'],
        'baseline_recall': baseline_metrics['recall'],
        'baseline_mean_lead_time_minutes': baseline_metrics['mean_lead_time_minutes'],
        'baseline_false_alert_rate': baseline_metrics['false_alert_rate'],
        'baseline_brier_score': baseline_metrics['brier_score'],
        'baseline_threshold_hpa': BASELINE_ARRAY_DROP_THRESHOLD_HPA,
        'recommendation': 'model' if model_wins else 'baseline',
        'top_features': _top_features(pipeline, list(FEATURE_NAMES)),
    }


async def _load_rows(
    database_url: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    conn = await asyncpg.connect(database_url)
    try:
        readings = await conn.fetch(
            '''
            SELECT buoy_id, observed_at, pressure_hpa
            FROM barometric_readings
            WHERE is_synthetic = TRUE
            ORDER BY observed_at, buoy_id
            '''
        )
        squalls = await conn.fetch(
            '''
            SELECT id, started_at, peak_at, ended_at, center_lat, center_lon,
                   front_origin_lat, front_origin_lon, bearing_deg, speed_kph,
                   pressure_drop_hpa, rise_minutes, hold_minutes, observed_buoy_ids
            FROM squall_events
            WHERE is_synthetic = TRUE
            ORDER BY started_at
            '''
        )
        buoys = await conn.fetch(
            '''
            SELECT id, lat, lon, contact_radius_m
            FROM buoys
            WHERE is_synthetic = TRUE
            ORDER BY id
            '''
        )
    finally:
        await conn.close()
    return [dict(row) for row in readings], [dict(row) for row in squalls], [dict(row) for row in buoys]


async def main() -> None:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL is required')

    readings, squalls, buoy_rows = await _load_rows(database_url)
    if not readings or len(squalls) < 2:
        print('insufficient synthetic data for a time-split evaluation (need >= 2 squall_events rows)')
        return

    result = evaluate(readings, squalls, buoy_rows)
    print('[SYNTHETIC DEMO EVIDENCE - NOT FIELD VALIDATION]')
    print(f"train events: {result['train_events']}  test events: {result['test_events']}")
    print(
        f"excluded low-quality windows: train={result['excluded_low_quality_windows_train']} "
        f"test={result['excluded_low_quality_windows_test']}"
    )
    print(
        f"model:    precision={result['precision']:.3f} recall={result['recall']:.3f} "
        f"lead={result['mean_lead_time_minutes']:.1f}min "
        f"false_alert_rate={result['false_alert_rate']:.3%} brier={result['brier_score']:.3f}"
    )
    print(
        f"baseline: precision={result['baseline_precision']:.3f} recall={result['baseline_recall']:.3f} "
        f"lead={result['baseline_mean_lead_time_minutes']:.1f}min "
        f"false_alert_rate={result['baseline_false_alert_rate']:.3%} brier={result['baseline_brier_score']:.3f}"
    )
    print(f"recommendation: {result['recommendation']}")
    write_section('squall', {key: value for key, value in result.items()})


if __name__ == '__main__':
    asyncio.run(main())
