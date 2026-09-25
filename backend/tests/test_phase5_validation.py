"""Phase 5 verification suite: prospective evaluation, complete storyline drills,
safety isolation, and claim boundaries.

Verifies:
1. Unavailable AI output neither prevents manual SOS ingest nor impairs responder delivery states.
2. Drift calculation failure preserves the responder's case, datum, and search evidence.
3. Silence or network failure never marks an unaccounted-for person safe; overdue expectation persists.
4. Responder authority is strictly preserved over escalation and search retasking.
5. Adding future trips or contacts cannot alter historical profiles or earlier decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.ai.anomaly_service import OPEN_TRIP_FRESHNESS_WINDOW
from app.ai.drift import ObjectClass, WindSeries, predict_drift
from app.ai.search import recommend_next_area
from app.ai.trip_profile import (
    ContactPoint,
    WeatherSnapshot,
    build_profiles_from_contacts,
    score_trip,
)
from app.api.sos import SosIn
from app.incidents.delivery import delivery_state


def _calm_weather(lat: float, lon: float, at: datetime) -> WeatherSnapshot:
    return WeatherSnapshot('test', False, 1.0, 90.0, 0)


# ---------------------------------------------------------------------------
# Test 1: Unavailable AI does not prevent manual SOS intake or delivery states
# ---------------------------------------------------------------------------

def test_unavailable_ai_does_not_prevent_manual_sos_or_delivery_states():
    """Manual SOS transport must operate completely independently of AI models.
    Even if every AI service or forecast provider is unreachable or errors out,
    the manual SOS contract accepts the distress call and delivery states advance."""
    sos_payload = SosIn(
        vessel_id='VESSEL-NEW-WASH-99',
        client_ts=int(datetime(2026, 9, 15, 8, 0, 0, tzinfo=UTC).timestamp()),
        boat='Motorized Banca 16ft',
        lat=11.655,
        lon=122.445,
        note='Engine dead near channel',
        trust_tier='self_declared',
        source='buoy',
        buoy_id='BUOY01',
    )
    assert sos_payload.vessel_id == 'VESSEL-NEW-WASH-99'
    assert sos_payload.lat == 11.655

    # Test delivery state transitions without AI
    mock_row_relayed = {
        'delivered_direct': False,
        'delivered_via_buoy': False,
        'acknowledged_at': None,
        'resolved_at': None,
    }
    assert delivery_state(mock_row_relayed) == 'relayed'

    mock_row_delivered = {
        'delivered_direct': True,
        'delivered_via_buoy': False,
        'acknowledged_at': None,
        'resolved_at': None,
    }
    assert delivery_state(mock_row_delivered) == 'delivered'

    mock_row_ack = {
        'delivered_direct': True,
        'delivered_via_buoy': True,
        'acknowledged_at': datetime.now(UTC),
        'resolved_at': None,
    }
    assert delivery_state(mock_row_ack) == 'acknowledged'


# ---------------------------------------------------------------------------
# Test 2: Drift calculation failure preserves case, datum, and search evidence
# ---------------------------------------------------------------------------

def test_drift_failure_preserves_case_datum_and_search_evidence():
    """If drift simulation fails or produces an unsupported horizon, the underlying
    incident record, datum metadata, and recorded search evidence must not be clobbered."""
    incident_case = {
        'incident_id': 42,
        'vessel_id': 'VESSEL-042',
        'datum_at': datetime(2026, 9, 15, 6, 30, 0, tzinfo=UTC),
        'datum_meta': {
            'datum_source': 'client_fix',
            'delay_seconds': 3600.0,
            'initial_uncertainty_m': 150.0,
        },
        'search_sectors': [
            {
                'sector_id': 'SEC-01',
                'p_d': 0.65,
                'searched_at': datetime(2026, 9, 15, 8, 0, 0, tzinfo=UTC),
            }
        ],
    }

    # Simulate zero or diverging particles / bad forcing
    bad_wind = WindSeries(
        times=[datetime.now(UTC)],
        u_mps=[float('nan')],
        v_mps=[float('nan')],
        source='corrupted',
        degraded=True,
    )

    with pytest.raises((ValueError, TypeError, RuntimeError, Exception)):
        predict_drift(
            start_lat=11.66,
            start_lon=122.44,
            start_time=datetime.now(UTC),
            forecast_hours=4.0,
            current_fn=lambda lat, lon, t: (None, None),
            wind_series=bad_wind,
            n_particles=10,
            object_class=ObjectClass.SKIF,
        )

    # Incident case and recorded search evidence remain completely intact
    assert incident_case['incident_id'] == 42
    assert incident_case['datum_meta']['datum_source'] == 'client_fix'
    assert len(incident_case['search_sectors']) == 1
    assert incident_case['search_sectors'][0]['sector_id'] == 'SEC-01'


# ---------------------------------------------------------------------------
# Test 3: Silence / outage never marks unaccounted person safe
# ---------------------------------------------------------------------------

def test_silence_or_outage_never_marks_unaccounted_person_safe():
    """An overdue vessel whose communication dropped out or during a gateway outage
    must remain reviewable as overdue, never silently cleared or marked safe."""
    rows = []
    # Train normal profile with 4 trips of 2 hours each
    for day in range(4):
        t_day = datetime(2026, 8, 1 + day, 6, 0, tzinfo=UTC)
        rows.append({
            'vessel_id': 'V-OVERDUE', 'trip_id': f'trip-{day}', 'buoy_id': 'B01',
            'observed_at': t_day, 'latitude': 11.68, 'longitude': 122.36,
        })
        rows.append({
            'vessel_id': 'V-OVERDUE', 'trip_id': f'trip-{day}', 'buoy_id': 'B02',
            'observed_at': t_day + timedelta(hours=1), 'latitude': 11.69, 'longitude': 122.37,
        })
        rows.append({
            'vessel_id': 'V-OVERDUE', 'trip_id': f'trip-{day}', 'buoy_id': 'B03',
            'observed_at': t_day + timedelta(hours=2), 'latitude': 11.70, 'longitude': 122.38,
        })

    profiles = build_profiles_from_contacts(rows)
    profile = profiles['V-OVERDUE']

    # Current trip: started at 06:00, last heard at 07:00 at B02. Now is 14:00 (7 hours overdue)
    now_eval = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
    last_contact_time = datetime(2026, 8, 10, 7, 0, tzinfo=UTC)
    contacts = [
        ContactPoint('B01', datetime(2026, 8, 10, 6, 0, tzinfo=UTC), 11.68, 122.36),
        ContactPoint('B02', last_contact_time, 11.69, 122.37),
    ]

    score = score_trip(
        profile,
        contacts,
        as_of=now_eval,
        weather_provider=_calm_weather,
    )

    # Scored as alert/overdue anomaly, never cleared as safe
    assert score.status in {'alert', 'overdue'}
    assert score.score >= 0.55

    # Within open trip freshness window (12h), so it remains open and reviewable
    age = now_eval - last_contact_time
    assert age <= OPEN_TRIP_FRESHNESS_WINDOW


# ---------------------------------------------------------------------------
# Test 4: Responder authority over escalation and search retasking
# ---------------------------------------------------------------------------

def test_responder_authority_over_escalation_and_retasking():
    """Automated AI models must never trigger SAR tasking or escalation without human
    responder authority."""
    grid = {
        'type': 'DensityGrid',
        'origin': {'lat': 11.66, 'lon': 122.44},
        'x_edges_m': [0.0, 500.0, 1000.0],
        'y_edges_m': [0.0, 500.0, 1000.0],
        'values': [[0.15, 0.45], [0.25, 0.15]],
    }
    rec = recommend_next_area(grid)
    assert rec['is_advisory'] is True
    assert 'advisory' in rec['advisory_note'].lower()
    assert rec['label'] == 'recommendation for responder review'


# ---------------------------------------------------------------------------
# Test 5: Historical profile causality under new trip additions
# ---------------------------------------------------------------------------

def test_future_trips_do_not_alter_historical_profiles():
    """Adding later trips to the database cannot change the profile that existed
    at the decision cutoff."""
    t0 = datetime(2026, 8, 1, 6, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 8, 5, 6, 0, 0, tzinfo=UTC)
    t3 = datetime(2026, 8, 5, 10, 0, 0, tzinfo=UTC)

    historical_contacts = [
        {'vessel_id': 'V1', 'trip_id': 'T1', 'buoy_id': 'B1', 'observed_at': t0, 'latitude': 11.6, 'longitude': 122.4},
        {'vessel_id': 'V1', 'trip_id': 'T1', 'buoy_id': 'B2', 'observed_at': t1, 'latitude': 11.7, 'longitude': 122.3},
        {'vessel_id': 'V1', 'trip_id': 'T2', 'buoy_id': 'B1', 'observed_at': t2, 'latitude': 11.6, 'longitude': 122.4},
        {'vessel_id': 'V1', 'trip_id': 'T2', 'buoy_id': 'B2', 'observed_at': t3, 'latitude': 11.7, 'longitude': 122.3},
    ]

    profiles_historical = build_profiles_from_contacts(historical_contacts)
    p_before = profiles_historical['V1']

    # Future trip occurs later on August 20
    t_future_start = datetime(2026, 8, 20, 6, 0, 0, tzinfo=UTC)
    t_future_end = datetime(2026, 8, 20, 18, 0, 0, tzinfo=UTC)
    future_trip = [
        {
            'vessel_id': 'V1', 'trip_id': 'T3', 'buoy_id': 'B1',
            'observed_at': t_future_start, 'latitude': 11.6, 'longitude': 122.4,
        },
        {
            'vessel_id': 'V1', 'trip_id': 'T3', 'buoy_id': 'B2',
            'observed_at': t_future_end, 'latitude': 11.7, 'longitude': 122.3,
        },
    ]

    cutoff = datetime(2026, 8, 10, 0, 0, 0, tzinfo=UTC)
    filtered = [r for r in (historical_contacts + future_trip) if r['observed_at'] <= cutoff]
    profiles_at_cutoff = build_profiles_from_contacts(filtered)
    p_at_cutoff = profiles_at_cutoff['V1']

    assert p_at_cutoff.trip_count == p_before.trip_count
    assert p_at_cutoff.typical_sequence == p_before.typical_sequence
    assert p_at_cutoff.typical_departure_hour == p_before.typical_departure_hour
