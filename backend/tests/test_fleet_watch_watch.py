"""Plan 69 Phase 2, watch policy (docs/fleet-watch/PHASE_2_PLAN.md T2-20 to T2-34)."""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.fleet_watch.tier import Tier
from app.fleet_watch.watch import (
    FLEET_SILENCE_MIN_VESSELS,
    FLEET_SILENCE_SHARE,
    GRACE_FRACTION,
    MISSED_AFTER_INTERVALS,
    RECEIVER_STALE_AFTER,
    Checkin,
    VesselVerdict,
    VesselWatchInput,
    case_confidence,
    effective_interval_s,
    evaluate_vessel,
    fleet_silence,
    is_watched,
    missed_deadline,
    should_sound_alarm,
)

T0 = datetime(2026, 9, 26, 2, 0, tzinfo=UTC)
SEA = (11.65, 122.50)
HARBOR = (11.55, 122.40)
FLEET_WATCH_DIR = Path(__file__).resolve().parents[1] / 'app' / 'fleet_watch'


def at_sea(lat, lon):
    return lat > 11.60


def checkin(minutes_ago=0.0, where=SEA, path='direct', fix_age_s=10, now=T0):
    lat, lon = where if where is not None else (None, None)
    return Checkin(
        observed_at=now - timedelta(minutes=minutes_ago),
        latitude=lat,
        longitude=lon,
        path=path,
        fix_age_s=fix_age_s if where is not None else None,
    )


def watch_input(latest, last_positioned=None, tier_at_latest=Tier.SEVERE, stagnant_until=None, vessel_id='NW-001'):
    if last_positioned is None and latest.has_fix:
        last_positioned = latest
    return VesselWatchInput(
        vessel_id=vessel_id,
        trip_id='auto-NW-001-1790000000',
        latest=latest,
        last_positioned=last_positioned,
        tier_at_latest=tier_at_latest,
        stagnant_until=stagnant_until,
    )


def verdict(state, vessel_id='V', path='direct'):
    return VesselVerdict(
        vessel_id=vessel_id, trip_id=None, state=state, interval_s=120, deadline=None, missed_count=0, path=path,
    )


def test_constants_match_the_spec():
    assert MISSED_AFTER_INTERVALS == 3
    assert GRACE_FRACTION == 0.2
    assert FLEET_SILENCE_SHARE == 0.30
    assert FLEET_SILENCE_MIN_VESSELS == 3
    assert timedelta(minutes=3) == RECEIVER_STALE_AFTER


def test_t2_20_watched_follows_the_latest_fix():
    assert is_watched(checkin(where=SEA), None, at_sea) is True
    assert is_watched(checkin(where=HARBOR), None, at_sea) is False


def test_t2_21_without_a_fix_the_previous_fix_decides():
    no_fix = checkin(where=None)
    assert no_fix.has_fix is False
    assert is_watched(no_fix, checkin(minutes_ago=5, where=SEA), at_sea) is True
    assert is_watched(no_fix, checkin(minutes_ago=5, where=HARBOR), at_sea) is False
    assert is_watched(no_fix, None, at_sea) is False


def test_t2_22_severe_deadline_is_7_point_2_minutes():
    assert missed_deadline(T0, 120) == T0 + timedelta(minutes=7, seconds=12)
    missed = evaluate_vessel(watch_input(checkin(minutes_ago=7.3)), Tier.SEVERE, T0, at_sea)
    on_time = evaluate_vessel(watch_input(checkin(minutes_ago=7.1)), Tier.SEVERE, T0, at_sea)
    assert missed.state == 'missed'
    assert missed.interval_s == 120
    assert missed.path == 'direct'
    assert on_time.state == 'on_time'
    assert on_time.deadline == T0 - timedelta(minutes=7.1) + timedelta(minutes=7.2)


def test_t2_23_a_tier_that_just_rose_keeps_the_longer_interval():
    assert effective_interval_s(Tier.NORMAL, Tier.SEVERE, 'direct') == 840
    early = evaluate_vessel(watch_input(checkin(minutes_ago=50), tier_at_latest=Tier.NORMAL), Tier.SEVERE, T0, at_sea)
    late = evaluate_vessel(watch_input(checkin(minutes_ago=50.5), tier_at_latest=Tier.NORMAL), Tier.SEVERE, T0, at_sea)
    assert early.state == 'on_time'
    assert late.state == 'missed'


def test_t2_24_a_relayed_vessel_is_expected_at_the_normal_interval():
    assert effective_interval_s(Tier.SEVERE, Tier.SEVERE, 'relayed') == 840
    result = evaluate_vessel(watch_input(checkin(minutes_ago=8, path='relayed')), Tier.SEVERE, T0, at_sea)
    assert result.state == 'on_time'
    assert result.interval_s == 840


def test_t2_25_missed_count_is_whole_intervals_since_the_last_check_in():
    result = evaluate_vessel(watch_input(checkin(minutes_ago=25)), Tier.SEVERE, T0, at_sea)
    assert result.state == 'missed'
    assert result.missed_count == 12


