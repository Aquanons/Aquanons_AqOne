from typing import Any


def delivery_state(row: Any) -> str:
    if row['resolved_at'] is not None or row['acknowledged_at'] is not None:
        return 'acknowledged'
    if row['delivered_direct'] or row['delivered_via_buoy']:
        return 'delivered'
    return 'relayed'
