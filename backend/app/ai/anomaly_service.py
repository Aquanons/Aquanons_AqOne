"""Trip-anomaly evaluation as a small, explicitly-clocked service.

Extracted from app/api/anomaly.py (docs/38 Phase 2) so evaluation has one
injected "now" rather than reading it from the latest row in the database -
that pinned "now" to whatever a demo write or historical dataset happened to
contain, which is how docs/30 and docs/31 each found a different way for a
stale or demo-influenced timestamp to manufacture a false overdue score.

- Live callers (POST /evaluate, the scheduled job in run_anomaly_evaluation.py)
  pass the server clock.
- Fixture/replay callers pass an explicit clock, so the same fixture scores
  identically for the same evaluation time and only moves when the clock
  advances.

`evaluate_and_persist` writes; nothing here is safe to call from a GET route
a dashboard polls (docs/38 acceptance boundary: "the active read endpoint is
read-only").
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from app.ai.trip_profile import ContactPoint, build_profiles_from_contacts, score_trip

# Decided 2026-08-29 (docs/38 Phase 2 stop-and-ask condition, project lead) -
# see docs/08_DEMO_AND_STATUS.md for the recorded rationale. How long after a
# vessel's last buoy contact its most recent trip still counts as "possibly
# still open," rather than excluded as stale/completed. Too short would
# exclude a vessel that is *already* hours overdue - the exact case this
# feature exists to catch. Too long lets a trip from days ago re-alert just
# because the wall clock advanced, the design flaw
# docs/31_DEMO_VERIFICATION_01.md found in the previous dataset-max-timestamp
# approach. The synthetic generator models full trips (departure to return)
# of roughly 6-13 hours, so 12 hours covers a complete trip cycle while still
# excluding anything from a prior day.
OPEN_TRIP_FRESHNESS_WINDOW = timedelta(hours=12)


def demo_evaluation_enabled() -> bool:
    """Whether this deployment may fold labelled synthetic contacts into
    evaluation, alongside live ones.

    Mirrors main.py's own DEMO_MODE gate for mounting /api/demo - the same
    flag that already means "this deployment is running the presenter demo,
    not serving real responders." Production candidates must never be
    derived only from synthetic data (docs/38 acceptance boundary), so a
    deployment that never sets DEMO_MODE only ever evaluates live contacts,
    even if that means an empty queue until a gateway is connected.
    """
    return os.environ.get('DEMO_MODE', '').strip().lower() in {'1', 'true', 'yes', 'on'}


async def _load_trip_rows(conn, *, include_synthetic: bool) -> list[dict[str, object]]:
    source_clause = "bc.source IN ('live', 'synthetic')" if include_synthetic else "bc.source = 'live'"
    rows = await conn.fetch(
        f'''
        SELECT bc.vessel_id, bc.trip_id, bc.buoy_id, bc.observed_at, bc.latitude,
               bc.longitude, bc.is_synthetic
        FROM buoy_contacts bc
        JOIN buoys b ON b.id = bc.buoy_id
        WHERE {source_clause}
        ORDER BY bc.vessel_id, bc.trip_id, bc.observed_at
        '''
    )
    return [dict(row) for row in rows]


def _group_latest_trips(rows: list[dict[str, object]]) -> list[tuple[str, str, list[ContactPoint]]]:
    grouped: dict[tuple[str, str], list[ContactPoint]] = {}
    for row in rows:
        key = (str(row['vessel_id']), str(row['trip_id']))
        grouped.setdefault(key, []).append(
            ContactPoint(
                buoy_id=str(row['buoy_id']),
                observed_at=row['observed_at'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
            )
        )
    latest: dict[str, tuple[str, list[ContactPoint]]] = {}
    for (vessel_id, trip_id), contacts in grouped.items():
        contacts.sort(key=lambda item: item.observed_at)
        if vessel_id not in latest or contacts[-1].observed_at > latest[vessel_id][1][-1].observed_at:
            latest[vessel_id] = (trip_id, contacts)
    return [(vessel_id, trip_id, contacts) for vessel_id, (trip_id, contacts) in latest.items()]


def _trip_is_synthetic(rows: list[dict[str, object]]) -> dict[tuple[str, str], bool]:
    """Per (vessel_id, trip_id), whether any contributing contact is synthetic.

    Only reachable with a synthetic contact in the mix at all when
    include_synthetic=True, since a plain live evaluation never loads one.
    Kept per-trip (not hardcoded) so a mixed trip is honestly labelled
    rather than silently marked live.
    """
    flags: dict[tuple[str, str], bool] = {}
    for row in rows:
        key = (str(row['vessel_id']), str(row['trip_id']))
        flags[key] = flags.get(key, False) or bool(row['is_synthetic'])
    return flags


async def _load_trip_states(conn) -> dict[str, dict[str, object]]:
    rows = await conn.fetch(
        '''
        SELECT trip_id, vessel_id, status, welfare_status, departure_at,
               expected_return_at, expected_checkin_interval_minutes, amendments
        FROM vessel_trips
        '''
    )
    return {str(r['trip_id']): dict(r) for r in rows}


def eligible_latest_trips(
    rows: list[dict[str, object]],
    *,
    as_of: datetime,
    trip_states: dict[str, dict[str, object]] | None = None,
) -> list[tuple[str, str, list[ContactPoint]]]:
    """The latest trip per vessel.

    Task 3.5 & Scenario C5: Determine eligibility from open/unresolved trip state rather
    than an arbitrary 12-hour latest-contact cutoff. An open/unresolved trip
    persists beyond 12 hours without silent expiration, while completed or
    cancelled trips are excluded. Open trips with zero contacts (e.g. during an outage)
    remain eligible rather than being silently ignored. Unrecorded legacy/synthetic
    trips fall back to OPEN_TRIP_FRESHNESS_WINDOW.
    """
    trip_states = trip_states or {}
    cutoff = as_of - OPEN_TRIP_FRESHNESS_WINDOW
    eligible: list[tuple[str, str, list[ContactPoint]]] = []
    seen_trips: set[str] = set()

    for vessel_id, trip_id, contacts in _group_latest_trips(rows):
        state = trip_states.get(trip_id)
        if state is not None:
            status = str(state.get('status') or '')
            if status in {'completed', 'cancelled'}:
                continue
            if status in {'open', 'overdue', 'unresolved'}:
                eligible.append((vessel_id, trip_id, contacts))
                seen_trips.add(trip_id)
                continue
        if contacts[-1].observed_at >= cutoff:
            eligible.append((vessel_id, trip_id, contacts))
            seen_trips.add(trip_id)

    # Scenario C5: include open/overdue trips that have zero buoy contacts
    for trip_id, state in trip_states.items():
        if trip_id in seen_trips:
            continue
        status = str(state.get('status') or '')
        if status in {'open', 'overdue', 'unresolved'}:
            vessel_id = str(state.get('vessel_id') or 'unknown')
            eligible.append((vessel_id, trip_id, []))
            seen_trips.add(trip_id)

    return eligible


async def evaluate_and_persist(conn, *, as_of: datetime, include_synthetic: bool) -> list[dict[str, object]]:
    """Score eligible open trips as of `as_of` and persist the result.

    Non-destructive: no TRUNCATE. Rows outside this run's scope (and, within
    scope, trips that fell out of eligibility since the last run) are simply
    left as-is except for their is_active flag, which is cleared first and
    then re-set only for trips still eligible this run - so a vessel that
    ages out of the freshness window or completes a newer trip drops out of
    `is_active = TRUE` without any row being deleted or truncated.
    """
    rows = await _load_trip_rows(conn, include_synthetic=include_synthetic)
    trip_states = await _load_trip_states(conn)
    eligible = eligible_latest_trips(rows, as_of=as_of, trip_states=trip_states)
    candidate_trip_ids = {trip_id for _, trip_id, _ in eligible}
    profiles = build_profiles_from_contacts(
        rows, built_at=as_of, as_of=as_of, exclude_trip_ids=candidate_trip_ids, trip_states=trip_states,
    )
    trip_is_synthetic = _trip_is_synthetic(rows)

    scope = [True, False] if include_synthetic else [False]
    await conn.execute(
        'UPDATE vessel_anomaly_scores SET is_active = FALSE WHERE is_synthetic = ANY($1::boolean[])',
        scope,
    )

    score_rows: list[dict[str, object]] = []
    for vessel_id, trip_id, contacts in eligible:
        profile = profiles[vessel_id]
        trip_state = trip_states.get(trip_id)
        score = score_trip(
            profile,
            contacts,
            as_of=as_of,
            trip_id=trip_id,
            trip_state=trip_state,
        )
        score_rows.append(score.to_response())
        is_synthetic = trip_is_synthetic.get((vessel_id, trip_id), True)
        await conn.execute(
            '''
            INSERT INTO vessel_profiles (
              vessel_id, profile_json, trip_count, low_confidence, rebuilt_at, is_synthetic
            ) VALUES ($1, $2::jsonb, $3, $4, $5, $6)
            ON CONFLICT (vessel_id) DO UPDATE SET
              profile_json = EXCLUDED.profile_json,
              trip_count = EXCLUDED.trip_count,
              low_confidence = EXCLUDED.low_confidence,
              rebuilt_at = EXCLUDED.rebuilt_at,
              is_synthetic = EXCLUDED.is_synthetic
            ''',
            vessel_id,
            profile.to_json(),
            profile.trip_count,
            profile.low_confidence,
            datetime.now(UTC),
            is_synthetic,
        )
        await conn.execute(
            '''
            INSERT INTO vessel_anomaly_scores (
              vessel_id, trip_id, observed_at, last_contact_at, score, status,
              factors, expected_next_buoy_id, expected_window_start,
              expected_window_end, is_active, low_confidence, updated_at,
              is_synthetic
            ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (vessel_id, trip_id) DO UPDATE SET
              observed_at = EXCLUDED.observed_at,
              last_contact_at = EXCLUDED.last_contact_at,
              score = EXCLUDED.score,
              status = EXCLUDED.status,
              factors = EXCLUDED.factors,
              expected_next_buoy_id = EXCLUDED.expected_next_buoy_id,
              expected_window_start = EXCLUDED.expected_window_start,
              expected_window_end = EXCLUDED.expected_window_end,
              is_active = EXCLUDED.is_active,
              low_confidence = EXCLUDED.low_confidence,
              updated_at = EXCLUDED.updated_at,
              is_synthetic = EXCLUDED.is_synthetic
            ''',
            vessel_id,
            trip_id,
            as_of,
            contacts[-1].observed_at,
            score.score,
            score.status,
            [factor.__dict__ for factor in score.factors],
            score.expected_contact.buoy_id,
            score.expected_contact.window_start,
            score.expected_contact.window_end,
            score.status in {'watch', 'overdue', 'alert'},
            profile.low_confidence,
            datetime.now(UTC),
            is_synthetic,
        )
        if score.status != 'normal':
            await _upsert_case(conn, vessel_id, trip_id, score, contacts, as_of=as_of, is_synthetic=is_synthetic)
    return score_rows


async def _upsert_case(
    conn, vessel_id: str, trip_id: str, score, contacts, *, as_of: datetime, is_synthetic: bool
) -> None:
    """Create or refresh the persistent review case for a non-normal score
    (docs/38 Phase 3). Only the score-derived snapshot columns are written
    here - acknowledged/dismissed/escalated/resolved are never touched by
    evaluation, only by app/api/anomaly_cases.py, so a later refresh cannot
    erase a responder's decision.

    Per the acceptance boundary ("Low-confidence results enter a
    verification queue. High-confidence results request responder
    attention."), case_type follows the model's own confidence in the
    vessel's profile, not the score's severity tier.
    """
    case_type = 'verification' if score.low_confidence else 'responder_attention'
    await conn.execute(
        '''
        INSERT INTO anomaly_cases (
          vessel_id, trip_id, case_type, score, status, reasons, source,
          score_evaluated_at, last_contact_at, is_synthetic, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, NOW())
        ON CONFLICT (vessel_id, trip_id) DO UPDATE SET
          case_type = EXCLUDED.case_type,
          score = EXCLUDED.score,
          status = EXCLUDED.status,
          reasons = EXCLUDED.reasons,
          source = EXCLUDED.source,
          score_evaluated_at = EXCLUDED.score_evaluated_at,
          last_contact_at = EXCLUDED.last_contact_at,
          is_synthetic = EXCLUDED.is_synthetic,
          updated_at = NOW()
        ''',
        vessel_id,
        trip_id,
        case_type,
        score.score,
        score.status,
        [factor.__dict__ for factor in score.factors],
        'synthetic' if is_synthetic else 'live',
        as_of,
        contacts[-1].observed_at,
        is_synthetic,
    )
