"""What the gateway-key ingest routes let a key holder assert."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from probe_harness import FakeConn, install_pool, now_utc, require_status
from pydantic import ValidationError

from app.api.contacts import ContactEventIn
from app.main import app

GATEWAY_KEY = 'probe-gateway-key'

# Positional arg of calibration_status in the INSERT INTO current_observations.
CALIBRATION_ARG = 7


def _current_responder(kind, sql, args):
    if kind == 'fetchrow' and 'INSERT INTO current_observations' in sql:
        return {
            'id': 1, 'event_id': args[0], 'buoy_id': args[1], 'source': args[6],
            'calibration_status': args[CALIBRATION_ARG],
        }
    return None


@pytest.mark.finding('backend.current-ingest.unbound-calibration-claim')
def test_request_text_cannot_mark_a_current_reading_qualified(monkeypatch):
    conn = FakeConn(_current_responder)
    install_pool(monkeypatch, conn, 'app.api.current_events')
    monkeypatch.setenv('GATEWAY_API_KEY', GATEWAY_KEY)
    body = {
        'event_id': 'probe-current-1', 'buoy_id': 'BUOY-NO-INSTRUMENT',
        'observed_at': now_utc().isoformat(), 'observed_u_mps': 0.2, 'observed_v_mps': 0.1,
        'source': 'live', 'calibration_status': 'qualified',
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/v1/current-events', json=body, headers={'X-Api-Key': GATEWAY_KEY})
    if response.status_code in (400, 403, 422):
        return
    require_status(response, 200)
    stored = conn.calls_matching('INSERT INTO current_observations')[0][2][CALIBRATION_ARG]
    assert stored != 'qualified', (
        'calibration_status=qualified was stored from request text for a buoy with no bound '
        'instrument or calibration record; drift treats such rows as production-grade'
    )


def _contact(**overrides):
    body = {
        'event_id': 'probe-contact-1', 'vessel_id': 'V1', 'trip_id': 'T1', 'buoy_id': 'B1',
        'observed_at': now_utc(), 'latitude': 11.66, 'longitude': 122.44, 'source': 'live',
    }
    body.update(overrides)
    return body


@pytest.mark.finding('backend.contacts.future-timestamp-anomaly-suppression')
def test_contact_ingest_rejects_a_day_ahead_timestamp():
    """current_events.py already rejects >5 min of future skew; contacts does not."""
    with pytest.raises(ValidationError):
        ContactEventIn(**_contact(observed_at=now_utc() + timedelta(days=1)))


@pytest.mark.finding('backend.contacts.future-timestamp-anomaly-suppression:control')
def test_contact_control_present_timestamp_is_accepted():
    ContactEventIn(**_contact())
