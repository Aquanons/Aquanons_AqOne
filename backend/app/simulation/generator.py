from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import pairwise
from typing import Any

import asyncpg
import numpy as np

from app import geo

# Geography is defined once in app.geo and shared with the dashboard. The
# previous centre here (11.6892, 122.3667) was ~8 km north-west of the real
# municipality - effectively Kalibo - which is why generated positions spread
# across Aklan and onto land.
CENTER_LAT = geo.CENTER_LAT
CENTER_LON = geo.CENTER_LON
MANILA_TZ = timezone(timedelta(hours=8))
DEFAULT_START = datetime(2026, 8, 1, tzinfo=MANILA_TZ)
BARO_STEP = timedelta(minutes=5)
CURRENT_STEP = timedelta(minutes=15)
TRACK_STEP = timedelta(minutes=30)

KM_PER_DEG_LAT = 110.574


def _km_per_deg_lon(lat: float) -> float:
    return 111.320 * math.cos(math.radians(lat))


def _offset(lat: float, lon: float, north_km: float = 0.0, east_km: float = 0.0) -> tuple[float, float]:
    return (
        lat + north_km / KM_PER_DEG_LAT,
        lon + east_km / _km_per_deg_lon(lat),
    )


def _water_positions_within(
    rng: np.random.Generator,
    count: int,
    min_km: float,
    max_km: float,
) -> list[tuple[float, float]]:
    """Sample water positions in a distance band around the municipal centre.

    The water polygon extends well offshore so drift simulations have room to
    run, but buoys and vessels belong in municipal waters. Sampling the whole
    polygon uniformly would scatter them far out to sea, so positions are drawn
    from a band measured from the town centre.
    """
    kept: list[tuple[float, float]] = []
    for _ in range(40):
        for lat, lon in geo.sample_water_points(rng, count * 8):
            distance = _distance_km(CENTER_LAT, CENTER_LON, lat, lon)
            if min_km <= distance <= max_km:
                kept.append((lat, lon))
        if len(kept) >= count:
            break

    if len(kept) < count:
        raise RuntimeError(
            f'Only found {len(kept)} of {count} water positions between '
            f'{min_km} and {max_km} km of the centre. Widen the band or check '
            f'WATER_POLYGON.'
        )

    picks = rng.choice(len(kept), size=count, replace=False)
    return [kept[int(i)] for i in picks]


def _distance_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    lat1 = math.radians(a_lat)
    lat2 = math.radians(b_lat)
    dlat = lat2 - lat1
    dlon = math.radians(b_lon - a_lon)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _project_track(
    origin_lat: float,
    origin_lon: float,
    bearing_deg: float,
    point_lat: float,
    point_lon: float,
) -> tuple[float, float]:
    bearing_rad = math.radians(bearing_deg)
    lat_scale = KM_PER_DEG_LAT
    lon_scale = _km_per_deg_lon((origin_lat + point_lat) / 2)
    north = (point_lat - origin_lat) * lat_scale
    east = (point_lon - origin_lon) * lon_scale
    along = east * math.sin(bearing_rad) + north * math.cos(bearing_rad)
    cross = east * math.cos(bearing_rad) - north * math.sin(bearing_rad)
    return along, cross


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _hhmm(minutes: int) -> str:
    minutes %= 24 * 60
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    raise TypeError(f'Cannot serialize {type(value)!r}')


def _synthetic_wind_vector(lat: float, lon: float, at: datetime) -> tuple[float, float]:
    hours = (at.astimezone(MANILA_TZ) - datetime(2026, 8, 1, tzinfo=MANILA_TZ)).total_seconds() / 3600.0
    daily = 2.0 * math.pi * hours / 24.0
    weekly = 2.0 * math.pi * hours / (24.0 * 7.0)
    spatial = (lat - CENTER_LAT) * 0.6 + (lon - CENTER_LON) * 0.4
    speed = 7.0 + 1.9 * math.sin(daily + spatial) + 0.7 * math.cos(weekly - spatial / 2.0)
    speed = float(_clip(speed, 2.5, 14.0))
    direction_from_deg = 65.0 + 28.0 * math.sin(weekly + spatial) + 12.0 * math.cos(daily / 2.0)
    direction_to_deg = (direction_from_deg + 180.0) % 360.0
    rad = math.radians(direction_to_deg)
    return speed * math.sin(rad), speed * math.cos(rad)


def _leeway_spec(reason: str) -> tuple[float, float]:
    if reason in {'capsize', 'adverse_weather'}:
        return 0.012, 0.004
    if reason == 'loss_of_signal':
        return 0.020, 0.007
    return 0.020, 0.007


@dataclass(frozen=True)
class VesselProfile:
    vessel_id: str
    boat_name: str
    home_lat: float
    home_lon: float
    preferred_heading_deg: float
    cruising_speed_kph: float
    departure_minutes: int
    return_minutes: int
    route_buoy_ids: tuple[str, ...]
    home_buoy_id: str


