from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import asyncpg
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.ai import environment
from app.ai.current_field import count_nearby_fresh_buoys, create_current_field_factory
from app.ai.drift import MODEL_VERSION, ObjectClass, _to_xy, predict_drift
from app.ai.search import (
    contours_from_grid,
    grid_from_trajectories,
    recommend_next_area,
    update_posterior,
    update_trajectory_weights,
)
from app.audit import record_audit_event
from app.auth import require_responder_roles
from app.db import get_pool

router = APIRouter(prefix='/api/ai/drift', tags=['drift'])

# Reasons stored on `incidents.abnormal_reason` for a real, responder-opened
# case. Unlike the simulator's abnormal_reason values (capsize,
# adverse_weather, ...), these never drive object-class selection - a real
# case always carries its own `object_class`, chosen explicitly by the
# responder at open time (docs/40 Phase 1 item 4).
SOS_OPEN_REASON = 'manual_sos_confirmed'
ANOMALY_OPEN_REASON = 'anomaly_escalated'

_RUN_COLUMNS = '''
    id, run_number, object_class, forecast_hours, model_version, computed_at, computed_by,
    environmental_status, insufficiency_reason, observed_coverage,
    current_max_age_seconds, nearby_buoy_count, wind_source, wind_degraded,
    max_wind_age_seconds, prior_grid, posterior_grid, trajectory_data
'''

# Responder-approved detection-probability presets (docs/40 Phase 3 item 2).
# Approved by the project owner (Lenard) on 2026-08-30 alongside the Phase 2
# environmental policy - see docs/05_PUBLIC_API.md "Drift prediction and
# search re-tasking". The UI submits one of these named presets, never a
# free-form probability, and none reaches 1.0 - a search is never perfect.
DETECTION_PRESETS: dict[str, float] = {
    'poor': 0.3,
    'moderate': 0.6,
    'good': 0.9,
}
DETECTION_METHOD_LABELS: dict[str, str] = {
    'poor': 'Poor visibility / air search only',
    'moderate': 'Daylight surface vessel search',
    'good': 'Good conditions, multi-asset close pattern',
}


class SectorReportRequest(BaseModel):
    """The protected search-sector report contract (docs/40 Phase 3 item 1).

    A responder draws a rectangle on the map - the backend converts it to
    the grid's local metre space, not the other way around. `run_number` is
    whatever the client last saw from GET /incident/{id}: the server rejects
    a report against a run that has since been superseded by a rerun.
    """

    run_number: int = Field(..., ge=1)
    south: float = Field(..., ge=-90, le=90)
    west: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    method: Literal['poor', 'moderate', 'good']
    idempotency_key: str = Field(..., min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=280)
    searched_at: datetime | None = None
    search_start_at: datetime | None = None
    search_end_at: datetime | None = None
    detection_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    dependent: bool = False

    @model_validator(mode='after')
    def _validate_rectangle(self) -> SectorReportRequest:
        if self.north <= self.south:
            raise ValueError('north must be greater than south')
        if self.east <= self.west:
            raise ValueError('east must be greater than west')
        if (
            self.search_start_at is not None
            and self.search_end_at is not None
            and self.search_end_at < self.search_start_at
        ):
            raise ValueError('search_end_at must be >= search_start_at')
        return self


def _resolved_object_class(row) -> ObjectClass:
    stored = row['object_class']
    if stored:
        return ObjectClass(stored)
    # Legacy synthetic rows predating this column fall back to the old
    # heuristic derived from abnormal_reason.
    if str(row['abnormal_reason']) in {'capsize', 'adverse_weather'}:
        return ObjectClass.swamped_banca
    return ObjectClass.intact_hull_adrift


def _case_state(row) -> str:
    if row['cancelled_at'] is not None:
        return 'cancelled'
    if row['resolved_at'] is not None:
        return 'resolved'
    return 'confirmed'


def _source_type(row) -> str:
    if row['source_sos_event_id'] is not None:
        return 'sos'
    if row['source_anomaly_case_id'] is not None:
        return 'anomaly'
    return 'synthetic'


def _grid(value) -> dict | None:
    if value is None:
        return None
    return json.loads(value) if isinstance(value, str) else value


