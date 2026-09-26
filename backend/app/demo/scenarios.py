from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

from app.db import get_pool
from app.simulation.generator import _event_pressure_at, _offset, _simulate_drift_track


@dataclass
class DemoState:
    scenario: str | None = None
    beat: int = -1
    fired: set[int] = field(default_factory=set)
    run_id: str | None = None
    updated_at: datetime | None = None
    target_vessel_id: str | None = None
    incident_id: int | None = None

    def response(self) -> dict[str, object]:
        return {
            'scenario': self.scenario,
            'beat': self.beat,
            'fired': sorted(self.fired),
            'run_id': self.run_id,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'target_vessel_id': self.target_vessel_id,
            'incident_id': self.incident_id,
        }


@dataclass(frozen=True)
class BeatDefinition:
    index: int
    label: str
    event_age_minutes: int


BEATS = (
    BeatDefinition(0, 'Baseline', 0),
    BeatDefinition(1, 'Pressure falls', 60),
    BeatDefinition(2, 'Zones escalate', 75),
    BeatDefinition(3, 'RETURN NOW', 90),
    BeatDefinition(4, 'Boat overdue', 90),
    BeatDefinition(5, 'SOS + drift', 90),
    BeatDefinition(6, 'Ack + re-task', 90),
)

SCENARIOS = {'squall-fleet', 'clear-day'}
SQUALL_CENTER = (11.6892, 122.3667)
SQUALL_BEARING_DEG = 72.0
SQUALL_SPEED_KPH = 28.0
SQUALL_PRESSURE_DROP_HPA = 5.0
SQUALL_RISE_MINUTES = 45
SQUALL_HOLD_MINUTES = 75
SQUALL_ORIGIN_DISTANCE_KM = 18.0

_state = DemoState()


def get_state() -> DemoState:
    return _state


def beat_definitions() -> tuple[BeatDefinition, ...]:
    return BEATS


def _beat(index: int) -> BeatDefinition:
    if index < 0 or index >= len(BEATS):
        raise ValueError('beat must be between 0 and 6')
    return BEATS[index]


def _stable_noise(buoy_id: str, observed_at: datetime) -> float:
    key = f'{buoy_id}:{observed_at.isoformat()}'.encode()
    value = int.from_bytes(hashlib.sha256(key).digest()[:4], 'big') / 2**32
    return (value * 2.0 - 1.0) * 0.16


def _baseline_pressure(buoy_id: str, observed_at: datetime) -> float:
    digest = hashlib.sha256(buoy_id.encode('utf-8')).digest()
    phase = int.from_bytes(digest[:4], 'big') / 2**32 * 2.0 * math.pi
    t_hours = observed_at.timestamp() / 3600.0
    diurnal = 1.15 * math.sin((2.0 * math.pi * t_hours / 24.0) + phase)
    semi_diurnal = 0.35 * math.sin((2.0 * math.pi * t_hours / 12.42) + phase / 2.5)
    slow_trend = 0.28 * math.sin((2.0 * math.pi * t_hours / (24.0 * 7.0)) + phase / 3.0)
    pressure = 1011.4 + diurnal + semi_diurnal + slow_trend + _stable_noise(buoy_id, observed_at)
    return round(max(998.5, min(1016.5, pressure)), 2)


def _event_template(started_at: datetime) -> dict[str, Any]:
    bearing_rad = math.radians(SQUALL_BEARING_DEG)
    origin_lat, origin_lon = _offset(
        SQUALL_CENTER[0],
        SQUALL_CENTER[1],
        north_km=-SQUALL_ORIGIN_DISTANCE_KM * math.cos(bearing_rad),
        east_km=-SQUALL_ORIGIN_DISTANCE_KM * math.sin(bearing_rad),
    )
    return {
        'started_at': started_at,
        'peak_at': started_at + timedelta(minutes=45),
        'ended_at': started_at + timedelta(hours=2, minutes=30),
        'center_lat': SQUALL_CENTER[0],
        'center_lon': SQUALL_CENTER[1],
        'front_origin_lat': origin_lat,
        'front_origin_lon': origin_lon,
        'bearing_deg': SQUALL_BEARING_DEG,
        'speed_kph': SQUALL_SPEED_KPH,
        'pressure_drop_hpa': SQUALL_PRESSURE_DROP_HPA,
        'rise_minutes': SQUALL_RISE_MINUTES,
        'hold_minutes': SQUALL_HOLD_MINUTES,
    }


