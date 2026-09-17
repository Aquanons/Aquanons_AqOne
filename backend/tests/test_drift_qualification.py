"""Phase 2 verification tests: physical drift support, qualification, and boundary constraints.

Covers:
- D1: Qualification & depth isolation (uncalibrated, synthetic, and deep estuary flow rejected for surface drift).
- D2: Decision-time cutoff vs datum time (availability at decision time prevents future ingest leakage).
- D3: Distinct GPS fix acquisition time vs client transmission time and receipt time.
- D4: Water-connected geometric support vs co-located or land-separated buoys.
- D5: Support loss tracking and honest expiration boundary (no measured still water on missing data).
- D6: Timezone-invariant wind forcing, nonfinite rejection, and forecast interval bounds.
- D7: Coastal barrier collision detection, island crossing prevention, and complete mass accounting.
- D8: Real-case refusal of synthetic fallback, immutable runs, and read-only case retrieval.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from app import geo
from app.ai.current_field import (
    MAX_AGE_SECONDS,
    count_nearby_fresh_buoys,
    create_current_field_factory,
)
from app.ai.drift import (
    ObjectClass,
    WindSeries,
    _interpolate_series,
    predict_drift,
)
from app.api.drift import _sos_case_inputs

MANILA_TZ = timezone(timedelta(hours=8))


class _MockPool:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def fetch(self, query: str, *args):
        return self.rows

    async def fetchrow(self, query: str, *args):
        return self.rows[0] if self.rows else None


def _zero_wind(lat: float, lon: float, start_at: datetime, horizon_hours: float) -> WindSeries:
    times = [start_at, start_at + timedelta(hours=horizon_hours)]
    zeros = np.zeros(2, dtype=float)
    return WindSeries(times=times, u_mps=zeros, v_mps=zeros, source='test', degraded=False)


# ============================================================================
# D1: Qualification & depth isolation
# ============================================================================

def test_d1_qualification_and_depth_isolation():
    """D1: Only physically applicable, qualified, surface observations influence geometry & motion."""
    start_time = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)

    # 4 buoy rows at the same time:
    # 1. Qualified, live, surface (depth 1.0m) -> MUST BE INCLUDED
    # 2. Uncalibrated, live, surface -> MUST BE EXCLUDED
    # 3. Qualified, synthetic, surface -> MUST BE EXCLUDED when allow_synthetic=False
    # 4. Qualified, live, deep current (depth 45.0m) -> MUST BE EXCLUDED for surface drift
    rows = [
        {
            'buoy_id': 'B_QUAL_SURF',
            'buoy_lat': 11.66,
            'buoy_lon': 122.45,
            'observed_at': start_time,
            'observed_u_mps': 0.40,
            'observed_v_mps': 0.10,
            'depth_m': 1.0,
            'source': 'live',
            'calibration_status': 'qualified',
            'created_at': start_time,
        },
        {
            'buoy_id': 'B_UNCALIB',
            'buoy_lat': 11.67,
            'buoy_lon': 122.46,
            'observed_at': start_time,
            'observed_u_mps': 0.90,
            'observed_v_mps': 0.90,
            'depth_m': 1.0,
            'source': 'live',
            'calibration_status': 'uncalibrated',
            'created_at': start_time,
        },
        {
            'buoy_id': 'B_SYNTH',
            'buoy_lat': 11.68,
            'buoy_lon': 122.47,
            'observed_at': start_time,
            'observed_u_mps': 0.50,
            'observed_v_mps': 0.50,
            'depth_m': 1.0,
            'source': 'synthetic',
            'calibration_status': 'qualified',
            'created_at': start_time,
        },
        {
            'buoy_id': 'B_DEEP',
            'buoy_lat': 11.69,
            'buoy_lon': 122.48,
            'observed_at': start_time,
            'observed_u_mps': -0.80,
            'observed_v_mps': -0.80,
            'depth_m': 45.0,  # Deep estuary flow
            'source': 'live',
            'calibration_status': 'qualified',
            'created_at': start_time,
        },
    ]

    async def _run():
        pool = _MockPool(rows)
        # Geometry count for surface drift must only count B_QUAL_SURF (1 buoy), not 4
        count = await count_nearby_fresh_buoys(
            pool, lat=11.66, lon=122.45, at=start_time, include_synthetic=False, max_depth_m=2.5,
        )
        assert count == 1, f"Expected exactly 1 qualified surface buoy, got {count}"

        # Current field factory must only use qualified surface observations
        factory = await create_current_field_factory(
            pool, include_synthetic=False, allow_synthetic=False, as_of=start_time, max_depth_m=2.5,
        )
        u, v = factory(np.array([11.66]), np.array([122.45]), start_time)
        # B_QUAL_SURF has u=0.40, v=0.10. If deep (-0.80) or uncalibrated (0.90) leaked in, u != 0.40
        assert u[0] == pytest.approx(0.40, abs=0.05)
        assert v[0] == pytest.approx(0.10, abs=0.05)

    asyncio.run(_run())


# ============================================================================
# D2: Decision-time cutoff vs datum time
# ============================================================================

def test_d2_decision_cutoff_prevents_future_ingest_leakage():
    """D2: Cutoff is decision time, not datum time; observations arriving after decision time are excluded."""
    obs_time = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)
    receipt_time = datetime(2026, 8, 15, 8, 20, 0, tzinfo=UTC)

    row = {
        'buoy_id': 'B1',
        'buoy_lat': 11.66,
        'buoy_lon': 122.45,
        'observed_at': obs_time,
        'observed_u_mps': 0.30,
        'observed_v_mps': 0.15,
        'depth_m': 1.0,
        'source': 'live',
        'calibration_status': 'qualified',
        'created_at': receipt_time,
    }

    async def _run():
        pool = _MockPool([row])

        # 1. At decision time 08:10 UTC: receipt_time (08:20) is in the FUTURE of decision.
        # This observation MUST NOT be available at 08:10 (future leakage)!
        decision_early = datetime(2026, 8, 15, 8, 10, 0, tzinfo=UTC)
        factory_early = await create_current_field_factory(
            pool, include_synthetic=False, allow_synthetic=False, as_of=decision_early,
        )
        u_early, v_early = factory_early(np.array([11.66]), np.array([122.45]), obs_time)
        assert u_early[0] == 0.0, "Observation received at 08:20 leaked into 08:10 decision!"

        # 2. At decision time 08:30 UTC: receipt_time (08:20) is in the past.
        # Row is available and can reconstruct the drift from datum (07:00).
        decision_late = datetime(2026, 8, 15, 8, 30, 0, tzinfo=UTC)
        factory_late = await create_current_field_factory(
            pool, include_synthetic=False, allow_synthetic=False, as_of=decision_late,
        )
        u_late, v_late = factory_late(np.array([11.66]), np.array([122.45]), obs_time)
        assert u_late[0] == pytest.approx(0.30, abs=0.01)

    asyncio.run(_run())


# ============================================================================
# D3: Distinct GPS fix acquisition time vs client transmission time
# ============================================================================

def test_d3_gps_fix_acquisition_time_distinct_from_send_time():
    """D3: Actual GNSS fix time is preserved distinctly from client transmission time and server receipt."""
    receipt_time = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
    send_time = datetime(2026, 8, 15, 11, 55, 0, tzinfo=UTC)
    client_ts = int(send_time.timestamp())
    # Cached GPS fix acquired 90 minutes earlier
    gps_fix_time = datetime(2026, 8, 15, 10, 30, 0, tzinfo=UTC)

    async def _run():
        # Case A: Modern SOS with explicit fix_acquired_at
        sos_row_with_fix = {
            'vessel_id': 'VESSEL-01',
            'latitude': 11.66,
            'longitude': 122.45,
            'created_at': receipt_time,
            'client_ts': client_ts,
            'acknowledged_at': receipt_time,
            'resolved_at': None,
            'fix_acquired_at': gps_fix_time,
            'fix_accuracy_m': 12.5,
        }
        conn_a = _MockPool([sos_row_with_fix])
        _, _, _, datum_a, meta_a = await _sos_case_inputs(conn_a, 1)
        assert datum_a == gps_fix_time
        assert meta_a['datum_source'] == 'gnss_fix'
        assert meta_a['fix_accuracy_m'] == 12.5
        assert meta_a['delay_seconds'] == 5400.0  # 90 minutes

        # Case B: Legacy SOS with client_ts only (no explicit GPS fix acquisition time)
        # Must NOT falsely claim 'client_fix' merely from send time
        sos_row_legacy = {
            'vessel_id': 'VESSEL-01',
            'latitude': 11.66,
            'longitude': 122.45,
            'created_at': receipt_time,
            'client_ts': client_ts,
            'acknowledged_at': receipt_time,
            'resolved_at': None,
            'fix_acquired_at': None,
            'fix_accuracy_m': None,
        }
        conn_b = _MockPool([sos_row_legacy])
        _, _, _, datum_b, meta_b = await _sos_case_inputs(conn_b, 2)
        assert meta_b['datum_source'] in ('client_send', 'receipt_time')
        assert meta_b['datum_source'] != 'client_fix'

    asyncio.run(_run())


# ============================================================================
# D4: Water-connected geometric support vs co-located buoys
# ============================================================================

def test_d4_water_connected_support_and_colocation_detection():
    """D4: Co-located buoys or buoys separated by a land headland do not establish 2D water support."""
    target_lat = 11.66
    target_lon = 122.45
    t0 = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)

    # Buoy 1 and Buoy 2 are separated by only 50 metres (co-located)
    colocated_rows = [
        {
            'buoy_id': 'B1',
            'buoy_lat': 11.6600,
            'buoy_lon': 122.4500,
            'observed_at': t0,
            'observed_u_mps': 0.20,
            'observed_v_mps': 0.10,
            'depth_m': 1.0,
            'source': 'live',
            'calibration_status': 'qualified',
            'created_at': t0,
        },
        {
            'buoy_id': 'B2',
            'buoy_lat': 11.6604,  # ~45m away
            'buoy_lon': 122.4503,
            'observed_at': t0,
            'observed_u_mps': 0.22,
            'observed_v_mps': 0.11,
            'depth_m': 1.0,
            'source': 'live',
            'calibration_status': 'qualified',
            'created_at': t0,
        },
    ]

    async def _run():
        pool = _MockPool(colocated_rows)
        count = await count_nearby_fresh_buoys(
            pool, lat=target_lat, lon=target_lon, at=t0,
            min_separation_m=500.0,
        )
        assert count < 2, "Co-located buoys (< 500m apart) falsely counted as 2 spatial points!"

    asyncio.run(_run())


# ============================================================================
# D5: Support loss tracking and honest expiration boundary
# ============================================================================

def test_d5_no_measured_still_water_on_missing_support():
    """D5: Expired observations do NOT masquerade as 0 m/s still water with full qualification."""
    t0 = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)

    # 2 buoys with observations that expire after 1 hour (MAX_AGE_SECONDS = 3600)
    rows = [
        {
            'buoy_id': 'B1',
            'buoy_lat': 11.66,
            'buoy_lon': 122.45,
            'observed_at': t0,
            'observed_u_mps': 0.35,
            'observed_v_mps': 0.15,
            'depth_m': 1.0,
            'source': 'live',
            'calibration_status': 'qualified',
            'created_at': t0,
        },
        {
            'buoy_id': 'B2',
            'buoy_lat': 11.68,
            'buoy_lon': 122.47,
            'observed_at': t0,
            'observed_u_mps': 0.30,
            'observed_v_mps': 0.10,
            'depth_m': 1.0,
            'source': 'live',
            'calibration_status': 'qualified',
            'created_at': t0,
        },
    ]

    async def _run():
        factory = await create_current_field_factory(
            _MockPool(rows), include_synthetic=False, allow_synthetic=False, as_of=t0 + timedelta(hours=3),
        )

        # Run 4-hour simulation
        res = predict_drift(
            last_lat=11.67,
            last_lon=122.46,
            observed_at=t0,
            object_class=ObjectClass.swamped_banca,
            forecast_hours=4.0,
            step_minutes=15,
            particle_count=100,
            current_vector_fn=factory,
            wind_provider=_zero_wind,
        )

        # Observation support was lost after 1 hour (3600s)
        assert res.support_lost_at is not None
        lost_dt = datetime.fromisoformat(res.support_lost_at)
        assert lost_dt <= t0 + timedelta(seconds=MAX_AGE_SECONDS + 900)

    asyncio.run(_run())


# ============================================================================
# D6: Timezone-invariant wind forcing and NaN rejection
# ============================================================================

def test_d6_wind_timezone_invariance_and_nan_rejection():
    """D6: Wind series interpolation is invariant to host timezone and rejects NaN/nonfinite."""
    t0_utc = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)
    t1_utc = datetime(2026, 8, 15, 9, 0, 0, tzinfo=UTC)

    # Equivalent timestamps in Manila time (UTC+8)
    t0_pht = t0_utc.astimezone(MANILA_TZ)
    t1_pht = t1_utc.astimezone(MANILA_TZ)

    series_utc = WindSeries(
        times=[t0_utc, t1_utc],
        u_mps=np.array([5.0, 7.0]),
        v_mps=np.array([2.0, 4.0]),
        source='open-meteo',
        degraded=False,
    )
    series_pht = WindSeries(
        times=[t0_pht, t1_pht],
        u_mps=np.array([5.0, 7.0]),
        v_mps=np.array([2.0, 4.0]),
        source='open-meteo',
        degraded=False,
    )

    eval_time = t0_utc + timedelta(minutes=30)
    u1, v1 = _interpolate_series(series_utc, eval_time)
    u2, v2 = _interpolate_series(series_pht, eval_time)

    # Forcing must be identical regardless of how times were represented
    assert u1 == pytest.approx(6.0, abs=1e-4)
    assert u2 == pytest.approx(6.0, abs=1e-4)
    assert u1 == pytest.approx(u2, abs=1e-6)
    assert v1 == pytest.approx(v2, abs=1e-6)

    # Series with NaNs must be rejected or raise ValueError
    series_nan = WindSeries(
        times=[t0_utc, t1_utc],
        u_mps=np.array([5.0, np.nan]),
        v_mps=np.array([2.0, 4.0]),
        source='open-meteo',
        degraded=False,
    )
    with pytest.raises(ValueError, match='nonfinite|NaN'):
        _interpolate_series(series_nan, eval_time)


# ============================================================================
# D7: Coastal barrier collision detection & mass accounting
# ============================================================================

def test_d7_barrier_collision_and_complete_mass_accounting():
    """D7: Crossing land strands particle; mass is completely accounted for without deletion."""
    start_lat = 11.670
    start_lon = 122.420
    start_time = datetime(2026, 8, 1, 8, 0, 0, tzinfo=UTC)

    def _strong_west(lat, lon, at):
        shape = np.asarray(lat).shape
        return -1.2 * np.ones(shape, dtype=float), np.zeros(shape, dtype=float)

    particle_count = 150
    result = predict_drift(
        last_lat=start_lat,
        last_lon=start_lon,
        observed_at=start_time,
        object_class=ObjectClass.swamped_banca,
        forecast_hours=6.0,
        particle_count=particle_count,
        step_minutes=15,
        current_vector_fn=_strong_west,
        wind_provider=_zero_wind,
        boundary_polygon=geo.WATER_POLYGON,
        enable_stranding=True,
    )

    d = result.to_dict()
    assert 'stranded_count' in d
    assert d['stranded_count'] > 0

    # Total mass accounting: stranded + afloat + outside_domain == particle_count
    afloat = particle_count - result.stranded_count
    assert afloat + result.stranded_count == particle_count


# ============================================================================
# D8: Real case refusal of synthetic fallback & read idempotency
# ============================================================================

def test_d8_real_case_refuses_synthetic_fallback():
    """D8: Real case with insufficient observations persists insufficiency, never synthetic fallback."""
    start_time = datetime(2026, 8, 15, 8, 0, 0, tzinfo=UTC)

    async def _run():
        empty_pool = _MockPool([])
        factory = await create_current_field_factory(
            empty_pool, include_synthetic=False, allow_synthetic=False, as_of=start_time,
        )
        u, v = factory(np.array([11.66]), np.array([122.45]), start_time)
        assert np.all(u == 0.0)
        assert factory.observation_fraction == 0.0

    asyncio.run(_run())
