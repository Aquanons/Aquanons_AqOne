"""Backend responder loop: acknowledged SOS events stay visible until resolved.

Phase 2 of docs/36_MANUAL_SOS_RESPONDER_LOOP_IMPLEMENTATION_PLAN.md. Before this
change, `/api/sos/active` dropped an incident the instant it was acknowledged,
so a dispatcher never saw the fisher's subsequent STILL_IN_DANGER / SAFE_NOW
reply. These tests pin the observed behaviour of the API - the active feed,
the acknowledgement, and the reply - not the SQL text, so the queries in
app/api/sos.py stay free to change shape.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import sos as sos_api
from app.auth import create_token, create_vessel_device_token
from app.main import app


class _FakePool:
    """An in-memory stand-in for the SOS rows this phase's queries touch.

    Mirrors the real SQL's semantics (COALESCE-style idempotency, the
    once-resolved-stays-resolved guard) in Python rather than in a real
    database, matched loosely on query text so it does not pin exact SQL.
    """

    def __init__(self) -> None:
        self.devices: dict[int, dict[str, object]] = {
            1: {'id': 1, 'vessel_id': 'V001', 'label': 'Handset A', 'revoked_at': None},
            2: {'id': 2, 'vessel_id': 'V002', 'label': 'Handset B', 'revoked_at': None},
        }
        self.sos_events: dict[int, dict[str, object]] = {}
        self.audit_events: list[dict[str, object]] = []

    def seed(self, **row: object) -> dict[str, object]:
        base: dict[str, object] = {
            'vessel_id': 'V001',
            'boat': 'NW-001',
            'latitude': None,
            'longitude': None,
            'note': None,
            'trust_tier': 'self_declared',
            'client_ts': 1755248500,
            'local_id': None,
            'seq': None,
            'delivered_direct': True,
            'delivered_via_buoy': False,
            'buoy_id': None,
            'created_at': datetime.now(UTC),
            'acknowledged_at': None,
            'acked_by': None,
            'eta_at': None,
            'responder_status': None,
            'responder_note': None,
            'fisher_reply': None,
            'fisher_replied_at': None,
            'resolved_at': None,
            'resolved_by': None,
            'resolved_reason': None,
            'is_synthetic': False,
        }
        base.update(row)
        self.sos_events[int(row['id'])] = base
        return base

    def acquire(self):
        return self

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

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
        return 'OK'

    async def fetch(self, query: str, *args):
        if 'FROM sos_events' in query and 'resolved_at IS NULL' in query:
            return [row for row in self.sos_events.values() if row['resolved_at'] is None]
        if 'FROM sos_events' in query and 'resolved_at IS NOT NULL' in query:
            return [row for row in self.sos_events.values() if row['resolved_at'] is not None]
        return []

    async def fetchrow(self, query: str, *args):
        if 'WHERE local_id = $1' in query and 'SELECT id, vessel_id' in query:
            matches = [e for e in self.sos_events.values() if e.get('local_id') == args[0]]
            return matches[0] if matches else None

        if 'UPDATE vessel_devices' in query and 'SET last_seen_at = NOW()' in query:
            return self.devices.get(int(args[0]))

        if 'SELECT resolved_at FROM sos_events' in query:
            event = self.sos_events.get(int(args[0]))
            if event is None:
                return None
            return {'resolved_at': event['resolved_at']}

        if 'UPDATE sos_events' in query and 'SET acknowledged_at' in query:
            event_id, acked_by, responder_status, responder_note, eta_minutes = args
            event = self.sos_events.get(int(event_id))
            if event is None:
                return None
            event['acknowledged_at'] = event['acknowledged_at'] or datetime.now(UTC)
            event['acked_by'] = acked_by
            event['responder_status'] = responder_status
            if responder_note is not None:
                event['responder_note'] = responder_note
            if eta_minutes is not None:
                event['eta_at'] = datetime.now(UTC) + timedelta(minutes=eta_minutes)
            return event

        if 'UPDATE sos_events' in query and 'SET resolved_at = NULL' in query:
            event = self.sos_events.get(int(args[0]))
            if event is None:
                return None
            event['resolved_at'] = None
            event['resolved_by'] = None
            event['resolved_reason'] = None
            return event

        if 'UPDATE sos_events' in query and 'SET resolved_at' in query:
            event_id, resolved_by, resolved_reason = args
            event = self.sos_events.get(int(event_id))
            if event is None:
                return None
            event['resolved_at'] = event['resolved_at'] or datetime.now(UTC)
            event['resolved_by'] = event['resolved_by'] or resolved_by
            event['resolved_reason'] = event['resolved_reason'] or resolved_reason
            return event

        if 'UPDATE sos_events' in query and 'SET fisher_reply' in query:
            event_id, reply, safe_now, vessel_id = args
            event = self.sos_events.get(int(event_id))
            if event is None or event['vessel_id'] != vessel_id:
                return None
            if event['resolved_at'] is None:
                event['fisher_reply'] = reply
                event['fisher_replied_at'] = datetime.now(UTC)
                if reply == safe_now:
                    event['resolved_at'] = datetime.now(UTC)
            return event

        return None


def _patch(monkeypatch, pool: _FakePool) -> None:
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)


def _operator_headers() -> dict[str, str]:
    token = create_token(1, 'ranger@example.com', 'mdrrmo')
    return {'Authorization': f'Bearer {token}'}


def test_acknowledge_stores_a_server_derived_absolute_eta_and_status(monkeypatch):
    pool = _FakePool()
    pool.seed(id=1)
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/sos/1/acknowledge',
            headers=_operator_headers(),
            json={'eta_minutes': 20, 'responder_status': 2, 'responder_note': 'On the way'},
        )

    assert response.status_code == 200
    body = response.json()
    assert body['responder_status'] == 2
    assert body['responder_note'] == 'On the way'
    now = datetime.now(UTC)
    eta = datetime.fromisoformat(body['eta_at'])
    # An absolute timestamp derived from the server's clock, not the 20
    # verbatim - see docs/13_RESPONDER_LOOP.md on why a duration is wrong.
    assert now < eta < now + timedelta(minutes=21)

    # docs/41 Phase 2: one redacted audit event, and never the free-text note.
    assert len(pool.audit_events) == 1
    event = pool.audit_events[0]
    assert event['action'] == 'sos.acknowledge'
    assert event['resource_type'] == 'sos_event'
    assert event['metadata'] == '{"responder_status": 2}'
    assert 'On the way' not in event['metadata']


def test_resolve_records_one_audit_event_and_a_retry_is_no_change(monkeypatch):
    pool = _FakePool()
    pool.seed(id=7, acknowledged_at=datetime.now(UTC), acked_by='ranger-01')
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post('/api/sos/7/resolve', headers=_operator_headers())
        second = client.post('/api/sos/7/resolve', headers=_operator_headers())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['resolved_at'] == second.json()['resolved_at']
    assert [e['outcome'] for e in pool.audit_events] == ['updated', 'no_change']
    assert all(e['action'] == 'sos.resolve' for e in pool.audit_events)


def test_resolve_records_a_distinct_resolver_and_reason(monkeypatch):
    """docs/41 Phase 3: resolving previously reused `acked_by` for the
    resolver too and recorded no reason at all - resolved_by/resolved_reason
    must now be distinct from whoever acknowledged, and the reason (free
    text) must never leak into the audit metadata.
    """
    pool = _FakePool()
    pool.seed(id=8, acknowledged_at=datetime.now(UTC), acked_by='ranger-01')
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/sos/8/resolve',
            headers=_operator_headers(),
            json={'reason': 'vessel returned safely to port'},
        )

    assert response.status_code == 200
    body = response.json()
    assert body['acked_by'] == 'ranger-01'
    assert body['resolved_by'] == 'ranger@example.com'
    assert body['resolved_reason'] == 'vessel returned safely to port'
    assert 'vessel returned safely' not in pool.audit_events[-1]['metadata']


def test_acknowledged_but_unresolved_sos_stays_in_the_active_feed(monkeypatch):
    pool = _FakePool()
    pool.seed(id=2, acknowledged_at=datetime.now(UTC), acked_by='ranger-01')
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/active', headers=_operator_headers())

    assert response.status_code == 200
    ids = [row['id'] for row in response.json()['events']]
    assert 2 in ids


def test_still_in_danger_reply_appears_on_the_active_event(monkeypatch):
    pool = _FakePool()
    pool.seed(id=3, acknowledged_at=datetime.now(UTC), acked_by='ranger-01')
    _patch(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        reply = client.post(
            '/api/sos/3/reply',
            headers={'Authorization': f'Bearer {token}'},
            json={'reply': 1},
        )
        active = client.get('/api/sos/active', headers=_operator_headers())

    assert reply.status_code == 200
    event = next(row for row in active.json()['events'] if row['id'] == 3)
    assert event['fisher_reply'] == 1
    assert event['resolved_at'] is None


def test_safe_now_resolves_and_removes_the_event_from_the_active_feed(monkeypatch):
    pool = _FakePool()
    pool.seed(id=4, acknowledged_at=datetime.now(UTC), acked_by='ranger-01')
    _patch(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        reply = client.post(
            '/api/sos/4/reply',
            headers={'Authorization': f'Bearer {token}'},
            json={'reply': 2},
        )
        active = client.get('/api/sos/active', headers=_operator_headers())

    assert reply.status_code == 200
    assert reply.json()['resolved_at'] is not None
    ids = [row['id'] for row in active.json()['events']]
    assert 4 not in ids


def test_retrying_the_reply_after_resolution_is_safe_and_cannot_reopen_it(monkeypatch):
    pool = _FakePool()
    pool.seed(id=5)
    _patch(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')
    headers = {'Authorization': f'Bearer {token}'}

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post('/api/sos/5/reply', headers=headers, json={'reply': 2})
        # A stray retry of the earlier "still in danger" tap, or the network
        # simply redelivering the SAFE_NOW request - either way this must not
        # change what was already recorded.
        second = client.post('/api/sos/5/reply', headers=headers, json={'reply': 1})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['resolved_at'] == second.json()['resolved_at']
    assert second.json()['fisher_reply'] == 2


def test_a_different_vessels_device_cannot_reply_to_the_event(monkeypatch):
    pool = _FakePool()
    pool.seed(id=6)
    _patch(monkeypatch, pool)
    other_device_token = create_vessel_device_token(2, 'V002')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/sos/6/reply',
            headers={'Authorization': f'Bearer {other_device_token}'},
            json={'reply': 1},
        )

    assert response.status_code == 404
    assert pool.sos_events[6]['fisher_reply'] is None


def test_unauthenticated_handset_reads_its_own_ack_by_local_id(monkeypatch):
    """The direct path raised this SOS with no credential, so reading its
    answer back must not demand one either (see the ack_by_local_id docstring,
    which mirrors the unauthenticated-ingest trust note in app/api/sos.py).
    """
    pool = _FakePool()
    pool.seed(
        id=9,
        local_id='1789406852548-9a5f31da',
        acknowledged_at=datetime.now(UTC),
        acked_by='ranger@example.com',
        eta_at=datetime.now(UTC) + timedelta(minutes=20),
        responder_status=2,
        responder_note='On the way',
    )
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/ack/1789406852548-9a5f31da')

    assert response.status_code == 200
    body = response.json()
    event = body['event']
    assert event['local_id'] == '1789406852548-9a5f31da'
    assert event['delivery_state'] == 'acknowledged'
    assert event['responder_status'] == 2
    assert event['responder_note'] == 'On the way'
    assert event['eta_at'] is not None
    assert event['resolved_at'] is None


def test_ack_by_local_id_returns_delivered_before_the_responder_answers(monkeypatch):
    """The incident exists on the backend but nobody has acked it yet - the
    phone learns its backend id (needed for replies) without any false claim
    that a responder answered.
    """
    pool = _FakePool()
    pool.seed(id=13, local_id='v1-ccc')
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/ack/v1-ccc')

    assert response.status_code == 200
    assert response.json()['event']['delivery_state'] == 'delivered'
    assert response.json()['event']['acknowledged_at'] is None


def test_ack_by_local_id_is_404_for_an_unknown_id(monkeypatch):
    pool = _FakePool()
    pool.seed(id=10)
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/ack/does-not-exist')

    assert response.status_code == 404


def test_ack_by_local_id_reveals_only_the_named_incidents_ack(monkeypatch):
    """Keyed on the handset's own id, the endpoint must never leak another
    incident - the display row should be the ack fields only, not the full
    vessel feed with coordinates and notes.
    """
    pool = _FakePool()
    pool.seed(id=11, local_id='v1-aaa')
    pool.seed(
        id=12,
        vessel_id='V002',
        local_id='v2-bbb',
        acked_by='ranger@example.com',
    )
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/ack/v2-bbb')

    assert response.status_code == 200
    body = response.json()
    assert body['vessel_id'] == 'V002'
    event = body['event']
    assert event['id'] == 12
    assert 'lat' not in event
    assert 'lon' not in event
    assert 'note' not in event


def test_recent_lists_only_resolved_incidents_with_sender_report(monkeypatch):
    pool = _FakePool()
    pool.seed(id=1, resolved_at=datetime.now(UTC), fisher_reply=2,
              skipper_name='Jade N. Salvador', phone='+63999',
              license_type='boatr', license_number='NWB-1')
    pool.seed(id=2)
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/recent', headers=_operator_headers())

    assert response.status_code == 200
    events = response.json()['events']
    assert [e['id'] for e in events] == [1]
    assert events[0]['skipper_name'] == 'Jade N. Salvador'
    assert events[0]['fisher_reply'] == 2
    assert events[0]['resolved_at'] is not None


def test_reopen_returns_a_resolved_incident_to_the_active_feed(monkeypatch):
    pool = _FakePool()
    pool.seed(id=3, resolved_at=datetime.now(UTC))
    _patch(monkeypatch, pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        reopened = client.post('/api/sos/3/reopen', headers=_operator_headers())
        assert reopened.status_code == 200
        assert reopened.json()['outcome'] == 'updated'
        assert reopened.json()['resolved_at'] is None

        missing = client.post('/api/sos/999/reopen', headers=_operator_headers())
        assert missing.status_code == 404

    with TestClient(app, raise_server_exceptions=False) as client:
        still_active = client.post('/api/sos/3/reopen', headers=_operator_headers())
        assert still_active.status_code == 200
        assert still_active.json()['outcome'] == 'no_change'

    assert [e['action'] for e in pool.audit_events] == ['sos.reopen']

