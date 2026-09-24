"""What anonymous public endpoints reveal."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from probe_harness import require_status, run_db

from app.api.hotspots import aggregate_hotspots
from app.main import app


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


@pytest.mark.finding('backend.public-sea-condition.operator-identity-disclosure')
def test_public_sea_condition_names_the_setter_on_real_postgres(probe_db):
    """users.id is bigint and sea_conditions.set_by_user_id is text; a fake pool cannot see that."""

    async def seed(conn):
        await conn.execute("UPDATE users SET full_name = 'Probe Dispatcher' WHERE id = 1")
        await conn.execute(
            "INSERT INTO sea_conditions (status, reason, set_by_user_id, set_by_name) "
            "VALUES ('caution', 'probe', '1', 'probe.mdrrmo@example.invalid')"
        )

    run_db(probe_db, seed)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/public/sea-condition')
    require_status(response, 200)
    current = response.json()['current']
    assert current['set_by_label'] == 'Probe Dispatcher'
    assert 'example.invalid' not in response.text
