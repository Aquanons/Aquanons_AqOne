from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.ai.squall import (
    QUALITY_MIN_BUOYS,
    assess_array_quality,
    build_buoys,
    build_history,
    estimate_propagation_vector,
    extract_pressure_features,
)
from app.api import public as public_api
from app.api import squall as squall_api
from app.main import app


def _buoy_rows() -> list[dict[str, object]]:
    return [
        {'id': 'B01', 'lat': 11.6892, 'lon': 122.3667, 'contact_radius_m': 900},
        {'id': 'B02', 'lat': 11.6992, 'lon': 122.4667, 'contact_radius_m': 900},
        {'id': 'B03', 'lat': 11.7192, 'lon': 122.5667, 'contact_radius_m': 900},
        {'id': 'B04', 'lat': 11.7192, 'lon': 122.6667, 'contact_radius_m': 900},
    ]


def _collinear_buoy_rows() -> list[dict[str, object]]:
    return [
        {'id': 'B01', 'lat': 11.6892, 'lon': 122.3667, 'contact_radius_m': 900},
        {'id': 'B02', 'lat': 11.6892, 'lon': 122.4667, 'contact_radius_m': 900},
        {'id': 'B03', 'lat': 11.6892, 'lon': 122.5667, 'contact_radius_m': 900},
    ]


def _readings(as_of: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for offset_minutes in range(90, -5, -5):
        at = as_of - timedelta(minutes=offset_minutes)
        for index, buoy_id in enumerate(['B01', 'B02', 'B03', 'B04']):
            base = 1015.0
            if buoy_id == 'B01' and offset_minutes <= 30:
                base -= (30 - offset_minutes) * 0.06
            if buoy_id == 'B02' and offset_minutes <= 45:
                base -= (45 - offset_minutes) * 0.04
            rows.append({'buoy_id': buoy_id, 'observed_at': at, 'pressure_hpa': base - index * 0.02})
    return rows


def test_extract_pressure_features_returns_pressure_trace_and_buoy_rows():
    as_of = datetime(2026, 8, 4, 12, tzinfo=UTC)
    buoys = build_buoys(_buoy_rows())
    history = build_history(_readings(as_of))

    bundle = extract_pressure_features(history, buoys, as_of)

    assert bundle.feature_names[0] == 'mean_tendency_30'
    assert len(bundle.values) == len(bundle.feature_names)
    assert set(bundle.pressure_trace) == {'B01', 'B02', 'B03', 'B04'}
    assert len(bundle.buoy_rows) == 4
    assert bundle.buoy_rows[0].pressure_tendency_30 <= 0


def test_propagation_vector_estimate_tracks_eastward_onset_progression():
    buoys = build_buoys(_buoy_rows())
    as_of = datetime(2026, 8, 4, 12, tzinfo=UTC)
    onset_times = {
        'B01': as_of - timedelta(minutes=45),
        'B02': as_of - timedelta(minutes=30),
        'B03': as_of - timedelta(minutes=15),
        'B04': as_of,
    }

    estimate = estimate_propagation_vector(onset_times, buoys)

    assert 75 <= estimate.bearing_deg <= 105
    assert estimate.speed_mps > 0
    assert estimate.onset_coverage == 1.0
    assert estimate.onset_span_minutes == 45.0
    assert estimate.geometry_degenerate is False


def test_propagation_vector_flags_collinear_geometry_and_caps_confidence():
    buoys = build_buoys(
        [
            {'id': 'B01', 'lat': 11.6892, 'lon': 122.3667, 'contact_radius_m': 900},
            {'id': 'B02', 'lat': 11.6892, 'lon': 122.4667, 'contact_radius_m': 900},
            {'id': 'B03', 'lat': 11.6892, 'lon': 122.5667, 'contact_radius_m': 900},
            {'id': 'B04', 'lat': 11.6892, 'lon': 122.6667, 'contact_radius_m': 900},
        ]
    )
    as_of = datetime(2026, 8, 4, 12, tzinfo=UTC)
    onset_times = {
        'B01': as_of - timedelta(minutes=45),
        'B02': as_of - timedelta(minutes=30),
        'B03': as_of - timedelta(minutes=15),
        'B04': as_of,
    }

    estimate = estimate_propagation_vector(onset_times, buoys)

    assert estimate.geometry_degenerate is True
    assert estimate.r2 == 0.0


def _quality_readings(buoy_ids: list[str], as_of: datetime) -> list[dict[str, object]]:
    """5-minute-step readings covering the full 90-minute lookback, no gaps."""
    rows: list[dict[str, object]] = []
    for offset_minutes in range(90, -1, -5):
        at = as_of - timedelta(minutes=offset_minutes)
        for index, buoy_id in enumerate(buoy_ids):
            rows.append({'buoy_id': buoy_id, 'observed_at': at, 'pressure_hpa': 1015.0 - index * 0.02})
    return rows


def test_assess_array_quality_accepts_a_complete_fresh_non_collinear_array():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())
    history = build_history(_quality_readings(['B01', 'B02', 'B03', 'B04'], as_of))

    quality = assess_array_quality(history, buoys, as_of)

    assert quality.ok is True
    assert quality.reason is None
    assert set(quality.qualifying_buoy_ids) == {'B01', 'B02', 'B03', 'B04'}
    assert quality.newest_observed_at == as_of


