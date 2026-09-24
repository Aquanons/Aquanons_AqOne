import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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
