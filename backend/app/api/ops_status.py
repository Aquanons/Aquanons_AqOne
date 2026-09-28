import os
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends

from app.auth import require_user
from app.db import get_pool
from app.notify import sms_configured

router = APIRouter(prefix='/api/ops', tags=['operations'])
GATEWAY_STALE_AFTER = timedelta(seconds=135)


@router.get('/status')
async def ops_status(_: dict = Depends(require_user)) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        last_poll = await conn.fetchval(
            "SELECT last_poll_at FROM gateway_status WHERE gateway_key = 'default'"
        )
        last_runs = await conn.fetch('SELECT job, last_run_at FROM scheduler_runs')
    now = datetime.now(UTC)
    raw_expiry = os.environ.get('DB_EXPIRES_AT', '').strip()
    try:
        expiry = date.fromisoformat(raw_expiry[:10]) if raw_expiry else None
    except ValueError:
        expiry = None
    return {
        'gateway_last_poll_at': last_poll.isoformat() if last_poll else None,
        'gateway_stale': last_poll is None or now - last_poll > GATEWAY_STALE_AFTER,
        'sms_configured': sms_configured(),
        'db_expires_at': expiry.isoformat() if expiry else None,
        'db_days_left': (expiry - now.date()).days if expiry else None,
        'scheduler_last_run': {row['job']: row['last_run_at'].isoformat() for row in last_runs},
    }


@router.get('/presence')
async def ops_presence(user: dict = Depends(require_user)) -> dict[str, object]:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET last_seen_at = NOW() WHERE id = $1',
            int(user['id']),
        )
        total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
        active_operators = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE last_seen_at > NOW() - INTERVAL '2 minutes'"
        )
        active_handsets = await conn.fetchval(
            "SELECT COUNT(*) FROM vessel_devices"
            " WHERE revoked_at IS NULL AND last_seen_at > NOW() - INTERVAL '15 minutes'"
        )
    return {
        'total_users': total_users,
        'active_operators_2m': active_operators,
        'active_handsets_15m': active_handsets,
        'active_total': active_operators + active_handsets,
    }
