"""What anonymous public endpoints reveal."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import FakeConn, install_pool, now_utc, require_status

from app.api.hotspots import aggregate_hotspots
from app.main import app

OPERATOR_EMAIL = 'operator.audit@example.invalid'


def _sea_condition_responder(kind, sql, args):
    if kind == 'fetchrow' and 'FROM sea_conditions' in sql:
        return {
            'id': 1, 'status': 'caution', 'reason': 'probe', 'set_by_user_id': '42',
            'set_by_name': OPERATOR_EMAIL, 'created_at': now_utc(),
        }
    return None


@pytest.mark.finding('backend.public-sea-condition.operator-identity-disclosure')
def test_public_sea_condition_does_not_expose_operator_account(monkeypatch):
    install_pool(monkeypatch, FakeConn(_sea_condition_responder), 'app.api.public', 'app.api.sea_condition')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/public/sea-condition')
    require_status(response, 200)
    current = response.json()['current']
    leaked = {key: current[key] for key in ('set_by_user_id', 'set_by_name') if key in current}
    assert OPERATOR_EMAIL not in response.text and not leaked, (
        f'anonymous GET /api/public/sea-condition returned operator account fields {sorted(leaked)}'
    )


def _catch_rows(reporters: int) -> list[dict[str, object]]:
    return [
        {'vessel_id': f'V{i}', 'latitude': 11.6601 + i * 0.0001, 'longitude': 122.4401}
        for i in range(reporters)
    ]


@pytest.mark.finding('backend.hotspots.minimum-cohort-policy-drift')
@pytest.mark.parametrize('reporters', [3, 4])
def test_hotspot_cell_needs_five_distinct_reporters(reporters):
    """docs/56_TECHNICAL_ARCHITECTURE_AND_DATA_FLOW_SPEC.md sets k >= 5."""
    cells = aggregate_hotspots(_catch_rows(reporters))
    assert cells == [], f'a cell built from only {reporters} vessels is published to anonymous clients'


@pytest.mark.finding('backend.hotspots.minimum-cohort-policy-drift:control')
def test_hotspot_control_five_reporters_publish():
    assert len(aggregate_hotspots(_catch_rows(5))) == 1