def test_t2_26_interval_literals_live_only_in_tier_py():
    offenders = []
    for module in sorted(FLEET_WATCH_DIR.glob('*.py')):
        if module.name == 'tier.py':
            continue
        for number, line in enumerate(module.read_text(encoding='utf-8').splitlines(), start=1):
            if re.search(r'(?<![\w.])(840|240|120)(?![\w.])', line):
                offenders.append(f'{module.name}:{number}: {line.strip()}')
    assert (FLEET_WATCH_DIR / 'tier.py').exists()
    assert offenders == []


def test_t2_27_stagnant_mode_holds_off_normal_and_elevated_but_not_severe():
    stagnant = T0 + timedelta(hours=1)
    for tier, expected in ((Tier.NORMAL, 'stagnant'), (Tier.ELEVATED, 'stagnant'), (Tier.SEVERE, 'missed')):
        item = watch_input(checkin(minutes_ago=200), tier_at_latest=tier, stagnant_until=stagnant)
        assert evaluate_vessel(item, tier, T0, at_sea).state == expected, tier


def test_t2_28_an_expired_stagnant_declaration_holds_off_nothing():
    item = watch_input(checkin(minutes_ago=200), tier_at_latest=Tier.NORMAL, stagnant_until=T0 - timedelta(seconds=1))
    assert evaluate_vessel(item, Tier.NORMAL, T0, at_sea).state == 'missed'


def test_harbor_vessel_is_never_missed():
    result = evaluate_vessel(watch_input(checkin(minutes_ago=500, where=HARBOR)), Tier.SEVERE, T0, at_sea)
    assert result.state == 'not_watched'


def test_t2_29_four_of_ten_missed_is_fleet_silence():
    verdicts = [verdict('missed', f'M{i}') for i in range(4)] + [verdict('on_time', f'O{i}') for i in range(6)]
    silence = fleet_silence(verdicts, T0 - timedelta(seconds=30), T0)
    assert silence.active is True
    assert silence.reason == 'share'


def test_t2_30_fewer_than_three_missed_is_never_fleet_silence():
    fresh = T0 - timedelta(seconds=30)
    cases = (
        [verdict('missed')] + [verdict('on_time')] * 9,
        [verdict('missed'), verdict('on_time')],
        [verdict('missed')] * 2 + [verdict('on_time')] * 2,
    )
    for verdicts in cases:
        assert fleet_silence(verdicts, fresh, T0).active is False


def test_t2_31_a_stale_receiver_is_fleet_silence_only_for_direct_vessels():
    direct = [verdict('on_time', path='direct')]
    relayed_only = [verdict('on_time', path='relayed'), verdict('not_watched', path='direct')]
    stale = fleet_silence(direct, T0 - timedelta(minutes=3, seconds=1), T0)
    assert stale.active is True
    assert stale.reason == 'receiver_stale'
    assert fleet_silence(direct, T0 - timedelta(minutes=3), T0).active is False
    assert fleet_silence(direct, None, T0).reason == 'receiver_stale'
    assert fleet_silence(relayed_only, None, T0).active is False


def test_t2_32_low_confidence_under_silence_or_without_a_recent_fix():
    missed = verdict('missed')
    fresh = watch_input(checkin(minutes_ago=10, fix_age_s=10))
    stale_fix = watch_input(checkin(minutes_ago=10, fix_age_s=25 * 60))
    no_fix_now = watch_input(checkin(minutes_ago=10, where=None), last_positioned=checkin(minutes_ago=45))
    quiet = fleet_silence([missed], T0, T0)
    loud = fleet_silence([verdict('missed')] * 3, T0, T0)
    assert case_confidence(missed, fresh, loud, T0) == 'low'
    assert case_confidence(missed, stale_fix, quiet, T0) == 'low'
    assert case_confidence(missed, no_fix_now, quiet, T0) == 'low'
    assert case_confidence(missed, fresh, quiet, T0) == 'high'


def test_t2_45_an_unknown_fix_age_is_never_a_recent_fix():
    # docs/02: FIX_AGE_S 65535 means unknown or older, and docs/04 turns it into null.
    # Treating it as 0 would sound the alarm with a position that may be hours old.
    unknown_age = watch_input(checkin(minutes_ago=1, fix_age_s=None))
    assert unknown_age.latest.fix_age_s is None
    assert case_confidence(verdict('missed'), unknown_age, fleet_silence([], T0, T0), T0) == 'low'


def test_t2_33_the_alarm_sounds_only_for_confident_severe_cases():
    assert should_sound_alarm('high', Tier.SEVERE) is True
    assert should_sound_alarm('high', Tier.ELEVATED) is False
    assert should_sound_alarm('low', Tier.SEVERE) is False


def test_t2_34_not_watched_vessels_do_not_dilute_the_share():
    verdicts = [verdict('missed')] * 3 + [verdict('on_time')] * 2 + [verdict('not_watched')] * 20
    assert fleet_silence(verdicts, T0, T0).active is True
