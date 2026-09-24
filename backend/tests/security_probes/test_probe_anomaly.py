"""Whether one bad row can stop overdue-vessel scoring for the whole fleet."""

from __future__ import annotations

import json
import time
from datetime import timedelta

import pytest
from probe_harness import ProbeBroken, now_utc, run_db

from app.ai.anomaly_service import evaluate_and_persist


async def _seed_live_alert(conn, now):
    await conn.execute("INSERT INTO buoys (id, label, lat, lon) VALUES ('B1', 'B1', 11.66, 122.44)")
    await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('V-LIVE', 'V-LIVE')")
    await conn.execute(
        '''
        INSERT INTO vessel_anomaly_scores
          (vessel_id, trip_id, observed_at, last_contact_at, score, status, factors,
           is_active, is_synthetic)
        VALUES ('V-LIVE', 'T-LIVE', $1, $1, 0.9, 'alert', '[]'::jsonb, TRUE, FALSE)
        ''',
        now,
    )


async def _evaluate_and_read_back(conn, now):
    """Mirrors the callers: a bare pooled connection, no explicit transaction."""
    error = None
    try:
        await evaluate_and_persist(conn, as_of=now, include_synthetic=False)
    except Exception as exc:  # the exception is the observation, not a probe error
        error = exc
    still_active = await conn.fetchval(
        "SELECT is_active FROM vessel_anomaly_scores WHERE vessel_id = 'V-LIVE'"
    )
    return error, still_active


@pytest.mark.finding('backend.ai.anomaly.zero-contact-poison-run')
def test_failed_evaluation_does_not_commit_score_deactivation(probe_db):
    """On real Postgres: does a zero-contact crash leave the live alert queue
    emptied? Safe = the run succeeds, or nothing it did was committed."""
    now = now_utc()

    async def body(conn):
        await _seed_live_alert(conn, now)
        await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('V-FRESH', 'V-FRESH')")
        await conn.execute(
            "INSERT INTO vessel_trips (trip_id, vessel_id, status) VALUES ('T-ZERO', 'V-FRESH', 'open')"
        )
        return await _evaluate_and_read_back(conn, now)

    error, still_active = run_db(probe_db, body)
    assert error is None or still_active, (
        f'evaluation raised {error!r} after committing is_active=FALSE on the seeded live alert - '
        'the partial run emptied the responder queue'
    )


@pytest.mark.finding('new.backend.anomaly.jsonb-parameter-encoding')
def test_one_ordinary_live_trip_evaluates_on_real_postgres(probe_db):
    """Not in the audit. Found while writing these probes: evaluate_and_persist
    passes Python lists to $N::jsonb and app/db.py registers no JSON codec, so
    asyncpg may reject every score write. The unit suite only uses fakes."""
    now = now_utc()

    async def body(conn):
        await _seed_live_alert(conn, now)
        await conn.execute(
            '''
            INSERT INTO buoy_contacts (event_id, buoy_id, vessel_id, trip_id, observed_at,
                                       latitude, longitude, source, is_synthetic,
                                       contact_type, contact_value)
            SELECT 'c' || g, 'B1', 'V-LIVE', 'T-NOW', $1::timestamptz - (g || ' minutes')::interval,
                   11.66, 122.44, 'live', FALSE, 'mesh_ping', 'c' || g
            FROM generate_series(10, 30, 10) AS g
            ''',
            now,
        )
        return await _evaluate_and_read_back(conn, now)

    error, _ = run_db(probe_db, body)
    assert error is None, f'scoring one ordinary live trip on real Postgres raised {error!r}'


@pytest.mark.finding('backend.ai.anomaly.authenticated-whole-fleet-recompute:measure')
def test_measure_whole_fleet_evaluation_cost(probe_db, record_property):
    """MEASURE only: records cost at one synthetic scale; never a verdict."""
    now = now_utc()
    vessels, contacts_per_vessel = 200, 50

    async def seed(conn):
        await conn.execute("INSERT INTO buoys (id, label, lat, lon) VALUES ('B1', 'B1', 11.66, 122.44)")
        await conn.executemany(
            'INSERT INTO vessels (id, boat_name) VALUES ($1, $1)',
            [(f'M{v:03d}',) for v in range(vessels)],
        )
        await conn.executemany(
            '''
            INSERT INTO buoy_contacts (event_id, buoy_id, vessel_id, trip_id, observed_at,
                                       latitude, longitude, source, is_synthetic,
                                       contact_type, contact_value)
            VALUES ($1, 'B1', $2, $3, $4, 11.66, 122.44, 'live', FALSE, 'mesh_ping', $1)
            ''',
            [
                (f'm-{v}-{c}', f'M{v:03d}', f'M{v:03d}-T{c // 10}', now - timedelta(hours=c))
                for v in range(vessels) for c in range(contacts_per_vessel)
            ],
        )

    run_db(probe_db, seed)

    async def evaluate(conn):
        started = time.perf_counter()
        rows = await evaluate_and_persist(conn, as_of=now, include_synthetic=False)
        return time.perf_counter() - started, len(rows)

    try:
        elapsed, scored = run_db(probe_db, evaluate)
    except Exception as exc:
        raise ProbeBroken(f'evaluation crashed on the synthetic fleet: {exc!r}') from exc
    metrics = {
        'contacts': vessels * contacts_per_vessel, 'vessels': vessels,
        'scored_trips': scored, 'elapsed_seconds': round(elapsed, 3),
    }
    record_property('measure', json.dumps(metrics))
    print(f'MEASURE {json.dumps(metrics)}')
