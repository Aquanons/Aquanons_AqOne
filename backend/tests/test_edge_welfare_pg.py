from datetime import UTC, datetime

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token
from app.main import app


def test_contact_via_is_stored(probe_db, monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'probe-gateway')
    async def seed():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO buoys (id, label) VALUES ('VIA-B1', 'Test buoy')")
        finally:
            await conn.close()
    import asyncio
    asyncio.run(seed())
    with TestClient(app) as client:
        response = client.post(
            '/api/v1/contacts', headers={'X-Api-Key': 'probe-gateway'},
            json={
                'event_id': 'contact-via-1', 'vessel_id': 'VIA-V1', 'trip_id': 'VIA-T1',
                'buoy_id': 'VIA-B1', 'observed_at': datetime.now(UTC).isoformat(),
                'source': 'live', 'contact_via': 'handset',
            },
        )
    assert response.status_code == 200
    async def check():
        conn = await asyncpg.connect(probe_db)
        try:
            via = await conn.fetchval(
                "SELECT contact_via FROM buoy_contacts WHERE event_id='contact-via-1'"
            )
            assert via == 'handset'
        finally:
            await conn.close()
    asyncio.run(check())


def test_welfare_timestamp_changes_on_safe_update(probe_db):
    token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo')
    headers = {'Authorization': f'Bearer {token}'}
    with TestClient(app) as client:
        created = client.post(
            '/api/v1/trips', headers=headers,
            json={'trip_id': 'WELFARE-T1', 'vessel_id': 'WELFARE-V1', 'welfare_status': 'unknown'},
        )
        updated = client.patch(
            '/api/v1/trips/WELFARE-T1', headers=headers, json={'welfare_status': 'safe'},
        )
    assert created.status_code == 200
    assert updated.status_code == 200
    assert updated.json()['trip']['welfare_updated_at'] is not None
