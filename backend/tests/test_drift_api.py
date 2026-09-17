"""Responder-confirmed drift/search cases (docs/40 Phases 1-3).

Phase 1: a case can only be opened from a source the responder has already
confirmed (an acknowledged SOS or an escalated anomaly case), never from an
arbitrary client-supplied position. Real incidents must never carry ground
truth; only a synthetic/demo incident may.

Phase 2: case-opening computes exactly one production drift run, gated by
the owner-approved environmental quality policy (app/ai/environment.py) -
insufficient inputs persist `insufficient_environmental_data` rather than a
contour built on the synthetic fallback. A GET always reads that stored run;
it never recomputes. An explicit rerun appends a new run without touching
the one before it.

Phase 3: a search-sector report is a map-space rectangle plus an approved
detection-method preset, converted to the grid's metre space at the backend
boundary. It is atomic (locks the case and its current run), rejects a
stale/superseded run, deduplicates its idempotency key, and returns a
"recommended next area" alongside the updated posterior.

`_FakePool` is a tiny in-memory double for the handful of query shapes
`app.api.drift` issues - dispatched by substring the same way the existing
`_FakeStore` in test_anomaly_cases.py works. `transaction()` is a no-op
context manager (single-threaded tests need no real locking); the
duplicate-case guarantee in Phase 1 is instead asserted by having the fake
raise the same `asyncpg.UniqueViolationError` a real unique-index violation
would.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import db as app_db
from app.ai.drift import DriftResult
from app.api import drift as drift_api
from app.auth import create_token
from app.main import app

AUTH = {'Authorization': f"Bearer {create_token(1, 'ops@example.com', 'mdrrmo')}"}

CASE_LAT = 11.7
CASE_LON = 122.4
CASE_AT = datetime(2026, 8, 29, 8, tzinfo=UTC)


def _fake_prediction(*, degraded: bool = False) -> DriftResult:
    ring = [[122.0, 11.0], [122.1, 11.0], [122.1, 11.1], [122.0, 11.1], [122.0, 11.0]]
    from app.ai.drift import _to_latlon
    lats, lons = _to_latlon(np.array([250.0, 750.0]), np.array([250.0, 250.0]), 11.0, 122.0)
    return DriftResult(
        grid={
            'type': 'DensityGrid',
            'origin': {'lat': 11.0, 'lon': 122.0},
            'x_edges_m': [0.0, 500.0, 1000.0],
            'y_edges_m': [0.0, 500.0, 1000.0],
            'values': [[0.5, 0.5], [0.0, 0.0]],
        },
        contours=[
            {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [ring]}, 'properties': {'mass': 0.95}},
        ],
        centroid_track=[{'at': CASE_AT.isoformat(), 'lat': 11.05, 'lon': 122.05}],
        degraded=degraded,
        runtime_ms=1.23,
        wind_source='synthetic' if degraded else 'open-meteo',
        object_class='person_in_water',
        trajectories=[
            {
                'at': CASE_AT.isoformat(),
                'lat': lats.copy(),
                'lon': lons.copy(),
            },
            {
                'at': (CASE_AT + timedelta(hours=24)).isoformat(),
                'lat': lats.copy(),
                'lon': lons.copy(),
            },
        ],
    )


def _make_predict_drift(*, degraded: bool = False):
    """A fast predict_drift double that still calls the real current_vector_fn
    once (as a real particle step would), so create_current_field_factory's
    `observation_fraction` gets populated from whatever buoy rows the test
    put in `pool.current_observations` - without running the actual
    2000-particle Monte Carlo simulation or fetching live wind.
    """

    def _predict(*, current_vector_fn, last_lat, last_lon, observed_at, **_kwargs):
        current_vector_fn(np.array([last_lat]), np.array([last_lon]), observed_at)
        return _fake_prediction(degraded=degraded)

    return _predict


class _FakePool:
    def __init__(self) -> None:
        self.sos_events: dict[int, dict] = {}
        self.anomaly_cases: dict[int, dict] = {}
        self.buoy_contacts: list[dict] = []
        self.current_observations: list[dict] = []
        self.incidents: dict[int, dict] = {}
        self.drift_runs: dict[int, list[dict]] = {}
        self.search_sectors: list[dict] = []
        self._next_incident_id = 1
        self._next_run_id = 1
        self.audit_events: list[dict] = []

    def acquire(self):
        return self

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def close(self) -> None:
        return None

    async def fetchval(self, _query: str, *_args):
        return 1

    async def fetchrow(self, query: str, *args):
        if 'FROM sos_events' in query:
            return self.sos_events.get(args[0])

        if 'FROM anomaly_cases WHERE id' in query:
            return self.anomaly_cases.get(args[0])

        if 'FROM buoy_contacts' in query:
            vessel_id, trip_id = args
            matches = [
                row for row in self.buoy_contacts
                if row['vessel_id'] == vessel_id and row['trip_id'] == trip_id
                and row['latitude'] is not None and row['longitude'] is not None
            ]
            if not matches:
                return None
            return max(matches, key=lambda row: row['observed_at'])

        if 'INSERT INTO incidents' in query:
            (
                vessel_id, at, lat, lon, reason, object_class,
                sos_id, anomaly_id, opened_by,
            ) = args
            if sos_id is not None and any(
                row['source_sos_event_id'] == sos_id for row in self.incidents.values()
            ):
                raise asyncpg.UniqueViolationError('duplicate source_sos_event_id')
            if anomaly_id is not None and any(
                row['source_anomaly_case_id'] == anomaly_id for row in self.incidents.values()
            ):
                raise asyncpg.UniqueViolationError('duplicate source_anomaly_case_id')
            incident_id = self._next_incident_id
            self._next_incident_id += 1
            self.incidents[incident_id] = {
                'id': incident_id,
                'vessel_id': vessel_id,
                'last_contact_at': at,
                'last_contact_lat': lat,
                'last_contact_lon': lon,
                'abnormal_reason': reason,
                'object_class': object_class,
                'true_track': None,
                'is_synthetic': False,
                'prior_grid': None,
                'posterior_grid': None,
                'source_sos_event_id': sos_id,
                'source_anomaly_case_id': anomaly_id,
                'opened_by': opened_by,
                'resolved_at': None,
                'resolved_by': None,
                'cancelled_at': None,
                'cancelled_by': None,
                'cancelled_reason': None,
            }
            return {'id': incident_id}

        if 'UPDATE incidents' in query and 'SET resolved_at' in query:
            incident_id, actor = args
            incident = self.incidents.get(incident_id)
            if incident is None:
                return None
            incident['resolved_at'] = incident['resolved_at'] or datetime.now(UTC)
            incident['resolved_by'] = incident['resolved_by'] or actor
            return dict(incident)

        if 'UPDATE incidents' in query and 'SET cancelled_at' in query:
            incident_id, actor, reason = args
            incident = self.incidents.get(incident_id)
            if incident is None:
                return None
            incident['cancelled_at'] = incident['cancelled_at'] or datetime.now(UTC)
            incident['cancelled_by'] = incident['cancelled_by'] or actor
            incident['cancelled_reason'] = incident['cancelled_reason'] or reason
            return dict(incident)

        if 'FROM drift_runs' in query:
            incident_id = args[0]
            runs = self.drift_runs.get(incident_id) or []
            if not runs:
                return None
            return dict(max(runs, key=lambda r: r['run_number']))

        if 'FROM search_sectors' in query and 'idempotency_key' in query:
            incident_id, idempotency_key = args
            for row in self.search_sectors:
                if row['incident_id'] == incident_id and row.get('idempotency_key') == idempotency_key:
                    return {'id': row['id']}
            return None

        if 'FROM incidents' in query and 'WHERE id = $1' in query:
            return self.incidents.get(args[0])

        return None

    async def fetch(self, query: str, *args):
        if 'FROM current_observations' in query:
            return self.current_observations
        if 'FROM search_sectors' in query:
            incident_id = args[0]
            return [row for row in self.search_sectors if row['incident_id'] == incident_id]
        if 'FROM incidents' in query:
            return list(self.incidents.values())
        return []

    async def execute(self, query: str, *args):
        if 'INSERT INTO operations_audit_events' in query:
            (
                actor_user_id, actor_email, actor_role, action, resource_type,
                resource_id, outcome, correlation_key, is_demo, metadata,
            ) = args
            self.audit_events.append({
                'actor_user_id': actor_user_id,
                'actor_email': actor_email,
                'actor_role': actor_role,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'outcome': outcome,
                'correlation_key': correlation_key,
                'is_demo': is_demo,
                'metadata': metadata,
            })
            return 'OK'
        if 'INSERT INTO drift_runs' in query:
            (
                incident_id, run_number, object_class, forecast_hours, model_version,
                computed_by, environmental_status, insufficiency_reason,
                observed_coverage, current_max_age_seconds, nearby_buoy_count,
                wind_source, wind_degraded, max_wind_age_seconds,
                prior_grid, posterior_grid,
                *extra,
            ) = args
            trajectory_data = extra[-1] if extra else None
            run_id = self._next_run_id
            self._next_run_id += 1
            self.drift_runs.setdefault(incident_id, []).append({
                'id': run_id,
                'run_number': run_number,
                'object_class': object_class,
                'forecast_hours': forecast_hours,
                'model_version': model_version,
                'computed_at': datetime.now(UTC),
                'computed_by': computed_by,
                'environmental_status': environmental_status,
                'insufficiency_reason': insufficiency_reason,
                'observed_coverage': observed_coverage,
                'current_max_age_seconds': current_max_age_seconds,
                'nearby_buoy_count': nearby_buoy_count,
                'wind_source': wind_source,
                'wind_degraded': wind_degraded,
                'max_wind_age_seconds': max_wind_age_seconds,
                'prior_grid': prior_grid,
                'posterior_grid': posterior_grid,
                'trajectory_data': trajectory_data,
            })
        elif 'UPDATE drift_runs SET posterior_grid' in query:
            grid_json = args[0]
            traj_json = args[1] if len(args) > 2 else None
            run_id = args[-1]
            for runs in self.drift_runs.values():
                for run in runs:
                    if run['id'] == run_id:
                        run['posterior_grid'] = grid_json
                        if traj_json is not None:
                            run['trajectory_data'] = traj_json
        elif 'UPDATE incidents SET prior_grid' in query:
            grid_json, incident_id = args
            incident = self.incidents[incident_id]
            incident['prior_grid'] = grid_json
            incident['posterior_grid'] = grid_json
        elif 'UPDATE incidents SET posterior_grid' in query:
            grid_json, incident_id = args
            self.incidents[incident_id]['posterior_grid'] = grid_json
        elif 'INSERT INTO search_sectors' in query and 'idempotency_key' in query:
            (
                incident_id, x_min, x_max, y_min, y_max, pod,
                run_id, reported_by, method, notes, idempotency_key,
                *rest,
            ) = args
            south = rest[0] if len(rest) > 0 else None
            west = rest[1] if len(rest) > 1 else None
            north = rest[2] if len(rest) > 2 else None
            east = rest[3] if len(rest) > 3 else None
            searched_at = rest[4] if len(rest) > 4 else datetime.now(UTC)
            self.search_sectors.append({
                'id': len(self.search_sectors) + 1,
                'incident_id': incident_id,
                'x_min_m': x_min, 'x_max_m': x_max, 'y_min_m': y_min, 'y_max_m': y_max,
                'detection_probability': pod,
                'run_id': run_id, 'reported_by': reported_by, 'method': method,
                'notes': notes, 'idempotency_key': idempotency_key,
                'south': south, 'west': west, 'north': north, 'east': east,
                'searched_at': searched_at,
            })
        elif 'INSERT INTO search_sectors' in query:
            incident_id, x_min, x_max, y_min, y_max, pod = args
            self.search_sectors.append({
                'id': len(self.search_sectors) + 1,
                'incident_id': incident_id,
                'x_min_m': x_min, 'x_max_m': x_max, 'y_min_m': y_min, 'y_max_m': y_max,
                'detection_probability': pod,
                'run_id': None, 'reported_by': None, 'method': None,
                'notes': None, 'idempotency_key': None,
                'searched_at': datetime.now(UTC),
            })
        return 'OK'


@pytest.fixture
def pool(monkeypatch):
    fake = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake)
    monkeypatch.setattr(drift_api, 'get_pool', lambda: fake)
    monkeypatch.setattr(drift_api, 'predict_drift', _make_predict_drift())
    return fake


def _sos(pool, id_, *, acknowledged=True, resolved=False, has_position=True) -> None:
    pool.sos_events[id_] = {
        'vessel_id': 'V-001',
        'latitude': CASE_LAT if has_position else None,
        'longitude': CASE_LON if has_position else None,
        'created_at': CASE_AT,
        'acknowledged_at': CASE_AT + timedelta(minutes=5) if acknowledged else None,
        'resolved_at': CASE_AT + timedelta(hours=1) if resolved else None,
    }


def _anomaly(pool, id_, *, escalated=True, resolved=False, position=True) -> None:
    pool.anomaly_cases[id_] = {
        'vessel_id': 'V-002',
        'trip_id': 'trip-1',
        'escalated_at': CASE_AT + timedelta(minutes=5) if escalated else None,
        'resolved_at': CASE_AT + timedelta(hours=1) if resolved else None,
    }
    if position:
        pool.buoy_contacts.append({
            'vessel_id': 'V-002', 'trip_id': 'trip-1',
            'latitude': CASE_LAT, 'longitude': CASE_LON,
            'observed_at': CASE_AT - timedelta(hours=1),
        })


def _nearby_buoy(pool, buoy_id: str, *, age_seconds: float = 0.0) -> None:
    """A buoy reading at the exact case position - distance 0, so only the
    age matters for the field-geometry check."""
    pool.current_observations.append({
        'buoy_id': buoy_id,
        'buoy_lat': CASE_LAT,
        'buoy_lon': CASE_LON,
        'observed_at': CASE_AT - timedelta(seconds=age_seconds),
        'observed_u_mps': 0.3,
        'observed_v_mps': 0.1,
    })


def _open_sos_case(client, *, source_id=1) -> dict:
    return client.post(
        '/api/ai/drift/cases',
        headers=AUTH,
        json={'source_type': 'sos', 'source_id': source_id, 'object_class': 'person_in_water'},
    ).json()


# The fake grid (see _fake_prediction) covers x/y in [0, 1000]m around
# origin (11.0, 122.0) - this rectangle safely covers the whole thing.
def _report_body(
    *, run_number=1, method='moderate', idempotency_key='key-1', notes=None,
    south=11.0, west=122.0, north=11.01, east=122.01, searched_at=CASE_AT,
) -> dict:
    body = {
        'run_number': run_number, 'south': south, 'west': west, 'north': north, 'east': east,
        'method': method, 'idempotency_key': idempotency_key,
        'searched_at': searched_at.isoformat() if searched_at else None,
    }
    if notes is not None:
        body['notes'] = notes
    return body


# --- Phase 1: case lifecycle -------------------------------------------------

def test_public_caller_cannot_open_or_read_cases(pool):
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post(
            '/api/ai/drift/cases',
            json={'source_type': 'sos', 'source_id': 1, 'object_class': 'person_in_water'},
        ).status_code == 401
        assert client.get('/api/ai/drift/incidents').status_code == 401
        assert client.get('/api/ai/drift/incident/1').status_code == 401


def test_unacknowledged_sos_cannot_open_a_case(pool):
    _sos(pool, 1, acknowledged=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'sos', 'source_id': 1, 'object_class': 'person_in_water'},
        )
    assert response.status_code == 409
    assert 'not been confirmed' in response.json()['detail']


def test_resolved_sos_cannot_open_a_case(pool):
    _sos(pool, 1, acknowledged=True, resolved=True)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'sos', 'source_id': 1, 'object_class': 'person_in_water'},
        )
    assert response.status_code == 409


def test_confirmed_sos_opens_a_case(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        body = _open_sos_case(client)
    assert body['case_state'] == 'confirmed'
    assert body['source_type'] == 'sos'
    assert body['vessel_id'] == 'V-001'
    assert body['run_number'] == 1


def test_duplicate_case_creation_is_rejected(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'sos', 'source_id': 1, 'object_class': 'person_in_water'},
        )
        second = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'sos', 'source_id': 1, 'object_class': 'person_in_water'},
        )
    assert first.status_code == 200
    assert second.status_code == 409


def test_unescalated_anomaly_cannot_open_a_case(pool):
    _anomaly(pool, 5, escalated=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'anomaly', 'source_id': 5, 'object_class': 'intact_hull_adrift'},
        )
    assert response.status_code == 409


def test_escalated_anomaly_without_a_position_fix_is_rejected(pool):
    _anomaly(pool, 5, escalated=True, position=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'anomaly', 'source_id': 5, 'object_class': 'intact_hull_adrift'},
        )
    assert response.status_code == 422


def test_escalated_anomaly_opens_a_case(pool):
    _anomaly(pool, 5)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'anomaly', 'source_id': 5, 'object_class': 'intact_hull_adrift'},
        )
    assert response.status_code == 200
    assert response.json()['source_type'] == 'anomaly'


def test_resolved_case_rejects_a_new_search_report(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        client.post(f'/api/ai/drift/cases/{incident_id}/resolve', headers=AUTH)
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(),
        )
    assert report.status_code == 409


def test_cancelled_case_rejects_a_new_search_report(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        client.post(
            f'/api/ai/drift/cases/{incident_id}/cancel',
            headers=AUTH, json={'reason': 'false alarm, vessel found at dock'},
        )
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(),
        )
    assert report.status_code == 409


def test_real_incident_response_has_no_ground_truth_field(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        response = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert 'ground_truth_track' not in body
    assert body['incident']['source_type'] == 'sos'
    assert body['incident']['case_state'] == 'confirmed'


def test_synthetic_incident_response_is_visibly_marked_and_carries_ground_truth(pool):
    pool.incidents[9] = {
        'id': 9,
        'vessel_id': 'V-DEMO',
        'last_contact_at': datetime(2026, 8, 1, 8, tzinfo=UTC),
        'last_contact_lat': 11.7,
        'last_contact_lon': 122.4,
        'abnormal_reason': 'capsize',
        'object_class': None,
        'true_track': [{'at': '2026-08-01T08:00:00+00:00', 'lat': 11.7, 'lon': 122.4}],
        'is_synthetic': True,
        'prior_grid': None,
        'posterior_grid': None,
        'source_sos_event_id': None,
        'source_anomaly_case_id': None,
        'resolved_at': None,
        'cancelled_at': None,
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/ai/drift/incident/9', headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body['incident']['is_synthetic'] is True
    assert body['incident']['source_type'] == 'synthetic'
    assert body['ground_truth_track']


def test_incidents_endpoint_lists_summaries(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        _open_sos_case(client)
        response = client.get('/api/ai/drift/incidents', headers=AUTH)

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]['vessel_id'] == 'V-001'
    assert payload[0]['object_class'] == 'person_in_water'
    assert payload[0]['source_type'] == 'sos'
    assert payload[0]['case_state'] == 'confirmed'


# --- Phase 2: environmental quality gate + immutable run snapshots ----------

def test_no_observations_produces_insufficient_field_geometry(pool):
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        response = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH)

    body = response.json()
    assert body['environmental_status'] == 'insufficient_environmental_data'
    assert body['insufficiency_reason'] == 'insufficient_field_geometry'
    assert body['contours'] == []
    assert body['posterior_grid'] is None
    assert body['prediction'] is None


def test_stale_observations_produce_insufficient_field_geometry(pool):
    _nearby_buoy(pool, 'B1', age_seconds=7200)  # 2h old, past the 60-minute policy cutoff
    _nearby_buoy(pool, 'B2', age_seconds=7200)
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        response = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH)

    assert response.json()['insufficiency_reason'] == 'insufficient_field_geometry'


def test_a_single_nearby_buoy_is_insufficient_geometry(pool):
    _nearby_buoy(pool, 'B1')  # only one - MIN_NEARBY_BUOYS is 2
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        response = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH)

    assert response.json()['insufficiency_reason'] == 'insufficient_field_geometry'


def test_degraded_wind_is_rejected_even_with_good_current_coverage(pool, monkeypatch):
    monkeypatch.setattr(drift_api, 'predict_drift', _make_predict_drift(degraded=True))
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        response = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH)

    body = response.json()
    assert body['environmental_status'] == 'insufficient_environmental_data'
    assert body['insufficiency_reason'] == 'degraded_wind_source'
    assert body['contours'] == []


def test_fresh_quality_passing_observations_produce_a_contour(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        opened = _open_sos_case(client)
        incident_id = opened['id']
        response = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH)

    assert opened['environmental_status'] == 'ok'
    body = response.json()
    assert body['environmental_status'] == 'ok'
    assert body['insufficiency_reason'] is None
    assert body['posterior_grid'] is not None
    assert len(body['contours']) == 3  # 50/75/95% mass targets
    assert body['prediction']['object_class'] == 'person_in_water'
    assert body['observation_fraction'] == 1.0


def test_repeated_gets_return_the_identical_stored_run(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        first = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH).json()
        second = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH).json()

    assert first['run_number'] == second['run_number'] == 1
    assert first['computed_at'] == second['computed_at']
    assert first['posterior_grid'] == second['posterior_grid']


def test_rerun_creates_a_new_version_without_modifying_the_first(pool):
    _sos(pool, 1)  # no buoys yet - run 1 is insufficient
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        first = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH).json()
        assert first['environmental_status'] == 'insufficient_environmental_data'

        # Buoys arrive after the fact - a responder explicitly reruns.
        _nearby_buoy(pool, 'B1')
        _nearby_buoy(pool, 'B2')
        rerun = client.post(f'/api/ai/drift/cases/{incident_id}/rerun', headers=AUTH)
        assert rerun.status_code == 200
        assert rerun.json()['run_number'] == 2
        assert rerun.json()['environmental_status'] == 'ok'

        second = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH).json()

    assert second['run_number'] == 2
    assert second['environmental_status'] == 'ok'
    # The original run is still there, untouched.
    stored_runs = pool.drift_runs[incident_id]
    assert len(stored_runs) == 2
    assert stored_runs[0]['run_number'] == 1
    assert stored_runs[0]['environmental_status'] == 'insufficient_environmental_data'


def test_search_report_is_rejected_when_the_current_run_is_insufficient(pool):
    _sos(pool, 1)  # no buoys - insufficient
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(),
        )
    assert report.status_code == 409


def test_search_report_updates_the_current_runs_posterior(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(),
        )
        detail = client.get(f'/api/ai/drift/incident/{incident_id}', headers=AUTH).json()

    assert report.status_code == 200
    assert len(report.json()['search_sectors']) == 1
    assert detail['search_sectors']


# --- Phase 3: protected search-sector report contract -----------------------

def test_public_caller_cannot_report_a_search(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        response = client.post(f'/api/ai/drift/incident/{incident_id}/searched', json=_report_body())
    assert response.status_code == 401


def test_reversed_bounds_are_rejected(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        north_south = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(south=11.01, north=11.0),
        )
        east_west = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(east=122.0, west=122.01),
        )
    assert north_south.status_code == 422
    assert east_west.status_code == 422


def test_out_of_grid_sector_is_rejected(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH,
            json=_report_body(south=5.0, west=100.0, north=5.01, east=100.01),
        )
    assert report.status_code == 422


def test_unknown_detection_method_is_rejected(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(method='perfect'),
        )
    assert report.status_code == 422


def test_no_detection_preset_reaches_full_certainty():
    """A search is never perfect - the approved presets are the only way a
    probability reaches the model, and none of them is 1.0 (docs/40 Phase 3
    item 2 / acceptance boundary "detection probability of 1.0 is rejected").
    """
    assert all(0.0 < value < 1.0 for value in drift_api.DETECTION_PRESETS.values())


def test_stale_run_is_rejected_after_a_rerun(pool):
    _sos(pool, 1)  # no buoys yet - run 1 is insufficient
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']

        _nearby_buoy(pool, 'B1')
        _nearby_buoy(pool, 'B2')
        client.post(f'/api/ai/drift/cases/{incident_id}/rerun', headers=AUTH)  # -> run 2

        stale = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(run_number=1),
        )
        current = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(run_number=2),
        )
    assert stale.status_code == 409
    assert 'stale run' in stale.json()['detail']
    assert current.status_code == 200


def test_duplicate_idempotency_key_does_not_double_apply(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        first = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(idempotency_key='same-key'),
        )
        second = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH, json=_report_body(idempotency_key='same-key'),
        )

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()['duplicate'] is False
    assert second.json()['duplicate'] is True
    assert second.json()['posterior_grid'] == first.json()['posterior_grid']
    assert len(pool.search_sectors) == 1

    # docs/41 Phase 2: the retry is auditable as a duplicate, not a second
    # real state transition, and the searched rectangle/notes never appear.
    report_events = [e for e in pool.audit_events if e['action'] == 'drift.search_sector_report']
    assert [e['outcome'] for e in report_events] == ['updated', 'duplicate']
    assert all(e['correlation_key'] == 'same-key' for e in report_events)


def test_two_sequential_reports_against_the_same_run_both_apply(pool):
    # The fake grid's two cells with nonzero mass are at x/y centres
    # (250, 250) and (750, 250)m from the origin - these rectangles hit one
    # each, so the runs are distinguishable rather than a uniform scaling
    # that renormalises away.
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        first = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH,
            json=_report_body(idempotency_key='report-1', south=11.0, west=122.0, north=11.003, east=122.003),
        )
        second = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH,
            json=_report_body(idempotency_key='report-2', south=11.0, west=122.006, north=11.003, east=122.009),
        )

    assert first.status_code == 200 and second.status_code == 200
    # The second report saw the first report's posterior, not the original
    # prior - it did not overwrite it.
    assert second.json()['posterior_grid'] != first.json()['posterior_grid']
    assert len(second.json()['search_sectors']) == 2
    assert len(pool.search_sectors) == 2


def test_next_area_lies_within_the_grid_with_positive_remaining_mass(pool):
    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)
    with TestClient(app, raise_server_exceptions=False) as client:
        incident_id = _open_sos_case(client)['id']
        report = client.post(
            f'/api/ai/drift/incident/{incident_id}/searched',
            headers=AUTH,
            json=_report_body(south=11.0, west=122.0, north=11.0045, east=122.0045),
        )

    assert report.status_code == 200
    next_area = report.json()['next_area']
    assert next_area['label'] == 'recommendation for responder review'
    assert next_area['remaining_mass'] > 0.0
    bounds = next_area['bounds']
    assert 11.0 <= bounds['south'] < bounds['north'] <= 11.01
    assert 122.0 <= bounds['west'] < bounds['east'] <= 122.01
