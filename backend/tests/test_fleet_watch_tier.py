"""Plan 69 Phase 2, tier policy (docs/fleet-watch/PHASE_2_PLAN.md T2-01 to T2-19)."""

from datetime import UTC, datetime, timedelta

import pytest
from app.fleet_watch.tier import (
    INTERVAL_S,
    MAX_RAISE,
    PUBLISHED_TIER_TTL,
    SLOT_CYCLE_S,
    PublishedTier,
    Raise,
    RaiseRejected,
    Tier,
    WeatherSignal,
    advisory_tier,
    fleet_tier,
    next_published,
    signal_tier,
    validate_raise,
)

T0 = datetime(2026, 9, 26, 2, 0, tzinfo=UTC)


def signal(advisory_id=1, priority='Warning', status='Published', area='All', expires_at=None, title=None):
    return WeatherSignal(
        advisory_id=advisory_id,
        title=title or f'{priority} {advisory_id}',
        priority=priority,
        status=status,
        area=area,
        expires_at=expires_at,
    )


def a_raise(tier=Tier.SEVERE, expires_at=None):
    return Raise(
        tier=tier,
        reason='Squall line reported',
        raised_by='dispatcher',
        expires_at=expires_at or T0 + timedelta(hours=2),
    )


def test_t2_01_intervals_are_whole_slot_cycles():
    assert INTERVAL_S == {Tier.NORMAL: 840, Tier.ELEVATED: 240, Tier.SEVERE: 120}
    assert SLOT_CYCLE_S == 120
    assert all(value % SLOT_CYCLE_S == 0 for value in INTERVAL_S.values())
    assert [tier.wire for tier in Tier] == ['normal', 'elevated', 'severe']


def test_t2_02_no_signal_and_no_raise_is_normal():
    decision = fleet_tier([], None, T0)
    assert decision.tier == Tier.NORMAL
    assert decision.interval_s == 840
    assert decision.source.kind == 'none'
    assert decision.source.advisory_id is None


def test_t2_03_published_warning_for_all_is_elevated_and_named():
    decision = fleet_tier([signal(advisory_id=101, title='Gale Warning')], None, T0)
    assert decision.tier == Tier.ELEVATED
    assert decision.interval_s == 240
    assert decision.source.kind == 'advisory'
    assert decision.source.advisory_id == 101
    assert decision.source.title == 'Gale Warning'


def test_t2_04_emergency_beats_warning():
    decision = fleet_tier([signal(1, 'Warning'), signal(2, 'Emergency')], None, T0)
    assert decision.tier == Tier.SEVERE
    assert decision.source.advisory_id == 2


def test_t2_05_expired_emergency_counts_for_nothing():
    expired = signal(priority='Emergency', expires_at=T0 - timedelta(seconds=1))
    assert signal_tier(expired, T0) == Tier.NORMAL
    assert fleet_tier([expired], None, T0).tier == Tier.NORMAL
    assert signal_tier(signal(priority='Emergency', expires_at=T0), T0) == Tier.SEVERE


def test_t2_06_draft_emergency_counts_for_nothing():
    assert signal_tier(signal(priority='Emergency', status='Draft'), T0) == Tier.NORMAL


def test_t2_07_area_must_be_new_washington_or_all_ignoring_case():
    assert signal_tier(signal(priority='Emergency', area='Kalibo'), T0) == Tier.NORMAL
    assert signal_tier(signal(priority='Emergency', area='NEW WASHINGTON'), T0) == Tier.SEVERE
    assert signal_tier(signal(priority='Emergency', area='all'), T0) == Tier.SEVERE


def test_t2_08_information_and_community_are_normal():
    assert signal_tier(signal(priority='Information'), T0) == Tier.NORMAL
    assert signal_tier(signal(priority='Community'), T0) == Tier.NORMAL
    assert advisory_tier([signal(priority='Information')], T0) == (Tier.NORMAL, None)


