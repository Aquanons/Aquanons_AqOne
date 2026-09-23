"""Catch-log idempotency keys across two paired vessels."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import require_status, run_db

from app.auth import require_vessel_device
from app.main import app


def _as_vessel(vessel_id: str):
    app.dependency_overrides[require_vessel_device] = lambda: {
        'device_id': 1, 'vessel_id': vessel_id, 'label': 'probe',
    }


@pytest.mark.finding('backend.catch.global-idempotency-cross-vessel-write')
def test_one_vessel_cannot_rewrite_another_vessels_catch_log(probe_db):
    victim = {
        'vessel_id': 'VESSEL-B', 'local_id': 'shared-key', 'estimated_quantity_kg': 5,
        'catch_date': '2026-09-01', 'share_for_hotspots': False,
    }
    attacker = {
        **victim, 'vessel_id': 'VESSEL-A', 'species_name': 'injected', 'method': 'injected',
        'notes': 'injected', 'share_for_hotspots': True,
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _as_vessel('VESSEL-B')
            require_status(client.post('/api/catch-logs', json=victim), 200)
            _as_vessel('VESSEL-A')
            second = client.post('/api/catch-logs', json=attacker)
    finally:
        app.dependency_overrides.pop(require_vessel_device, None)

    rows = run_db(
        probe_db,
        lambda conn: conn.fetch(
            'SELECT vessel_id, species_name, method, notes, share_for_hotspots FROM catch_logs '
            'ORDER BY vessel_id'
        ),
    )
    victim_rows = [dict(row) for row in rows if row['vessel_id'] == 'VESSEL-B']
    assert victim_rows == [
        {'vessel_id': 'VESSEL-B', 'species_name': None, 'method': None, 'notes': None,
         'share_for_hotspots': False},
    ], (
        f'VESSEL-A reusing VESSEL-B\'s local_id (HTTP {second.status_code}, body {second.text[:200]}) '
        f'changed VESSEL-B\'s row to {victim_rows}'
    )
