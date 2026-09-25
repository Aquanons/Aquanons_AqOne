from datetime import datetime


def vessel_verified(has_active_device: bool, confirmed_at: datetime | None) -> bool:
    return has_active_device or confirmed_at is not None
