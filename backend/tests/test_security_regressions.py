"""Promoted security-audit regression tests.

Guards verified security fixes in the default test suite (runs on every PR and CI
without requiring a live Postgres instance). Probes that require Postgres or verify
deferred roadmap items remain behind AQONE_SECURITY_PROBES in tests/security_probes/.
"""

from __future__ import annotations

import asyncio
import re
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ai.anomaly_service import eligible_latest_trips, evaluate_and_persist
from app.api.contacts import ContactEventIn
from app.demo.weather import coordinates
from app.main import app
from tests.security_probes.probe_harness import (
    REPO_ROOT,
    FakeConn,
    ProbeBroken,
    install_pool,
    now_utc,
    operator_headers,
    require_status,
)

# ---------------------------------------------------------------------------
# Section 1: Anomaly Service & Fleet Evaluation (SEC-02, SEC-03)
# ---------------------------------------------------------------------------


def _contact_row(vessel_id, trip_id, observed_at, lat=11.66, lon=122.44):
    return {
        'vessel_id': vessel_id,
        'trip_id': trip_id,
        'buoy_id': 'B1',
        'observed_at': observed_at,
        'latitude': lat,
        'longitude': lon,
        'is_synthetic': False,
    }


def _trip_state(trip_id, vessel_id, status):
    return {
        'trip_id': trip_id,
        'vessel_id': vessel_id,
        'status': status,
        'welfare_status': 'unknown',
        'departure_at': None,
        'expected_return_at': None,
        'expected_checkin_interval_minutes': None,
        'amendments': [],
    }


def _run_evaluation(contact_rows, trip_states):
    def responder(kind, sql, args):
        if kind == 'fetch' and 'FROM buoy_contacts' in sql:
            return contact_rows
        if kind == 'fetch' and 'FROM vessel_trips' in sql:
            return trip_states
        return None

    conn = FakeConn(responder)
    error = None
    try:
        asyncio.run(evaluate_and_persist(conn, as_of=now_utc(), include_synthetic=False))
    except Exception as exc:
        error = exc
    deactivated = bool(conn.calls_matching('SET is_active = FALSE'))
    return error, deactivated


@pytest.mark.finding('backend.contacts.optional-position-crash')
def test_contact_without_coordinates_does_not_abort_fleet_evaluation():
    now = now_utc()
    try:
        ContactEventIn(
            event_id='e1',
            vessel_id='V-NOPOS',
            trip_id='T-NOPOS',
            buoy_id='B1',
            observed_at=now,
            source='live',
        )
    except ValidationError:
        return
    rows = [
        _contact_row('V-NOPOS', 'T-NOPOS', now - timedelta(hours=1), lat=None, lon=None),
        _contact_row('V-OK', 'T-OK', now - timedelta(hours=1)),
    ]
    try:
        eligible = eligible_latest_trips(rows, as_of=now)
    except (TypeError, ValueError) as exc:
        pytest.fail(f'one accepted contact without coordinates aborts evaluation for every vessel: {exc!r}')
    assert 'V-OK' in {vessel for vessel, _, _ in eligible}


@pytest.mark.finding('backend.ai.anomaly.zero-contact-poison-run')
def test_zero_contact_trip_for_a_fresh_vessel_does_not_abort_evaluation():
    error, deactivated = _run_evaluation([], [_trip_state('T-ZERO', 'V-FRESH', 'open')])
    assert error is None, (
        f'an open trip with no contacts for a never-seen vessel aborts evaluation: {error!r} '
        f'(active scores already deactivated before the crash: {deactivated})'
    )


