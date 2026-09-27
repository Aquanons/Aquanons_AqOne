from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.api import public

# docs/72: the buoy map must show where a buoy really is, or nothing at all.

NOW = datetime(2026, 9, 27, 8, 0, tzinfo=UTC)


def _row(**overrides):
    row = {
        'id': 'B01',
        'label': 'Buoy 01',
        'lat': 11.671,
        'lon': 122.466,
        'contact_radius_m': 1340,
        'lora_radius_m': 7023,
        'is_gateway_linked': True,
        'is_synthetic': True,
        'last_heard_at': NOW - timedelta(minutes=5),
    }
    row.update(overrides)
    return row


def test_a_buoy_is_placed_at_its_recorded_position() -> None:
    marker = public.buoy_marker(_row(), NOW)
    assert (marker['latitude'], marker['longitude']) == (11.671, 122.466)
    assert marker['coverage_radius_meters'] == 1340
    assert marker['lora_radius_meters'] == 7023
    assert marker['is_gateway_linked'] is True
    assert marker['is_synthetic'] is True
    assert marker['last_heard_at'] == '2026-09-27T07:55:00+00:00'
    assert marker['status'] == 'active'


def test_a_buoy_without_a_position_is_not_placed_anywhere() -> None:
    marker = public.buoy_marker(_row(lat=None, lon=None, contact_radius_m=None), NOW)
    assert marker['latitude'] is None
    assert marker['longitude'] is None
    assert marker['coverage_radius_meters'] is None


def test_status_follows_when_the_buoy_was_last_heard() -> None:
    assert public.buoy_marker(_row(last_heard_at=NOW - timedelta(minutes=59)), NOW)['status'] == 'active'
    assert public.buoy_marker(_row(last_heard_at=NOW - timedelta(minutes=61)), NOW)['status'] == 'silent'
    assert public.buoy_marker(_row(last_heard_at=None), NOW)['status'] == 'unknown'


def test_there_is_no_invented_buoy_mesh() -> None:
    assert not hasattr(public, 'DEMO_BUOYS')
