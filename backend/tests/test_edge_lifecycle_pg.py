import asyncio
from datetime import UTC, datetime

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token, create_vessel_device_token
from app.main import app


def _sql(url, statement, *args):
    async def run():
        conn = await asyncpg.connect(url)
        try:
            return await conn.fetchrow(statement, *args)
        finally:
            await conn.close()
    return asyncio.run(run())


def _seed(probe_db, local_id=None):
    async def run():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('B1', 'Boat 1') ON CONFLICT DO NOTHING")
            await conn.execute(
                "INSERT INTO vessel_devices (id, vessel_id, label) VALUES (1, 'B1', 'probe') ON CONFLICT DO NOTHING"
            )
            return await conn.fetchrow(
                "INSERT INTO sos_events (vessel_id, note, local_id) VALUES ('B1', 'help', $1) RETURNING id",
                local_id,
            )
        finally:
            await conn.close()
    return asyncio.run(run())


def _operator_headers():
    return {'Authorization': f'Bearer {create_token(1, "probe.mdrrmo@example.invalid", "mdrrmo") }'}


def test_resolve_without_reason_stores_unspecified(probe_db):
    event = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(f"/api/sos/{event['id']}/resolve", headers=_operator_headers())
    assert response.status_code == 200
    assert response.json()['resolution_code'] == 'unspecified'


def test_resolve_with_reason_code_is_returned_in_vessel_feed(probe_db):
    event = _seed(probe_db, 'reason-call')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/sos/{event['id']}/resolve", headers=_operator_headers(), json={'reason_code': 'rescued'},
        )
        ack = client.get('/api/sos/ack/reason-call')
        vessel = client.get(
            '/api/sos/vessel/B1',
            headers={'Authorization': f'Bearer {create_vessel_device_token(1, "B1")}'},
        )
    assert response.status_code == 200
    assert ack.status_code == 200
    assert ack.json()['event']['resolution_code'] == 'rescued'
    assert vessel.status_code == 200
    assert vessel.json()['events'][0]['resolution_code'] == 'rescued'


def test_vessel_feed_returns_all_unresolved_and_only_recent_resolved(probe_db):
    async def seed_rows():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('B1', 'Boat 1')")
            await conn.execute("INSERT INTO vessel_devices (id, vessel_id, label) VALUES (1, 'B1', 'probe')")
            await conn.executemany(
                '''
                INSERT INTO sos_events (vessel_id, created_at, resolved_at)
                VALUES ('B1', NOW() - ($1 * INTERVAL '1 minute'), $2)
                ''',
                [(i, None) for i in range(25)]
                + [(i + 100, datetime(2026, 9, 24, tzinfo=UTC)) for i in range(30)],
            )
        finally:
            await conn.close()
    asyncio.run(seed_rows())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            '/api/sos/vessel/B1',
            headers={'Authorization': f'Bearer {create_vessel_device_token(1, "B1")}'},
        )
    assert response.status_code == 200
    events = response.json()['events']
    assert len(events) == 45
    assert sum(event['resolved_at'] is None for event in events) == 25


def test_reopen_restores_active_and_downlink_and_audits(probe_db, monkeypatch):
    event = _seed(probe_db)
    _sql(probe_db, 'UPDATE sos_events SET resolved_at = NOW() WHERE id = $1', event['id'])
    monkeypatch.setenv('GATEWAY_API_KEY', 'probe-gateway')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(f"/api/sos/{event['id']}/reopen", headers=_operator_headers())
        active = client.get('/api/sos/active', headers=_operator_headers())
        downlink = client.get('/api/sos/downlink', headers={'X-Api-Key': 'probe-gateway'})
    assert response.status_code == 200
    assert any(row['id'] == event['id'] for row in active.json()['events'])
    assert any(row['id'] == event['id'] for row in downlink.json()['events'])
    audit = _sql(probe_db, "SELECT action FROM operations_audit_events WHERE resource_id = $1", str(event['id']))
    assert audit['action'] == 'sos.reopen'


def test_reopen_of_open_incident_is_no_change(probe_db):
    event = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(f"/api/sos/{event['id']}/reopen", headers=_operator_headers())
    assert response.status_code == 200
    assert response.json()['outcome'] == 'no_change'


def test_ack_with_stale_version_conflicts(probe_db):
    event = _seed(probe_db)
    with TestClient(app) as client:
        endpoint = f"/api/sos/{event['id']}/acknowledge"
        headers = _operator_headers()
        first = client.post(endpoint, headers=headers, json={'expected_version': 0})
        stale = client.post(endpoint, headers=headers, json={'expected_version': 0})
    assert first.status_code == 200
    assert stale.status_code == 409
    assert stale.json()['detail'] == 'version_conflict'
    assert stale.json()['current']['version'] == 1


def test_version_conflict_body_carries_current_for_acknowledge(probe_db):
    event = _seed(probe_db)
    _sql(probe_db, 'UPDATE sos_events SET version = 1 WHERE id = $1', event['id'])
    with TestClient(app) as client:
        response = client.post(
            f"/api/sos/{event['id']}/acknowledge",
            headers=_operator_headers(),
            json={'expected_version': 0},
        )
    assert response.status_code == 409
    body = response.json()
    assert body['detail'] == 'version_conflict'
    current = body.get('current')
    assert current is not None, '409 body must expose the event under current'
    assert current['id'] == event['id']
    assert current['version'] == _sql(
        probe_db, 'SELECT version FROM sos_events WHERE id = $1', event['id'],
    )['version']


