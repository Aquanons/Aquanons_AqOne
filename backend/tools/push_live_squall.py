"""Gateway stand-in: push a realistic squall pressure array into a live
deployment through the trusted gateway ingest (POST /api/v1/pressure-events),
so GET /api/public/squall shows the full lifecycle (unknown -> watch ->
return_now) on the handset.

Requires:
  - A running backend with SQUALL_RETURN_NOW_ENABLED=true
  - 3+ live buoys in the DB (is_synthetic=false)
  - The GATEWAY_API_KEY env var (or --api-key arg)

Usage (one-shot backfill):
  python -m tools.push_live_squall --api-key KEY --buoy buoy-a --buoy buoy-b --buoy buoy-c:11.708:122.365

Usage (watch mode, keeps readings fresh indefinitely):
  python -m tools.push_live_squall --api-key KEY --watch --buoy buoy-a --buoy buoy-b --buoy buoy-c:11.708:122.365
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.demo.scenarios import (
    _baseline_pressure,
    _event_template,
)
from app.simulation.generator import _event_pressure_at

LOOKBACK_MINUTES = 90
STEP_MINUTES = 5
READINGS_PER_WINDOW = LOOKBACK_MINUTES // STEP_MINUTES + 1
WINDOW_OFFSETS = list(range(LOOKBACK_MINUTES, -1, -STEP_MINUTES))

KNOWN_LIVE_BUOYS: dict[str, dict[str, float]] = {
    'buoy-a': {'lat': 11.68, 'lon': 122.414},
    'buoy-b': {'lat': 11.652, 'lon': 122.448},
}


def _parse_buoy_arg(arg: str) -> tuple[str, float, float]:
    parts = arg.split(':')
    if len(parts) == 3:
        return parts[0], float(parts[1]), float(parts[2])
    if len(parts) == 1 and parts[0] in KNOWN_LIVE_BUOYS:
        pos = KNOWN_LIVE_BUOYS[parts[0]]
        return parts[0], pos['lat'], pos['lon']
    raise ValueError(f'buoy arg must be id:lat:lon or a known buoy id, got: {arg!r}')


def stage_window(
    buoy_positions: dict[str, dict[str, float]],
    as_of: datetime,
) -> list[dict[str, Any]]:
    event_started_at = as_of - timedelta(minutes=LOOKBACK_MINUTES)
    event = _event_template(event_started_at)
    readings: list[dict[str, Any]] = []
    for buoy_id, pos in buoy_positions.items():
        buoy = {'lat': pos['lat'], 'lon': pos['lon']}
        for offset in WINDOW_OFFSETS:
            observed_at = as_of - timedelta(minutes=offset)
            pressure = _baseline_pressure(buoy_id, observed_at)
            pressure += _event_pressure_at(event, buoy, observed_at)
            pressure = round(max(998.5, min(1016.5, pressure)), 2)
            readings.append({
                'buoy_id': buoy_id,
                'observed_at': observed_at,
                'pressure_hpa': pressure,
            })
    return readings


def _event_id(buoy_id: str, observed_at: datetime) -> str:
    raw = f'squall-feeder-{buoy_id}-{int(observed_at.timestamp())}'
    return raw[:128]


def _push_reading(
    base_url: str,
    api_key: str,
    buoy_id: str,
    observed_at: datetime,
    pressure_hpa: float,
) -> dict[str, Any]:
    payload = json.dumps({
        'v': 1,
        'event_id': _event_id(buoy_id, observed_at),
        'buoy_id': buoy_id,
        'observed_at': observed_at.isoformat(),
        'pressure_hpa': pressure_hpa,
        'source': 'live',
    }).encode('utf-8')
    req = urllib.request.Request(
        f'{base_url}/api/v1/pressure-events',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'X-Api-Key': api_key,
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _poll_squall(base_url: str) -> dict[str, Any]:
    req = urllib.request.Request(f'{base_url}/api/public/squall')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def push_window(
    base_url: str,
    api_key: str,
    buoy_positions: dict[str, dict[str, float]],
    as_of: datetime | None = None,
) -> dict[str, Any]:
    as_of = as_of or datetime.now(UTC)
    readings = stage_window(buoy_positions, as_of)
    results: list[dict[str, Any]] = []
    for reading in readings:
        try:
            result = _push_reading(
                base_url, api_key,
                reading['buoy_id'], reading['observed_at'], reading['pressure_hpa'],
            )
            results.append(result)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            results.append({'error': exc.code, 'detail': body})
    return {'pushed': len(results), 'results': results, 'as_of': as_of.isoformat()}


def push_topup(
    base_url: str,
    api_key: str,
    buoy_positions: dict[str, dict[str, float]],
) -> datetime:
    now = datetime.now(UTC)
    event_started_at = now - timedelta(minutes=LOOKBACK_MINUTES)
    event = _event_template(event_started_at)
    for buoy_id, pos in buoy_positions.items():
        buoy = {'lat': pos['lat'], 'lon': pos['lon']}
        pressure = _baseline_pressure(buoy_id, now)
        pressure += _event_pressure_at(event, buoy, now)
        pressure = round(max(998.5, min(1016.5, pressure)), 2)
        with contextlib.suppress(urllib.error.HTTPError):
            _push_reading(base_url, api_key, buoy_id, now, pressure)
    return now


def _parse_args() -> dict[str, Any]:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://127.0.0.1:8000'))
    parser.add_argument('--api-key', default=os.environ.get('GATEWAY_API_KEY', ''))
    parser.add_argument('--buoy', action='append', dest='buoys', default=[],
                        help='id:lat:lon or known id (buoy-a, buoy-b)')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=int, default=5,
                        help='minutes between top-up pushes in watch mode')
    parser.add_argument('--minutes', type=int, default=0,
                        help='cap watch mode after N minutes (0 = run forever)')
    args = parser.parse_args()
    return vars(args)


def main() -> None:
    opts = _parse_args()
    base_url = opts['base_url'].rstrip('/')
    api_key = opts['api_key']
    if not api_key:
        print('ERROR: --api-key or GATEWAY_API_KEY env var is required', file=sys.stderr)
        sys.exit(1)

    buoy_positions: dict[str, dict[str, float]] = {}
    for arg in opts['buoys']:
        bid, lat, lon = _parse_buoy_arg(arg)
        buoy_positions[bid] = {'lat': lat, 'lon': lon}

    if len(buoy_positions) < 3:
        print(
            f'ERROR: at least 3 live buoys required, got {len(buoy_positions)}.\n'
            'Pass --buoy id:lat:lon for each, or use known ids: '
            + ', '.join(KNOWN_LIVE_BUOYS),
            file=sys.stderr,
        )
        sys.exit(1)

    print(f'Pushing squall scenario to {base_url}')
    print(f'Buoys: {", ".join(buoy_positions.keys())}')

    push_window(base_url, api_key, buoy_positions)

    status = _poll_squall(base_url)
    print(f'level={status.get("level")}  return_now={status.get("return_now")}  '
          f'reason={status.get("status_reason")}  source={status.get("source")}')

    if not opts['watch']:
        return

    print(f'\nWatch mode: top-up every {opts["interval"]}min', end='')
    if opts['minutes']:
        print(f' for {opts["minutes"]}min')
    else:
        print(' (Ctrl+C to stop)')

    deadline = time.monotonic() + opts['minutes'] * 60 if opts['minutes'] else float('inf')
    try:
        while time.monotonic() < deadline:
            time.sleep(opts['interval'] * 60)
            push_topup(base_url, api_key, buoy_positions)
            status = _poll_squall(base_url)
            ts = datetime.now(UTC).strftime('%H:%M:%S')
            print(f'[{ts}] level={status.get("level")}  return_now={status.get("return_now")}')
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
