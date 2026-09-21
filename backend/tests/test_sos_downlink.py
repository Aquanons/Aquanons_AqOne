"""Gateway-only SOS downlink - the return leg of the distress loop.

The shore LoRa gateway reads the responder's acknowledgement and ETA here and
puts them back on the radio. Before this endpoint existed the gateway's only
option was GET /api/sos/active behind an operator login, so a board shipped
without a dispatcher's email and password silently never downlinked anything:
the SOS reached the dashboard, the dispatcher acknowledged with an ETA, and
the handset waited forever.

These pin: the endpoint is unreachable without GATEWAY_API_KEY - not the demo
key, not an operator token; it discloses ONLY the responder's answer, never
the position, note, boat, trust tier or owner identity that /active carries,
because that key ships hardcoded in firmware on a mast; delivery_state is
collapsed server-side so firmware never recomputes it; and a just-resolved
incident stays in the feed long enough for the closure to reach the boat.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import sos as sos_api
from app.main import app

# Everything /active exposes that a mast-mounted relay has no business holding.
DISPATCHER_ONLY_FIELDS = (
    'latitude', 'longitude', 'note', 'boat', 'trust_tier', 'buoy_id',
    'skipper_name', 'license_type', 'license_number', 'phone',
    'created_at', 'is_synthetic', 'fisher_reply',
)


def _row(**overrides):
    base = {
        'id': 41,
        'vessel_id': 'NW-001',
        'seq': 7,
        'delivered_direct': False,
        'delivered_via_buoy': True,
        'acknowledged_at': None,
        'acked_by': None,
        'eta_at': None,
        'responder_status': None,
        'responder_note': None,
        'resolved_at': None,
    }
    base.update(overrides)
    return base


class _FakePool:
    """Stands in for the sos_events read.

    The WHERE clause is the real SQL's job; what these tests own is the
    response shape the gateway parses and the fields it must never receive.
    """

    def __init__(self, rows=None) -> None:
        self.rows = rows if rows is not None else [_row()]
        self.fetch_args: tuple = ()

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetch(self, query: str, *args):
        self.fetch_args = args
        if 'FROM sos_events' in query:
            return self.rows
        return []


def _client_with(monkeypatch, rows=None):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    pool = _FakePool(rows)
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    return TestClient(app, raise_server_exceptions=False), pool


def test_missing_gateway_key_is_rejected(monkeypatch):
    monkeypatch.delenv('GATEWAY_API_KEY', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/sos/downlink').status_code == 401


def test_wrong_gateway_key_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'wrong-key'})
    assert response.status_code == 401


def test_operator_bearer_token_does_not_substitute_for_the_gateway_key(monkeypatch):
    """The two credentials are not interchangeable in either direction."""
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            '/api/sos/downlink', headers={'Authorization': 'Bearer whatever'}
        )
    assert response.status_code == 401


def test_demo_key_does_not_substitute_for_the_gateway_key(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    monkeypatch.setenv('DEMO_CONTROL_KEY', 'demo-key')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/sos/downlink', headers={'X-Demo-Key': 'demo-key'})
    assert response.status_code == 401


def test_correct_key_returns_the_responder_answer(monkeypatch):
    client, _ = _client_with(monkeypatch)
    with client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'correct-key'})
    assert response.status_code == 200
    events = response.json()['events']
    assert len(events) == 1
    assert events[0]['vessel_id'] == 'NW-001'
    assert events[0]['id'] == 41
    assert events[0]['seq'] == 7


def test_downlink_never_discloses_dispatcher_data(monkeypatch):
    """The whole reason this is not GATEWAY_API_KEY access to /active.

    A gateway key is hardcoded in firmware bolted to a mast. If it ever leaks
    it must not become a live feed of where every fishing boat in the
    municipality is, who owns it and what its licence number is.
    """
    client, _ = _client_with(monkeypatch)
    with client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'correct-key'})
    event = response.json()['events'][0]
    for field in DISPATCHER_ONLY_FIELDS:
        assert field not in event, f'{field} must not reach the gateway'


def test_delivery_state_is_collapsed_server_side(monkeypatch):
    """Firmware must not own a second copy of _delivery_state()."""
    client, _ = _client_with(monkeypatch, [
        _row(vessel_id='A', delivered_direct=False, delivered_via_buoy=False),
        _row(vessel_id='B', delivered_via_buoy=True),
        _row(vessel_id='C', acknowledged_at=dt.datetime(2026, 9, 21, 3, 0, tzinfo=dt.UTC)),
    ])
    with client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'correct-key'})
    states = {e['vessel_id']: e['delivery_state'] for e in response.json()['events']}
    assert states == {'A': 'relayed', 'B': 'delivered', 'C': 'acknowledged'}


def test_acknowledged_incident_carries_eta_and_responder_fields(monkeypatch):
    """The payload the fisher is actually waiting on."""
    client, _ = _client_with(monkeypatch, [
        _row(
            acknowledged_at=dt.datetime(2026, 9, 21, 3, 0, tzinfo=dt.UTC),
            acked_by='dispatcher_maria',
            eta_at=dt.datetime(2026, 9, 21, 3, 40, tzinfo=dt.UTC),
            responder_status=2,
            responder_note='Coast Guard boat en route from Dumaguit',
        ),
    ])
    with client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'correct-key'})
    event = response.json()['events'][0]
    assert event['delivery_state'] == 'acknowledged'
    assert event['acknowledged_at'].startswith('2026-09-21T03:00')
    assert event['eta_at'].startswith('2026-09-21T03:40')
    assert event['acked_by'] == 'dispatcher_maria'
    assert event['responder_status'] == 2
    assert event['responder_note'] == 'Coast Guard boat en route from Dumaguit'


def test_resolved_incidents_are_held_for_the_downlink_window(monkeypatch):
    """A closure the gateway never sees leaves the handset counting down an
    ETA for a rescue that already finished.
    """
    client, pool = _client_with(monkeypatch, [
        _row(resolved_at=dt.datetime(2026, 9, 21, 3, 50, tzinfo=dt.UTC)),
    ])
    with client:
        response = client.get('/api/sos/downlink', headers={'X-Api-Key': 'correct-key'})
    event = response.json()['events'][0]
    assert event['resolved_at'].startswith('2026-09-21T03:50')
    assert event['delivery_state'] == 'acknowledged'
    # The window is passed to SQL as a parameter, not baked into the query text.
    assert pool.fetch_args == (sos_api.DOWNLINK_RESOLVED_WINDOW_HOURS,)
