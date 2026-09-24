import asyncio
from datetime import UTC, datetime

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token
from app.main import app


def _operator_headers():
    token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo')
    return {'Authorization': f'Bearer {token}'}


def _seed(probe_db, rows):
    async def run():
        conn = await asyncpg.connect(probe_db)
        try:
            for vessel_id in {row['vessel_id'] for row in rows}:
                await conn.execute(
                    'INSERT INTO vessels (id, boat_name) VALUES ($1, $1) ON CONFLICT DO NOTHING',
                    vessel_id,
                )
            return await conn.fetch(
                '''
                INSERT INTO sos_events (
                  vessel_id, client_ts, trust_tier, delivered_direct,
                  delivered_via_buoy, latitude, longitude, alt_latitude, alt_longitude, created_at
                )
                SELECT r.vessel_id, r.client_ts, r.trust_tier, r.delivered_direct,
                       r.delivered_via_buoy, r.latitude, r.longitude, r.alt_latitude,
                       r.alt_longitude, r.created_at
                FROM unnest(
                  $1::TEXT[], $2::BIGINT[], $3::TEXT[], $4::BOOLEAN[], $5::BOOLEAN[],
                  $6::DOUBLE PRECISION[], $7::DOUBLE PRECISION[], $8::DOUBLE PRECISION[],
                  $9::DOUBLE PRECISION[], $10::TIMESTAMPTZ[]
                ) AS r(vessel_id, client_ts, trust_tier, delivered_direct, delivered_via_buoy,
                       latitude, longitude, alt_latitude, alt_longitude, created_at)
                RETURNING id, vessel_id
                ''',
                [row['vessel_id'] for row in rows],
                [row.get('client_ts') for row in rows],
                [row.get('trust_tier', 'self_declared') for row in rows],
                [row.get('delivered_direct', True) for row in rows],
                [row.get('delivered_via_buoy', False) for row in rows],
                [row.get('latitude', 11.65) for row in rows],
                [row.get('longitude', 122.5) for row in rows],
                [row.get('alt_latitude') for row in rows],
                [row.get('alt_longitude') for row in rows],
                [row.get('created_at') or datetime.now(UTC) for row in rows],
            )
        finally:
            await conn.close()
    return asyncio.run(run())


def _get_active():
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.get('/api/sos/active', headers=_operator_headers())


def test_active_orders_known_vessel_above_flood(probe_db):
    async def seed_trip():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('KNOWN', 'KNOWN')")
            await conn.execute("INSERT INTO vessel_trips (trip_id, vessel_id) VALUES ('known-trip', 'KNOWN')")
        finally:
            await conn.close()
    asyncio.run(seed_trip())
    rows = [{'vessel_id': f'ANON-{i}', 'client_ts': i} for i in range(500)]
    rows.append({'vessel_id': 'KNOWN', 'client_ts': 1000, 'created_at': datetime(2026, 9, 24, 10, tzinfo=UTC)})
    _seed(probe_db, rows)

    response = _get_active()

    assert response.status_code == 200
    body = response.json()
    assert body['total'] == 501
    assert body['flood'] == {'unknown_vessels_last_minute': 500, 'active': True}
    assert body['events'][0]['vessel_id'] == 'KNOWN'
    assert body['events'][0]['vessel_verified'] is False


def test_active_limit_and_total(probe_db):
    _seed(probe_db, [{'vessel_id': f'LIMIT-{i}', 'client_ts': i} for i in range(5)])
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/active?limit=2', headers=_operator_headers())
        too_small = client.get('/api/sos/active?limit=0', headers=_operator_headers())
        too_large = client.get('/api/sos/active?limit=1001', headers=_operator_headers())
    assert response.status_code == 200
    assert len(response.json()['events']) == 2
    assert response.json()['total'] == 5
    assert too_small.status_code == too_large.status_code == 422


def test_active_marks_late_calls(probe_db):
    pressed_at = int(datetime.now(UTC).timestamp()) - 31 * 60
    _seed(probe_db, [{'vessel_id': 'LATE', 'client_ts': pressed_at}])
    event = _get_active().json()['events'][0]
    assert event['is_late'] is True
    assert event['pressed_at'].startswith(datetime.fromtimestamp(pressed_at, UTC).isoformat()[:16])


def test_active_counts_open_calls_per_vessel(probe_db):
    _seed(probe_db, [{'vessel_id': 'REPEAT', 'client_ts': i} for i in range(3)])
    events = _get_active().json()['events']
    assert len(events) == 3
    assert {event['open_calls_for_vessel'] for event in events} == {3}


def test_active_reports_delivery_path(probe_db):
    _seed(probe_db, [
        {'vessel_id': 'DIRECT', 'client_ts': 1},
        {'vessel_id': 'POD', 'client_ts': 2, 'delivered_direct': False, 'delivered_via_buoy': True},
    ])
    events = {event['vessel_id']: event for event in _get_active().json()['events']}
    assert events['DIRECT']['delivery_path'] == 'direct'
    assert events['POD']['delivery_path'] == 'pod'
