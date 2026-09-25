"""GET /api/ai/anomaly/active and GET /vessel/{id} are read-only (docs/38
Phase 2 item 4 / acceptance boundary: "the active read endpoint is
read-only... must not truncate or rebuild database tables during dashboard
polling").

Before this phase, both routes called `_rebuild_and_score`, which issued a
`TRUNCATE TABLE vessel_profiles, vessel_anomaly_scores` on every call - so a
dashboard simply polling the feed repeatedly wiped and rewrote two tables.
These tests pin that a GET now only ever calls `fetch`/`fetchrow`, never
`execute`, while POST /evaluate - the explicit write path - still does.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import anomaly as anomaly_api
from app.auth import create_token
from app.main import app


def _operator_headers() -> dict[str, str]:
    token = create_token(1, 'ranger@example.com', 'mdrrmo')
    return {'Authorization': f'Bearer {token}'}


class _FakePool:
    def __init__(self) -> None:
        self.score_row = {
            'vessel_id': 'V-001',
            'trip_id': 'trip-current',
            'observed_at': datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            'last_contact_at': datetime(2026, 8, 10, 6, 45, tzinfo=UTC),
            'score': 0.7,
            'status': 'alert',
            'factors': [],
            'expected_next_buoy_id': 'B03',
            'expected_window_start': datetime(2026, 8, 10, 7, 15, tzinfo=UTC),
            'expected_window_end': datetime(2026, 8, 10, 7, 45, tzinfo=UTC),
            'is_active': True,
            'low_confidence': False,
            'updated_at': datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            'is_synthetic': False,
        }
        self.executed: list[str] = []
        self.fetched: list[str] = []
        self.monitoring_active = True

    def acquire(self):
        return self

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetch(self, query: str, *args):
        self.fetched.append(query)
        if 'FROM vessel_anomaly_scores' in query:
            return [self.score_row]
        return []

    async def fetchrow(self, query: str, *args):
        self.fetched.append(query)
        if 'FROM vessel_profiles' in query:
            return {
                'profile_json': {},
                'trip_count': 4,
                'low_confidence': False,
                'rebuilt_at': datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            }
        if 'FROM vessel_anomaly_scores' in query:
            return self.score_row
        return None

    async def fetchval(self, query: str, *args):
        self.fetched.append(query)
        return self.monitoring_active

    async def execute(self, query: str, *args):
        self.executed.append(query)
        return 'OK'


def test_active_never_writes(monkeypatch):
    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(anomaly_api, 'get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/ai/anomaly/active', headers=_operator_headers())

    assert response.status_code == 200
    assert pool.executed == [], 'GET /active must never issue a write/DDL statement'
    body = response.json()
    assert body['rows'][0]['vessel_id'] == 'V-001'
    assert body['rows'][0]['source'] == 'live'
    assert body['rows'][0]['evaluated_at'] == body['rows'][0]['observed_at']
    assert body['rows'][0]['data_age_seconds'] >= 0


def test_vessel_detail_never_writes(monkeypatch):
    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(anomaly_api, 'get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/ai/anomaly/vessel/V-001', headers=_operator_headers())

    assert response.status_code == 200
    assert pool.executed == [], 'GET /vessel/{id} must never issue a write/DDL statement'
    assert response.json()['score']['source'] == 'live'


def test_evaluate_is_the_write_path(monkeypatch):
    """Contrast case: POST /evaluate is allowed - even expected - to write."""
    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(anomaly_api, 'get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/ai/anomaly/evaluate', headers=_operator_headers())

    assert response.status_code == 200
    assert pool.executed, 'POST /evaluate is the write path and should have executed something'
