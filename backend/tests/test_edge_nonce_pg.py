import asyncio

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token, create_vessel_device_token
from app.main import app


def _request(client, **payload):
    body = {
        'vessel_id': 'VNONCE',
        'client_ts': 1_900_000_000,
        'boat': 'B1',
        'lat': 11.66,
        'lon': 122.45,
        **payload,
    }
    return client.post('/api/sos', json=body)


def _sql(url, statement, *args):
    async def run():
        conn = await asyncpg.connect(url)
        try:
            return await conn.fetchrow(statement, *args)
        finally:
            await conn.close()
    return asyncio.run(run())


def _operator_headers():
    return {'Authorization': f'Bearer {create_token(1, "probe.mdrrmo@example.invalid", "mdrrmo")}'}


def test_prepared_rows_cannot_capture_nonce_sos(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        for seq in range(60):
            local_id = f'prepared-{seq}'
            response = _request(
                client,
                client_ts=1_900_001_000 + seq,
                local_id=local_id,
                lat=11.70,
                lon=122.50,
            )
            assert response.status_code == 200
        for seq in range(60):
            response = client.post(f'/api/sos/reply/prepared-{seq}', json={'reply': 2})
            assert response.status_code == 200
        real = _request(
            client,
            client_ts=1_900_001_023,
            local_id='real-incident',
            nonce=42,
            lat=11.61,
            lon=122.41,
            note='engine failure',
        )
        active = client.get('/api/sos/active', headers=_operator_headers())
    assert real.status_code == 200
    match = next(row for row in active.json()['events'] if row['id'] == real.json()['id'])
    assert match['resolved_at'] is None
    assert (match['latitude'], match['longitude']) == (11.61, 122.41)
    assert real.json()['nonce'] == 42


def test_same_second_different_nonce_two_rows(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        first = _request(client, nonce=100, local_id='nonce-100')
        second = _request(client, nonce=101, local_id='nonce-101')
    assert first.status_code == second.status_code == 200
    assert first.json()['id'] != second.json()['id']
    assert (first.json()['nonce'], second.json()['nonce']) == (100, 101)


def test_same_nonce_merges_across_transports(probe_db, monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'probe-gateway')
    with TestClient(app, raise_server_exceptions=False) as client:
        direct = _request(client, nonce=200, local_id='nonce-cross-transport')
        buoy = client.post(
            '/api/sos',
            headers={'X-Api-Key': 'probe-gateway'},
            json={
                'vessel_id': 'VNONCE', 'client_ts': 1_900_000_000, 'nonce': 200,
                'source': 'buoy', 'buoy_id': 'BUOY01', 'seq': 7,
                'lat': 11.66, 'lon': 122.45,
            },
        )
        ack = client.get('/api/sos/ack/nonce-cross-transport')
    assert direct.status_code == buoy.status_code == 200
    assert direct.json()['id'] == buoy.json()['id']
    assert ack.status_code == 200 and ack.json()['event']['nonce'] == 200
    row = _sql(
        probe_db,
        'SELECT nonce, delivered_direct, delivered_via_buoy FROM sos_events WHERE id = $1',
        direct.json()['id'],
    )
    assert row['nonce'] == 200
    assert row['delivered_direct'] and row['delivered_via_buoy']


def test_position_conflict_stores_alt_position(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        first = _request(client, nonce=300)
        second = _request(client, nonce=300, lat=11.68, lon=122.45)
    assert first.status_code == second.status_code == 200
    row = _sql(
        probe_db,
        'SELECT latitude, longitude, alt_latitude, alt_longitude FROM sos_events WHERE id = $1',
        first.json()['id'],
    )
    assert (row['latitude'], row['longitude']) == (11.66, 122.45)
    assert (row['alt_latitude'], row['alt_longitude']) == (11.68, 122.45)


def test_close_positions_do_not_conflict(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        first = _request(client, nonce=400)
        second = _request(client, nonce=400, lat=11.6645, lon=122.45)
    assert first.status_code == second.status_code == 200
    row = _sql(
        probe_db,
        'SELECT alt_latitude, alt_longitude FROM sos_events WHERE id = $1',
        first.json()['id'],
    )
    assert row['alt_latitude'] is None and row['alt_longitude'] is None


def test_legacy_without_nonce_still_merges_on_client_ts(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        first = _request(client, local_id='legacy-direct')
        second = client.post(
            '/api/sos',
            headers={'X-Api-Key': 'probe-gateway'},
            json={
                'vessel_id': 'VNONCE', 'client_ts': 1_900_000_000,
                'source': 'buoy', 'buoy_id': 'BUOY02', 'seq': 8,
            },
        )
    assert first.status_code == second.status_code == 200
    assert first.json()['id'] == second.json()['id']


def test_vessel_feed_returns_all_unresolved_and_only_recent_resolved(probe_db):
    async def seed_rows():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('VNONCE', 'B1') ON CONFLICT DO NOTHING")
            await conn.execute("INSERT INTO vessel_devices (id, vessel_id, label) VALUES (1, 'VNONCE', 'probe')")
            await conn.executemany(
                '''
                INSERT INTO sos_events (vessel_id, created_at, resolved_at)
                VALUES ('VNONCE', NOW() - ($1 * INTERVAL '1 minute'), NULL)
                ''',
                [(i,) for i in range(25)],
            )
            await conn.executemany(
                '''
                INSERT INTO sos_events (vessel_id, created_at, resolved_at)
                VALUES ('VNONCE', NOW() - ($1 * INTERVAL '1 minute'), NOW())
                ''',
                [(i + 100,) for i in range(30)],
            )
        finally:
            await conn.close()
    asyncio.run(seed_rows())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            '/api/sos/vessel/VNONCE',
            headers={'Authorization': f'Bearer {create_vessel_device_token(1, "VNONCE")}'},
        )
    assert response.status_code == 200
    events = response.json()['events']
    assert len(events) == 45
    assert sum(event['resolved_at'] is None for event in events) == 25
