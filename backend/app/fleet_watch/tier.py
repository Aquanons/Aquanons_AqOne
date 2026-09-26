from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum


class Tier(IntEnum):
    NORMAL = 0
    ELEVATED = 1
    SEVERE = 2

    @property
    def wire(self) -> str:
        return ('normal', 'elevated', 'severe')[self]


SLOT_CYCLE_S = 120
INTERVAL_S: Mapping[Tier, int] = {
    Tier.NORMAL: 840,
    Tier.ELEVATED: 240,
    Tier.SEVERE: 120,
}
PUBLISHED_TIER_TTL = timedelta(minutes=10)
MAX_RAISE = timedelta(hours=12)
AREAS = frozenset({'new washington', 'all'})


@dataclass(frozen=True)
class WeatherSignal:
    advisory_id: int
    title: str
    priority: str
    status: str
    area: str
    expires_at: datetime | None


@dataclass(frozen=True)
class Raise:
    tier: Tier
    reason: str
    raised_by: str
    expires_at: datetime


@dataclass(frozen=True)
class TierSource:
    kind: str
    advisory_id: int | None = None
    title: str | None = None
    raise_: Raise | None = None


@dataclass(frozen=True)
class TierDecision:
    tier: Tier
    interval_s: int
    source: TierSource


@dataclass(frozen=True)
class PublishedTier:
    tier: Tier
    interval_s: int
    rev: int
    exp: datetime


@dataclass(frozen=True)
class RaiseRejected:
    code: str


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('datetime must be timezone-aware')


def signal_tier(signal: WeatherSignal, now: datetime) -> Tier:
    _require_aware(now)
    if signal.expires_at is not None:
        _require_aware(signal.expires_at)
    if (
        signal.status.casefold() != 'published'
        or signal.area.casefold() not in AREAS
        or signal.expires_at is not None and now > signal.expires_at
    ):
        return Tier.NORMAL
    return {'emergency': Tier.SEVERE, 'warning': Tier.ELEVATED}.get(signal.priority.casefold(), Tier.NORMAL)


def advisory_tier(
    signals: list[WeatherSignal] | tuple[WeatherSignal, ...], now: datetime
) -> tuple[Tier, WeatherSignal | None]:
    _require_aware(now)
    candidates = [(signal_tier(signal, now), signal) for signal in signals]
    active = [(tier, signal) for tier, signal in candidates if tier > Tier.NORMAL]
    if not active:
        return Tier.NORMAL, None
    return max(active, key=lambda pair: (pair[0], pair[1].expires_at is None, pair[1].expires_at or now))


def fleet_tier(
    signals: list[WeatherSignal] | tuple[WeatherSignal, ...], active_raise: Raise | None, now: datetime
) -> TierDecision:
    _require_aware(now)
    advisory, signal = advisory_tier(signals, now)
    if active_raise is not None:
        _require_aware(active_raise.expires_at)
    raise_is_active = active_raise is not None and now < active_raise.expires_at
    if raise_is_active and active_raise.tier > advisory:
        tier = active_raise.tier
        source = TierSource('raise', raise_=active_raise)
    elif signal is not None:
        tier = advisory
        source = TierSource('advisory', advisory_id=signal.advisory_id, title=signal.title)
    else:
        tier = advisory
        source = TierSource('none')
    return TierDecision(tier, INTERVAL_S[tier], source)


def validate_raise(
    tier: Tier,
    reason: str,
    duration: timedelta,
    advisory_tier: Tier,
    now: datetime,
    raised_by: str,
) -> Raise | RaiseRejected:
    _require_aware(now)
    normalized_reason = reason.strip()
    if not normalized_reason or len(normalized_reason) > 200:
        return RaiseRejected('reason_invalid')
    if duration <= timedelta(0) or duration > MAX_RAISE:
        return RaiseRejected('raise_too_long')
    if tier <= advisory_tier:
        return RaiseRejected('cannot_lower')
    return Raise(tier, normalized_reason, raised_by, now + duration)


def next_published(previous: PublishedTier | None, decision: TierDecision, now: datetime) -> PublishedTier:
    _require_aware(now)
    if previous is not None:
        _require_aware(previous.exp)
    rev = 1 if previous is None else previous.rev + (previous.tier != decision.tier)
    return PublishedTier(decision.tier, decision.interval_s, rev, now + PUBLISHED_TIER_TTL)
