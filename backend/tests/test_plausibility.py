from datetime import UTC, datetime, timedelta

from app.incidents.plausibility import PlausibilityContext, flags

NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


def _event(**overrides):
    event = {
        'latitude': 11.65,
        'longitude': 122.5,
        'delivered_direct': True,
        'delivered_via_buoy': False,
        'open_calls_for_vessel': 1,
        'alt_latitude': None,
        'alt_longitude': None,
    }
    event.update(overrides)
    return event


def test_flags_position_on_land():
    assert 'position_on_land' in flags(_event(latitude=11.6473, longitude=122.42), PlausibilityContext())


def test_flags_buoy_position_beyond_radio_range():
    event = _event(latitude=11.6473, longitude=122.52, delivered_direct=False, delivered_via_buoy=True)
    context = PlausibilityContext(gateway_latitude=11.6473, gateway_longitude=122.42, max_range_km=7.5)
    assert 'position_beyond_radio_range' in flags(event, context)


def test_flags_position_jump_from_recent_contact():
    event = _event(latitude=11.6, longitude=122.7)
    context = PlausibilityContext(
        contact_at=NOW - timedelta(minutes=30), contact_latitude=11.6, contact_longitude=122.45,
        now=NOW,
    )
    assert 'position_jump' in flags(event, context)


def test_flags_three_open_calls_for_one_vessel():
    context = PlausibilityContext(open_calls_for_vessel=3)
    assert 'many_calls_same_vessel' in flags(_event(), context)


def test_many_calls_flag_at_two_open_calls():
    assert 'many_calls_same_vessel' in flags(_event(), PlausibilityContext(open_calls_for_vessel=2))
    assert 'many_calls_same_vessel' not in flags(_event(), PlausibilityContext(open_calls_for_vessel=1))


def test_flags_alternative_position_conflict():
    assert 'position_conflict' in flags(_event(alt_latitude=11.66, alt_longitude=122.51), PlausibilityContext())


def test_normal_event_has_no_flags():
    assert flags(_event(), PlausibilityContext()) == []


def test_direct_path_never_gets_radio_range_flag():
    event = _event(latitude=11.6473, longitude=122.52, delivered_direct=True, delivered_via_buoy=True)
    context = PlausibilityContext(gateway_latitude=11.6473, gateway_longitude=122.42, max_range_km=1)
    assert 'position_beyond_radio_range' not in flags(event, context)