def test_t2_09_unexpired_raise_above_advisories_wins_and_is_named():
    decision = fleet_tier([signal(priority='Warning')], a_raise(Tier.SEVERE), T0)
    assert decision.tier == Tier.SEVERE
    assert decision.interval_s == 120
    assert decision.source.kind == 'raise'
    assert decision.source.raise_ is not None
    assert decision.source.raise_.reason == 'Squall line reported'


def test_t2_10_raise_stops_counting_once_expired():
    active = a_raise(Tier.SEVERE, expires_at=T0 + timedelta(hours=2))
    decision = fleet_tier([signal(advisory_id=7, priority='Warning')], active, T0 + timedelta(hours=2, seconds=1))
    assert decision.tier == Tier.ELEVATED
    assert decision.source.kind == 'advisory'
    assert decision.source.advisory_id == 7


def test_t2_11_advisory_is_named_when_it_meets_the_raise():
    decision = fleet_tier([signal(advisory_id=9, priority='Emergency')], a_raise(Tier.SEVERE), T0)
    assert decision.tier == Tier.SEVERE
    assert decision.source.kind == 'advisory'
    assert decision.source.advisory_id == 9


def check(tier, reason, advisory=Tier.NORMAL, duration=timedelta(hours=1), raised_by='d'):
    return validate_raise(tier, reason, duration, advisory, T0, raised_by)


def test_t2_12_valid_raise_expires_after_its_duration():
    result = check(Tier.SEVERE, '  Squall line reported  ', Tier.ELEVATED, timedelta(hours=2), 'dispatcher')
    assert isinstance(result, Raise)
    assert result.tier == Tier.SEVERE
    assert result.reason == 'Squall line reported'
    assert result.raised_by == 'dispatcher'
    assert result.expires_at == T0 + timedelta(hours=2)
    assert check(Tier.SEVERE, 'ok', duration=MAX_RAISE).expires_at == T0 + timedelta(hours=12)


def test_t2_13_raise_longer_than_12_hours_is_refused():
    assert check(Tier.SEVERE, 'ok', duration=timedelta(hours=12, minutes=1)) == RaiseRejected('raise_too_long')


def test_t2_14_raise_must_be_strictly_above_the_advisory_tier():
    assert check(Tier.ELEVATED, 'ok', Tier.ELEVATED) == RaiseRejected('cannot_lower')
    assert check(Tier.NORMAL, 'ok', Tier.ELEVATED) == RaiseRejected('cannot_lower')


def test_t2_15_raise_needs_a_reason_of_1_to_200_characters():
    assert check(Tier.SEVERE, '   ') == RaiseRejected('reason_invalid')
    assert check(Tier.SEVERE, 'x' * 201) == RaiseRejected('reason_invalid')
    assert isinstance(check(Tier.SEVERE, 'x' * 200), Raise)


def test_t2_16_first_publication_is_revision_1_expiring_in_10_minutes():
    published = next_published(None, fleet_tier([signal()], None, T0), T0)
    assert published == PublishedTier(tier=Tier.ELEVATED, interval_s=240, rev=1, exp=T0 + timedelta(minutes=10))
    assert timedelta(minutes=10) == PUBLISHED_TIER_TTL


def test_t2_17_unchanged_tier_keeps_revision_and_moves_expiry():
    first = next_published(None, fleet_tier([signal()], None, T0), T0)
    later = T0 + timedelta(minutes=1)
    second = next_published(first, fleet_tier([signal()], None, later), later)
    assert second.rev == first.rev
    assert second.exp == later + timedelta(minutes=10)


def test_t2_18_changed_tier_bumps_revision():
    first = next_published(None, fleet_tier([signal()], None, T0), T0)
    later = T0 + timedelta(minutes=1)
    second = next_published(first, fleet_tier([signal(priority='Emergency')], None, later), later)
    assert second.tier == Tier.SEVERE
    assert second.rev == first.rev + 1


def test_t2_19_naive_now_is_a_programming_error():
    naive = datetime(2026, 9, 26, 2, 0)
    with pytest.raises(ValueError):
        fleet_tier([], None, naive)
    with pytest.raises(ValueError):
        signal_tier(signal(), naive)
