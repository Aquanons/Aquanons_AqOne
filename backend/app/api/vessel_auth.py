from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.audit import record_audit_event
from app.auth import (
    bearer_scheme,
    create_vessel_device_token,
    decode_vessel_device_token,
    hash_password,
    require_device_admin_roles,
    require_vessel_device,
    verify_password,
)
from app.db import get_pool

router = APIRouter(prefix='/api/vessel-auth', tags=['vessel-auth'])

_PAIRING_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
_PAIRING_CODE_LENGTH = 8
_PAIRING_TTL_MINUTES = 15


def _pairing_code() -> str:
    rng = random.SystemRandom()
    return ''.join(rng.choice(_PAIRING_ALPHABET) for _ in range(_PAIRING_CODE_LENGTH))


class PairingCodeIn(BaseModel):
    vessel_id: str = Field(min_length=1, max_length=32)
    boat: str = Field(default='', max_length=32)


class EnrollIn(BaseModel):
    vessel_id: str = Field(min_length=1, max_length=32)
    pairing_code: str = Field(min_length=4, max_length=32)
    device_label: str = Field(default='Fisher handset', max_length=64)


class RevokeIn(BaseModel):
    reason: str = Field(default='lost device', max_length=120)


@router.post('/pairing-codes')
async def issue_pairing_code(
    payload: PairingCodeIn,
    user: dict[str, object] = require_device_admin_roles,
) -> dict[str, object]:
    code = _pairing_code()
    expires_at = datetime.now(UTC) + timedelta(minutes=_PAIRING_TTL_MINUTES)
    vessel_id = payload.vessel_id.strip()
    boat = payload.boat.strip()
    pool = get_pool()

    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            '''
            INSERT INTO vessels (id, boat_name)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET
              boat_name = CASE
                            WHEN NULLIF($2, '') IS NULL THEN vessels.boat_name
                            ELSE EXCLUDED.boat_name
                          END
            ''',
            vessel_id,
            boat or vessel_id,
        )
        await conn.execute(
            '''
            INSERT INTO vessel_device_pairings (
              vessel_id, code_hash, issued_by_user_id, issued_by_email, expires_at
            )
            VALUES ($1, $2, $3, $4, $5)
            ''',
            vessel_id,
            hash_password(code),
            int(str(user.get('id') or '0') or '0'),
            str(user.get('email') or ''),
            expires_at,
        )
        await record_audit_event(
            conn,
            actor=user,
            action='vessel_device.pairing_code_issue',
            resource_type='vessel',
            resource_id=vessel_id,
            outcome='created',
            is_demo=False,
        )

    return {
        'vessel_id': vessel_id,
        'pairing_code': code,
        'expires_at': expires_at.isoformat(),
    }


@router.post('/enroll')
async def enroll_device(payload: EnrollIn) -> dict[str, object]:
    vessel_id = payload.vessel_id.strip()
    pool = get_pool()

    async with pool.acquire() as conn:
        candidates = await conn.fetch(
            '''
            SELECT id, code_hash
            FROM vessel_device_pairings
            WHERE vessel_id = $1
              AND consumed_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 10
            ''',
            vessel_id,
        )

    match = next(
        (
            row
            for row in candidates
            if verify_password(payload.pairing_code.strip(), row['code_hash'])
        ),
        None,
    )
    if match is None:
        raise HTTPException(status_code=401, detail='invalid or expired pairing code')

    async with pool.acquire() as conn, conn.transaction():
        pairing = await conn.fetchrow(
            '''
            UPDATE vessel_device_pairings
               SET consumed_at = NOW()
             WHERE id = $1
               AND consumed_at IS NULL
            RETURNING id
            ''',
            match['id'],
        )
        if pairing is None:
            raise HTTPException(status_code=409, detail='pairing code already used')

        row = await conn.fetchrow(
            '''
            INSERT INTO vessel_devices (
              vessel_id, label, last_seen_at, last_token_issued_at
            )
            VALUES ($1, $2, NOW(), NOW())
            RETURNING id, vessel_id, label, paired_at
            ''',
            vessel_id,
            payload.device_label.strip() or 'Fisher handset',
        )

    token = create_vessel_device_token(row['id'], row['vessel_id'])
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    return {
        'token': token,
        'expires_at': expires_at.isoformat(),
        'device': {
            'id': row['id'],
            'vessel_id': row['vessel_id'],
            'label': row['label'],
            'paired_at': row['paired_at'].isoformat(),
        },
    }


@router.post('/refresh')
async def refresh_device_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, object]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail='device credential required')
    claims = decode_vessel_device_token(credentials.credentials, expired_grace=timedelta(days=30))
    if claims.get('kind') != 'vessel_device':
        raise HTTPException(status_code=401, detail='invalid token')
    try:
        device_id = int(claims['device_id'])
        vessel_id = str(claims['vessel_id'])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail='invalid token') from exc
    pool = get_pool()
    async with pool.acquire() as conn:
        device = await conn.fetchrow(
            '''
            UPDATE vessel_devices
               SET last_token_issued_at = NOW()
             WHERE id = $1 AND vessel_id = $2 AND revoked_at IS NULL
             RETURNING id, vessel_id, label
            ''',
            device_id,
            vessel_id,
        )
    if device is None:
        raise HTTPException(status_code=401, detail='device credential revoked')

    token = create_vessel_device_token(
        int(device['id']),
        str(device['vessel_id']),
    )
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    return {
        'token': token,
        'expires_at': expires_at.isoformat(),
        'device': {
            'id': device['id'],
            'vessel_id': device['vessel_id'],
            'label': device['label'],
        },
    }


@router.post('/devices/{device_id}/revoke')
async def revoke_device(
    device_id: int,
    payload: RevokeIn | None = None,
    user: dict[str, object] = require_device_admin_roles,
) -> dict[str, object]:
    body = payload or RevokeIn()
    pool = get_pool()
    async with pool.acquire() as conn, conn.transaction():
        prior = await conn.fetchrow(
            'SELECT revoked_at FROM vessel_devices WHERE id = $1 FOR UPDATE', device_id,
        )
        if prior is None:
            raise HTTPException(status_code=404, detail='no such vessel device')
        was_already_revoked = prior['revoked_at'] is not None

        row = await conn.fetchrow(
            '''
            UPDATE vessel_devices
               SET revoked_at = COALESCE(revoked_at, NOW()),
                   revoked_by_user_id = $2,
                   revoked_reason = COALESCE(NULLIF($3, ''), revoked_reason)
             WHERE id = $1
            RETURNING id, vessel_id, revoked_at, revoked_reason
            ''',
            device_id,
            int(str(user.get('id') or '0') or '0'),
            body.reason.strip(),
        )
        # reason is short free text and never logged (docs/41 Phase 2).
        await record_audit_event(
            conn,
            actor=user,
            action='vessel_device.revoke',
            resource_type='vessel_device',
            resource_id=row['id'],
            outcome='no_change' if was_already_revoked else 'updated',
            is_demo=False,
        )
    return {
        'device': {
            'id': row['id'],
            'vessel_id': row['vessel_id'],
            'revoked_at': row['revoked_at'].isoformat(),
            'revoked_reason': row['revoked_reason'],
        }
    }


@router.get('/me')
async def current_device(
    device: dict[str, object] = Depends(require_vessel_device),
) -> dict[str, object]:
    return {'device': device}