@dataclass(frozen=True)
class TripPlan:
    vessel_id: str
    boat_name: str
    trip_id: str
    day_index: int
    departure_at: datetime
    planned_return_at: datetime
    route_buoy_ids: tuple[str, ...]
    home_lat: float
    home_lon: float
    cruising_speed_kph: float
    is_incident: bool = False
    incident_cutoff: int | None = None


@dataclass
class SimulationPlan:
    vessels: list[dict[str, Any]]
    buoys: list[dict[str, Any]]
    buoy_contacts: list[dict[str, Any]]
    barometric_readings: list[dict[str, Any]]
    squall_events: list[dict[str, Any]]
    current_observations: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    sos_events: list[dict[str, Any]]

    def counts(self) -> dict[str, int]:
        return {
            'vessels': len(self.vessels),
            'buoys': len(self.buoys),
            'buoy_contacts': len(self.buoy_contacts),
            'barometric_readings': len(self.barometric_readings),
            'squall_events': len(self.squall_events),
            'current_observations': len(self.current_observations),
            'incidents': len(self.incidents),
            'sos_events': len(self.sos_events),
        }

    def fingerprint(self) -> str:
        payload = {
            'vessels': self.vessels,
            'buoys': self.buoys,
            'buoy_contacts': self.buoy_contacts,
            'barometric_readings': self.barometric_readings,
            'squall_events': self.squall_events,
            'current_observations': self.current_observations,
            'incidents': self.incidents,
            'sos_events': self.sos_events,
        }
        encoded = json.dumps(payload, default=_json_default, sort_keys=True).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def example_squall(self) -> dict[str, Any] | None:
        return self.squall_events[0] if self.squall_events else None


def build_plan(days: int, seed: int, start_at: datetime = DEFAULT_START) -> SimulationPlan:
    rng = np.random.default_rng(seed)
    buoys = _build_buoys(rng, start_at)
    vessels, profiles = _build_vessels(rng, buoys, start_at)
    trips = _build_trips(rng, profiles, days, start_at)
    incident_trips = _mark_incidents(rng, trips)
    squall_events = _build_squall_events(rng, buoys, days, start_at)
    barometric_readings = _build_barometric_readings(rng, buoys, squall_events, days, start_at)
    current_observations = _build_current_observations(rng, buoys, squall_events, days, start_at)
    buoy_contacts, incidents, sos_events = _build_trip_activity(
        rng,
        trips,
        incident_trips,
        buoys,
        squall_events,
    )
    return SimulationPlan(
        vessels=vessels,
        buoys=buoys,
        buoy_contacts=buoy_contacts,
        barometric_readings=barometric_readings,
        squall_events=squall_events,
        current_observations=current_observations,
        incidents=incidents,
        sos_events=sos_events,
    )


def _build_buoys(rng: np.random.Generator, start_at: datetime) -> list[dict[str, Any]]:
    count = int(rng.integers(8, 13))
    positions, radii = _build_mesh_chain(rng, count)

    rows: list[dict[str, Any]] = []
    for index in range(count):
        lat, lon = positions[index]
        lora_radius = radii[index]
        gateway_linked = any(
            _distance_km(lat, lon, station['lat'], station['lon']) * 1000.0 <= lora_radius
            for station in geo.SHORE_STATIONS
        )
        rows.append(
            {
                'id': f'B{index + 1:02d}',
                'label': f'Buoy {index + 1:02d}',
                'lat': lat,
                'lon': lon,
                # WiFi SoftAP bubble: the range within which a phone can hand
                # over an SOS. Short, per docs/03_PHONE_BUOY_WIFI.md.
                'contact_radius_m': int(rng.integers(800, 1501)),
                # LoRa link range: buoy-to-buoy and buoy-to-gateway relay.
                'lora_radius_m': int(lora_radius),
                'is_gateway_linked': gateway_linked,
                'created_at': start_at - timedelta(days=30 + index),
                'is_synthetic': True,
            }
        )
    return rows


LORA_RADIUS_MIN_M = 6000.0
LORA_RADIUS_MAX_M = 8000.0

# Each new buoy is placed between 0.55x and 0.90x of LoRa range from an
# existing one: close enough that the link is comfortably inside range, far
# enough that the buoy extends coverage instead of stacking on its neighbour.
# The overlap this produces is what makes the mesh legible on the map.
LINK_SPACING_MIN = 0.55
LINK_SPACING_MAX = 0.90


