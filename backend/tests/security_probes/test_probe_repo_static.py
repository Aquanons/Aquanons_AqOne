"""Static probes over tracked firmware and release artifacts.

Evidence level is STATIC: they prove what the source or artifact contains,
not what is flashed or installed in the field. Failure messages name keys
and lengths only - never a secret value.
"""

from __future__ import annotations

import re

import pytest
from probe_harness import REPO_ROOT

SHORE = REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneShore.ino'
BUOY = REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneBuoy.ino'
LOAM_BUOY = REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneLoam.h'
LOAM_SHORE = REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneLoam.h'
GRADLE = REPO_ROOT / 'mobile' / 'android' / 'app' / 'build.gradle.kts'
TRACKED_APK = REPO_ROOT / 'mobile' / 'releases' / 'aqone-release.apk'

PLACEHOLDER = re.compile(r'^$|your|change|example|placeholder|xxx|<.*>', re.I)


def _code(path) -> str:
    """Source with // and /* */ comments removed, so prose cannot match."""
    text = path.read_text('utf-8')
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def _string_constant(path, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"', _code(path))
    return match.group(1) if match else None


@pytest.mark.finding('firmware.shore.committed-uplink-credential')
@pytest.mark.parametrize('name', ['UPLINK_SSID', 'UPLINK_PASS', 'GATEWAY_API_KEY'])
def test_shore_sketch_holds_no_concrete_credential(name):
    value = _string_constant(SHORE, name)
    if value is None:
        return  # moved out of the sketch (build flag / secrets header)
    # A plain bool, so pytest's assertion rewriting has no value to print.
    is_placeholder = PLACEHOLDER.search(value) is not None
    length = len(value)
    del value
    assert is_placeholder, (
        f'{name} in the tracked shore sketch is a concrete {length}-character value, not a placeholder'
    )


@pytest.mark.finding('firmware.loam.shared-default-key')
def test_loam_key_is_not_the_repository_default():
    value = _string_constant(LOAM_BUOY, 'LOAM_KEY')
    assert value != 'aqone-dev-key-change-me', 'LOAM_KEY is still the published default in AqOneLoam.h'


@pytest.mark.finding('firmware.loam.shared-default-key')
def test_loam_signature_key_is_selected_per_source_id():
    """One global key means any holder can sign as any SRC_ID."""
    hmac_calls = re.findall(r'mbedtls_md_hmac_starts\([^;]*;', _code(LOAM_BUOY))
    assert hmac_calls and all('LOAM_KEY' not in call for call in hmac_calls), (
        f'every HMAC in AqOneLoam.h is keyed with the single global LOAM_KEY ({len(hmac_calls)} call sites)'
    )


@pytest.mark.finding('firmware.loam.shared-default-key:control')
def test_loam_control_headers_are_byte_identical():
    assert LOAM_BUOY.read_bytes() == LOAM_SHORE.read_bytes()


@pytest.mark.finding('firmware.shore.tls-peer-verification-disabled')
def test_shore_verifies_the_backend_certificate():
    code = _code(SHORE)
    assert 'setInsecure()' not in code, 'the shore sketch calls WiFiClientSecure::setInsecure()'


def _case_block(code: str, label: str) -> str:
    start = code.index(f'case {label}:')
    following = re.search(r'\bcase T_[A-Z_]+\s*:', code[start + 1:])
    return code[start: start + 1 + following.start()] if following else code[start:]


@pytest.mark.finding('firmware.warning.missing-revision-tombstone')
def test_buoy_warning_cache_orders_updates_by_revision():
    block = _case_block(_code(BUOY), 'T_WARN')
    assert re.search(r'\b(rev|revision|version|ver)\b', block, re.I), (
        'the buoy T_WARN handler overwrites a cached warning by id with no revision comparison, '
        'so a replayed older frame replaces a newer one'
    )


@pytest.mark.finding('firmware.buoy.chat-starves-sos-tx-ring')
def test_tx_ring_keeps_capacity_for_distress_frames():
    loam = _code(LOAM_BUOY)
    enqueue = loam[loam.index('bool txEnqueue('):]
    enqueue = enqueue[: enqueue.index('\n}') + 2]
    guarded = re.search(r'reserve|priority|T_SOS|T_CHAT|chatInFlight|CHAT_MAX', enqueue, re.I)
    assert guarded, (
        'txEnqueue takes the first free slot for any frame type; chat and SOS share the ring with '
        'no reserved capacity (runtime starvation still needs a bench test)'
    )


@pytest.mark.finding('mobile.release.debug-signing-fallback')
def test_release_build_does_not_fall_back_to_debug_signing():
    gradle = GRADLE.read_text('utf-8')
    fallback = re.search(r'signingConfigs\.getByName\("debug"\)', gradle)
    assert not fallback, 'the release buildType falls back to the debug signing config when key.properties is absent'


@pytest.mark.finding('mobile.release.debug-signing-fallback')
def test_tracked_release_apk_is_not_debug_signed():
    """Heuristic: the Android debug certificate's subject is 'CN=Android Debug'.
    Confirm with apksigner verify --print-certs if this fails."""
    if not TRACKED_APK.exists():
        return
    assert b'Android Debug' not in TRACKED_APK.read_bytes(), (
        'mobile/releases/aqone-release.apk carries an "Android Debug" signing certificate'
    )
