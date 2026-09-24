"""SOS ingest, dispatcher feed, and fisher-reply probes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import operator_headers, require_status, run_db

from app.main import app

GATEWAY_KEY = 'probe-gateway-key'


def _sos(**overrides):
    body = {
        'vessel_id': 'PROBE-V1',
        'client_ts': 1_700_000_000,
        'boat': 'PROBE',
        'lat': 11.6639,
        'lon': 122.4602,
        'note': 'probe',
        'source': 'direct',
        'local_id': 'probe-local-1',
    }
    body.update(overrides)
    return {key: value for key, value in body.items() if value is not None}


@pytest.mark.finding('backend.sos.anonymous-incidents-crowd-dispatch-feed')
def test_genuine_sos_survives_a_burst_of_anonymous_sos(probe_db):
    with TestClient(app, raise_server_exceptions=False) as client:
        genuine = client.post('/api/sos', json=_sos(vessel_id='GENUINE-1', local_id='genuine-local'))
        require_status(genuine, 200)
        flood_statuses: dict[int, int] = {}
        for i in range(100):
            flood = client.post(
                '/api/sos',
                json=_sos(vessel_id=f'FLOOD-{i:03d}', client_ts=1_700_000_100 + i, local_id=None),
            )
            flood_statuses[flood.status_code] = flood_statuses.get(flood.status_code, 0) + 1
        feed = client.get('/api/sos/active', headers=operator_headers())
    require_status(feed, 200)
    vessels = [event['vessel_id'] for event in feed.json()['events']]
    assert 'GENUINE-1' in vessels, (
        f'after 100 anonymous SOS (statuses {flood_statuses}) the dispatcher feed holds '
        f'{len(vessels)} incidents and the older genuine unresolved incident is gone'
    )


@pytest.mark.finding('mobile.sos.buoy-only-reply-unroutable')
def test_handset_reply_reaches_an_sos_that_arrived_only_over_the_buoy(probe_db, monkeypatch):
    """Backend half. The un-enrolled handset replies with
    POST /api/sos/reply/{its own local_id} (mobile/lib/services/backend_client.dart
    replyToSos); a buoy-only SOS never carried that local_id to the backend.
    Encodes today's handset request - revisit when the fix changes the route.
    """
    monkeypatch.setenv('GATEWAY_API_KEY', GATEWAY_KEY)
    body = _sos(
        vessel_id='BUOY-ONLY-V', client_ts=1_700_000_500, source='buoy',
        buoy_id='BUOY01', src_id=65537, seq=42, local_id=None,
    )
    direct_body = _sos(
        vessel_id='BUOY-ONLY-V', client_ts=1_700_000_500, source='direct',
        local_id='1755248500123-abcdef12',
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        ingest = client.post('/api/sos', json=body, headers={'X-Api-Key': GATEWAY_KEY})
        require_status(ingest, 200)
        direct_ingest = client.post('/api/sos', json=direct_body)
        require_status(direct_ingest, 200)
        reply = client.post('/api/sos/reply/1755248500123-abcdef12', json={'reply': 2})

    stored = run_db(
        probe_db,
        lambda conn: conn.fetchrow(
            'SELECT fisher_reply, resolved_at FROM sos_events WHERE vessel_id = $1', 'BUOY-ONLY-V'
        ),
    )
    assert stored['fisher_reply'] == 2, (
        f'handset reply returned HTTP {reply.status_code}; the buoy-only incident still has '
        f'fisher_reply={stored["fisher_reply"]} resolved_at={stored["resolved_at"]}'
    )
