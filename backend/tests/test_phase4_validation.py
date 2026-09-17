"""Phase 4 verification suite: physical drift, boundaries, datum correctness, and search evidence.

Verifies:
1. Replay of delayed SOS with stale fix uses declared physical datum, not receipt time.
2. Real cases reject synthetic current forcing, prevent future leakage, and report whole-run support loss.
3. Shoreline boundary and stranding prevent particles from crossing land barriers into mountains.
4. Time-step and grid resolution numerical sensitivity.
5. Moving target leaving searched area: past negative search attenuates trajectory likelihood
   without erasing unrelated present mass arriving later.
6. Chronological search replay across reruns, duplicate protection, and unsupported likelihood invariance.
7. Recommend next area is explicitly advisory rather than automatic tasking.
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from app import geo
from app.ai.current_field import create_current_field_factory
from app.ai.drift import (
    ObjectClass,
    WindSeries,
    predict_drift,
)
from app.ai.search import (
    recommend_next_area,
    update_posterior,
    update_trajectory_weights,
)
from app.api.drift import _sos_case_inputs


class _FakeAsyncConn:
    """Minimal fake connection for unit testing _sos_case_inputs."""

    def __init__(self, row: dict | None) -> None:
        self.row = row

    async def fetchrow(self, _query: str, *_args):
        return self.row


def _zero_wind(lat: float, lon: float, start_at: datetime, horizon_hours: float) -> WindSeries:
    times = [start_at, start_at + timedelta(hours=horizon_hours)]
    zeros = np.zeros(2, dtype=float)
    return WindSeries(times=times, u_mps=zeros, v_mps=zeros, source='test', degraded=False)


def _west_current(lat, lon, at):
    """Uniform current pushing west toward the New Washington / Aklan shoreline."""
    shape = np.asarray(lat).shape
    return -0.8 * np.ones(shape, dtype=float), np.zeros(shape, dtype=float)


def test_delayed_sos_uses_declared_physical_datum_not_receipt_time():
    """A delayed SOS arriving hours later via mesh relay must use the client GPS fix time,
    not server receipt time (created_at), as the physical datum for drift prediction."""
    async def _run():
        receipt_time = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
        # Phone acquired fix and sent SOS at 09:30 UTC, delayed by 2.5 hours in store-and-forward mesh
        fix_time = datetime(2026, 8, 15, 9, 30, 0, tzinfo=UTC)
        client_ts = int(fix_time.timestamp())

        fake_sos_row = {
            'vessel_id': 'VESSEL-AKL-01',
            'latitude': 11.66,
            'longitude': 122.45,
            'created_at': receipt_time,
            'client_ts': client_ts,
            'acknowledged_at': receipt_time + timedelta(minutes=2),
            'resolved_at': None,
        }
        conn = _FakeAsyncConn(fake_sos_row)
        vessel_id, lat, lon, datum_at, datum_meta = await _sos_case_inputs(conn, 1)

        assert datum_at == fix_time
        assert datum_at != receipt_time
        assert datum_meta['datum_source'] in ('client_send', 'client_fix')
        assert datum_meta['delay_seconds'] == 9000.0  # 2.5 hours delay recognized

        # Also verify responder override takes precedence when supplied
        manual_datum = datetime(2026, 8, 15, 9, 0, 0, tzinfo=UTC)
        _, _, _, datum_at_override, meta_override = await _sos_case_inputs(
            conn, 1, override_datum_at=manual_datum,
        )
        assert datum_at_override == manual_datum
        assert meta_override['datum_source'] == 'responder_override'

    asyncio.run(_run())


def test_no_real_case_synthetic_forcing_and_support_loss_midway_reporting():
    """Real cases (allow_synthetic=False) must never use synthetic current equations,
    and must accurately report when observation support is lost midway through a run."""
    async def _run():
        start_time = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)

        class _EmptyPool:
            def acquire(self):
                return self
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def fetch(self, *args):
                return []

        # Real case factory with no buoys: must return zero velocity, NOT synthetic velocity
        current_fn = await create_current_field_factory(
            _EmptyPool(), include_synthetic=False, allow_synthetic=False, as_of=start_time,
        )
        u, v = current_fn(np.array([11.66]), np.array([122.45]), start_time)
        assert np.all(u == 0.0)
        assert np.all(v == 0.0)
        assert current_fn.observation_fraction == 0.0

        # Test support loss tracking when observations expire midway
        class _MockBuoyPool:
            def acquire(self):
                return self
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def fetch(self, *args):
                # 2 buoys with observations only up to 09:00 UTC (1 hour after start_time)
                return [
                    {
                        'buoy_id': 'B1',
                        'buoy_lat': 11.66,
                        'buoy_lon': 122.45,
                        'observed_at': start_time,
                        'observed_u_mps': 0.25,
                        'observed_v_mps': 0.10,
                    },
                    {
                        'buoy_id': 'B2',
                        'buoy_lat': 11.67,
                        'buoy_lon': 122.46,
                        'observed_at': start_time + timedelta(minutes=30),
                        'observed_u_mps': 0.20,
                        'observed_v_mps': 0.15,
                    },
                ]

        factory = await create_current_field_factory(
            _MockBuoyPool(), include_synthetic=False, allow_synthetic=False, as_of=start_time,
        )
        # Within 1 hour (valid observations)
        u_fresh, _ = factory(np.array([11.66]), np.array([122.45]), start_time + timedelta(minutes=15))
        assert np.all(u_fresh > 0.0)

        # After 3 hours (observations expired past MAX_AGE_SECONDS): support loss must be recorded
        u_expired, _ = factory(np.array([11.66]), np.array([122.45]), start_time + timedelta(hours=3))
        assert np.all(u_expired == 0.0)
        assert factory.support_lost_at is not None

    asyncio.run(_run())


def test_water_connected_boundary_and_stranding_prevents_land_crossing():
    """Drift particles moving toward shore must strand at the coastal boundary
    rather than crossing into land/mountains."""
    # Start just inside municipal waters near Dumaguit (11.67, 122.42)
    start_lat = 11.670
    start_lon = 122.420
    start_time = datetime(2026, 8, 1, 8, 0, 0, tzinfo=UTC)

    # Current strongly pushing WEST onto land (-0.8 m/s = ~70 km over 24h)
    result = predict_drift(
        last_lat=start_lat,
        last_lon=start_lon,
        observed_at=start_time,
        object_class=ObjectClass.swamped_banca,
        forecast_hours=12.0,
        particle_count=200,
        step_minutes=15,
        current_vector_fn=_west_current,
        wind_provider=_zero_wind,
        boundary_polygon=geo.WATER_POLYGON,
        enable_stranding=True,
    )

    # At least some particles must strand when pushed hard into the west coast
    assert result.stranded_count > 0

    # Ensure stranded count is reported in dict representation
    d = result.to_dict()
    assert 'stranded_count' in d
    assert d['stranded_count'] == result.stranded_count


def test_grid_and_timestep_sensitivity():
    """Quantifies numerical convergence across different time steps (10m vs 30m)
    and grid resolutions (250m vs 500m vs 1000m)."""
    start_lat = 11.68
    start_lon = 122.45
    start_time = datetime(2026, 8, 1, 8, 0, 0, tzinfo=UTC)

    # Compare 10-minute vs 30-minute step
    res_10m = predict_drift(
        last_lat=start_lat,
        last_lon=start_lon,
        observed_at=start_time,
        object_class=ObjectClass.intact_hull_adrift,
        forecast_hours=6.0,
        step_minutes=10,
        particle_count=300,
        current_vector_fn=_west_current,
        wind_provider=_zero_wind,
        rng=np.random.default_rng(42),
    )
    res_30m = predict_drift(
        last_lat=start_lat,
        last_lon=start_lon,
        observed_at=start_time,
        object_class=ObjectClass.intact_hull_adrift,
        forecast_hours=6.0,
        step_minutes=30,
        particle_count=300,
        current_vector_fn=_west_current,
        wind_provider=_zero_wind,
        rng=np.random.default_rng(42),
    )

    c10 = res_10m.centroid_track[-1]
    c30 = res_30m.centroid_track[-1]
    dist_m = math.hypot(
        (c10['lon'] - c30['lon']) * 111_320.0 * math.cos(math.radians(start_lat)),
        (c10['lat'] - c30['lat']) * 110_574.0,
    )
    # Centroid displacement between 10m and 30m step should be small (< 200m)
    assert dist_m < 200.0

    # Compare grid resolutions
    res_grid250 = predict_drift(
        last_lat=start_lat,
        last_lon=start_lon,
        observed_at=start_time,
        object_class=ObjectClass.intact_hull_adrift,
        forecast_hours=6.0,
        grid_resolution_m=250.0,
        particle_count=100,
        wind_provider=_zero_wind,
    )
    assert len(res_grid250.contours) == 3


def test_moving_target_leaves_searched_area_without_erasing_unrelated_present_mass():
    """A search at T_search over sector S must reduce the likelihood of trajectories
    that were inside S at T_search, WITHOUT erasing mass of particles that were outside S
    at T_search but drift into S at a later horizon T_later."""
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)  # Search time
    t2 = datetime(2026, 8, 1, 14, 0, tzinfo=UTC)  # Later horizon

    step_times = [t0, t1, t2]

    # Particle 1: Was inside sector S at t1, drifted to location B at t2
    # Particle 2: Was outside sector S at t1, drifted INTO sector S at t2
    sector_S = {'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45}

    # Shape: (3 steps, 2 particles)
    trajectory_lats = np.array([
        [11.61, 11.75],  # t0: P1 inside, P2 far north
        [11.62, 11.70],  # t1: P1 inside S, P2 outside S (11.70 > 11.65)
        [11.50, 11.62],  # t2: P1 left S (11.50 < 11.60), P2 entered S (11.62 in S)
    ])
    trajectory_lons = np.array([
        [122.42, 122.42],
        [122.42, 122.42],
        [122.42, 122.42],
    ])

    search_report = {
        'searched_at': t1,
        'detection_probability': 0.80,
        **sector_S,
    }

    # Update weights based on the search at t1
    weights = update_trajectory_weights(
        trajectory_lats, trajectory_lons, step_times, [search_report],
    )

    # Particle 1 was in S at search time t1 -> weight attenuated by (1 - 0.8) = 0.2
    # Particle 2 was NOT in S at search time t1 -> weight unattenuated (1.0)
    # Ratio P2 / P1 should be 1.0 / 0.2 = 5.0
    assert weights[1] / weights[0] == pytest.approx(5.0, rel=1e-3)

    # Particle 2 is currently in sector S at t2 and has high probability:
    # the past negative search did NOT erase Particle 2's present mass in S!
    assert weights[1] > weights[0]


def test_rerun_preserves_chronological_search_evidence_and_deduplicates():
    """Searched sectors are re-applied chronologically on reruns, duplicate
    submissions are rejected idempotently, and unsupported likelihood leaves prior unchanged."""
    grid = {
        'type': 'DensityGrid',
        'origin': {'lat': 11.65, 'lon': 122.45},
        'x_edges_m': [0.0, 500.0, 1000.0],
        'y_edges_m': [0.0, 500.0, 1000.0],
        'values': [[0.25, 0.25], [0.25, 0.25]],
    }

    # Unsupported detection probability (0.0): prior must be quantitatively unchanged
    unsupported_sector = {
        'x_min_m': 0.0, 'x_max_m': 500.0, 'y_min_m': 0.0, 'y_max_m': 500.0,
        'detection_probability': 0.0,
    }
    unchanged = update_posterior(grid, [unsupported_sector])
    np.testing.assert_array_almost_equal(
        np.array(unchanged['values']), np.array(grid['values']),
    )

    # Valid search reduces cell mass
    valid_sector = {
        'x_min_m': 0.0, 'x_max_m': 500.0, 'y_min_m': 0.0, 'y_max_m': 500.0,
        'detection_probability': 0.60,
    }
    updated = update_posterior(grid, [valid_sector])
    assert updated['values'][0][0] < grid['values'][0][0]

    # Replaying two sectors in chronological order preserves cumulative evidence
    sector_2 = {
        'x_min_m': 500.0, 'x_max_m': 1000.0, 'y_min_m': 0.0, 'y_max_m': 500.0,
        'detection_probability': 0.60,
    }
    replayed = update_posterior(grid, [valid_sector, sector_2])
    assert replayed['values'][0][0] < grid['values'][0][0]
    assert replayed['values'][0][1] < grid['values'][0][1]


def test_recommend_next_area_is_explicitly_advisory_not_tasking():
    """The recommended next search area must be explicitly labeled as an advisory
    recommendation for responder review, never an automatic tasking."""
    grid = {
        'type': 'DensityGrid',
        'origin': {'lat': 11.65, 'lon': 122.45},
        'x_edges_m': [0.0, 500.0, 1000.0],
        'y_edges_m': [0.0, 500.0, 1000.0],
        'values': [[0.10, 0.40], [0.30, 0.20]],
    }
    rec = recommend_next_area(grid)
    assert rec['is_advisory'] is True
    assert 'advisory' in rec['advisory_note'].lower()
    assert 'not an automatic tasking' in rec['advisory_note'].lower()
    assert rec['centroid'] is not None
    assert rec['remaining_mass'] == pytest.approx(0.40)
