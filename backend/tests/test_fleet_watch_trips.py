"""Plan 69 Phase 2, trip decision (docs/fleet-watch/PHASE_2_PLAN.md T2-35, T2-36; spec 68 REQ-016, D11)."""

from datetime import UTC, datetime

import pytest

from app.fleet_watch.trips import OpenTrip, TripAction, auto_trip_id, trip_action
from app.fleet_watch.watch import Checkin

T0 = datetime(2026, 9, 21, 14, 13, 20, tzinfo=UTC)
SEA = (11.65, 122.50)
HARBOR = (11.55, 122.40)


def at_sea(lat, lon):
    return lat > 11.60


def checkin(where):
    lat, lon = where if where is not None else (None, None)
    return Checkin(observed_at=T0, latitude=lat, longitude=lon, path='direct', fix_age_s=10 if where else None)


GATEWAY_TRIP = OpenTrip(trip_id='auto-NW-001-1789990000', reporter_type='gateway')
HANDSET_TRIP = OpenTrip(trip_id='trip-2026-09-21-01', reporter_type='handset')


@pytest.mark.parametrize(
    ('where', 'open_trip', 'expected'),
    [
        (SEA, None, TripAction(kind='open', trip_id='auto-NW-001-1790000000')),
        (SEA, GATEWAY_TRIP, TripAction(kind='attach', trip_id=GATEWAY_TRIP.trip_id)),
        (SEA, HANDSET_TRIP, TripAction(kind='attach', trip_id=HANDSET_TRIP.trip_id)),
        (HARBOR, GATEWAY_TRIP, TripAction(kind='complete', trip_id=GATEWAY_TRIP.trip_id)),
        (HARBOR, HANDSET_TRIP, TripAction(kind='attach', trip_id=HANDSET_TRIP.trip_id)),
        (HARBOR, None, TripAction(kind='none', trip_id=None)),
        (None, GATEWAY_TRIP, TripAction(kind='attach', trip_id=GATEWAY_TRIP.trip_id)),
        (None, None, TripAction(kind='none', trip_id=None)),
    ],
    ids=[
        'sea-no-trip-opens',
        'sea-gateway-trip-attaches',
        'sea-handset-trip-attaches',
        'harbor-gateway-trip-completes',
        'harbor-handset-trip-never-completes',
        'harbor-no-trip-stores-without-trip',
        'no-fix-open-trip-attaches',
        'no-fix-no-trip-stores-without-trip',
    ],
)
def test_t2_35_what_a_check_in_does_to_a_trip(where, open_trip, expected):
    assert trip_action('NW-001', checkin(where), open_trip, at_sea) == expected


def test_t2_36_auto_trip_id_matches_the_ingest_contract():
    assert auto_trip_id('NW-001', T0) == 'auto-NW-001-1790000000'
