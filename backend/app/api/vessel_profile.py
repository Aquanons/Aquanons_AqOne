from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.audit import record_audit_event
from app.auth import get_optional_vessel_device, require_responder_roles, touch_vessel
from app.db import get_pool

# Unenrolled vessels may create a self-declared profile. Once a vessel has an
# active device, profile writes are bound to that device.
router = APIRouter(prefix='/api/vessel-profile', tags=['vessel-profile'])
confirm_router = APIRouter(prefix='/api/vessels', tags=['vessel-profile'])


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
    shore_contact_name: str | None = Field(default=None, max_length=64)
    shore_contact_phone: str | None = Field(default=None, max_length=20)

    @field_validator('license_type')
    @classmethod
    def _normalise_license_type(cls, value: str) -> str:
        # Same shape as SosIn's trust-tier normalisation: the handset sends
        # one of boatr/fishr/cfvgl/none, and anything else is a forged or
        # hand-typed value that must never light the green badge - it reads
        # as unverified rather than rejecting the whole profile, because a
        # 422 here would also drop the skipper name and phone number.
        return value if value in {'boatr', 'fishr', 'cfvgl', 'none'} else 'none'


@router.post('', status_code=200)
async def register_vessel_profile(
    payload: VesselProfileIn,
    vessel_device: dict[str, Any] | None = Depends(get_optional_vessel_device),
) -> dict[str, object]:
    """Declare/refresh this vessel's owner identity. Idempotent upsert.

    Unenrolled vessels may create a profile or refresh it anonymously, last
    write wins: the vessel_id is unguessable, so presenting it is ownership
    on the self-declared tier, the same basis SOS ingest already trusts.
    A vessel with an active device requires that device's bearer for every
    write, enforced above.
    """
    is_authorized = (
        vessel_device is not None
        and vessel_device.get('vessel_id') == payload.vessel_id
    )

    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT v.id, v.boat_name, v.skipper_name, v.license_type, v.license_number, v.phone,
                   v.shore_contact_name, v.shore_contact_phone,
                   EXISTS (SELECT 1 FROM vessel_devices d WHERE d.vessel_id = v.id AND d.revoked_at IS NULL)
                     AS has_active_device
              FROM vessels v
             WHERE v.id = $1
            """,
            payload.vessel_id,
        )

        has_active_device = bool(existing.get('has_active_device', False)) if existing is not None else False
        if existing is not None and has_active_device and not is_authorized:
            if vessel_device is None:
                raise HTTPException(status_code=401, detail='vessel device credential required')
            raise HTTPException(status_code=403, detail='device is paired for another vessel')

        can_overwrite = is_authorized or not has_active_device

        row = await conn.fetchrow(
            """
            INSERT INTO vessels (id, boat_name, skipper_name, license_type,
                                 license_number, phone, profile_updated_at,
                                 phone_set_by, license_set_by,
                                 shore_contact_name, shore_contact_phone)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(),
                    CASE WHEN $6 <> '' THEN $8 ELSE NULL END,
                    CASE WHEN $4 <> 'none' OR $5 <> '' THEN $8 ELSE NULL END,
                    $9, $10)
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
              phone_set_by = CASE WHEN $7 AND EXCLUDED.phone <> '' THEN $8
                                  ELSE COALESCE(vessels.phone_set_by, EXCLUDED.phone_set_by) END,
              license_set_by = CASE
                WHEN $7 AND (EXCLUDED.license_type <> 'none' OR EXCLUDED.license_number <> '') THEN $8
                ELSE COALESCE(vessels.license_set_by, EXCLUDED.license_set_by)
              END,
              shore_contact_name = CASE
                WHEN EXCLUDED.shore_contact_name IS NULL THEN vessels.shore_contact_name
                WHEN vessels.shore_contact_name IS NULL OR vessels.shore_contact_name = '' OR $7
                  THEN EXCLUDED.shore_contact_name
                ELSE vessels.shore_contact_name
              END,
              shore_contact_phone = CASE
                WHEN EXCLUDED.shore_contact_phone IS NULL THEN vessels.shore_contact_phone
                WHEN vessels.shore_contact_phone IS NULL OR vessels.shore_contact_phone = '' OR $7
                  THEN EXCLUDED.shore_contact_phone
                ELSE vessels.shore_contact_phone
              END,
              profile_updated_at = NOW()
            RETURNING id, boat_name, skipper_name, license_type,
                      license_number, phone, profile_updated_at,
                      phone_set_by, license_set_by, shore_contact_name, shore_contact_phone
            """,
            payload.vessel_id,
            payload.boat,
            payload.skipper_name,
            payload.license_type,
            payload.license_number,
            payload.phone,
            can_overwrite,
            'device' if is_authorized else 'anonymous',
            payload.shore_contact_name,
            payload.shore_contact_phone,
        )
        await touch_vessel(conn, row['id'])
    data = dict(row)
    return {
        'vessel_id': data['id'],
        'boat': data['boat_name'],
        'skipper_name': data['skipper_name'],
        'license_type': data['license_type'],
        'license_number': data['license_number'],
        'phone': data['phone'],
        'shore_contact_name': data.get('shore_contact_name'),
        'shore_contact_phone': data.get('shore_contact_phone'),
        'profile_updated_at': (
            data['profile_updated_at'].isoformat() if data.get('profile_updated_at') else None
        ),
    }


@confirm_router.post('/{vessel_id}/confirm')
async def confirm_vessel(vessel_id: str, user: dict = require_responder_roles) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT confirmed_at FROM vessels WHERE id = $1 FOR UPDATE', vessel_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such vessel')
        row = await conn.fetchrow(
            '''
            UPDATE vessels
               SET confirmed_at = COALESCE(confirmed_at, NOW()),
                   confirmed_by = COALESCE(confirmed_by, $2)
             WHERE id = $1
            RETURNING id, confirmed_at, confirmed_by
            ''',
            vessel_id,
            user.get('email') or 'unknown',
        )
        await record_audit_event(
            conn,
            actor=user,
            action='vessel.confirm',
            resource_type='vessel',
            resource_id=row['id'],
            outcome='no_change' if prior['confirmed_at'] is not None else 'updated',
            is_demo=False,
        )
    return {
        'vessel_id': row['id'],
        'confirmed_at': row['confirmed_at'].isoformat(),
        'confirmed_by': row['confirmed_by'],
    }
