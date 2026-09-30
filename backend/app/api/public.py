"""Unauthenticated read-only safety feeds for the fisherman handset.

Every other API surface requires a bearer token. The handset has no account and
never will: `docs/07_SCOPE_OUT.md` records the decision that fisherman identity
is a device-local id with no password, because a person in distress cannot be
asked to log in.

That decision left the app unable to read the two feeds it most needs. It called
`/api/sea-condition`, got 401, fell back to `/api/public/sea-condition`, which
had never been built, and rendered "Sea condition unavailable" forever. The
squall model had no route to the handset at all.

These endpoints are read-only and expose no personal data - a sea-state
declaration and a weather nowcast. They carry the same reasoning as
unauthenticated SOS ingest: safety information must not be gated behind
credentials the person at risk cannot hold.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.api.sea_condition import _buoy_telemetry
from app.api.squall import (
    _latest_observed_at,
    _load_rows,
    _return_now_enabled,
    build_squall_status,
)
from app.db import get_pool
from app.geo import SHORE_STATIONS

router = APIRouter(prefix='/api/public', tags=['public'])

OPEN_METEO_FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
OPEN_METEO_MARINE_URL = 'https://marine-api.open-meteo.com/v1/marine'
FORECAST_UPSTREAM_TIMEOUT_SECONDS = 5.0
MAX_FORECAST_DAYS = 7

BUOY_ACTIVE_WINDOW = timedelta(hours=1)


def buoy_marker(row, now: datetime) -> dict[str, object]:
    last_heard_at = row['last_heard_at']
    if last_heard_at is None:
        status = 'unknown'
    elif now - last_heard_at <= BUOY_ACTIVE_WINDOW:
        status = 'active'
    else:
        status = 'silent'
    return {
        'id': row['id'],
        'name': row['label'],
        'latitude': row['lat'],
        'longitude': row['lon'],
        'coverage_radius_meters': row['contact_radius_m'],
        'lora_radius_meters': row['lora_radius_m'],
        'is_gateway_linked': row['is_gateway_linked'],
        'is_synthetic': row['is_synthetic'],
        'last_heard_at': last_heard_at.isoformat() if last_heard_at else None,
        'status': status,
    }


@router.get('/buoys')
async def public_buoys() -> dict[str, object]:
    """Registered buoys and the shore gateways, for the handset map and the dashboard.

    A buoy with no recorded position is listed with null coordinates, never
    placed somewhere plausible; the handset skips it and the dashboard lists it
    as unplaced.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''
            SELECT b.id, b.label, b.lat, b.lon, b.contact_radius_m, b.lora_radius_m,
                   b.is_gateway_linked, b.is_synthetic,
                   GREATEST(
                     (SELECT MAX(COALESCE(c.observed_at, c.created_at))
                      FROM buoy_contacts c WHERE c.buoy_id = b.id),
                     (SELECT MAX(r.observed_at)
                      FROM barometric_readings r WHERE r.buoy_id = b.id)
                   ) AS last_heard_at
            FROM buoys b
            ORDER BY b.id
            LIMIT 50
            '''
        )
    now = datetime.now(UTC)
    return {
        'buoys': [buoy_marker(row, now) for row in rows],
        'shore_stations': list(SHORE_STATIONS),
    }


@router.get('/alerts/waves')
async def public_wave_alerts() -> dict[str, object]:
    return {'wave_warnings': []}


@router.get('/alerts/capsizing')
async def public_capsizing_alerts() -> dict[str, object]:
    return {'capsizing_advisories': []}


def _serialise_public_sea_condition(row) -> dict[str, object]:
    setter_label = ''
    if isinstance(row, dict) or hasattr(row, 'get'):
        setter_label = (row.get('setter_full_name') or '').strip()
    elif hasattr(row, '__getitem__'):
        try:
            val = row['setter_full_name']
            if val and isinstance(val, str):
                setter_label = val.strip()
        except (KeyError, IndexError):
            pass
    return {
        'id': row['id'],
        'status': row['status'],
        'reason': row['reason'],
        'set_by_label': setter_label if setter_label else 'MDRRMO',
        'created_at': row['created_at'].isoformat(),
    }


@router.get('/sea-condition')
async def public_sea_condition() -> dict[str, object]:
    """The MDRRMO's current declaration.

    This is a human decision, not model output. Public feed exposes set_by_label
    without disclosing operator identity or email.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT sc.*, u.full_name AS setter_full_name
            FROM sea_conditions sc
            LEFT JOIN users u ON u.id::text = sc.set_by_user_id
            ORDER BY sc.created_at DESC, sc.id DESC
            LIMIT 1
            '''
        )
        telemetry = await _buoy_telemetry(conn)
    current = _serialise_public_sea_condition(row) if row else {'status': 'unknown'}
    if telemetry:
        current['buoy_telemetry'] = telemetry
    return {'current': current}