async def reset(pool, run_id: str) -> dict[str, int | str]:
    deleted: dict[str, int | str] = {'run_id': run_id}
    tables = (
        'search_sectors',
        'incidents',
        'sos_events',
        'buoy_contacts',
        'barometric_readings',
        'squall_events',
        'advisories',
        'vessels',
    )
    async with pool.acquire() as conn, conn.transaction():
        for table in tables:
            result = await conn.execute(f'DELETE FROM {table} WHERE demo_tag = $1', run_id)
            deleted[table] = int(result.rsplit(' ', 1)[-1])

    state = get_state()
    if state.run_id == run_id:
        state.scenario = None
        state.beat = -1
        state.fired.clear()
        state.run_id = None
        state.updated_at = datetime.now(UTC)
        state.target_vessel_id = None
        state.incident_id = None
    return deleted


async def _load_buoys(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        '''
        SELECT id, lat, lon, contact_radius_m
        FROM buoys
        WHERE is_synthetic = TRUE
        ORDER BY id
        '''
    )
    return [dict(row) for row in rows]


async def _write_pressure_window(pool, run_id: str, beat: BeatDefinition, scenario: str) -> None:
    as_of = datetime.now(UTC).replace(second=0, microsecond=0)
    event = _event_template(as_of - timedelta(minutes=beat.event_age_minutes))
    async with pool.acquire() as conn:
        buoys = await _load_buoys(conn)
        if not buoys:
            raise RuntimeError('demo requires synthetic buoys')
        readings = []
        for buoy in buoys:
            for step in range(19):
                observed_at = as_of - timedelta(minutes=(18 - step) * 5)
                pressure = _baseline_pressure(buoy['id'], observed_at)
                if beat.index > 0 and scenario == 'squall-fleet':
                    pressure += _event_pressure_at(event, buoy, observed_at)
                readings.append(
                    (
                        buoy['id'],
                        observed_at,
                        round(max(998.5, min(1016.5, pressure)), 2),
                        run_id,
                    )
                )
        async with conn.transaction():
            await conn.execute('DELETE FROM barometric_readings WHERE demo_tag = $1', run_id)
            await conn.execute('DELETE FROM squall_events WHERE demo_tag = $1', run_id)
            await conn.executemany(
                '''
                INSERT INTO barometric_readings
                    (buoy_id, observed_at, pressure_hpa, is_synthetic, demo_tag)
                VALUES ($1, $2, $3, TRUE, $4)
                ''',
                readings,
            )
            if scenario == 'squall-fleet':
                await conn.execute(
                    '''
                    INSERT INTO squall_events (
                      started_at, peak_at, ended_at, center_lat, center_lon,
                      front_origin_lat, front_origin_lon, bearing_deg, speed_kph,
                      pressure_drop_hpa, rise_minutes, hold_minutes,
                      observed_buoy_ids, is_synthetic, demo_tag
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,TRUE,$14)
                    ''',
                    event['started_at'],
                    event['peak_at'],
                    event['ended_at'],
                    event['center_lat'],
                    event['center_lon'],
                    event['front_origin_lat'],
                    event['front_origin_lon'],
                    event['bearing_deg'],
                    event['speed_kph'],
                    event['pressure_drop_hpa'],
                    event['rise_minutes'],
                    event['hold_minutes'],
                    json.dumps([buoy['id'] for buoy in buoys]),
                    run_id,
                )


