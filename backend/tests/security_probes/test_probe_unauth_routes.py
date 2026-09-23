"""Routes that change or disclose vessel state without binding the caller.

The no-database probes rely on one fact: with DATABASE_URL unset, a request
that passes authentication reaches the handler and gets 503 from get_pool().
So 503 means "no auth check stood in the way"; 401/403 means one did.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import ProbeBroken, require_status, run_db

from app.main import app

TRIP_ROUTES = [
    ('GET', '/api/v1/trips', None),
    ('GET', '/api/v1/trips/PROBE-TRIP', None),
    ('PATCH', '/api/v1/trips/PROBE-TRIP', {'welfare_status': 'safe', 'expected_return_at': '2030-01-01T00:00:00Z'}),
]

WARNING_DELIVERY_ROUTES = [
    (
        'POST',
        '/api/advisories/delivery',
        {
            'warning_id': 101,
            'delivery_state': 'user_acknowledged',
            'vessel_id': 'dummy-victim',
            'occurred_at': '2026-01-01T00:00:00Z',
            'details': {'probe': True},
        },
    ),
    ('GET', '/api/advisories/101/deliveries', None),
]


def _anonymous(monkeypatch, method, path, body):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.request(method, path, json=body)
    if response.status_code == 422:
        raise ProbeBroken(f'{method} {path} rejected the probe body: {response.text[:300]}')
    return response


@pytest.mark.finding('backend.trips.unbound-public-access')
@pytest.mark.parametrize(('method', 'path', 'body'), TRIP_ROUTES)
def test_trip_route_requires_a_bound_principal(monkeypatch, method, path, body):
    response = _anonymous(monkeypatch, method, path, body)
    assert response.status_code in (401, 403), (
        f'{method} {path} with no credentials reached the handler (HTTP {response.status_code})'
    )


@pytest.mark.finding('backend.warning-delivery.unbound-state-authority')
@pytest.mark.parametrize(('method', 'path', 'body'), WARNING_DELIVERY_ROUTES)
def test_warning_delivery_route_requires_an_authority(monkeypatch, method, path, body):
    response = _anonymous(monkeypatch, method, path, body)
    assert response.status_code in (401, 403), (
        f'{method} {path} with no credentials reached the handler (HTTP {response.status_code})'
    )


@pytest.mark.finding('backend.vessel-profile.unbound-owner-write')
def test_anonymous_caller_cannot_replace_an_existing_vessel_identity(probe_db):
    owner = {
        'vessel_id': 'VESSEL-B', 'boat': 'NW-B', 'skipper_name': 'Real Owner',
        'license_type': 'motorized', 'license_number': 'REAL-001', 'phone': '+639170000001',
    }
    attacker = {**owner, 'skipper_name': 'Impostor', 'license_number': 'FAKE-999', 'phone': '+639179999999'}
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post('/api/vessel-profile', json=owner)
        require_status(first, 200)
        overwrite = client.post('/api/vessel-profile', json=attacker)

    stored = run_db(
        probe_db,
        lambda conn: conn.fetchrow(
            'SELECT skipper_name, license_number, phone FROM vessels WHERE id = $1', 'VESSEL-B'
        ),
    )
    assert dict(stored) == {
        'skipper_name': 'Real Owner', 'license_number': 'REAL-001', 'phone': '+639170000001',
    }, (
        f'a second unauthenticated POST (HTTP {overwrite.status_code}) replaced the identity '
        f'dispatchers see for VESSEL-B with {dict(stored)}'
    )
