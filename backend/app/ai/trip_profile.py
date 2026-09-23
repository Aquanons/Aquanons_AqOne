"""Explainable trip profiling and anomaly scoring.

Assumptions:
- Trips are repeated buoy-contact sequences.
- The most common historical route is the habitual route.
- Inter-contact intervals are approximately normal per leg.
- Distance offshore is approximated from a fixed coastal origin near New
  Washington, Aklan.
- Weather severity is a simple scalar derived from wind and weather code.
- Cold-start vessels (<3 trips) inherit fleet averages and are marked
  low_confidence.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import pairwise
from statistics import mean
from typing import Any

import numpy as np

CENTER_LAT = 11.6892
CENTER_LON = 122.3667
MANILA_TZ = timezone(timedelta(hours=8))

ANOMALY_CONFIG = {
    'thresholds': {'normal': 0.25, 'watch': 0.35, 'overdue': 0.55, 'alert': 0.65},
    'weights': {'overdue': 0.85, 'sequence': 0.10, 'distance': 0.03, 'weather': 0.02},
    'minimum_trips_for_confidence': 3,
    'expected_window_padding_minutes': 15,
    'expected_window_sigma': 0.75,
}


@dataclass(frozen=True)
class WeatherSnapshot:
    source: str
    degraded: bool
    wind_speed_mps: float
    wind_direction_deg: float
    weather_code: int


@dataclass(frozen=True)
class ContactPoint:
    buoy_id: str
    observed_at: datetime
    latitude: float
    longitude: float


@dataclass(frozen=True)
class TripSample:
    vessel_id: str
    trip_id: str
    contacts: list[ContactPoint]


@dataclass(frozen=True)
class VesselProfile:
    vessel_id: str
    trip_count: int
    low_confidence: bool
    typical_departure_hour: float
    departure_hour_std: float
    typical_sequence: list[str]
    interval_stats: list[dict[str, float]]
    typical_trip_duration_minutes: dict[str, float]
    typical_max_distance_km: dict[str, float]
    rebuilt_at: str
    source: str = 'synthetic'

    @property
    def is_synthetic(self) -> bool:
        return self.source == 'synthetic'

    def to_json(self) -> dict[str, Any]:
        return {
            'vessel_id': self.vessel_id,
            'trip_count': self.trip_count,
            'low_confidence': self.low_confidence,
            'typical_departure_hour': self.typical_departure_hour,
            'departure_hour_std': self.departure_hour_std,
            'typical_sequence': self.typical_sequence,
            'interval_stats': self.interval_stats,
            'typical_trip_duration_minutes': self.typical_trip_duration_minutes,
            'typical_max_distance_km': self.typical_max_distance_km,
            'rebuilt_at': self.rebuilt_at,
            'source': self.source,
        }

    def for_vessel(self, vessel_id: str, low_confidence: bool) -> VesselProfile:
        return VesselProfile(
            vessel_id=vessel_id,
            trip_count=self.trip_count,
            low_confidence=low_confidence,
            typical_departure_hour=self.typical_departure_hour,
            departure_hour_std=self.departure_hour_std,
            typical_sequence=self.typical_sequence,
            interval_stats=self.interval_stats,
            typical_trip_duration_minutes=self.typical_trip_duration_minutes,
            typical_max_distance_km=self.typical_max_distance_km,
            rebuilt_at=self.rebuilt_at,
            source=self.source,
        )


@dataclass(frozen=True)
class ExpectedContact:
    buoy_id: str | None
    window_start: datetime
    window_end: datetime
    expected_at: datetime
    leg_index: int


@dataclass(frozen=True)
class AnomalyFactor:
    name: str
    value: float
    weight: float
    contribution: float
    explanation: str


@dataclass(frozen=True)
class AnomalyScore:
    vessel_id: str
    trip_id: str
    score: float
    status: str
    factors: list[AnomalyFactor]
    expected_contact: ExpectedContact
    low_confidence: bool
    observed_at: datetime
    last_contact_at: datetime
    profile: VesselProfile

    def to_response(self) -> dict[str, Any]:
        return {
            'vessel_id': self.vessel_id,
            'trip_id': self.trip_id,
            'score': round(self.score, 4),
            'status': self.status,
            'low_confidence': self.low_confidence,
            'observed_at': self.observed_at.isoformat(),
            'last_contact_at': self.last_contact_at.isoformat(),
            'expected_contact': {
                'buoy_id': self.expected_contact.buoy_id,
                'window_start': self.expected_contact.window_start.isoformat(),
                'window_end': self.expected_contact.window_end.isoformat(),
                'expected_at': self.expected_contact.expected_at.isoformat(),
                'leg_index': self.expected_contact.leg_index,
            },
            'factors': [factor.__dict__ for factor in self.factors],
            'profile': self.profile.to_json(),
        }


def _ensure_tz(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=MANILA_TZ)
    return ts.astimezone(MANILA_TZ)


def _km_per_deg_lon(lat: float) -> float:
    return 111.320 * math.cos(math.radians(lat))


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = lat2_r - lat1_r
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _mean_std(values: list[float]) -> dict[str, float]:
    if not values:
        return {'mean': 0.0, 'std': 0.0, 'p10': 0.0, 'p90': 0.0}
    arr = np.asarray(values, dtype=float)
    return {
        'mean': float(arr.mean()),
        'std': float(arr.std(ddof=0)),
        'p10': float(np.percentile(arr, 10)),
        'p90': float(np.percentile(arr, 90)),
    }


def _compress_route(contacts: list[ContactPoint]) -> list[str]:
    route: list[str] = []
    for item in contacts:
        if not route or route[-1] != item.buoy_id:
            route.append(item.buoy_id)
    return route


def _group_trip_samples(rows: list[dict[str, Any]]) -> dict[str, list[TripSample]]:
    grouped: dict[str, dict[str, list[ContactPoint]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get('latitude') is None or row.get('longitude') is None:
            continue
        grouped[str(row['vessel_id'])][str(row['trip_id'])].append(
            ContactPoint(
                buoy_id=str(row['buoy_id']),
                observed_at=row['observed_at'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
            )
        )
    samples: dict[str, list[TripSample]] = {}
    for vessel_id, trips in grouped.items():
        samples[vessel_id] = [
            TripSample(vessel_id=vessel_id, trip_id=trip_id, contacts=sorted(points, key=lambda c: c.observed_at))
            for trip_id, points in trips.items()
        ]
        samples[vessel_id].sort(key=lambda sample: sample.contacts[0].observed_at)
    return samples


def build_profiles_from_contacts(
    rows: list[dict[str, Any]],
    *,
    built_at: datetime | None = None,
    as_of: datetime | None = None,
    exclude_trip_ids: set[str] | list[str] | None = None,
    trip_states: dict[str, dict[str, Any]] | None = None,
) -> dict[str, VesselProfile]:
    built_at = _ensure_tz(built_at or datetime.now(MANILA_TZ))
    as_of_tz = _ensure_tz(as_of) if as_of else None
    exclude_set = set(exclude_trip_ids) if exclude_trip_ids else set()

    # Leakage prevention (Task 3.6 & Scenario C6): only use historical contacts strictly
    # before as_of, exclude candidate trip_ids, and exclude trips known to be non-completed
    # (abnormal, open, cancelled) so they do not contaminate the normal profile baseline.
    filtered_rows = rows
    if as_of_tz or exclude_set or trip_states:
        filtered_rows = [
            r for r in rows
            if (as_of_tz is None or _ensure_tz(r['observed_at']) < as_of_tz)
            and (not exclude_set or str(r.get('trip_id')) not in exclude_set)
            and (
                not trip_states
                or trip_states.get(str(r.get('trip_id')), {}).get('status', 'completed') == 'completed'
            )
        ]

    grouped = _group_trip_samples(filtered_rows)
    all_trips = [trip for trips in grouped.values() for trip in trips]
    fleet = _build_profile('fleet', all_trips, built_at, low_confidence=False)
    profiles: dict[str, VesselProfile] = {'fleet': fleet}
    for vessel_id, trips in grouped.items():
        if len(trips) < ANOMALY_CONFIG['minimum_trips_for_confidence']:
            profiles[vessel_id] = fleet.for_vessel(vessel_id, low_confidence=True)
        else:
            profiles[vessel_id] = _build_profile(vessel_id, trips, built_at, low_confidence=False)

    # Ensure all vessels in original rows have a profile entry even if all contacts were filtered
    for r in rows:
        v_id = str(r['vessel_id'])
        if v_id not in profiles:
            profiles[v_id] = fleet.for_vessel(v_id, low_confidence=True)

    if trip_states:
        for state in trip_states.values():
            v_id = str(state.get('vessel_id') or '')
            if v_id and v_id not in profiles:
                profiles[v_id] = fleet.for_vessel(v_id, low_confidence=True)

    return profiles


def _build_profile(vessel_id: str, trips: list[TripSample], built_at: datetime, low_confidence: bool) -> VesselProfile:
    if not trips:
        return VesselProfile(
            vessel_id=vessel_id,
            trip_count=0,
            low_confidence=True,
            typical_departure_hour=0.0,
            departure_hour_std=0.0,
            typical_sequence=[],
            interval_stats=[],
            typical_trip_duration_minutes={'mean': 0.0, 'std': 0.0, 'p10': 0.0, 'p90': 0.0},
            typical_max_distance_km={'mean': 0.0, 'std': 0.0, 'p10': 0.0, 'p90': 0.0},
            rebuilt_at=built_at.isoformat(),
        )

    departure_hours = [
        contacts[0].observed_at.astimezone(MANILA_TZ).hour
        + contacts[0].observed_at.astimezone(MANILA_TZ).minute / 60.0
        for contacts in (trip.contacts for trip in trips)
        if contacts
    ]
    trip_durations = [
        (trip.contacts[-1].observed_at - trip.contacts[0].observed_at).total_seconds() / 60.0
        for trip in trips
        if len(trip.contacts) >= 2
    ]
    max_distances = [
        max(_distance_km(CENTER_LAT, CENTER_LON, c.latitude, c.longitude) for c in trip.contacts)
        for trip in trips
        if trip.contacts
    ]
    sequence_counts = Counter(tuple(_compress_route(trip.contacts)) for trip in trips if trip.contacts)
    typical_sequence = list(sequence_counts.most_common(1)[0][0]) if sequence_counts else []
    matching_trips = [trip for trip in trips if _compress_route(trip.contacts) == typical_sequence] or trips
    interval_by_leg: dict[int, list[float]] = defaultdict(list)
    for trip in matching_trips:
        for index, (left, right) in enumerate(pairwise(trip.contacts)):
            interval_by_leg[index].append((right.observed_at - left.observed_at).total_seconds() / 60.0)
    interval_stats = [
        {'leg_index': float(index), **_mean_std(values)}
        for index, values in sorted(interval_by_leg.items())
    ]
    if not departure_hours:
        departure_hours = [0.0]
    return VesselProfile(
        vessel_id=vessel_id,
        trip_count=len(trips),
        low_confidence=low_confidence,
        typical_departure_hour=float(mean(departure_hours)),
        departure_hour_std=float(np.std(np.asarray(departure_hours), ddof=0)),
        typical_sequence=typical_sequence,
        interval_stats=interval_stats,
        typical_trip_duration_minutes=_mean_std(trip_durations),
        typical_max_distance_km=_mean_std(max_distances),
        rebuilt_at=built_at.isoformat(),
    )


def _interval_for_leg(profile: VesselProfile, leg_index: int) -> dict[str, float]:
    if not profile.interval_stats:
        return {'leg_index': float(leg_index), 'mean': 0.0, 'std': 0.0, 'p10': 0.0, 'p90': 0.0}
    for item in profile.interval_stats:
        if int(item['leg_index']) == leg_index:
            return item
    return profile.interval_stats[-1]


def expected_next_contact(
    profile: VesselProfile,
    contacts: list[ContactPoint],
    *,
    observed_at: datetime | None = None,
) -> ExpectedContact:
    observed_at = _ensure_tz(observed_at or (contacts[-1].observed_at if contacts else datetime.now(MANILA_TZ)))
    route = _compress_route(contacts)
    prefix_len = 0
    for left, right in zip(route, profile.typical_sequence):  # noqa: B905
        if left != right:
            break
        prefix_len += 1
    leg_index = max(0, prefix_len - 1)
    next_buoy = profile.typical_sequence[prefix_len] if prefix_len < len(profile.typical_sequence) else None
    last_contact_at = contacts[-1].observed_at if contacts else observed_at
    interval = _interval_for_leg(profile, leg_index)
    mean_minutes = interval['mean'] or profile.typical_trip_duration_minutes['mean'] / max(
        1, len(profile.typical_sequence) or 1
    )
    std_minutes = interval['std'] or max(10.0, mean_minutes * 0.25)
    padding = ANOMALY_CONFIG['expected_window_padding_minutes']
    expected_at = last_contact_at + timedelta(minutes=mean_minutes)
    window_start = last_contact_at + timedelta(
        minutes=max(5.0, mean_minutes - ANOMALY_CONFIG['expected_window_sigma'] * std_minutes)
    )
    window_end = last_contact_at + timedelta(
        minutes=mean_minutes + ANOMALY_CONFIG['expected_window_sigma'] * std_minutes + padding
    )
    return ExpectedContact(next_buoy, window_start, window_end, expected_at, leg_index)


def _score_factor(value: float, weight: float, explanation: str, name: str) -> AnomalyFactor:
    bounded = max(0.0, min(1.0, value))
    return AnomalyFactor(
        name=name,
        value=bounded,
        weight=weight,
        contribution=bounded * weight,
        explanation=explanation,
    )


def score_to_status(score: float) -> str:
    thresholds = ANOMALY_CONFIG['thresholds']
    if score >= thresholds['alert']:
        return 'alert'
    if score >= thresholds['overdue']:
        return 'overdue'
    if score >= thresholds['watch']:
        return 'watch'
    return 'normal'


def _synthetic_weather_snapshot(lat: float, lon: float, at: datetime) -> WeatherSnapshot:
    hours = at.astimezone(MANILA_TZ).hour + at.minute / 60.0
    daily = 2.0 * math.pi * hours / 24.0
    seasonal = 2.0 * math.pi * (at.timetuple().tm_yday / 365.0)
    wind_speed = (
        6.0
        + 1.8 * math.sin(daily + (lat - CENTER_LAT) * 0.3)
        + 1.2 * math.cos(seasonal + (lon - CENTER_LON) * 0.2)
    )
    wind_speed = float(np.clip(wind_speed, 1.0, 15.0))
    wind_direction = (80.0 + 45.0 * math.sin(seasonal + (lat - CENTER_LAT))) % 360.0
    weather_code = 95 if wind_speed > 10.5 else 3 if wind_speed > 8.0 else 0
    return WeatherSnapshot('synthetic', True, wind_speed, wind_direction, weather_code)


def weather_severity(snapshot: WeatherSnapshot) -> float:
    wind_component = min(1.0, snapshot.wind_speed_mps / 12.0)
    code_component = (
        1.0
        if snapshot.weather_code in {95, 96, 99}
        else 0.3
        if snapshot.weather_code in {61, 63, 65}
        else 0.0
    )
    return max(0.0, min(1.0, 0.7 * wind_component + 0.3 * code_component))


def _sequence_deviation(profile: VesselProfile, route: list[str]) -> float:
    if not profile.typical_sequence or not route:
        return 0.0
    prefix = 0
    for left, right in zip(route, profile.typical_sequence):  # noqa: B905
        if left != right:
            break
        prefix += 1

    # An unfinished normal prefix along the typical sequence is on-route, not anomalous
    if prefix == len(route) and len(route) <= len(profile.typical_sequence):
        return 0.0

    expected_len = max(len(profile.typical_sequence), len(route), 1)
    mismatch = 1.0 - (prefix / expected_len)
    if route and prefix < len(route) and prefix < len(profile.typical_sequence):
        mismatch += 0.15
    return max(0.0, min(1.0, mismatch))


def score_trip(
    profile: VesselProfile,
    contacts: list[ContactPoint],
    *,
    as_of: datetime | None = None,
    trip_id: str | None = None,
    trip_state: dict[str, Any] | None = None,
    weather_provider: Callable[[float, float, datetime], WeatherSnapshot] | None = None,
) -> AnomalyScore:
    as_of = _ensure_tz(as_of or (contacts[-1].observed_at if contacts else datetime.now(MANILA_TZ)))
    effective_trip_id = trip_id or (contacts[0].observed_at.date().isoformat() if contacts else 'unknown')
    if not contacts:
        dep_at = trip_state.get('departure_at') if trip_state else None
        dep_tz = (
            _ensure_tz(dep_at)
            if isinstance(dep_at, datetime)
            else (_ensure_tz(datetime.fromisoformat(str(dep_at))) if dep_at else None)
        )
        rep_at = trip_state.get('reported_at') if trip_state else None
        rep_tz = (
            _ensure_tz(rep_at)
            if isinstance(rep_at, datetime)
            else (_ensure_tz(datetime.fromisoformat(str(rep_at))) if rep_at else None)
        )
        last_contact_tz = dep_tz or rep_tz or as_of
        exp_ret = trip_state.get('expected_return_at') if trip_state else None
        if exp_ret:
            exp_ret_tz = (
                _ensure_tz(exp_ret)
                if isinstance(exp_ret, datetime)
                else _ensure_tz(datetime.fromisoformat(str(exp_ret)))
            )
            overdue_minutes = max(0.0, (as_of - exp_ret_tz).total_seconds() / 60.0)
            if overdue_minutes > 0:
                ret_factor = 1.0 - math.exp(-overdue_minutes / 30.0)
                score_val = max(0.55, min(1.0, ret_factor))
                status = 'alert' if score_val >= ANOMALY_CONFIG['thresholds']['alert'] else 'overdue'
                time_str = exp_ret_tz.strftime("%H:%M")
                explanation = f'Overdue past expected return deadline ({time_str}) with zero contacts observed.'
                factor = _score_factor(score_val, 1.0, explanation, 'overdue')
                expected = ExpectedContact(None, dep_tz or as_of, exp_ret_tz, exp_ret_tz, 0)
                return AnomalyScore(
                    profile.vessel_id,
                    effective_trip_id,
                    score_val,
                    status,
                    [factor],
                    expected,
                    True,
                    as_of,
                    last_contact_tz,
                    profile,
                )
        expected = ExpectedContact(None, as_of, as_of, as_of, 0)
        factor = _score_factor(0.0, 1.0, 'No contacts observed yet.', 'empty')
        return AnomalyScore(
            profile.vessel_id,
            effective_trip_id,
            0.0,
            'normal',
            [factor],
            expected,
            profile.low_confidence,
            as_of,
            last_contact_tz,
            profile,
        )

    route = _compress_route(contacts)
    expected = expected_next_contact(profile, contacts, observed_at=as_of)
    overdue_minutes = max(0.0, (as_of - expected.window_end).total_seconds() / 60.0)
    overdue_scale = max(10.0, (expected.window_end - expected.window_start).total_seconds() / 120.0)
    overdue_factor = 1.0 - math.exp(-overdue_minutes / overdue_scale) if overdue_minutes > 0 else 0.0
    overdue_explanation = 'Late beyond the expected-contact window.'

    # Task 3.5 & 3.7: evaluate explicit trip expectations and welfare state if known
    if trip_state:
        exp_ret = trip_state.get('expected_return_at')
        if exp_ret:
            if isinstance(exp_ret, datetime):
                exp_ret_tz = _ensure_tz(exp_ret)
            else:
                exp_ret_tz = _ensure_tz(datetime.fromisoformat(str(exp_ret)))
            overdue_return_minutes = max(0.0, (as_of - exp_ret_tz).total_seconds() / 60.0)
            if overdue_return_minutes > 0:
                ret_factor = 1.0 - math.exp(-overdue_return_minutes / 30.0)
                overdue_factor = max(overdue_factor, ret_factor)
                overdue_explanation = f'Overdue past expected return deadline ({exp_ret_tz.strftime("%H:%M")}).'
            elif overdue_minutes > 0:
                # Still before expected return; contact delay may be inter-buoy or gateway outage
                overdue_factor = min(overdue_factor, 0.30)
                time_str = exp_ret_tz.strftime("%H:%M")
                overdue_explanation = f'Inter-buoy contact delay before expected return ({time_str}).'
            else:
                overdue_explanation = 'Within expected return window.'

        welfare = trip_state.get('welfare_status')
        if welfare == 'safe':
            overdue_factor = min(overdue_factor, 0.15)
            overdue_explanation += ' (Vessel self-reported safe).'
        elif welfare == 'distress':
            overdue_factor = 1.0
            overdue_explanation = 'Vessel or responder reported distress.'

    sequence_factor = _sequence_deviation(profile, route)
    current_distance = max(_distance_km(CENTER_LAT, CENTER_LON, c.latitude, c.longitude) for c in contacts)
    typical_distance = profile.typical_max_distance_km['mean'] or current_distance or 1.0
    distance_factor = max(
        0.0,
        min(
            1.0,
            (current_distance - typical_distance)
            / max(1.0, profile.typical_max_distance_km['std'] * 2.0 + 1.0),
        ),
    )
    weather_factor = 0.0
    weather_reason = 'Weather conditions not assessed (no connected provider).'
    if weather_provider is not None:
        weather = weather_provider(
            contacts[-1].latitude, contacts[-1].longitude, contacts[-1].observed_at
        )
        weather_factor = weather_severity(weather)
        weather_reason = (
            'Adverse weather at the last known position/time.'
            if weather_factor > 0
            else 'Weather conditions normal at last known position.'
        )
    elif profile.is_synthetic:
        weather = _synthetic_weather_snapshot(
            contacts[-1].latitude, contacts[-1].longitude, contacts[-1].observed_at
        )
        weather_factor = weather_severity(weather)
        weather_reason = (
            'Adverse weather at the last known position/time.'
            if weather_factor > 0
            else 'Weather conditions normal at last known position.'
        )

    if (as_of - contacts[-1].observed_at) > timedelta(hours=2):
        weather_reason += ' (Position is stale).'

    weights = ANOMALY_CONFIG['weights']
    factors = [
        _score_factor(
            overdue_factor,
            weights['overdue'],
            overdue_explanation,
            'overdue',
        ),
        _score_factor(
            sequence_factor,
            weights['sequence'],
            (
                'Observed buoy sequence diverges from the habitual route.'
                if sequence_factor > 0
                else 'Following expected route sequence.'
            ),
            'sequence',
        ),
        _score_factor(
            distance_factor,
            weights['distance'],
            'Distance from departure origin exceeds typical trip radius.',
            'distance',
        ),
        _score_factor(
            weather_factor,
            weights['weather'],
            weather_reason,
            'weather',
        ),
    ]
    score = min(1.0, sum(item.contribution for item in factors))
    if profile.low_confidence:
        score = min(1.0, score * 0.9)
    status = score_to_status(score)
    return AnomalyScore(
        vessel_id=profile.vessel_id,
        trip_id=effective_trip_id,
        score=score,
        status=status,
        factors=factors,
        expected_contact=expected,
        low_confidence=profile.low_confidence,
        observed_at=as_of,
        last_contact_at=contacts[-1].observed_at,
        profile=profile,
    )
