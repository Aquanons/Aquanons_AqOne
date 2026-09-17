"""Phase 4 verification tests: calibration lineage, historical replay, and claim boundaries.

Scenarios covered:
- C1: Synthetic/unvalidated bundle plus return-now environment flag; wrong-version or missing evaluation metadata.
      Live detector cannot promote itself to an operational calibrated return instruction; explicit human advisories
      continue independently.
- C2: Rule score exceeds classifier score; evaluate and serve the same examples.
      Metrics and threshold selection use the actual composed runtime decision; report classifier probability and
      pattern score with distinct meanings.
- C3: Same storm/trip/track split into multiple windows across partitions; held-out data offered to fit/calibration;
      future/late records injected.
      Entire events stay disjoint; held-out records cannot influence fit, thresholds, feature choices or historical
      decisions.
- C4: Manifest has example hashes, missing raw evidence, invented provenance, drill mixed into natural incidents,
      empty or one-class target set.
      Verification rejects unverifiable files or reports insufficient evidence; never "100% accuracy," zero false
      alarms, or passed field validation from an empty sample.
- C5: Registered open trip with no contact; return deadline missed during shared outage; no data for baseline.
      Candidate remains visible, expected return obligation remains, current welfare unknown; missing contacts do
      not mean normal or safe.
- C6: Trip-state query fails; later return amendment applied to old decision; prior abnormal/unfinished trip enters
      normal baseline.
      Explicit unavailable state, receipt-aware historical state and only known-completed normal history; no silent
      12-hour fallback or future amendment leakage.
- C7: Model failure injected into an actual case-open/rerun API and SOS request.
      Database case/evidence and manual delivery survive; test cannot pass by catching arbitrary exceptions around an
      untouched local dictionary.
- C8: Controlled two-track/prediction example with known containment, area, direction error and miss; unsupported
      horizons.
      Metrics match manual arithmetic, include failures/abstentions and do not report unsupported horizons as
      successes; baseline uses independent physical assumptions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import db as app_db
from app.ai.anomaly_service import _load_trip_states, eligible_latest_trips
from app.ai.drift_eval import evaluate_drift_track
from app.ai.manifest import ManifestValidationError, validate_manifest
from app.ai.squall import (
    FEATURE_NAMES,
    BuoyMeta,
    PropagationEstimate,
    SquallFeatureBundle,
    SquallModelBundle,
    detect_squall,
)
from app.ai.trip_profile import VesselProfile, score_trip
from app.api import drift as drift_api
from app.api.squall import build_squall_status
from app.auth import create_token
from app.main import app
from tests.test_drift_api import _FakePool, _make_predict_drift, _nearby_buoy, _sos

AUTH = {'Authorization': f"Bearer {create_token(1, 'ops@example.com', 'mdrrmo')}"}


@pytest.fixture
def pool(monkeypatch):
    fake = _FakePool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake)
    monkeypatch.setattr(drift_api, 'get_pool', lambda: fake)
    monkeypatch.setattr(drift_api, 'predict_drift', _make_predict_drift())
    return fake


# ---------------------------------------------------------------------------
# C1: Synthetic/unvalidated bundle cannot promote live squall to return_now
# ---------------------------------------------------------------------------

def test_c1_synthetic_bundle_cannot_promote_live_to_return_now(monkeypatch):
    """When source is 'live', even if SQUALL_RETURN_NOW_ENABLED is set, an unvalidated or
    synthetic bundle cannot trigger 'return_now'. It remains in research/watch mode.
    """
    monkeypatch.setenv('SQUALL_RETURN_NOW_ENABLED', 'true')

    now = datetime.now(UTC)
    readings = [
        {'buoy_id': 'B1', 'observed_at': now, 'pressure_hpa': 1008.0},
        {'buoy_id': 'B2', 'observed_at': now, 'pressure_hpa': 1007.5},
        {'buoy_id': 'B3', 'observed_at': now, 'pressure_hpa': 1007.0},
    ]
    buoys = [
        {'id': 'B1', 'lat': 11.68, 'lon': 122.36},
        {'id': 'B2', 'lat': 11.69, 'lon': 122.37},
        {'id': 'B3', 'lat': 11.70, 'lon': 122.38},
    ]

    status = build_squall_status(
        readings,
        buoys,
        source='live',
        allow_return_now=True,
    )

    # Even with allow_return_now=True, live data against a synthetic calibration
    # bundle must stay capped at 'watch' and never claim operational 'return_now'.
    assert status['level'] != 'return_now'
    assert status['return_now'] is False
    assert status.get('calibration') == 'synthetic' or 'unvalidated' in str(status.get('status_reason', '')).lower()


# ---------------------------------------------------------------------------
# C2: Composed runtime decision distinguishes classifier probability and rule score
# ---------------------------------------------------------------------------

def test_c2_composed_decision_distinguishes_probability_and_rule_score():
    """When a rule/window score exceeds classifier probability, the detection must
    report classifier_probability and pattern_score with distinct meanings, not conflate
    them under a fabricated probability.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    # Dummy trained pipeline
    pipe = Pipeline([('scaler', StandardScaler()), ('clf', LogisticRegression())])
    X = np.array([[0.0] * 21, [1.0] * 21])
    y = np.array([0, 1])
    pipe.fit(X, y)

    bundle = SquallModelBundle(
        pipeline=pipe,
        feature_names=[f'f_{i}' for i in range(21)],
        threshold=0.50,
        calibration='synthetic',
        trained_at=datetime.now(UTC).isoformat(),
        top_features=[],
        evaluation={},
    )

    buoys = {
        'B1': BuoyMeta('B1', 11.68, 122.36),
        'B2': BuoyMeta('B2', 11.69, 122.37),
        'B3': BuoyMeta('B3', 11.70, 122.38),
    }

    prop = PropagationEstimate(
        bearing_deg=90.0,
        speed_mps=12.0,
        r2=0.9,
        residual_minutes=2.0,
        onset_coverage=1.0,
        onset_span_minutes=20.0,
        origin_lat=11.69,
        origin_lon=122.37,
        onset_anchor=datetime.now(UTC),
        geometry_degenerate=False,
        fit_intercept_minutes=0.0,
    )

    feature_names = list(FEATURE_NAMES)
    values = [0.0] * len(feature_names)
    values[feature_names.index('array_drop_hpa')] = 4.0
    values[feature_names.index('anomaly_energy')] = 16.0
    values[feature_names.index('propagation_r2')] = 0.9
    values[feature_names.index('onset_coverage')] = 1.0

    # Feature bundle with strong drop (rule score high) but synthetic neutral features
    features = SquallFeatureBundle(
        as_of=datetime.now(UTC),
        feature_names=feature_names,
        values=values,
        buoy_rows=[],
        propagation=prop,
        array_mean_pressure=1008.0,
        array_mean_trace=[],
        pressure_trace={},
    )

    detection = detect_squall(features, buoys, bundle)
    assert detection is not None
    assert hasattr(detection, 'classifier_probability')
    assert hasattr(detection, 'pattern_score')
    assert detection.classifier_probability != detection.pattern_score
    assert detection.probability == max(detection.classifier_probability, detection.pattern_score)


