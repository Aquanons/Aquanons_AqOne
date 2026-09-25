from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import _DUMMY_HASH
from app.api.current_events import CurrentEventIn, ingest_current_event
from app.api.public import _serialise_public_sea_condition
from app.api.squall import _load_rows
from app.auth import ALGORITHM, JWT_SECRET, create_token, verify_user_session
from app.demo.weather import MAX_COORDINATE_CELLS, coordinates
from app.main import app


class FakeDbConn:
    def __init__(self, user_row=None):
        self.user_row = user_row
        self.queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, sql, *args):
        self.queries.append((sql, args))
        if 'FROM users' in sql:
            return self.user_row
        return None

    async def execute(self, sql, *args):
        self.queries.append((sql, args))
        return 'OK'

    def transaction(self):
        class _Tx:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *args):
                return False

        return _Tx()


class FakeDbPool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _AcquireCtx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *args):
                return False

        return _AcquireCtx()


@pytest.mark.real_user_session
def test_verify_user_session_rejects_missing_user(monkeypatch):
    pool = FakeDbPool(FakeDbConn(user_row=None))
    monkeypatch.setattr('app.db.get_pool', lambda: pool)

    claims = {'sub': '42', 'email': 'test@example.com', 'role': 'mdrrmo', 'ver': 0}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_user_session(42, claims))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'user not found'


@pytest.mark.real_user_session
def test_verify_user_session_rejects_role_mismatch(monkeypatch):
    user_row = {'id': 42, 'email': 'test@example.com', 'role': 'mdrrmo', 'token_version': 0}
    pool = FakeDbPool(FakeDbConn(user_row=user_row))
    monkeypatch.setattr('app.db.get_pool', lambda: pool)

    claims = {'sub': '42', 'email': 'test@example.com', 'role': 'admin', 'ver': 0}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_user_session(42, claims))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'role mismatch'


@pytest.mark.real_user_session
def test_verify_user_session_rejects_token_version_mismatch(monkeypatch):
    user_row = {'id': 42, 'email': 'test@example.com', 'role': 'mdrrmo', 'token_version': 2}
    pool = FakeDbPool(FakeDbConn(user_row=user_row))
    monkeypatch.setattr('app.db.get_pool', lambda: pool)

    claims = {'sub': '42', 'email': 'test@example.com', 'role': 'mdrrmo', 'ver': 1}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_user_session(42, claims))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'session revoked'


@pytest.mark.real_user_session
def test_verify_user_session_rejects_missing_ver_claim():
    claims = {'sub': '42', 'email': 'test@example.com', 'role': 'mdrrmo'}
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_user_session(42, claims))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'session expired'


@pytest.mark.real_user_session
def test_verify_user_session_accepts_valid_session(monkeypatch):
    user_row = {'id': 42, 'email': 'test@example.com', 'role': 'mdrrmo', 'token_version': 3}
    pool = FakeDbPool(FakeDbConn(user_row=user_row))
    monkeypatch.setattr('app.db.get_pool', lambda: pool)

    claims = {'sub': '42', 'email': 'test@example.com', 'role': 'mdrrmo', 'ver': 3}
    user = asyncio.run(verify_user_session(42, claims))
    assert user['id'] == '42'
    assert user['email'] == 'test@example.com'
    assert user['role'] == 'mdrrmo'


