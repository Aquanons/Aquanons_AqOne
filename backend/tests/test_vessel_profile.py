"""Vessel identity profile: sender identification for SOS incidents.

The handset declares its owner identity once at onboarding and again on every
profile change (`mobile/lib/data/identity_store.dart` toRegistrationPayload),
so the dashboard can identify who raised a distress call. Like SOS ingest it
is deliberately unauthenticated - it is the same self-declared identity as the
call itself - while the read side (GET /api/sos/active) stays dispatcher-gated.
"""

from fastapi.testclient import TestClient

from app.main import app


def _payload(**overrides):
    base = {
        'vessel_id': 'V001',
        'boat': 'NW-001',
        'skipper_name': 'Juan Dela Cruz',
        'license_type': 'motorized',
        'license_number': 'NWB-2026-08412',
        'phone': '+639171234567',
    }
    base.update(overrides)
    return base


def test_register_is_reachable_without_a_token(monkeypatch):
    """The handset has no account, exactly like SOS ingest."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-profile', json=_payload())

    assert response.status_code != 401, 'profile registration must never require a token'
    assert response.status_code == 503  # no DB in this test


def test_register_rejects_oversized_fields(monkeypatch):
    """Caps mirror the handset (config.dart: vessel<=32, boat<=32, name<=64,
    phone<=20, license<=24) so an oversized row cannot poison the feed."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/api/vessel-profile', json=_payload(vessel_id='V' * 33)).status_code == 422
        assert client.post('/api/vessel-profile', json=_payload(skipper_name='S' * 65)).status_code == 422
        assert client.post('/api/vessel-profile', json=_payload(phone='9' * 21)).status_code == 422
        assert client.post('/api/vessel-profile', json=_payload(license_number='L' * 25)).status_code == 422


