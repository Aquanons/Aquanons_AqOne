"""Operator login, session lifetime, and the squall training switch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from probe_harness import FakeConn, install_pool, operator_headers, require_status

from app.main import app


@pytest.mark.finding('backend.auth.login-timing-enumeration')
def test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password(monkeypatch):
    """Deterministic stand-in for a timing measurement: bcrypt is the only
    expensive step, so count how often it runs on each branch."""
    install_pool(monkeypatch, FakeConn(), 'app.api.auth')
    calls = []

    def counting_verify(password, password_hash):
        calls.append(password_hash)
        return False

    monkeypatch.setattr('app.api.auth.verify_password', counting_verify)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/login', json={'email': 'nobody@example.com', 'password': 'x'})
    require_status(response, 401)
    assert len(calls) == 1, (
        f'login for an unknown email ran bcrypt {len(calls)} times; a known email with a wrong '
        'password runs it once, so response time reveals which emails have accounts'
    )


@pytest.mark.finding('backend.operator-jwt.no-server-revocation')
def test_token_for_an_account_that_no_longer_exists_is_rejected(monkeypatch):
    """The fake database holds no users at all, standing in for an account
    that was deleted or disabled after the token was issued."""
    conn = FakeConn()
    install_pool(monkeypatch, conn, 'app.api.auth')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/me', headers=operator_headers(user_id=987654))
    assert response.status_code == 401, (
        f'a token for a non-existent operator was accepted (HTTP {response.status_code}); '
        f'the server consulted {len(conn.calls)} database queries to check it'
    )


def _stub_training(monkeypatch):
    import inspect
    caller_frame = inspect.currentframe().f_back
    caller_role = caller_frame.f_locals.get('role', 'admin') if caller_frame else 'admin'

    def responder(kind, sql, args):
        if 'FROM users' in sql and args and args[0] == 1:
            return {'id': 1, 'email': f'probe.{caller_role}@example.invalid', 'role': caller_role, 'token_version': 0}
        return None

    install_pool(monkeypatch, FakeConn(responder), 'app.api.squall')
    monkeypatch.setenv('ALLOW_TRAINING', 'true')
    writes = []

    async def fake_rows(conn, *, live):
        return [{'reading': 1}], [{'squall': 1}], []

    monkeypatch.setattr('app.api.squall._load_rows', fake_rows)
    monkeypatch.setattr('app.api.squall.build_buoys', lambda rows: {})
    monkeypatch.setattr(
        'app.api.squall.train_from_rows',
        lambda readings, squalls, buoys: (SimpleNamespace(calibration='probe', top_features=[]), {}),
    )
    monkeypatch.setattr('app.api.squall.save_bundle', writes.append)
    return writes


@pytest.mark.finding('backend.ai.squall.flag-authorizes-live-model-replacement')
@pytest.mark.parametrize('role', ['mdrrmo', 'lgu'])
def test_non_admin_operator_cannot_replace_the_live_squall_model(monkeypatch, role):
    writes = _stub_training(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/ai/squall/train', headers=operator_headers(role=role))
    assert not writes and response.status_code == 403, (
        f'with ALLOW_TRAINING=true a {role} token got HTTP {response.status_code} and '
        f'{len(writes)} model write(s) to the live squall artifact'
    )


@pytest.mark.finding('backend.ai.squall.flag-authorizes-live-model-replacement:control')
def test_squall_control_admin_reaches_the_model_write(monkeypatch):
    writes = _stub_training(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/ai/squall/train', headers=operator_headers(role='admin'))
    assert response.status_code == 200 and len(writes) == 1, response.text
