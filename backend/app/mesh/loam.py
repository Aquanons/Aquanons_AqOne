"""LoAM mesh protocol codec and radio behavior simulation.

Implements binary LoAM frame encoding/decoding, HMAC signing, payload building,
warning caching with revision/expiry/cancellation logic, and priority queueing
where SOS traffic has absolute priority over warning rebroadcasts.
Per docs/02_LOAM_PACKET_SPEC.md and firmware/AqOneLoam.h.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
from collections import deque
from datetime import datetime
from typing import Any

# Frame constants
LOAM_MAGIC = 0xA5
LOAM_VERSION = 0x01

# Types
T_SOS = 0x01
T_ACK = 0x02
T_PING = 0x03
T_STATUS = 0x04
T_CHAT = 0x05
T_ETA = 0x06
T_WARN = 0x07

# Flags
F_SIGNED = 0x01
F_WANTS_ACK = 0x02
F_ACK = 0x04
F_KNOWN = 0x07

# Sizes
LOAM_HEADER = 22
LOAM_SIG_LEN = 8
LOAM_MAX_PAYLOAD = 225
LOAM_MAX_FRAME = LOAM_HEADER + LOAM_MAX_PAYLOAD + LOAM_SIG_LEN

DEFAULT_LOAM_KEY = b'aqone-dev-key-change-me'


def loam_sign(frame: bytes, payload_len: int, key: bytes = DEFAULT_LOAM_KEY) -> bytes:
    """HMAC-SHA256 truncated to 8 bytes, over the frame with relay-mutable bytes zeroed.

    Neutralized fields:
      - RELAY_ID (offsets 8..11, 4 bytes)
      - TTL & HOPS (offsets 18..19, 2 bytes)
    Region hashed:
      frame[0..7] ++ {0,0,0,0} ++ frame[12..17] ++ {0,0} ++ frame[20..21+payload_len]
    """
    zero_relay = b'\x00\x00\x00\x00'
    zero_hops = b'\x00\x00'
    data_to_sign = (
        frame[:8]
        + zero_relay
        + frame[12:18]
        + zero_hops
        + frame[20 : 22 + payload_len]
    )
    full_hmac = hmac.new(key, data_to_sign, hashlib.sha256).digest()
    return full_hmac[:LOAM_SIG_LEN]


def encode_frame(
    msg_type: int,
    flags: int = 0,
    src: int = 0,
    relay: int = 0,
    seq: int = 0,
    ts: int = 0,
    ttl: int = 4,
    hops: int = 0,
    payload: bytes | str | dict[str, Any] = b'',
    key: bytes = DEFAULT_LOAM_KEY,
) -> bytes:
    """Encode a binary LoAM frame with HMAC signature."""
    if isinstance(payload, dict):
        raw_payload = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    elif isinstance(payload, str):
        raw_payload = payload.encode('utf-8')
    else:
        raw_payload = bytes(payload)

    payload_len = len(raw_payload)
    if payload_len > LOAM_MAX_PAYLOAD:
        raise ValueError(f'Payload len {payload_len} exceeds max {LOAM_MAX_PAYLOAD}')

    effective_flags = flags | F_SIGNED
    header = struct.pack(
        '>BBBBIIHIBBH',
        LOAM_MAGIC,
        LOAM_VERSION,
        msg_type,
        effective_flags,
        src,
        relay,
        seq,
        ts,
        ttl,
        hops,
        payload_len,
    )
    body = header + raw_payload
    sig = loam_sign(body, payload_len, key)
    return body + sig


def decode_frame(data: bytes, key: bytes = DEFAULT_LOAM_KEY) -> dict[str, Any] | None:
    """Decode and verify a binary LoAM frame. Returns None on any parse or verification error."""
    if len(data) < LOAM_HEADER + LOAM_SIG_LEN:
        return None

    magic, version, msg_type, flags, src, relay, seq, ts, ttl, hops, payload_len = (
        struct.unpack('>BBBBIIHIBBH', data[:LOAM_HEADER])
    )

    if magic != LOAM_MAGIC or version != LOAM_VERSION:
        return None
    if flags & ~F_KNOWN:
        return None
    if payload_len > LOAM_MAX_PAYLOAD:
        return None
    if len(data) != LOAM_HEADER + payload_len + LOAM_SIG_LEN:
        return None
    if hops > 15:
        return None

    raw_payload = data[LOAM_HEADER : LOAM_HEADER + payload_len]
    expected_sig = loam_sign(data[: LOAM_HEADER + payload_len], payload_len, key)
    actual_sig = data[LOAM_HEADER + payload_len :]

    if (flags & F_SIGNED) and not hmac.compare_digest(expected_sig, actual_sig):
        return None

    return {
        'type': msg_type,
        'flags': flags,
        'src': src,
        'relay': relay,
        'seq': seq,
        'ts': ts,
        'ttl': ttl,
        'hops': hops,
        'payload_len': payload_len,
        'payload_bytes': raw_payload,
        'sig': actual_sig,
    }


def relay_frame(raw: bytes, relay_id: int, key: bytes = DEFAULT_LOAM_KEY) -> bytes | None:
    """Simulate relay node advancing TTL/hops and updating RELAY_ID.

    The origin HMAC signature is preserved as-is.
    """
    f = decode_frame(raw, key=key)
    if f is None or f['ttl'] <= 0 or f['hops'] >= 15:
        return None

    buf = bytearray(raw)
    buf[18] = f['ttl'] - 1
    buf[19] = f['hops'] + 1
    buf[8:12] = relay_id.to_bytes(4, 'big')
    return bytes(buf)


def build_warn_payload(advisory: dict[str, Any]) -> dict[str, Any]:
    """Build a compact LoAM WARN JSON payload from an advisory object."""
    doc: dict[str, Any] = {
        'v': 1,
        'id': advisory.get('id', 0),
        'rev': advisory.get('revision', advisory.get('rev', 1)),
        'src': advisory.get('source', 'MDRRMO'),
        'pr': advisory.get('priority', 'Warning'),
        'area': advisory.get('municipality', 'All'),
    }

    if advisory.get('cancelled') or advisory.get('status') == 'Cancelled':
        doc['cancelled'] = True

    pub_at = advisory.get('publish_date')
    if isinstance(pub_at, datetime):
        doc['iss'] = int(pub_at.timestamp())
    elif isinstance(pub_at, int):
        doc['iss'] = pub_at

    exp_at = advisory.get('expiration_date')
    if isinstance(exp_at, datetime):
        doc['exp'] = int(exp_at.timestamp())
    elif isinstance(exp_at, int):
        doc['exp'] = exp_at

    title = advisory.get('title', '')
    if title:
        doc['ttl'] = title[:48]

    desc = advisory.get('description', '')
    if desc:
        doc['txt'] = desc[:80]

    sig_type = advisory.get('sig_type', 'official')
    doc['sig_type'] = sig_type

    return doc


class WarningCache:
    """In-memory 6-slot warning cache emulating buoy firmware behavior.

    Enforces:
      - 6 maximum slots
      - Expiry pruning against current epoch
      - Revision superseding (higher revision overwrites lower; lower cannot overwrite higher)
      - Cancellation tombstones (cancelled warnings cannot be resurrected by older revision frames)
    """

    MAX_SLOTS = 6

    def __init__(self):
        self.slots: dict[int, dict[str, Any]] = {}
        self.tombstones: dict[int, int] = {}  # wid -> latest cancelled revision

    def put(self, payload: dict[str, Any], current_time: int = 0) -> bool:
        wid = payload.get('id', 0)
        if not wid:
            return False

        exp_at = payload.get('exp', 0)
        if current_time > 0 and exp_at > 0 and current_time > exp_at:
            return False  # Expired

        rev = payload.get('rev', 1)
        is_cancelled = payload.get('cancelled', False) or payload.get('status') == 'Cancelled'

        # Check tombstone
        if wid in self.tombstones and rev <= self.tombstones[wid]:
            return False  # Cannot resurrect cancelled warning with old/same rev

        if wid in self.slots:
            cached_rev = self.slots[wid].get('rev', 1)
            if rev < cached_rev:
                return False  # Dropped: older revision
            if is_cancelled:
                self.tombstones[wid] = rev
                del self.slots[wid]
                return True
            self.slots[wid] = payload
            return True

        if is_cancelled:
            self.tombstones[wid] = rev
            return True

        # Evict if full: remove expired first, then oldest
        if len(self.slots) >= self.MAX_SLOTS:
            expired_keys = [
                k for k, v in self.slots.items()
                if current_time > 0 and v.get('exp', 0) > 0 and current_time > v['exp']
            ]
            if expired_keys:
                del self.slots[expired_keys[0]]
            else:
                first_key = next(iter(self.slots))
                del self.slots[first_key]

        self.slots[wid] = payload
        return True

    def get_active(self, current_time: int = 0) -> list[dict[str, Any]]:
        active = []
        for wid, w in list(self.slots.items()):
            exp_at = w.get('exp', 0)
            if current_time > 0 and exp_at > 0 and current_time > exp_at:
                del self.slots[wid]
                continue
            active.append(w)
        return active


class RadioPriorityScheduler:
    """LoRa channel transmission scheduler enforcing absolute SOS priority.

    SOS traffic (0x01) preempts routine warning rebroadcasts.
    Warning rebroadcasts follow a bounded retry schedule with backoff.
    """

    def __init__(self):
        self.sos_queue: deque[bytes] = deque()
        self.warning_queue: list[dict[str, Any]] = []
        self.tx_history: list[dict[str, Any]] = []

    def enqueue_sos(self, frame: bytes) -> None:
        self.sos_queue.append(frame)

    def enqueue_warning(
        self,
        frame: bytes,
        warning_id: int,
        max_retries: int = 3,
        backoff_intervals: list[int] | None = None,
    ) -> None:
        if backoff_intervals is None:
            backoff_intervals = [30, 60, 120]
        self.warning_queue.append({
            'frame': frame,
            'warning_id': warning_id,
            'retry_count': 0,
            'max_retries': max_retries,
            'backoff_intervals': backoff_intervals,
            'next_attempt': 0,
            'state': 'pending',
        })

    def pop_next(self, current_time: int = 0) -> bytes | None:
        # SOS frames ALWAYS take absolute priority
        if self.sos_queue:
            frame = self.sos_queue.popleft()
            self.tx_history.append({'type': 'sos', 'time': current_time})
            return frame

        # Only process warnings if no SOS is pending
        for item in self.warning_queue:
            if item['state'] == 'pending' and current_time >= item['next_attempt']:
                item['retry_count'] += 1
                self.tx_history.append({
                    'type': 'warning',
                    'id': item['warning_id'],
                    'retry': item['retry_count'],
                    'time': current_time,
                })
                if item['retry_count'] >= item['max_retries']:
                    item['state'] = 'exhausted'
                else:
                    idx = min(item['retry_count'] - 1, len(item['backoff_intervals']) - 1)
                    item['next_attempt'] = current_time + item['backoff_intervals'][idx]
                return item['frame']

        return None