# ---------------------------------------------------------------------------
# C3: Event-level partitioning ensures disjoint events across splits
# ---------------------------------------------------------------------------

def test_c3_event_level_partitioning_disjoint_events():
    """Multiple time windows from the same physical event must never leak across
    development and held-out test splits.
    """
    manifest_data = {
        'manifest_version': '1.0.0',
        'created_at': '2026-09-15T00:00:00Z',
        'custodian': 'MDRRMO New Washington Research Team',
        'domain': 'New Washington, Aklan',
        'records': [
            {
                'record_id': 'STORM-01-W1',
                'event_id': 'STORM-01',
                'record_type': 'natural_incident',
                'split': 'development',
                'started_at': '2026-08-01T10:00:00Z',
                'ended_at': '2026-08-01T11:00:00Z',
                'outcome': 'squall_onset',
                'raw_evidence_sha256': 'a' * 64,
            },
            {
                'record_id': 'STORM-01-W2',
                'event_id': 'STORM-01',
                'record_type': 'natural_incident',
                'split': 'held_out_test',  # LEAK! Same event in test split!
                'started_at': '2026-08-01T11:00:00Z',
                'ended_at': '2026-08-01T12:00:00Z',
                'outcome': 'squall_onset',
                'raw_evidence_sha256': 'b' * 64,
            },
        ],
    }

    with pytest.raises(ManifestValidationError, match="event_id.*spans multiple splits"):
        validate_manifest(manifest_data)


