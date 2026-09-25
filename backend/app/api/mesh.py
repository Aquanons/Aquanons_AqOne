from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app import auth as auth_api
from app.api.contacts import is_valid_gateway_key
from app.auth import VALID_ROLES, bearer_scheme, decode_token, get_vessel_device_from_token
from app.db import get_pool
from app.mesh.chat_policy import RateLimiter, chat_origin, sender_is_reserved

router = APIRouter(prefix='/api/mesh', tags=['mesh'])

# Cap on a single page of history. The Heltec hub polls this endpoint on a
# short interval and has a few hundred KB of heap, so an unbounded LIMIT would
# be a memory fault on the device rather than a slow response here.
MAX_LIMIT = 200
_rate_limiter = RateLimiter()


class MeshChatIn(BaseModel):
    """A chat message relayed from the Heltec WiFi hub.

    Anonymous fishermen may post, with their origin fixed to the app path.
    """

    sender: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=256)

    # Which leg of the relay the message arrived on. The hub uses this to
    # avoid rebroadcasting its own uplink back to the boats that just sent it:
    # anything tagged "hub" came off the mesh and is already on their screens.
    origin: str = Field(default='app', max_length=16)


def _row_to_message(row) -> dict:
    return {
        'id': row['id'],
        'sender': row['sender'],
        'text': row['text'],
        'origin': row['origin'],
        'created_at': row['created_at'].isoformat(),
    }


async def _mesh_credential(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Header(default=None, alias='X-Api-Key'),
) -> tuple[str, dict[str, Any]] | None:
    if credentials is not None and credentials.credentials:
        token = credentials.credentials
        claims = decode_token(token)
        kind = claims.get('kind', 'user')
        if kind == 'vessel_device':
            device = await get_vessel_device_from_token(token)
            if device is None:
                raise HTTPException(status_code=401, detail='device credential revoked')
            return 'vessel', device
        if kind == 'user':
            user_id = claims.get('sub')
            if not user_id:
                raise HTTPException(status_code=401, detail='invalid token')
            user = await auth_api.verify_user_session(user_id, claims)
            if user.get('role') not in VALID_ROLES:
                raise HTTPException(status_code=403, detail='operator credential required')
            return 'operator', user
        raise HTTPException(status_code=401, detail='invalid token')
    if is_valid_gateway_key(api_key):
        return 'gateway', {}
    return None


@router.post('/chat', status_code=201)
async def ingest_chat(
    payload: MeshChatIn,
    request: Request,
    credential: tuple[str, dict[str, Any]] | None = Depends(_mesh_credential),
) -> dict:
    """Accept a chat message from the app, gateway, or an operator."""
    credential_kind, credential = credential or (None, {})
    origin = chat_origin(credential_kind)
    sender = payload.sender
    if credential_kind == 'operator':
        sender = credential.get('full_name') or credential.get('email', 'MDRRMO').split('@')[0]
    elif credential_kind == 'vessel':
        pool = get_pool()
        async with pool.acquire() as conn:
            sender = await conn.fetchval('SELECT boat_name FROM vessels WHERE id = $1', credential['vessel_id'])
        sender = sender or payload.sender
    if origin != 'mdrrmo' and sender_is_reserved(sender):
        raise HTTPException(status_code=422, detail='sender_reserved')
    client_ip = request.client.host if request.client else 'unknown'
    if not _rate_limiter.allow(sender, client_ip):
        raise HTTPException(status_code=429, detail='chat_rate_limit')
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            INSERT INTO mesh_chat (sender, text, origin)
            VALUES ($1, $2, $3)
            RETURNING id, sender, text, origin, created_at
            ''',
            sender,
            payload.text,
            origin,
        )
        await conn.execute(
            '''
            DELETE FROM mesh_chat
            WHERE created_at < NOW() - INTERVAL '30 days'
            '''
        )
    return _row_to_message(row)


@router.get('/chat')
async def get_chat(
    limit: int = 50,
    since_id: int = Query(default=0, ge=0),
    credential: tuple[str, dict[str, Any]] | None = Depends(_mesh_credential),
) -> dict:
    """Return recent chat messages, oldest first, to a relay or operator.

    Pass ``since_id`` to fetch only what has landed since the last poll. The
    hub relies on this: without it, every poll would look like a fresh batch
    and the boats would see the same messages over and over.
    """
    if credential is None:
        raise HTTPException(status_code=401, detail='chat credential required')
    pool = get_pool()
    capped = max(1, min(limit, MAX_LIMIT))
    async with pool.acquire() as conn:
        if since_id:
            # Ascending here - "the next N after since_id" - so a hub that has
            # been offline catches up in order instead of skipping a gap.
            rows = await conn.fetch(
                '''
                SELECT id, sender, text, origin, created_at
                FROM mesh_chat
                WHERE id > $1
                ORDER BY id ASC
                LIMIT $2
                ''',
                since_id,
                capped,
            )
        else:
            rows = await conn.fetch(
                '''
                SELECT id, sender, text, origin, created_at
                FROM mesh_chat
                ORDER BY id DESC
                LIMIT $1
                ''',
                capped,
            )
            rows = list(reversed(rows))

    return {'messages': [_row_to_message(row) for row in rows]}
