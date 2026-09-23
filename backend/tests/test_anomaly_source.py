"""app.ai.anomaly_service: explicit source selection, freshness, and clock
injection (docs/38 Phase 1 item 5, Phase 2 items 1-4).

Production evaluation must never fall back to synthetic-only data (docs/38
acceptance boundary), and a trip that ended long before the evaluation
instant must not re-alert just because the clock advanced (the docs/31
design flaw). These pin, without a real database:

- the reader filters strictly to `bc.source = 'live'` unless DEMO_MODE is on;
- `eligible_latest_trips` excludes a trip whose last contact is older than
  OPEN_TRIP_FRESHNESS_WINDOW relative to the supplied `as_of`;
- `evaluate_and_persist` never truncates, always clears `is_active` before
  reinserting (so a trip that ages out simply stops being written, not
  deleted), and produces identical scores for the same fixture and `as_of`,
  changing only when `as_of` advances.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.ai import anomaly_service
from app.api.contacts import ContactEventIn


class _FakeConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.executed: list[tuple[str, tuple]] = []

    async def fetch(self, query: str, *args):
        self.executed.append((query, args))
        return self._rows

    async def execute(self, query: str, *args):
        self.executed.append((query, args))
        return 'OK'

    def transaction(self):
        class _NullContext:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        return _NullContext()


def test_demo_evaluation_disabled_by_default(monkeypatch):
    monkeypatch.delenv('DEMO_MODE', raising=False)
    assert anomaly_service.demo_evaluation_enabled() is False


def test_demo_evaluation_enabled_when_flag_set(monkeypatch):
    monkeypatch.setenv('DEMO_MODE', 'true')
    assert anomaly_service.demo_evaluation_enabled() is True


def test_production_reader_filters_to_live_only():
    conn = _FakeConnection([])
    asyncio.run(anomaly_service._load_trip_rows(conn, include_synthetic=False))
    query = conn.executed[0][0]
    assert "WHERE bc.source = 'live'" in query
    assert "IN ('live', 'synthetic')" not in query


def test_demo_reader_includes_both_sources():
    conn = _FakeConnection([])
    asyncio.run(anomaly_service._load_trip_rows(conn, include_synthetic=True))
    assert "WHERE bc.source IN ('live', 'synthetic')" in conn.executed[0][0]


def test_trip_is_synthetic_marks_a_trip_synthetic_if_any_contact_is():
    rows = [
        {'vessel_id': 'V1', 'trip_id': 'T1', 'is_synthetic': False},
        {'vessel_id': 'V1', 'trip_id': 'T1', 'is_synthetic': True},
        {'vessel_id': 'V2', 'trip_id': 'T2', 'is_synthetic': False},
    ]
    flags = anomaly_service._trip_is_synthetic(rows)
    assert flags[('V1', 'T1')] is True
    assert flags[('V2', 'T2')] is False


def _row(vessel_id: str, trip_id: str, buoy_id: str, observed_at: datetime) -> dict[str, object]:
    return {
        'vessel_id': vessel_id,
        'trip_id': trip_id,
        'buoy_id': buoy_id,
        'observed_at': observed_at,
        'latitude': 11.6892,
        'longitude': 122.3667,
        'is_synthetic': False,
    }


def test_eligible_latest_trips_excludes_a_trip_outside_the_freshness_window():
    as_of = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    rows = [
        _row('V-FRESH', 'trip-1', 'B01', as_of - timedelta(hours=2)),
        _row('V-STALE', 'trip-1', 'B01', as_of - timedelta(hours=20)),
    ]
    latest = anomaly_service.eligible_latest_trips(rows, as_of=as_of)
    eligible = {vessel_id for vessel_id, _trip_id, _contacts in latest}
    assert eligible == {'V-FRESH'}


def test_eligible_latest_trips_boundary_is_inclusive():
    as_of = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    cutoff = as_of - anomaly_service.OPEN_TRIP_FRESHNESS_WINDOW
    rows = [
        _row('V-AT-CUTOFF', 'trip-1', 'B01', cutoff),
        _row('V-JUST-PAST-CUTOFF', 'trip-1', 'B01', cutoff - timedelta(seconds=1)),
    ]
    latest = anomaly_service.eligible_latest_trips(rows, as_of=as_of)
    eligible = {vessel_id for vessel_id, _trip_id, _contacts in latest}
    assert eligible == {'V-AT-CUTOFF'}


def _fleet_rows() -> list[dict[str, object]]:
    """Two vessels with enough history to avoid the cold-start fleet
    fallback, plus one "current" trip each. V-FRESH's current trip has
    reached B01/B02 recently and is still waiting on B03 - the classic
    overdue setup from test_trip_profile.py's own fixtures. V-STALE's
    current trip is more than OPEN_TRIP_FRESHNESS_WINDOW old relative to
    every `as_of` these tests use, so it must never be scored.
    """
    rows: list[dict[str, object]] = []
    for vessel_id, current_day in (('V-FRESH', 10), ('V-STALE', 9)):
        for day in range(1, 5):
            start = datetime(2026, 8, day, 6, 0, tzinfo=UTC)
            for index, buoy_id in enumerate(('B01', 'B02', 'B03')):
                rows.append(_row(vessel_id, f'trip-{day}', buoy_id, start + timedelta(minutes=45 * index)))
        current_start = datetime(2026, 8, current_day, 6, 0, tzinfo=UTC)
        rows.append(_row(vessel_id, 'trip-current', 'B01', current_start))
        rows.append(_row(vessel_id, 'trip-current', 'B02', current_start + timedelta(minutes=45)))
    return rows


def test_evaluate_and_persist_excludes_the_stale_vessel():
    as_of = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    conn = _FakeConnection(_fleet_rows())
    scores = asyncio.run(anomaly_service.evaluate_and_persist(conn, as_of=as_of, include_synthetic=False))

    assert {row['vessel_id'] for row in scores} == {'V-FRESH'}
    insert_calls = [q for q, _args in conn.executed if 'INSERT INTO vessel_anomaly_scores' in q]
    assert len(insert_calls) == 1


def test_evaluate_and_persist_never_truncates():
    conn = _FakeConnection(_fleet_rows())
    as_of = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    asyncio.run(anomaly_service.evaluate_and_persist(conn, as_of=as_of, include_synthetic=False))
    assert not any('TRUNCATE' in query for query, _args in conn.executed)


def test_evaluate_and_persist_clears_is_active_before_reinserting():
    conn = _FakeConnection(_fleet_rows())
    as_of = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    asyncio.run(anomaly_service.evaluate_and_persist(conn, as_of=as_of, include_synthetic=False))

    def _is_clear(query: str) -> bool:
        return 'UPDATE vessel_anomaly_scores' in query and 'is_active = FALSE' in query

    clear_index = next(i for i, (q, _args) in enumerate(conn.executed) if _is_clear(q))
    insert_index = next(
        i for i, (q, _args) in enumerate(conn.executed) if 'INSERT INTO vessel_anomaly_scores' in q
    )
    assert clear_index < insert_index


async def _evaluate(rows: list[dict[str, object]], *, as_of: datetime) -> list[dict[str, object]]:
    return await anomaly_service.evaluate_and_persist(_FakeConnection(rows), as_of=as_of, include_synthetic=False)


def test_evaluate_and_persist_is_deterministic_for_the_same_clock():
    rows = _fleet_rows()
    as_of = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    scores_first = asyncio.run(_evaluate(rows, as_of=as_of))
    scores_second = asyncio.run(_evaluate(rows, as_of=as_of))
    assert scores_first == scores_second


def test_evaluate_and_persist_score_changes_only_when_the_clock_advances():
    rows = _fleet_rows()
    early = asyncio.run(_evaluate(rows, as_of=datetime(2026, 8, 10, 8, 0, tzinfo=UTC)))
    late = asyncio.run(_evaluate(rows, as_of=datetime(2026, 8, 10, 14, 0, tzinfo=UTC)))
    early_score = next(row['score'] for row in early if row['vessel_id'] == 'V-FRESH')
    late_score = next(row['score'] for row in late if row['vessel_id'] == 'V-FRESH')
    # Still overdue further past the expected-contact window - later must not
    # score lower, and here it should be strictly higher.
    assert late_score > early_score


def test_zero_contact_trip_evaluates_with_fleet_profile_and_persists():
    """SEC-02: Zero-contact trip for a fresh vessel falls back to fleet profile and uses departure_at/reported_at."""
    as_of = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    departure = as_of - timedelta(hours=3)

    class _ZeroContactConn(_FakeConnection):
        async def fetch(self, query: str, *args):
            self.executed.append((query, args))
            if 'FROM buoy_contacts' in query:
                return []
            if 'FROM vessel_trips' in query:
                return [{
                    'trip_id': 'T-ZERO',
                    'vessel_id': 'V-FRESH',
                    'status': 'open',
                    'welfare_status': 'unknown',
                    'departure_at': departure,
                    'expected_return_at': None,
                    'expected_checkin_interval_minutes': None,
                    'reported_at': None,
                    'amendments': [],
                }]
            return []

    conn = _ZeroContactConn([])
    scores = asyncio.run(anomaly_service.evaluate_and_persist(conn, as_of=as_of, include_synthetic=False))
    assert len(scores) == 1
    assert scores[0]['vessel_id'] == 'V-FRESH'

    score_insert = next(args for q, args in conn.executed if 'INSERT INTO vessel_anomaly_scores' in q)
    assert score_insert[3] == departure


def test_contact_without_coordinates_skipped_without_crashing():
    """SEC-03: Contacts with missing coordinates are safely skipped without aborting evaluation."""
    as_of = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    rows = [
        _row('V-GOOD', 'trip-good', 'B01', as_of - timedelta(hours=1)),
        {
            'vessel_id': 'V-BAD',
            'trip_id': 'trip-bad',
            'buoy_id': 'B01',
            'observed_at': as_of - timedelta(hours=1),
            'latitude': None,
            'longitude': None,
            'is_synthetic': False,
        },
    ]
    latest = anomaly_service.eligible_latest_trips(rows, as_of=as_of)
    vessels = {v for v, _, _ in latest}
    assert 'V-GOOD' in vessels
    assert 'V-BAD' not in vessels


def test_contact_event_in_rejects_future_clock_skew():
    """SEC-04: ContactEventIn rejects observed_at more than 5 minutes in the future."""
    now = datetime.now(UTC)
    valid = ContactEventIn(
        event_id='e1',
        vessel_id='V1',
        trip_id='T1',
        buoy_id='B1',
        observed_at=now,
        source='live',
    )
    assert valid.observed_at == now

    with pytest.raises(ValidationError):
        ContactEventIn(
            event_id='e2',
            vessel_id='V1',
            trip_id='T1',
            buoy_id='B1',
            observed_at=now + timedelta(minutes=6),
            source='live',
        )