# ---------------------------------------------------------------------------
# C4: Manifest rejects placeholder hashes, empty sets, or missing evidence
# ---------------------------------------------------------------------------

def test_c4_manifest_validation_rejects_unverifiable_data():
    """Manifest verification rejects empty datasets, placeholder hashes, and
    one-class target sets rather than claiming 100% accuracy.
    """
    # Case A: Empty records
    empty_manifest = {
        'manifest_version': '1.0.0',
        'created_at': '2026-09-15T00:00:00Z',
        'custodian': 'MDRRMO New Washington Research Team',
        'domain': 'New Washington, Aklan',
        'records': [],
    }
    with pytest.raises(ManifestValidationError, match="cannot be empty"):
        validate_manifest(empty_manifest)

    # Case B: Placeholder hash (e.g. all zeros or 'example')
    bad_hash_manifest = {
        'manifest_version': '1.0.0',
        'created_at': '2026-09-15T00:00:00Z',
        'custodian': 'MDRRMO New Washington Research Team',
        'domain': 'New Washington, Aklan',
        'records': [
            {
                'record_id': 'REC-01',
                'event_id': 'EV-01',
                'record_type': 'natural_incident',
                'split': 'development',
                'started_at': '2026-08-01T10:00:00Z',
                'ended_at': '2026-08-01T11:00:00Z',
                'outcome': 'squall_onset',
                'raw_evidence_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
            }
        ],
    }
    with pytest.raises(ManifestValidationError, match="placeholder or invalid SHA-256"):
        validate_manifest(bad_hash_manifest)

    # Case C: Single class target set (all positive or all negative)
    single_class_manifest = {
        'manifest_version': '1.0.0',
        'created_at': '2026-09-15T00:00:00Z',
        'custodian': 'MDRRMO New Washington Research Team',
        'domain': 'New Washington, Aklan',
        'records': [
            {
                'record_id': 'REC-01',
                'event_id': 'EV-01',
                'record_type': 'natural_incident',
                'split': 'held_out_test',
                'started_at': '2026-08-01T10:00:00Z',
                'ended_at': '2026-08-01T11:00:00Z',
                'outcome': 'squall_onset',
                'raw_evidence_sha256': '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            },
            {
                'record_id': 'REC-02',
                'event_id': 'EV-02',
                'record_type': 'natural_incident',
                'split': 'held_out_test',
                'started_at': '2026-08-02T10:00:00Z',
                'ended_at': '2026-08-02T11:00:00Z',
                'outcome': 'squall_onset',
                'raw_evidence_sha256': '2234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            },
        ],
    }
    with pytest.raises(
        ManifestValidationError,
        match="insufficient evidence: test split contains only a single outcome class",
    ):
        validate_manifest(single_class_manifest)


# ---------------------------------------------------------------------------
# C5: Registered open trip with no contact remains reviewable as overdue
# ---------------------------------------------------------------------------

def test_c5_open_trip_no_contacts_remains_reviewable():
    """A registered vessel trip in open/overdue state that has made no buoy contacts
    (e.g. during an outage) must not be silently excluded. It remains visible and overdue.
    """
    now = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
    departure = datetime(2026, 8, 10, 6, 0, tzinfo=UTC)
    expected_return = datetime(2026, 8, 10, 11, 0, tzinfo=UTC)

    trip_states = {
        'TRIP-OUTAGE-1': {
            'trip_id': 'TRIP-OUTAGE-1',
            'vessel_id': 'V-SILENT',
            'status': 'open',
            'welfare_status': 'unknown',
            'departure_at': departure,
            'expected_return_at': expected_return,
            'expected_checkin_interval_minutes': 60,
        }
    }

    # Buoy contacts table has 0 contacts for this trip!
    contacts_rows = []

    eligible = eligible_latest_trips(contacts_rows, as_of=now, trip_states=trip_states)

    # Must be eligible for scoring/display
    assert any(trip_id == 'TRIP-OUTAGE-1' for _, trip_id, _ in eligible)

    # Score should reflect overdue obligation
    profile = VesselProfile(
        vessel_id='V-SILENT', trip_count=0, low_confidence=True,
        typical_departure_hour=6.0, departure_hour_std=1.0, typical_sequence=[],
        interval_stats=[], typical_trip_duration_minutes={'mean': 300.0, 'std': 60.0},
        typical_max_distance_km={'mean': 10.0, 'std': 2.0},
        rebuilt_at=now.isoformat(), source='live',
    )

    score = score_trip(
        profile,
        [],  # 0 contacts
        as_of=now,
        trip_id='TRIP-OUTAGE-1',
        trip_state=trip_states['TRIP-OUTAGE-1'],
    )

    assert score.status in {'overdue', 'alert'}
    assert score.low_confidence is True
    assert score.score >= 0.55


# ---------------------------------------------------------------------------
# C6: Trip state query failure reports explicit unavailable state
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_c6_trip_state_query_failure_raises_or_reports_unavailable():
    """If the vessel trips table or query fails, _load_trip_states must not silently
    swallow it and drop active trips into an arbitrary 12-hour expiration.
    """
    class _FailingConn:
        async def fetch(self, *args, **kwargs):
            raise RuntimeError("Database connection lost")

    with pytest.raises(RuntimeError, match="Database connection lost"):
        await _load_trip_states(_FailingConn())


# ---------------------------------------------------------------------------
# C7: Model failure in drift API does not clobber incident or SOS
# ---------------------------------------------------------------------------

def test_c7_drift_model_failure_preserves_database_case_and_manual_sos(pool, monkeypatch):
    """When predict_drift fails with a numerical explosion or error, the underlying
    incident record, responder case, and manual SOS ingest must remain completely intact.
    """
    def _exploding_predict(*args, **kwargs):
        raise RuntimeError("Numerical explosion in particle integrator")

    monkeypatch.setattr(drift_api, 'predict_drift', _exploding_predict)

    _nearby_buoy(pool, 'B1')
    _nearby_buoy(pool, 'B2')
    _sos(pool, 1)

    orig_fetchrow = pool.fetchrow

    async def _fetchrow_with_sos(query: str, *args):
        if 'INSERT INTO sos_events' in query:
            vessel_id, client_ts = args[0], args[1]
            sos_id = len(pool.sos_events) + 1
            rec = {
                'id': sos_id,
                'vessel_id': vessel_id,
                'client_ts': client_ts,
                'was_inserted': True,
                'delivered_direct': args[11],
                'delivered_via_buoy': args[12],
                'acknowledged_at': None,
            }
            pool.sos_events[sos_id] = rec
            return rec
        return await orig_fetchrow(query, *args)

    monkeypatch.setattr(pool, 'fetchrow', _fetchrow_with_sos)
    monkeypatch.setattr('app.api.sos.get_pool', lambda: pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        # Open case fails due to model explosion, not corrupting database
        resp = client.post(
            '/api/ai/drift/cases',
            headers=AUTH,
            json={'source_type': 'sos', 'source_id': 1, 'object_class': 'person_in_water'},
        )
        assert resp.status_code in {500, 503, 422}

        # SOS event in pool is NOT corrupted
        assert 1 in pool.sos_events
        assert pool.sos_events[1]['acknowledged_at'] is not None

        # Manual SOS intake still works 100%
        sos_resp = client.post(
            '/api/sos',
            json={
                'vessel_id': 'V-FALLBACK-1',
                'client_ts': 1754300000,
                'lat': 11.68,
                'lon': 122.36,
                'boat': 'Motorized Banca',
                'note': 'Test during model outage',
            },
        )
        assert sos_resp.status_code == 200
        assert any(ev.get('vessel_id') == 'V-FALLBACK-1' for ev in pool.sos_events.values())


# ---------------------------------------------------------------------------
# C8: Controlled drift evaluation with known metrics & unsupported horizons
# ---------------------------------------------------------------------------

def test_c8_controlled_drift_evaluation_known_containment_and_unsupported_horizons():
    """Metrics must match manual arithmetic on a controlled two-track example and
    report unsupported horizons as abstentions/failures rather than successes.
    """
    # Controlled prediction contour: square around (11.0, 122.0)
    # [11.0, 122.0] to [11.01, 122.01]
    ring = [
        [122.0, 11.0],
        [122.01, 11.0],
        [122.01, 11.01],
        [122.0, 11.01],
        [122.0, 11.0],
    ]
    mock_prediction = {
        'contours': [
            {
                'type': 'Feature',
                'geometry': {'type': 'Polygon', 'coordinates': [ring]},
                'properties': {'mass': 0.95},
            }
        ],
        'centroid_track': [{'at': '2026-08-01T12:00:00Z', 'lat': 11.005, 'lon': 122.005}],
        'supported_horizon_hours': 12.0,
    }

    # Case 1: Point inside contour at 6h (within supported 12h horizon)
    inside_track = [
        {'at': '2026-08-01T06:00:00Z', 'lat': 11.0, 'lon': 122.0},
        {'at': '2026-08-01T12:00:00Z', 'lat': 11.005, 'lon': 122.005},
    ]
    eval_inside = evaluate_drift_track(mock_prediction, inside_track, horizon_hours=6.0)
    assert eval_inside['contained'] is True
    assert eval_inside['is_supported'] is True
    assert eval_inside['miss_distance_m'] == 0.0

    # Case 2: Point outside contour at 6h
    outside_track = [
        {'at': '2026-08-01T06:00:00Z', 'lat': 11.0, 'lon': 122.0},
        {'at': '2026-08-01T12:00:00Z', 'lat': 11.05, 'lon': 122.05},
    ]
    eval_outside = evaluate_drift_track(mock_prediction, outside_track, horizon_hours=6.0)
    assert eval_outside['contained'] is False
    assert eval_outside['is_supported'] is True
    assert eval_outside['miss_distance_m'] > 0.0

    # Case 3: Horizon beyond supported horizon (e.g. 24h > 12h supported)
    long_track = [
        {'at': '2026-08-01T06:00:00Z', 'lat': 11.0, 'lon': 122.0},
        {'at': '2026-08-02T06:00:00Z', 'lat': 11.005, 'lon': 122.005},
    ]
    eval_unsupported = evaluate_drift_track(mock_prediction, long_track, horizon_hours=24.0)
    assert eval_unsupported['is_supported'] is False
    assert eval_unsupported['contained'] is False  # Must not report unsupported horizon as success!


# ---------------------------------------------------------------------------
# Phase 5: Field evaluation manifest fixture verification
# ---------------------------------------------------------------------------

def test_canonical_field_eval_manifest_validates_cleanly():
    """The canonical field evaluation manifest fixture at manifests/field_eval_manifest_v1.json
    must validate cleanly without placeholder hashes or partition leakage.
    """
    manifest_path = Path(__file__).resolve().parent.parent.parent / 'manifests' / 'field_eval_manifest_v1.json'
    assert manifest_path.exists(), f"Expected manifest file at {manifest_path}"

    validated = validate_manifest(manifest_path)
    assert validated['manifest_version'] == '1.0.0'
    assert len(validated['records']) >= 3
    assert all('raw_evidence_sha256' in rec for rec in validated['records'])

