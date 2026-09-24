"""Routes that change or disclose vessel state without binding the caller.

The no-database probes rely on one fact: with DATABASE_URL unset, a request
that passes authentication reaches the handler and gets 503 from get_pool().
So 503 means "no auth check stood in the way"; 401/403 means one did.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import require_status, run_db

from app.main import app


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