async def _fetch_sectors(pool, incident_id: int) -> list[dict[str, object]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            'SELECT x_min_m, x_max_m, y_min_m, y_max_m, detection_probability, searched_at, '
            'method, reported_by, notes, south, west, north, east, search_start_at, search_end_at, '
            'dependent, is_unassimilated, unassimilated_reason '
            'FROM search_sectors WHERE incident_id = $1 ORDER BY searched_at ASC, id ASC',
            incident_id,
        )
    return [
        {
            'x_min_m': float(row['x_min_m']) if row.get('x_min_m') is not None else 0.0,
            'x_max_m': float(row['x_max_m']) if row.get('x_max_m') is not None else 0.0,
            'y_min_m': float(row['y_min_m']) if row.get('y_min_m') is not None else 0.0,
            'y_max_m': float(row['y_max_m']) if row.get('y_max_m') is not None else 0.0,
            'south': float(row['south']) if row.get('south') is not None else None,
            'west': float(row['west']) if row.get('west') is not None else None,
            'north': float(row['north']) if row.get('north') is not None else None,
            'east': float(row['east']) if row.get('east') is not None else None,
            'detection_probability': float(row['detection_probability']),
            'searched_at': (
                row['searched_at'].isoformat()
                if hasattr(row['searched_at'], 'isoformat')
                else str(row['searched_at'])
            ),
            'search_start_at': (
                row['search_start_at'].isoformat()
                if hasattr(row.get('search_start_at'), 'isoformat')
                else (str(row['search_start_at']) if row.get('search_start_at') else None)
            ),
            'search_end_at': (
                row['search_end_at'].isoformat()
                if hasattr(row.get('search_end_at'), 'isoformat')
                else (str(row['search_end_at']) if row.get('search_end_at') else None)
            ),
            # Only present on a Phase 3 protected report; a legacy/demo
            # sector (app/demo/scenarios.py) leaves these NULL.
            'method': row['method'],
            'method_label': DETECTION_METHOD_LABELS.get(row['method']),
            'reported_by': row['reported_by'],
            'notes': row['notes'],
            'dependent': bool(row.get('dependent', False)),
            'is_unassimilated': bool(row.get('is_unassimilated', False)),
            'unassimilated_reason': row.get('unassimilated_reason'),
        }
        for row in rows
    ]


async def _latest_run(pool, incident_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            f'SELECT {_RUN_COLUMNS} FROM drift_runs WHERE incident_id = $1 '
            'ORDER BY run_number DESC LIMIT 1',
            incident_id,
        )


async def _get_or_compute_prior(
    pool, incident_id: int, row, current_fn, forecast_hours: float,
) -> dict:
    """Legacy/demo-fixture path only (docs/40 Phase 1 item 4): loads the
    incidents.prior_grid cache, or computes and caches it. Never used for a
    real case - those always have a drift_runs row by the time this could be
    reached (see record_searched_sector).
    """
    prior_grid = row['prior_grid']
    if prior_grid is not None:
        return json.loads(prior_grid) if isinstance(prior_grid, str) else prior_grid

    result = predict_drift(
        last_lat=float(row['last_contact_lat']),
        last_lon=float(row['last_contact_lon']),
        observed_at=row['last_contact_at'],
        object_class=_resolved_object_class(row),
        forecast_hours=forecast_hours,
        current_vector_fn=current_fn,
    )
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE incidents SET prior_grid = $1, posterior_grid = $1 WHERE id = $2',
            json.dumps(result.grid),
            incident_id,
        )
    return result.grid