def _build_mesh_chain(
    rng: np.random.Generator,
    count: int,
) -> tuple[list[tuple[float, float]], list[float]]:
    """Place buoys as a connected LoRa chain anchored at a shore gateway.

    Independent random sampling produced a set of isolated points - buoys 4-9 km
    apart with ~1 km radios - which could not have relayed anything to shore.
    Placement is now incremental: the first buoy must reach a shore station
    directly, and every later buoy must land within LoRa range of one already
    placed. Connectivity is therefore a property of construction, and
    tests/test_mesh.py verifies it holds.
    """
    anchor_station = min(
        geo.SHORE_STATIONS,
        key=lambda s: min(
            _distance_km(s['lat'], s['lon'], lat, lon) for lat, lon in geo.WATER_POLYGON
        ),
    )

    positions: list[tuple[float, float]] = []
    radii: list[float] = []

    for index in range(count):
        radius_m = float(rng.uniform(LORA_RADIUS_MIN_M, LORA_RADIUS_MAX_M))
        placed = False

        for _ in range(4000):
            lat, lon = geo.sample_water_points(rng, 1)[0]

            if not positions:
                # Anchor: must reach the shore gateway directly.
                gap_m = (
                    _distance_km(lat, lon, anchor_station['lat'], anchor_station['lon']) * 1000.0
                )
                if LINK_SPACING_MIN * radius_m <= gap_m <= LINK_SPACING_MAX * radius_m:
                    placed = True
            else:
                # Later buoys: within link range of an existing buoy, but not
                # so close that they duplicate its coverage.
                gaps = [
                    _distance_km(lat, lon, plat, plon) * 1000.0 for plat, plon in positions
                ]
                nearest = min(gaps)
                budget = min(radius_m, min(radii))
                if LINK_SPACING_MIN * budget <= nearest <= LINK_SPACING_MAX * budget:
                    placed = True

            if placed:
                positions.append((lat, lon))
                radii.append(radius_m)
                break

        if not placed:
            raise RuntimeError(
                f'Could not place buoy {index + 1} of {count} within LoRa range of '
                f'the existing chain. The water polygon may be too small for this '
                f'many buoys at {LORA_RADIUS_MIN_M / 1000:.0f}-'
                f'{LORA_RADIUS_MAX_M / 1000:.0f} km spacing.'
            )

    return positions, radii


def _build_vessels(
    rng: np.random.Generator,
    buoys: list[dict[str, Any]],
    start_at: datetime,
) -> tuple[list[dict[str, Any]], list[VesselProfile]]:
    count = int(rng.integers(30, 51))
    profiles: list[VesselProfile] = []
    rows: list[dict[str, Any]] = []

    # Home anchorages sit just off the coastal barangays, inshore of the buoys.
    home_positions = _water_positions_within(rng, count, min_km=0.8, max_km=6.5)

    for index in range(count):
        vessel_id = f'V{index + 1:03d}'
        boat_name = f'NW-{index + 1:03d}'
        home_lat, home_lon = home_positions[index]
        preferred_heading_deg = float(rng.uniform(18.0, 145.0))
        cruising_speed_kph = float(rng.uniform(12.0, 18.5))
        departure_minutes = int(rng.integers(260, 395))
        return_minutes = int(rng.integers(970, 1155))
        route_buoy_ids = _select_route_buoys(
            home_lat,
            home_lon,
            preferred_heading_deg,
            buoys,
            route_size=int(rng.integers(3, 5)),
        )
        home_buoy_id = route_buoy_ids[0]
        profiles.append(
            VesselProfile(
                vessel_id=vessel_id,
                boat_name=boat_name,
                home_lat=home_lat,
                home_lon=home_lon,
                preferred_heading_deg=preferred_heading_deg,
                cruising_speed_kph=cruising_speed_kph,
                departure_minutes=departure_minutes,
                return_minutes=return_minutes,
                route_buoy_ids=tuple(route_buoy_ids),
                home_buoy_id=home_buoy_id,
            )
        )
        rows.append(
            {
                'id': vessel_id,
                'boat_name': boat_name,
                'home_buoy_id': home_buoy_id,
                'preferred_heading_deg': preferred_heading_deg,
                'typical_departure_local': _hhmm(departure_minutes),
                'typical_return_local': _hhmm(return_minutes),
                'cruising_speed_kph': cruising_speed_kph,
                'route_buoy_ids': list(route_buoy_ids),
                'created_at': start_at - timedelta(days=90 + index),
                'is_synthetic': True,
            }
        )
    return rows, profiles


def _select_route_buoys(
    home_lat: float,
    home_lon: float,
    bearing_deg: float,
    buoys: list[dict[str, Any]],
    route_size: int,
) -> list[str]:
    scored: list[tuple[float, float, str]] = []
    for buoy in buoys:
        segment_bearing = bearing_deg
        along, cross = _project_track(home_lat, home_lon, segment_bearing, buoy['lat'], buoy['lon'])
        if along < 0:
            along_penalty = 10.0
        elif along > 30:
            along_penalty = (along - 30) * 0.25
        else:
            along_penalty = 0.0
        score = abs(cross) + along_penalty
        scored.append((score, along, buoy['id']))
    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    selected = scored[: max(2, route_size)]
    selected.sort(key=lambda item: (item[1], item[2]))
    return [item[2] for item in selected]