def test_version_conflict_body_carries_current_for_resolve(probe_db):
    event = _seed(probe_db)
    _sql(probe_db, 'UPDATE sos_events SET version = 1 WHERE id = $1', event['id'])
    with TestClient(app) as client:
        response = client.post(
            f"/api/sos/{event['id']}/resolve",
            headers=_operator_headers(),
            json={'expected_version': 0},
        )
    assert response.status_code == 409
    body = response.json()
    assert body['detail'] == 'version_conflict'
    current = body.get('current')
    assert current is not None, '409 body must expose the event under current'
    assert current['id'] == event['id']
    assert current['version'] == _sql(
        probe_db, 'SELECT version FROM sos_events WHERE id = $1', event['id'],
    )['version']


def test_version_conflict_body_carries_current_for_reopen(probe_db):
    event = _seed(probe_db)
    _sql(
        probe_db,
        'UPDATE sos_events SET resolved_at = NOW(), version = 1 WHERE id = $1',
        event['id'],
    )
    with TestClient(app) as client:
        response = client.post(
            f"/api/sos/{event['id']}/reopen",
            headers=_operator_headers(),
            json={'expected_version': 0},
        )
    assert response.status_code == 409
    body = response.json()
    assert body['detail'] == 'version_conflict'
    current = body.get('current')
    assert current is not None, '409 body must expose the event under current'
    assert current['id'] == event['id']
    assert current['version'] == _sql(
        probe_db, 'SELECT version FROM sos_events WHERE id = $1', event['id'],
    )['version']


def test_transport_merge_does_not_bump_version(probe_db):
    event = _seed(probe_db)
    _sql(probe_db, 'UPDATE sos_events SET version = 7 WHERE id = $1', event['id'])
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json={'vessel_id': 'B1', 'client_ts': 1, 'boat': 'Boat 1'})
    assert response.status_code == 200
    assert _sql(probe_db, 'SELECT version FROM sos_events WHERE id = $1', event['id'])['version'] == 7


def test_still_in_danger_reopens_within_two_hours(probe_db):
    device_event = _seed(probe_db, 'reply-device-call')
    local_event = _seed(probe_db, 'reply-call')
    _sql(
        probe_db,
        "UPDATE sos_events SET resolved_at = NOW() - INTERVAL '30 minutes' WHERE id = ANY($1::bigint[])",
        [device_event['id'], local_event['id']],
    )
    with TestClient(app) as client:
        device_reply = client.post(
            f"/api/sos/{device_event['id']}/reply",
            headers={'Authorization': f'Bearer {create_vessel_device_token(1, "B1")}'},
            json={'reply': 1},
        )
        local_reply = client.post('/api/sos/reply/reply-call', json={'reply': 1})
    assert device_reply.status_code == local_reply.status_code == 200
    assert device_reply.json()['resolved_at'] is None
    assert local_reply.json()['resolved_at'] is None


def test_still_in_danger_on_open_incident_does_not_mark_reopened(probe_db):
    local_id = 'reply-open-no-reopen'
    event = _seed(probe_db, local_id)
    with TestClient(app) as client:
        response = client.post(f'/api/sos/reply/{local_id}', json={'reply': 1})

    assert response.status_code == 200
    row = _sql(
        probe_db,
        'SELECT fisher_reply, reopened_at, reopened_by FROM sos_events WHERE id = $1',
        event['id'],
    )
    assert row['fisher_reply'] == 1
    assert row['reopened_at'] is None
    assert row['reopened_by'] is None


def test_still_in_danger_reopen_is_audited(probe_db):
    local_id = 'reply-resolved-reopen-audit'
    event = _seed(probe_db, local_id)
    _sql(
        probe_db,
        "UPDATE sos_events SET resolved_at = NOW() - INTERVAL '30 minutes' WHERE id = $1",
        event['id'],
    )
    with TestClient(app) as client:
        response = client.post(f'/api/sos/reply/{local_id}', json={'reply': 1})

    assert response.status_code == 200
    row = _sql(
        probe_db,
        'SELECT reopened_at, reopened_by FROM sos_events WHERE id = $1',
        event['id'],
    )
    assert row['reopened_by'] == 'fisher'
    assert row['reopened_at'] is not None
    audit = _sql(
        probe_db,
        'SELECT action FROM operations_audit_events WHERE resource_id = $1',
        str(event['id']),
    )
    assert audit is not None
    assert audit['action'] == 'sos.reopen'


def test_still_in_danger_after_window_stays_resolved(probe_db):
    device_event = _seed(probe_db, 'reply-device-expired')
    _seed(probe_db, 'reply-expired')
    _sql(
        probe_db,
        "UPDATE sos_events SET resolved_at = NOW() - INTERVAL '3 hours' "
        "WHERE local_id IN ('reply-device-expired', 'reply-expired')",
    )
    device_version = _sql(probe_db, 'SELECT version FROM sos_events WHERE id = $1', device_event['id'])['version']
    with TestClient(app, raise_server_exceptions=False) as client:
        device_reply = client.post(
            f"/api/sos/{device_event['id']}/reply",
            headers={'Authorization': f'Bearer {create_vessel_device_token(1, "B1")}'},
            json={'reply': 1},
        )
        local_reply = client.post('/api/sos/reply/reply-expired', json={'reply': 1})
    assert device_reply.status_code == local_reply.status_code == 200
    assert device_reply.json()['resolved_at'] is not None
    assert local_reply.json()['resolved_at'] is not None
    current = _sql(probe_db, 'SELECT version FROM sos_events WHERE id = $1', device_event['id'])
    assert current['version'] == device_version
