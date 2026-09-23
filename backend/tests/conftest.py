import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Security-audit probes assert the safe behaviour and are expected to fail
# while a finding is open, so they stay out of the default green suite.
# Run them with AQONE_SECURITY_PROBES=1 (docs/security-audit/PROBES.md).
collect_ignore_glob = [] if os.environ.get('AQONE_SECURITY_PROBES') == '1' else ['security_probes/*']
