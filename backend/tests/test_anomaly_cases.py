"""Persistent responder-review cases (docs/38 Phase 3).

Covers: low- vs high-confidence routing to verification/responder_attention,
a case being created once (not duplicated) across repeated evaluation, each
responder action persisting through a later re-evaluation, and that a
public/handset caller cannot read or mutate the case queue.

`_FakeStore` doubles as both the raw connection `evaluate_and_persist` takes
directly, and the pool `app.api.anomaly_cases` acquires from - the same
object backs both so a test can evaluate, then act over HTTP, then
re-evaluate, and see one consistent in-memory case store throughout.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db as app_db
from app.ai import anomaly_service
from app.api import anomaly_cases as anomaly_cases_api
from app.auth import create_token
from app.main import app


def _operator_headers() -> dict[str, str]:
    return {'Authorization': f'Bearer {create_token(1, "ranger@example.com", "mdrrmo")}'}


def _row(vessel_id: str, trip_id: str, buoy_id: str, observed_at: datetime) -> dict[str, object]:
    return {
        'vessel_id': vessel_id,
        'trip_id': trip_id,
        'buoy_id': buoy_id,
        'observed_at': observed_at,
        'latitude': 11.7,
        'longitude': 122.5,
        'is_synthetic': False,
    }


def _overdue_current_trip(vessel_id: str, day: int) -> list[dict[str, object]]:
    start = datetime(2026, 8, day, 6, 0, tzinfo=UTC)
    return [
        _row(vessel_id, 'trip-current', 'B01', start),
        _row(vessel_id, 'trip-current', 'B02', start + timedelta(minutes=45)),
    ]


def _history(vessel_id: str, trip_count: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for day in range(1, trip_count + 1):
        start = datetime(2026, 8, day, 6, 0, tzinfo=UTC)
        for index, buoy_id in enumerate(('B01', 'B02', 'B03')):
            rows.append(_row(vessel_id, f'trip-{day}', buoy_id, start + timedelta(minutes=45 * index)))
    return rows


def _fleet_rows() -> list[dict[str, object]]:
    """V-COLDSTART has only one prior trip (< minimum_trips_for_confidence,
    so low_confidence) plus an overdue current trip. V-ESTABLISHED has four
    (well past the threshold) plus the same shape of overdue current trip.
    Both are overdue at the as_of values these tests use.
    """
    return (
        _history('V-COLDSTART', 1)
        + _overdue_current_trip('V-COLDSTART', 10)
        + _history('V-ESTABLISHED', 4)
        + _overdue_current_trip('V-ESTABLISHED', 10)
    )


class _FakeStore:
    def __init__(self, contact_rows: list[dict[str, object]]) -> None:
        self.contact_rows = contact_rows
        self.cases: dict[tuple[str, str], dict[str, object]] = {}
        self._next_case_id = 1
        self.audit_events: list[dict[str, object]] = []

    # --- raw-connection interface, used directly by evaluate_and_persist ---
    async def fetch(self, query: str, *args):
        if 'FROM buoy_contacts' in query:
            return self.contact_rows
        if 'FROM anomaly_cases' in query:
            open_cases = [c for c in self.cases.values() if c['resolved_at'] is None]
            return sorted(open_cases, key=lambda c: c['updated_at'], reverse=True)
        return []

    async def execute(self, query: str, *args):
        if 'INSERT INTO operations_audit_events' in query:
            (
                actor_user_id, actor_email, actor_role, action, resource_type,
                resource_id, outcome, correlation_key, is_demo, metadata,
            ) = args
            self.audit_events.append({
                'actor_user_id': actor_user_id,
                'actor_email': actor_email,
                'actor_role': actor_role,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'outcome': outcome,
                'correlation_key': correlation_key,
                'is_demo': is_demo,
                'metadata': metadata,
            })
            return 'INSERT 0 1'
        if 'INSERT INTO anomaly_cases' in query:
            vessel_id, trip_id, case_type, score, status, reasons, source, score_at, last_contact_at, is_synth = args
            key = (vessel_id, trip_id)
            case = self.cases.get(key)
            if case is None:
                case = {
                    'id': self._next_case_id,
                    'vessel_id': vessel_id,
                    'trip_id': trip_id,
                    'created_at': datetime.now(UTC),
                    'acknowledged_at': None,
                    'acknowledged_by': None,
                    'dismissed_at': None,
                    'dismissed_by': None,
                    'dismissed_reason': None,
                    'escalated_at': None,
                    'escalated_by': None,
                    'escalated_reason': None,
                    'resolved_at': None,
                    'resolved_by': None,
                }
                self._next_case_id += 1
                self.cases[key] = case
            case.update(
                case_type=case_type,
                score=score,
                status=status,
                reasons=reasons,
                source=source,
                score_evaluated_at=score_at,
                last_contact_at=last_contact_at,
                is_synthetic=is_synth,
                updated_at=datetime.now(UTC),
            )
        return 'OK'

    # --- pool interface, used by app.api.anomaly_cases via get_pool() ---
    def acquire(self):
        return self

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    def _by_id(self, case_id: int) -> dict[str, object] | None:
        for case in self.cases.values():
            if case['id'] == case_id:
                return case
        return None

    async def fetchrow(self, query: str, *args):
        if query.startswith('SELECT') and 'FOR UPDATE' in query:
            case = self._by_id(args[0])
            if case is None:
                return None
            for column in ('acknowledged_at', 'dismissed_at', 'escalated_at', 'resolved_at'):
                if column in query:
                    return {column: case[column]}
            return None
        if 'UPDATE anomaly_cases' not in query:
            return None
        case_id = args[0]
        case = self._by_id(case_id)
        if case is None:
            return None
        if 'acknowledged_at' in query:
            _, actor = args
            case['acknowledged_at'] = case['acknowledged_at'] or datetime.now(UTC)
            case['acknowledged_by'] = case['acknowledged_by'] or actor
        elif 'dismissed_at' in query:
            _, actor, reason = args
            case['dismissed_at'] = case['dismissed_at'] or datetime.now(UTC)
            case['dismissed_by'] = case['dismissed_by'] or actor
            case['dismissed_reason'] = case['dismissed_reason'] or reason
        elif 'escalated_at' in query:
            _, actor, reason = args
            case['escalated_at'] = case['escalated_at'] or datetime.now(UTC)
            case['escalated_by'] = case['escalated_by'] or actor
            case['escalated_reason'] = case['escalated_reason'] or reason
        elif 'resolved_at' in query:
            _, actor = args
            case['resolved_at'] = case['resolved_at'] or datetime.now(UTC)
            case['resolved_by'] = case['resolved_by'] or actor
        return dict(case)


def _evaluate(store: _FakeStore, *, as_of: datetime) -> None:
    asyncio.run(anomaly_service.evaluate_and_persist(store, as_of=as_of, include_synthetic=False))


def test_low_confidence_routes_to_verification_and_high_confidence_to_responder_attention():
    store = _FakeStore(_fleet_rows())
    _evaluate(store, as_of=datetime(2026, 8, 10, 10, 0, tzinfo=UTC))

    assert store.cases[('V-COLDSTART', 'trip-current')]['case_type'] == 'verification'
    assert store.cases[('V-ESTABLISHED', 'trip-current')]['case_type'] == 'responder_attention'


def test_case_is_created_once_across_repeated_evaluation():
    store = _FakeStore(_fleet_rows())
    _evaluate(store, as_of=datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
    first_id = store.cases[('V-ESTABLISHED', 'trip-current')]['id']

    _evaluate(store, as_of=datetime(2026, 8, 10, 13, 0, tzinfo=UTC))
    second_id = store.cases[('V-ESTABLISHED', 'trip-current')]['id']

    assert first_id == second_id
    assert len(store.cases) == 2  # one per vessel, never duplicated per run


def test_responder_action_survives_a_later_re_evaluation(monkeypatch):
    store = _FakeStore(_fleet_rows())
    monkeypatch.setattr(app_db, 'get_pool', lambda: store)
    monkeypatch.setattr(anomaly_cases_api, 'get_pool', lambda: store)

    _evaluate(store, as_of=datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
    case_id = store.cases[('V-ESTABLISHED', 'trip-current')]['id']

    with TestClient(app, raise_server_exceptions=False) as client:
        ack = client.post(f'/api/ai/anomaly/cases/{case_id}/acknowledge', headers=_operator_headers())
    assert ack.status_code == 200
    assert ack.json()['acknowledged_by'] == 'ranger@example.com'

    # A later evaluation refreshes the score snapshot but must not touch the
    # acknowledgement - the whole point of keeping them in separate columns.
    _evaluate(store, as_of=datetime(2026, 8, 10, 12, 0, tzinfo=UTC))

    case = store.cases[('V-ESTABLISHED', 'trip-current')]
    assert case['id'] == case_id
    assert case['acknowledged_by'] == 'ranger@example.com'
    assert case['acknowledged_at'] is not None

    with TestClient(app, raise_server_exceptions=False) as client:
        listing = client.get('/api/ai/anomaly/cases/open', headers=_operator_headers())
    body = next(row for row in listing.json() if row['id'] == case_id)
    assert body['acknowledged_by'] == 'ranger@example.com'


def test_dismiss_requires_a_reason_and_is_idempotent(monkeypatch):
    store = _FakeStore(_fleet_rows())
    monkeypatch.setattr(app_db, 'get_pool', lambda: store)
    monkeypatch.setattr(anomaly_cases_api, 'get_pool', lambda: store)
    _evaluate(store, as_of=datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
    case_id = store.cases[('V-ESTABLISHED', 'trip-current')]['id']

    with TestClient(app, raise_server_exceptions=False) as client:
        missing_reason = client.post(f'/api/ai/anomaly/cases/{case_id}/dismiss', json={}, headers=_operator_headers())
        assert missing_reason.status_code == 422

        first = client.post(
            f'/api/ai/anomaly/cases/{case_id}/dismiss',
            json={'reason': 'known route deviation, confirmed safe by radio'},
            headers=_operator_headers(),
        )
        second = client.post(
            f'/api/ai/anomaly/cases/{case_id}/dismiss',
            json={'reason': 'a different reason should not overwrite the first'},
            headers=_operator_headers(),
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['dismissed_reason'] == second.json()['dismissed_reason']


def test_escalate_requires_a_reason(monkeypatch):
    store = _FakeStore(_fleet_rows())
    monkeypatch.setattr(app_db, 'get_pool', lambda: store)
    monkeypatch.setattr(anomaly_cases_api, 'get_pool', lambda: store)
    _evaluate(store, as_of=datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
    case_id = store.cases[('V-ESTABLISHED', 'trip-current')]['id']

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f'/api/ai/anomaly/cases/{case_id}/escalate',
            json={'reason': 'no radio contact, dispatching nearest vessel'},
            headers=_operator_headers(),
        )

    assert response.status_code == 200
    assert response.json()['escalated_reason'] == 'no radio contact, dispatching nearest vessel'

    # docs/41 Phase 2: one redacted audit event, and the free-text reason
    # never appears in it.
    assert len(store.audit_events) == 1
    event = store.audit_events[0]
    assert event['action'] == 'anomaly.escalate'
    assert event['outcome'] == 'updated'
    assert 'no radio contact' not in event['metadata']


def test_resolve_is_idempotent_and_leaves_the_case_out_of_open_listing(monkeypatch):
    store = _FakeStore(_fleet_rows())
    monkeypatch.setattr(app_db, 'get_pool', lambda: store)
    monkeypatch.setattr(anomaly_cases_api, 'get_pool', lambda: store)
    _evaluate(store, as_of=datetime(2026, 8, 10, 10, 0, tzinfo=UTC))
    case_id = store.cases[('V-ESTABLISHED', 'trip-current')]['id']

    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f'/api/ai/anomaly/cases/{case_id}/resolve', headers=_operator_headers())
        listing = client.get('/api/ai/anomaly/cases/open', headers=_operator_headers())

    assert all(row['id'] != case_id for row in listing.json())


def test_public_caller_cannot_read_or_mutate_the_case_queue(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/ai/anomaly/cases/open').status_code == 401
        assert client.post('/api/ai/anomaly/cases/1/acknowledge').status_code == 401
        assert client.post('/api/ai/anomaly/cases/1/dismiss', json={'reason': 'x'}).status_code == 401
        assert client.post('/api/ai/anomaly/cases/1/escalate', json={'reason': 'x'}).status_code == 401
        assert client.post('/api/ai/anomaly/cases/1/resolve').status_code == 401
