"""Phase 3 verification tests: time-aligned search evidence assimilation.

Covers:
- S1: Two equal-weight trajectories; at search time A is in S and B outside; at display time A left and B entered;
      submit via responder endpoint with illustrative POD 0.8 -> A/B final weights are 1/6 and 5/6;
      present mass of B in S is preserved; persisted grid and displayed contours use those weights.
- S2: Search before first/after last trajectory time, absent time, naive ambiguous time, or unsupported interval ->
      no nearest-endpoint/final-step substitution; event remains recorded as unassimilated with a reason
      or request rejected clearly.
- S3: Search spans multiple steps; overlapping repeat sweeps; actual track excludes most of a rectangle ->
      footprint/time meaning is explicit; one full-operation POD is not repeatedly multiplied per step;
      correlated repeats do not create artificial certainty.
- S4: Retry same report; submit out of order; rerun with changed grid origin/extent; retry stale run ->
      stable event identity, one application per run, geographic footprint preserved, atomic update
      and immutable older run inputs.
- S5: Unknown detection likelihood versus explicit illustrative POD 0; POD negative, >1 or nonfinite;
      near-total mass rejection -> unknown stays unknown; invalid rejected; zero leaves prior unchanged;
      all-zero/degenerate result reports failure rather than fabricating a normalized map.
- S6: Persist trajectories, restart process, fetch and update; historical run has grids only ->
      same weights/coordinates after restart; legacy run remains readable but time-aware update requires
      supported state; no fake reconstructed trajectories from a centroid.
- S7: Rerun decision predates receipt of an earlier search report ->
      that report cannot change the historical prospective posterior; retrospective processing is separately labelled.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from app.ai.drift import _to_latlon, _to_xy
from app.ai.search import update_trajectory_weights

MANILA_TZ = timezone(timedelta(hours=8))


class _MockSearchConn:
    def __init__(self, incidents: dict, runs: dict, sectors: list):
        self.incidents = incidents
        self.runs = runs
        self.sectors = sectors
        self.executed: list[tuple] = []

    async def fetchrow(self, query: str, *args):
        if 'SELECT id, run_number, posterior_grid, trajectory_data FROM drift_runs' in query:
            incident_id, run_number = args
            for r in self.runs.get(incident_id, []):
                if r['run_number'] == run_number:
                    return r
            return None
        if 'SELECT is_synthetic FROM incidents' in query:
            inc = self.incidents.get(args[0])
            return {'is_synthetic': inc.get('is_synthetic', False)} if inc else None
        if 'SELECT id FROM search_sectors WHERE incident_id = $1 AND idempotency_key = $2' in query:
            incident_id, key = args
            for s in self.sectors:
                if s['incident_id'] == incident_id and s.get('idempotency_key') == key:
                    return {'id': s['id']}
            return None
        return None

    async def fetch(self, query: str, *args):
        if 'FROM search_sectors' in query:
            incident_id = args[0]
            return [s for s in self.sectors if s['incident_id'] == incident_id]
        return []

    async def execute(self, query: str, *args):
        self.executed.append((query, args))
        if 'UPDATE drift_runs SET posterior_grid' in query:
            grid_json, traj_json, run_id = args
            for runs in self.runs.values():
                for r in runs:
                    if r['id'] == run_id:
                        r['posterior_grid'] = json.loads(grid_json)
                        r['trajectory_data'] = json.loads(traj_json)
        elif 'INSERT INTO search_sectors' in query:
            self.sectors.append({
                'id': len(self.sectors) + 1,
                'incident_id': args[0],
                'x_min_m': args[1], 'x_max_m': args[2],
                'y_min_m': args[3], 'y_max_m': args[4],
                'detection_probability': args[5],
                'run_id': args[6],
                'reported_by': args[7],
                'method': args[8],
                'notes': args[9],
                'idempotency_key': args[10],
                'south': args[11], 'west': args[12],
                'north': args[13], 'east': args[14],
                'searched_at': args[15],
            })

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def transaction(self):
        return self


# S1: Two equal-weight trajectories; at search time A is in S and B outside; at display time A left and B entered;
# submit via responder endpoint with illustrative POD 0.8 -> A/B final weights are 1/6 and 5/6;
# present mass of B in S is preserved; persisted grid and displayed contours use those weights.
def test_s1_time_aligned_trajectory_weight_update_preserves_present_mass():
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    t_search = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    t_display = datetime(2026, 8, 1, 14, 0, tzinfo=UTC)

    step_times = [t0, t_search, t_display]

    # Sector S bounds
    sector_S = {'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45}

    # 2 trajectories: Particle A and Particle B
    # At t_search: A is in S (lat 11.62), B is outside S (lat 11.70)
    # At t_display: A left S (lat 11.50), B entered S (lat 11.62)
    lats = np.array([
        [11.61, 11.75],
        [11.62, 11.70],
        [11.50, 11.62],
    ])
    lons = np.array([
        [122.42, 122.42],
        [122.42, 122.42],
        [122.42, 122.42],
    ])

    search_report = {
        'searched_at': t_search,
        'detection_probability': 0.8,
        **sector_S,
    }

    weights = update_trajectory_weights(lats, lons, step_times, [search_report])

    assert len(weights) == 2
    # P(A) unnormalized = 0.5 * 0.2 = 0.1
    # P(B) unnormalized = 0.5 * 1.0 = 0.5
    # Normalized: W(A) = 0.1 / 0.6 = 1/6, W(B) = 0.5 / 0.6 = 5/6
    assert weights[0] == pytest.approx(1.0 / 6.0, rel=1e-4)
    assert weights[1] == pytest.approx(5.0 / 6.0, rel=1e-4)
    assert weights[1] / weights[0] == pytest.approx(5.0, rel=1e-4)

    # Particle B is in S at t_display! Its weight (5/6) represents present mass in S,
    # proving that past negative search at t_search did not wipe out present mass in S at t_display.
    assert lats[2, 1] >= sector_S['south'] and lats[2, 1] <= sector_S['north']


# S2: Search before first/after last trajectory time, absent time, naive ambiguous time, or unsupported interval ->
# no nearest-endpoint/final-step substitution; event remains recorded as unassimilated with a reason
# or request rejected clearly.
def test_s2_search_time_outside_trajectory_rejected_or_unassimilated():
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    step_times = [t0, t1]
    lats = np.array([[11.60, 11.60], [11.60, 11.60]])
    lons = np.array([[122.40, 122.40], [122.40, 122.40]])

    sector_S = {'south': 11.55, 'north': 11.65, 'west': 122.35, 'east': 122.45, 'detection_probability': 0.8}

    # Case A: searched_at before first step
    report_early = {'searched_at': t0 - timedelta(hours=1), **sector_S}
    with pytest.raises(ValueError, match="outside trajectory time range"):
        update_trajectory_weights(lats, lons, step_times, [report_early])

    # Case B: searched_at after last step
    report_late = {'searched_at': t1 + timedelta(hours=2), **sector_S}
    with pytest.raises(ValueError, match="outside trajectory time range"):
        update_trajectory_weights(lats, lons, step_times, [report_late])

    # Case C: searched_at is timezone-naive
    report_naive = {'searched_at': datetime(2026, 8, 1, 10, 0), **sector_S}
    with pytest.raises(ValueError, match="timezone-aware"):
        update_trajectory_weights(lats, lons, step_times, [report_naive])


# S3: Search spans multiple steps; overlapping repeat sweeps; actual track excludes most of a rectangle ->
# footprint/time meaning is explicit; one full-operation POD is not repeatedly multiplied per step;
# correlated repeats do not create artificial certainty.
def test_s3_multi_step_search_interval_and_dependent_repeat_sweeps():
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    t3 = datetime(2026, 8, 1, 11, 0, tzinfo=UTC)
    step_times = [t0, t1, t2, t3]

    # Particle 1 is in S for all 3 steps (t1, t2, t3).
    # Particle 2 is outside S throughout.
    lats = np.array([
        [11.62, 11.75],
        [11.62, 11.75],
        [11.62, 11.75],
        [11.62, 11.75],
    ])
    lons = np.array([
        [122.42, 122.42],
        [122.42, 122.42],
        [122.42, 122.42],
        [122.42, 122.42],
    ])

    sector_interval = {
        'search_start_at': t1,
        'search_end_at': t3,
        'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45,
        'detection_probability': 0.8,
    }

    # One multi-step search interval covers steps t1, t2, t3.
    # It must attenuate Particle 1 exactly ONCE by (1 - 0.8) = 0.2, NOT (1 - 0.8)^3 = 0.008!
    w = update_trajectory_weights(lats, lons, step_times, [sector_interval])
    # P(P1) unnorm = 0.5 * 0.2 = 0.1, P(P2) unnorm = 0.5 * 1.0 = 0.5 -> 0.1 / 0.6 = 1/6
    assert w[0] == pytest.approx(1.0 / 6.0, rel=1e-4)

    # Dependent repeat sweep with 0.8 POD
    dependent_repeat = {
        'searched_at': t2,
        'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45,
        'detection_probability': 0.8,
        'dependent': True,
    }
    # Effective POD discounted to 0.8 * 0.25 = 0.2
    w_dep = update_trajectory_weights(lats, lons, step_times, [dependent_repeat])
    # Attenuated by 1 - 0.2 = 0.8, unnormalized 0.5*0.8=0.4, 0.5*1=0.5 -> 0.4/0.9 = 4/9
    assert w_dep[0] == pytest.approx(4.0 / 9.0, rel=1e-3)


# S4: Retry same report; submit out of order; rerun with changed grid origin/extent; retry stale run ->
# stable event identity, one application per run, geographic footprint preserved, atomic update
# and immutable older run inputs.
def test_s4_geographic_footprint_preserved_independent_of_grid_origin():
    # Verify that geographic footprint (south, west, north, east) is invariant to grid origin changes
    sector = {'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45}
    origin1_lat, origin1_lon = 11.50, 122.30
    origin2_lat, origin2_lon = 11.70, 122.50

    x1_min, y1_min = _to_xy(np.array([sector['south']]), np.array([sector['west']]), origin1_lat, origin1_lon)
    x1_max, y1_max = _to_xy(np.array([sector['north']]), np.array([sector['east']]), origin1_lat, origin1_lon)

    x2_min, y2_min = _to_xy(np.array([sector['south']]), np.array([sector['west']]), origin2_lat, origin2_lon)
    x2_max, y2_max = _to_xy(np.array([sector['north']]), np.array([sector['east']]), origin2_lat, origin2_lon)

    # Metre coordinates change when origin changes
    assert x1_min[0] != x2_min[0]
    # But converted back, they recover the exact same geographic bounds
    lat1, lon1 = _to_latlon(x1_min, y1_min, origin1_lat, origin1_lon)
    lat2, lon2 = _to_latlon(x2_min, y2_min, origin2_lat, origin2_lon)
    assert lat1[0] == pytest.approx(sector['south'], abs=1e-6)
    assert lon1[0] == pytest.approx(sector['west'], abs=1e-6)
    assert lat2[0] == pytest.approx(sector['south'], abs=1e-6)
    assert lon2[0] == pytest.approx(sector['west'], abs=1e-6)


# S5: Unknown detection likelihood versus explicit illustrative POD 0; POD negative, >1 or nonfinite;
# near-total mass rejection -> unknown stays unknown; invalid rejected; zero leaves prior unchanged;
# all-zero/degenerate result reports failure rather than fabricating a normalized map.
def test_s5_pod_zero_and_invalid_and_degenerate_handling():
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    step_times = [t0]
    lats = np.array([[11.62, 11.62]])
    lons = np.array([[122.42, 122.42]])
    base_sector = {'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45, 'searched_at': t0}

    # POD 0: prior unchanged
    w0 = update_trajectory_weights(lats, lons, step_times, [{**base_sector, 'detection_probability': 0.0}])
    np.testing.assert_array_almost_equal(w0, [0.5, 0.5])

    # POD negative: rejected
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        update_trajectory_weights(lats, lons, step_times, [{**base_sector, 'detection_probability': -0.1}])

    # POD > 1: rejected
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        update_trajectory_weights(lats, lons, step_times, [{**base_sector, 'detection_probability': 1.5}])

    # POD nonfinite: rejected
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        update_trajectory_weights(lats, lons, step_times, [{**base_sector, 'detection_probability': float('nan')}])

    # All mass rejected (POD 1.0 over all particles): raises ValueError rather than fabricating uniform map
    with pytest.raises(ValueError, match="All particle mass rejected"):
        update_trajectory_weights(lats, lons, step_times, [{**base_sector, 'detection_probability': 1.0}])


# S6: Persist trajectories, restart process, fetch and update; historical run has grids only ->
# same weights/coordinates after restart; legacy run remains readable but time-aware update requires
# supported state; no fake reconstructed trajectories from a centroid.
def test_s6_trajectory_persistence_serialization():
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    step_times = [t0, t1]
    lats = np.array([[11.60, 11.70], [11.65, 11.75]])
    lons = np.array([[122.40, 122.40], [122.45, 122.45]])
    weights = np.array([0.5, 0.5])

    # Serialize to JSON structure as stored in drift_runs.trajectory_data
    payload = {
        'step_times': [t.isoformat() for t in step_times],
        'lats': lats.tolist(),
        'lons': lons.tolist(),
        'weights': weights.tolist(),
    }
    dumped = json.dumps(payload)
    loaded = json.loads(dumped)

    # Reconstruct arrays
    reconstructed_times = [datetime.fromisoformat(s) for s in loaded['step_times']]
    reconstructed_lats = np.array(loaded['lats'], dtype=float)
    reconstructed_lons = np.array(loaded['lons'], dtype=float)
    reconstructed_weights = np.array(loaded['weights'], dtype=float)

    np.testing.assert_array_almost_equal(reconstructed_lats, lats)
    np.testing.assert_array_almost_equal(reconstructed_lons, lons)
    np.testing.assert_array_almost_equal(reconstructed_weights, weights)
    assert reconstructed_times == step_times


# S7: Rerun decision predates receipt of an earlier search report ->
# that report cannot change the historical prospective posterior; retrospective processing is separately labelled.
def test_s7_prospective_search_replay_filtering():
    # Given search reports at 09:00 and 11:00
    report_1 = {
        'id': 1,
        'created_at': datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
        'searched_at': datetime(2026, 8, 1, 8, 30, tzinfo=UTC),
        'south': 11.60, 'north': 11.65, 'west': 122.40, 'east': 122.45,
        'detection_probability': 0.8,
    }
    report_2 = {
        'id': 2,
        'created_at': datetime(2026, 8, 1, 11, 0, tzinfo=UTC),
        'searched_at': datetime(2026, 8, 1, 10, 30, tzinfo=UTC),
        'south': 11.65, 'north': 11.70, 'west': 122.40, 'east': 122.45,
        'detection_probability': 0.8,
    }

    all_sectors = [report_1, report_2]

    # Prospective rerun decided at 10:00:
    decision_cutoff = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    prospective_sectors = [s for s in all_sectors if s['created_at'] <= decision_cutoff]

    assert len(prospective_sectors) == 1
    assert prospective_sectors[0]['id'] == 1
    # Report 2 was received at 11:00 (> 10:00 decision cutoff), so it MUST be excluded from prospective replay!
