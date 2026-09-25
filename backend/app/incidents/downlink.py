from datetime import datetime, timedelta
from typing import Any

DOWNLINK_MAX = 12
OPEN_WINDOW = timedelta(hours=24)
RESOLVED_WINDOW = timedelta(hours=6)


def last_change(row: Any) -> datetime:
    return max(
        value for value in (
            row['created_at'], row['acknowledged_at'], row['resolved_at'],
            row['reopened_at'], row['fisher_replied_at'],
        ) if value is not None
    )


def priority_band(row: Any) -> int:
    if row['resolved_at'] is not None:
        return 2
    return 0 if row['acknowledged_at'] is not None else 1


def select_downlink(candidates: list[Any], now: datetime) -> list[Any]:
    """Fit the return feed to 12 slots, the shared gateway MAX_VESSELS and buoy MAX_TRACKED capacity."""
    eligible = [
        row for row in candidates
        if not row.get('is_synthetic', False)
        and (
            now - last_change(row) <= OPEN_WINDOW
            if row['resolved_at'] is None
            else now - row['resolved_at'] <= RESOLVED_WINDOW
        )
    ]
    by_change = sorted(eligible, key=last_change, reverse=True)
    by_priority = sorted(by_change, key=priority_band)
    return by_priority[:DOWNLINK_MAX]
