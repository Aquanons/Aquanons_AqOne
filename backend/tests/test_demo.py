import asyncio

import pytest
from fastapi import HTTPException

from app.api.demo import require_demo_key
from app.demo import scenarios
from app.demo.scenarios import DemoState
from app.demo.weather import forecast, marine


class _FakeConnection:
    def __init__(self):
        self.executed = []

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return None

    async def execute(self, query, *args):
        self.executed.append((query, args))
        table = query.split('FROM ')[1].split(' ')[0]
        return f'DELETE {1 if args else 0}' if table else 'DELETE 0'


class _FakePool:
    def __init__(self):
        self.connection = _FakeConnection()

    def acquire(self):
        return self.connection


def test_demo_routes_are_absent_when_demo_mode_is_unset(monkeypatch):
    monkeypatch.delenv('DEMO_MODE', raising=False)
    from app.main import app

    assert not any(getattr(route, 'path', '').startswith('/api/demo') for route in app.routes)


def test_demo_key_rejects_missing_and_wrong_values(monkeypatch):
    monkeypatch.setenv('DEMO_CONTROL_KEY', 'correct-key')

    with pytest.raises(HTTPException) as missing:
        asyncio.run(require_demo_key(None))
    assert missing.value.status_code == 403

    with pytest.raises(HTTPException) as wrong:
        asyncio.run(require_demo_key('wrong-key'))
    assert wrong.value.status_code == 403


def test_weather_proxy_returns_requested_cells_in_order():
    cells = [(11.70, 122.48), (11.62, 122.48), (11.76, 122.58)]

    weather = forecast(2, cells)
    waves = marine(2, cells)

    assert len(weather) == len(cells)
    assert len(waves) == len(cells)
    assert weather[0]['current']['wind_gusts_10m'] == 48.0
    assert weather[1]['current']['wind_gusts_10m'] == 22.0
    assert waves[2]['current']['wave_height'] == 2.2


def test_reset_removes_only_tagged_rows():
    pool = _FakePool()
    state = scenarios.get_state()
    state.scenario = 'clear-day'
    state.beat = 0
    state.fired = {0}
    state.run_id = 'run-1'

    deleted = asyncio.run(scenarios.reset(pool, 'run-1'))

    assert deleted['run_id'] == 'run-1'
    assert len(pool.connection.executed) == 8
    assert scenarios.get_state() == DemoState(updated_at=state.updated_at)


def test_firing_same_beat_is_idempotent(monkeypatch):
    state = scenarios.get_state()
    state.scenario = 'squall-fleet'
    state.beat = 0
    state.fired = {0}
    state.run_id = 'run-1'
    writes = []

    async def fake_write(_pool, run_id, beat, scenario):
        writes.append((run_id, beat.index, scenario))

    monkeypatch.setattr(scenarios, 'get_pool', lambda: object())
    monkeypatch.setattr(scenarios, '_write_pressure_window', fake_write)

    first = asyncio.run(scenarios.fire_beat(1))
    second = asyncio.run(scenarios.fire_beat(1))

    assert first == second
    assert writes == [('run-1', 1, 'squall-fleet')]


def test_synthetic_buoy_trace_is_behind_the_demo_key():
    # docs/72: the tutorial recording reads the scenario's pressure traces here,
    # because /api/ai/squall/buoy/{id} serves live readings only.
    from app.api.demo import router

    route = next(r for r in router.routes if r.path == '/api/demo/squall/buoy/{buoy_id}')
    assert any(dep.call is require_demo_key for dep in route.dependant.dependencies)
