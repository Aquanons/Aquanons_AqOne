from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import catch as catch_api
from app.api import sos as sos_api
from app.api import vessel_auth as vessel_auth_api
from app.auth import create_token, create_vessel_device_token, decode_token
from app.main import app


class _FakePool:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.queries: list[str] = []
        self.vessels: dict[str, dict[str, object]] = {}
        self.pairings: list[dict[str, object]] = []
        self.devices: dict[int, dict[str, object]] = {
            1: {
                'id': 1,
                'vessel_id': 'V001',
                'label': 'Handset A',
                'revoked_at': None,
                'last_seen_at': None,
            },
            2: {
                'id': 2,
                'vessel_id': 'V002',
                'label': 'Handset B',
                'revoked_at': None,
                'last_seen_at': None,
            },
        }
        self.sos_events: dict[int, dict[str, object]] = {
            9: {
                'id': 9,
                'vessel_id': 'V002',
                'fisher_reply': None,
                'fisher_replied_at': None,
                'resolved_at': None,
            }
        }
        self.catch_logs: dict[int, dict[str, object]] = {
            7: {
                'id': 7,
                'vessel_id': 'V002',
                'quantity_kg': 10.0,
                'quantity_confirmed': False,
                'quantity_confirmed_at': None,
            }
        }
        self.sos_rows_by_vessel: dict[str, list[dict[str, object]]] = {
            'V001': [
                {
                    'id': 101,
                    'local_id': 'local-1',
                    'seq': 4,
                    'client_ts': 1754300000,
                    'acknowledged_at': None,
                    'acked_by': None,
                    'eta_at': None,
                    'responder_status': None,
                    'responder_note': None,
                    'fisher_reply': None,
                    'resolved_at': None,
                    'delivered_direct': True,
                    'delivered_via_buoy': False,
                    'created_at': now,
                }
            ]
        }
        self._next_pairing_id = 1
        self._next_device_id = 3
        self._next_catch_id = 100
        self.audit_events: list[dict[str, object]] = []

    def acquire(self):
        return self

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def execute(self, query: str, *args):
        if 'INSERT INTO vessels' in query:
            vessel_id = args[0]
            boat_name = args[1] if len(args) > 1 else vessel_id
            self.vessels[vessel_id] = {'id': vessel_id, 'boat_name': boat_name}
            return 'INSERT 0 1'
        if 'INSERT INTO vessel_device_pairings' in query:
            pairing = {
                'id': self._next_pairing_id,
                'vessel_id': args[0],
                'code_hash': args[1],
                'issued_by_user_id': args[2],
                'issued_by_email': args[3],
                'expires_at': args[4],
                'consumed_at': None,
                'created_at': datetime.now(UTC),
            }
            self._next_pairing_id += 1
            self.pairings.append(pairing)
            return 'INSERT 0 1'
        if 'UPDATE vessel_devices' in query and 'last_token_issued_at = NOW()' in query:
            device = self.devices.get(int(args[0]))
            if device is not None:
                device['last_token_issued_at'] = datetime.now(UTC)
            return 'UPDATE 1'
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
        return 'OK'

    async def fetch(self, query: str, *args):
        if 'FROM vessel_device_pairings' in query:
            vessel_id = args[0]
            now = datetime.now(UTC)
            return [
                row
                for row in self.pairings
                if row['vessel_id'] == vessel_id
                and row['consumed_at'] is None
                and row['expires_at'] > now
            ]
        if 'FROM sos_events' in query:
            return list(self.sos_rows_by_vessel.get(args[0], []))
        return []

    async def fetchrow(self, query: str, *args):
        self.queries.append(query)
        if 'SELECT revoked_at FROM vessel_devices' in query:
            device = self.devices.get(int(args[0]))
            if device is None:
                return None
            return {'revoked_at': device.get('revoked_at')}

        if 'UPDATE vessel_devices' in query and 'SET last_seen_at = NOW()' in query:
            device = self.devices.get(int(args[0]))
            if device is None:
                return None
            device['last_seen_at'] = datetime.now(UTC)
            return device

        if 'UPDATE vessel_device_pairings' in query and 'SET consumed_at = NOW()' in query:
            pairing_id = int(args[0])
            for row in self.pairings:
                if row['id'] == pairing_id and row['consumed_at'] is None:
                    row['consumed_at'] = datetime.now(UTC)
                    return {'id': pairing_id}
            return None

        if 'INSERT INTO vessel_devices' in query:
            row = {
                'id': self._next_device_id,
                'vessel_id': args[0],
                'label': args[1],
                'paired_at': datetime.now(UTC),
                'revoked_at': None,
            }
            self.devices[self._next_device_id] = dict(row)
            self._next_device_id += 1
            return row

        if 'SET revoked_at = COALESCE' in query:
            device = self.devices.get(int(args[0]))
            if device is None:
                return None
            device['revoked_at'] = device.get('revoked_at') or datetime.now(UTC)
            device['revoked_reason'] = args[2]
            return {
                'id': device['id'],
                'vessel_id': device['vessel_id'],
                'revoked_at': device['revoked_at'],
                'revoked_reason': device.get('revoked_reason'),
            }

        if 'UPDATE sos_events' in query and 'SET fisher_reply' in query:
            event_id, reply, _safe_now, vessel_id = args
            event = self.sos_events.get(int(event_id))
            if event is None or event['vessel_id'] != vessel_id:
                return None
            event['fisher_reply'] = reply
            event['fisher_replied_at'] = datetime.now(UTC)
            event['resolved_at'] = datetime.now(UTC) if reply == 2 else None
            return {
                'id': event['id'],
                'fisher_reply': event['fisher_reply'],
                'fisher_replied_at': event['fisher_replied_at'],
                'resolved_at': event['resolved_at'],
            }

        if 'UPDATE catch_logs' in query and 'SET quantity_kg' in query:
            catch_log_id, quantity_kg, vessel_id = args
            row = self.catch_logs.get(int(catch_log_id))
            if row is None or row['vessel_id'] != vessel_id:
                return None
            row['quantity_kg'] = quantity_kg
            row['quantity_confirmed'] = True
            row['quantity_confirmed_at'] = datetime.now(UTC)
            return row

        if 'INSERT INTO catch_logs' in query:
            row = {
                'id': self._next_catch_id,
                'created_at': datetime.now(UTC),
                'was_inserted': True,
            }
            self._next_catch_id += 1
            return row

        return None


