from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import floor

from app.fleet_watch.tier import INTERVAL_S, Tier

MISSED_AFTER_INTERVALS = 3
GRACE_FRACTION = 0.2
FLEET_SILENCE_SHARE = 0.30
FLEET_SILENCE_MIN_VESSELS = 3
RECEIVER_STALE_AFTER = timedelta(minutes=3)
RECENT_POSITION = timedelta(minutes=30)

AtSea = Callable[[float, float], bool]


@dataclass(frozen=True)
class Checkin:
    observed_at: datetime
    latitude: float | None
    longitude: float | None
    path: str
    fix_age_s: int | None

    @property
    def has_fix(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass(frozen=True)
class VesselWatchInput:
    vessel_id: str
    trip_id: str | None
    latest: Checkin
    last_positioned: Checkin | None
    tier_at_latest: Tier
    stagnant_until: datetime | None


@dataclass(frozen=True)
class VesselVerdict:
    vessel_id: str
    trip_id: str | None
    state: str
    interval_s: int
    deadline: datetime | None
    missed_count: int
    path: str


@dataclass(frozen=True)
class FleetSilence:
    active: bool
    reason: str | None


CaseConfidence = str


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('datetime must be timezone-aware')


def is_watched(latest: Checkin, last_positioned: Checkin | None, at_sea: AtSea) -> bool:
    positioned = latest if latest.has_fix else last_positioned
    return positioned is not None and positioned.has_fix and at_sea(positioned.latitude, positioned.longitude)


def effective_interval_s(tier_at_latest: Tier, current_tier: Tier, latest_path: str) -> int:
    if latest_path == 'relayed':
        return INTERVAL_S[Tier.NORMAL]
    return max(INTERVAL_S[tier_at_latest], INTERVAL_S[current_tier])


def missed_deadline(last_at: datetime, interval_s: int) -> datetime:
    _require_aware(last_at)
    return last_at + timedelta(seconds=MISSED_AFTER_INTERVALS * interval_s * (1 + GRACE_FRACTION))


def evaluate_vessel(item: VesselWatchInput, current_tier: Tier, now: datetime, at_sea: AtSea) -> VesselVerdict:
    _require_aware(now)
    _require_aware(item.latest.observed_at)
    if item.stagnant_until is not None:
        _require_aware(item.stagnant_until)
    interval = effective_interval_s(item.tier_at_latest, current_tier, item.latest.path)
    deadline = missed_deadline(item.latest.observed_at, interval)
    if not is_watched(item.latest, item.last_positioned, at_sea):
        state = 'not_watched'
    elif item.stagnant_until is not None and item.stagnant_until > now and current_tier < Tier.SEVERE:
        state = 'stagnant'
    elif now > deadline:
        state = 'missed'
    else:
        state = 'on_time'
    missed_count = floor((now - item.latest.observed_at).total_seconds() / interval) if state == 'missed' else 0
    return VesselVerdict(item.vessel_id, item.trip_id, state, interval, deadline, missed_count, item.latest.path)


def fleet_silence(
    verdicts: Sequence[VesselVerdict], receiver_last_upload_at: datetime | None, now: datetime
) -> FleetSilence:
    _require_aware(now)
    if receiver_last_upload_at is not None:
        _require_aware(receiver_last_upload_at)
    watched = [item for item in verdicts if item.state != 'not_watched']
    if any(item.path == 'direct' for item in watched) and (
        receiver_last_upload_at is None or now - receiver_last_upload_at > RECEIVER_STALE_AFTER
    ):
        return FleetSilence(True, 'receiver_stale')
    missed = sum(item.state == 'missed' for item in watched)
    if len(watched) and missed >= FLEET_SILENCE_MIN_VESSELS and missed / len(watched) >= FLEET_SILENCE_SHARE:
        return FleetSilence(True, 'share')
    return FleetSilence(False, None)


def case_confidence(
    verdict: VesselVerdict, item: VesselWatchInput, silence: FleetSilence, now: datetime
) -> CaseConfidence:
    _require_aware(now)
    position = item.latest if item.latest.has_fix else item.last_positioned
    if position is None or position.fix_age_s is None or silence.active:
        return 'low'
    _require_aware(position.observed_at)
    fix_taken_at = position.observed_at - timedelta(seconds=position.fix_age_s)
    return 'low' if now - fix_taken_at > RECENT_POSITION else 'high'


def should_sound_alarm(confidence: CaseConfidence, current_tier: Tier) -> bool:
    return confidence == 'high' and current_tier == Tier.SEVERE
