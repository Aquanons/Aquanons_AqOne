from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.db import get_pool

router = APIRouter(prefix='/api/mesh', tags=['mesh'])

# Cap on a single page of history. The Heltec hub polls this endpoint on a
# short interval and has a few hundred KB of heap, so an unbounded LIMIT would
# be a memory fault on the device rather than a slow response here.
MAX_LIMIT = 200


class MeshChatIn(BaseModel):
    """A chat message relayed from the Heltec WiFi hub.

    Unauthenticated - fishermen have no account. The sender name is
    self-declared.
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


@router.post('/chat', status_code=201)
async def ingest_chat(payload: MeshChatIn) -> dict:
    """Accept a chat message and store it. Unauthenticated."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''
            INSERT INTO mesh_chat (sender, text, origin)
            VALUES ($1, $2, $3)
            RETURNING id, sender, text, origin, created_at
            ''',
            payload.sender,
            payload.text,
            payload.origin,
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
) -> dict:
    """Return recent chat messages, oldest first. Unauthenticated.

    Pass ``since_id`` to fetch only what has landed since the last poll. The
    hub relies on this: without it, every poll would look like a fresh batch
    and the boats would see the same messages over and over.
    """
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