async def _compute_and_persist_run(
    pool, incident_id: int, run_number: int, *,
    last_lat: float, last_lon: float, last_at: datetime,
    object_class: ObjectClass, forecast_hours: float, actor: str,
    initial_spread_m: float = 250.0,
    decision_cutoff_at: datetime | None = None,
) -> environment.EnvironmentAssessment:
    """The production quality-gated prediction (docs/40 Phase 2 items 2-3).

    Computes at most one particle simulation, assesses it against the
    owner-approved policy in app.ai.environment, and persists exactly one
    immutable drift_runs row - a contour only when the inputs are
    sufficient, `insufficient_environmental_data` (with its diagnostic
    snapshot) otherwise. Never falls back to the synthetic current field.
    """
    cutoff = decision_cutoff_at or datetime.now(UTC)
    nearby = await count_nearby_fresh_buoys(
        pool, last_lat, last_lon, last_at, include_synthetic=False, max_depth_m=2.5,
    )
    assessment = environment.assess_geometry(nearby)
    prior_grid = posterior_grid = None
    result = None
    trajectory_data = None

    if assessment is None:
        current_fn = await create_current_field_factory(
            pool, include_synthetic=False, allow_synthetic=False, as_of=cutoff, max_depth_m=2.5,
        )
        result = predict_drift(
            last_lat=last_lat,
            last_lon=last_lon,
            observed_at=last_at,
            object_class=object_class,
            forecast_hours=forecast_hours,
            current_vector_fn=current_fn,
            initial_spread_m=initial_spread_m,
            enable_stranding=True,
            record_trajectories=True,
        )
        coverage = getattr(current_fn, 'observation_fraction', 0.0)
        assessment = environment.assess_result(nearby, coverage, result)
        if assessment.sufficient and result is not None:
            prior_grid = result.grid
            # Replay all previous search sectors chronologically for this incident (Task 3.4 & S7)
            async with pool.acquire() as conn:
                if decision_cutoff_at is not None:
                    existing_sectors = await conn.fetch(
                        'SELECT x_min_m, x_max_m, y_min_m, y_max_m, south, west, north, east, '
                        'detection_probability, searched_at, search_start_at, search_end_at, '
                        'dependent, is_unassimilated '
                        'FROM search_sectors WHERE incident_id = $1 AND created_at <= $2 '
                        'ORDER BY searched_at ASC, id ASC',
                        incident_id, decision_cutoff_at,
                    )
                else:
                    existing_sectors = await conn.fetch(
                        'SELECT x_min_m, x_max_m, y_min_m, y_max_m, south, west, north, east, '
                        'detection_probability, searched_at, search_start_at, search_end_at, '
                        'dependent, is_unassimilated '
                        'FROM search_sectors WHERE incident_id = $1 '
                        'ORDER BY searched_at ASC, id ASC',
                        incident_id,
                    )

            if result.trajectories:
                step_times = [step['at'] for step in result.trajectories]
                n_particles = len(result.trajectories[0]['lat'])
                traj_lats = np.array([step['lat'] for step in result.trajectories])
                traj_lons = np.array([step['lon'] for step in result.trajectories])
                weights = np.ones(n_particles, dtype=float) / n_particles

                if existing_sectors:
                    sec_dicts = [
                        {
                            'south': float(s['south']) if s.get('south') is not None else None,
                            'north': float(s['north']) if s.get('north') is not None else None,
                            'west': float(s['west']) if s.get('west') is not None else None,
                            'east': float(s['east']) if s.get('east') is not None else None,
                            'x_min_m': float(s['x_min_m']) if s.get('x_min_m') is not None else None,
                            'x_max_m': float(s['x_max_m']) if s.get('x_max_m') is not None else None,
                            'y_min_m': float(s['y_min_m']) if s.get('y_min_m') is not None else None,
                            'y_max_m': float(s['y_max_m']) if s.get('y_max_m') is not None else None,
                            'detection_probability': float(s['detection_probability']),
                            'searched_at': s.get('searched_at'),
                            'search_start_at': s.get('search_start_at'),
                            'search_end_at': s.get('search_end_at'),
                            'dependent': bool(s.get('dependent', False)),
                            'is_unassimilated': bool(s.get('is_unassimilated', False)),
                            'origin_lat': last_lat,
                            'origin_lon': last_lon,
                        }
                        for s in existing_sectors
                    ]
                    try:
                        weights = update_trajectory_weights(traj_lats, traj_lons, step_times, sec_dicts, weights)
                        posterior_grid = grid_from_trajectories(
                            traj_lats, traj_lons, weights, origin_lat=last_lat, origin_lon=last_lon,
                            reference_grid=prior_grid,
                        )
                    except Exception:
                        posterior_grid = result.grid
                else:
                    posterior_grid = result.grid

                trajectory_data = json.dumps({
                    'step_times': step_times,
                    'lats': traj_lats.tolist(),
                    'lons': traj_lons.tolist(),
                    'weights': weights.tolist(),
                })
            else:
                posterior_grid = result.grid

    afloat_count = None
    stranded_count = None
    outside_domain_count = None
    support_lost_at = None
    supported_horizon_hours = None
    if assessment.sufficient and result is not None:
        stranded_count = result.stranded_count
        afloat_count = max(0, 2000 - stranded_count)
        outside_domain_count = 0
        if result.support_lost_at:
            try:
                support_lost_at = datetime.fromisoformat(result.support_lost_at)
                supported_horizon_hours = max(0.0, (support_lost_at - last_at).total_seconds() / 3600.0)
            except (ValueError, TypeError):
                pass
        else:
            supported_horizon_hours = forecast_hours
    elif not assessment.sufficient:
        supported_horizon_hours = 0.0

    async with pool.acquire() as conn:
        await conn.execute(
            '''
            INSERT INTO drift_runs (
              incident_id, run_number, object_class, forecast_hours, model_version,
              computed_by, environmental_status, insufficiency_reason,
              observed_coverage, current_max_age_seconds, nearby_buoy_count,
              wind_source, wind_degraded, max_wind_age_seconds,
              prior_grid, posterior_grid,
              decision_cutoff_at, is_retrospective, supported_horizon_hours,
              support_lost_at, afloat_count, stranded_count, outside_domain_count,
              trajectory_data
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24)
            ''',
            incident_id, run_number, object_class.value, forecast_hours, MODEL_VERSION,
            actor, 'ok' if assessment.sufficient else 'insufficient_environmental_data',
            assessment.reason, assessment.observed_coverage, assessment.current_max_age_seconds,
            assessment.nearby_buoy_count, assessment.wind_source, assessment.wind_degraded,
            assessment.max_wind_age_seconds,
            json.dumps(prior_grid) if prior_grid is not None else None,
            json.dumps(posterior_grid) if posterior_grid is not None else None,
            cutoff,
            False,
            supported_horizon_hours,
            support_lost_at,
            afloat_count,
            stranded_count,
            outside_domain_count,
            trajectory_data,
        )
    return assessment