@pytest.mark.finding('backend.ai.anomaly.zero-contact-poison-run')
def test_zero_contact_trip_for_a_known_vessel_does_not_abort_evaluation():
    history = [
        _contact_row('V-OLD', 'T-OLD', now_utc() - timedelta(days=3, hours=h)) for h in range(3)
    ]
    trip_states = [_trip_state('T-OLD', 'V-OLD', 'completed'), _trip_state('T-NEW', 'V-OLD', 'open')]
    error, deactivated = _run_evaluation(history, trip_states)
    assert error is None, (
        f'an open zero-contact trip for a vessel with history aborts evaluation: {error!r} '
        f'(active scores already deactivated before the crash: {deactivated})'
    )


# ---------------------------------------------------------------------------
# Section 2: Operator Authentication and Squall Training (SEC-12, SEC-13, SEC-14)
# ---------------------------------------------------------------------------


@pytest.mark.finding('backend.auth.login-timing-enumeration')
def test_unknown_email_pays_the_same_bcrypt_cost_as_a_wrong_password(monkeypatch):
    install_pool(monkeypatch, FakeConn(), 'app.api.auth')
    calls = []

    def counting_verify(password, password_hash):
        calls.append(password_hash)
        return False

    monkeypatch.setattr('app.api.auth.verify_password', counting_verify)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/login', json={'email': 'nobody@example.com', 'password': 'x'})
    require_status(response, 401)
    assert len(calls) == 1, (
        f'login for an unknown email ran bcrypt {len(calls)} times; a known email with a wrong '
        'password runs it once, so response time reveals which emails have accounts'
    )


@pytest.mark.finding('backend.operator-jwt.no-server-revocation')
def test_token_for_an_account_that_no_longer_exists_is_rejected(monkeypatch):
    conn = FakeConn()
    install_pool(monkeypatch, conn, 'app.api.auth')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/me', headers=operator_headers(user_id=987654))
    assert response.status_code == 401, (
        f'a token for a non-existent operator was accepted (HTTP {response.status_code}); '
        f'the server consulted {len(conn.calls)} database queries to check it'
    )


def _stub_training(monkeypatch):
    import inspect
    caller_frame = inspect.currentframe().f_back
    caller_role = caller_frame.f_locals.get('role', 'admin') if caller_frame else 'admin'

    def responder(kind, sql, args):
        if 'FROM users' in sql and args and args[0] == 1:
            return {'id': 1, 'email': f'probe.{caller_role}@example.invalid', 'role': caller_role, 'token_version': 0}
        return None

    install_pool(monkeypatch, FakeConn(responder), 'app.api.squall')
    monkeypatch.setenv('ALLOW_TRAINING', 'true')
    writes = []

    async def fake_rows(conn, *, live):
        return [{'reading': 1}], [{'squall': 1}], []

    monkeypatch.setattr('app.api.squall._load_rows', fake_rows)
    monkeypatch.setattr('app.api.squall.build_buoys', lambda rows: {})
    monkeypatch.setattr(
        'app.api.squall.train_from_rows',
        lambda readings, squalls, buoys: (SimpleNamespace(calibration='probe', top_features=[]), {}),
    )
    monkeypatch.setattr('app.api.squall.save_bundle', writes.append)
    return writes


