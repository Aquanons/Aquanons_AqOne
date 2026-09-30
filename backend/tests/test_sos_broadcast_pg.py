"""SOS nearby broadcast Phase 1b against real Postgres (docs/73 Rev 2, Section 14).

Acceptance tests written by the spec author. Do not edit them to make them pass.
"""

import asyncio
import logging

import asyncpg
from fastapi.testclient import TestClient

from app.auth import create_token
from app.main import app


def _run(url, statement, *args, fetch='row'):
    async def run():
        conn = await asyncpg.connect(url)
        try:
            if fetch == 'row':
                return await conn.fetchrow(statement, *args)
            if fetch == 'all':
                return await conn.fetch(statement, *args)
            return await conn.execute(statement, *args)
        finally:
            await conn.close()
    return asyncio.run(run())


def _seed(url, vessel_id='NB1', lat=11.70, lon=122.44):
    _run(url, "INSERT INTO vessels (id, boat_name) VALUES ($1, 'Near Boat') ON CONFLICT DO NOTHING",
         vessel_id, fetch='exec')
    return _run(
        url,
        'INSERT INTO sos_events (vessel_id, note, latitude, longitude) VALUES ($1, $2, $3, $4) RETURNING id',
        vessel_id, 'engine', lat, lon,
    )['id']


def _headers():
    return {'Authorization': f'Bearer {create_token(1, "probe.mdrrmo@example.invalid", "mdrrmo")}'}


def _broadcast(url, event_id):
    return _run(url, 'SELECT * FROM sos_broadcasts WHERE sos_event_id = $1', event_id)


def _actions(url, event_id):
    rows = _run(
        url,
        "SELECT action FROM operations_audit_events WHERE resource_type = 'sos_event' "
        'AND resource_id = $1 ORDER BY id',
        str(event_id), fetch='all',
    )
    return [r['action'] for r in rows]


def _version(url, event_id):
    return _run(url, 'SELECT version FROM sos_events WHERE id = $1', event_id)['version']


def _nearby(client):
    return client.get('/api/public/sos-nearby?lat=11.70&lon=122.44&radius_km=10').json()['broadcasts']


def _active_state(client, event_id):
    events = client.get('/api/sos/active', headers=_headers()).json()['events']
    return next(e['broadcast_state'] for e in events if e['id'] == event_id)


def test_reack_audits_an_update_not_a_second_create(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(),
                           json={'eta_minutes': 30}).status_code == 200
        assert client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(),
                           json={'eta_minutes': 45}).status_code == 200
    actions = _actions(probe_db, event_id)
    assert actions.count('sos.broadcast') == 1
    assert actions.count('sos.broadcast_update') == 1


def test_ack_with_broadcast_off_cancels_an_active_broadcast(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={'eta_minutes': 30})
        eta_before = _run(probe_db, 'SELECT eta_at FROM sos_events WHERE id = $1', event_id)['eta_at']
        assert len(_nearby(client)) == 1

        res = client.post(
            f'/api/sos/{event_id}/acknowledge', headers=_headers(),
            json={'broadcast_enabled': False, 'expected_version': _version(probe_db, event_id)},
        )
        assert res.status_code == 200
        assert res.json()['broadcast']['state'] == 'cancelled'
        assert _nearby(client) == []
        assert _active_state(client, event_id) == 'cancelled'

    row = _broadcast(probe_db, event_id)
    assert row['state'] == 'cancelled'
    assert row['expired_at'] is not None
    eta_after = _run(probe_db, 'SELECT eta_at FROM sos_events WHERE id = $1', event_id)['eta_at']
    assert eta_after == eta_before
    assert 'sos.broadcast_cancel' in _actions(probe_db, event_id)


def test_ack_with_broadcast_off_and_no_broadcast_creates_nothing(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(),
                          json={'broadcast_enabled': False})
        assert res.status_code == 200
        assert res.json()['broadcast'] is None
        assert _active_state(client, event_id) == 'off'
    assert _broadcast(probe_db, event_id) is None