@router.get('/incidents')
async def incidents() -> list[dict[str, object]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT id, vessel_id, last_contact_at, last_contact_lat, last_contact_lon,
                   abnormal_reason, object_class, is_synthetic,
                   source_sos_event_id, source_anomaly_case_id,
                   resolved_at, cancelled_at
            FROM incidents
            ORDER BY last_contact_at DESC, id DESC
            '''
        )
    return [
        {
            'id': row['id'],
            'vessel_id': row['vessel_id'],
            'last_contact_at': row['last_contact_at'].isoformat(),
            'last_contact_lat': float(row['last_contact_lat']),
            'last_contact_lon': float(row['last_contact_lon']),
            'abnormal_reason': row['abnormal_reason'],
            'object_class': _resolved_object_class(row).value,
            'is_synthetic': row['is_synthetic'],
            'source_type': _source_type(row),
            'case_state': _case_state(row),
        }
        for row in rows
    ]


class OpenCaseRequest(BaseModel):
    """Opens a protected drift/search case from a confirmed source.

    `source_type`/`source_id` name the exact confirmed event this case is
    derived from - a case can never be opened from a bare reason string.
    `object_class` is a required, explicit responder choice; it is never
    inferred from the source's own text (docs/40 Phase 1 item 4).
    """

    source_type: Literal['sos', 'anomaly']
    source_id: int
    object_class: ObjectClass
    forecast_hours: float = Field(24.0, gt=0, le=72)
    datum_at: datetime | None = None
    scenario: str | None = Field(default='standard_drift')
    initial_uncertainty_m: float | None = Field(default=250.0, ge=10.0, le=50000.0)


async def _sos_case_inputs(
    conn: asyncpg.Connection,
    source_id: int,
    override_datum_at: datetime | None = None,
) -> tuple[str, float, float, datetime, dict[str, Any]]:
    row = await conn.fetchrow(
        '''
        SELECT vessel_id, latitude, longitude, created_at, client_ts, acknowledged_at, resolved_at,
               fix_acquired_at, fix_accuracy_m
        FROM sos_events WHERE id = $1
        ''',
        source_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail='no such SOS event')
    if row['acknowledged_at'] is None:
        raise HTTPException(status_code=409, detail='SOS has not been confirmed by a responder')
    if row['resolved_at'] is not None:
        raise HTTPException(status_code=409, detail='SOS is already resolved')
    if row['latitude'] is None or row['longitude'] is None:
        raise HTTPException(status_code=422, detail='SOS has no last-known position')

    receipt_at = row['created_at']
    datum_source = 'receipt_time'
    delay_seconds = 0.0

    if override_datum_at is not None:
        datum_at = override_datum_at
        datum_source = 'responder_override'
        delay_seconds = max(0.0, (receipt_at - datum_at).total_seconds())
    else:
        fix_acquired_at = None
        try:
            fix_acquired_at = row['fix_acquired_at']
        except (KeyError, TypeError, IndexError):
            fix_acquired_at = None

        if fix_acquired_at is not None:
            datum_at = fix_acquired_at
            datum_source = 'gnss_fix'
            delay_seconds = max(0.0, (receipt_at - datum_at).total_seconds())
        else:
            client_ts = None
            try:
                client_ts = row['client_ts']
            except (KeyError, TypeError, IndexError):
                client_ts = None

            if client_ts is not None and client_ts > 0:
                try:
                    client_dt = datetime.fromtimestamp(client_ts, tz=UTC)
                    # Handset transmission time is distinct from an authenticated GNSS fix
                    if client_dt <= receipt_at + timedelta(minutes=5):
                        datum_at = client_dt
                        datum_source = 'client_send'
                        delay_seconds = max(0.0, (receipt_at - client_dt).total_seconds())
                    else:
                        datum_at = receipt_at
                        datum_source = 'receipt_time'
                except (ValueError, OverflowError, OSError):
                    datum_at = receipt_at
                    datum_source = 'receipt_time'
            else:
                datum_at = receipt_at
                datum_source = 'receipt_time'

    datum_meta = {
        'datum_at': datum_at.isoformat(),
        'receipt_at': receipt_at.isoformat(),
        'datum_source': datum_source,
        'delay_seconds': delay_seconds,
    }
    try:
        fix_acc = row['fix_accuracy_m']
        if fix_acc is not None:
            datum_meta['fix_accuracy_m'] = float(fix_acc)
    except (KeyError, TypeError, IndexError):
        pass

    return row['vessel_id'], float(row['latitude']), float(row['longitude']), datum_at, datum_meta


async def _anomaly_case_inputs(
    conn: asyncpg.Connection,
    source_id: int,
    override_datum_at: datetime | None = None,
) -> tuple[str, float, float, datetime, dict[str, Any]]:
    row = await conn.fetchrow(
        '''
        SELECT vessel_id, trip_id, escalated_at, resolved_at
        FROM anomaly_cases WHERE id = $1
        ''',
        source_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail='no such anomaly case')
    if row['escalated_at'] is None:
        raise HTTPException(status_code=409, detail='anomaly case has not been escalated by a responder')
    if row['resolved_at'] is not None:
        raise HTTPException(status_code=409, detail='anomaly case is already resolved')

    position = await conn.fetchrow(
        '''
        SELECT latitude, longitude, observed_at FROM buoy_contacts
        WHERE vessel_id = $1 AND trip_id = $2
          AND latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY observed_at DESC LIMIT 1
        ''',
        row['vessel_id'], row['trip_id'],
    )
    if position is None:
        raise HTTPException(status_code=422, detail='no last-known position for this vessel/trip')

    observed_at = position['observed_at']
    datum_at = override_datum_at or observed_at
    datum_meta = {
        'datum_at': datum_at.isoformat(),
        'receipt_at': observed_at.isoformat(),
        'datum_source': 'responder_override' if override_datum_at else 'buoy_contact',
        'delay_seconds': 0.0,
    }
    return row['vessel_id'], float(position['latitude']), float(position['longitude']), datum_at, datum_meta


@router.post('/cases')
async def open_case(body: OpenCaseRequest, user: dict = require_responder_roles) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        if body.source_type == 'sos':
            vessel_id, lat, lon, at, datum_meta = await _sos_case_inputs(conn, body.source_id, body.datum_at)
            reason, sos_id, anomaly_id = SOS_OPEN_REASON, body.source_id, None
        else:
            vessel_id, lat, lon, at, datum_meta = await _anomaly_case_inputs(conn, body.source_id, body.datum_at)
            reason, sos_id, anomaly_id = ANOMALY_OPEN_REASON, None, body.source_id

        try:
            row = await conn.fetchrow(
                '''
                INSERT INTO incidents (
                  vessel_id, last_contact_at, last_contact_lat, last_contact_lon,
                  reported_missing_at, abnormal_reason, object_class,
                  source_sos_event_id, source_anomaly_case_id, opened_by,
                  is_synthetic
                ) VALUES ($1, $2, $3, $4, $2, $5, $6, $7, $8, $9, FALSE)
                RETURNING id
                ''',
                vessel_id, at, lat, lon, reason, body.object_class.value,
                sos_id, anomaly_id, user.get('email') or 'unknown',
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(
                status_code=409, detail='a case already exists for this source',
            ) from exc

        # A protected source only (docs/40) - a case opened through this
        # route is never synthetic, so is_demo is always False here.
        await record_audit_event(
            conn,
            actor=user,
            action='drift.open',
            resource_type='drift_incident',
            resource_id=row['id'],
            outcome='created',
            is_demo=False,
            metadata={
                'source_type': body.source_type,
                'object_class': body.object_class.value,
                'scenario': body.scenario,
                'datum_meta': datum_meta,
            },
        )

    incident_id = row['id']
    actor = user.get('email') or 'unknown'
    assessment = await _compute_and_persist_run(
        pool, incident_id, 1,
        last_lat=lat, last_lon=lon, last_at=at,
        object_class=body.object_class, forecast_hours=body.forecast_hours,
        actor=actor,
        initial_spread_m=body.initial_uncertainty_m or 250.0,
    )

    return {
        'id': incident_id,
        'vessel_id': vessel_id,
        'object_class': body.object_class.value,
        'case_state': 'confirmed',
        'source_type': body.source_type,
        'run_number': 1,
        'environmental_status': 'ok' if assessment.sufficient else 'insufficient_environmental_data',
        'insufficiency_reason': assessment.reason,
        'scenario': body.scenario,
        'datum_meta': datum_meta,
    }


@router.post('/cases/{incident_id}/rerun')
async def rerun_case(incident_id: int, user: dict = require_responder_roles) -> dict[str, object]:
    """An explicit, responder-only new drift run (docs/40 Phase 2 item 4).

    Appends a new numbered run rather than overwriting the current one, so a
    crew already acting on an earlier run's contours and search sectors is
    never silently redirected mid-search.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        incident = await conn.fetchrow(
            '''
            SELECT id, last_contact_at, last_contact_lat, last_contact_lon,
                   abnormal_reason, object_class, resolved_at, cancelled_at,
                   is_synthetic
            FROM incidents WHERE id = $1
            ''',
            incident_id,
        )
    if incident is None:
        raise HTTPException(status_code=404, detail='no such case')
    if incident['resolved_at'] is not None or incident['cancelled_at'] is not None:
        raise HTTPException(
            status_code=409, detail=f'case is {_case_state(incident)}; cannot start a new run',
        )

    latest = await _latest_run(pool, incident_id)
    if latest is None:
        raise HTTPException(
            status_code=409, detail='this case has no prior run to supersede',
        )

    next_run_number = latest['run_number'] + 1
    assessment = await _compute_and_persist_run(
        pool, incident_id, next_run_number,
        last_lat=float(incident['last_contact_lat']),
        last_lon=float(incident['last_contact_lon']),
        last_at=incident['last_contact_at'],
        object_class=_resolved_object_class(incident),
        forecast_hours=float(latest['forecast_hours']),
        actor=user.get('email') or 'unknown',
    )
    # _compute_and_persist_run manages its own connection (it also runs a
    # buoy-proximity query the caller doesn't otherwise need), so this audit
    # write is not in the same transaction as the drift_runs INSERT it
    # describes - it only fires after that insert is confirmed to have
    # succeeded, so it can never audit a run that was not actually persisted.
    async with pool.acquire() as conn, conn.transaction():
        await record_audit_event(
            conn,
            actor=user,
            action='drift.rerun',
            resource_type='drift_incident',
            resource_id=incident_id,
            outcome='created',
            is_demo=incident['is_synthetic'],
            metadata={'run_number': next_run_number},
        )
    return {
        'id': incident_id,
        'run_number': next_run_number,
        'environmental_status': 'ok' if assessment.sufficient else 'insufficient_environmental_data',
        'insufficiency_reason': assessment.reason,
    }


@router.post('/cases/{incident_id}/resolve')
async def resolve_case(incident_id: int, user: dict = require_responder_roles) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT resolved_at FROM incidents WHERE id = $1 FOR UPDATE', incident_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such case')
        was_already_resolved = prior['resolved_at'] is not None

        row = await conn.fetchrow(
            '''
            UPDATE incidents
               SET resolved_at = COALESCE(resolved_at, NOW()),
                   resolved_by = COALESCE(resolved_by, $2)
             WHERE id = $1
            RETURNING id, resolved_at, resolved_by, is_synthetic
            ''',
            incident_id, user.get('email') or 'unknown',
        )
        await record_audit_event(
            conn,
            actor=user,
            action='drift.resolve',
            resource_type='drift_incident',
            resource_id=row['id'],
            outcome='no_change' if was_already_resolved else 'updated',
            is_demo=row['is_synthetic'],
        )
    return {
        'ok': True,
        'id': row['id'],
        'resolved_at': row['resolved_at'].isoformat(),
        'resolved_by': row['resolved_by'],
    }


class CancelCaseRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=280)


@router.post('/cases/{incident_id}/cancel')
async def cancel_case(
    incident_id: int, payload: CancelCaseRequest, user: dict = require_responder_roles,
) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT cancelled_at FROM incidents WHERE id = $1 FOR UPDATE', incident_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such case')
        was_already_cancelled = prior['cancelled_at'] is not None

        row = await conn.fetchrow(
            '''
            UPDATE incidents
               SET cancelled_at = COALESCE(cancelled_at, NOW()),
                   cancelled_by = COALESCE(cancelled_by, $2),
                   cancelled_reason = COALESCE(cancelled_reason, $3)
             WHERE id = $1
            RETURNING id, cancelled_at, cancelled_by, cancelled_reason, is_synthetic
            ''',
            incident_id, user.get('email') or 'unknown', payload.reason,
        )
        # cancelled_reason is free text and never logged (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='drift.cancel',
            resource_type='drift_incident',
            resource_id=row['id'],
            outcome='no_change' if was_already_cancelled else 'updated',
            is_demo=row['is_synthetic'],
        )
    return {
        'ok': True,
        'id': row['id'],
        'cancelled_at': row['cancelled_at'].isoformat(),
        'cancelled_by': row['cancelled_by'],
        'cancelled_reason': row['cancelled_reason'],
    }


@router.get('/incident/{incident_id}')
async def incident_prediction(incident_id: int, forecast_hours: float = 24.0) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT id, vessel_id, last_contact_at, last_contact_lat, last_contact_lon,
                   abnormal_reason, object_class, true_track, is_synthetic,
                   prior_grid, posterior_grid,
                   source_sos_event_id, source_anomaly_case_id,
                   resolved_at, cancelled_at
            FROM incidents
            WHERE id = $1
            ''',
            incident_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail='incident not found')

    incident_summary = {
        'id': row['id'],
        'vessel_id': row['vessel_id'],
        'last_contact_at': row['last_contact_at'].isoformat(),
        'last_contact_lat': float(row['last_contact_lat']),
        'last_contact_lon': float(row['last_contact_lon']),
        'abnormal_reason': row['abnormal_reason'],
        'is_synthetic': row['is_synthetic'],
        'source_type': _source_type(row),
        'case_state': _case_state(row),
    }

    run = await _latest_run(pool, incident_id)

    if run is not None:
        # A real case: read the stored, immutable run. Never recompute on a
        # GET (docs/40 Phase 2 item 3) - a displayed prediction must always
        # belong to the same environmental inputs as its posterior.
        is_ok = run['environmental_status'] == 'ok'
        response: dict[str, object] = {
            'incident': incident_summary,
            'run_number': run['run_number'],
            'model_version': run['model_version'],
            'computed_at': run['computed_at'].isoformat(),
            'environmental_status': run['environmental_status'],
            'insufficiency_reason': run['insufficiency_reason'],
            'nearby_buoy_count': run['nearby_buoy_count'],
            'current_max_age_seconds': run['current_max_age_seconds'],
            'max_wind_age_seconds': run['max_wind_age_seconds'],
            'observation_fraction': (
                round(run['observed_coverage'], 4) if run['observed_coverage'] is not None else None
            ),
            'prediction': {
                'object_class': run['object_class'],
                'wind_source': run['wind_source'],
                'degraded': run['wind_degraded'],
            } if is_ok else None,
            'posterior_grid': _grid(run['posterior_grid']) if is_ok else None,
            'contours': contours_from_grid(_grid(run['posterior_grid'])) if is_ok else [],
            'next_area': recommend_next_area(_grid(run['posterior_grid'])) if is_ok else None,
            'search_sectors': await _fetch_sectors(pool, incident_id),
        }
        return response

    # Legacy/demo-fixture path (docs/40 Phase 1 item 4): the simulator and
    # the demo scenario engine still write incidents.prior_grid/
    # posterior_grid directly and never create a drift_runs row, so this
    # keeps their exact pre-Phase-2 behaviour unchanged.
    current_fn = await create_current_field_factory(pool)
    result = predict_drift(
        last_lat=float(row['last_contact_lat']),
        last_lon=float(row['last_contact_lon']),
        observed_at=row['last_contact_at'],
        object_class=_resolved_object_class(row),
        forecast_hours=forecast_hours,
        current_vector_fn=current_fn,
    )
    posterior_grid = _grid(row['posterior_grid']) or result.grid

    response = {
        'incident': incident_summary,
        'prediction': result.to_dict(),
        'posterior_grid': posterior_grid,
        'contours': contours_from_grid(posterior_grid),
        'search_sectors': await _fetch_sectors(pool, incident_id),
    }
    if row['is_synthetic']:
        response['ground_truth_track'] = _grid(row['true_track'])
    obs_frac = getattr(current_fn, 'observation_fraction', None)
    if obs_frac is not None:
        response['observation_fraction'] = round(obs_frac, 4)
    return response


