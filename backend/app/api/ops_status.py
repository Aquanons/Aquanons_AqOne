import os
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends

from app.auth import require_user
from app.db import get_pool
from app.geo import point_in_water
from app.notify import sms_configured

router = APIRouter(prefix='/api/ops', tags=['operations'])
GATEWAY_STALE_AFTER = timedelta(seconds=135)

VESSEL_ACTIVE_15M = """(
  EXISTS(SELECT 1 FROM vessel_devices d
          WHERE d.vessel_id = v.id
            AND d.revoked_at IS NULL
            AND d.last_seen_at > NOW() - INTERVAL '15 minutes')
  OR v.last_seen_at > NOW() - INTERVAL '15 minutes'
  OR EXISTS(SELECT 1 FROM sos_events s
             WHERE s.vessel_id = v.id
               AND s.created_at > NOW() - INTERVAL '15 minutes')
  OR EXISTS(SELECT 1 FROM buoy_contacts b
             WHERE b.vessel_id = v.id
               AND b.source = 'live'
               AND COALESCE(b.observed_at, b.created_at) > NOW() - INTERVAL '15 minutes')
  OR EXISTS(SELECT 1 FROM catch_logs c
             WHERE c.vessel_id = v.id
               AND c.created_at > NOW() - INTERVAL '15 minutes')
)"""


@router.get('/status')
async def ops_status(_: dict = Depends(require_user)) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        last_poll = await conn.fetchval(
            "SELECT last_poll_at FROM gateway_status WHERE gateway_key = 'default'"
        )
        last_runs = await conn.fetch('SELECT job, last_run_at FROM scheduler_runs')
    now = datetime.now(UTC)
    raw_expiry = os.environ.get('DB_EXPIRES_AT', '').strip()
    try:
        expiry = date.fromisoformat(raw_expiry[:10]) if raw_expiry else None
    except ValueError:
        expiry = None
    return {
        'gateway_last_poll_at': last_poll.isoformat() if last_poll else None,
        'gateway_stale': last_poll is None or now - last_poll > GATEWAY_STALE_AFTER,
        'sms_configured': sms_configured(),
        'db_expires_at': expiry.isoformat() if expiry else None,
        'db_days_left': (expiry - now.date()).days if expiry else None,
        'scheduler_last_run': {row['job']: row['last_run_at'].isoformat() for row in last_runs},
    }


@router.get('/presence')
async def ops_presence(user: dict = Depends(require_user)) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET last_seen_at = NOW() WHERE id = $1',
            int(user['id']),
        )
        total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
        active_operators = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE last_seen_at > NOW() - INTERVAL '2 minutes'"
        )
        active_vessels = await conn.fetchval(
            'SELECT COUNT(*) FROM vessels v WHERE ' + VESSEL_ACTIVE_15M
        )
    return {
        'total_users': total_users,
        'active_operators_2m': active_operators,
        'active_vessels_15m': active_vessels,
        'active_total': active_operators + active_vessels,
    }


@router.get('/roster')
async def ops_roster(_: dict = Depends(require_user)) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT v.id AS vessel_id, v.boat_name, v.skipper_name,
                   v.license_type, v.license_number, v.phone,
                   ''' + VESSEL_ACTIVE_15M + ''' AS vessel_active,
                   (SELECT t.status FROM vessel_trips t
                     WHERE t.vessel_id = v.id
                     ORDER BY t.created_at DESC LIMIT 1) AS last_trip_status,
                   f.latitude AS last_lat, f.longitude AS last_lon,
                   f.observed_at AS last_fix_at, f.source AS last_fix_source
              FROM vessels v
         LEFT JOIN LATERAL (
                   SELECT latitude, longitude, observed_at, source FROM (
                     SELECT latitude, longitude, created_at AS observed_at, 'sos' AS source
                       FROM sos_events WHERE vessel_id = v.id
                        AND latitude IS NOT NULL AND longitude IS NOT NULL
                      UNION ALL
                     SELECT latitude, longitude, observed_at, 'buoy'
                       FROM buoy_contacts WHERE vessel_id = v.id
                        AND latitude IS NOT NULL AND longitude IS NOT NULL
                      UNION ALL
                     SELECT latitude, longitude, created_at, 'catch'
                       FROM catch_logs WHERE vessel_id = v.id
                        AND latitude IS NOT NULL AND longitude IS NOT NULL
                      UNION ALL
                     SELECT latitude, longitude, created_at, 'spot'
                       FROM fishing_spots WHERE vessel_id = v.id
                   ) fixes
                   ORDER BY observed_at DESC LIMIT 1
                 ) f ON true
             ORDER BY v.boat_name
            '''
        )
    return {
        'vessels': [
            {
                'vessel_id': row['vessel_id'],
                'boat_name': row['boat_name'],
                'skipper_name': row['skipper_name'],
                'license_type': row['license_type'],
                'license_number': row['license_number'],
                'phone': row['phone'],
                'vessel_active': bool(row['vessel_active']),
                'last_trip_status': row['last_trip_status'],
                'last_lat': row['last_lat'],
                'last_lon': row['last_lon'],
                'last_fix_at': row['last_fix_at'].isoformat() if row['last_fix_at'] else None,
                'last_fix_source': row['last_fix_source'],
                'last_fix_on_water': (
                    None if row['last_lat'] is None or row['last_lon'] is None
                    else bool(point_in_water(float(row['last_lat']), float(row['last_lon'])))
                ),
            }
            for row in rows
        ],
    }
