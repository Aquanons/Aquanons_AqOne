from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.geo import SHORE_STATIONS, distance_km, point_in_water

POD_TO_SHORE_MAX_RANGE_KM = 7.5


@dataclass(frozen=True)
class PlausibilityContext:
    """Plausibility inputs; range uses docs/33_LORA_RF_BUDGET.md, Recommended configuration (SF10)."""

    gateway_latitude: float = SHORE_STATIONS[0]['lat']
    gateway_longitude: float = SHORE_STATIONS[0]['lon']
    max_range_km: float = POD_TO_SHORE_MAX_RANGE_KM
    contact_at: datetime | None = None
    contact_latitude: float | None = None
    contact_longitude: float | None = None
    open_calls_for_vessel: int = 1
    now: datetime = field(default_factory=lambda: datetime.now(UTC))


def flags(event: Any, context: PlausibilityContext) -> list[str]:
    result = []
    latitude = event['latitude']
    longitude = event['longitude']
    has_position = latitude is not None and longitude is not None

    if has_position and not point_in_water(latitude, longitude):
        result.append('position_on_land')
    if (
        has_position
        and event['delivered_via_buoy']
        and not event['delivered_direct']
        and distance_km(latitude, longitude, context.gateway_latitude, context.gateway_longitude)
        > context.max_range_km
    ):
        result.append('position_beyond_radio_range')
    if (
        has_position
        and context.contact_at is not None
        and context.contact_latitude is not None
        and context.contact_longitude is not None
        and timedelta(0) <= context.now - context.contact_at <= timedelta(hours=1)
        and distance_km(latitude, longitude, context.contact_latitude, context.contact_longitude) > 20
    ):
        result.append('position_jump')
    if context.open_calls_for_vessel > 1:
        result.append('many_calls_same_vessel')
    if event['alt_latitude'] is not None or event['alt_longitude'] is not None:
        result.append('position_conflict')
    return result
