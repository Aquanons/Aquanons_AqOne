"""Tests for explicit vessel trips and welfare monitoring (Phase 2 Task 2.4)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import trips as trips_api
from app.auth import create_token
from app.main import app


class _FakeTripsConn:
    def __init__(self, pool: _FakeTripsPool):
        self.pool = pool

    async def execute(self, query: str, *args):
        pass

    async def fetchrow(self, query: str, *args):
        if 'INSERT INTO vessel_trips' in query:
            trip_id = args[0]
            if trip_id in self.pool.trips:
                return None  # ON CONFLICT DO NOTHING
            row = {
                'id': len(self.pool.trips) + 1,
                'trip_id': trip_id,
                'vessel_id': args[1],
                'departure_at': args[2],
                'expected_return_at': args[3],
                'expected_checkin_interval_minutes': args[4],
                'status': args[5],
                'welfare_status': args[6],
                'reported_at': args[7],
                'synced_at': args[8],
                'reporter_id': args[9],
                'reporter_type': args[10],
                'vessel_type': args[11],
                'vessel_length_m': args[12],
                'vessel_draft_m': args[13],
                'amendments': [],
                'created_at': datetime.now(UTC),
                'updated_at': datetime.now(UTC),
            }
            self.pool.trips[trip_id] = row
            return row

        if 'SELECT * FROM vessel_trips WHERE trip_id = $1' in query:
            trip_id = args[0]
            return self.pool.trips.get(trip_id)

        if 'UPDATE vessel_trips' in query:
            trip_id = args[0]
            row = self.pool.trips.get(trip_id)
            if not row:
                return None
            if args[1] is not None:
                row['status'] = args[1]
            if args[2] is not None:
                row['welfare_status'] = args[2]
            if args[3] is not None:
                row['expected_return_at'] = args[3]
            if args[4] is not None:
                row['expected_checkin_interval_minutes'] = args[4]
            if args[5] is not None:
                row['reported_at'] = args[5]
            row['synced_at'] = args[6]
            if args[7] is not None:
                row['amendments'] = json.loads(args[7]) if isinstance(args[7], str) else args[7]
            row['updated_at'] = args[6]
            return row

        raise AssertionError(f'unexpected query: {query}')

    async def fetch(self, query: str, *args):
        if 'FROM vessel_trips' in query:
            vessel_id = args[0]
            status = args[1]
            limit = args[2]
            res = list(self.pool.trips.values())
            if vessel_id:
                res = [r for r in res if r['vessel_id'] == vessel_id]
            if status:
                res = [r for r in res if r['status'] == status]
            return res[:limit]
        raise AssertionError(f'unexpected query: {query}')


class _FakeTripsAcquire:
    def __init__(self, conn: _FakeTripsConn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


class _FakeTripsPool:
    def __init__(self):
        self.trips: dict[str, dict[str, object]] = {}

    def acquire(self):
        return _FakeTripsAcquire(_FakeTripsConn(self))


OP_HEADERS = {'Authorization': f'Bearer {create_token(1, "mdrrmo@test.local", "mdrrmo")}'}


def test_open_trip_creation_and_idempotency(monkeypatch):
    fake_pool = _FakeTripsPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(trips_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        # Create an open trip
        payload = {
            'trip_id': 'TRIP-NW-2026-001',
            'vessel_id': 'NW-001',
            'departure_at': '2026-09-15T05:00:00Z',
            'expected_return_at': '2026-09-15T12:00:00Z',
            'expected_checkin_interval_minutes': 120,
            'status': 'open',
            'welfare_status': 'normal',
            'vessel_type': 'banca',
            'vessel_length_m': 7.5,
            'vessel_draft_m': 0.45,
        }
        res1 = client.post('/api/v1/trips', json=payload, headers=OP_HEADERS)
        assert res1.status_code == 200
        body1 = res1.json()
        assert body1['created'] is True
        assert body1['trip']['trip_id'] == 'TRIP-NW-2026-001'
        assert body1['trip']['status'] == 'open'
        assert body1['trip']['welfare_status'] == 'normal'

        # Retrying same trip_id is idempotent and returns existing
        res2 = client.post('/api/v1/trips', json=payload, headers=OP_HEADERS)
        assert res2.status_code == 200
        body2 = res2.json()
        assert body2['created'] is False
        assert body2['trip']['trip_id'] == 'TRIP-NW-2026-001'


def test_already_at_sea_trip_with_unknown_departure(monkeypatch):
    fake_pool = _FakeTripsPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(trips_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        # Fisher already at sea: departure_at is None
        payload = {
            'trip_id': 'TRIP-AT-SEA-002',
            'vessel_id': 'NW-002',
            'departure_at': None,
            'expected_return_at': '2026-09-15T15:00:00Z',
            'status': 'open',
            'welfare_status': 'unknown',
        }
        res = client.post('/api/v1/trips', json=payload, headers=OP_HEADERS)
        assert res.status_code == 200
        data = res.json()['trip']
        assert data['departure_at'] is None
        assert data['status'] == 'open'
        assert data['welfare_status'] == 'unknown'


def test_voluntary_amendments_and_welfare_update(monkeypatch):
    fake_pool = _FakeTripsPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(trips_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        # Create base trip
        client.post(
            '/api/v1/trips',
            json={
                'trip_id': 'TRIP-NW-003',
                'vessel_id': 'NW-003',
                'departure_at': '2026-09-15T04:00:00Z',
                'expected_return_at': '2026-09-15T10:00:00Z',
                'status': 'open',
            },
            headers=OP_HEADERS,
        )

        # Apply amendment: extending expected return and reporting safe
        new_return = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
        patch_res = client.patch(
            '/api/v1/trips/TRIP-NW-003',
            json={
                'expected_return_at': new_return,
                'welfare_status': 'safe',
                'amendment_note': 'Catch is good near Buoy 2, staying 3 more hours',
            },
            headers=OP_HEADERS,
        )
        assert patch_res.status_code == 200
        trip = patch_res.json()['trip']
        assert trip['welfare_status'] == 'safe'
        assert len(trip['amendments']) == 1
        assert 'Catch is good' in trip['amendments'][0]['note']

        # Query single trip
        get_res = client.get('/api/v1/trips/TRIP-NW-003', headers=OP_HEADERS)
        assert get_res.status_code == 200
        assert get_res.json()['trip']['welfare_status'] == 'safe'


def test_list_trips_filtering(monkeypatch):
    fake_pool = _FakeTripsPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(trips_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(
            '/api/v1/trips',
            json={'trip_id': 'T-1', 'vessel_id': 'NW-A', 'status': 'open'},
            headers=OP_HEADERS,
        )
        client.post(
            '/api/v1/trips',
            json={'trip_id': 'T-2', 'vessel_id': 'NW-B', 'status': 'completed'},
            headers=OP_HEADERS,
        )

        res_open = client.get('/api/v1/trips?status=open', headers=OP_HEADERS)
        assert res_open.status_code == 200
        trips_open = res_open.json()['trips']
        assert len(trips_open) == 1
        assert trips_open[0]['trip_id'] == 'T-1'

        res_vessel = client.get('/api/v1/trips?vessel_id=NW-B', headers=OP_HEADERS)
        assert res_vessel.status_code == 200
        trips_vessel = res_vessel.json()['trips']
        assert len(trips_vessel) == 1
        assert trips_vessel[0]['trip_id'] == 'T-2'


def test_trips_unauthenticated_rejected(monkeypatch):
    """SEC-09: Unauthenticated requests to trips routes are rejected."""
    fake_pool = _FakeTripsPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(trips_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/v1/trips').status_code == 401
        assert client.get('/api/v1/trips/T-1').status_code == 401
        assert client.post('/api/v1/trips', json={'trip_id': 'T-1', 'vessel_id': 'V1'}).status_code == 401
        assert client.patch('/api/v1/trips/T-1', json={'welfare_status': 'safe'}).status_code == 401


def test_trips_vessel_device_authorized_and_mismatched(monkeypatch):
    """SEC-09: Vessel device token is authorized for matching vessel, forbidden for other."""
    fake_pool = _FakeTripsPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(trips_api, 'get_pool', lambda: fake_pool)

    payload = {
        'trip_id': 'T-MATCH',
        'vessel_id': 'NW-MATCH',
        'status': 'open',
    }

    device_override = ('vessel_device', {'vessel_id': 'NW-MATCH', 'device_id': 1})
    app.dependency_overrides[trips_api._authorize_mutation] = lambda: device_override
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            res_match = client.post('/api/v1/trips', json=payload)
            assert res_match.status_code == 200

            res_mismatch = client.post(
                '/api/v1/trips',
                json={**payload, 'trip_id': 'T-OTHER', 'vessel_id': 'NW-OTHER'},
            )
            assert res_mismatch.status_code == 403
    finally:
        app.dependency_overrides.pop(trips_api._authorize_mutation, None)
