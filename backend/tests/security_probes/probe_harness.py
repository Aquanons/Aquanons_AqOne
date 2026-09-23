"""Helpers shared by the security-audit probes (see conftest.py for verdict rules)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from app.auth import create_token

REPO_ROOT = Path(__file__).resolve().parents[3]


class ProbeBroken(RuntimeError):
    """The probe could not observe the behaviour (bad fixture, 422 body...).

    Raised instead of an assertion so the report marks the finding
    INCONCLUSIVE rather than CONFIRMED.
    """


def require_status(response, *codes: int) -> None:
    if response.status_code not in codes:
        raise ProbeBroken(f'expected HTTP {codes}, got {response.status_code}: {response.text[:300]}')


class FakeConn:
    """An asyncpg stand-in that records every query.

    `responder(kind, sql, args)` supplies return values; `sql` is whitespace-
    collapsed so probes can match on fragments. Doubles as the pool.
    """

    def __init__(self, responder=None):
        self.calls: list[tuple[str, str, tuple]] = []
        self._responder = responder or (lambda kind, sql, args: None)

    async def _run(self, kind, sql, args):
        flat = ' '.join(sql.split())
        self.calls.append((kind, flat, args))
        return self._responder(kind, flat, args)

    async def execute(self, sql, *args):
        result = await self._run('execute', sql, args)
        return 'OK' if result is None else result

    async def fetchrow(self, sql, *args):
        return await self._run('fetchrow', sql, args)

    async def fetchval(self, sql, *args):
        return await self._run('fetchval', sql, args)

    async def fetch(self, sql, *args):
        result = await self._run('fetch', sql, args)
        return [] if result is None else result

    def transaction(self):
        return _NullContext(None)

    def acquire(self):
        return _NullContext(self)

    def calls_matching(self, fragment: str) -> list[tuple[str, str, tuple]]:
        return [call for call in self.calls if fragment in call[1]]


class _NullContext:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


def install_pool(monkeypatch, conn: FakeConn, *module_names: str) -> None:
    """Route get_pool() to `conn` in app.db and every module that imported it.

    DATABASE_URL is removed first so app startup can never reach a real
    database from a fake-pool probe.
    """
    import importlib

    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr('app.db.get_pool', lambda: conn)
    for name in module_names:
        monkeypatch.setattr(importlib.import_module(name), 'get_pool', lambda: conn)


def operator_headers(role: str = 'mdrrmo', user_id: int = 1) -> dict[str, str]:
    token = create_token(user_id, f'probe.{role}@example.invalid', role)
    return {'Authorization': f'Bearer {token}'}


def now_utc() -> datetime:
    return datetime.now(UTC)


def run_db(url: str, body):
    """Run `await body(conn)` on a fresh connection to `url` and return it."""

    async def go():
        conn = await asyncpg.connect(url)
        try:
            return await body(conn)
        finally:
            await conn.close()

    return asyncio.run(go())
