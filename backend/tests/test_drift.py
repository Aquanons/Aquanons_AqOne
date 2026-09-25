import asyncio
import math
from datetime import UTC, datetime

import numpy as np

from app.ai.drift import ObjectClass, WindSeries, predict_drift
from app.api.drift import _sos_case_inputs


def _uniform_east_current(lat, lon, at):
    shape = np.asarray(lat).shape
    return np.ones(shape, dtype=float), np.zeros(shape, dtype=float)


def _zero_wind(lat, lon, start_at, horizon_hours):
    times = [start_at, start_at.replace(hour=min(23, start_at.hour + 1))]
    zeros = np.zeros(2, dtype=float)
    return WindSeries(times=times, u_mps=zeros, v_mps=zeros, source='test', degraded=False)


def test_uniform_eastward_current_moves_centroid_expected_distance():
    result = predict_drift(
        last_lat=11.6892,
        last_lon=122.3667,
        observed_at=datetime(2026, 8, 1, tzinfo=UTC),
        object_class=ObjectClass.person_in_water,
        forecast_hours=24,
        particle_count=1000,
        step_minutes=60,
        current_vector_fn=_uniform_east_current,
        wind_provider=_zero_wind,
        initial_spread_m=0.0,
        diffusivity_m2_s=0.0,
    )

    final = result.centroid_track[-1]
    east_m = (final['lon'] - 122.3667) * 111_320.0 * math.cos(math.radians(11.6892))
    assert abs(east_m - 86_400.0) < 500.0

    assert len(result.contours) == 3
    for feature in result.contours:
        assert feature['geometry']['type'] == 'Polygon'
        ring = feature['geometry']['coordinates'][0]
        assert ring[0] == ring[-1]


def test_drift_start_ignores_implausible_client_ts():
    created_at = datetime.now(UTC)
    class _Conn:
        async def fetchrow(self, *_args):
            return {
                'vessel_id': 'V1', 'latitude': 11.7, 'longitude': 122.3,
                'created_at': created_at, 'client_ts': int(created_at.timestamp()) - 3 * 365 * 86400,
                'acknowledged_at': created_at, 'resolved_at': None,
                'fix_acquired_at': None, 'fix_accuracy_m': None,
            }

    vessel_id, lat, lon, started_at, metadata = asyncio.run(_sos_case_inputs(_Conn(), 1))
    assert (vessel_id, lat, lon) == ('V1', 11.7, 122.3)
    assert started_at == created_at
    assert metadata['clock_suspect'] is True