def test_register_upserts_into_vessels(monkeypatch):
    """The vessel row may exist only as the skeleton an SOS created; the
    profile must refresh in place, and a blank boat keeps the existing name."""
    from app import db as app_db
    from app.api import vessel_profile as profile_api

    class _FakePool:
        def __init__(self):
            self.query = None
            self.args = None

        async def fetchrow(self, query, *args):
            self.query = query
            self.args = args
            return {
                'id': args[0], 'boat_name': args[1] or 'NW-001',
                'skipper_name': args[2], 'license_type': args[3],
                'license_number': args[4], 'phone': args[5],
                'profile_updated_at': None,
            }

        def acquire(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(profile_api, 'get_pool', lambda: pool)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-profile', json=_payload())

    assert response.status_code == 200
    assert 'ON CONFLICT (id) DO UPDATE' in pool.query
    assert "CASE WHEN $2 = '' THEN vessels.boat_name ELSE $2 END" in pool.query
    body = response.json()
    assert body['vessel_id'] == 'V001'
    assert body['boat'] == 'NW-001'
    assert body['skipper_name'] == 'Juan Dela Cruz'
    assert body['license_number'] == 'NWB-2026-08412'
    assert body['phone'] == '+639171234567'


def _profile_pool(monkeypatch, captured):
    from app import db as app_db
    from app.api import vessel_profile as profile_api

    class _FakePool:
        async def fetchrow(self, query, *args):
            captured['query'] = query
            captured['args'] = args
            return {
                'id': args[0], 'boat_name': args[1] or 'NW-001',
                'skipper_name': args[2], 'license_type': args[3],
                'license_number': args[4], 'phone': args[5],
                'avatar_png': args[7], 'profile_updated_at': None,
                'avatar_updated_at': None,
            }

        def acquire(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    pool = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(profile_api, 'get_pool', lambda: pool)


def test_register_stores_a_base64_avatar(monkeypatch):
    """The cropped profile photo is decoded from its data URL and stored inline
    as bytes the dashboard feed can inline behind auth."""
    import base64

    captured = {}
    _profile_pool(monkeypatch, captured)
    png = b'\x89PNG\r\n\x1a\nfake-bytes'
    data_url = 'data:image/png;base64,' + base64.b64encode(png).decode()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-profile', json=_payload(avatar=data_url))

    assert response.status_code == 200
    assert captured['args'][6] is True, 'a present avatar must be an update'
    assert captured['args'][7] == png
    assert response.json()['has_avatar'] is True


def test_register_without_avatar_keeps_the_stored_photo(monkeypatch):
    """A profile edit that carries no photo must not erase the one on file."""
    captured = {}
    _profile_pool(monkeypatch, captured)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post('/api/vessel-profile', json=_payload())

    assert captured['args'][6] is False
    assert captured['args'][7] is None


def test_register_with_empty_avatar_clears_the_photo(monkeypatch):
    """The handset removed the photo; push that as an explicit clear."""
    captured = {}
    _profile_pool(monkeypatch, captured)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post('/api/vessel-profile', json=_payload(avatar=''))

    assert captured['args'][6] is True
    assert captured['args'][7] is None


def test_register_rejects_invalid_avatar(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/vessel-profile', json=_payload(avatar='not base64!!'))

    assert response.status_code == 422


def test_active_feed_inlines_the_vessel_avatar(monkeypatch):
    """GET /api/sos/active turns the stored bytes into a data URL the row can
    render, and never leaks the raw BYTEA into the JSON."""
    import base64
    from datetime import UTC, datetime

    from app import db as app_db
    from app.api import sos as sos_api
    from app.auth import create_token

    avatar_png = b'\x89PNG\r\n\x1a\non-the-wire'

    class _ActiveSosFakePool:
        async def fetch(self, query, *args):
            return [{
                'id': 1, 'vessel_id': 'V001', 'boat': 'NW-001',
                'latitude': 11.6, 'longitude': 122.4, 'note': 'engine failure',
                'trust_tier': 'self_declared', 'client_ts': 1754300000,
                'delivered_direct': True, 'delivered_via_buoy': False,
                'buoy_id': None, 'created_at': datetime.now(UTC),
                'acknowledged_at': None, 'acked_by': None,
                'eta_at': None, 'responder_status': None, 'responder_note': None,
                'fisher_reply': None, 'fisher_replied_at': None, 'resolved_at': None,
                'is_synthetic': False,
                'skipper_name': 'Juan Dela Cruz', 'license_type': 'motorized',
                'license_number': 'NWB-2026-08412', 'phone': '+639171234567',
                'avatar_png': avatar_png,
            }]

        def acquire(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    pool = _ActiveSosFakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    token = create_token(1, 'ranger@example.com', 'mdrrmo')
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get('/api/sos/active', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 200
    event = res.json()['events'][0]
    expected = 'data:image/png;base64,' + base64.b64encode(avatar_png).decode()
    assert event['avatar'] == expected
    assert 'avatar_png' not in event


def test_active_feed_carries_the_vessel_profile(monkeypatch):
    """GET /api/sos/active sends the joined profile so the drawer can show who
    raised the call without a second request."""
    from datetime import UTC, datetime

    from app import db as app_db
    from app.api import sos as sos_api
    from app.auth import create_token

    class _ActiveSosFakePool:
        def __init__(self, events):
            self.events = events

        async def fetch(self, query, *args):
            assert 'LEFT JOIN vessels' in query, 'active_sos must join the vessel profile'
            assert 'skipper_name' in query, 'active_sos must select the vessel profile'
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
            'latitude': 11.6, 'longitude': 122.4, 'note': 'engine failure',
            'trust_tier': 'self_declared', 'client_ts': 1754300000,
            'delivered_direct': True, 'delivered_via_buoy': False,
            'buoy_id': None, 'created_at': datetime.now(UTC),
            'acknowledged_at': None, 'acked_by': None,
            'eta_at': None, 'responder_status': None, 'responder_note': None,
            'fisher_reply': None, 'fisher_replied_at': None, 'resolved_at': None,
            'is_synthetic': False,
            'skipper_name': 'Juan Dela Cruz',
            'license_type': 'motorized',
            'license_number': 'NWB-2026-08412',
            'phone': '+639171234567',
        }
    ])
    monkeypatch.setattr(app_db, 'get_pool', lambda: pool)
    monkeypatch.setattr(sos_api, 'get_pool', lambda: pool)
    token = create_token(1, 'ranger@example.com', 'mdrrmo')
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get('/api/sos/active', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    event = res.json()['events'][0]
    assert event['skipper_name'] == 'Juan Dela Cruz'
    assert event['license_number'] == 'NWB-2026-08412'
    assert event['phone'] == '+639171234567'
