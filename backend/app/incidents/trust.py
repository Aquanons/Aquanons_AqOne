from dataclasses import dataclass
from datetime import datetime


def vessel_verified(has_active_device: bool, confirmed_at: datetime | None) -> bool:
    return has_active_device or confirmed_at is not None


@dataclass(frozen=True)
class SosProvenance:
    trust_tier: str
    buoy_id: str | None
    src_id: int | None
    seq: int | None
    delivered_direct: bool
    delivered_via_buoy: bool


def sos_provenance(
    *,
    vessel_id: str,
    requested_tier: str,
    source: str,
    buoy_id: str | None,
    src_id: int | None,
    seq: int | None,
    device_vessel_id: str | None,
    gateway_authenticated: bool,
) -> SosProvenance:
    """SEC-06: believe only what the caller's credentials back up.

    `phone_verified` needs a vessel device bound to the same vessel, and the
    buoy route fields need the gateway key; anything else is stored as a
    self-declared direct delivery, so no buoy row is auto-registered. Ingest
    can never claim `confirmed_by_responder`.
    """
    trust_tier = 'phone_verified' if (
        device_vessel_id == vessel_id and requested_tier == 'phone_verified'
    ) else 'self_declared'
    if gateway_authenticated and source == 'buoy':
        return SosProvenance(trust_tier, buoy_id, src_id, seq, False, True)
    return SosProvenance(trust_tier, None, None, None, True, False)
