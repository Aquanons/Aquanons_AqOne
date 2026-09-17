from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db import get_pool

# Deliberately NOT behind require_user, for the same reason SOS ingest is not
# (app/api/sos.py): a fisherman at sea has no account and no token to hold.
# The profile is the same self-declared identity as the SOS itself; the read
# side (GET /api/sos/active) stays dispatcher-gated, so an unauthenticated
# write only ever describes this one vessel it claims to be.
router = APIRouter(prefix='/api/vessel-profile', tags=['vessel-profile'])


class VesselProfileIn(BaseModel):
    """The identity a handset declares for its vessel.

    Mirrors `VesselIdentity.toRegistrationPayload()` field-for-field
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
async def register_vessel_profile(payload: VesselProfileIn) -> dict[str, object]:
    """Declare/refresh this vessel's owner identity. Idempotent upsert.

    The handset pushes this once at onboarding and again whenever the profile
    changes (`main.dart` fires it best-effort, never blocking an SOS). It must
    not fail because the vessel row exists only as the skeleton an SOS created,
    hence the upsert: the empty-boat branch keeps the name an SOS already set.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            INSERT INTO vessels (id, boat_name, skipper_name, license_type,
                                 license_number, phone, profile_updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (id) DO UPDATE SET
              boat_name          = CASE WHEN $2 = '' THEN vessels.boat_name ELSE $2 END,
              skipper_name       = $3,
              license_type       = $4,
              license_number     = $5,
              phone              = $6,
              profile_updated_at = NOW()
            RETURNING id, boat_name, skipper_name, license_type,
                      license_number, phone, profile_updated_at
            ''',
            payload.vessel_id,
            payload.boat,
            payload.skipper_name,
            payload.license_type,
            payload.license_number,
            payload.phone,
        )
    return {
        'vessel_id': row['id'],
        'boat': row['boat_name'],
        'skipper_name': row['skipper_name'],
        'license_type': row['license_type'],
        'license_number': row['license_number'],
        'phone': row['phone'],
        'profile_updated_at': (
            row['profile_updated_at'].isoformat() if row['profile_updated_at'] else None
        ),
    }