def test_assess_array_quality_reports_insufficient_data_when_no_readings_exist():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())

    quality = assess_array_quality({}, buoys, as_of)

    assert quality.ok is False
    assert f'0 of {QUALITY_MIN_BUOYS}' in quality.reason
    assert quality.newest_observed_at is None
    assert quality.qualifying_buoy_ids == []


def test_assess_array_quality_excludes_a_stale_buoy_but_still_qualifies_with_three():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())
    rows = _quality_readings(['B01', 'B02', 'B03', 'B04'], as_of)
    # B04's latest reading is 30 minutes old - well past the 10-minute freshness bound.
    rows = [r for r in rows if not (r['buoy_id'] == 'B04' and r['observed_at'] > as_of - timedelta(minutes=30))]
    history = build_history(rows)

    quality = assess_array_quality(history, buoys, as_of)

    assert quality.ok is True
    assert set(quality.qualifying_buoy_ids) == {'B01', 'B02', 'B03'}


def test_assess_array_quality_is_insufficient_with_only_two_fresh_buoys():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())
    rows = _quality_readings(['B01', 'B02', 'B03', 'B04'], as_of)
    stale_cutoff = as_of - timedelta(minutes=30)
    rows = [r for r in rows if not (r['buoy_id'] in {'B03', 'B04'} and r['observed_at'] > stale_cutoff)]
    history = build_history(rows)

    quality = assess_array_quality(history, buoys, as_of)

    assert quality.ok is False
    assert 'B03' not in quality.qualifying_buoy_ids
    assert 'B04' not in quality.qualifying_buoy_ids


def test_assess_array_quality_rejects_a_buoy_with_out_of_range_pressure():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())
    rows = _quality_readings(['B01', 'B02', 'B03', 'B04'], as_of)
    for row in rows:
        if row['buoy_id'] == 'B04' and row['observed_at'] == as_of:
            row['pressure_hpa'] = 5000.0  # sensor fault, well outside the sanity range

    quality = assess_array_quality(build_history(rows), buoys, as_of)

    assert quality.ok is True
    assert 'B04' not in quality.qualifying_buoy_ids


def test_assess_array_quality_rejects_a_gap_wider_than_tolerance():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())
    rows = _quality_readings(['B01', 'B02', 'B03', 'B04'], as_of)
    # Drop a real 20-minute stretch out of B04's history, distinct from staleness.
    gap_start = as_of - timedelta(minutes=50)
    gap_end = as_of - timedelta(minutes=30)
    rows = [r for r in rows if not (r['buoy_id'] == 'B04' and gap_start < r['observed_at'] < gap_end)]

    quality = assess_array_quality(build_history(rows), buoys, as_of)

    assert quality.ok is True
    assert 'B04' not in quality.qualifying_buoy_ids


def test_assess_array_quality_rejects_collinear_geometry_even_with_enough_fresh_buoys():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_collinear_buoy_rows())
    history = build_history(_quality_readings(['B01', 'B02', 'B03'], as_of))

    quality = assess_array_quality(history, buoys, as_of)

    assert quality.ok is False
    assert len(quality.qualifying_buoy_ids) == 3  # each buoy individually qualifies
    assert 'geometry' in quality.reason or 'collinear' in quality.reason or 'degenerate' in quality.reason


def test_assess_array_quality_reports_newest_observation_even_when_insufficient():
    as_of = datetime.now(UTC)
    buoys = build_buoys(_buoy_rows())
    lone_reading_at = as_of - timedelta(minutes=3)
    history = build_history([{'buoy_id': 'B01', 'observed_at': lone_reading_at, 'pressure_hpa': 1010.0}])

    quality = assess_array_quality(history, buoys, as_of)

    assert quality.ok is False
    assert quality.newest_observed_at == lone_reading_at


