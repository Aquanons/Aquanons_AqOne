"""Offline checks that the firmware's security guards do what they claim.

The shore CA bundle is checked against a recorded copy of the backend's public
certificate chain (`fixtures/tls/aqone-backend-chain.pem`), walked the way
mbedTLS on the ESP32 walks it: a trusted root may sign any certificate in the
presented chain, otherwise the next presented certificate must.
Refresh the fixture when Render changes certificate authority:

    openssl s_client -connect aqone-backend.onrender.com:443 \
        -servername aqone-backend.onrender.com -showcerts </dev/null \
        | sed -n '/BEGIN/,/END/p' > fixtures/tls/aqone-backend-chain.pem

Only signatures and names are checked, never validity dates, so the recorded
leaf expiring does not fail this test.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from cryptography import x509

from tests.security_probes.probe_harness import REPO_ROOT

SHORE_SKETCH = REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneShore.ino'
BACKEND_CHAIN = REPO_ROOT / 'fixtures' / 'tls' / 'aqone-backend-chain.pem'
LOAM_HEADERS = [
    REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneLoam.h',
    REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneLoam.h',
]
SECRETS_EXAMPLES = [
    REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneSecrets.h.example',
    REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneSecrets.h.example',
]
OLD_DEFAULT_LOAM_KEY = 'aqone-dev-key-change-me'
MIN_LOAM_KEY_LENGTH = 16


def _shore_ca_bundle() -> list[x509.Certificate]:
    code = SHORE_SKETCH.read_text('utf-8')
    start = code.index('BACKEND_CA_CERTS[]')
    literal = code[start: code.index(';', start)]
    pem = ''.join(re.findall(r'"([^"]*)"', literal)).replace('\\n', '\n')
    return x509.load_pem_x509_certificates(pem.encode())


def _signed_by(child: x509.Certificate, parent: x509.Certificate) -> bool:
    if child.issuer != parent.subject:
        return False
    try:
        child.verify_directly_issued_by(parent)
    except (ValueError, TypeError, x509.InvalidSignature):
        return False
    return True


def _chain_is_trusted(chain: list[x509.Certificate], roots: list[x509.Certificate]) -> bool:
    for index, cert in enumerate(chain):
        if any(_signed_by(cert, root) for root in roots):
            return True
        following = chain[index + 1] if index + 1 < len(chain) else None
        if following is None or not _signed_by(cert, following):
            return False
    return False


def test_shore_ca_bundle_trusts_the_recorded_backend_chain():
    chain = x509.load_pem_x509_certificates(BACKEND_CHAIN.read_bytes())
    roots = _shore_ca_bundle()
    assert _chain_is_trusted(chain, roots), (
        'no root in BACKEND_CA_CERTS signs any certificate of the recorded backend chain '
        f'(chain issuers: {[c.issuer.rfc4514_string() for c in chain]}; '
        f'bundle subjects: {[r.subject.rfc4514_string() for r in roots]})'
    )


def test_shore_ca_bundle_roots_are_unexpired():
    now = datetime.now(UTC)
    expired = [r.subject.rfc4514_string() for r in _shore_ca_bundle() if r.not_valid_after_utc <= now]
    assert not expired, f'expired roots in BACKEND_CA_CERTS: {expired}'


def _loam_key_example(path) -> str:
    match = re.search(r'constexpr\s+char\s+LOAM_KEY\s*\[\s*\]\s*=\s*"([^"]*)"', path.read_text('utf-8'))
    assert match, f'{path.name} must declare LOAM_KEY as `static constexpr char LOAM_KEY[] = "...";`'
    return match.group(1)


def _static_asserts(path) -> list[str]:
    return re.findall(r'static_assert\s*\((.*?)\)\s*;', path.read_text('utf-8'), re.S)


def _function_body(code: str, signature: str) -> str:
    opening = code.index('{', code.index(signature))
    depth = 0
    for position in range(opening, len(code)):
        if code[position] == '{':
            depth += 1
        elif code[position] == '}':
            depth -= 1
            if depth == 0:
                return code[opening:position + 1]
    raise AssertionError(f'unclosed function body for {signature}')


def test_loam_key_guard_rejects_every_committed_placeholder_at_compile_time():
    rejected = {OLD_DEFAULT_LOAM_KEY} | {_loam_key_example(p) for p in SECRETS_EXAMPLES}
    for header in LOAM_HEADERS:
        asserts = [a for a in _static_asserts(header) if 'LOAM_KEY' in a]
        compared = {lit for a in asserts for lit in re.findall(r'LOAM_KEY\s*,\s*"([^"]*)"', a)}
        missing = sorted(rejected - compared)
        assert not missing, f'{header.parent.name}/AqOneLoam.h has no static_assert rejecting LOAM_KEY {missing}'
        lengths = [int(n) for a in asserts for n in re.findall(r'>=\s*(\d+)', a)]
        assert lengths and max(lengths) >= MIN_LOAM_KEY_LENGTH, (
            f'{header.parent.name}/AqOneLoam.h has no static_assert that LOAM_KEY is at least '
            f'{MIN_LOAM_KEY_LENGTH} characters'
        )


def test_tx_ring_chat_reserve_reads_the_type_byte_the_encoder_writes():
    code = LOAM_HEADERS[0].read_text('utf-8')
    type_offset = re.search(r'buf\[(\d+)\]\s*=\s*type;', code)
    assert type_offset, 'loamEncode no longer writes the frame type at a fixed buf[] offset'
    enqueue = code[code.index('bool txEnqueue('):]
    enqueue = enqueue[: enqueue.index('\n}')]
    assert re.search(rf'bytes\[{type_offset.group(1)}\]\s*==\s*T_CHAT', enqueue), (
        f'txEnqueue must decide the chat reserve from bytes[{type_offset.group(1)}] (TYPE); '
        'any other offset never matches T_CHAT, so chat can fill the ring again'
    )


def test_shore_chat_calls_send_gateway_key():
    code = SHORE_SKETCH.read_text('utf-8')
    for signature in ('bool postChat(', 'void pollChat('):
        body = _function_body(code, signature)
        assert 'https.addHeader("X-Api-Key", GATEWAY_API_KEY);' in body, (
            f'{signature} must authenticate its /api/mesh/chat request with GATEWAY_API_KEY'
        )
