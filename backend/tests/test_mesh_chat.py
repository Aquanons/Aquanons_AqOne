"""The mesh chat relay has to stay reachable and stay unauthenticated.

Two ways this silently breaks, both of which have already happened once:

  * The router is never registered, so /api/mesh/chat falls through to the
    static dashboard mount at "/" and answers with HTML. The hub's POSTs get a
    404 it has no way to report, and messages from sea simply vanish.
  * The router gets swept up in the `_protected` list. Every other router
    belongs there, but the Heltec hub and the fishermen behind it have no
    accounts and no token to send, so auth on this path takes the relay down
    for exactly the people it exists to serve.

There is no database in the test environment, so the routes answer 503 from
get_pool(). That is fine - what is being asserted is which layer answered.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api import mesh as mesh_api
from app.main import app

CHAT = '/api/mesh/chat'


class _FakeMeshPool:
    """Enough of asyncpg's pool surface to exercise the real insert/query SQL
    in mesh.py without a database - see test_vessel_auth.py::_FakePool for
    the pattern this follows."""

    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []
        self._next_id = 1

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetchrow(self, query: str, *args):
        assert 'INSERT INTO mesh_chat' in query
        sender, text, origin = args
        row = {
            'id': self._next_id,
            'sender': sender,
            'text': text,
            'origin': origin,
            'created_at': datetime.now(UTC),
        }
        self._next_id += 1
        self.rows.append(row)
        return row

    async def execute(self, query: str, *args):
        return 'OK'

    async def fetch(self, query: str, *args):
        assert 'FROM mesh_chat' in query
        if 'WHERE id > $1' in query:
            since_id, limit = args
            return [row for row in self.rows if row['id'] > since_id][:limit]
        (limit,) = args
        return list(reversed(self.rows[-limit:]))


def _patch_pool(monkeypatch, pool: _FakeMeshPool) -> None:
    monkeypatch.setattr(mesh_api, 'get_pool', lambda: pool)


def test_chat_history_is_served_by_the_api_not_the_static_mount(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        response = client.get(CHAT)

    assert 'application/json' in response.headers['content-type']
    assert response.status_code == 503, 'no database here; 404 would mean unrouted'


def test_chat_ingest_is_served_by_the_api_not_the_static_mount(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        response = client.post(CHAT, json={'sender': 'Boat-1', 'text': 'engine trouble'})

    assert 'application/json' in response.headers['content-type']
    assert response.status_code == 503


def test_chat_does_not_require_a_bearer_token(monkeypatch):
    """The hub cannot authenticate. Neither leg of the relay may demand it."""
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        get = client.get(CHAT)
        post = client.post(CHAT, json={'sender': 'Boat-1', 'text': 'hello'})

    for response in (get, post):
        assert response.status_code not in (401, 403), (
            'mesh chat was moved behind require_user - the Heltec hub has no '
            'token and the relay stops carrying messages'
        )


def test_validation_runs_before_the_database(monkeypatch):
    """A malformed POST is rejected on its own merits, not masked by the 503."""
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        assert client.post(CHAT, json={'sender': '', 'text': 'x'}).status_code == 422
        assert client.post(CHAT, json={'sender': 'a', 'text': ''}).status_code == 422
        # The firmware clamps outgoing text to 256 bytes; the model must agree,
        # or the hub's own messages start bouncing back as validation errors.
        assert (
            client.post(CHAT, json={'sender': 'a', 'text': 'x' * 257}).status_code == 422
        )


def test_since_id_rejects_a_negative_cursor(monkeypatch):
    """The hub sends its stored cursor verbatim; a corrupt one must not scan
    the whole table."""
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        assert client.get(f'{CHAT}?since_id=-1').status_code == 422


def test_other_api_routers_are_still_protected(monkeypatch):
    """Contrast case: opening up mesh must not have opened up everything."""
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with TestClient(app) as client:
        response = client.get('/api/sea-condition')

    assert response.status_code in (401, 403)


def test_ingest_returns_201_only_once_the_row_is_persisted(monkeypatch):
    """The handset's 'cloud relay stored' fact is only true after this."""
    pool = _FakeMeshPool()
    _patch_pool(monkeypatch, pool)

    with TestClient(app) as client:
        response = client.post(
            CHAT, json={'sender': 'Maria Gracia', 'text': 'heading back'}
        )

    assert response.status_code == 201
    body = response.json()
    assert body['sender'] == 'Maria Gracia'
    assert body['text'] == 'heading back'
    assert body['origin'] == 'app'
    assert pool.rows and pool.rows[0]['sender'] == 'Maria Gracia'


def test_since_id_returns_only_newer_messages_in_ascending_order(monkeypatch):
    """A hub/handset that was offline must catch up in order, not skip a gap."""
    pool = _FakeMeshPool()
    _patch_pool(monkeypatch, pool)

    with TestClient(app) as client:
        for text in ('first', 'second', 'third'):
            client.post(CHAT, json={'sender': 'Boat-1', 'text': text})

        response = client.get(f'{CHAT}?since_id=1')

    assert response.status_code == 200
    messages = response.json()['messages']
    assert [m['text'] for m in messages] == ['second', 'third']
    assert [m['id'] for m in messages] == sorted(m['id'] for m in messages)


def test_get_without_since_id_returns_the_most_recent_window_oldest_first(
    monkeypatch,
):
    pool = _FakeMeshPool()
    _patch_pool(monkeypatch, pool)

    with TestClient(app) as client:
        for text in ('a', 'b', 'c'):
            client.post(CHAT, json={'sender': 'Boat-1', 'text': text})

        response = client.get(f'{CHAT}?limit=2')

    messages = response.json()['messages']
    assert [m['text'] for m in messages] == ['b', 'c']
