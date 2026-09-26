"""docs/05 "Factor object" (docs/71 RND-02): `factors` and `reasons` leave the
API as JSON arrays of {code, value, weight, contribution, description}.

asyncpg hands a jsonb column back as text, and the stored objects use the
model's own `name`/`explanation`; before this fix both reached the dashboard
unchanged, so every trip check read "No reason recorded."
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api import anomaly as anomaly_api
from app.api import anomaly_cases as anomaly_cases_api
from app.auth import create_token
from app.main import app

STORED = json.dumps([
    {'name': 'overdue', 'value': 1.0, 'weight': 0.85, 'contribution': 0.85,
     'explanation': 'Late beyond the expected-contact window.'},
    {'name': 'weather', 'value': 0.2, 'weight': 0.02, 'contribution': 0.004,
     'explanation': 'Adverse weather at the last known position/time.'},
])
EXPECTED = [
    {'code': 'overdue', 'value': 1.0, 'weight': 0.85, 'contribution': 0.85,
     'description': 'Late beyond the expected-contact window.'},
    {'code': 'weather', 'value': 0.2, 'weight': 0.02, 'contribution': 0.004,
     'description': 'Adverse weather at the last known position/time.'},
]
AT = datetime(2026, 9, 26, 8, 0, tzinfo=UTC)


class _Pool:
    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def fetchval(self, *_):
        return False

    async def fetch(self, query, *_):
        if 'FROM anomaly_cases' in query:
            return [{
                'id': 1, 'vessel_id': 'V1', 'trip_id': 'T1', 'case_type': 'responder_attention',
                'score': 0.98, 'status': 'alert', 'reasons': STORED, 'source': 'live',
                'score_evaluated_at': AT, 'last_contact_at': AT, 'is_synthetic': False,
                'created_at': AT, 'updated_at': AT,
                'acknowledged_at': None, 'acknowledged_by': None, 'dismissed_at': None,
                'dismissed_by': None, 'dismissed_reason': None, 'escalated_at': None,
                'escalated_by': None, 'escalated_reason': None, 'resolved_at': None, 'resolved_by': None,
            }]
        return [{
            'vessel_id': 'V1', 'trip_id': 'T1', 'observed_at': AT, 'last_contact_at': AT,
            'score': 0.98, 'status': 'alert', 'factors': STORED, 'expected_next_buoy_id': 'B06',
            'expected_window_start': AT, 'expected_window_end': AT, 'is_active': True,
            'low_confidence': False, 'updated_at': AT, 'is_synthetic': False,
        }]


def _get(monkeypatch, path):
    monkeypatch.setattr(anomaly_api, 'get_pool', lambda: _Pool())
    monkeypatch.setattr(anomaly_cases_api, 'get_pool', lambda: _Pool())
    token = create_token(1, 'ranger@example.com', 'mdrrmo')
    with TestClient(app) as client:
        response = client.get(path, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    return response.json()


def test_open_cases_serve_reasons_as_contract_factors(monkeypatch):
    assert _get(monkeypatch, '/api/ai/anomaly/cases/open')[0]['reasons'] == EXPECTED


def test_active_rows_serve_factors_as_contract_factors(monkeypatch):
    assert _get(monkeypatch, '/api/ai/anomaly/active')['rows'][0]['factors'] == EXPECTED


def test_a_factor_keeps_fields_of_its_own_kind():
    factor = {'code': 'missed_checkins', 'missed': 3, 'description': 'Three check-ins missed.'}
    assert anomaly_api.contract_factors([factor]) == [factor]


def test_missing_factors_are_an_empty_list():
    assert anomaly_api.contract_factors(None) == []
