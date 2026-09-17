"""Dataset manifest validation and event-level partitioning rules (Phase 4 Tasks 4.3, C3, C4).

Enforces:
1. No placeholder or invalid evidence hashes.
2. Disjoint event-level splits: no event/storm/track may span multiple partitions.
3. Target set diversity: held-out splits must contain both event and non-event classes.
4. Non-empty records and explicit provenance class.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SHA256_HEX_RE = re.compile(r'^[0-9a-fA-F]{64}$')
PLACEHOLDER_HASHES = {
    '0' * 64,
    'f' * 64,
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',  # empty string hash
}


class ManifestValidationError(ValueError):
    """Raised when a dataset manifest fails verification or has invalid provenance."""
    pass


@dataclass(frozen=True)
class ManifestSummary:
    manifest_version: str
    custodian: str
    record_count: int
    splits: dict[str, int]
    event_count: int
    outcomes: dict[str, int]


def validate_manifest(data: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Validate an event-level dataset manifest per docs/52 specification."""
    if isinstance(data, (str, Path)):
        path = Path(data)
        if not path.exists():
            raise ManifestValidationError(f"Manifest file not found: {path}")
        with open(path, encoding='utf-8') as f:
            manifest = json.load(f)
    elif isinstance(data, dict):
        manifest = data
    else:
        raise ManifestValidationError("Manifest must be a dictionary, file path, or JSON string")

    # Required top-level fields
    for field in ('manifest_version', 'created_at', 'custodian', 'domain', 'records'):
        if field not in manifest:
            raise ManifestValidationError(f"Missing required manifest field: '{field}'")

    records = manifest['records']
    if not isinstance(records, list) or len(records) == 0:
        raise ManifestValidationError("records cannot be empty; requires verifiable dataset")

    event_splits: dict[str, set[str]] = {}
    test_outcomes: set[str] = set()

    for idx, rec in enumerate(records):
        rec_id = rec.get('record_id') or f"index_{idx}"
        for req in ('split', 'record_type', 'outcome', 'raw_evidence_sha256'):
            if req not in rec:
                raise ManifestValidationError(f"Record '{rec_id}' missing required field: '{req}'")

        # Check raw_evidence_sha256
        sha = str(rec['raw_evidence_sha256']).strip().lower()
        if not SHA256_HEX_RE.match(sha) or sha in PLACEHOLDER_HASHES:
            raise ManifestValidationError(
                f"Record '{rec_id}' has placeholder or invalid SHA-256 evidence hash: '{sha}'"
            )

        split = str(rec['split']).strip().lower()
        event_id = rec.get('event_id') or rec.get('trip_id') or rec.get('storm_id')
        if event_id:
            event_splits.setdefault(str(event_id), set()).add(split)

        if 'test' in split or 'held_out' in split:
            test_outcomes.add(str(rec['outcome']).strip().lower())

    # Scenario C3: verify event disjointness across splits
    for ev_id, splits in event_splits.items():
        if len(splits) > 1:
            raise ManifestValidationError(
                f"event_id '{ev_id}' spans multiple splits ({sorted(splits)}); "
                "event-level partitioning violation (leakage between development and evaluation)"
            )

    # Scenario C4: verify held-out test split diversity
    if test_outcomes and len(test_outcomes) < 2:
        raise ManifestValidationError(
            "insufficient evidence: test split contains only a single outcome class "
            f"({sorted(test_outcomes)}); evaluation requires balanced/distinguishable targets"
        )

    return manifest