def _build_trips(
    rng: np.random.Generator,
    profiles: list[VesselProfile],
    days: int,
    start_at: datetime,
) -> list[TripPlan]:
    trips: list[TripPlan] = []
    for day_index in range(days):
        day_start = start_at + timedelta(days=day_index)
        for profile in profiles:
            departure_jitter = int(rng.normal(0, 22))
            departure_at = day_start + timedelta(minutes=profile.departure_minutes + departure_jitter)
            transit_noise = rng.uniform(0.92, 1.08)
            total_route_km = _route_length_km(profile.home_lat, profile.home_lon, profile.route_buoy_ids)
            outbound_hours = total_route_km / max(1.0, profile.cruising_speed_kph * transit_noise)
            fishing_hours = float(_clip(rng.normal(3.8, 0.9), 1.8, 6.5))
            return_at = departure_at + timedelta(hours=outbound_hours * 2 + fishing_hours)
            trips.append(
                TripPlan(
                    vessel_id=profile.vessel_id,
                    boat_name=profile.boat_name,
                    trip_id=f'{profile.vessel_id}-{day_index + 1:02d}',
                    day_index=day_index,
                    departure_at=departure_at,
                    planned_return_at=return_at,
                    route_buoy_ids=profile.route_buoy_ids,
                    home_lat=profile.home_lat,
                    home_lon=profile.home_lon,
                    cruising_speed_kph=profile.cruising_speed_kph,
                )
            )
    return trips


def _mark_incidents(rng: np.random.Generator, trips: list[TripPlan]) -> set[str]:
    incident_count = int(rng.integers(5, 9))
    eligible = [trip for trip in trips if len(trip.route_buoy_ids) >= 3]
    chosen = rng.choice(len(eligible), size=min(incident_count, len(eligible)), replace=False)
    incident_ids: set[str] = set()
    for index in sorted(int(value) for value in chosen):
        incident_ids.add(eligible[index].trip_id)
    return incident_ids


def _build_squall_events(
    rng: np.random.Generator,
    buoys: list[dict[str, Any]],
    days: int,
    start_at: datetime,
) -> list[dict[str, Any]]:
    # Squalls are frequent in Philippine waters, and 6-10 events over 14 days
    # left so few positive examples that a train/test split had almost nothing
    # to score against - precision and recall both came out at zero. Two to
    # three events per day is both realistic for the tropics and enough to
    # train and evaluate on.
    count = int(rng.integers(28, 45))
    rows: list[dict[str, Any]] = []
    for index in range(count):
        started_at = start_at + timedelta(
            days=float(rng.uniform(0.5, days - 0.8)),
            minutes=float(rng.uniform(0, 90)),
        )
        rise_minutes = int(rng.integers(30, 61))
        hold_minutes = int(rng.integers(45, 121))
        speed_kph = float(rng.uniform(20.0, 40.0))
        bearing_deg = float(rng.uniform(0.0, 360.0))
        pressure_drop_hpa = float(rng.uniform(3.0, 6.0))
        path_km = float(rng.uniform(24.0, 34.0))
        front_origin_lat, front_origin_lon = _offset(
            CENTER_LAT,
            CENTER_LON,
            north_km=-(path_km / 2.0) * math.cos(math.radians(bearing_deg)),
            east_km=-(path_km / 2.0) * math.sin(math.radians(bearing_deg)),
        )
        peak_at = started_at + timedelta(hours=(path_km / speed_kph) / 2.0)
        center_lat, center_lon = _offset(
            front_origin_lat,
            front_origin_lon,
            north_km=(path_km / 2.0) * math.cos(math.radians(bearing_deg)),
            east_km=(path_km / 2.0) * math.sin(math.radians(bearing_deg)),
        )
        ended_at = started_at + timedelta(hours=path_km / speed_kph) + timedelta(minutes=hold_minutes)
        observed_buoys = _observed_buoys_for_event(
            buoys,
            front_origin_lat,
            front_origin_lon,
            bearing_deg,
            speed_kph,
            rise_minutes,
            hold_minutes,
            pressure_drop_hpa,
        )
        rows.append(
            {
                'id': index + 1,
                'started_at': started_at,
                'peak_at': peak_at,
                'ended_at': ended_at,
                'center_lat': center_lat,
                'center_lon': center_lon,
                'front_origin_lat': front_origin_lat,
                'front_origin_lon': front_origin_lon,
                'bearing_deg': bearing_deg,
                'speed_kph': speed_kph,
                'pressure_drop_hpa': pressure_drop_hpa,
                'rise_minutes': rise_minutes,
                'hold_minutes': hold_minutes,
                'observed_buoy_ids': observed_buoys,
                'is_synthetic': True,
            }
        )
    rows.sort(key=lambda row: row['started_at'])
    return rows


def _observed_buoys_for_event(
    buoys: list[dict[str, Any]],
    origin_lat: float,
    origin_lon: float,
    bearing_deg: float,
    speed_kph: float,
    rise_minutes: int,
    hold_minutes: int,
    pressure_drop_hpa: float,
) -> list[str]:
    observed: list[tuple[float, str]] = []
    for buoy in buoys:
        along, cross = _project_track(origin_lat, origin_lon, bearing_deg, buoy['lat'], buoy['lon'])
        if along < 0 or along > 36:
            continue
        spatial = math.exp(-((abs(cross) / 10.5) ** 2))
        if spatial * pressure_drop_hpa < 0.8:
            continue
        arrival_hours = along / speed_kph
        observed.append((arrival_hours, buoy['id']))
    observed.sort(key=lambda item: (item[0], item[1]))
    if not observed:
        fallback = min(
            buoys,
            key=lambda buoy: (
                abs(_project_track(origin_lat, origin_lon, bearing_deg, buoy['lat'], buoy['lon'])[1]),
                buoy['id'],
            ),
        )
        observed.append((0.0, fallback['id']))
    return [item[1] for item in observed]


