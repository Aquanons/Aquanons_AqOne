from datetime import datetime, timedelta
from typing import Any

FLOOD_WINDOW = timedelta(seconds=60)
FLOOD_THRESHOLD = 10


def _corroborated(event: Any) -> bool:
    return bool(
        event.get('corroborated', False)
        or event.get('delivered_via_buoy', False)
        or event.get('vessel_verified', False)
        or event.get('has_trip_history', False)
    )


def triage_key(event: Any) -> tuple[bool, bool, float]:
    return (
        event['acknowledged_at'] is not None,
        not _corroborated(event),
        -event['created_at'].timestamp(),
    )


def flood_status(events: list[Any], now: datetime) -> dict[str, int | bool]:
    unknown = {
        event['vessel_id']
        for event in events
        if not _corroborated(event)
        and timedelta(0) <= now - event['created_at'] <= FLOOD_WINDOW
    }
    return {
        'unknown_vessels_last_minute': len(unknown),
        'active': len(unknown) > FLOOD_THRESHOLD,
    }
