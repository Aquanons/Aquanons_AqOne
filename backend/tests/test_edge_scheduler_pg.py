import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi.testclient import TestClient

from app import scheduler
from app.auth import create_token
from app.main import app
from app.scheduler import ANOMALY_JOB, ESCALATION_JOB, run_escalation_job, run_job_once


def _headers():
    return {'Authorization': f"Bearer {create_token(1, 'probe.mdrrmo@example.invalid', 'mdrrmo')}"}


def test_scheduler_single_runner(probe_db, monkeypatch):
    calls = []

    async def run():
        from app import scheduler

        pool = await asyncpg.create_pool(probe_db)
        monkeypatch.setattr(scheduler, 'get_pool', lambda: pool)
        try:
            async def work():
                await asyncio.sleep(0.05)
                calls.append(1)

            results = await asyncio.gather(
                run_job_once('probe-single-runner', work), run_job_once('probe-single-runner', work)
            )
            assert sum(results) == 1
            assert len(calls) == 1
            async with pool.acquire() as conn:
                assert await conn.fetchval("SELECT count(*) FROM scheduler_runs WHERE job = 'probe-single-runner'") == 1
        finally:
            await pool.close()

    asyncio.run(run())


def test_escalation_marks_and_audits(probe_db, monkeypatch):
    monkeypatch.delenv('SEMAPHORE_API_KEY', raising=False)
    monkeypatch.delenv('ONCALL_SMS_NUMBERS', raising=False)

    async def seed():
        conn = await asyncpg.connect(probe_db)
        try:
            await conn.execute("INSERT INTO vessels (id, boat_name) VALUES ('ESC-1', 'Bangka 1')")
            return await conn.fetchval('''
                INSERT INTO sos_events (vessel_id, client_ts, created_at, latitude, longitude)
                VALUES ('ESC-1', 1, $1, 11.7, 122.3) RETURNING id
            ''', datetime.now(UTC) - timedelta(minutes=3))
        finally:
            await conn.close()

    event_id = asyncio.run(seed())
    async def check():
        from app import scheduler

        pool = await asyncpg.create_pool(probe_db)
        monkeypatch.setattr(scheduler, 'get_pool', lambda: pool)
        try:
            assert await run_job_once('probe-sos-escalation', run_escalation_job)
            async with pool.acquire() as conn:
                event = await conn.fetchrow('SELECT escalated_at FROM sos_events WHERE id = $1', event_id)
                audit = await conn.fetchrow(
                    "SELECT action, outcome FROM operations_audit_events "
                    "WHERE action = 'sos.escalate' AND resource_id = $1",
                    str(event_id),
                )
                assert event['escalated_at'] is not None
                assert audit['action'] == 'sos.escalate'
                assert audit['outcome'] == 'not_configured'
                assert await conn.fetchval(
                    "SELECT last_run_at FROM scheduler_runs WHERE job = 'probe-sos-escalation'"
                ) is not None
        finally:
            await pool.close()

    asyncio.run(check())
    with TestClient(app) as client:
        status = client.get('/api/ops/status', headers=_headers())
    assert status.status_code == 200
    assert status.json()['sms_configured'] is False
    assert status.json()['scheduler_last_run']['probe-sos-escalation'] is not None


def test_ops_status_reports_database_expiry_and_sms_configuration(probe_db, monkeypatch):
    expiry = (datetime.now(UTC).date() + timedelta(days=20)).isoformat()
    monkeypatch.setenv('DB_EXPIRES_AT', expiry)
    monkeypatch.setenv('SEMAPHORE_API_KEY', 'test-key')
    monkeypatch.setenv('ONCALL_SMS_NUMBERS', '+639171234567')
    with TestClient(app) as client:
        response = client.get('/api/ops/status', headers=_headers())
    assert response.status_code == 200
    body = response.json()
    assert body['sms_configured'] is True
    assert body['db_expires_at'] == expiry
    assert body['db_days_left'] == 20
    assert 'scheduler_last_run' in body


def test_ops_status_scheduler_keys_match_contract(probe_db, monkeypatch):
    async def check():
        pool = await asyncpg.create_pool(probe_db)
        monkeypatch.setattr(scheduler, 'get_pool', lambda: pool)
        try:
            async def no_op():
                return None

            assert await scheduler.run_job_once(ESCALATION_JOB, no_op)
            assert await scheduler.run_job_once(ANOMALY_JOB, no_op)
        finally:
            await pool.close()

    asyncio.run(check())
    with TestClient(app) as client:
        response = client.get('/api/ops/status', headers=_headers())
    assert response.status_code == 200
    assert set(response.json()['scheduler_last_run']) == {'escalation', 'anomaly'}


def test_scheduler_starts_the_contract_jobs(monkeypatch):
    async def check():
        job_ids = []

        async def record(job_id, interval, fn):
            job_ids.append(job_id)

        monkeypatch.setattr(scheduler, '_run_periodically', record)
        await scheduler.start()
        await asyncio.sleep(0)
        await scheduler.stop()
        assert set(job_ids) == {'escalation', 'anomaly'}

    asyncio.run(check())
