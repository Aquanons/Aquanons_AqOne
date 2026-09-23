"""SOS ingest, dispatcher feed, and fisher-reply probes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import FakeConn, install_pool, operator_headers, require_status, run_db

from app.main import app

GATEWAY_KEY = 'probe-gateway-key'

# Positional args of the INSERT INTO sos_events in app/api/sos.py ingest_sos.
TRUST_TIER_ARG = 6
BUOY_ID_ARG = 8
DELIVERED_VIA_BUOY_ARG = 12


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


def _sos_insert_responder(kind, sql, args):
    if kind == 'fetchrow' and 'INSERT INTO sos_events' in sql:
        return {
            'id': 1, 'was_inserted': True, 'vessel_id': args[0], 'client_ts': args[1],
            'delivered_direct': args[11], 'delivered_via_buoy': args[12], 'acknowledged_at': None,
        }
    return None


def _post_anonymous_sos(monkeypatch, body):
    conn = FakeConn(_sos_insert_responder)
    install_pool(monkeypatch, conn, 'app.api.sos')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    inserts = conn.calls_matching('INSERT INTO sos_events')
    return response, (inserts[0][2] if inserts else None), conn


@pytest.mark.finding('backend.sos.untrusted-provenance-claims')
def test_anonymous_sos_cannot_self_assert_responder_confirmation(monkeypatch):
    response, args, _ = _post_anonymous_sos(monkeypatch, _sos(trust_tier='confirmed_by_responder'))
    if response.status_code in (401, 403, 422):
        return
    require_status(response, 200)
    assert args[TRUST_TIER_ARG] != 'confirmed_by_responder', (
        'an unauthenticated request stored trust_tier=confirmed_by_responder on a new incident'
    )


@pytest.mark.finding('backend.sos.untrusted-provenance-claims')
def test_anonymous_sos_cannot_claim_buoy_delivery_without_gateway_key(monkeypatch):
    body = _sos(source='buoy', buoy_id='UNTRUSTED-BUOY', src_id=4242, seq=7, local_id=None)
    response, args, conn = _post_anonymous_sos(monkeypatch, body)
    if response.status_code in (401, 403):
        return
    require_status(response, 200)
    registered_buoys = [call[2][0] for call in conn.calls_matching('INSERT INTO buoys')]
    assert not args[DELIVERED_VIA_BUOY_ARG] and args[BUOY_ID_ARG] is None, (
        'a request with no gateway key was stored as delivered_via_buoy='
        f'{args[DELIVERED_VIA_BUOY_ARG]} with buoy_id={args[BUOY_ID_ARG]!r}; '
        f'buoys auto-registered: {registered_buoys}'
    )


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
    with TestClient(app, raise_server_exceptions=False) as client:
        ingest = client.post('/api/sos', json=body, headers={'X-Api-Key': GATEWAY_KEY})
        require_status(ingest, 200)
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