@pytest.mark.finding('backend.ai.squall.flag-authorizes-live-model-replacement')
@pytest.mark.parametrize('role', ['mdrrmo', 'lgu'])
def test_non_admin_operator_cannot_replace_the_live_squall_model(monkeypatch, role):
    writes = _stub_training(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/ai/squall/train', headers=operator_headers(role=role))
    assert not writes and response.status_code == 403, (
        f'with ALLOW_TRAINING=true a {role} token got HTTP {response.status_code} and '
        f'{len(writes)} model write(s) to the live squall artifact'
    )


@pytest.mark.finding('backend.ai.squall.flag-authorizes-live-model-replacement:control')
def test_squall_control_admin_reaches_the_model_write(monkeypatch):
    writes = _stub_training(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/ai/squall/train', headers=operator_headers(role='admin'))
    assert response.status_code == 200 and len(writes) == 1, response.text


# ---------------------------------------------------------------------------
# Section 3: Ingest Trust and Contact Skew (SEC-04, SEC-16)
# ---------------------------------------------------------------------------

GATEWAY_KEY = 'probe-gateway-key'
CALIBRATION_ARG = 7


def _current_responder(kind, sql, args):
    if kind == 'fetchrow' and 'INSERT INTO current_observations' in sql:
        return {
            'id': 1,
            'event_id': args[0],
            'buoy_id': args[1],
            'source': args[6],
            'calibration_status': args[CALIBRATION_ARG],
        }
    return None


@pytest.mark.finding('backend.current-ingest.unbound-calibration-claim')
def test_request_text_cannot_mark_a_current_reading_qualified(monkeypatch):
    conn = FakeConn(_current_responder)
    install_pool(monkeypatch, conn, 'app.api.current_events')
    monkeypatch.setenv('GATEWAY_API_KEY', GATEWAY_KEY)
    body = {
        'event_id': 'probe-current-1',
        'buoy_id': 'BUOY-NO-INSTRUMENT',
        'observed_at': now_utc().isoformat(),
        'observed_u_mps': 0.2,
        'observed_v_mps': 0.1,
        'source': 'live',
        'calibration_status': 'qualified',
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
        'event_id': 'probe-contact-1',
        'vessel_id': 'V1',
        'trip_id': 'T1',
        'buoy_id': 'B1',
        'observed_at': now_utc(),
        'latitude': 11.66,
        'longitude': 122.44,
        'source': 'live',
    }
    body.update(overrides)
    return body


@pytest.mark.finding('backend.contacts.future-timestamp-anomaly-suppression')
def test_contact_ingest_rejects_a_day_ahead_timestamp():
    with pytest.raises(ValidationError):
        ContactEventIn(**_contact(observed_at=now_utc() + timedelta(days=1)))


@pytest.mark.finding('backend.contacts.future-timestamp-anomaly-suppression:control')
def test_contact_control_present_timestamp_is_accepted():
    ContactEventIn(**_contact())


# ---------------------------------------------------------------------------
# Section 4: Public Disclosure (SEC-15)
# ---------------------------------------------------------------------------

OPERATOR_EMAIL = 'operator.audit@example.invalid'


def _sea_condition_responder(kind, sql, args):
    if kind == 'fetchrow' and 'FROM sea_conditions' in sql:
        return {
            'id': 1,
            'status': 'caution',
            'reason': 'probe',
            'set_by_user_id': '42',
            'set_by_name': OPERATOR_EMAIL,
            'created_at': now_utc(),
        }
    return None


@pytest.mark.finding('backend.public-sea-condition.operator-identity-disclosure')
def test_public_sea_condition_does_not_expose_operator_account(monkeypatch):
    install_pool(monkeypatch, FakeConn(_sea_condition_responder), 'app.api.public', 'app.api.sea_condition')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/public/sea-condition')
    require_status(response, 200)
    current = response.json()['current']
    leaked = {key: current[key] for key in ('set_by_user_id', 'set_by_name') if key in current}
    assert OPERATOR_EMAIL not in response.text and not leaked, (
        f'anonymous GET /api/public/sea-condition returned operator account fields {sorted(leaked)}'
    )


# ---------------------------------------------------------------------------
# Section 5: Static Repo & Firmware Checks (SEC-26, SEC-27, SEC-28, SEC-29, SEC-30, SEC-31, SEC-32)
# ---------------------------------------------------------------------------

SHORE = REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneShore.ino'
BUOY = REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneBuoy.ino'
LOAM_BUOY = REPO_ROOT / 'firmware' / 'buoy' / 'AqOneBuoy' / 'AqOneLoam.h'
LOAM_SHORE = REPO_ROOT / 'firmware' / 'shore' / 'AqOneShore' / 'AqOneLoam.h'
GRADLE = REPO_ROOT / 'mobile' / 'android' / 'app' / 'build.gradle.kts'
TRACKED_APK = REPO_ROOT / 'mobile' / 'releases' / 'aqone-release.apk'

PLACEHOLDER = re.compile(r'^$|your|change|example|placeholder|xxx|<.*>', re.I)


def _code(path) -> str:
    text = path.read_text('utf-8')
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def _string_constant(path, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"', _code(path))
    return match.group(1) if match else None


def _case_block(code: str, label: str) -> str:
    start = code.index(f'case {label}:')
    following = re.search(r'\bcase T_[A-Z_]+\s*:', code[start + 1:])
    return code[start: start + 1 + following.start()] if following else code[start:]


@pytest.mark.finding('firmware.shore.committed-uplink-credential')
@pytest.mark.parametrize('name', ['UPLINK_SSID', 'UPLINK_PASS', 'GATEWAY_API_KEY'])
def test_shore_sketch_holds_no_concrete_credential(name):
    value = _string_constant(SHORE, name)
    if value is None:
        return
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


@pytest.mark.finding('firmware.loam.shared-default-key:control')
def test_loam_control_headers_are_byte_identical():
    assert LOAM_BUOY.read_bytes() == LOAM_SHORE.read_bytes()


@pytest.mark.finding('firmware.shore.tls-peer-verification-disabled')
def test_shore_verifies_the_backend_certificate():
    code = _code(SHORE)
    assert 'setInsecure()' not in code, 'the shore sketch calls WiFiClientSecure::setInsecure()'


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
    if not TRACKED_APK.exists():
        return
    assert b'Android Debug' not in TRACKED_APK.read_bytes(), (
        'mobile/releases/aqone-release.apk carries an "Android Debug" signing certificate'
    )


# ---------------------------------------------------------------------------
# Section 6: Resource Bounds & Mesh Chat (SEC-17, SEC-19)
# ---------------------------------------------------------------------------


@pytest.mark.finding('backend.demo-weather.unbounded-coordinate-expansion')
def test_demo_weather_rejects_ten_thousand_coordinate_cells():
    many = 10_000
    with pytest.raises(ValueError):
        coordinates(','.join(['11.66'] * many), ','.join(['122.44'] * many))


@pytest.mark.finding('backend.mesh.unbounded-public-storage')
def test_mesh_chat_has_a_retention_or_admission_control():
    sources = [
        *(REPO_ROOT / 'backend' / 'app').rglob('*.py'),
        *(REPO_ROOT / 'backend' / 'migrations').glob('*.sql'),
        *(REPO_ROOT / 'backend').glob('*.py'),
        *REPO_ROOT.glob('render.yaml'),
    ]
    pattern = re.compile(r'DELETE\s+FROM\s+mesh_chat|mesh_chat.*retention|pg_cron|RateLimit|slowapi', re.I)
    hits = [str(path.relative_to(REPO_ROOT)) for path in sources if pattern.search(path.read_text('utf-8'))]
    assert hits, 'no retention job, cleanup statement, or rate limiter for anonymous mesh_chat rows'


# ---------------------------------------------------------------------------
# Section 7: SOS Integrity (SEC-06)
# ---------------------------------------------------------------------------

TRUST_TIER_ARG = 7
BUOY_ID_ARG = 9
DELIVERED_VIA_BUOY_ARG = 13


def _sos(**overrides):
    body = {
        'vessel_id': 'PROBE-V1',
        'client_ts': 1_700_000_000,
        'boat': 'PROBE',
        'lat': 11.6639,
        'lon': 122.4602,
        'note': 'probe',
        'source': 'direct',
        'local_id': 'probe-local-1',
    }
    body.update(overrides)
    return {key: value for key, value in body.items() if value is not None}


def _sos_insert_responder(kind, sql, args):
    if kind == 'fetchrow' and 'INSERT INTO sos_events' in sql:
        return {
            'id': 1,
            'was_inserted': True,
            'vessel_id': args[0],
            'client_ts': args[1],
            'nonce': args[2],
            'delivered_direct': args[12],
            'delivered_via_buoy': args[13],
            'acknowledged_at': None,
        }
    return None


def _post_anonymous_sos(monkeypatch, body):
    conn = FakeConn(_sos_insert_responder)
    install_pool(monkeypatch, conn, 'app.api.sos')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/sos', json=body)
    inserts = conn.calls_matching('INSERT INTO sos_events')
    return response, (inserts[0][2] if inserts else None), conn


@pytest.mark.finding('backend.sos.untrusted-provenance-claims')
def test_anonymous_sos_cannot_self_assert_responder_confirmation(monkeypatch):
    response, args, _ = _post_anonymous_sos(monkeypatch, _sos(trust_tier='confirmed_by_responder'))
    if response.status_code in (401, 403, 422):
        return
    require_status(response, 200)
    assert args[TRUST_TIER_ARG] != 'confirmed_by_responder', (
        'an unauthenticated request stored trust_tier=confirmed_by_responder on a new incident'
    )


@pytest.mark.finding('backend.sos.untrusted-provenance-claims')
def test_anonymous_sos_cannot_claim_buoy_delivery_without_gateway_key(monkeypatch):
    body = _sos(source='buoy', buoy_id='UNTRUSTED-BUOY', src_id=4242, seq=7, local_id=None)
    response, args, conn = _post_anonymous_sos(monkeypatch, body)
    if response.status_code in (401, 403):
        return
    require_status(response, 200)
    registered_buoys = [call[2][0] for call in conn.calls_matching('INSERT INTO buoys')]
    assert not args[DELIVERED_VIA_BUOY_ARG] and args[BUOY_ID_ARG] is None, (
        'a request with no gateway key was stored as delivered_via_buoy='
        f'{args[DELIVERED_VIA_BUOY_ARG]} with buoy_id={args[BUOY_ID_ARG]!r}; '
        f'buoys auto-registered: {registered_buoys}'
    )


# ---------------------------------------------------------------------------
# Section 8: Unauthenticated Routes (SEC-09, SEC-10)
# ---------------------------------------------------------------------------

TRIP_ROUTES = [
    ('GET', '/api/v1/trips', None),
    ('GET', '/api/v1/trips/PROBE-TRIP', None),
    ('PATCH', '/api/v1/trips/PROBE-TRIP', {'welfare_status': 'safe', 'expected_return_at': '2030-01-01T00:00:00Z'}),
]

WARNING_DELIVERY_ROUTES = [
    (
        'POST',
        '/api/advisories/delivery',
        {
            'warning_id': 101,
            'delivery_state': 'user_acknowledged',
            'vessel_id': 'dummy-victim',
            'occurred_at': '2026-01-01T00:00:00Z',
            'details': {'probe': True},
        },
    ),
    ('GET', '/api/advisories/101/deliveries', None),
]


def _anonymous(monkeypatch, method, path, body):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.request(method, path, json=body)
    if response.status_code == 422:
        raise ProbeBroken(f'{method} {path} rejected the probe body: {response.text[:300]}')
    return response


@pytest.mark.finding('backend.trips.unbound-public-access')
@pytest.mark.parametrize(('method', 'path', 'body'), TRIP_ROUTES)
def test_trip_route_requires_a_bound_principal(monkeypatch, method, path, body):
    response = _anonymous(monkeypatch, method, path, body)
    assert response.status_code in (401, 403), (
        f'{method} {path} with no credentials reached the handler (HTTP {response.status_code})'
    )


@pytest.mark.finding('backend.warning-delivery.unbound-state-authority')
@pytest.mark.parametrize(('method', 'path', 'body'), WARNING_DELIVERY_ROUTES)
def test_warning_delivery_route_requires_an_authority(monkeypatch, method, path, body):
    response = _anonymous(monkeypatch, method, path, body)
    assert response.status_code in (401, 403), (
        f'{method} {path} with no credentials reached the handler (HTTP {response.status_code})'
    )
