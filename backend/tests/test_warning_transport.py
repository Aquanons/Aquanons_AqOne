"""Tests for warning delivery state tracking (Phase 2 Task 2.5)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app import db as app_db
from app.api import advisories as advisories_api
from app.auth import create_token
from app.main import app


class _FakeWarnConn:
    def __init__(self, pool: _FakeWarnPool):
        self.pool = pool

    async def fetchrow(self, query: str, *args):
        if 'SELECT id FROM advisories WHERE id = $1' in query:
            wid = args[0]
            if wid in self.pool.advisories:
                return {'id': wid}
            return None

        if 'SELECT id, warning_id, delivery_state' in query and 'warning_delivery_events' in query:
            wid = args[0]
            state = args[1]
            vessel = args[2]
            buoy = args[3]
            for d in self.pool.deliveries:
                if (
                    d['warning_id'] == wid
                    and d['delivery_state'] == state
                    and d.get('vessel_id') == vessel
                    and d.get('buoy_id') == buoy
                ):
                    return d
            return None

        if 'INSERT INTO warning_delivery_events' in query:
            row = {
                'id': len(self.pool.deliveries) + 1,
                'warning_id': args[0],
                'vessel_id': args[1],
                'buoy_id': args[2],
                'delivery_state': args[3],
                'occurred_at': args[4],
                'recorded_at': datetime.now(UTC),
                'details': args[5],
            }
            self.pool.deliveries.append(row)
            return row

        raise AssertionError(f'unexpected query: {query}')

    async def fetch(self, query: str, *args):
        if 'SELECT id, warning_id, vessel_id, buoy_id, delivery_state' in query:
            wid = args[0]
            return [d for d in self.pool.deliveries if d['warning_id'] == wid]
        raise AssertionError(f'unexpected query: {query}')


class _FakeWarnAcquire:
    def __init__(self, conn: _FakeWarnConn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


class _FakeWarnPool:
    def __init__(self):
        self.advisories = {101, 102}
        self.deliveries: list[dict[str, object]] = []

    def acquire(self):
        return _FakeWarnAcquire(_FakeWarnConn(self))


GATEWAY_KEY = 'test-gateway-key'
GW_HEADERS = {'X-Api-Key': GATEWAY_KEY}
OP_HEADERS = {'Authorization': f'Bearer {create_token(1, "mdrrmo@test.local", "mdrrmo")}'}


def test_warning_delivery_lifecycle_and_validation(monkeypatch):
    fake_pool = _FakeWarnPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(advisories_api, 'get_pool', lambda: fake_pool)
    monkeypatch.setenv('GATEWAY_API_KEY', GATEWAY_KEY)

    with TestClient(app, raise_server_exceptions=False) as client:
        # Invalid delivery state
        res_bad = client.post(
            '/api/advisories/delivery',
            json={'warning_id': 101, 'delivery_state': 'delivered_somewhere'},
            headers=GW_HEADERS,
        )
        assert res_bad.status_code == 422

        # Nonexistent warning
        res_404 = client.post(
            '/api/advisories/delivery',
            json={'warning_id': 999, 'delivery_state': 'gateway_accepted'},
            headers=GW_HEADERS,
        )
        assert res_404.status_code == 404

        # Step 1: gateway_accepted
        res_gw = client.post(
            '/api/advisories/delivery',
            json={
                'warning_id': 101,
                'delivery_state': 'gateway_accepted',
                'buoy_id': 'SHORE01',
            },
            headers=GW_HEADERS,
        )
        assert res_gw.status_code == 200
        assert res_gw.json()['delivery_state'] == 'gateway_accepted'

        # Step 2: buoy_received
        res_buoy = client.post(
            '/api/advisories/delivery',
            json={
                'warning_id': 101,
                'delivery_state': 'buoy_received',
                'buoy_id': 'BUOY01',
            },
            headers=GW_HEADERS,
        )
        assert res_buoy.status_code == 200

        # Step 3: phone_received
        res_phone = client.post(
            '/api/advisories/delivery',
            json={
                'warning_id': 101,
                'delivery_state': 'phone_received',
                'vessel_id': 'NW-001',
                'buoy_id': 'BUOY01',
            },
            headers=GW_HEADERS,
        )
        assert res_phone.status_code == 200

        # Step 4: user_acknowledged without vessel_id must be rejected (422)
        res_ack_no_vessel = client.post(
            '/api/advisories/delivery',
            json={
                'warning_id': 101,
                'delivery_state': 'user_acknowledged',
            },
            headers=GW_HEADERS,
        )
        assert res_ack_no_vessel.status_code == 422

        # Step 4: user_acknowledged with vessel_id succeeds
        res_ack = client.post(
            '/api/advisories/delivery',
            json={
                'warning_id': 101,
                'delivery_state': 'user_acknowledged',
                'vessel_id': 'NW-001',
            },
            headers=GW_HEADERS,
        )
        assert res_ack.status_code == 200

        # Query deliveries for warning 101
        res_list = client.get('/api/advisories/101/deliveries', headers=OP_HEADERS)
        assert res_list.status_code == 200
        events = res_list.json()['deliveries']
        assert len(events) == 4
        states = [e['delivery_state'] for e in events]
        assert states == [
            'gateway_accepted',
            'buoy_received',
            'phone_received',
            'user_acknowledged',
        ]


def test_advisories_philippine_standard_time_today(monkeypatch):
    """W2: Publication date and today calculation must use Philippine Standard Time (UTC+8)."""
    from datetime import timedelta, timezone
    pht = timezone(timedelta(hours=8))

    # At 22:30 UTC on Sep 15, it is 06:30 PHT on Sep 16
    fixed_utc = datetime(2026, 9, 15, 22, 30, 0, tzinfo=UTC)

    class FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            if tz == UTC:
                return fixed_utc
            if tz == pht or (tz and tz.utcoffset(None) == timedelta(hours=8)):
                return fixed_utc.astimezone(pht)
            return fixed_utc

    monkeypatch.setattr(advisories_api, 'datetime', FixedDatetime)

    # In Philippine time, it is already Sep 16
    today = advisories_api._today()
    assert today == date(2026, 9, 16), f"Expected Sep 16 in PHT, got {today}"


def test_warning_delivery_deduplication_and_idempotency(monkeypatch):
    """W6: Duplicate gateway/buoy/phone events must be deduped, not duplicate rows."""
    fake_pool = _FakeWarnPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(advisories_api, 'get_pool', lambda: fake_pool)
    monkeypatch.setenv('GATEWAY_API_KEY', GATEWAY_KEY)

    with TestClient(app, raise_server_exceptions=False) as client:
        payload = {
            'warning_id': 101,
            'delivery_state': 'buoy_received',
            'buoy_id': 'BUOY01',
        }
        res1 = client.post('/api/advisories/delivery', json=payload, headers=GW_HEADERS)
        assert res1.status_code == 200

        # Submitting the identical delivery event again
        res2 = client.post('/api/advisories/delivery', json=payload, headers=GW_HEADERS)
        assert res2.status_code == 200
        assert res2.json().get('deduped') is True

        res_list = client.get('/api/advisories/101/deliveries', headers=OP_HEADERS)
        events = res_list.json()['deliveries']
        assert len(events) == 1, "Duplicate delivery event was inserted instead of deduped"


def test_advisories_delivery_unauthenticated_rejected(monkeypatch):
    """SEC-10: Delivery POST requires gateway key, deliveries GET requires operator auth."""
    fake_pool = _FakeWarnPool()
    monkeypatch.setattr(app_db, 'get_pool', lambda: fake_pool)
    monkeypatch.setattr(advisories_api, 'get_pool', lambda: fake_pool)

    with TestClient(app, raise_server_exceptions=False) as client:
        # POST without gateway key -> 401
        res_post = client.post(
            '/api/advisories/delivery',
            json={'warning_id': 101, 'delivery_state': 'gateway_accepted'},
        )
        assert res_post.status_code == 401

        # GET without operator token -> 401
        res_get = client.get('/api/advisories/101/deliveries')
        assert res_get.status_code == 401


def test_loam_frame_codec_and_relay_tamper_detection():
    """W3: Authentic frame traverses gateway -> relay -> receiver; corrupted or tampered frame rejected."""
    from app.mesh.loam import (
        T_WARN,
        WarningCache,
        build_warn_payload,
        decode_frame,
        encode_frame,
        relay_frame,
    )

    adv = {
        'id': 105,
        'revision': 1,
        'title': 'Gale Warning',
        'priority': 'Warning',
        'municipality': 'New Washington',
        'description': 'Rough seas expected over eastern seaboard',
        'publish_date': 1789401600,
        'expiration_date': 1789488000,
    }
    payload = build_warn_payload(adv)

    # 1. Gateway encodes frame
    gw_frame = encode_frame(
        msg_type=T_WARN,
        src=0x00020001,
        relay=0x00020001,
        seq=42,
        ts=1789401600,
        ttl=4,
        hops=0,
        payload=payload,
    )
    assert len(gw_frame) > 30

    # 2. Relay buoy advances hops and updates relay ID
    relayed_frame = relay_frame(gw_frame, relay_id=0x00010001)
    assert relayed_frame is not None

    # 3. Receiving buoy decodes relayed frame successfully
    decoded = decode_frame(relayed_frame)
    assert decoded is not None
    assert decoded['type'] == T_WARN
    assert decoded['ttl'] == 3
    assert decoded['hops'] == 1
    assert decoded['relay'] == 0x00010001

    cache = WarningCache()
    assert cache.put(payload, current_time=1789401700) is True
    assert len(cache.get_active(current_time=1789401700)) == 1

    # 4. Altered payload bytes (tampering) fails verification
    tampered_bytes = bytearray(relayed_frame)
    tampered_bytes[25] ^= 0xFF
    assert decode_frame(bytes(tampered_bytes)) is None

    # 5. Wrong HMAC key fails verification
    wrong_key = b'wrong-attacker-key-here'
    assert decode_frame(relayed_frame, key=wrong_key) is None

    # 6. Corrupt / excessive hops (> 15) dropped
    bad_hops = bytearray(relayed_frame)
    bad_hops[19] = 16
    assert decode_frame(bytes(bad_hops)) is None

    # 7. Expired payload rejected by cache
    expired_payload = dict(payload, exp=1789400000)
    assert cache.put(expired_payload, current_time=1789401700) is False


def test_warning_rebroadcast_retry_queue_and_backoff():
    """W4: Gateway rebroadcast retry queue honors bounded retries and exponential backoff."""
    from app.mesh.loam import T_WARN, RadioPriorityScheduler, encode_frame

    sched = RadioPriorityScheduler()
    frame = encode_frame(msg_type=T_WARN, src=0x00020001, seq=1, payload={'id': 101, 'pr': 'Warning'})

    sched.enqueue_warning(frame, warning_id=101, max_retries=3, backoff_intervals=[30, 60, 120])

    # t=0: Attempt 1
    out1 = sched.pop_next(current_time=0)
    assert out1 == frame

    # t=15: Still in backoff interval (next is at 30)
    assert sched.pop_next(current_time=15) is None

    # t=30: Attempt 2 (next backoff 60 -> next attempt at 90)
    out2 = sched.pop_next(current_time=30)
    assert out2 == frame

    # t=70: In backoff
    assert sched.pop_next(current_time=70) is None

    # t=90: Attempt 3 (reaches max retries 3 -> exhausted)
    out3 = sched.pop_next(current_time=90)
    assert out3 == frame

    # t=200: Queue is exhausted, no further broadcasts
    assert sched.pop_next(current_time=200) is None


def test_warning_revision_superseding_and_cancellation_tombstone():
    """W5: Newer revision supersedes older; cancelled warning cannot be resurrected by old frame."""
    from app.mesh.loam import WarningCache

    cache = WarningCache()

    # 1. Initial warning rev=1
    w1 = {'id': 201, 'rev': 1, 'ttl': 'Gale Warning', 'pr': 'Warning', 'exp': 1000}
    assert cache.put(w1, current_time=100) is True
    assert len(cache.get_active(current_time=100)) == 1

    # 2. Older or duplicate revision (rev=1 or rev=0) arrives -> rejected
    w_old = {'id': 201, 'rev': 0, 'ttl': 'Old Title', 'pr': 'Warning', 'exp': 1000}
    assert cache.put(w_old, current_time=100) is False
    assert cache.get_active(current_time=100)[0]['ttl'] == 'Gale Warning'

    # 3. Newer revision rev=2 arrives -> accepted and replaces rev=1
    w2 = {'id': 201, 'rev': 2, 'ttl': 'Severe Gale Warning', 'pr': 'Emergency', 'exp': 1000}
    assert cache.put(w2, current_time=100) is True
    assert cache.get_active(current_time=100)[0]['ttl'] == 'Severe Gale Warning'
    assert cache.get_active(current_time=100)[0]['pr'] == 'Emergency'

    # 4. Cancellation notice rev=3 arrives -> removes warning and sets tombstone
    w_cancel = {'id': 201, 'rev': 3, 'cancelled': True}
    assert cache.put(w_cancel, current_time=100) is True
    assert len(cache.get_active(current_time=100)) == 0

    # 5. Old frame rev=2 arrives later -> rejected by tombstone, cannot resurrect
    assert cache.put(w2, current_time=100) is False
    assert len(cache.get_active(current_time=100)) == 0

    # 6. Expiry pruning
    w3 = {'id': 202, 'rev': 1, 'ttl': 'Squall', 'exp': 200}
    cache.put(w3, current_time=100)
    assert len(cache.get_active(current_time=100)) == 1
    # Time advances past expiry
    assert len(cache.get_active(current_time=250)) == 0

    # 7. Max 6 slots bound
    for i in range(10, 18):
        cache.put({'id': i, 'rev': 1, 'ttl': f'Notice {i}', 'exp': 5000}, current_time=100)
    assert len(cache.get_active(current_time=100)) <= WarningCache.MAX_SLOTS


def test_sos_absolute_priority_over_warning_traffic():
    """W7: Distress SOS frames take absolute priority over warning rebroadcasts."""
    from app.mesh.loam import T_SOS, T_WARN, RadioPriorityScheduler, encode_frame

    sched = RadioPriorityScheduler()

    # Fill warning queue with multiple retries
    w_frame1 = encode_frame(msg_type=T_WARN, src=0x00020001, seq=10, payload={'id': 301})
    w_frame2 = encode_frame(msg_type=T_WARN, src=0x00020001, seq=11, payload={'id': 302})
    sched.enqueue_warning(w_frame1, warning_id=301)
    sched.enqueue_warning(w_frame2, warning_id=302)

    # An SOS frame arrives
    sos_frame = encode_frame(msg_type=T_SOS, src=0x00010001, seq=1, payload={'vessel_id': 'NW-001'})
    sched.enqueue_sos(sos_frame)

    # pop_next MUST return the SOS frame first, regardless of pending warnings
    first_tx = sched.pop_next(current_time=0)
    assert first_tx == sos_frame

    # Subsequent pops yield warning frames only after SOS queue is empty
    second_tx = sched.pop_next(current_time=0)
    assert second_tx == w_frame1