def _event_pressure_at(
    event: dict[str, Any],
    buoy: dict[str, Any],
    observed_at: datetime,
) -> float:
    along, cross = _project_track(
        event['front_origin_lat'],
        event['front_origin_lon'],
        event['bearing_deg'],
        buoy['lat'],
        buoy['lon'],
    )
    if along < 0:
        return 0.0
    arrival_at = event['started_at'] + timedelta(hours=along / event['speed_kph'])
    minute_offset = (observed_at - arrival_at).total_seconds() / 60.0
    if minute_offset < 0:
        return 0.0
    rise = float(event['rise_minutes'])
    hold = float(event['hold_minutes'])
    drop = float(event['pressure_drop_hpa'])
    spatial = math.exp(-((abs(cross) / 10.5) ** 2))
    if minute_offset <= rise:
        temporal = minute_offset / rise
    elif minute_offset <= rise + hold:
        temporal = 1.0
    elif minute_offset <= rise + hold + rise:
        temporal = max(0.0, 1.0 - ((minute_offset - rise - hold) / rise))
    else:
        temporal = 0.0
    return -drop * spatial * temporal


def _build_barometric_readings(
    rng: np.random.Generator,
    buoys: list[dict[str, Any]],
    events: list[dict[str, Any]],
    days: int,
    start_at: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total_steps = days * 24 * 12
    buoy_phases = {buoy['id']: float(rng.uniform(0.0, 2 * math.pi)) for buoy in buoys}
    for buoy in buoys:
        phase = buoy_phases[buoy['id']]
        for step in range(total_steps):
            observed_at = start_at + step * BARO_STEP
            t_hours = step / 12.0
            diurnal = 1.15 * math.sin((2 * math.pi * t_hours / 24.0) + phase)
            semi_diurnal = 0.35 * math.sin((2 * math.pi * t_hours / 12.42) + phase / 2.5)
            slow_trend = 0.28 * math.sin((2 * math.pi * t_hours / (24.0 * 7.0)) + phase / 3.0)
            noise = float(rng.normal(0.0, 0.16))
            pressure = 1011.4 + diurnal + semi_diurnal + slow_trend + noise
            for event in events:
                pressure += _event_pressure_at(event, buoy, observed_at)
            rows.append(
                {
                    'buoy_id': buoy['id'],
                    'observed_at': observed_at,
                    'pressure_hpa': round(float(_clip(pressure, 998.5, 1016.5)), 2),
                    'is_synthetic': True,
                }
            )
    return rows


def _current_vector(
    lat: float,
    lon: float,
    observed_at: datetime,
    start_at: datetime,
) -> tuple[float, float]:
    hours = (observed_at - start_at).total_seconds() / 3600.0
    tide = 2 * math.pi * hours / 12.42
    daily = 2 * math.pi * hours / 24.0
    weekly = 2 * math.pi * hours / (24.0 * 7.0)
    spatial_lat = (lat - CENTER_LAT) * 18.0
    spatial_lon = (lon - CENTER_LON) * 18.0
    u = (
        0.32
        + 0.20 * math.sin(tide + spatial_lat)
        + 0.10 * math.cos(daily + spatial_lon / 2.0)
        + 0.05 * math.sin(weekly + spatial_lat / 3.0)
    )
    v = (
        0.18
        + 0.16 * math.cos(tide * 0.9 + spatial_lon)
        + 0.08 * math.sin(daily + spatial_lat / 2.0)
        + 0.04 * math.cos(weekly - spatial_lon / 3.0)
    )
    speed = math.hypot(u, v)
    if speed > 1.45:
        scale = 1.45 / speed
        u *= scale
        v *= scale
    return u, v


def _build_current_observations(
    rng: np.random.Generator,
    buoys: list[dict[str, Any]],
    events: list[dict[str, Any]],
    days: int,
    start_at: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total_steps = days * 24 * 4
    for buoy in buoys:
        for step in range(total_steps):
            observed_at = start_at + step * CURRENT_STEP
            true_u, true_v = _current_vector(buoy['lat'], buoy['lon'], observed_at, start_at)
            gust = 0.04 * math.sin((2 * math.pi * step) / 64.0)
            noisy_u = true_u + float(rng.normal(0.0, 0.03)) + gust
            noisy_v = true_v + float(rng.normal(0.0, 0.03)) - gust / 2.0
            observed_speed = math.hypot(noisy_u, noisy_v)
            if observed_speed > 1.5:
                scale = 1.5 / observed_speed
                noisy_u *= scale
                noisy_v *= scale
            rows.append(
                {
                    'buoy_id': buoy['id'],
                    'observed_at': observed_at,
                    'true_u_mps': round(true_u, 3),
                    'true_v_mps': round(true_v, 3),
                    'observed_u_mps': round(noisy_u, 3),
                    'observed_v_mps': round(noisy_v, 3),
                    'is_synthetic': True,
                }
            )
    return rows


def _route_length_km(home_lat: float, home_lon: float, route_buoy_ids: tuple[str, ...]) -> float:
    # Approximation used only to shape the trip duration.
    points = [(home_lat, home_lon)]
    for index, _ in enumerate(route_buoy_ids):
        # The caller passes the actual buoy coordinates through the route list,
        # so this fallback is only used for duration estimation. Distances are
        # set by the buoy selector ordering, not exact geography.
        points.append((home_lat + (index + 1) * 0.015, home_lon + (index + 1) * 0.015))
    distance = 0.0
    for a, b in pairwise(points):
        distance += _distance_km(a[0], a[1], b[0], b[1])
    return max(distance, 6.0)


def _build_trip_activity(
    rng: np.random.Generator,
    trips: list[TripPlan],
    incident_trip_ids: set[str],
    buoys: list[dict[str, Any]],
    squall_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    buoy_lookup = {buoy['id']: buoy for buoy in buoys}
    buoy_contacts: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    sos_events: list[dict[str, Any]] = []
    vessel_reason_cycle = ['engine_failure', 'capsize', 'loss_of_signal', 'adverse_weather']
    incident_counter = 0
    for trip in trips:
        profile_route = [buoy_lookup[buoy_id] for buoy_id in trip.route_buoy_ids]
        outbound_distances = _cumulative_route_distances(trip.home_lat, trip.home_lon, profile_route)
        speed = max(10.0, trip.cruising_speed_kph * float(rng.uniform(0.9, 1.08)))
        outbound_hours = outbound_distances[-1] / speed
        fishing_hours = float(_clip(rng.normal(3.8, 0.9), 1.8, 6.5))
        inbound_start = trip.departure_at + timedelta(hours=outbound_hours + fishing_hours)
        route_times_out = [trip.departure_at + timedelta(hours=distance / speed) for distance in outbound_distances]
        route_times_in = [inbound_start]
        return_distance = 0.0
        previous_lat = profile_route[-1]['lat']
        previous_lon = profile_route[-1]['lon']
        for buoy in reversed(profile_route[:-1]):
            return_distance += _distance_km(previous_lat, previous_lon, buoy['lat'], buoy['lon'])
            route_times_in.append(inbound_start + timedelta(hours=return_distance / speed))
            previous_lat, previous_lon = buoy['lat'], buoy['lon']
        if trip.trip_id in incident_trip_ids:
            incident_counter += 1
            cutoff = int(rng.integers(2, len(profile_route) + 1))
            cutoff = min(cutoff, len(profile_route))
            contact_rows = []
            for seq_index, (buoy, contact_at) in enumerate(
                zip(profile_route[:cutoff], route_times_out[:cutoff], strict=True),
                start=1,
            ):
                contact_rows.append(
                    {
                        'buoy_id': buoy['id'],
                        'vessel_id': trip.vessel_id,
                        'trip_id': trip.trip_id,
                        'sequence_no': seq_index,
                        'observed_at': contact_at,
                        'latitude': buoy['lat'],
                        'longitude': buoy['lon'],
                        'contact_type': 'mesh_ping',
                        'contact_value': f'outbound-{seq_index}',
                        'created_at': contact_at,
                        'is_synthetic': True,
                    }
                )
            buoy_contacts.extend(contact_rows)
            last_contact = contact_rows[-1]
            drift_track = _simulate_drift_track(
                last_contact['observed_at'],
                last_contact['latitude'],
                last_contact['longitude'],
                rng,
                vessel_reason_cycle[(incident_counter - 1) % len(vessel_reason_cycle)],
                squall_events,
            )
            incidents.append(
                {
                    'id': incident_counter,
                    'vessel_id': trip.vessel_id,
                    'last_contact_at': last_contact['observed_at'],
                    'last_contact_buoy_id': last_contact['buoy_id'],
                    'last_contact_lat': last_contact['latitude'],
                    'last_contact_lon': last_contact['longitude'],
                    'reported_missing_at': last_contact['observed_at'] + timedelta(hours=float(rng.uniform(1.5, 4.5))),
                    'abnormal_reason': vessel_reason_cycle[(incident_counter - 1) % len(vessel_reason_cycle)],
                    'true_track': drift_track,
                    'is_synthetic': True,
                }
            )
            sos_events.append(
                {
                    'id': incident_counter,
                    'vessel_id': trip.vessel_id,
                    'buoy_id': last_contact['buoy_id'],
                    'latitude': last_contact['latitude'],
                    'longitude': last_contact['longitude'],
                    'note': 'Synthetic distress after contact loss',
                    'created_at': last_contact['observed_at'] + timedelta(minutes=int(rng.integers(5, 25))),
                    'is_synthetic': True,
                }
            )
            continue

        contact_rows = []
        seq_no = 1
        for buoy, contact_at in zip(profile_route, route_times_out, strict=True):
            contact_rows.append(
                {
                    'buoy_id': buoy['id'],
                    'vessel_id': trip.vessel_id,
                    'trip_id': trip.trip_id,
                    'sequence_no': seq_no,
                    'observed_at': contact_at,
                    'latitude': buoy['lat'],
                    'longitude': buoy['lon'],
                    'contact_type': 'mesh_ping',
                    'contact_value': f'outbound-{seq_no}',
                    'created_at': contact_at,
                    'is_synthetic': True,
                }
            )
            seq_no += 1
        for buoy, contact_at in zip(reversed(profile_route), route_times_in, strict=True):
            contact_rows.append(
                {
                    'buoy_id': buoy['id'],
                    'vessel_id': trip.vessel_id,
                    'trip_id': trip.trip_id,
                    'sequence_no': seq_no,
                    'observed_at': contact_at,
                    'latitude': buoy['lat'],
                    'longitude': buoy['lon'],
                    'contact_type': 'mesh_ping',
                    'contact_value': f'inbound-{seq_no}',
                    'created_at': contact_at,
                    'is_synthetic': True,
                }
            )
            seq_no += 1
        buoy_contacts.extend(contact_rows)

    buoy_contacts.sort(key=lambda row: (row['observed_at'], row['vessel_id'], row['sequence_no']))
    incidents.sort(key=lambda row: (row['last_contact_at'], row['vessel_id']))
    sos_events.sort(key=lambda row: (row['created_at'], row['vessel_id']))
    return buoy_contacts, incidents, sos_events


def _cumulative_route_distances(
    start_lat: float,
    start_lon: float,
    points: list[dict[str, Any]],
) -> list[float]:
    distances: list[float] = []
    total = 0.0
    prev_lat, prev_lon = start_lat, start_lon
    for point in points:
        total += _distance_km(prev_lat, prev_lon, point['lat'], point['lon'])
        distances.append(total)
        prev_lat, prev_lon = point['lat'], point['lon']
    return distances


def _simulate_drift_track(
    start_at: datetime,
    start_lat: float,
    start_lon: float,
    rng: np.random.Generator,
    reason: str,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    track: list[dict[str, Any]] = []
    downwind, crosswind = _leeway_spec(reason)
    cross_sign = float(rng.choice([-1.0, 1.0]))
    lat = start_lat
    lon = start_lon
    for step in range(49):
        observed_at = start_at + step * TRACK_STEP
        true_u, true_v = _current_vector(lat, lon, observed_at, DEFAULT_START)
        wind_u, wind_v = _synthetic_wind_vector(lat, lon, observed_at)
        leeway_u = downwind * wind_u + cross_sign * crosswind * (-wind_v)
        leeway_v = downwind * wind_v + cross_sign * crosswind * wind_u
        u = true_u + leeway_u
        v = true_v + leeway_v
        drift_m_per_s = math.hypot(u, v)
        if drift_m_per_s > 1.5:
            scale = 1.5 / drift_m_per_s
            u *= scale
            v *= scale
        track.append(
            {
                'observed_at': observed_at,
                'lat': round(lat, 6),
                'lon': round(lon, 6),
                'u_mps': round(u, 3),
                'v_mps': round(v, 3),
            }
        )
        dt_seconds = TRACK_STEP.total_seconds()
        next_lat = lat + (v * dt_seconds) / 1000.0 / KM_PER_DEG_LAT
        next_lon = lon + (u * dt_seconds) / 1000.0 / _km_per_deg_lon(lat)

        # Beaching. Advection is pure physics and knows nothing about the
        # coastline, so an unconstrained track walks straight across Panay.
        # A real drifting object that reaches the shore stops there, so the
        # track terminates at the last position still in the water rather than
        # being nudged back out to sea - which would fake a drift path that
        # never happened.
        if not geo.point_in_water(next_lat, next_lon):
            break

        lat = next_lat
        lon = next_lon
    return track


async def regenerate(database_url: str, plan: SimulationPlan) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            await conn.execute(
                '''
                TRUNCATE TABLE
                  incidents,
                  current_observations,
                  barometric_readings,
                  squall_events,
                  buoy_contacts,
                  sos_events,
                  buoys,
                  vessels
                RESTART IDENTITY CASCADE
                '''
            )
            await _insert_vessels(conn, plan.vessels)
            await _insert_buoys(conn, plan.buoys)
            await _insert_buoy_contacts(conn, plan.buoy_contacts)
            await _insert_barometric_readings(conn, plan.barometric_readings)
            await _insert_squall_events(conn, plan.squall_events)
            await _insert_current_observations(conn, plan.current_observations)
            await _insert_incidents(conn, plan.incidents)
            await _insert_sos_events(conn, plan.sos_events)
    finally:
        await conn.close()


async def _insert_vessels(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO vessels (
          id,
          boat_name,
          home_buoy_id,
          preferred_heading_deg,
          typical_departure_local,
          typical_return_local,
          cruising_speed_kph,
          route_buoy_ids,
          created_at,
          is_synthetic
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10)
        ''',
        [
            (
                row['id'],
                row['boat_name'],
                row['home_buoy_id'],
                row['preferred_heading_deg'],
                row['typical_departure_local'],
                row['typical_return_local'],
                row['cruising_speed_kph'],
                json.dumps(row['route_buoy_ids']),
                row['created_at'],
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


async def _insert_buoys(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO buoys (
          id, vessel_id, label, created_at, lat, lon,
          contact_radius_m, lora_radius_m, is_gateway_linked, is_synthetic
        )
        VALUES ($1, NULL, $2, $3, $4, $5, $6, $7, $8, $9)
        ''',
        [
            (
                row['id'],
                row['label'],
                row['created_at'],
                row['lat'],
                row['lon'],
                row['contact_radius_m'],
                row['lora_radius_m'],
                row['is_gateway_linked'],
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


async def _insert_buoy_contacts(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO buoy_contacts (
          buoy_id,
          vessel_id,
          trip_id,
          sequence_no,
          observed_at,
          latitude,
          longitude,
          contact_type,
          contact_value,
          created_at,
          is_synthetic
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''',
        [
            (
                row['buoy_id'],
                row['vessel_id'],
                row['trip_id'],
                row['sequence_no'],
                row['observed_at'],
                row['latitude'],
                row['longitude'],
                row['contact_type'],
                row['contact_value'],
                row['created_at'],
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


async def _insert_barometric_readings(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO barometric_readings (buoy_id, observed_at, pressure_hpa, is_synthetic)
        VALUES ($1, $2, $3, $4)
        ''',
        [
            (row['buoy_id'], row['observed_at'], row['pressure_hpa'], row['is_synthetic'])
            for row in rows
        ],
    )


async def _insert_squall_events(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO squall_events (
          id,
          started_at,
          peak_at,
          ended_at,
          center_lat,
          center_lon,
          front_origin_lat,
          front_origin_lon,
          bearing_deg,
          speed_kph,
          pressure_drop_hpa,
          rise_minutes,
          hold_minutes,
          observed_buoy_ids,
          is_synthetic
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb, $15)
        ''',
        [
            (
                row['id'],
                row['started_at'],
                row['peak_at'],
                row['ended_at'],
                row['center_lat'],
                row['center_lon'],
                row['front_origin_lat'],
                row['front_origin_lon'],
                row['bearing_deg'],
                row['speed_kph'],
                row['pressure_drop_hpa'],
                row['rise_minutes'],
                row['hold_minutes'],
                json.dumps(row['observed_buoy_ids']),
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


async def _insert_current_observations(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO current_observations (
          buoy_id,
          observed_at,
          true_u_mps,
          true_v_mps,
          observed_u_mps,
          observed_v_mps,
          is_synthetic
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''',
        [
            (
                row['buoy_id'],
                row['observed_at'],
                row['true_u_mps'],
                row['true_v_mps'],
                row['observed_u_mps'],
                row['observed_v_mps'],
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


async def _insert_incidents(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO incidents (
          id,
          vessel_id,
          last_contact_at,
          last_contact_buoy_id,
          last_contact_lat,
          last_contact_lon,
          reported_missing_at,
          abnormal_reason,
          true_track,
          is_synthetic
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
        ''',
        [
            (
                row['id'],
                row['vessel_id'],
                row['last_contact_at'],
                row['last_contact_buoy_id'],
                row['last_contact_lat'],
                row['last_contact_lon'],
                row['reported_missing_at'],
                row['abnormal_reason'],
                json.dumps(row['true_track'], default=_json_default),
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


async def _insert_sos_events(conn: asyncpg.Connection, rows: list[dict[str, Any]]) -> None:
    await conn.executemany(
        '''
        INSERT INTO sos_events (id, vessel_id, buoy_id, latitude, longitude, note, created_at, is_synthetic)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''',
        [
            (
                row['id'],
                row['vessel_id'],
                row['buoy_id'],
                row['latitude'],
                row['longitude'],
                row['note'],
                row['created_at'],
                row['is_synthetic'],
            )
            for row in rows
        ],
    )


def _print_summary(plan: SimulationPlan) -> None:
    counts = plan.counts()
    for name in (
        'vessels',
        'buoys',
        'buoy_contacts',
        'barometric_readings',
        'squall_events',
        'current_observations',
        'incidents',
        'sos_events',
    ):
        print(f'{name}: {counts[name]}')
    example = plan.example_squall()
    if example:
        observed = ', '.join(example['observed_buoy_ids']) if example['observed_buoy_ids'] else 'none'
        print(
            'example_squall_event: '
            f'id={example["id"]} '
            f'started_at={example["started_at"].isoformat()} '
            f'buoys={observed}'
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate synthetic AqOne simulation data')
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--database-url', default=os.environ.get('DATABASE_URL'))
    return parser.parse_args()


async def _async_main() -> None:
    args = _parse_args()
    if not args.database_url:
        raise RuntimeError('DATABASE_URL is required')
    plan = build_plan(days=args.days, seed=args.seed)
    await regenerate(args.database_url, plan)
    _print_summary(plan)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == '__main__':
    main()
