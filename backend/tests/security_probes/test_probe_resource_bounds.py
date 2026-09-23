"""Unbounded work or storage reachable without an account."""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from probe_harness import REPO_ROOT, now_utc, run_db

from app.api.squall import _load_rows
from app.demo.weather import coordinates


@pytest.mark.finding('backend.demo-weather.unbounded-coordinate-expansion')
def test_demo_weather_rejects_ten_thousand_coordinate_cells():
    many = 10_000
    with pytest.raises(ValueError):
        coordinates(','.join(['11.66'] * many), ','.join(['122.44'] * many))


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


@pytest.mark.finding('backend.mesh.unbounded-public-storage')
def test_mesh_chat_has_a_retention_or_admission_control():
    """Static: any DELETE/retention for mesh_chat, or a limiter on its POST route."""
    sources = [
        *(REPO_ROOT / 'backend' / 'app').rglob('*.py'),
        *(REPO_ROOT / 'backend' / 'migrations').glob('*.sql'),
        *(REPO_ROOT / 'backend').glob('*.py'),
        *REPO_ROOT.glob('render.yaml'),
    ]
    pattern = re.compile(r'DELETE\s+FROM\s+mesh_chat|mesh_chat.*retention|pg_cron|RateLimit|slowapi', re.I)
    hits = [str(path.relative_to(REPO_ROOT)) for path in sources if pattern.search(path.read_text('utf-8'))]
    assert hits, 'no retention job, cleanup statement, or rate limiter for anonymous mesh_chat rows'
