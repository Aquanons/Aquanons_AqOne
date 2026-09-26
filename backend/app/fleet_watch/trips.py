from dataclasses import dataclass
from datetime import datetime

from app.fleet_watch.watch import AtSea, Checkin


@dataclass(frozen=True)
class OpenTrip:
    trip_id: str
    reporter_type: str


@dataclass(frozen=True)
class TripAction:
    kind: str
    trip_id: str | None


def auto_trip_id(vessel_id: str, observed_at: datetime) -> str:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError('datetime must be timezone-aware')
    return f'auto-{vessel_id}-{int(observed_at.timestamp())}'


def trip_action(vessel_id: str, checkin: Checkin, open_trip: OpenTrip | None, at_sea: AtSea) -> TripAction:
    if checkin.observed_at.tzinfo is None or checkin.observed_at.utcoffset() is None:
        raise ValueError('datetime must be timezone-aware')
    if open_trip is None:
        if checkin.has_fix and at_sea(checkin.latitude, checkin.longitude):
            return TripAction('open', auto_trip_id(vessel_id, checkin.observed_at))
        return TripAction('none', None)
    if not checkin.has_fix:
        return TripAction('attach', open_trip.trip_id)
    if at_sea(checkin.latitude, checkin.longitude):
        return TripAction('attach', open_trip.trip_id)
    if open_trip.reporter_type == 'gateway':
        return TripAction('complete', open_trip.trip_id)
    return TripAction('attach', open_trip.trip_id)
