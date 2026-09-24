from __future__ import annotations

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

ALGORITHM = 'HS256'
TOKEN_TTL_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '12'))
VESSEL_DEVICE_TOKEN_TTL_HOURS = int(
    os.environ.get('VESSEL_DEVICE_JWT_EXPIRY_HOURS', '24')
)

VALID_ROLES = {'mdrrmo', 'lgu', 'admin'}

# Action matrix (docs/05_PUBLIC_API.md "Roles"): responder incident work and
# advisory/sea-condition publication are open to every operator role; vessel
# device management is reserved for lgu/admin per docs/00_START_HERE.md.
RESPONDER_ROLES = ('mdrrmo', 'lgu', 'admin')
DEVICE_ADMIN_ROLES = ('lgu', 'admin')
# Global audit search/export (docs/41 Phase 3) is the one place lgu is NOT
# treated as equal to admin - seeing every operator's action history across
# every case is a narrower privilege than the operational actions above.
ADMIN_ROLES = ('admin',)

_bearer = HTTPBearer(auto_error=False)


def _load_secret() -> str:
    secret = os.environ.get('JWT_SECRET')
    if secret:
        return secret
    # An ephemeral secret keeps the service booting (and the Railway healthcheck
    # green) when JWT_SECRET is unset, but every redeploy invalidates all
    # existing tokens. That is a deployment misconfiguration, so say so loudly.
    logger.warning(
        'JWT_SECRET is not set. Using an ephemeral secret - all sessions will '
        'be invalidated on restart. Set JWT_SECRET in the environment.'
    )
    return secrets.token_urlsafe(48)


JWT_SECRET = _load_secret()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except ValueError:
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_token(user_id: int, email: str, role: str, token_version: int = 0) -> str:
    now = datetime.now(UTC)
    payload = {
        'kind': 'user',
        'sub': str(user_id),
        'email': email,
        'role': role,
        'ver': token_version,
        'iat': now,
        'exp': now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def create_vessel_device_token(device_id: int, vessel_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        'kind': 'vessel_device',
        'device_id': str(device_id),
        'vessel_id': vessel_id,
        'iat': now,
        'exp': now + timedelta(hours=VESSEL_DEVICE_TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail='session expired') from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail='invalid token') from exc


def decode_vessel_device_token(token: str, *, expired_grace: timedelta) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], leeway=expired_grace)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail='session expired') from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail='invalid token') from exc


async def verify_user_session(user_id: int | str, claims: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail='invalid token') from exc

    token_ver = claims.get('ver')
    if token_ver is None:
        raise HTTPException(status_code=401, detail='session expired')

    from app.db import get_pool

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT id, email, full_name, role, token_version
              FROM users
             WHERE id = $1
            ''',
            user_id_int,
        )

    if row is None:
        raise HTTPException(status_code=401, detail='user not found')
    if claims.get('role') != row['role']:
        raise HTTPException(status_code=401, detail='role mismatch')
    if token_ver != row['token_version']:
        raise HTTPException(status_code=401, detail='session revoked')

    return {
        'id': str(row['id']),
        'email': row['email'],
        'full_name': row.get('full_name', ''),
        'role': row['role'],
        'token_version': row['token_version'],
    }


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Reject any request without a valid bearer token.

    Applied to every /api router except the auth endpoints themselves. The
    401 is what the dashboard listens for to bounce the operator back to the
    login page.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail='authentication required')
    claims = decode_token(credentials.credentials)
    if claims.get('kind', 'user') != 'user':
        raise HTTPException(status_code=401, detail='invalid token')
    user_id = claims.get('sub')
    if not user_id:
        raise HTTPException(status_code=401, detail='invalid token')
    return await verify_user_session(user_id, claims)


async def require_operator_user(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    role = user.get('role')
    if role not in VALID_ROLES:
        raise HTTPException(status_code=403, detail='operator token required')
    return user


def require_roles(*roles: str):
    """Dependency factory: reject a valid, authenticated user whose role is
    not in `roles`. Built on top of `require_user` so token validation stays
    in one place; the action matrix in docs/05_PUBLIC_API.md is the source of
    truth for which roles belong on which route.
    """

    async def _dep(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        if user.get('role') not in roles:
            raise HTTPException(status_code=403, detail='role not permitted for this action')
        return user

    return _dep


# Module-level singletons, not a `Depends(require_roles(...))` call at each
# route's parameter default - ruff (B008) flags a function call in an
# argument default, and FastAPI dependency instances are safe to share
# across routes since they carry no per-request state of their own.
require_responder_roles = Depends(require_roles(*RESPONDER_ROLES))
require_device_admin_roles = Depends(require_roles(*DEVICE_ADMIN_ROLES))
require_admin_role = Depends(require_roles(*ADMIN_ROLES))


bearer_scheme = _bearer


async def require_vessel_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail='device credential required')

    claims = decode_token(credentials.credentials)
    if claims.get('kind') != 'vessel_device':
        raise HTTPException(status_code=401, detail='invalid token')

    device_id_text = claims.get('device_id')
    vessel_id = claims.get('vessel_id')
    if not isinstance(device_id_text, str) or not isinstance(vessel_id, str):
        raise HTTPException(status_code=401, detail='invalid token')

    try:
        device_id = int(device_id_text)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail='invalid token') from exc

    from app.db import get_pool

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            UPDATE vessel_devices
               SET last_seen_at = NOW()
             WHERE id = $1
            RETURNING id, vessel_id, label, revoked_at
            ''',
            device_id,
        )

    if row is None or row['revoked_at'] is not None:
        raise HTTPException(status_code=401, detail='device credential revoked')
    if row['vessel_id'] != vessel_id:
        raise HTTPException(status_code=401, detail='invalid token')

    return {
        'device_id': row['id'],
        'vessel_id': row['vessel_id'],
        'label': row['label'],
    }


async def get_vessel_device_from_token(token: str) -> dict[str, Any] | None:
    try:
        claims = decode_token(token)
    except HTTPException:
        return None
    if claims.get('kind') != 'vessel_device':
        return None

    device_id_text = claims.get('device_id')
    vessel_id = claims.get('vessel_id')
    if not isinstance(device_id_text, str) or not isinstance(vessel_id, str):
        return None

    try:
        device_id = int(device_id_text)
    except ValueError:
        return None

    from app.db import get_pool

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            UPDATE vessel_devices
               SET last_seen_at = NOW()
             WHERE id = $1
            RETURNING id, vessel_id, label, revoked_at
            ''',
            device_id,
        )

    if row is None or row['revoked_at'] is not None or row['vessel_id'] != vessel_id:
        return None

    return {
        'device_id': row['id'],
        'vessel_id': row['vessel_id'],
        'label': row['label'],
    }


async def get_optional_vessel_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any] | None:
    if credentials is None or not credentials.credentials:
        return None
    return await get_vessel_device_from_token(credentials.credentials)
