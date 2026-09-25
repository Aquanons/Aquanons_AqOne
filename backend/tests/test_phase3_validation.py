import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.ai.anomaly_service import eligible_latest_trips
from app.ai.squall import (
    BuoyMeta,
    PropagationEstimate,
    SquallFeatureBundle,
    _arrival_projection,
    build_buoys,
)
from app.ai.trip_profile import (
    ContactPoint,
    VesselProfile,
    _sequence_deviation,
    build_profiles_from_contacts,
    score_trip,
)


def _sample_buoys() -> dict[str, BuoyMeta]:
    return build_buoys([
        {'id': 'B01', 'lat': 11.6892, 'lon': 122.3667, 'contact_radius_m': 900},
        {'id': 'B02', 'lat': 11.6992, 'lon': 122.4667, 'contact_radius_m': 900},
        {'id': 'B03', 'lat': 11.7192, 'lon': 122.5667, 'contact_radius_m': 900},
        {'id': 'B04', 'lat': 11.7292, 'lon': 122.6667, 'contact_radius_m': 900},
    ])


def _base_bundle(prop: PropagationEstimate, as_of: datetime) -> SquallFeatureBundle:
    return SquallFeatureBundle(
        as_of=as_of,
        feature_names=[],
        values=[],
        buoy_rows=[],
        propagation=prop,
        array_mean_pressure=1010.0,
        array_mean_trace=[],
        pressure_trace={},
    )


def test_coordinate_origin_invariance_in_arrival_projection():
    """Verification Gate: Demonstrate that changing the coordinate origin
    consistently preserves predicted absolute arrival time.
    """
    buoys = _sample_buoys()
    as_of = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)
    anchor = as_of - timedelta(minutes=30)

    prop1 = PropagationEstimate(
        bearing_deg=90.0,
        speed_mps=15.0,
        r2=0.95,
        residual_minutes=1.2,
        onset_coverage=1.0,
        onset_span_minutes=30.0,
        origin_lat=11.6892,
        origin_lon=122.3667,
        onset_anchor=anchor,
        geometry_degenerate=False,
        fit_intercept_minutes=0.0,
    )
    bundle1 = _base_bundle(prop1, as_of)
    arr1 = _arrival_projection(bundle1, buoys)
    assert len(arr1) == 4

    slope = 1.0 / (15.0 * 60.0)
    delta_north_m = 5000.0
    delta_east_m = 8000.0
    d_along = delta_east_m * math.sin(math.radians(90.0)) + delta_north_m * math.cos(math.radians(90.0))
    shifted_intercept = 0.0 + slope * d_along

    shifted_lat = 11.6892 + (delta_north_m / 110574.0)
    shifted_lon = 122.3667 + (delta_east_m / (111320.0 * math.cos(math.radians(11.6892))))

    prop2 = replace(
        prop1,
        origin_lat=shifted_lat,
        origin_lon=shifted_lon,
        fit_intercept_minutes=shifted_intercept,
    )
    bundle2 = replace(bundle1, propagation=prop2)
    arr2 = _arrival_projection(bundle2, buoys)

    for item1, item2 in zip(arr1, arr2, strict=True):
        assert item1['buoy_id'] == item2['buoy_id']
        t1 = datetime.fromisoformat(item1['arrival_at'])
        t2 = datetime.fromisoformat(item2['arrival_at'])
        assert abs((t1 - t2).total_seconds()) < 1.0
        assert math.isclose(item1['arrival_minutes'], item2['arrival_minutes'], abs_tol=0.1)


def test_timestamp_shift_invariance_in_arrival_projection():
    """Verification Gate: Demonstrate that shifting all observation and decision
    timestamps by a common interval shifts predicted arrival timestamps by that same interval.
    """
    buoys = _sample_buoys()
    as_of = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)
    anchor = as_of - timedelta(minutes=25)

    delta = timedelta(hours=3, minutes=15)

    prop = PropagationEstimate(
        bearing_deg=85.0,
        speed_mps=12.0,
        r2=0.92,
        residual_minutes=2.0,
        onset_coverage=1.0,
        onset_span_minutes=25.0,
        origin_lat=11.6892,
        origin_lon=122.3667,
        onset_anchor=anchor,
        geometry_degenerate=False,
        fit_intercept_minutes=1.5,
    )
    bundle = _base_bundle(prop, as_of)
    arr_orig = _arrival_projection(bundle, buoys)

    prop_shifted = replace(prop, onset_anchor=anchor + delta)
    bundle_shifted = replace(bundle, as_of=as_of + delta, propagation=prop_shifted)
    arr_shifted = _arrival_projection(bundle_shifted, buoys)

    for item_orig, item_sh in zip(arr_orig, arr_shifted, strict=True):
        t_orig = datetime.fromisoformat(item_orig['arrival_at'])
        t_sh = datetime.fromisoformat(item_sh['arrival_at'])
        assert abs(((t_orig + delta) - t_sh).total_seconds()) < 1.0
        assert math.isclose(item_orig['arrival_minutes'], item_sh['arrival_minutes'], abs_tol=0.1)


