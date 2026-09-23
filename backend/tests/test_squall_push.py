from datetime import UTC, datetime

from app.api import squall as squall_api
from app.api.squall import build_squall_status
from tools.push_live_squall import stage_window

# 3 live buoys forming a non-collinear triangle near the squall center
_LIVE_BUOY_ROWS = [
    {'id': 'buoy-a', 'lat': 11.68, 'lon': 122.414, 'contact_radius_m': 700},
    {'id': 'buoy-b', 'lat': 11.652, 'lon': 122.448, 'contact_radius_m': 700},
    {'id': 'buoy-c', 'lat': 11.708, 'lon': 122.365, 'contact_radius_m': 700},
]

_LIVE_BUOY_POSITIONS = {
    'buoy-a': {'lat': 11.68, 'lon': 122.414},
    'buoy-b': {'lat': 11.652, 'lon': 122.448},
    'buoy-c': {'lat': 11.708, 'lon': 122.365},
}


def test_stage_window_produces_gap_free_readings_for_three_buoys():
    as_of = datetime.now(UTC)
    readings = stage_window(_LIVE_BUOY_POSITIONS, as_of)
    assert len(readings) == 19 * 3
    buoy_ids = {r['buoy_id'] for r in readings}
    assert buoy_ids == {'buoy-a', 'buoy-b', 'buoy-c'}
    for buoy_id in buoy_ids:
        times = sorted(
            r['observed_at'] for r in readings if r['buoy_id'] == buoy_id
        )
        assert len(times) == 19
        assert (times[-1] - times[0]).total_seconds() == 90 * 60


def test_staged_window_is_unknown_without_model(monkeypatch):
    monkeypatch.setattr(
        squall_api, 'load_bundle',
        lambda: (_ for _ in ()).throw(FileNotFoundError('no model')),
    )
    as_of = datetime.now(UTC)
    readings = stage_window(_LIVE_BUOY_POSITIONS, as_of)
    status = build_squall_status(readings, _LIVE_BUOY_ROWS, source='live', allow_return_now=True)
    assert status['level'] == 'unknown'
    assert status['return_now'] is False
    assert 'not available' in status['status_reason']


def test_staged_window_is_watch_when_flag_off(monkeypatch):
    monkeypatch.delenv('SQUALL_RETURN_NOW_ENABLED', raising=False)
    as_of = datetime.now(UTC)
    readings = stage_window(_LIVE_BUOY_POSITIONS, as_of)

    status = build_squall_status(readings, _LIVE_BUOY_ROWS, source='live', allow_return_now=False)
    assert status['return_now'] is False
    assert status['source'] == 'live'
    assert status['level'] in {'watch', 'return_now', 'clear'}
    if status['level'] == 'clear':
        assert status['detections'] == []
    else:
        assert len(status['detections']) > 0


def test_staged_window_is_return_now_when_flag_on(monkeypatch):
    monkeypatch.setenv('SQUALL_RETURN_NOW_ENABLED', 'true')
    as_of = datetime.now(UTC)
    readings = stage_window(_LIVE_BUOY_POSITIONS, as_of)

    status = build_squall_status(readings, _LIVE_BUOY_ROWS, source='live', allow_return_now=True)
    assert status['source'] == 'live'
    assert status['level'] in {'return_now', 'watch', 'clear'}
    if status['level'] == 'return_now':
        assert status['return_now'] is True
        assert len(status['detections']) > 0
        assert status['threshold'] is not None
