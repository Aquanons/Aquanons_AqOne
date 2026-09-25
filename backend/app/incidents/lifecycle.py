from datetime import datetime, timedelta
from enum import StrEnum


class ResolutionCode(StrEnum):
    RESCUED = 'rescued'
    SAFE_CONFIRMED = 'safe_confirmed'
    STOOD_DOWN_BY_FISHER = 'stood_down_by_fisher'
    DUPLICATE = 'duplicate'
    CLOSED_UNCONFIRMED = 'closed_unconfirmed'
    UNSPECIFIED = 'unspecified'


REOPEN_WINDOW = timedelta(hours=2)


def resolution_code_from(raw: str | ResolutionCode | None) -> ResolutionCode:
    return ResolutionCode(raw) if raw is not None else ResolutionCode.UNSPECIFIED


def can_reopen(resolved_at: datetime | None) -> bool:
    return resolved_at is not None


def fisher_reply_reopens(resolved_at: datetime | None, reply: int, now: datetime) -> bool:
    if not can_reopen(resolved_at) or reply != 1:
        return False
    return timedelta(0) <= now - resolved_at <= REOPEN_WINDOW