class _FakeSquallPool:
    """Enough of the pool surface for `_load_rows` (app/api/squall.py) to run
    against seeded readings/buoys instead of a real database.

    `is_synthetic` mirrors the real column: a pool built with
    `is_synthetic=True` only answers a query that asks for synthetic rows,
    and vice versa - the same source-isolation the live/demo tables enforce.
    """

    def __init__(
        self,
        readings: list[dict[str, object]],
        buoy_rows: list[dict[str, object]] | None = None,
        *,
        is_synthetic: bool = False,
    ) -> None:
        self._readings = readings
        self._buoy_rows = buoy_rows if buoy_rows is not None else _buoy_rows()
        self._is_synthetic = is_synthetic

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def fetch(self, query: str, *args):
        wants_synthetic = args[0] if args else None
        if wants_synthetic is not None and wants_synthetic != self._is_synthetic:
            return []
        if 'FROM barometric_readings' in query:
            return list(self._readings)
        if 'FROM buoys' in query:
            return list(self._buoy_rows)
        return []


def _mock_threshold_crossing_detection(monkeypatch, *, probability: float = 0.9) -> None:
    monkeypatch.setattr(squall_api, 'load_bundle', lambda: object())
    monkeypatch.setattr(
        squall_api,
        'current_detection',
        lambda readings, buoys, model: [
            {'probability': probability, 'arrival_by_buoy': [{'buoy_id': 'B01', 'arrival_minutes': 12}]}
        ],
    )
    monkeypatch.setattr(
        squall_api,
        'event_detection_summary',
        lambda model, detections: {
            'threshold': 0.5,
            'detections': detections,
            'top_features': [],
            'evaluation': {},
        },
    )


def test_fresh_qualifying_live_array_is_watch_when_return_now_disabled(monkeypatch):
    """Contrast case for the insufficient-array test below: fresh, complete
    data must still reach a candidate state - the gate must not make
    GET /api/public/squall permanently inert. But a live detection must be
    capped at watch, never return_now, until the flag is enabled
    (docs/39 Phase 3/4 safety boundary)."""
    monkeypatch.delenv('SQUALL_RETURN_NOW_ENABLED', raising=False)
    now = datetime.now(UTC)
    pool = _FakeSquallPool(_quality_readings(['B01', 'B02', 'B03', 'B04'], now))
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)
    _mock_threshold_crossing_detection(monkeypatch)

    with TestClient(app) as client:
        response = client.get('/api/public/squall')

    body = response.json()
    assert body['level'] == 'watch'
    assert body['return_now'] is False
    assert body['source'] == 'live'
    assert body['lead_minutes'] == 12


def test_fresh_qualifying_live_array_reaches_return_now_when_flag_enabled(monkeypatch):
    monkeypatch.setenv('SQUALL_RETURN_NOW_ENABLED', 'true')
    now = datetime.now(UTC)
    pool = _FakeSquallPool(_quality_readings(['B01', 'B02', 'B03', 'B04'], now))
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)
    _mock_threshold_crossing_detection(monkeypatch)

    with TestClient(app) as client:
        response = client.get('/api/public/squall')

    body = response.json()
    assert body['level'] == 'return_now'
    assert body['return_now'] is True


def test_fresh_qualifying_live_array_below_threshold_is_clear(monkeypatch):
    now = datetime.now(UTC)
    pool = _FakeSquallPool(_quality_readings(['B01', 'B02', 'B03', 'B04'], now))
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)
    monkeypatch.setattr(squall_api, 'load_bundle', lambda: object())
    monkeypatch.setattr(squall_api, 'current_detection', lambda readings, buoys, model: [])
    monkeypatch.setattr(
        squall_api,
        'event_detection_summary',
        lambda model, detections: {'threshold': 0.5, 'detections': [], 'top_features': [], 'evaluation': {}},
    )

    with TestClient(app) as client:
        response = client.get('/api/public/squall')

    body = response.json()
    assert body['level'] == 'clear'
    assert body['return_now'] is False
    assert body['status_reason'] is None


def test_insufficient_live_array_is_unknown_and_never_return_now(monkeypatch):
    """A single buoy - or a stale one - never reaches watch/return_now, and
    the model is never even loaded: the gate runs before any detection
    (docs/39 Phase 2/3). The model is made to raise if it is ever reached,
    so this fails loudly if the gate stops short-circuiting."""
    stale_at = datetime.now(UTC) - timedelta(hours=6)
    pool = _FakeSquallPool([{'buoy_id': 'B01', 'observed_at': stale_at, 'pressure_hpa': 1005.0}])
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)

    def _must_not_be_called():
        raise AssertionError('the model must not run on an insufficient array')

    monkeypatch.setattr(squall_api, 'load_bundle', lambda: _must_not_be_called())

    with TestClient(app) as client:
        response = client.get('/api/public/squall')

    body = response.json()
    assert body['level'] == 'unknown'
    assert body['return_now'] is False
    assert body['status_reason']
    assert body['source'] == 'live'


