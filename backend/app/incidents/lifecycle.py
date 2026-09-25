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


def fisher_reply_reopens(resolved_at: datetime | None, reply: int, now: datetime) -> bool:
    if resolved_at is None or reply != 1:
        return False
    return timedelta(0) <= now - resolved_at <= REOPEN_WINDOW
