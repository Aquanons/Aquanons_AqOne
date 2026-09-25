import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token
from app.main import app


def _seed_contact(probe_db, *, contact_via: str, minutes_ago: int) -> None:
    async def run():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO buoys (id, label) VALUES ('B1', 'Test buoy')")
            await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('V1', 'Test vessel')")
            await conn.execute(
                '''
                INSERT INTO buoy_contacts (
                    event_id, buoy_id, vessel_id, trip_id, observed_at,
                    latitude, longitude, source, is_synthetic,
                    contact_type, contact_value, contact_via
                ) VALUES ($1, 'B1', 'V1', 'T1', $2, 11.66, 122.44,
                          'live', FALSE, 'mesh_ping', $1, $3)
                ''',
                f'contact-{contact_via}-{minutes_ago}',
                datetime.now(UTC) - timedelta(minutes=minutes_ago),
                contact_via,
            )
        finally:
            await conn.close()
    asyncio.run(run())


def _active_response():
    with TestClient(app, raise_server_exceptions=False) as client:
        token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo')
        return client.get(
            '/api/ai/anomaly/active',
            headers={'Authorization': f'Bearer {token}'},
        )


def test_active_is_unavailable_without_live_contacts(probe_db):
    response = _active_response()
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict), 'active anomaly response must include top-level monitoring metadata'
    assert body['rows'] == []
    assert body['monitoring'] == 'unavailable'
    assert body['monitoring_reason']


def test_active_is_available_with_a_recent_buoy_contact(probe_db):
    _seed_contact(probe_db, contact_via='buoy', minutes_ago=5)
    response = _active_response()
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict), 'active anomaly response must include top-level monitoring metadata'
    assert body['monitoring'] == 'active'
    assert body['monitoring_reason'] is None


def test_handset_contacts_alone_leave_monitoring_unavailable(probe_db):
    _seed_contact(probe_db, contact_via='handset', minutes_ago=5)
    response = _active_response()
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict), 'active anomaly response must include top-level monitoring metadata'
    assert body['monitoring'] == 'unavailable'


def test_stale_contacts_leave_monitoring_unavailable(probe_db):
    _seed_contact(probe_db, contact_via='buoy', minutes_ago=31)
    response = _active_response()
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict), 'active anomaly response must include top-level monitoring metadata'
    assert body['monitoring'] == 'unavailable'
