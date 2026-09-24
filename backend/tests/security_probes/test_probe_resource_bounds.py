"""Unbounded work or storage reachable without an account."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from probe_harness import now_utc, require_status, run_db

from app.api.squall import _load_rows
from app.main import app


@pytest.mark.finding('backend.public-squall.unbounded-history-load')
def test_public_squall_does_not_load_week_old_readings(probe_db):
    """GET /api/public/squall calls _load_rows(conn, live=True) per request."""
    now = now_utc()
    old_rows = 5_000

    async def body(conn):
        await conn.executemany(
            'INSERT INTO buoys (id, label, lat, lon, is_synthetic) VALUES ($1, $1, $2, 122.44, FALSE)',
            [('B1', 11.66), ('B2', 11.67), ('B3', 11.68)],
        )
        await conn.executemany(
            'INSERT INTO barometric_readings (buoy_id, observed_at, pressure_hpa, is_synthetic) '
            'VALUES ($1, $2, 1010.0, FALSE)',
            [(f'B{i % 3 + 1}', now - timedelta(days=7, minutes=i)) for i in range(old_rows)]
            + [(f'B{i % 3 + 1}', now - timedelta(minutes=i)) for i in range(90)],
        )
        readings, _, _ = await _load_rows(conn, live=True)
        return readings

    readings = run_db(probe_db, body)
    stale = [r for r in readings if r['observed_at'] < now - timedelta(days=2)]
    assert not stale, (
        f'one anonymous request loaded {len(readings)} readings, {len(stale)} of them over two days old; '
        'the load grows with retained history'
    )


@pytest.mark.finding('review.public-squall.observed-at-contract')
def test_public_squall_still_reports_the_last_real_reading_when_all_are_stale(probe_db):
    """docs/05: observed_at is the newest real reading ever seen, null only when there has never been one.

    The SEC-18 24-hour window must bound the work, not erase that fact.
    """
    newest = now_utc() - timedelta(days=2)

    async def seed(conn):
        await conn.executemany(
            'INSERT INTO buoys (id, label, lat, lon, is_synthetic) VALUES ($1, $1, $2, 122.44, FALSE)',
            [('B1', 11.66), ('B2', 11.67), ('B3', 11.68)],
        )
        await conn.executemany(
            'INSERT INTO barometric_readings (buoy_id, observed_at, pressure_hpa, is_synthetic) '
            'VALUES ($1, $2, 1010.0, FALSE)',
            [(f'B{i % 3 + 1}', newest - timedelta(minutes=i)) for i in range(30)],
        )

    run_db(probe_db, seed)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/public/squall')
    require_status(response, 200)
    status = response.json()

    assert status['level'] == 'unknown'
    assert status['observed_at'] is not None, (
        'every reading is older than the 24-hour window, so the handset is told there has never been one'
    )
    reported = datetime.fromisoformat(status['observed_at'])
    assert abs((reported - newest).total_seconds()) < 1
    assert status['data_age_seconds'] >= timedelta(days=2).total_seconds() - 60
