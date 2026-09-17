from __future__ import annotations

from base64 import b64decode
from binascii import Error as Base64Error

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import get_pool

# Deliberately NOT behind require_user, for the same reason SOS ingest is not
# (app/api/sos.py): a fisherman at sea has no account and no token to hold.
# The profile is the same self-declared identity as the SOS itself; the read
# side (GET /api/sos/active) stays dispatcher-gated, so an unauthenticated
# write only ever describes this one vessel it claims to be.
router = APIRouter(prefix='/api/vessel-profile', tags=['vessel-profile'])

# Ceiling on the avatar data URL. The handset crops to 512x512 PNG (roughly
# 0.5-1 MB before base64), so this admits every real upload while stopping a
# client from pushing a payload that would bloat every dispatcher poll. The
# dashboard receives the image inline in GET /api/sos/active.
_MAX_AVATAR_CHARS = 2_000_000


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

    # Cropped profile picture as base64, optionally a `data:image/png;base64,`
    # URL. Three states: absent/None keeps whatever the backend holds, an empty
    # string clears it (the handset removed the photo), and anything else
    # replaces it. A partial profile push must never erase a stored photo.
    avatar: str | None = Field(default=None, max_length=_MAX_AVATAR_CHARS)


def _decode_avatar(value: str | None) -> tuple[bool, bytes | None]:
    """Return (should_update, png_bytes) for the avatar field.

    `should_update` is False only when the field was omitted, which keeps the
    stored image; an explicit empty string clears it.
    """
    if value is None:
        return False, None
    if value == '':
        return True, None
    encoded = value.split(',', 1)[1] if value.startswith('data:') else value
    try:
        return True, b64decode(encoded, validate=True)
    except (Base64Error, ValueError) as error:
        raise HTTPException(status_code=422, detail='avatar is not valid base64 image data') from error


@router.post('', status_code=200)
async def register_vessel_profile(payload: VesselProfileIn) -> dict[str, object]:
    """Declare/refresh this vessel's owner identity. Idempotent upsert.

    The handset pushes this once at onboarding and again whenever the profile
    changes (`main.dart` fires it best-effort, never blocking an SOS). It must
    not fail because the vessel row exists only as the skeleton an SOS created,
    hence the upsert: the empty-boat branch keeps the name an SOS already set.
    """
    set_avatar, avatar_png = _decode_avatar(payload.avatar)
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            INSERT INTO vessels (id, boat_name, skipper_name, license_type,
                                 license_number, phone, avatar_png,
                                 profile_updated_at, avatar_updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $8::BYTEA, NOW(),
                    CASE WHEN $7::BOOLEAN THEN NOW() ELSE NULL END)
            ON CONFLICT (id) DO UPDATE SET
              boat_name          = CASE WHEN $2 = '' THEN vessels.boat_name ELSE $2 END,
              skipper_name       = $3,
              license_type       = $4,
              license_number     = $5,
              phone              = $6,
              avatar_png         = CASE WHEN $7::BOOLEAN THEN $8::BYTEA ELSE vessels.avatar_png END,
              avatar_updated_at  = CASE WHEN $7::BOOLEAN THEN NOW() ELSE vessels.avatar_updated_at END,
              profile_updated_at = NOW()
            RETURNING id, boat_name, skipper_name, license_type,
                      license_number, phone, avatar_png, profile_updated_at,
                      avatar_updated_at
            ''',
            payload.vessel_id,
            payload.boat,
            payload.skipper_name,
            payload.license_type,
            payload.license_number,
            payload.phone,
            set_avatar,
            avatar_png,
        )
    data = dict(row)
    return {
        'vessel_id': data['id'],
        'boat': data['boat_name'],
        'skipper_name': data['skipper_name'],
        'license_type': data['license_type'],
        'license_number': data['license_number'],
        'phone': data['phone'],
        'has_avatar': data.get('avatar_png') is not None,
        'profile_updated_at': (
            data['profile_updated_at'].isoformat() if data.get('profile_updated_at') else None
        ),
    }
