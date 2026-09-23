"""Tests for gateway-only current-event ingest (Phase 2 Task 2.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi.testclient import TestClient

from app import db as app_db
from app.api import current_events as current_events_api
from app.main import app


def _payload(**overrides):
    base = {
        'v': 1,
        'event_id': 'cur-gw-01-000101',
        'buoy_id': 'BUOY01',
        'observed_at': (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        'observed_u_mps': 0.35,
        'observed_v_mps': -0.12,
        'depth_m': 1.5,
        'source': 'live',
        'calibration_status': 'qualified',
    }
    base.update(overrides)
    return base


def test_missing_gateway_key_rejected(monkeypatch):
    monkeypatch.delenv('GATEWAY_API_KEY', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post('/api/v1/current-events', json=_payload())
    assert res.status_code == 401


def test_wrong_gateway_key_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(
            '/api/v1/current-events',
            json=_payload(),
            headers={'X-Api-Key': 'wrong-key'},
        )
    assert res.status_code == 401


def test_future_clock_skew_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    far_future = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(
            '/api/v1/current-events',
            json=_payload(observed_at=far_future),
            headers={'X-Api-Key': 'correct-key'},
        )
    assert res.status_code == 422


def test_synthetic_rejected_without_demo_mode(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    monkeypatch.delenv('DEMO_MODE', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(
            '/api/v1/current-events',
            json=_payload(source='synthetic'),
            headers={'X-Api-Key': 'correct-key'},
        )
    assert res.status_code == 403


class _FakeCurrentConn:
    def __init__(self, pool: _FakeCurrentPool):
        self.pool = pool

    async def fetchrow(self, query: str, *args):
        if 'INSERT INTO current_observations' in query:
            event_id = args[0]
            buoy_id = args[1]
            if buoy_id not in self.pool.known_buoys:
                raise asyncpg.ForeignKeyViolationError('unknown buoy_id')
            if event_id in self.pool.rows:
                return None  # DO NOTHING on conflict
            row = {
                'id': len(self.pool.rows) + 1,
                'event_id': event_id,
                'buoy_id': buoy_id,
                'source': args[6],
                'calibration_status': args[7],
            }
            self.pool.rows[event_id] = row
            return row

        if 'SELECT id, event_id, buoy_id, source, calibration_status' in query:
            event_id = args[0]
            return self.pool.rows.get(event_id)

        raise AssertionError(f'unexpected query: {query}')


class _FakeCurrentAcquire:
    def __init__(self, conn: _FakeCurrentConn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


class _FakeCurrentPool:
    def __init__(self):
        self.rows: dict[str, dict[str, object]] = {}
        self.known_buoys = {'BUOY01'}

    def acquire(self):
        return _FakeCurrentAcquire(_FakeCurrentConn(self))


def test_successful_ingest_and_idempotency(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    fake_pool = _FakeCurrentPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(current_events_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        # First ingest
        res1 = client.post(
            '/api/v1/current-events',
            json=_payload(),
            headers={'X-Api-Key': 'correct-key'},
        )
        assert res1.status_code == 200
        body1 = res1.json()
        assert body1['accepted'] is True
        assert body1['deduped'] is False
        assert body1['event_id'] == 'cur-gw-01-000101'
        assert body1['calibration_status'] == 'uncalibrated'

        # Duplicate ingest with same event_id
        res2 = client.post(
            '/api/v1/current-events',
            json=_payload(),
            headers={'X-Api-Key': 'correct-key'},
        )
        assert res2.status_code == 200
        body2 = res2.json()
        assert body2['accepted'] is True
        assert body2['deduped'] is True
        assert body2['observation_id'] == body1['observation_id']
