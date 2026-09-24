from datetime import UTC, datetime, timedelta

from app.incidents.triage import flood_status, triage_key

NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


def _event(event_id, *, acknowledged=False, corroborated=False, age_seconds=0, vessel=None):
    return {
        'id': event_id,
        'vessel_id': vessel or f'V{event_id}',
        'acknowledged_at': NOW if acknowledged else None,
        'created_at': NOW - timedelta(seconds=age_seconds),
        'corroborated': corroborated,
    }


def test_triage_orders_unacknowledged_then_corroborated_then_newest():
    rows = [
        _event(1, acknowledged=True, corroborated=True),
        _event(2, corroborated=False, age_seconds=1),
        _event(3, corroborated=True, age_seconds=20),
        _event(4, corroborated=True, age_seconds=1),
    ]
    assert [row['id'] for row in sorted(rows, key=triage_key)] == [4, 3, 2, 1]


def test_flood_status_counts_distinct_unknown_vessels_in_last_minute():
    rows = [_event(i, age_seconds=30) for i in range(10)]
    rows.extend([_event(99, age_seconds=30, vessel='V0'), _event(100, age_seconds=61)])
    assert flood_status(rows, NOW) == {'unknown_vessels_last_minute': 10, 'active': False}
    rows.append(_event(101, age_seconds=30))
    assert flood_status(rows, NOW) == {'unknown_vessels_last_minute': 11, 'active': True}


def test_flood_status_ignores_corroborated_events():
    rows = [_event(i, corroborated=True, age_seconds=30) for i in range(20)]
    assert flood_status(rows, NOW) == {'unknown_vessels_last_minute': 0, 'active': False}
