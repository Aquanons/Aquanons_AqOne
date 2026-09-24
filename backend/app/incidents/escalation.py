from datetime import timedelta
from typing import Any

ESCALATE_AFTER = timedelta(minutes=2)


def due_for_escalation(events: list[dict[str, Any]], now) -> list[dict[str, Any]]:
    cutoff = now - ESCALATE_AFTER
    return [
        event for event in events
        if event.get('acknowledged_at') is None
        and event.get('resolved_at') is None
        and event.get('escalated_at') is None
        and not event.get('is_synthetic', False)
        and event.get('created_at') is not None
        and event['created_at'] <= cutoff
    ]


def escalation_text(event: dict[str, Any]) -> str:
    vessel = str(event.get('boat_name') or event.get('vessel_id') or 'Unknown vessel')
    lat, lon = event.get('latitude'), event.get('longitude')
    position = f'{lat}, {lon}' if lat is not None and lon is not None else 'position unavailable'
    created = event.get('created_at')
    timestamp = created.strftime('%Y-%m-%d %H:%M UTC') if created else 'time unavailable'
    return f'SOS unanswered: {vessel}; position {position}; reported {timestamp}'[:160]
