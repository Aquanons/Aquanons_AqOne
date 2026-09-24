from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from app.auth import require_user
from app.db import get_pool

router = APIRouter(prefix='/api/ops', tags=['operations'])
GATEWAY_STALE_AFTER = timedelta(seconds=135)


@router.get('/status')
async def ops_status(_: dict = Depends(require_user)) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        last_poll = await conn.fetchval(
            "SELECT last_poll_at FROM gateway_status WHERE gateway_key = 'default'"
        )
    now = datetime.now(UTC)
    return {
        'gateway_last_poll_at': last_poll.isoformat() if last_poll else None,
        'gateway_stale': last_poll is None or now - last_poll > GATEWAY_STALE_AFTER,
    }