def test_logout_endpoint_increments_token_version(monkeypatch):
    conn = FakeDbConn(user_row={'id': 1, 'email': 'ops@example.com', 'role': 'mdrrmo', 'token_version': 0})
    pool = FakeDbPool(conn)
    monkeypatch.setattr('app.db.get_pool', lambda: pool)
    monkeypatch.setattr('app.api.auth.get_pool', lambda: pool)

    token = create_token(1, 'ops@example.com', 'mdrrmo', token_version=0)
    with TestClient(app) as client:
        res = client.post('/api/logout', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    assert res.json() == {'message': 'Logged out.'}
    assert any('UPDATE users SET token_version = token_version + 1' in q[0] for q in conn.queries)


@pytest.mark.real_user_session
def test_operator_token_refresh(probe_db):
    import jwt

    token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo', token_version=0)
    with TestClient(app) as client:
        response = client.post('/api/token/refresh', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    claims = jwt.decode(response.json()['token'], JWT_SECRET, algorithms=[ALGORITHM])
    assert claims['sub'] == '1'
    assert claims['role'] == 'mdrrmo'
    assert claims['ver'] == 0


@pytest.mark.real_user_session
def test_operator_token_refresh_rejects_revoked(probe_db):
    import asyncio

    import asyncpg

    async def revoke():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("UPDATE users SET token_version = 1 WHERE id = 1")
        finally:
            await conn.close()

    asyncio.run(revoke())
    token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo', token_version=0)
    with TestClient(app) as client:
        response = client.post('/api/token/refresh', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
    assert response.json()['detail'] == 'session revoked'


def test_login_unknown_email_verifies_dummy_hash(monkeypatch):
    conn = FakeDbConn(user_row=None)
    pool = FakeDbPool(conn)
    monkeypatch.setattr('app.db.get_pool', lambda: pool)
    monkeypatch.setattr('app.api.auth.get_pool', lambda: pool)

    checked_hashes = []

    def fake_verify(password, hash_val):
        checked_hashes.append(hash_val)
        return False

    monkeypatch.setattr('app.api.auth.verify_password', fake_verify)

    with TestClient(app) as client:
        res = client.post('/api/login', json={'email': 'nobody@example.com', 'password': 'secret'})
    assert res.status_code == 401
    assert checked_hashes == [_DUMMY_HASH]


def test_public_sea_condition_serializer_never_discloses_account():
    row_with_full_name = {
        'id': 1,
        'status': 'safe',
        'reason': 'Calm seas',
        'set_by_user_id': 42,
        'set_by_name': 'operator@example.invalid',
        'setter_full_name': 'Officer Santos',
        'created_at': datetime(2026, 8, 29, 5, 0, tzinfo=UTC),
    }
    serialised = _serialise_public_sea_condition(row_with_full_name)
    assert serialised['set_by_label'] == 'Officer Santos'
    assert 'set_by_user_id' not in serialised
    assert 'set_by_name' not in serialised
    assert 'operator@example.invalid' not in str(serialised)

    row_without_full_name = {
        'id': 2,
        'status': 'caution',
        'reason': 'Rough waters',
        'set_by_user_id': 42,
        'set_by_name': 'operator@example.invalid',
        'setter_full_name': '',
        'created_at': datetime(2026, 8, 29, 6, 0, tzinfo=UTC),
    }
    serialised2 = _serialise_public_sea_condition(row_without_full_name)
    assert serialised2['set_by_label'] == 'MDRRMO'
    assert 'set_by_user_id' not in serialised2
    assert 'set_by_name' not in serialised2


def test_demo_weather_coordinates_cap():
    lat = ','.join(['11.66'] * MAX_COORDINATE_CELLS)
    lon = ','.join(['122.44'] * MAX_COORDINATE_CELLS)
    coords = coordinates(lat, lon)
    assert len(coords) == MAX_COORDINATE_CELLS

    too_many_lat = ','.join(['11.66'] * (MAX_COORDINATE_CELLS + 1))
    too_many_lon = ','.join(['122.44'] * (MAX_COORDINATE_CELLS + 1))
    with pytest.raises(ValueError, match='coordinate cell count exceeds maximum'):
        coordinates(too_many_lat, too_many_lon)


def test_current_events_demotes_qualified_calibration(monkeypatch):
    stored_args = []

    class FakeCurrentConn:
        async def fetchrow(self, sql, *args):
            stored_args.append(args)
            return {
                'id': 1,
                'event_id': args[0],
                'buoy_id': args[1],
                'source': args[6],
                'calibration_status': args[7],
            }

    pool = FakeDbPool(FakeCurrentConn())
    monkeypatch.setattr('app.api.current_events.get_pool', lambda: pool)

    payload = CurrentEventIn(
        event_id='event-cal-1',
        buoy_id='BUOY-1',
        observed_at=datetime.now(UTC),
        observed_u_mps=0.1,
        observed_v_mps=-0.2,
        source='live',
        calibration_status='qualified',
    )
    result = asyncio.run(ingest_current_event(payload, x_demo_key=None))
    assert result['calibration_status'] == 'uncalibrated'
    assert stored_args[0][7] == 'uncalibrated'


def test_squall_load_rows_live_default_since():
    now = datetime.now(UTC)
    recorded_queries = []

    class FakeSquallConn:
        async def fetch(self, sql, *args):
            recorded_queries.append((sql, args))
            return []

    conn = FakeSquallConn()
    asyncio.run(_load_rows(conn, live=True))
    assert len(recorded_queries) >= 1
    sql, args = recorded_queries[0]
    assert 'observed_at >= $2' in sql
    since_arg = args[1]
    assert isinstance(since_arg, datetime)
    assert since_arg <= now - timedelta(hours=23, minutes=59)