def test_return_now_flag_cannot_bypass_the_quality_gate(monkeypatch):
    """docs/39 Phase 4 test requirement: the release flag can enable
    return_now only for fresh, quality-passing input - it is not a general
    override. A single stale reading stays unknown even with the flag on,
    and the model is never loaded."""
    monkeypatch.setenv('SQUALL_RETURN_NOW_ENABLED', 'true')
    stale_at = datetime.now(UTC) - timedelta(hours=6)
    pool = _FakeSquallPool([{'buoy_id': 'B01', 'observed_at': stale_at, 'pressure_hpa': 1005.0}])
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)

    def _must_not_be_called():
        raise AssertionError('the model must not run on an insufficient array, flag or no flag')

    monkeypatch.setattr(squall_api, 'load_bundle', lambda: _must_not_be_called())

    with TestClient(app) as client:
        response = client.get('/api/public/squall')

    body = response.json()
    assert body['level'] == 'unknown'
    assert body['return_now'] is False


def test_synthetic_only_data_is_invisible_to_the_public_live_route(monkeypatch):
    """The exact bug docs/39's findings section opens with: production must
    never see synthetic rows, no matter how fresh and complete they are."""
    now = datetime.now(UTC)
    pool = _FakeSquallPool(_quality_readings(['B01', 'B02', 'B03', 'B04'], now), is_synthetic=True)
    monkeypatch.setattr(public_api, 'get_pool', lambda: pool)

    with TestClient(app) as client:
        response = client.get('/api/public/squall')

    body = response.json()
    assert body['level'] == 'unknown'
    assert body['source'] == 'live'
    assert body['observed_at'] is None


def test_dashboard_squall_route_requires_a_bearer_token():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/ai/squall/current')
    assert response.status_code == 401


def test_demo_squall_status_may_reach_return_now_unconditionally(monkeypatch):
    """The demo route (app/api/demo.py) is structurally safe to leave
    ungated: it is demo-key-only and the real handset never calls it, so
    SQUALL_RETURN_NOW_ENABLED must not affect it (docs/39 Phase 3)."""
    monkeypatch.delenv('SQUALL_RETURN_NOW_ENABLED', raising=False)
    now = datetime.now(UTC)
    _mock_threshold_crossing_detection(monkeypatch)

    status = squall_api.build_squall_status(
        _quality_readings(['B01', 'B02', 'B03', 'B04'], now),
        _buoy_rows(),
        source='synthetic',
        allow_return_now=True,
    )

    assert status['level'] == 'return_now'
    assert status['source'] == 'synthetic'


def test_build_squall_status_exposes_onset_at_for_watch_and_return_now(monkeypatch):
    now = datetime.now(UTC)
    onset_iso = '2026-09-23T12:00:00+00:00'
    monkeypatch.setattr(squall_api, 'load_bundle', lambda: object())
    monkeypatch.setattr(
        squall_api,
        'current_detection',
        lambda readings, buoys, model: [
            {
                'probability': 0.9,
                'arrival_by_buoy': [{'buoy_id': 'B01', 'arrival_minutes': 12}],
                'propagation': {'onset_anchor': onset_iso},
            }
        ],
    )
    monkeypatch.setattr(
        squall_api,
        'event_detection_summary',
        lambda model, detections: {
            'threshold': 0.5,
            'detections': detections,
            'top_features': [],
            'evaluation': {},
        },
    )

    status = squall_api.build_squall_status(
        _quality_readings(['B01', 'B02', 'B03', 'B04'], now),
        _buoy_rows(),
        source='synthetic',
        allow_return_now=True,
    )
    assert status['level'] == 'return_now'
    assert status['onset_at'] == onset_iso

    unknown_status = squall_api.build_squall_status([], _buoy_rows(), source='live', allow_return_now=False)
    assert unknown_status['level'] == 'unknown'
    assert unknown_status['onset_at'] is None



def test_a_buoy_without_a_position_does_not_take_down_the_nowcast():
    """Old SOS ingest auto-registered buoys with no lat/lon; production then
    answered GET /api/public/squall with a 500 (float(None) in build_buoys)."""
    now = datetime.now(UTC)
    rows = [*_buoy_rows(), {'id': 'NOPOS', 'lat': None, 'lon': None, 'contact_radius_m': None}]
    readings = _quality_readings(['B01', 'B02', 'B03', 'B04', 'NOPOS'], now)

    assert 'NOPOS' not in build_buoys(rows)
    status = squall_api.build_squall_status(readings, rows, source='live', allow_return_now=False)

    assert status['level'] in {'unknown', 'clear', 'watch', 'return_now'}
    assert 'NOPOS' not in status['triggered_buoys']