def test_poorly_constrained_or_degenerate_front_rejected():
    """Task 3.3: Reject poorly constrained fronts or geometry unsupported by the array."""
    buoys = _sample_buoys()
    as_of = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)

    prop_base = PropagationEstimate(
        bearing_deg=90.0, speed_mps=10.0, r2=0.95, residual_minutes=1.0,
        onset_coverage=1.0, onset_span_minutes=15.0, origin_lat=11.6892,
        origin_lon=122.3667, onset_anchor=as_of, geometry_degenerate=False,
    )

    bundle_degen = _base_bundle(
        replace(
            prop_base,
            r2=0.0,
            residual_minutes=999.0,
            onset_coverage=0.5,
            onset_span_minutes=10.0,
            geometry_degenerate=True,
        ),
        as_of=as_of,
    )
    assert _arrival_projection(bundle_degen, buoys) == []

    bundle_low_r2 = _base_bundle(
        replace(prop_base, r2=0.12, residual_minutes=15.0, onset_coverage=0.8),
        as_of=as_of,
    )
    assert _arrival_projection(bundle_low_r2, buoys) == []


def test_profile_leakage_prevention():
    """Verification Gate: Demonstrate that adding the candidate trip or future contacts
    to storage cannot change its historical baseline or historical decision.
    """
    as_of = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)

    def _row(t_id: str, b_id: str, ts: datetime, lat: float, lon: float) -> dict[str, object]:
        return {
            'vessel_id': 'V-LEAK',
            'trip_id': t_id,
            'buoy_id': b_id,
            'observed_at': ts,
            'latitude': lat,
            'longitude': lon,
        }

    historical_rows = [
        _row('T-01', 'B01', datetime(2026, 9, 10, 6, 0, tzinfo=UTC), 11.68, 122.36),
        _row('T-01', 'B02', datetime(2026, 9, 10, 7, 0, tzinfo=UTC), 11.69, 122.46),
        _row('T-02', 'B01', datetime(2026, 9, 11, 6, 0, tzinfo=UTC), 11.68, 122.36),
        _row('T-02', 'B02', datetime(2026, 9, 11, 7, 0, tzinfo=UTC), 11.69, 122.46),
        _row('T-03', 'B01', datetime(2026, 9, 12, 6, 0, tzinfo=UTC), 11.68, 122.36),
        _row('T-03', 'B02', datetime(2026, 9, 12, 7, 0, tzinfo=UTC), 11.69, 122.46),
    ]

    profile_clean = build_profiles_from_contacts(
        historical_rows, as_of=as_of, exclude_trip_ids={'T-CANDIDATE'}
    )['V-LEAK']

    polluted_rows = list(historical_rows) + [
        _row('T-CANDIDATE', 'B01', datetime(2026, 9, 15, 6, 0, tzinfo=UTC), 11.68, 122.36),
        _row('T-CANDIDATE', 'B04', datetime(2026, 9, 15, 7, 0, tzinfo=UTC), 11.72, 122.66),
        _row('T-FUTURE', 'B03', datetime(2026, 9, 16, 6, 0, tzinfo=UTC), 11.71, 122.56),
    ]

    profile_guarded = build_profiles_from_contacts(
        polluted_rows, as_of=as_of, exclude_trip_ids={'T-CANDIDATE'}
    )['V-LEAK']

    assert profile_clean.trip_count == profile_guarded.trip_count == 3
    assert profile_clean.typical_sequence == profile_guarded.typical_sequence == ['B01', 'B02']
    assert profile_clean.typical_departure_hour == profile_guarded.typical_departure_hour
    assert profile_clean.interval_stats == profile_guarded.interval_stats


