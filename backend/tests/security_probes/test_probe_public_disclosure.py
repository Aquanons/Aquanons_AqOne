"""What anonymous public endpoints reveal."""

from __future__ import annotations

import pytest

from app.api.hotspots import aggregate_hotspots


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