async def _write_anomaly_contacts(pool, run_id: str) -> str:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    async with pool.acquire() as conn:
        vessels = await conn.fetch(
            '''
            SELECT v.id, v.boat_name, COUNT(DISTINCT bc.trip_id) AS trip_count
            FROM vessels v
            JOIN buoy_contacts bc ON bc.vessel_id = v.id
            WHERE v.is_synthetic = TRUE AND bc.is_synthetic = TRUE
            GROUP BY v.id, v.boat_name
            HAVING COUNT(DISTINCT bc.trip_id) >= 3
            ORDER BY COUNT(DISTINCT bc.trip_id) DESC, v.id
            LIMIT 4
            '''
        )
        if not vessels:
            raise RuntimeError('demo requires generator vessels with three trips')
        target = dict(vessels[0])
        buoy_rows = await conn.fetch(
            'SELECT id, lat, lon FROM buoys WHERE is_synthetic = TRUE ORDER BY id'
        )
        if not buoy_rows:
            raise RuntimeError('demo requires synthetic buoys')
        target_buoy = dict(buoy_rows[-1])
        await conn.execute('DELETE FROM buoy_contacts WHERE demo_tag = $1', run_id)
        await conn.executemany(
            '''
            INSERT INTO buoy_contacts (
              buoy_id, vessel_id, trip_id, sequence_no, observed_at,
              latitude, longitude, contact_type, contact_value,
              created_at, is_synthetic, demo_tag
            ) VALUES ($1,$2,$3,1,$4,$5,$6,'mesh_ping',$7,$4,TRUE,$8)
            ''',
            [
                (
                    target_buoy['id'],
                    vessel['id'],
                    f'demo-{run_id}-{index}',
                    now - timedelta(minutes=180) if index == 0 else now,
                    target_buoy['lat'],
                    target_buoy['lon'],
                    'demo-outbound-1',
                    run_id,
                )
                for index, vessel in enumerate(vessels)
            ],
        )
    return str(target['id'])


async def _write_incident(pool, run_id: str, vessel_id: str) -> int:
    from app.api.sos import SosIn, record_sos
    from app.incidents.trust import sos_provenance

    async with pool.acquire() as conn:
        contact = await conn.fetchrow(
            '''
            SELECT buoy_id, observed_at, latitude, longitude
            FROM buoy_contacts
            WHERE demo_tag = $1 AND vessel_id = $2
            ORDER BY observed_at DESC
            LIMIT 1
            ''',
            run_id,
            vessel_id,
        )
        existing = await conn.fetchrow(
            'SELECT id FROM incidents WHERE demo_tag = $1 ORDER BY id DESC LIMIT 1', run_id
        )
    if contact is None:
        raise RuntimeError('demo anomaly contact is missing')
    if existing is not None:
        return int(existing['id'])

    client_ts = int(contact['observed_at'].timestamp())
    payload = SosIn(
        vessel_id=vessel_id,
        client_ts=client_ts,
        boat=vessel_id,
        lat=float(contact['latitude']),
        lon=float(contact['longitude']),
        note='Capsize distress in demo scenario',
        source='direct',
    )
    provenance = sos_provenance(
        vessel_id=vessel_id,
        requested_tier=payload.trust_tier,
        source=payload.source,
        buoy_id=None,
        src_id=None,
        seq=None,
        device_vessel_id=None,
        gateway_authenticated=False,
    )
    async with pool.acquire() as conn, conn.transaction():
        await record_sos(conn, payload, provenance)
    rng_seed = int(hashlib.sha256(run_id.encode('utf-8')).hexdigest()[:8], 16)
    track = _simulate_drift_track(
        contact['observed_at'],
        float(contact['latitude']),
        float(contact['longitude']),
        np.random.default_rng(rng_seed),
        'capsize',
        [],
    )
    async with pool.acquire() as conn:
        await conn.execute(
            '''
            UPDATE sos_events
            SET is_synthetic = TRUE, demo_tag = $1
            WHERE vessel_id = $2 AND client_ts = $3
            ''',
            run_id,
            vessel_id,
            client_ts,
        )
        row = await conn.fetchrow(
            '''
            INSERT INTO incidents (
              vessel_id, last_contact_at, last_contact_buoy_id,
              last_contact_lat, last_contact_lon, reported_missing_at,
              abnormal_reason, true_track, is_synthetic, demo_tag
            ) VALUES ($1,$2,$3,$4,$5,$6,'capsize',$7::jsonb,TRUE,$8)
            RETURNING id
            ''',
            vessel_id,
            contact['observed_at'],
            contact['buoy_id'],
            contact['latitude'],
            contact['longitude'],
            contact['observed_at'] + timedelta(minutes=15),
            json.dumps(
                track,
                default=lambda value: value.isoformat() if isinstance(value, datetime) else value,
            ),
            run_id,
        )
    return int(row['id'])