def test_cancelled_broadcast_can_be_turned_back_on(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={})
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={'broadcast_enabled': False})
        res = client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={'broadcast_enabled': True})
        assert res.status_code == 200
        assert res.json()['broadcast']['state'] == 'active'
        assert len(_nearby(client)) == 1
        assert _active_state(client, event_id) == 'active'


def test_reopen_revives_an_expired_broadcast_and_audits_it(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={})
        client.post(f'/api/sos/{event_id}/resolve', headers=_headers(), json={'reason_code': 'rescued'})
        assert _broadcast(probe_db, event_id)['state'] == 'expired'
        assert client.post(f'/api/sos/{event_id}/reopen', headers=_headers(), json={}).status_code == 200
        assert len(_nearby(client)) == 1
    assert _broadcast(probe_db, event_id)['state'] == 'active'
    assert 'sos.broadcast_reactivate' in _actions(probe_db, event_id)


def test_reopen_never_revives_a_cancelled_broadcast(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={})
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={'broadcast_enabled': False})
        client.post(f'/api/sos/{event_id}/resolve', headers=_headers(), json={'reason_code': 'rescued'})
        assert client.post(f'/api/sos/{event_id}/reopen', headers=_headers(), json={}).status_code == 200
        assert _nearby(client) == []
    assert _broadcast(probe_db, event_id)['state'] == 'cancelled'


def test_broadcast_radius_is_5_10_or_20(probe_db):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        for bad in (1, 7, 50):
            res = client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(),
                              json={'broadcast_radius_km': bad})
            assert res.status_code == 422, bad
        assert _broadcast(probe_db, event_id) is None
        res = client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(),
                          json={'broadcast_radius_km': 20})
        assert res.status_code == 200
    assert _broadcast(probe_db, event_id)['radius_km'] == 20


def test_broadcast_failure_is_logged_and_the_ack_still_lands(probe_db, caplog):
    event_id = _seed(probe_db)
    _run(probe_db, 'DROP TABLE sos_broadcasts', fetch='exec')
    caplog.set_level(logging.ERROR)
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={'eta_minutes': 30})
    assert res.status_code == 200
    assert res.json()['broadcast'] is None
    acked = _run(probe_db, 'SELECT acknowledged_at FROM sos_events WHERE id = $1', event_id)
    assert acked['acknowledged_at'] is not None
    assert any(r.levelno >= logging.ERROR and r.name.startswith('app.') for r in caplog.records)


def test_resolve_still_lands_when_broadcast_expiry_fails(probe_db, caplog):
    event_id = _seed(probe_db)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f'/api/sos/{event_id}/acknowledge', headers=_headers(), json={})
        _run(probe_db, 'DROP TABLE sos_broadcasts', fetch='exec')
        caplog.set_level(logging.ERROR)
        res = client.post(f'/api/sos/{event_id}/resolve', headers=_headers(), json={'reason_code': 'rescued'})
    assert res.status_code == 200
    resolved = _run(probe_db, 'SELECT resolved_at FROM sos_events WHERE id = $1', event_id)
    assert resolved['resolved_at'] is not None
    assert any(r.levelno >= logging.ERROR and r.name.startswith('app.') for r in caplog.records)


def test_feed_failures_are_logged_not_hidden(probe_db, caplog):
    event_id = _seed(probe_db)
    _run(probe_db, 'DROP TABLE sos_broadcasts', fetch='exec')
    caplog.set_level(logging.ERROR)
    with TestClient(app, raise_server_exceptions=False) as client:
        nearby = client.get('/api/public/sos-nearby?lat=11.70&lon=122.44&radius_km=10')
        assert nearby.status_code == 200
        assert nearby.json()['broadcasts'] == []
        errors_after_nearby = [r for r in caplog.records if r.levelno >= logging.ERROR and r.name.startswith('app.')]
        assert errors_after_nearby, 'sos-nearby swallowed a database error without logging it'
        caplog.clear()
        assert _active_state(client, event_id) == 'off'
    assert any(r.levelno >= logging.ERROR and r.name.startswith('app.') for r in caplog.records), (
        '/api/sos/active swallowed a broadcast lookup error without logging it'
    )