def test_unfinished_normal_prefix_not_penalized_as_anomalous():
    """Task 3.6: Do not score an unfinished normal prefix as a completed anomalous route."""
    profile = VesselProfile(
        vessel_id='V-PREFIX',
        trip_count=5,
        low_confidence=False,
        typical_departure_hour=6.0,
        departure_hour_std=0.5,
        typical_sequence=['B01', 'B02', 'B03', 'B04'],
        interval_stats=[],
        typical_trip_duration_minutes={'mean': 180.0, 'std': 20.0, 'p10': 150.0, 'p90': 210.0},
        typical_max_distance_km={'mean': 25.0, 'std': 3.0, 'p10': 20.0, 'p90': 30.0},
        rebuilt_at=datetime.now(UTC).isoformat(),
    )

    normal_prefix = ['B01', 'B02']
    assert _sequence_deviation(profile, normal_prefix) == 0.0

    diverged = ['B01', 'B04']
    assert _sequence_deviation(profile, diverged) > 0.0


def test_open_trips_persist_beyond_12_hours():
    """Verification Gate: Demonstrate open trips persist beyond 12 hours."""
    as_of = datetime(2026, 9, 15, 22, 0, tzinfo=UTC)
    old_contact = as_of - timedelta(hours=16)

    def _contact(v_id: str, t_id: str) -> dict[str, object]:
        return {
            'vessel_id': v_id,
            'trip_id': t_id,
            'buoy_id': 'B01',
            'observed_at': old_contact,
            'latitude': 11.68,
            'longitude': 122.36,
        }

    rows = [
        _contact('V-1', 'TRIP-OPEN'),
        _contact('V-2', 'TRIP-COMPLETED'),
        _contact('V-3', 'TRIP-LEGACY'),
    ]
    trip_states = {
        'TRIP-OPEN': {
            'status': 'open',
            'welfare_status': 'unknown',
            'expected_return_at': as_of - timedelta(hours=2),
        },
        'TRIP-COMPLETED': {'status': 'completed', 'welfare_status': 'normal'},
    }

    eligible = eligible_latest_trips(rows, as_of=as_of, trip_states=trip_states)
    eligible_ids = {trip_id for _, trip_id, _ in eligible}

    assert 'TRIP-OPEN' in eligible_ids
    assert 'TRIP-COMPLETED' not in eligible_ids
    assert 'TRIP-LEGACY' not in eligible_ids


def test_delayed_return_amendment_prevents_premature_overdue_alert():
    """Verification Gate: Delayed return applies to the correct trip."""
    as_of = datetime(2026, 9, 15, 14, 0, tzinfo=UTC)
    contacts = [
        ContactPoint('B01', as_of - timedelta(hours=5), 11.6892, 122.3667),
        ContactPoint('B02', as_of - timedelta(hours=4), 11.6992, 122.4667),
    ]
    profile = VesselProfile(
        vessel_id='V-RET', trip_count=5, low_confidence=False,
        typical_departure_hour=9.0, departure_hour_std=0.5,
        typical_sequence=['B01', 'B02', 'B03'], interval_stats=[],
        typical_trip_duration_minutes={'mean': 180.0, 'std': 20.0, 'p10': 150.0, 'p90': 210.0},
        typical_max_distance_km={'mean': 25.0, 'std': 3.0, 'p10': 20.0, 'p90': 30.0},
        rebuilt_at=as_of.isoformat(),
    )

    state_overdue = {
        'status': 'open',
        'expected_return_at': as_of - timedelta(hours=1),
        'welfare_status': 'unknown',
    }
    score_overdue = score_trip(profile, contacts, as_of=as_of, trip_state=state_overdue)
    assert score_overdue.status in {'overdue', 'alert'}
    assert any('expected return deadline' in f.explanation for f in score_overdue.factors)

    state_amended = {
        'status': 'open',
        'expected_return_at': as_of + timedelta(hours=3),
        'welfare_status': 'safe',
        'welfare_updated_at': as_of - timedelta(hours=1),
    }
    score_amended = score_trip(profile, contacts, as_of=as_of, trip_state=state_amended)
    assert score_amended.status == 'normal'
    assert any('self-reported safe' in f.explanation for f in score_amended.factors)
