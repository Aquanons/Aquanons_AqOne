"""Vessel-profile overwrite rule against real Postgres (docs/05, confirmed by Len 2026-09-30).

Acceptance tests written by the spec author. Do not edit them to make them pass.
"""

import asyncio

import asyncpg
from fastapi.testclient import TestClient

from app.main import app


def _row(url, vessel_id):
    async def run():
        conn = await asyncpg.connect(url)
        try:
            return await conn.fetchrow(
                'SELECT skipper_name, phone, last_seen_at FROM vessels WHERE id = $1', vessel_id,
            )
        finally:
            await conn.close()
    return asyncio.run(run())


def _payload(**over):
    base = {
        'vessel_id': 'PV1', 'boat': 'NW-001', 'skipper_name': 'Juan Dela Cruz',
        'license_type': 'boatr', 'license_number': 'NWB-1', 'phone': '+639171234567',
    }
    base.update(over)
    return base


def test_anonymous_overwrite_of_identity_is_rejected_and_nothing_changes(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/api/vessel-profile', json=_payload()).status_code == 200
        res = client.post('/api/vessel-profile', json=_payload(skipper_name='Impostor', phone='+639000000000'))
    assert res.status_code == 409
    row = _row(probe_db, 'PV1')
    assert row['skipper_name'] == 'Juan Dela Cruz'
    assert row['phone'] == '+639171234567'


def test_anonymous_create_and_blank_fill_still_work_and_stamp_last_seen(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/api/vessel-profile', json=_payload(phone='')).status_code == 200
        assert client.post('/api/vessel-profile', json=_payload(phone='+639171234567')).status_code == 200
    row = _row(probe_db, 'PV1')
    assert row['phone'] == '+639171234567'
    assert row['last_seen_at'] is not None


def test_identical_resend_is_not_an_overwrite(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/api/vessel-profile', json=_payload()).status_code == 200
        assert client.post('/api/vessel-profile', json=_payload()).status_code == 200
