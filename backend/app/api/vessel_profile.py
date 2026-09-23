from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_optional_vessel_device
from app.db import get_pool

# Deliberately NOT behind require_user, for the same reason SOS ingest is not
# (app/api/sos.py): a fisherman at sea has no account and no token to hold.
# The profile is the same self-declared identity as the SOS itself; the read
# side (GET /api/sos/active) stays dispatcher-gated, so an unauthenticated
# write only ever describes this one vessel it claims to be.
router = APIRouter(prefix='/api/vessel-profile', tags=['vessel-profile'])


class VesselProfileIn(BaseModel):
    """The identity a handset declares for its vessel.

    Mirrors `VesselIdentity.toRegistrationPayload()`
    (`mobile/lib/data/identity_store.dart`) and the caps the handset already
    enforces (`mobile/lib/core/config.dart`: maxVesselIdLength=32,
    maxBoatLength=32, maxNameLength=64, maxPhoneLength=20,
    maxLicenseLength=24). Pydantic rejects anything beyond those with 422
    before any DB write, so a row cannot be poisoned with an oversized name.
    """

    vessel_id: str = Field(min_length=1, max_length=32)
    boat: str = Field(default='', max_length=32)
    skipper_name: str = Field(default='', max_length=64)
    license_type: str = Field(default='none', max_length=24)
    license_number: str = Field(default='', max_length=24)
    phone: str = Field(default='', max_length=20)


@router.post('', status_code=200)
async def register_vessel_profile(
    payload: VesselProfileIn,
    vessel_device: dict[str, Any] | None = Depends(get_optional_vessel_device),
) -> dict[str, object]:
    """Declare/refresh this vessel's owner identity. Idempotent upsert.

    An unauthenticated request may create a new profile or fill in blank/skeleton
    fields. Modifying an existing non-blank identity field requires a valid
    vessel device bearer token bound to this vessel_id; otherwise 409 Conflict.
    """
    is_authorized = (
        vessel_device is not None
        and vessel_device.get('vessel_id') == payload.vessel_id
    )

    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT id, boat_name, skipper_name, license_type, license_number, phone
              FROM vessels
             WHERE id = $1
            """,
            payload.vessel_id,
        )

        if existing is not None and not is_authorized:
            ex_skipper = existing['skipper_name'] or ''
            ex_lic_num = existing['license_number'] or ''
            ex_phone = existing['phone'] or ''
            ex_lic_type = existing['license_type'] or ''
            if ex_lic_type == 'none':
                ex_lic_type = ''
            ex_boat = existing['boat_name'] or ''
            if ex_boat == existing['id']:
                ex_boat = ''

            if (
                (ex_skipper and payload.skipper_name and payload.skipper_name != ex_skipper)
                or (ex_lic_num and payload.license_number and payload.license_number != ex_lic_num)
                or (ex_phone and payload.phone and payload.phone != ex_phone)
                or (
                    ex_lic_type
                    and payload.license_type
                    and payload.license_type != 'none'
                    and payload.license_type != ex_lic_type
                )
                or (ex_boat and payload.boat and payload.boat != ex_boat)
            ):
                raise HTTPException(
                    status_code=409,
                    detail='modifying existing vessel identity requires vessel device authentication',
                )

        row = await conn.fetchrow(
            """
            INSERT INTO vessels (id, boat_name, skipper_name, license_type,
                                 license_number, phone, profile_updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (id) DO UPDATE SET
              boat_name = CASE
                WHEN EXCLUDED.boat_name = '' THEN vessels.boat_name
                WHEN vessels.boat_name IS NULL OR vessels.boat_name = ''
                  OR vessels.boat_name = vessels.id THEN EXCLUDED.boat_name
                WHEN $7 THEN EXCLUDED.boat_name
                ELSE vessels.boat_name
              END,
              skipper_name = CASE
                WHEN vessels.skipper_name IS NULL OR vessels.skipper_name = '' THEN EXCLUDED.skipper_name
                WHEN $7 THEN EXCLUDED.skipper_name
                ELSE vessels.skipper_name
              END,
              license_type = CASE
                WHEN vessels.license_type IS NULL OR vessels.license_type = ''
                  OR vessels.license_type = 'none' THEN EXCLUDED.license_type
                WHEN $7 THEN EXCLUDED.license_type
                ELSE vessels.license_type
              END,
              license_number = CASE
                WHEN vessels.license_number IS NULL OR vessels.license_number = '' THEN EXCLUDED.license_number
                WHEN $7 THEN EXCLUDED.license_number
                ELSE vessels.license_number
              END,
              phone = CASE
                WHEN vessels.phone IS NULL OR vessels.phone = '' THEN EXCLUDED.phone
                WHEN $7 THEN EXCLUDED.phone
                ELSE vessels.phone
              END,
              profile_updated_at = NOW()
            RETURNING id, boat_name, skipper_name, license_type,
                      license_number, phone, profile_updated_at
            """,
            payload.vessel_id,
            payload.boat,
            payload.skipper_name,
            payload.license_type,
            payload.license_number,
            payload.phone,
            is_authorized,
        )
    data = dict(row)
    return {
        'vessel_id': data['id'],
        'boat': data['boat_name'],
        'skipper_name': data['skipper_name'],
        'license_type': data['license_type'],
        'license_number': data['license_number'],
        'phone': data['phone'],
        'profile_updated_at': (
            data['profile_updated_at'].isoformat() if data.get('profile_updated_at') else None
        ),
    }
