"""Whether one bad row can stop overdue-vessel scoring for the whole fleet."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import timedelta

import pytest
from probe_harness import FakeConn, ProbeBroken, now_utc, run_db
from pydantic import ValidationError

from app.ai.anomaly_service import eligible_latest_trips, evaluate_and_persist
from app.api.contacts import ContactEventIn


def _contact_row(vessel_id, trip_id, observed_at, lat=11.66, lon=122.44):
    return {
        'vessel_id': vessel_id, 'trip_id': trip_id, 'buoy_id': 'B1', 'observed_at': observed_at,
        'latitude': lat, 'longitude': lon, 'is_synthetic': False,
    }


def _trip_state(trip_id, vessel_id, status):
    return {
        'trip_id': trip_id, 'vessel_id': vessel_id, 'status': status, 'welfare_status': 'unknown',
        'departure_at': None, 'expected_return_at': None,
        'expected_checkin_interval_minutes': None, 'amendments': [],
    }


@pytest.mark.finding('backend.contacts.optional-position-crash')
def test_contact_without_coordinates_does_not_abort_fleet_evaluation():
    now = now_utc()
    try:
        ContactEventIn(
            event_id='e1', vessel_id='V-NOPOS', trip_id='T-NOPOS', buoy_id='B1',
            observed_at=now, source='live',
        )
    except ValidationError:
        return  # ingest refuses position-less contacts, so the crash is unreachable
    rows = [
        _contact_row('V-NOPOS', 'T-NOPOS', now - timedelta(hours=1), lat=None, lon=None),
        _contact_row('V-OK', 'T-OK', now - timedelta(hours=1)),
    ]
    try:
        eligible = eligible_latest_trips(rows, as_of=now)
    except (TypeError, ValueError) as exc:
        pytest.fail(f'one accepted contact without coordinates aborts evaluation for every vessel: {exc!r}')
    assert 'V-OK' in {vessel for vessel, _, _ in eligible}


def _run_evaluation(contact_rows, trip_states):
    def responder(kind, sql, args):
        if kind == 'fetch' and 'FROM buoy_contacts' in sql:
            return contact_rows
        if kind == 'fetch' and 'FROM vessel_trips' in sql:
            return trip_states
        return None

    conn = FakeConn(responder)
    error = None
    try:
        asyncio.run(evaluate_and_persist(conn, as_of=now_utc(), include_synthetic=False))
    except Exception as exc:  # the exception is the observation, not a probe error
        error = exc
    deactivated = bool(conn.calls_matching('SET is_active = FALSE'))
    return error, deactivated


@pytest.mark.finding('backend.ai.anomaly.zero-contact-poison-run')
def test_zero_contact_trip_for_a_fresh_vessel_does_not_abort_evaluation():
    error, deactivated = _run_evaluation([], [_trip_state('T-ZERO', 'V-FRESH', 'open')])
    assert error is None, (
        f'an open trip with no contacts for a never-seen vessel aborts evaluation: {error!r} '
        f'(active scores already deactivated before the crash: {deactivated})'
    )


@pytest.mark.finding('backend.ai.anomaly.zero-contact-poison-run')
def test_zero_contact_trip_for_a_known_vessel_does_not_abort_evaluation():
    history = [
        _contact_row('V-OLD', 'T-OLD', now_utc() - timedelta(days=3, hours=h)) for h in range(3)
    ]
    trip_states = [_trip_state('T-OLD', 'V-OLD', 'completed'), _trip_state('T-NEW', 'V-OLD', 'open')]
    error, deactivated = _run_evaluation(history, trip_states)
    assert error is None, (
        f'an open zero-contact trip for a vessel with history aborts evaluation: {error!r} '
        f'(active scores already deactivated before the crash: {deactivated})'
    )


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
