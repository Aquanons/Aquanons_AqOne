"""Shared harness for the security-audit verification probes.

Every probe asserts the SAFE behaviour for one finding in
docs/security-audit/NEEDS-VALIDATION.md:

  FAILED with AssertionError / "Failed:"  -> CONFIRMED (unsafe behaviour observed)
  PASSED                                  -> REFUTED   (the safe behaviour holds)
  FAILED with ProbeBroken or any other exception, or ERROR
                                          -> INCONCLUSIVE (the probe broke)
  SKIPPED                                 -> NOT RUN   (e.g. no local Postgres)

Tests whose finding id ends in ':control' check the harness can see the
behaviour at all; they must PASS, or the paired probe is INCONCLUSIVE.

The finding id travels into the JUnit XML as a <property name="finding">,
so the results report can be generated without re-reading test names.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from urllib.parse import urlparse

import asyncpg
import pytest

import migrate

LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}


def pytest_configure(config):
    config.addinivalue_line('markers', 'finding(id): the audit finding id this probe verifies')


@pytest.fixture(autouse=True)
def _tag_finding(request, record_property):
    marker = request.node.get_closest_marker('finding')
    if marker is not None:
        record_property('finding', marker.args[0])


@pytest.fixture
def probe_db(monkeypatch):
    """A fresh, fully migrated, throwaway Postgres database per test.

    Needs AQONE_PROBE_PG_ADMIN_URL pointing at a LOCAL server's maintenance
    database (e.g. postgresql://postgres:<pw>@localhost:5432/postgres). The
    probe creates aqone_probe_<random>, points DATABASE_URL at it, runs every
    migration, and drops it afterwards. It refuses any non-local host.
    """
    admin_url = os.environ.get('AQONE_PROBE_PG_ADMIN_URL')
    if not admin_url:
        pytest.skip('AQONE_PROBE_PG_ADMIN_URL is not set - DB probe not run')
    parsed = urlparse(admin_url)
    if parsed.hostname not in LOCAL_HOSTS:
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