FORECAST_UNITS: dict[str, str] = {
    'time': 'iso8601',
    'temperature': 'celsius',
    'wind_speed': 'km/h',
    'wind_gusts': 'km/h',
    'precipitation': 'mm',
    'wave_height': 'm',
}


def _safe_float(val: object, allow_negative: bool = True) -> float | None:
    if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    f = float(val)
    if not math.isfinite(f):
        return None
    if not allow_negative and f < 0:
        return None
    return f


def _safe_int(val: object, allow_negative: bool = False) -> int | None:
    if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    try:
        f = float(val)
        if not math.isfinite(f):
            return None
        i = int(f)
        if not allow_negative and i < 0:
            return None
        return i
    except (ValueError, OverflowError):
        return None


def _parse_marine_hourly(marine_payload: dict[str, object]) -> dict[str, float | None]:
    """Extract hourly significant wave heights keyed by ISO timestamp string.

    Returns a mapping from time string to wave height in metres (or None if
    missing, non-finite, negative, or ambiguous).
    Duplicate timestamps with conflicting readings are marked None so they are
    never guessed or shifted.
    """
    hourly = marine_payload.get('hourly')
    if not isinstance(hourly, dict):
        return {}
    times = hourly.get('time')
    heights = hourly.get('wave_height')
    if not isinstance(times, list) or not isinstance(heights, list):
        return {}

    marine_by_time: dict[str, float | None] = {}
    seen_counts: dict[str, int] = {}

    for time_str, raw_height in zip(times, heights, strict=False):
        if not isinstance(time_str, str):
            continue
        seen_counts[time_str] = seen_counts.get(time_str, 0) + 1
        valid_height = _safe_float(raw_height, allow_negative=False)
        if seen_counts[time_str] == 1:
            marine_by_time[time_str] = valid_height
        else:
            prev = marine_by_time.get(time_str)
            if prev != valid_height or valid_height is None:
                marine_by_time[time_str] = None

    return marine_by_time


def _daily_wave_max(marine_payload: dict[str, object]) -> dict[str, float]:
    """Max hourly significant wave height per calendar day.

    The marine API only reports hourly, so this collapses to a daily figure
    the same way the handset's own client-side fallback does
    (`DailyOutlook.parseMarineDailyMax` in mobile/lib/models/daily_outlook.dart)
    - kept in sync so a proxied day and a directly-fetched fallback day never
    disagree about the same swell.
    """
    hourly_waves = _parse_marine_hourly(marine_payload)
    by_day: dict[str, float] = {}
    for time_str, height in hourly_waves.items():
        if height is None:
            continue
        day = time_str[:10]
        by_day[day] = max(by_day.get(day, float('-inf')), height)
    return by_day


def _parse_atmo_hourly(
    atmo_payload: dict[str, object],
    marine_by_time: dict[str, float | None],
    max_hours: int,
) -> list[dict[str, object]]:
    hourly = atmo_payload.get('hourly')
    if not isinstance(hourly, dict):
        return []
    times = hourly.get('time')
    if not isinstance(times, list):
        return []

    codes = hourly.get('weather_code')
    temps = hourly.get('temperature_2m')
    winds = hourly.get('wind_speed_10m')
    gusts = hourly.get('wind_gusts_10m')
    precips = hourly.get('precipitation')

    def _val(series: object, idx: int) -> object:
        if isinstance(series, list) and idx < len(series):
            return series[idx]
        return None

    seen_times: set[str] = set()
    duplicate_times: set[str] = set()
    for t in times:
        if isinstance(t, str):
            if t in seen_times:
                duplicate_times.add(t)
            seen_times.add(t)

    emitted_times: set[str] = set()
    out_hours: list[dict[str, object]] = []

    for index, time_str in enumerate(times):
        if not isinstance(time_str, str) or time_str in emitted_times:
            continue
        if len(out_hours) >= max_hours:
            break

        emitted_times.add(time_str)
        is_ambiguous = time_str in duplicate_times

        wave = marine_by_time.get(time_str)

        if is_ambiguous:
            out_hours.append(
                {
                    'time': time_str,
                    'weather_code': None,
                    'temp_c': None,
                    'wind_kph': None,
                    'gust_kph': None,
                    'precip_mm': None,
                    'wave_m': None,
                }
            )
        else:
            out_hours.append(
                {
                    'time': time_str,
                    'weather_code': _safe_int(_val(codes, index), allow_negative=False),
                    'temp_c': _safe_float(_val(temps, index), allow_negative=True),
                    'wind_kph': _safe_float(_val(winds, index), allow_negative=False),
                    'gust_kph': _safe_float(_val(gusts, index), allow_negative=False),
                    'precip_mm': _safe_float(_val(precips, index), allow_negative=False),
                    'wave_m': wave,
                }
            )

    return out_hours


