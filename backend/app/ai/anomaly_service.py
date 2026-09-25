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

import json
import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app import geo
from app.ai.trip_profile import (
    ContactPoint,
    _build_profile,
    build_profiles_from_contacts,
    score_trip,
)


def _json_dumps(data: Any) -> str:
    def _default(obj: Any) -> str:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(data, default=_default)


def _determine_last_contact_at(
    contacts: list[ContactPoint],
    trip_state: dict[str, object] | None,
    as_of: datetime,
) -> datetime:
    if contacts:
        return contacts[-1].observed_at
    if trip_state:
        dep = trip_state.get('departure_at')
        if dep is not None:
            return dep if isinstance(dep, datetime) else datetime.fromisoformat(str(dep))
        rep = trip_state.get('reported_at')
        if rep is not None:
            return rep if isinstance(rep, datetime) else datetime.fromisoformat(str(rep))
    return as_of

# A 72-hour last-at-sea window keeps overnight silence observable while
# eventually ageing out trips from prior days.
OPEN_TRIP_FRESHNESS_WINDOW = timedelta(hours=72)


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
        SELECT bc.vessel_id, bc.trip_id, bc.buoy_id, bc.observed_at,
               COALESCE(bc.latitude, b.lat) AS latitude,
               COALESCE(bc.longitude, b.lon) AS longitude,
               bc.is_synthetic, bc.contact_via
        FROM buoy_contacts bc
        JOIN buoys b ON b.id = bc.buoy_id
        WHERE {source_clause}
        ORDER BY bc.vessel_id, bc.trip_id, bc.observed_at
        '''
    )
    return [dict(row) for row in rows if row.get('contact_via', 'buoy') != 'handset']


def _group_latest_trips(rows: list[dict[str, object]]) -> list[tuple[str, str, list[ContactPoint]]]:
    grouped: dict[tuple[str, str], list[ContactPoint]] = {}
    for row in rows:
        if row.get('latitude') is None or row.get('longitude') is None:
            continue
        if row.get('contact_via', 'buoy') == 'handset':
            continue
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
        SELECT trip_id, vessel_id, status, welfare_status, welfare_updated_at, departure_at,
               expected_return_at, expected_checkin_interval_minutes, reported_at, amendments
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

    Open trips remain eligible without contacts for a check-needed score; contacted
    trips must have an at-sea contact in the last 72 hours.
    """
    trip_states = trip_states or {}
    cutoff = as_of - OPEN_TRIP_FRESHNESS_WINDOW
    eligible: list[tuple[str, str, list[ContactPoint]]] = []
    seen_trips: set[str] = set()

    for vessel_id, trip_id, contacts in _group_latest_trips(rows):
        state = trip_states.get(trip_id)
        at_sea = [
            contact for contact in contacts
            if geo.point_in_water(contact.latitude, contact.longitude)
        ]
        if state is not None:
            status = str(state.get('status') or '')
            if status in {'completed', 'cancelled'}:
                continue
            if status in {'open', 'overdue', 'unresolved'} and not at_sea:
                eligible.append((vessel_id, trip_id, []))
                seen_trips.add(trip_id)
                continue
        if at_sea and max(contact.observed_at for contact in at_sea) >= cutoff:
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
    async with conn.transaction():
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
            profile = profiles.get(vessel_id)
            if profile is None:
                fleet_prof = profiles.get('fleet') or _build_profile('fleet', [], built_at=as_of, low_confidence=False)
                profile = fleet_prof.for_vessel(vessel_id, low_confidence=True)
            trip_state = trip_states.get(trip_id)
            if trip_state is not None:
                trip_state = dict(trip_state)
                trip_state['fleet_p90_trip_duration_minutes'] = profiles['fleet'].typical_trip_duration_minutes['p90']
            score = score_trip(
                profile,
                contacts,
                as_of=as_of,
                trip_id=trip_id,
                trip_state=trip_state,
            )
            score_rows.append(score.to_response())
            is_synthetic = trip_is_synthetic.get((vessel_id, trip_id), True)
            last_contact_at = _determine_last_contact_at(contacts, trip_state, as_of)
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
                _json_dumps(profile.to_json()),
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
                last_contact_at,
                score.score,
                score.status,
                _json_dumps([factor.__dict__ for factor in score.factors]),
                score.expected_contact.buoy_id,
                score.expected_contact.window_start,
                score.expected_contact.window_end,
                score.status in {'watch', 'overdue', 'alert', 'check_needed'},
                profile.low_confidence,
                datetime.now(UTC),
                is_synthetic,
            )
            if score.status != 'normal':
                await _upsert_case(
                    conn,
                    vessel_id,
                    trip_id,
                    score,
                    as_of=as_of,
                    last_contact_at=last_contact_at,
                    is_synthetic=is_synthetic,
                )
        return score_rows


async def _upsert_case(
    conn,
    vessel_id: str,
    trip_id: str,
    score,
    *,
    as_of: datetime,
    last_contact_at: datetime,
    is_synthetic: bool,
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
        _json_dumps([factor.__dict__ for factor in score.factors]),
        'synthetic' if is_synthetic else 'live',
        as_of,
        last_contact_at,
        is_synthetic,
    )
