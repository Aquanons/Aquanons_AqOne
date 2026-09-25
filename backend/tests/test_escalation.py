from datetime import UTC, datetime, timedelta

from app.incidents.escalation import ESCALATE_AFTER, due_for_escalation, escalation_text


def test_due_for_escalation_excludes_acknowledged_synthetic_resolved_and_already_escalated():
    now = datetime.now(UTC)
    old = now - ESCALATE_AFTER - timedelta(seconds=1)
    events = [
        {'id': 1, 'created_at': old, 'vessel_id': 'V1'},
        {'id': 2, 'created_at': old, 'vessel_id': 'V2', 'acknowledged_at': now},
        {'id': 3, 'created_at': old, 'vessel_id': 'V3', 'is_synthetic': True},
        {'id': 4, 'created_at': old, 'vessel_id': 'V4', 'resolved_at': now},
        {'id': 5, 'created_at': old, 'vessel_id': 'V5', 'escalated_at': now},
    ]
    assert [event['id'] for event in due_for_escalation(events, now)] == [1]


def test_due_for_escalation_requires_open_old_real_unacknowledged_event():
    now = datetime.now(UTC)
    old = now - ESCALATE_AFTER - timedelta(seconds=1)
    assert due_for_escalation([{'id': 1, 'created_at': old, 'vessel_id': 'V1'}], now)[0]['id'] == 1
    assert due_for_escalation([{'id': 1, 'created_at': now, 'vessel_id': 'V1'}], now) == []


def test_escalation_text_is_short_and_names_vessel_position_and_time():
    event = {
        'vessel_id': 'V-17', 'boat_name': 'Bangka 17', 'latitude': 11.7, 'longitude': 122.3,
        'created_at': datetime(2026, 9, 24, 8, 15, tzinfo=UTC),
    }
    text = escalation_text(event)
    assert len(text) <= 160
    assert 'Bangka 17' in text
    assert '11.7' in text and '122.3' in text
    assert '2026-09-24' in text