@router.get('/forecast')
async def public_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(default=7, ge=1, le=MAX_FORECAST_DAYS),
) -> dict[str, object]:
    """Transparent Open-Meteo weather and marine proxy - see docs/05_PUBLIC_API.md.

    Supplies both seven-day daily outlook and hourly forecast coverage.
    No server-side fusion model exists yet, so this never claims
    `aqone-fusion` and never includes a `risk` block - the handset scores
    each day itself when `risk` is absent. `wave_m` stays null rather than
    0.0 whenever the marine model has nothing for an interval: a missing reading
    must never read as flat calm.
    The daily calendar day partitioning stays on the local timezone ('auto'),
    preserving existing client day boundaries.
    """
    try:
        async with httpx.AsyncClient(timeout=FORECAST_UPSTREAM_TIMEOUT_SECONDS) as client:
            atmo_response = await client.get(
                OPEN_METEO_FORECAST_URL,
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'daily': (
                        'weather_code,temperature_2m_max,temperature_2m_min,'
                        'wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum'
                    ),
                    'hourly': (
                        'weather_code,temperature_2m,wind_speed_10m,'
                        'wind_gusts_10m,precipitation'
                    ),
                    'forecast_days': days,
                    'timezone': 'auto',
                },
            )
            atmo_response.raise_for_status()
            atmo = atmo_response.json()

            marine: dict[str, object] = {}
            try:
                marine_response = await client.get(
                    OPEN_METEO_MARINE_URL,
                    params={
                        'latitude': lat,
                        'longitude': lon,
                        'hourly': 'wave_height',
                        'forecast_days': days,
                        'timezone': 'auto',
                    },
                )
                marine_response.raise_for_status()
                marine = marine_response.json()
            except (httpx.HTTPError, ValueError):
                # Wave data is frequently unavailable for nearshore cells.
                # That degrades wave_m to null for every day below, not the
                # whole forecast to an error.
                marine = {}
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail='upstream weather provider unavailable'
        ) from exc

    daily = atmo.get('daily')
    if not isinstance(daily, dict):
        raise HTTPException(status_code=502, detail='malformed weather provider response')

    times = daily.get('time')
    if not isinstance(times, list):
        raise HTTPException(status_code=502, detail='malformed weather provider response')

    marine_by_time = _parse_marine_hourly(marine)
    wave_by_day = _daily_wave_max(marine)

    def _at(key: str, index: int) -> object | None:
        series = daily.get(key)
        if isinstance(series, list) and index < len(series):
            return series[index]
        return None

    out_days: list[dict[str, object]] = []
    for index, date_str in enumerate(times):
        if not isinstance(date_str, str):
            continue
        if len(out_days) >= days:
            break
        wave = wave_by_day.get(date_str)
        out_days.append(
            {
                'date': date_str,
                'weather_code': _safe_int(_at('weather_code', index), allow_negative=False),
                'temp_max': _safe_float(_at('temperature_2m_max', index), allow_negative=True),
                'temp_min': _safe_float(_at('temperature_2m_min', index), allow_negative=True),
                'wind_kph': _safe_float(_at('wind_speed_10m_max', index), allow_negative=False),
                'gust_kph': _safe_float(_at('wind_gusts_10m_max', index), allow_negative=False),
                'precip_mm': _safe_float(_at('precipitation_sum', index), allow_negative=False),
                'wave_m': wave,
            }
        )

    out_hours = _parse_atmo_hourly(atmo, marine_by_time, max_hours=days * 24)

    timezone_name = str(atmo.get('timezone') or 'auto')
    timezone_abbr = str(atmo.get('timezone_abbreviation') or '')
    utc_offset = _safe_int(atmo.get('utc_offset_seconds')) or 0
    resp_lat = _safe_float(atmo.get('latitude'))
    resp_lon = _safe_float(atmo.get('longitude'))

    return {
        'source': 'open-meteo',
        'generated_at': datetime.now(UTC).isoformat(),
        'requested_latitude': lat,
        'requested_longitude': lon,
        'latitude': resp_lat if resp_lat is not None else lat,
        'longitude': resp_lon if resp_lon is not None else lon,
        'timezone': timezone_name,
        'timezone_abbreviation': timezone_abbr,
        'utc_offset_seconds': utc_offset,
        'units': FORECAST_UNITS,
        'marine_available': bool(marine and 'hourly' in marine),
        'model_issue_time': None,
        'valid_interval_start': out_hours[0]['time'] if out_hours else None,
        'valid_interval_end': out_hours[-1]['time'] if out_hours else None,
        'days': out_days,
        'hours': out_hours,
    }


