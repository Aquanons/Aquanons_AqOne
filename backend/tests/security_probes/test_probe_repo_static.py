"""Static probes over tracked firmware and release artifacts.

Evidence level is STATIC: they prove what the source or artifact contains,
not what is flashed or installed in the field. Failure messages name keys
and lengths only - never a secret value.
"""

from __future__ import annotations

import re

import pytest
from probe_harness import REPO_ROOT

LOAM_BUOY = REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneLoam.h'


def _code(path) -> str:
    """Source with // and /* */ comments removed, so prose cannot match."""
    text = path.read_text('utf-8')
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


@pytest.mark.finding('firmware.loam.shared-default-key')
def test_loam_signature_key_is_selected_per_source_id():
    """One global key means any holder can sign as any SRC_ID."""
    hmac_calls = re.findall(r'mbedtls_md_hmac_starts\([^;]*;', _code(LOAM_BUOY))
    assert hmac_calls and all('LOAM_KEY' not in call for call in hmac_calls), (
        f'every HMAC in AqOneLoam.h is keyed with the single global LOAM_KEY ({len(hmac_calls)} call sites)'
    )