def _patch_pools(monkeypatch, pool: _FakePool) -> None:
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    monkeypatch.setattr(catch_api, 'get_pool', lambda: pool)
    monkeypatch.setattr(vessel_auth_api, 'get_pool', lambda: pool)


def test_pairing_code_issue_requires_operator_token():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/vessel-auth/pairing-codes',
            json={'vessel_id': 'V001', 'boat': 'NW-001'},
        )
    assert response.status_code == 401


def test_issue_and_enroll_vessel_device(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    # Device pairing is lgu/admin-only (docs/41 Phase 1 action matrix) - mdrrmo
    # cannot issue pairing codes.
    operator = create_token(1, 'ops@example.com', 'admin')

    with TestClient(app, raise_server_exceptions=False) as client:
        issue = client.post(
            '/api/vessel-auth/pairing-codes',
            headers={'Authorization': f'Bearer {operator}'},
            json={'vessel_id': 'V001', 'boat': 'NW-001'},
        )
        assert issue.status_code == 200
        code = issue.json()['pairing_code']

        enroll = client.post(
            '/api/vessel-auth/enroll',
            json={
                'vessel_id': 'V001',
                'pairing_code': code,
                'device_label': 'Handset A',
            },
        )

    assert enroll.status_code == 200
    claims = decode_token(enroll.json()['token'])
    assert claims['kind'] == 'vessel_device'
    assert claims['vessel_id'] == 'V001'

    # docs/41 Phase 2: pairing-code issue gets one redacted audit event -
    # enroll (fisher-side, unauthenticated) does not, since it is not one of
    # the operator actions this phase wires.
    assert len(pool.audit_events) == 1
    event = pool.audit_events[0]
    assert event['action'] == 'vessel_device.pairing_code_issue'
    assert event['resource_id'] == 'V001'
    assert event['outcome'] == 'created'


def test_vessel_status_rejects_cross_vessel_token(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            '/api/sos/vessel/V002',
            headers={'Authorization': f'Bearer {token}'},
        )

    assert response.status_code == 403


def test_fisher_reply_cannot_touch_other_vessel(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/sos/9/reply',
            headers={'Authorization': f'Bearer {token}'},
            json={'reply': 1},
        )

    assert response.status_code == 404


def test_catch_log_ingest_rejects_body_vessel_mismatch(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/catch-logs',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'vessel_id': 'V002',
                'local_id': 'catch-1',
                'species_name': 'Galunggong',
                'estimated_quantity_kg': 12,
                'catch_date': '2026-08-16',
            },
        )

    assert response.status_code == 403


