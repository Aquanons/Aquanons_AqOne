from datetime import UTC, datetime, timedelta

from app.incidents.downlink import DOWNLINK_MAX, select_downlink

NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


def _event(event_id, *, acknowledged=False, resolved=False, changed=0, synthetic=False):
    created = NOW - timedelta(minutes=changed + 1)
    return {
        'id': event_id,
        'vessel_id': f'V{event_id}',
        'created_at': created,
        'acknowledged_at': created if acknowledged else None,
        'resolved_at': created if resolved else None,
        'reopened_at': None,
        'fisher_replied_at': None,
        'is_synthetic': synthetic,
    }


def test_downlink_never_exceeds_smallest_radio_table():
    selected = select_downlink([_event(i, acknowledged=True) for i in range(30)], NOW)
    assert len(selected) == DOWNLINK_MAX == 12


def test_downlink_prioritizes_acknowledged_then_open_then_resolved():
    rows = [
        _event(1, resolved=True),
        _event(2),
        _event(3, acknowledged=True),
    ]
    assert [row['id'] for row in select_downlink(rows, NOW)] == [3, 2, 1]


def test_downlink_orders_latest_change_first_within_each_band():
    rows = [_event(1, acknowledged=True), _event(2, acknowledged=True, changed=10)]
    assert [row['id'] for row in select_downlink(rows, NOW)] == [1, 2]


def test_downlink_excludes_synthetic_rows():
    rows = [_event(1, acknowledged=True, synthetic=True), _event(2, acknowledged=True)]
    assert [row['id'] for row in select_downlink(rows, NOW)] == [2]


def test_downlink_excludes_stale_open_and_expired_resolved_rows():
    stale_open = _event(1)
    stale_open['created_at'] = NOW - timedelta(hours=25)
    expired_resolved = _event(2, resolved=True)
    expired_resolved['resolved_at'] = NOW - timedelta(hours=7)
    current = _event(3)
    assert [row['id'] for row in select_downlink([stale_open, expired_resolved, current], NOW)] == [3]
