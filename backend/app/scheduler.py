from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.ai.anomaly_service import demo_evaluation_enabled, evaluate_and_persist
from app.audit import record_audit_event
from app.db import get_pool
from app.incidents.escalation import ESCALATE_AFTER, due_for_escalation, escalation_text
from app.notify import NotifyResult, send_sms

logger = logging.getLogger(__name__)
_tasks: list[asyncio.Task] = []
ESCALATION_JOB = 'escalation'
ANOMALY_JOB = 'anomaly'


async def run_job_once(job_id: str, fn: Callable[[], Awaitable[object]]) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        locked = await conn.fetchval('SELECT pg_try_advisory_lock(hashtext($1))', job_id)
        if not locked:
            return False
        try:
            await fn()
            await conn.execute(
                '''INSERT INTO scheduler_runs (job, last_run_at) VALUES ($1, NOW())
                   ON CONFLICT (job) DO UPDATE SET last_run_at = EXCLUDED.last_run_at''',
                job_id,
            )
            return True
        finally:
            await conn.fetchval('SELECT pg_advisory_unlock(hashtext($1))', job_id)


async def run_escalation_job() -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT s.id, s.vessel_id, s.created_at, s.latitude, s.longitude,
                      s.is_synthetic, v.boat_name
                 FROM sos_events s JOIN vessels v ON v.id = s.vessel_id
                WHERE s.acknowledged_at IS NULL AND s.resolved_at IS NULL
                  AND s.escalated_at IS NULL AND s.is_synthetic = FALSE
                  AND s.created_at <= NOW() - $1::INTERVAL
                ORDER BY s.created_at''',
            ESCALATE_AFTER,
        )
    due = due_for_escalation([dict(row) for row in rows], datetime.now(UTC))
    completed = 0
    for event in due:
        async with pool.acquire() as conn, conn.transaction():
            claimed = await conn.fetchrow(
                '''UPDATE sos_events SET escalated_at = NOW()
                    WHERE id = $1 AND acknowledged_at IS NULL AND resolved_at IS NULL
                      AND escalated_at IS NULL AND is_synthetic = FALSE
                    RETURNING id''',
                event['id'],
            )
            if claimed is None:
                continue
        result = await send_sms(escalation_text(event))
        async with pool.acquire() as conn, conn.transaction():
            if result is NotifyResult.FAILED:
                await conn.execute('UPDATE sos_events SET escalated_at = NULL WHERE id = $1', event['id'])
            await record_audit_event(
                conn,
                actor=None,
                action='sos.escalate',
                resource_type='sos_event',
                resource_id=event['id'],
                outcome=str(result),
                metadata={'notification': str(result)},
            )
        completed += 1
    return completed


async def _evaluation_job() -> None:
    pool = get_pool()
    as_of = datetime.now(UTC)
    async with pool.acquire() as conn:
        await evaluate_and_persist(conn, as_of=as_of, include_synthetic=demo_evaluation_enabled())


async def _run_periodically(job_id: str, interval: float, fn: Callable[[], Awaitable[object]]) -> None:
    while True:
        try:
            await run_job_once(job_id, fn)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Scheduled job failed: %s', job_id)
        await asyncio.sleep(interval)


async def start() -> None:
    global _tasks
    _tasks = [
        asyncio.create_task(_run_periodically(ESCALATION_JOB, 30, run_escalation_job)),
        asyncio.create_task(_run_periodically(ANOMALY_JOB, 300, _evaluation_job)),
    ]


async def stop() -> None:
    global _tasks
    tasks, _tasks = _tasks, []
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
