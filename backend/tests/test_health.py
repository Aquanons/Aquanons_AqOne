from fastapi.testclient import TestClient

from app import db as app_db
from app.main import app


class _FakePool:
    async def close(self) -> None:
        return None

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return None

    async def fetchval(self, _query: str):
        return 1


def test_healthz_returns_200(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example')

    async def fake_create_pool(_url):
        return _FakePool()

    monkeypatch.setattr(app_db.asyncpg, 'create_pool', fake_create_pool)

    with TestClient(app) as client:
        response = client.get('/healthz')

    assert response.status_code == 200


def test_startup_without_database_url_stays_alive(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        health = client.get('/healthz')
        ready = client.get('/health/ready')

    assert health.status_code == 200
    assert ready.status_code == 503


def test_ready_reports_the_deployed_commit(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example')
    monkeypatch.setenv('RENDER_GIT_COMMIT', 'abc1234def')

    async def fake_create_pool(_url):
        return _FakePool()

    monkeypatch.setattr(app_db.asyncpg, 'create_pool', fake_create_pool)

    with TestClient(app) as client:
        ready = client.get('/health/ready')
        monkeypatch.delenv('RENDER_GIT_COMMIT')
        local = client.get('/health/ready')

    assert ready.status_code == 200
    assert ready.json() == {'status': 'ok', 'commit': 'abc1234def'}
    assert local.json() == {'status': 'ok', 'commit': None}
