import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token
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


def test_downlink_caps_and_orders_by_priority(probe_db, monkeypatch):
    async def seed():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.executemany(
                'INSERT INTO vessels (id, boat_name) VALUES ($1, $1)',
                [(f'DL-{i:02}',) for i in range(30)],
            )
            await conn.executemany(
                '''
                INSERT INTO sos_events (vessel_id, client_ts, created_at, acknowledged_at, resolved_at)
                VALUES ($1, $2, $3, $4, $5)
                ''',
                [
                    (f'DL-{i:02}', i, datetime.now(UTC) - timedelta(hours=4, minutes=10 - i),
                     datetime.now(UTC) - timedelta(hours=4, minutes=10 - i), None)
                    for i in range(10)
                ]
                + [
                    (f'DL-{i:02}', i, datetime.now(UTC) - timedelta(hours=3, minutes=10 - i), None, None)
                    for i in range(10, 20)
                ]
                + [
                    (f'DL-{i:02}', i, datetime.now(UTC) - timedelta(hours=2),
                     datetime.now(UTC) - timedelta(hours=2), datetime.now(UTC) - timedelta(hours=2))
                    for i in range(20, 30)
                ],
            )
        finally:
            await conn.close()
    asyncio.run(seed())
    monkeypatch.setenv('GATEWAY_API_KEY', 'probe-gateway')

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'probe-gateway'})

    assert response.status_code == 200
    events = response.json()['events']
    assert len(events) == 12
    assert [event['vessel_id'] for event in events[:10]] == [f'DL-{i:02}' for i in range(9, -1, -1)]
    assert [event['vessel_id'] for event in events[10:]] == ['DL-19', 'DL-18']


def test_downlink_poll_records_gateway_last_seen(probe_db, monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'probe-gateway')
    before = datetime.now(UTC)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'probe-gateway'})
    assert response.status_code == 200
    row = _sql(probe_db, "SELECT last_poll_at FROM gateway_status WHERE gateway_key = 'default'")
    assert before <= row['last_poll_at'] <= datetime.now(UTC)


def test_ops_status_reports_gateway_last_poll_and_rejects_gateway_key(probe_db, monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'probe-gateway')
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get('/api/sos/downlink', headers={'X-Api-Key': 'probe-gateway'})
        operator = client.get('/api/ops/status', headers=_operator_headers())
        gateway = client.get('/api/ops/status', headers={'X-Api-Key': 'probe-gateway'})
    assert operator.status_code == 200
    assert operator.json()['gateway_last_poll_at'] is not None
    assert operator.json()['gateway_stale'] is False
    assert gateway.status_code == 401
