from __future__ import annotations

import hmac
import json
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.ai.squall import build_buoys, buoy_detail
from app.api.squall import _load_rows, build_squall_status
from app.db import get_pool
from app.demo.scenarios import advance, fire_beat, get_state, reset, start_scenario
from app.demo.weather import coordinates, forecast, marine

router = APIRouter(prefix='/api/demo', tags=['demo'])


async def require_demo_key(
    demo_key: str | None = Header(default=None, alias='X-Demo-Key'),
) -> None:
    configured_key = os.environ.get('DEMO_CONTROL_KEY', '')
    if not configured_key or demo_key is None or not hmac.compare_digest(demo_key, configured_key):
        raise HTTPException(status_code=403, detail='invalid demo key')


@router.get('/state', dependencies=[Depends(require_demo_key)])
async def state() -> dict[str, object]:
    return get_state().response()


@router.post('/scenario/{name}/start', dependencies=[Depends(require_demo_key)])
async def start(name: str) -> dict[str, object]:
    try:
        return await start_scenario(name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post('/beat/{index}', dependencies=[Depends(require_demo_key)])
async def beat(index: int) -> dict[str, object]:
    try:
        return await fire_beat(index)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post('/advance', dependencies=[Depends(require_demo_key)])
async def advance_demo() -> dict[str, object]:
    try:
        return await advance()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post('/reset', dependencies=[Depends(require_demo_key)])
async def reset_demo() -> dict[str, object]:
    state = get_state()
    if state.run_id is None:
        return {'status': 'reset', 'deleted': {}, **state.response()}
    deleted = await reset(get_pool(), state.run_id)
    return {'status': 'reset', 'deleted': deleted, **get_state().response()}


@router.get('/drift/incident/{incident_id}', dependencies=[Depends(require_demo_key)])
async def demo_drift_ground_truth(incident_id: int) -> dict[str, object]:
    """Ground-truth track for a synthetic replay incident (docs/40 Phase 1
    item 5). The normal responder route (`GET /api/ai/drift/incident/{id}`)
    never returns `true_track` - it is real-track data and only ever
    legitimate for a synthetic evaluation replay. Gated the same way as every
    other route here: DEMO_MODE (this router is only mounted when it is set,
    app/main.py) plus `require_demo_key`, and additionally 404s on a real
    incident so a demo key alone can never unlock live case data.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT id, is_synthetic, true_track FROM incidents WHERE id = $1',
            incident_id,
        )
    if row is None or not row['is_synthetic']:
        raise HTTPException(status_code=404, detail='no synthetic incident with that id')
    true_track = row['true_track']
    if isinstance(true_track, str):
        true_track = json.loads(true_track)
    return {'incident_id': row['id'], 'source': 'synthetic', 'ground_truth_track': true_track}


@router.get('/squall', dependencies=[Depends(require_demo_key)])
async def demo_squall() -> dict[str, object]:
    """Synthetic squall status for the presenter console (docs/39 Phase 3).

    Production (`/api/ai/squall/current`, `/api/public/squall`) now reads
    live rows only, so the synthetic scenario has nowhere left to display -
    this is that dedicated, visibly-labelled (`source: "synthetic"`) demo
    surface. Gated by DEMO_MODE (this router is only mounted when it's set,
    app/main.py) and require_demo_key, same as every other route here.
    Synthetic data may freely reach `return_now`: this route is demo-key-only
    and the real handset never calls it.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        readings, _, buoy_rows = await _load_rows(conn, live=False)
    return build_squall_status(readings, buoy_rows, source='synthetic', allow_return_now=True)


@router.get('/squall/buoy/{buoy_id}', dependencies=[Depends(require_demo_key)])
async def demo_squall_buoy(buoy_id: str) -> dict[str, object]:
    """Synthetic pressure trace for one buoy, the demo twin of
    `/api/ai/squall/buoy/{id}` (which reads live readings only). The tutorial
    recorder (docs/72) uses it to capture the scenario's squall chart."""
    pool = get_pool()
    async with pool.acquire() as conn:
        readings, _, buoy_rows = await _load_rows(conn, live=False)
    buoys = build_buoys(buoy_rows)
    if buoy_id not in buoys:
        raise HTTPException(status_code=404, detail='buoy not found')
    try:
        return buoy_detail(readings, buoy_id, buoys)
    except KeyError:
        raise HTTPException(status_code=404, detail='no pressure readings available for buoy') from None


def _weather_cells(latitude: str | None, longitude: str | None) -> list[tuple[float, float]]:
    try:
        return coordinates(latitude, longitude)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _active_beat() -> int:
    state = get_state()
    if state.run_id is None:
        raise HTTPException(status_code=409, detail='no demo scenario is active')
    return state.beat


@router.get('/weather/forecast')
async def weather_forecast(
    latitude: str | None = Query(default=None),
    longitude: str | None = Query(default=None),
) -> list[dict[str, dict[str, float | int | str]]]:
    return forecast(_active_beat(), _weather_cells(latitude, longitude))


@router.get('/weather/marine')
async def weather_marine(
    latitude: str | None = Query(default=None),
    longitude: str | None = Query(default=None),
) -> list[dict[str, dict[str, float | int | str]]]:
    return marine(_active_beat(), _weather_cells(latitude, longitude))