@router.get('/squall')
async def public_squall() -> dict[str, object]:
    """Squall nowcast for the handset.

    Reads live pressure telemetry only (docs/39 Phase 3) - production never
    lets an old synthetic scenario reach a real handset. `build_squall_status`
    runs the quality gate (docs/39 Phase 2) before any detection: a missing,
    stale, or incomplete array reports `level: "unknown"` with a reason and
    the last real observation time, never an invented "all clear". `level:
    "return_now"` additionally requires SQUALL_RETURN_NOW_ENABLED - a live
    detection cannot alarm a handset before that field-validation gate opens
    (docs/39 Phase 4), regardless of how confident the model is.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        readings, _, buoy_rows = await _load_rows(conn, live=True)
        fallback_at = await _latest_observed_at(conn, live=True) if not readings else None
    status = build_squall_status(
        readings,
        buoy_rows,
        source='live',
        allow_return_now=_return_now_enabled(),
        fallback_observed_at=fallback_at,
    )
    status['signal_type'] = 'pressure_pattern_research'
    status['is_calibrated'] = False
    return status


@router.get('/sos-nearby')
async def public_sos_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=10, ge=1, le=50),
    vessel_id: str | None = Query(default=None, max_length=32),
) -> dict[str, object]:
    """Active SOS broadcasts near the caller, for nearby helpers.

    Unauthenticated like the other handset safety feeds: a fisher at sea
    holds no account. Privacy is in the shape, not the auth: rounded
    position only, no owner, phone, license, note, or exact GPS.
    Synthetic and demo incidents never appear here.
    Caller filters its own vessel via optional vessel_id.
    """
    import math as _math

    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                '''
                SELECT b.id AS broadcast_id, b.sos_event_id, b.center_lat,
                       b.center_lon, b.radius_km, b.eta_at, b.responder_status,
                       b.state, b.created_at,
                       e.vessel_id, e.boat, e.note, e.resolved_at, e.is_synthetic
                FROM sos_broadcasts b
                JOIN sos_events e ON e.id = b.sos_event_id
                WHERE b.state = 'active'
                  AND e.resolved_at IS NULL
                  AND e.is_synthetic IS FALSE
                ORDER BY b.created_at DESC
                LIMIT 50
                ''',
            )
        except Exception:
            return {'broadcasts': []}
    out: list[dict[str, object]] = []
    for row in rows:
        data = dict(row)
        if vessel_id and data.get('vessel_id') == vessel_id:
            continue
        try:
            clat = float(data['center_lat'])
            clon = float(data['center_lon'])
        except (TypeError, ValueError):
            continue
        north = (clat - lat) * 110.574
        east = (clon - lon) * 111.320 * _math.cos(_math.radians((clat + lat) / 2))
        dist = _math.hypot(north, east)
        limit = float(data.get('radius_km') or radius_km)
        if dist > min(limit, float(radius_km)):
            continue
        eta = data.get('eta_at')
        out.append({
            'broadcast_id': data.get('broadcast_id'),
            'sos_event_id': data.get('sos_event_id'),
            'center_lat': clat,
            'center_lon': clon,
            'distance_km': round(dist, 2),
            'radius_km': data.get('radius_km'),
            'eta_at': eta.isoformat() if hasattr(eta, 'isoformat') else eta,
            'responder_status': data.get('responder_status'),
            'created_at': data.get('created_at').isoformat()
            if hasattr(data.get('created_at'), 'isoformat') else data.get('created_at'),
        })
    out.sort(key=lambda item: float(item.get('distance_km') or 1e9))
    return {'broadcasts': out}
