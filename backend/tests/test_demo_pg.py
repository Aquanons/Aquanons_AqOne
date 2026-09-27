import asyncio

import asyncpg

from app.db import shutdown_db, startup_db
from app.demo import scenarios
from app.simulation.generator import build_plan, regenerate

# docs/71 RND-08, RND-09: the presenter demo runs every beat on freshly
# generated data, and the generator leaves the database able to take new rows.

SEQUENCED_TABLES = ('squall_events', 'incidents', 'sos_events')


def test_generated_tables_accept_rows_without_an_explicit_id(probe_db):
    async def run():
        await regenerate(probe_db, build_plan(days=14, seed=42))
        conn = await asyncpg.connect(probe_db)
        try:
            for table in SEQUENCED_TABLES:
                highest = await conn.fetchval(f'SELECT MAX(id) FROM {table}')
                following = await conn.fetchval(f"SELECT nextval(pg_get_serial_sequence('{table}', 'id'))")
                assert following > highest, f'{table}: next id {following} collides with {highest}'
        finally:
            await conn.close()

    asyncio.run(run())


def test_every_squall_fleet_beat_succeeds_on_generated_data(probe_db, monkeypatch):
    monkeypatch.setattr(scenarios, '_state', scenarios.DemoState())

    async def run():
        await regenerate(probe_db, build_plan(days=14, seed=42))
        await startup_db()
        try:
            await scenarios.start_scenario('squall-fleet')
            for beat in (1, 2, 3, 4, 5, 6):
                state = await scenarios.fire_beat(beat)
                assert state['beat'] == beat
        finally:
            await shutdown_db()
        run_id = state['run_id']
        conn = await asyncpg.connect(probe_db)
        try:
            assert await conn.fetchval('SELECT COUNT(*) FROM sos_events WHERE demo_tag = $1', run_id) == 1
            assert await conn.fetchval('SELECT COUNT(*) FROM incidents WHERE demo_tag = $1', run_id) == 1
            assert await conn.fetchval('SELECT COUNT(*) FROM search_sectors WHERE demo_tag = $1', run_id) == 1
        finally:
            await conn.close()
        return state

    state = asyncio.run(run())
    assert state['incident_id'] is not None


def test_a_synthetic_replay_is_shown_at_its_evaluated_horizon(probe_db):
    # docs/71 RND-07: the map compares the forecast with the truth over the
    # same span drift_eval scores, not a fixed 24 hours.
    import json

    from fastapi.testclient import TestClient

    from app.ai.drift_replay import replay_horizon_hours
    from app.auth import create_token
    from app.main import app

    async def seed():
        await regenerate(probe_db, build_plan(days=14, seed=42))
        conn = await asyncpg.connect(probe_db)
        try:
            return await conn.fetchrow('SELECT id, true_track FROM incidents WHERE is_synthetic ORDER BY id LIMIT 1')
        finally:
            await conn.close()

    row = asyncio.run(seed())
    track = json.loads(row['true_track']) if isinstance(row['true_track'], str) else row['true_track']
    token = create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo')
    with TestClient(app) as client:
        response = client.get(
            f"/api/ai/drift/incident/{row['id']}?forecast_hours=24",
            headers={'Authorization': f'Bearer {token}'},
        )
    assert response.status_code == 200
    body = response.json()
    assert body['forecast_hours'] == replay_horizon_hours(track)
    assert body['forecast_hours'] < 24
    assert len({json.dumps(contour['geometry']['coordinates']) for contour in body['contours']}) == 3
