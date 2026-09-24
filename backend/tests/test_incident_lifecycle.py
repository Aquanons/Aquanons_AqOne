from datetime import UTC, datetime, timedelta

from app.incidents.lifecycle import ResolutionCode, can_reopen, fisher_reply_reopens, resolution_code_from


def test_resolution_codes():
    assert {code.value for code in ResolutionCode} == {
        'rescued', 'safe_confirmed', 'stood_down_by_fisher', 'duplicate',
        'closed_unconfirmed', 'unspecified',
    }


def test_missing_reason_is_unspecified():
    assert resolution_code_from(None) is ResolutionCode.UNSPECIFIED


def test_fisher_reply_reopens_only_still_in_danger_within_two_hours():
    resolved = datetime.now(UTC) - timedelta(minutes=30)
    now = datetime.now(UTC)
    assert fisher_reply_reopens(resolved, 1, now)
    assert not fisher_reply_reopens(resolved, 2, now)
    assert not fisher_reply_reopens(resolved, 1, now + timedelta(hours=2))


def test_can_reopen_requires_a_resolved_incident():
    assert can_reopen(datetime.now(UTC))
    assert not can_reopen(None)
