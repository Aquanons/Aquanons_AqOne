"""Unbounded work or storage reachable without an account."""

from __future__ import annotations

from datetime import timedelta

import pytest
from probe_harness import now_utc, run_db

from app.api.squall import _load_rows


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
