"""Gateway-only contact-event ingest (docs/38 Phase 1, docs/04 "Contact events").

The trip-anomaly detector's only trustworthy input. These pin: the endpoint is
unreachable without GATEWAY_API_KEY - not the demo key, not an operator
token, not open like SOS ingest, because a contact event is not a distress
call; malformed payloads 422; an unknown buoy_id 400; and a retried event_id
returns the original contact rather than creating a second one.
"""

from __future__ import annotations

import asyncpg
from fastapi.testclient import TestClient

from app import db as app_db
from app.api import contacts as contacts_api
from app.main import app


def _payload(**overrides):
    base = {
        'v': 1,
        'event_id': 'gw-01-000042',
        'vessel_id': 'NW-001',
        'trip_id': 'trip-2026-08-29-01',
        'buoy_id': 'BUOY01',
        'observed_at': '2026-08-29T05:00:00Z',
        'latitude': 11.6050,
        'longitude': 122.3125,
        'source': 'live',
    }
    base.update(overrides)
    return base


def test_missing_gateway_key_is_rejected(monkeypatch):
    monkeypatch.delenv('GATEWAY_API_KEY', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=_payload())
    assert response.status_code == 401


def test_wrong_gateway_key_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=_payload(), headers={'X-Api-Key': 'wrong-key'})
    assert response.status_code == 401


def test_operator_bearer_token_does_not_substitute_for_the_gateway_key(monkeypatch):
    """A dashboard operator must not be able to manufacture a contact event."""
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/v1/contacts', json=_payload(), headers={'Authorization': 'Bearer whatever'}
        )
    assert response.status_code == 401


def test_correct_key_reaches_the_handler(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=_payload(), headers={'X-Api-Key': 'correct-key'})
    # 503 because there is no database in this test - the point is it is not 401.
    assert response.status_code == 503


def test_missing_source_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    body = _payload()
    del body['source']
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=body, headers={'X-Api-Key': 'correct-key'})
    assert response.status_code == 422


def test_invalid_source_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    body = _payload(source='fake')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=body, headers={'X-Api-Key': 'correct-key'})
    assert response.status_code == 422


def test_invalid_timestamp_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    body = _payload(observed_at='not-a-timestamp')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=body, headers={'X-Api-Key': 'correct-key'})
    assert response.status_code == 422


def test_empty_event_id_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    body = _payload(event_id='')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=body, headers={'X-Api-Key': 'correct-key'})
    assert response.status_code == 422


def test_oversized_vessel_id_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    body = _payload(vessel_id='V' * 33)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/contacts', json=body, headers={'X-Api-Key': 'correct-key'})
    assert response.status_code == 422


class _FakePool:
    """In-memory stand-in for buoy_contacts, matched loosely on query text.

    Mirrors the real SQL's semantics - ON CONFLICT (event_id) ... DO NOTHING,
    then a fallback SELECT of the existing row - without a real database.
    """

    def __init__(self) -> None:
        self.contacts: dict[str, dict[str, object]] = {}
        self.known_buoys = {'BUOY01'}
        self.vessels: set[str] = set()
        self._next_id = 1

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def execute(self, query: str, *args):
        if 'INSERT INTO vessels' in query:
            (vessel_id,) = args[:1]
            self.vessels.add(vessel_id)
        return 'OK'

    async def fetchrow(self, query: str, *args):
        if 'INSERT INTO buoy_contacts' in query:
            (
                event_id, buoy_id, vessel_id, trip_id, _observed_at, _lat, _lon,
                _source, _is_synthetic, _contact_via,
            ) = args
            if buoy_id not in self.known_buoys:
                raise asyncpg.ForeignKeyViolationError('unknown buoy_id')
            if event_id in self.contacts:
                return None
            row = {'id': self._next_id, 'event_id': event_id, 'vessel_id': vessel_id, 'trip_id': trip_id}
            self.contacts[event_id] = row
            self._next_id += 1
            return row
        if 'SELECT id, event_id, vessel_id, trip_id FROM buoy_contacts' in query:
            (event_id,) = args
            return self.contacts.get(event_id)
        return None


def test_first_submission_inserts_and_retry_returns_the_same_contact(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(contacts_api, 'get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post('/api/v1/contacts', json=_payload(), headers={'X-Api-Key': 'correct-key'})
        second = client.post('/api/v1/contacts', json=_payload(), headers={'X-Api-Key': 'correct-key'})

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body['deduped'] is False
    assert second_body['deduped'] is True
    # Same logical contact both times - the whole point of the idempotency key.
    assert first_body['contact_id'] == second_body['contact_id']
    assert len(pool.contacts) == 1


def test_a_previously_unseen_vessel_is_registered(monkeypatch):
    """Scoring later needs vessels.id to exist (vessel_profiles,
    vessel_anomaly_scores and anomaly_cases all FK to it) - a vessel whose
    only activity so far is a routine contact must not be silently dropped
    from that chain.
    """
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(contacts_api, 'get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/v1/contacts', json=_payload(vessel_id='NEW-VESSEL'), headers={'X-Api-Key': 'correct-key'}
        )

    assert response.status_code == 200
    assert 'NEW-VESSEL' in pool.vessels


def test_unknown_buoy_id_is_rejected(monkeypatch):
    monkeypatch.setenv('GATEWAY_API_KEY', 'correct-key')
    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(contacts_api, 'get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/v1/contacts',
            json=_payload(buoy_id='UNKNOWN-BUOY'),
            headers={'X-Api-Key': 'correct-key'},
        )
    assert response.status_code == 400