def test_confirm_weight_cannot_touch_other_vessel(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/catch-logs/7/confirm-weight',
            headers={'Authorization': f'Bearer {token}'},
            json={'quantity_kg': 11},
        )

    assert response.status_code == 404


def test_pairing_code_issue_rejects_mdrrmo_role(monkeypatch):
    """docs/41 Phase 1: device management is lgu/admin-only. mdrrmo could
    previously issue pairing codes via require_operator_user; this is the one
    deliberate narrowing in the Phase 1 action matrix.
    """
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    operator = create_token(1, 'ops@example.com', 'mdrrmo')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/vessel-auth/pairing-codes',
            headers={'Authorization': f'Bearer {operator}'},
            json={'vessel_id': 'V001', 'boat': 'NW-001'},
        )

    assert response.status_code == 403


def test_revoke_device_rejects_mdrrmo_role(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    operator = create_token(1, 'ops@example.com', 'mdrrmo')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/vessel-auth/devices/1/revoke',
            headers={'Authorization': f'Bearer {operator}'},
            json={'reason': 'lost device'},
        )

    assert response.status_code == 403


def test_revoke_device_allows_lgu_role(monkeypatch):
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    operator = create_token(1, 'ops@example.com', 'lgu')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/vessel-auth/devices/1/revoke',
            headers={'Authorization': f'Bearer {operator}'},
            json={'reason': 'lost device'},
        )

    assert response.status_code == 200
    assert pool.devices[1]['revoked_at'] is not None

    assert len(pool.audit_events) == 1
    event = pool.audit_events[0]
    assert event['action'] == 'vessel_device.revoke'
    assert event['outcome'] == 'updated'
    assert 'lost device' not in event['metadata']


def test_revoke_device_twice_is_no_change_the_second_time(monkeypatch):
    """Idempotency (docs/41 Phase 2): a retry must not claim a second real
    transition happened."""
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    operator = create_token(1, 'ops@example.com', 'admin')

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post(
            '/api/vessel-auth/devices/1/revoke',
            headers={'Authorization': f'Bearer {operator}'},
            json={'reason': 'lost device'},
        )
        second = client.post(
            '/api/vessel-auth/devices/1/revoke',
            headers={'Authorization': f'Bearer {operator}'},
            json={'reason': 'lost device'},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert [e['outcome'] for e in pool.audit_events] == ['updated', 'no_change']


def test_refresh_rejects_revoked_device(monkeypatch):
    pool = _FakePool()
    pool.devices[1]['revoked_at'] = datetime.now(UTC) - timedelta(minutes=1)
    _patch_pools(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/vessel-auth/refresh',
            headers={'Authorization': f'Bearer {token}'},
        )

    assert response.status_code == 401


def test_catch_log_conflict_target_is_vessel_scoped(monkeypatch):
    """SEC-11: Catch log upsert uses vessel-scoped unique conflict target."""
    pool = _FakePool()
    _patch_pools(monkeypatch, pool)
    token = create_vessel_device_token(1, 'V001')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/catch-logs',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'vessel_id': 'V001',
                'local_id': 'catch-scoped-1',
                'species_name': 'Galunggong',
                'estimated_quantity_kg': 12,
                'catch_date': '2026-08-16',
            },
        )

    assert response.status_code == 200
    insert_query = next(q for q in pool.queries if 'INSERT INTO catch_logs' in q)
    assert 'ON CONFLICT (vessel_id, local_id) WHERE local_id IS NOT NULL' in insert_query
