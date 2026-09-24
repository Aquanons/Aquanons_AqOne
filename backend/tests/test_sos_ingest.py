"""SOS ingest: reachable without a token, and never doubles an incident.

An SOS now reaches the backend by two independent routes - straight over HTTPS
from the handset, and through the LoRa mesh via the gateway. Both are attempted
for every distress call on purpose, because there is no way to know in advance
which will get through. The cost of that redundancy is that the same emergency
can arrive twice, and a dispatcher must never see two incidents for one boat.

De-duplication is on (vessel_id, client_ts). The LoRa frame carries only 64
payload bytes, so it cannot also carry the handset's 36-character local_id -
but its header already carries TS, the same epoch second the phone records as
client_ts. Both routes therefore share a key for free.
"""

from fastapi.testclient import TestClient

from app.main import app


def _payload(**overrides):
    base = {
        'vessel_id': 'V001',
        'client_ts': 1754300000,
        'boat': 'NW-001',
        'lat': 11.6639,
        'lon': 122.4602,
        'note': 'engine failure',
        'source': 'direct',
        'local_id': 'abc-123',
    }
    base.update(overrides)
    return base


def test_ingest_is_reachable_without_a_token(monkeypatch):
    """A handset in distress has no account and cannot obtain one at sea."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=_payload())

    # 503 because there is no database in this test, but crucially not 401.
    # If this ever returns 401 the product cannot deliver its core function.
    assert response.status_code != 401, 'SOS ingest must never require a token'
    assert response.status_code == 503


def test_reading_sos_still_requires_a_token(monkeypatch):
    """Dispatcher data stays protected even though ingest is open."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get('/api/sos/active').status_code == 401
        assert client.get('/api/sos/recent').status_code == 401
        assert client.post('/api/sos/1/acknowledge').status_code == 401
        assert client.post('/api/sos/1/reply', json={'reply': 1}).status_code == 401


def test_client_ts_is_required(monkeypatch):
    """Without it there is no cross-transport de-duplication key."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload()
    del body['client_ts']
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/api/sos', json=body).status_code == 422


def test_buoy_payload_needs_no_local_id(monkeypatch):
    """The LoRa route cannot carry a UUID, and must still be accepted."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(source='buoy', buoy_id='B01', src_id=65537, seq=42)
    del body['local_id']
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)

    assert response.status_code != 422, 'buoy-delivered SOS must validate without local_id'
    assert response.status_code == 503  # reached the handler, no DB in tests


def test_oversized_vessel_id_is_rejected(monkeypatch):
    """Phase 4: length limits mirror the handset's own caps (config.dart
    maxVesselIdLength = 32) and the firmware's fixed C buffers - see the
    SosIn docstring in app/api/sos.py. A real client can never send more than
    this; something that does is not a legitimate distress call this
    endpoint needs to accept as-is.
    """
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(vessel_id='V' * 33)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    assert response.status_code == 422


