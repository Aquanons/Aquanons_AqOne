from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import timedelta

import asyncpg

from app.ai.anomaly_service import OPEN_TRIP_FRESHNESS_WINDOW
from app.ai.eval_store import write_section
from app.ai.trip_profile import (
    AnomalyScore,
    ContactPoint,
    build_profiles_from_contacts,
    score_trip,
)

# How far forward of a trip's last contact to sweep when checking whether it
# is ever misclassified as overdue. Matches
# app.ai.anomaly_service.OPEN_TRIP_FRESHNESS_WINDOW - the live pipeline never
# scores a trip past that age (it is excluded as stale first), so sweeping
# further here would measure a scenario production never actually reaches.
SWEEP_HORIZON_MINUTES = int(OPEN_TRIP_FRESHNESS_WINDOW.total_seconds() / 60)
SWEEP_STEP_MINUTES = 5


async def _load_rows(database_url: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch(
            '''
            SELECT bc.vessel_id, bc.trip_id, bc.buoy_id, bc.observed_at, bc.latitude, bc.longitude
            FROM buoy_contacts bc
            JOIN buoys b ON b.id = bc.buoy_id
            WHERE bc.is_synthetic = TRUE
            ORDER BY bc.vessel_id, bc.trip_id, bc.observed_at
            '''
        )
        incidents = await conn.fetch(
            'SELECT vessel_id, last_contact_at FROM incidents WHERE is_synthetic = TRUE ORDER BY id'
        )
    finally:
        await conn.close()
    return [dict(row) for row in rows], [dict(row) for row in incidents]


def _group(rows: list[dict[str, object]]) -> dict[tuple[str, str], list[ContactPoint]]:
    grouped: dict[tuple[str, str], list[ContactPoint]] = defaultdict(list)
    for row in rows:
        grouped[(str(row['vessel_id']), str(row['trip_id']))].append(
            ContactPoint(
                buoy_id=str(row['buoy_id']),
                observed_at=row['observed_at'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
            )
        )
    for contacts in grouped.values():
        contacts.sort(key=lambda item: item.observed_at)
    return grouped


def evaluate(rows: list[dict[str, object]], incidents: list[dict[str, object]]) -> dict[str, object]:
    """Pure aggregate-metrics computation - no I/O, so docs/38 Phase 4's
    regression tests can exercise it without a database.

    Both incident and normal trips now sweep `as_of` forward from the
    trip's own last contact, in the same 5-minute steps over the same
    12-hour horizon. Before this fix, a normal trip was instead re-scored
    at each of its own historical contact timestamps
    (`as_of = contacts[idx - 1].observed_at`) - never advancing past its own
    final contact - so `status == 'alert'` was only ever checked at moments
    the vessel was, by construction, still actively checking in.
    `false_alarm_rate` was therefore true by construction, not by
    measurement (docs/30_DEMO_DECISION_01_ANOMALY.md §1.1). Sweeping
    forward asks the real question: if this vessel went quiet right here
    and nothing more arrived, would the model eventually flag it anyway?
    """
    profiles = build_profiles_from_contacts(rows)
    grouped = _group(rows)
    incident_index = {(row['vessel_id'], row['last_contact_at']) for row in incidents}

    latencies: list[float] = []
    false_alarms = 0
    normal_trips = 0
    factor_example: AnomalyScore | None = None

    for (vessel_id, _trip_id), contacts in grouped.items():
        profile = profiles[vessel_id]
        last = contacts[-1]
        is_incident = (vessel_id, last.observed_at) in incident_index

        alerted_at: float | None = None
        alert_score: AnomalyScore | None = None
        for minutes in range(0, SWEEP_HORIZON_MINUTES + 1, SWEEP_STEP_MINUTES):
            as_of = last.observed_at + timedelta(minutes=minutes)
            score = score_trip(profile, contacts, as_of=as_of)
            if score.status == 'alert':
                alerted_at = float(minutes)
                alert_score = score
                break

        if is_incident:
            if alerted_at is not None:
                latencies.append(alerted_at)
                if factor_example is None:
                    factor_example = alert_score
        else:
            normal_trips += 1
            if alerted_at is not None:
                false_alarms += 1

    median_latency = 0.0 if not latencies else sorted(latencies)[len(latencies) // 2]
    false_alarm_rate = 0.0 if normal_trips == 0 else false_alarms / normal_trips

    return {
        'median_detection_latency_minutes': median_latency,
        'false_alarm_rate': false_alarm_rate,
        'incidents_detected': len(latencies),
        'normal_trips_evaluated': normal_trips,
        'eligible_normal_trips': normal_trips,
        'candidates_raised': false_alarms,
        # Every buoy_contacts row already requires a real, registered buoy
        # (the JOIN in _load_rows) and every grouped trip has at least one
        # contact, so this synthetic dataset has nothing to exclude for
        # staleness or missing coverage - reported honestly as 0 rather
        # than fabricated (docs/38 Phase 4 item 2).
        'excluded_stale_or_out_of_coverage': 0,
        'factor_breakdown_example': factor_example.to_response()['factors'] if factor_example is not None else None,
    }


async def main() -> None:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL is required')

    rows, incidents = await _load_rows(database_url)
    result = evaluate(rows, incidents)

    print(f'median_detection_latency_minutes: {result["median_detection_latency_minutes"]:.1f}')
    print(f'false_alarm_rate: {result["false_alarm_rate"]:.3%}')
    print(f'eligible_normal_trips: {result["eligible_normal_trips"]}')
    print(f'candidates_raised: {result["candidates_raised"]}')
    print(f'excluded_stale_or_out_of_coverage: {result["excluded_stale_or_out_of_coverage"]}')
    write_section(
        'trip_anomaly',
        {
            'median_detection_latency_minutes': result['median_detection_latency_minutes'],
            'false_alarm_rate': result['false_alarm_rate'],
            'incidents_detected': result['incidents_detected'],
            'normal_trips_evaluated': result['normal_trips_evaluated'],
            'eligible_normal_trips': result['eligible_normal_trips'],
            'candidates_raised': result['candidates_raised'],
            'excluded_stale_or_out_of_coverage': result['excluded_stale_or_out_of_coverage'],
        },
    )
    if result['factor_breakdown_example'] is not None:
        print('factor_breakdown_example:')
        print(json.dumps(result['factor_breakdown_example'], indent=2))


if __name__ == '__main__':
    asyncio.run(main())
