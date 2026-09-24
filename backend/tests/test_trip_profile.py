from datetime import UTC, datetime, timedelta

from app.ai.trip_profile import (
    MANILA_TZ,
    ContactPoint,
    WeatherSnapshot,
    build_profiles_from_contacts,
    score_trip,
)


def _rows_for_trip(vessel_id: str, trip_id: str, start: datetime, route: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, buoy_id in enumerate(route):
        rows.append(
            {
                'vessel_id': vessel_id,
                'trip_id': trip_id,
                'buoy_id': buoy_id,
                'observed_at': start + timedelta(minutes=45 * index),
                'latitude': 11.6892 + index * 0.01,
                'longitude': 122.3667 + index * 0.01,
            }
        )
    return rows


def _calm_weather(lat: float, lon: float, at: datetime) -> WeatherSnapshot:
    return WeatherSnapshot('test', False, 1.0, 90.0, 0)


def test_profile_builder_uses_fleet_fallback_for_cold_start():
    rows = []
    rows.extend(_rows_for_trip('V-001', 'trip-1', datetime(2026, 8, 1, 6, tzinfo=UTC), ['B01', 'B02', 'B03']))
    rows.extend(_rows_for_trip('V-001', 'trip-2', datetime(2026, 8, 2, 6, tzinfo=UTC), ['B01', 'B02', 'B03']))
    profiles = build_profiles_from_contacts(rows)

    assert profiles['V-001'].low_confidence is True
    assert profiles['V-001'].typical_sequence == ['B01', 'B02', 'B03']


def test_overdue_vessel_scores_high():
    rows = []
    for day in range(4):
        trip_day = datetime(2026, 8, 1 + day, 6, tzinfo=UTC)
        rows.extend(_rows_for_trip('V-002', f'trip-{day + 1}', trip_day, ['B01', 'B02', 'B03']))
    profiles = build_profiles_from_contacts(rows)
    profile = profiles['V-002']
    contacts = [
        ContactPoint('B01', datetime(2026, 8, 10, 6, tzinfo=UTC), 11.6892, 122.3667),
        ContactPoint('B02', datetime(2026, 8, 10, 6, 45, tzinfo=UTC), 11.6992, 122.3767),
    ]

    score = score_trip(
        profile,
        contacts,
        as_of=contacts[-1].observed_at + timedelta(hours=4),
        weather_provider=_calm_weather,
    )

    assert score.status == 'alert'
    assert score.score >= 0.85


def test_normal_vessel_scores_low():
    rows = []
    for day in range(4):
        trip_day = datetime(2026, 8, 1 + day, 6, tzinfo=UTC)
        rows.extend(_rows_for_trip('V-003', f'trip-{day + 1}', trip_day, ['B01', 'B02', 'B03']))
    profiles = build_profiles_from_contacts(rows)
    profile = profiles['V-003']
    contacts = [
        ContactPoint('B01', datetime(2026, 8, 10, 6, tzinfo=UTC), 11.6892, 122.3667),
        ContactPoint('B02', datetime(2026, 8, 10, 6, 45, tzinfo=UTC), 11.6992, 122.3767),
        ContactPoint('B03', datetime(2026, 8, 10, 7, 30, tzinfo=UTC), 11.7092, 122.3867),
    ]

    score = score_trip(
        profile,
        contacts,
        as_of=contacts[-1].observed_at + timedelta(minutes=5),
        weather_provider=_calm_weather,
    )

    assert score.status == 'normal'
    assert score.score < 0.25


def test_new_profile_not_damped():
    profile = build_profiles_from_contacts([])['fleet']
    contact = ContactPoint('B01', datetime(2026, 8, 10, 6, tzinfo=UTC), 11.6892, 122.3667)
    score = score_trip(
        profile, [contact], as_of=contact.observed_at + timedelta(hours=4),
        trip_state={'welfare_status': 'distress'}, weather_provider=_calm_weather,
    )
    assert score.score >= 0.85


def test_no_contact_trip_becomes_check_needed_after_fleet_p90():
    profile = build_profiles_from_contacts([])['fleet']
    profile = profile.__class__(
        **{**profile.__dict__, 'typical_trip_duration_minutes': {'mean': 150, 'std': 20, 'p10': 120, 'p90': 180}}
    )
    now = datetime(2026, 8, 10, 12, tzinfo=UTC)
    state = {
        'departure_at': now - timedelta(hours=4), 'expected_return_at': None, 'welfare_status': 'unknown',
    }
    not_yet = score_trip(
        profile, [], as_of=now, trip_state={**state, 'fleet_p90_trip_duration_minutes': 300},
    )
    assert not_yet.status == 'normal'
    score = score_trip(
        profile, [], as_of=now, trip_state=state,
    )
    assert score.status == 'check_needed'


def test_safe_checkin_caps_only_two_hours():
    rows = []
    for day in range(4):
        rows.extend(
            _rows_for_trip(
                'V-SAFE', f'history-{day}', datetime(2026, 8, day + 1, 6, tzinfo=UTC), ['B01', 'B02', 'B03']
            )
        )
    profile = build_profiles_from_contacts(rows)['V-SAFE']
    contacts = [
        ContactPoint('B01', datetime(2026, 8, 10, 6, tzinfo=UTC), 11.6892, 122.3667),
        ContactPoint('B02', datetime(2026, 8, 10, 6, 45, tzinfo=UTC), 11.6992, 122.3767),
    ]
    now = contacts[-1].observed_at + timedelta(hours=4)
    recent = score_trip(
        profile, contacts, as_of=now,
        trip_state={'welfare_status': 'safe', 'welfare_updated_at': now - timedelta(hours=1)},
        weather_provider=_calm_weather,
    )
    stale = score_trip(
        profile, contacts, as_of=now,
        trip_state={'welfare_status': 'safe', 'welfare_updated_at': now - timedelta(hours=3)},
        weather_provider=_calm_weather,
    )
    assert recent.score < stale.score


def test_departure_hour_is_circular():
    rows = []
    for trip_id, day, hour, minute in [('late', 1, 23, 30), ('early', 2, 0, 30)]:
        rows.extend(_rows_for_trip(
            'V-MIDNIGHT', trip_id, datetime(2026, 8, day, hour, minute, tzinfo=MANILA_TZ), ['B01']
        ))
    profile = build_profiles_from_contacts(rows)['V-MIDNIGHT']
    assert min(profile.typical_departure_hour, 24 - profile.typical_departure_hour) < 0.1
    assert profile.departure_hour_std < 1


def test_distance_from_home_landing():
    rows = []
    for day in range(4):
        start = datetime(2026, 8, day + 1, 6, tzinfo=UTC)
        rows.extend([
            {'vessel_id': 'V-HOME', 'trip_id': f'trip-{day}', 'buoy_id': 'B01',
             'observed_at': start, 'latitude': 11.74, 'longitude': 122.45},
            {'vessel_id': 'V-HOME', 'trip_id': f'trip-{day}', 'buoy_id': 'B02',
             'observed_at': start + timedelta(hours=1), 'latitude': 11.75, 'longitude': 122.46},
        ])
    profile = build_profiles_from_contacts(rows)['V-HOME']
    assert profile.typical_max_distance_km['mean'] < 3
