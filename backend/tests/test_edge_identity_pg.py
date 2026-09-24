import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
import jwt
from fastapi.testclient import TestClient

from app.auth import ALGORITHM, JWT_SECRET, create_token, create_vessel_device_token
from app.main import app


def _sql(url, statement, *args):
    async def run():
        conn = await asyncpg.connect(url)
        try:
            return await conn.fetchrow(statement, *args)
        finally:
            await conn.close()
    return asyncio.run(run())


def _operator_headers():
    token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo')
    return {'Authorization': f'Bearer {token}'}


def _device(probe_db, vessel_id, *, revoked=False):
    async def run():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute(
                '''
                INSERT INTO vessels (id, boat_name, license_type)
                VALUES ($1, $1, 'none') ON CONFLICT (id) DO NOTHING
                ''',
                vessel_id,
            )
            return await conn.fetchval(
                '''
                INSERT INTO vessel_devices (vessel_id, label, revoked_at)
                VALUES ($1, 'probe', CASE WHEN $2 THEN NOW() ELSE NULL END)
                RETURNING id
                ''',
                vessel_id,
                revoked,
            )
        finally:
            await conn.close()
    return asyncio.run(run())


def _expired_device_token(device_id, vessel_id, expired_days):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            'kind': 'vessel_device',
            'device_id': str(device_id),
            'vessel_id': vessel_id,
            'iat': now - timedelta(days=expired_days + 1),
            'exp': now - timedelta(days=expired_days),
        },
        JWT_SECRET,
        algorithm=ALGORITHM,
    )


def test_enrolled_vessel_blank_fill_needs_device(probe_db):
    _sql(
        probe_db,
        "INSERT INTO vessels (id, boat_name, license_type) VALUES ('ENROLLED', 'ENROLLED', 'none')",
    )
    device_id = _device(probe_db, 'ENROLLED')
    other_device_id = _device(probe_db, 'OTHER')
    payload = {
        'vessel_id': 'ENROLLED', 'boat': 'Bangka 1', 'skipper_name': 'Juan',
        'license_type': 'none', 'license_number': '', 'phone': '+639170000000',
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        anonymous = client.post('/api/vessel-profile', json=payload)
        wrong_device = client.post(
            '/api/vessel-profile', json=payload,
            headers={'Authorization': f'Bearer {create_vessel_device_token(other_device_id, "OTHER")}'},
        )
        authorized = client.post(
            '/api/vessel-profile', json=payload,
            headers={'Authorization': f'Bearer {create_vessel_device_token(device_id, "ENROLLED")}'},
        )
    assert anonymous.status_code == 401
    assert wrong_device.status_code == 403
    assert authorized.status_code == 200
    assert _sql(probe_db, "SELECT phone_set_by FROM vessels WHERE id = 'ENROLLED'")['phone_set_by'] == 'device'


def test_unenrolled_blank_fill_records_anonymous(probe_db):
    _sql(probe_db, "INSERT INTO vessels (id, boat_name, license_type) VALUES ('OPEN', 'OPEN', 'none')")
    payload = {
        'vessel_id': 'OPEN', 'boat': 'Bangka 2', 'skipper_name': 'Maria',
        'license_type': 'FishR', 'license_number': '', 'phone': '+639170000001',
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-profile', json=payload)
    assert response.status_code == 200
    row = _sql(probe_db, "SELECT phone_set_by, license_set_by FROM vessels WHERE id = 'OPEN'")
    assert row['phone_set_by'] == row['license_set_by'] == 'anonymous'


def test_license_text_never_sets_tier(probe_db):
    _sql(probe_db, "INSERT INTO vessels (id, boat_name, license_type) VALUES ('FISHR', 'Bangka', 'FishR')")
    _sql(
        probe_db,
        "INSERT INTO sos_events (vessel_id, client_ts, trust_tier) VALUES ('FISHR', 1900000000, 'self_declared')",
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/active', headers=_operator_headers())
    assert response.status_code == 200
    assert response.json()['events'][0]['vessel_verified'] is False


def test_confirm_vessel_sets_tier_and_audits(probe_db):
    _sql(probe_db, "INSERT INTO vessels (id, boat_name) VALUES ('CONFIRM', 'Bangka 3')")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessels/CONFIRM/confirm', headers=_operator_headers())
    assert response.status_code == 200
    row = _sql(probe_db, "SELECT confirmed_at, confirmed_by FROM vessels WHERE id = 'CONFIRM'")
    assert row['confirmed_at'] is not None
    assert row['confirmed_by'] == 'probe.mdrrmo@example.invalid'
    audit = _sql(probe_db, "SELECT action FROM operations_audit_events WHERE action = 'vessel.confirm'")
    assert audit['action'] == 'vessel.confirm'


def test_profile_stores_shore_contact(probe_db):
    payload = {
        'vessel_id': 'SHORE-CONTACT', 'boat': 'Bangka 4', 'skipper_name': 'Pedro',
        'license_type': 'none', 'license_number': '', 'phone': '',
        'shore_contact_name': 'Ana', 'shore_contact_phone': '+639170000002',
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-profile', json=payload)
    assert response.status_code == 200
    row = _sql(
        probe_db,
        "SELECT shore_contact_name, shore_contact_phone FROM vessels WHERE id = 'SHORE-CONTACT'",
    )
    assert row['shore_contact_name'] == 'Ana'
    assert row['shore_contact_phone'] == '+639170000002'


def test_refresh_accepts_recently_expired_token(probe_db):
    device_id = _device(probe_db, 'REFRESH-3D')
    token = _expired_device_token(device_id, 'REFRESH-3D', 3)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-auth/refresh', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json()['token']


def test_refresh_rejects_revoked_device(probe_db):
    device_id = _device(probe_db, 'REVOKED', revoked=True)
    token = create_vessel_device_token(device_id, 'REVOKED')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-auth/refresh', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_refresh_rejects_token_older_than_grace(probe_db):
    device_id = _device(probe_db, 'REFRESH-31D')
    token = _expired_device_token(device_id, 'REFRESH-31D', 31)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-auth/refresh', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