async def _publish_advisory(pool, run_id: str) -> None:
    observed_at = datetime.now(UTC)
    async with pool.acquire() as conn:
        await conn.execute(
            '''
            INSERT INTO advisories (
              source_key, title, category, description, municipality, priority,
              publish_date, status, source, score, demo_tag
            ) VALUES ($1,'RETURN NOW: squall front detected','Weather Advisory',
              'Pressure propagation across the buoy array indicates dangerous weather. '
              'Return to shore now.', 'All', 'Emergency', $2, 'Published',
              'AqOne demo scenario', 85, $3)
            ON CONFLICT (source_key) DO UPDATE SET
              description = EXCLUDED.description,
              priority = EXCLUDED.priority,
              publish_date = EXCLUDED.publish_date,
              status = EXCLUDED.status,
              score = EXCLUDED.score,
              updated_at = NOW(),
              demo_tag = EXCLUDED.demo_tag
            ''',
            f'demo:squall:{run_id}',
            observed_at.date(),
            run_id,
        )


async def _record_search_sector(pool, run_id: str, incident_id: int) -> None:
    from app.api.drift import record_legacy_search_sector

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            'SELECT id FROM search_sectors WHERE incident_id = $1 AND demo_tag = $2 LIMIT 1',
            incident_id,
            run_id,
        )
    if existing is not None:
        return

    await record_legacy_search_sector(
        incident_id,
        x_min_m=-2500.0,
        x_max_m=2500.0,
        y_min_m=-2500.0,
        y_max_m=2500.0,
        detection_probability=0.85,
    )
    async with pool.acquire() as conn:
        await conn.execute(
            '''
            UPDATE search_sectors
            SET demo_tag = $1
            WHERE id = (
              SELECT id FROM search_sectors
              WHERE incident_id = $2 AND demo_tag IS NULL
              ORDER BY id DESC LIMIT 1
            )
            ''',
            run_id,
            incident_id,
        )


async def start_scenario(name: str) -> dict[str, object]:
    if name not in SCENARIOS:
        raise ValueError('unknown demo scenario')
    pool = get_pool()
    previous_run = _state.run_id
    if previous_run is not None:
        await reset(pool, previous_run)
    run_id = str(uuid.uuid4())
    await _write_pressure_window(pool, run_id, BEATS[0], name)
    _state.scenario = name
    _state.run_id = run_id
    _state.beat = 0
    _state.fired = {0}
    _state.updated_at = datetime.now(UTC)
    return _state.response()


async def fire_beat(index: int) -> dict[str, object]:
    state = get_state()
    if state.run_id is None or state.scenario is None:
        raise ValueError('no demo scenario is active')
    if state.scenario == 'clear-day' and index != 0:
        raise ValueError('clear-day has baseline beat 0 only')
    if index in state.fired and state.beat == index:
        return state.response()
    beat = _beat(index)
    pool = get_pool()
    await _write_pressure_window(pool, state.run_id, beat, state.scenario)
    if index == 3 and state.scenario == 'squall-fleet':
        await _publish_advisory(pool, state.run_id)
    if index == 4 and state.scenario == 'squall-fleet':
        state.target_vessel_id = await _write_anomaly_contacts(pool, state.run_id)
    elif index == 5 and state.scenario == 'squall-fleet':
        if state.target_vessel_id is None:
            state.target_vessel_id = await _write_anomaly_contacts(pool, state.run_id)
        state.incident_id = await _write_incident(pool, state.run_id, state.target_vessel_id)
    elif index == 6 and state.scenario == 'squall-fleet':
        if state.incident_id is None:
            if state.target_vessel_id is None:
                state.target_vessel_id = await _write_anomaly_contacts(pool, state.run_id)
            state.incident_id = await _write_incident(pool, state.run_id, state.target_vessel_id)
        await _record_search_sector(pool, state.run_id, state.incident_id)
    state.beat = index
    state.fired.add(index)
    state.updated_at = datetime.now(UTC)
    return state.response()


async def advance() -> dict[str, object]:
    state = get_state()
    next_beat = next((beat.index for beat in BEATS if beat.index not in state.fired), None)
    if next_beat is None:
        return state.response()
    return await fire_beat(next_beat)
