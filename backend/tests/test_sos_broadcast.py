"""SOS nearby broadcast: ACK creates one broadcast, resolve expires it."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import public as public_api
from app.api import sos as sos_api
from app.auth import create_token


class _FakeConn:
    def __init__(self, pool: _FakePool) -> None:
        self._pool = pool

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def transaction(self):
        return self

    async def execute(self, query: str, *args):
        return await self._pool.execute(query, *args)

    async def fetch(self, query: str, *args):
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        return await self._pool.fetchrow(query, *args)


class _FakePool:
    def __init__(self) -> None:
        self.sos_events: dict[int, dict] = {}
        self.broadcasts: dict[int, dict] = {}
        self.audit: list[dict] = []
        self._next_broadcast = 1

    def acquire(self):
        return _FakeConn(self)

    async def execute(self, query: str, *args):
        if 'INSERT INTO operations_audit_events' in query:
            self.audit.append({'action': args[3]})
            return 'OK'
        if 'UPDATE sos_broadcasts' in query and 'expired' in query:
            return 'OK'
        return 'OK'

    async def fetch(self, query: str, *args):
        if 'FROM sos_broadcasts' in query and "state = 'active'" in query:
            if 'JOIN sos_events' in query:
                out = []
                for b in self.broadcasts.values():
                    if b['state'] != 'active':
                        continue
                    e = self.sos_events.get(b['sos_event_id'])
                    if not e or e['resolved_at'] is not None or e['is_synthetic']:
                        continue
                    out.append({**b, **e})
                return out
            return [
                {'sos_event_id': b['sos_event_id'], 'state': b['state']}
                for b in self.broadcasts.values() if b['state'] == 'active'
            ]
        if 'FROM sos_events' in query and 'resolved_at IS NULL' in query:
            return [r for r in self.sos_events.values() if r['resolved_at'] is None]
        return []

    async def fetchrow(self, query: str, *args):
        if 'INSERT INTO sos_broadcasts' in query:
            event_id = int(args[0])
            existing = next(
                (b for b in self.broadcasts.values() if b['sos_event_id'] == event_id), None,
            )
            payload = {
                'broadcast_id': existing['broadcast_id'] if existing else self._next_broadcast,
                'sos_event_id': event_id,
                'center_lat': args[1],
                'center_lon': args[2],
                'radius_km': args[3],
                'eta_at': args[4],
                'responder_status': args[5],
                'state': 'active',
                'created_at': datetime.now(UTC),
            }
            if existing is None:
                self.broadcasts[self._next_broadcast] = payload
                self._next_broadcast += 1
            else:
                existing.update(payload)
                payload = existing
            return payload
        if 'UPDATE sos_broadcasts' in query and 'expired' in query:
            event_id = int(args[0])
            for b in self.broadcasts.values():
                if b['sos_event_id'] == event_id and b['state'] == 'active':
                    b['state'] = 'expired'
                    return {'id': b['broadcast_id']}
            return None
        if 'UPDATE sos_events' in query and 'SET acknowledged_at' in query:
            event_id = int(args[0])
            e = self.sos_events.get(event_id)
            if e is None:
                return None
            e['acknowledged_at'] = e['acknowledged_at'] or datetime.now(UTC)
            e['acked_by'] = args[1]
            e['responder_status'] = args[2]
            if args[3] is not None:
                e['responder_note'] = args[3]
            if args[4] is not None:
                e['eta_at'] = datetime.now(UTC) + timedelta(minutes=int(args[4]))
            e['version'] += 1
            return e
        if query.strip().startswith('SELECT * FROM sos_events WHERE id'):
            return self.sos_events.get(int(args[0]))
        if 'UPDATE sos_events' in query and 'SET resolved_at' in query:
            e = self.sos_events.get(int(args[0]))
            if e is None:
                return None
            e['resolved_at'] = e['resolved_at'] or datetime.now(UTC)
            e['version'] += 1
            return e
        if 'INSERT INTO operations_audit_events' in query:
            self.audit.append({'action': args[3]})
            return 'OK'
        return None


def _seed(pool: _FakePool, **over: object) -> dict:
    base: dict = {
        'id': 1, 'vessel_id': 'V001', 'boat': 'NW-001', 'latitude': 11.70,
        'longitude': 122.44, 'note': 'engine', 'trust_tier': 'self_declared',
        'client_ts': 1755248500, 'local_id': None, 'seq': None,
        'delivered_direct': True, 'delivered_via_buoy': False, 'buoy_id': None,
        'created_at': datetime.now(UTC), 'acknowledged_at': None, 'acked_by': None,
        'eta_at': None, 'responder_status': None, 'responder_note': None,
        'fisher_reply': None, 'fisher_replied_at': None, 'resolved_at': None,
        'resolved_by': None, 'resolved_reason': None,
        'resolution_code': None, 'version': 0, 'reopened_at': None,
        'is_synthetic': False, 'alt_latitude': None, 'alt_longitude': None,
        'nonce': None,
    }
    base.update(over)
    pool.sos_events[int(base['id'])] = base
    return base


def _patch(monkeypatch, pool: _FakePool) -> None:
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)


def _op() -> dict[str, str]:
    return {'Authorization': f"Bearer {create_token(1, 'r@example.com', 'mdrrmo')}"}


def test_ack_creates_one_broadcast_and_reack_updates_in_place(monkeypatch):
    pool = _FakePool()
    _seed(pool, id=1)
    _patch(monkeypatch, pool)
    with TestClient(sos_api.router, raise_server_exceptions=False) as _:
        pass
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post('/api/sos/1/acknowledge', headers=_op(), json={'eta_minutes': 30})
        second = client.post('/api/sos/1/acknowledge', headers=_op(), json={'eta_minutes': 45})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['broadcast']['sos_event_id'] == 1
    assert len(pool.broadcasts) == 1
    actions = [a['action'] for a in pool.audit]
    assert 'sos.acknowledge' in actions
    assert 'sos.broadcast' in actions


def test_synthetic_never_broadcasts(monkeypatch):
    pool = _FakePool()
    _seed(pool, id=2, is_synthetic=True)
    _patch(monkeypatch, pool)
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post('/api/sos/2/acknowledge', headers=_op(), json={})
    assert res.status_code == 200
    assert res.json()['broadcast'] is None
    assert pool.broadcasts == {}


def test_nearby_filters_by_radius_and_hides_synthetic(monkeypatch):
    pool = _FakePool()
    _seed(pool, id=1, latitude=11.70, longitude=122.44)
    _seed(pool, id=2, latitude=11.71, longitude=122.45, is_synthetic=True)
    _patch(monkeypatch, pool)
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        client.post('/api/sos/1/acknowledge', headers=_op(), json={'broadcast_radius_km': 10})
        client.post('/api/sos/2/acknowledge', headers=_op(), json={'broadcast_radius_km': 10})
        near = client.get('/api/public/sos-nearby?lat=11.70&lon=122.44&radius_km=10')
        far = client.get('/api/public/sos-nearby?lat=12.50&lon=123.50&radius_km=10')
    assert near.status_code == 200
    ids = [b['sos_event_id'] for b in near.json()['broadcasts']]
    assert ids == [1]
    assert far.json()['broadcasts'] == []


def test_resolve_expires_broadcast(monkeypatch):
    pool = _FakePool()
    _seed(pool, id=1)
    _patch(monkeypatch, pool)
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        client.post('/api/sos/1/acknowledge', headers=_op(), json={})
        assert len([b for b in pool.broadcasts.values() if b['state'] == 'active']) == 1
        res = client.post('/api/sos/1/resolve', headers=_op(), json={})
        near = client.get('/api/public/sos-nearby?lat=11.70&lon=122.44&radius_km=10')
    assert res.status_code == 200
    assert near.json()['broadcasts'] == []
