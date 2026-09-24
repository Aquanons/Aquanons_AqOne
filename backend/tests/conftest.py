import asyncio
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
import pytest

import migrate

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('AQONE_SCHEDULER', '0')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Security-audit probes assert the safe behaviour and are expected to fail
# while a finding is open, so they stay out of the default green suite.
# Run them with AQONE_SECURITY_PROBES=1 (docs/security-audit/PROBES.md).
collect_ignore_glob = [] if os.environ.get('AQONE_SECURITY_PROBES') == '1' else ['security_probes/*']


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'real_user_session: test exercises the real user session database lookup in app.auth',
    )
    config.addinivalue_line('markers', 'finding(id): the audit finding id this probe verifies')


@pytest.fixture
def probe_db(monkeypatch):
    """A fresh, fully migrated, throwaway Postgres database per test."""
    admin_url = os.environ.get('AQONE_PROBE_PG_ADMIN_URL')
    if not admin_url:
        pytest.skip('AQONE_PROBE_PG_ADMIN_URL is not set - DB probe not run')
    parsed = urlparse(admin_url)
    if parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
        pytest.fail('refusing to run: AQONE_PROBE_PG_ADMIN_URL must point at localhost')

    name = f'aqone_probe_{uuid.uuid4().hex[:12]}'
    url = parsed._replace(path=f'/{name}').geturl()

    async def admin(sql: str) -> None:
        conn = await asyncpg.connect(admin_url)
        try:
            await conn.execute(sql)
        finally:
            await conn.close()

    asyncio.run(admin(f'CREATE DATABASE {name}'))
    try:
        monkeypatch.setenv('DATABASE_URL', url)
        asyncio.run(migrate.main())

        async def seed_probe_operator():
            conn = await asyncpg.connect(url)
            try:
                await conn.execute(
                    '''
                    INSERT INTO users (id, email, email_normalized, password_hash, role, token_version)
                    VALUES (1, 'probe.mdrrmo@example.invalid', 'probe.mdrrmo@example.invalid', 'hash', 'mdrrmo', 0)
                    ON CONFLICT DO NOTHING
                    '''
                )
            finally:
                await conn.close()

        asyncio.run(seed_probe_operator())
        yield url
    finally:
        asyncio.run(admin(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)'))


@pytest.fixture(autouse=True)
def _stub_user_session_for_fake_pools(request, monkeypatch):
    if 'security_probes' in str(request.fspath) or 'test_security_regressions' in str(request.fspath):
        return
    if request.node.get_closest_marker('real_user_session'):
        return

    async def _stub_verify(user_id, claims):
        return {
            'id': str(claims.get('sub', user_id)),
            'email': claims.get('email'),
            'role': claims.get('role'),
        }

    monkeypatch.setattr('app.auth.verify_user_session', _stub_verify)