def test_vessel_id_at_the_exact_limit_is_accepted(monkeypatch):
    """The boundary itself must still work - only over the limit rejects."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(vessel_id='V' * 32)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    # 503 because there is no database in this test - the point is it is not 422.
    assert response.status_code == 503


def test_oversized_boat_name_is_rejected(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(boat='B' * 33)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    assert response.status_code == 422


def test_oversized_note_is_rejected(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(note='n' * 65)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    assert response.status_code == 422


def test_note_containing_html_is_accepted_and_preserved(monkeypatch):
    """The backend's job is to store the fisher's text faithfully, not to
    sanitise it - escaping on render is the dashboard's responsibility
    (web/js/dashboard-utils.js escapeHtml(), web/test/dashboard-utils.test.js).
    A backend that stripped or mangled this would corrupt a real distress
    message; a backend that stored it verbatim and unauthenticated-rendered
    it unescaped would be the XSS gap Phase 3 closed. This test pins the
    backend side of that contract: accept and preserve, do not escape here.
    """
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(note='<img src=x onerror=alert(1)>')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    # Valid per the length/shape contract (well within 64 chars) - 503 only
    # because there is no database in this test, never 422.
    assert response.status_code == 503


def test_lat_out_of_range_is_rejected(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(lat=91.0)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    assert response.status_code == 422


def test_lon_out_of_range_is_rejected(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(lon=-181.0)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    assert response.status_code == 422


def test_unrecognised_trust_tier_is_normalised_not_rejected(monkeypatch):
    """trust_tier is corroboration metadata, not a routing field (see
    docs/06_DELIVERY_STATES.md and the SosIn._normalise_trust_tier
    validator) - an unexpected value must never cause a distress call to
    422. It is coerced to the safe default instead.
    """
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = _payload(trust_tier='not-a-real-tier')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    # Must reach the handler (503, no DB) rather than 422 - the whole point
    # is this field is never a reason to drop a real SOS.
    assert response.status_code == 503


def test_dedup_key_is_stable_across_transports():
    """The two routes describe the same emergency with the same key.

    Documents the contract the SQL relies on: whatever else differs between a
    direct and a buoy delivery, (vessel_id, client_ts) is identical, so
    ON CONFLICT collapses them into one row.
    """
    direct = _payload(source='direct', local_id='abc-123')
    buoy = _payload(source='buoy', buoy_id='B01', src_id=65537, seq=42)
    buoy.pop('local_id')

    assert (direct['vessel_id'], direct['client_ts']) == (buoy['vessel_id'], buoy['client_ts'])
    # And they genuinely carry different transport metadata, so the upsert has
    # something to merge rather than being a no-op.
    assert direct.get('local_id') and not buoy.get('local_id')
    assert buoy.get('buoy_id') and not direct.get('buoy_id')


def test_active_sos_returns_is_synthetic_provenance(monkeypatch):
    from datetime import UTC, datetime

    from app import db as app_db
    from app.api import sos as sos_api
    from app.auth import create_token

    class _ActiveSosFakePool:
        def __init__(self, events):
            self.events = events
        async def fetch(self, query, *args):
            assert 'is_synthetic' in query, 'active_sos query must select is_synthetic'
            return self.events
        def acquire(self):
            return self
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    pool = _ActiveSosFakePool([
        {
            'id': 1, 'vessel_id': 'V001', 'boat': 'NW-001',
            'latitude': 11.6, 'longitude': 122.4, 'note': 'real sos',
            'trust_tier': 'self_declared', 'client_ts': 1754300000,
            'delivered_direct': True, 'delivered_via_buoy': False,
            'buoy_id': None, 'created_at': datetime.now(UTC),
            'acknowledged_at': None, 'acked_by': None,
            'eta_at': None, 'responder_status': None, 'responder_note': None,
            'fisher_reply': None, 'fisher_replied_at': None, 'resolved_at': None,
            'is_synthetic': False,
        },
        {
            'id': 2, 'vessel_id': 'V002', 'boat': 'NW-002',
            'latitude': 11.7, 'longitude': 122.5, 'note': 'demo sos',
            'trust_tier': 'self_declared', 'client_ts': 1754300001,
            'delivered_direct': True, 'delivered_via_buoy': False,
            'buoy_id': None, 'created_at': datetime.now(UTC),
            'acknowledged_at': None, 'acked_by': None,
            'eta_at': None, 'responder_status': None, 'responder_note': None,
            'fisher_reply': None, 'fisher_replied_at': None, 'resolved_at': None,
            'is_synthetic': True,
        }
    ])
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    token = create_token(1, 'ranger@example.com', 'mdrrmo')
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get('/api/sos/active', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    events = res.json()['events']
    assert len(events) == 2
    assert events[0]['id'] == 1 and events[0]['is_synthetic'] is False
    assert events[1]['id'] == 2 and events[1]['is_synthetic'] is True


def test_buoy_sos_registers_an_unknown_buoy_first(monkeypatch):
    """A gateway reports whatever buoy id it was flashed with.

    sos_events.buoy_id is a foreign key into buoys, so an unregistered id used
    to fail the insert with a 500 - the gateway then withheld its ack and the
    SOS never reached the dashboard.
    """
    from app import db as app_db
    from app.api import sos as sos_api

    class _IngestFakePool:
        def __init__(self):
            self.statements = []
        async def execute(self, query, *args):
            self.statements.append((query, args))
        async def fetchrow(self, query, *args):
            self.statements.append((query, args))
            return {
                'id': 7, 'was_inserted': True, 'vessel_id': args[0], 'client_ts': args[1],
                'delivered_direct': False, 'delivered_via_buoy': True, 'acknowledged_at': None,
            }
        def acquire(self):
            return self
        def transaction(self):
            return self
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    pool = _IngestFakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    monkeypatch.setenv('GATEWAY_API_KEY', 'test-gateway-key')
    body = _payload(source='buoy', buoy_id='SHORE01', src_id=255, seq=1)
    del body['local_id']
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body, headers={'X-Api-Key': 'test-gateway-key'})

    assert response.status_code == 200
    queries = [q for q, _ in pool.statements]
    buoy_insert = next(i for i, q in enumerate(queries) if 'INSERT INTO buoys' in q)
    sos_insert = next(i for i, q in enumerate(queries) if 'INSERT INTO sos_events' in q)
    assert buoy_insert < sos_insert
    assert pool.statements[buoy_insert][1] == ('SHORE01',)


def test_buoy_sos_without_gateway_key_drops_buoy_provenance(monkeypatch):
    """Anonymous SOS claiming buoy provenance has buoy fields dropped and no buoy auto-registered."""
    from app import db as app_db
    from app.api import sos as sos_api

    class _IngestFakePool:
        def __init__(self):
            self.statements = []

        async def execute(self, query, *args):
            self.statements.append((query, args))

        async def fetchrow(self, query, *args):
            self.statements.append((query, args))
            return {
                'id': 7, 'was_inserted': True, 'vessel_id': args[0], 'client_ts': args[1],
                'delivered_direct': args[11], 'delivered_via_buoy': args[12], 'acknowledged_at': None,
            }

        def acquire(self):
            return self

        def transaction(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    pool = _IngestFakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    body = _payload(source='buoy', buoy_id='SHORE01', src_id=255, seq=1)
    del body['local_id']
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)

    assert response.status_code == 200
    queries = [q for q, _ in pool.statements]
    assert not any('INSERT INTO buoys' in q for q in queries)
    sos_call = next(call for call in pool.statements if 'INSERT INTO sos_events' in call[0])
    assert sos_call[1][8] is None
    assert sos_call[1][11] is True
    assert sos_call[1][12] is False


def test_shore_gateway_wire_payload_validates(monkeypatch):
    """The exact JSON firmware/shore/AqOneShore.ino postSos() builds.

    This is the firmware-to-backend contract for the LoRa route, and it is the
    one path with no way to see a validation failure: postSos() only logs the
    status code, and a 422 there is indistinguishable on the board from a
    delivery that worked. A field renamed on either side would silently stop
    every mesh-delivered distress call from reaching the dashboard.

    seq is the buoy's own SOS counter (payload `sq`), not the mesh frame seq -
    a uint32 from NVS that keeps counting across reboots, so it is deliberately
    larger here than the small frame seq this used to send.
    """
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = {
        'vessel_id': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6',  # always 32 chars
        'client_ts': 1790000000,
        'boat': 'BG-123',
        'trust_tier': 'self_declared',
        'source': 'buoy',
        'buoy_id': 'BUOY01',
        'src_id': 65537,
        'seq': 40321,
        'note': 'engine down',
        'lat': 11.6050,
        'lon': 122.3125,
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)

    assert response.status_code != 422, (
        f'shore gateway payload rejected by validation: {response.text}'
    )
    assert response.status_code != 401, 'SOS ingest must never require a token'
    assert response.status_code == 503  # reached the handler, no DB in tests


def test_shore_gateway_payload_without_fix_or_note_validates(monkeypatch):
    """The shed case: buildSosPayload drops the boat name, then the note, and
    omits lat/lon entirely when the phone has no fix (never 0,0 - that is a
    real position in the Gulf of Guinea). What survives must still be a valid
    distress call.
    """
    monkeypatch.delenv('DATABASE_URL', raising=False)
    body = {
        'vessel_id': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6',
        'client_ts': 1790000000,
        'boat': '',
        'trust_tier': 'self_declared',
        'source': 'buoy',
        'buoy_id': 'BUOY01',
        'src_id': 65537,
        'seq': 40321,
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)

    assert response.status_code != 422, (
        f'shed shore payload rejected by validation: {response.text}'
    )
    assert response.status_code == 503