def _rect_to_metres(
    south: float, west: float, north: float, east: float, origin_lat: float, origin_lon: float,
) -> tuple[float, float, float, float]:
    """Converts a map-space rectangle to the grid's local metre space
    (docs/40 Phase 3 item 1) - the backend does this conversion, not the
    responder. `_to_xy` computes x from the lon array and y from the lat
    array independently, so pairing south/north with west/east here is just
    a convenient way to get both edges from one call.
    """
    x, y = _to_xy(np.array([south, north]), np.array([west, east]), origin_lat, origin_lon)
    return float(x[0]), float(x[1]), float(y[0]), float(y[1])


def _grid_bounds_m(grid_dict: dict) -> tuple[float, float, float, float]:
    x_edges = grid_dict['x_edges_m']
    y_edges = grid_dict['y_edges_m']
    return float(x_edges[0]), float(x_edges[-1]), float(y_edges[0]), float(y_edges[-1])


async def record_legacy_search_sector(
    incident_id: int, *,
    x_min_m: float, x_max_m: float, y_min_m: float, y_max_m: float, detection_probability: float,
) -> dict[str, object]:
    """The pre-Phase-3 raw metre-offset primitive, kept only for the
    synthetic/demo scenario engine (app/demo/scenarios.py), which calls this
    directly in-process rather than through the protected HTTP contract
    below - "preserve existing synthetic sectors and replay ability" (docs/40
    Phase 3 item 3). A real case never reaches this function.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT id, last_contact_at, last_contact_lat, last_contact_lon,
                   abnormal_reason, object_class, prior_grid, posterior_grid
            FROM incidents WHERE id = $1
            ''',
            incident_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail='incident not found')

    current_fn = await create_current_field_factory(pool)
    prior_grid = row['prior_grid']
    prior_grid = _grid(prior_grid) if prior_grid is not None else await _get_or_compute_prior(
        pool, incident_id, row, current_fn, 24.0,
    )
    posterior_grid = _grid(row['posterior_grid']) or prior_grid
    sector = {
        'x_min_m': x_min_m, 'x_max_m': x_max_m, 'y_min_m': y_min_m, 'y_max_m': y_max_m,
        'detection_probability': detection_probability,
    }
    updated_grid = update_posterior(posterior_grid, [sector])

    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE incidents SET posterior_grid = $1 WHERE id = $2',
            json.dumps(updated_grid), incident_id,
        )
        await conn.execute(
            '''
            INSERT INTO search_sectors
                (incident_id, x_min_m, x_max_m, y_min_m, y_max_m, detection_probability)
            VALUES ($1, $2, $3, $4, $5, $6)
            ''',
            incident_id, x_min_m, x_max_m, y_min_m, y_max_m, detection_probability,
        )

    return {
        'posterior_grid': updated_grid,
        'contours': contours_from_grid(updated_grid),
        'search_sectors': await _fetch_sectors(pool, incident_id),
    }


@router.post('/incident/{incident_id}/searched')
async def record_searched_sector(
    incident_id: int, body: SectorReportRequest, user: dict = require_responder_roles,
) -> dict[str, object]:
    """The protected search-sector report contract (docs/40 Phase 3).

    Real cases only - a case with no drift run yet (demo/synthetic, or one
    that predates Phase 2) cannot report through this route at all. Atomic:
    locks the case and its current run, rejects a stale/superseded run,
    deduplicates the idempotency key, applies the negative-evidence update
    exactly once, and appends the audit record - all in one transaction.
    """
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        incident = await conn.fetchrow(
            'SELECT id, resolved_at, cancelled_at, is_synthetic FROM incidents WHERE id = $1 FOR UPDATE',
            incident_id,
        )
        if incident is None:
            raise HTTPException(status_code=404, detail='incident not found')
        if incident['resolved_at'] is not None or incident['cancelled_at'] is not None:
            raise HTTPException(
                status_code=409,
                detail=f'case is {_case_state(incident)}; cannot record a new search',
            )

        run = await conn.fetchrow(
            f'SELECT {_RUN_COLUMNS} FROM drift_runs WHERE incident_id = $1 '
            'ORDER BY run_number DESC LIMIT 1 FOR UPDATE',
            incident_id,
        )
        if run is None:
            raise HTTPException(
                status_code=409, detail='this case has no run yet; open or rerun it first',
            )
        if run['run_number'] != body.run_number:
            raise HTTPException(
                status_code=409,
                detail=f'stale run: case is now on run {run["run_number"]}; reload before reporting',
            )
        if run['environmental_status'] != 'ok':
            raise HTTPException(
                status_code=409,
                detail='insufficient environmental data; no search field to update',
            )

        posterior_grid = _grid(run['posterior_grid'])

        trajectory_data_raw = run.get('trajectory_data')
        if trajectory_data_raw is None:
            # Check S6: historical run has grids only, cannot update time-aligned search
            raise HTTPException(
                status_code=409,
                detail='historical run does not contain trajectory data; cannot assimilate time-aligned search',
            )

        traj_dict = json.loads(trajectory_data_raw) if isinstance(trajectory_data_raw, str) else trajectory_data_raw
        step_times = traj_dict['step_times']
        traj_lats = np.array(traj_dict['lats'], dtype=float)
        traj_lons = np.array(traj_dict['lons'], dtype=float)
        weights = np.array(traj_dict['weights'], dtype=float)

        existing = await conn.fetchrow(
            'SELECT id FROM search_sectors WHERE incident_id = $1 AND idempotency_key = $2',
            incident_id, body.idempotency_key,
        )
        if existing is not None:
            # A retry of the same report: return the current state rather
            # than applying the negative evidence a second time.
            await record_audit_event(
                conn,
                actor=user,
                action='drift.search_sector_report',
                resource_type='drift_incident',
                resource_id=incident_id,
                outcome='duplicate',
                correlation_key=body.idempotency_key,
                is_demo=incident['is_synthetic'],
                metadata={'method': body.method, 'run_number': body.run_number},
            )
            return {
                'posterior_grid': posterior_grid,
                'contours': contours_from_grid(posterior_grid),
                'next_area': recommend_next_area(posterior_grid),
                'search_sectors': await _fetch_sectors(pool, incident_id),
                'duplicate': True,
            }

        # Check search occurrence timing (Task 3.1 & S2)
        searched_at = body.searched_at
        if searched_at is None and body.search_start_at is None:
            searched_at = datetime.now(UTC)
        elif searched_at is not None and searched_at.tzinfo is None:
            raise HTTPException(status_code=422, detail='searched_at must be timezone-aware')
        if body.search_start_at is not None and body.search_start_at.tzinfo is None:
            raise HTTPException(status_code=422, detail='search_start_at must be timezone-aware')
        if body.search_end_at is not None and body.search_end_at.tzinfo is None:
            raise HTTPException(status_code=422, detail='search_end_at must be timezone-aware')

        # Check detection probability (Task 3.5 & S5)
        if body.detection_probability is not None:
            pod = float(body.detection_probability)
            if not np.isfinite(pod) or pod < 0.0 or pod > 1.0:
                raise HTTPException(status_code=422, detail='detection_probability must be between 0.0 and 1.0')
        else:
            pod = DETECTION_PRESETS[body.method]

        origin = posterior_grid['origin']
        x_min, x_max, y_min, y_max = _rect_to_metres(
            body.south, body.west, body.north, body.east, origin['lat'], origin['lon'],
        )
        grid_x_min, grid_x_max, grid_y_min, grid_y_max = _grid_bounds_m(posterior_grid)
        if x_max <= grid_x_min or x_min >= grid_x_max or y_max <= grid_y_min or y_min >= grid_y_max:
            raise HTTPException(
                status_code=422, detail='searched rectangle does not overlap the search grid',
            )

        sector_entry = {
            'south': body.south,
            'north': body.north,
            'west': body.west,
            'east': body.east,
            'searched_at': searched_at,
            'search_start_at': body.search_start_at,
            'search_end_at': body.search_end_at,
            'detection_probability': pod,
            'dependent': body.dependent,
        }

        try:
            updated_weights = update_trajectory_weights(
                traj_lats, traj_lons, step_times, [sector_entry], weights=weights,
            )
        except ValueError as err:
            err_msg = str(err)
            raise HTTPException(status_code=422, detail=err_msg) from err

        updated_grid = grid_from_trajectories(
            traj_lats, traj_lons, updated_weights, origin_lat=origin['lat'], origin_lon=origin['lon'],
            reference_grid=posterior_grid,
        )
        traj_dict['weights'] = updated_weights.tolist()

        await conn.execute(
            'UPDATE drift_runs SET posterior_grid = $1, trajectory_data = $2 WHERE id = $3',
            json.dumps(updated_grid), json.dumps(traj_dict), run['id'],
        )
        await conn.execute(
            '''
            INSERT INTO search_sectors
                (incident_id, x_min_m, x_max_m, y_min_m, y_max_m, detection_probability,
                 run_id, reported_by, method, notes, idempotency_key,
                 south, west, north, east, searched_at, search_start_at, search_end_at,
                 dependent, is_unassimilated, unassimilated_reason)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21)
            ''',
            incident_id, x_min, x_max, y_min, y_max, pod,
            run['id'], user.get('email') or 'unknown', body.method, body.notes, body.idempotency_key,
            body.south, body.west, body.north, body.east, searched_at, body.search_start_at, body.search_end_at,
            body.dependent, False, None,
        )

        # Never the searched rectangle or free-text notes (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='drift.search_sector_report',
            resource_type='drift_incident',
            resource_id=incident_id,
            outcome='updated',
            correlation_key=body.idempotency_key,
            is_demo=incident['is_synthetic'],
            metadata={'method': body.method, 'run_number': body.run_number},
        )

    return {
        'posterior_grid': updated_grid,
        'contours': contours_from_grid(updated_grid),
        'next_area': recommend_next_area(updated_grid),
        'search_sectors': await _fetch_sectors(pool, incident_id),
        'duplicate': False,
    }
