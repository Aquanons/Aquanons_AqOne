from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.api.advisories import public_router as public_advisories_router
from app.api.advisories import router as advisories_router
from app.api.anomaly import router as anomaly_router
from app.api.anomaly_cases import router as anomaly_cases_router
from app.api.auth import router as auth_router
from app.api.catch import protected_router as catch_read_router
from app.api.catch import router as catch_ingest_router
from app.api.contacts import router as contacts_router
from app.api.current_events import router as current_events_router
from app.api.demo import router as demo_router
from app.api.drift import router as drift_router
from app.api.hotspots import router as hotspots_router
from app.api.mesh import router as mesh_router
from app.api.metrics import router as metrics_router
from app.api.ops_audit import router as ops_audit_router
from app.api.ops_status import router as ops_status_router
from app.api.pressure_events import router as pressure_events_router
from app.api.public import router as public_router
from app.api.sea_condition import router as sea_condition_router
from app.api.sos import gateway_router as sos_downlink_router
from app.api.sos import protected_router as sos_read_router
from app.api.sos import router as sos_ingest_router
from app.api.squall import router as squall_router
from app.api.trips import router as trips_router
from app.api.vessel_auth import router as vessel_auth_router
from app.api.vessel_profile import confirm_router as vessel_confirmation_router
from app.api.vessel_profile import router as vessel_profile_router
from app.auth import require_user
from app.db import get_pool, shutdown_db, startup_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await startup_db()
    yield
    await shutdown_db()


app = FastAPI(lifespan=lifespan)

# Routers are registered BEFORE the static mount below. Starlette matches
# routes in registration order, so mounting the dashboard at "/" first would
# shadow every API path - including /health/ready, which would turn the
# Railway healthcheck red for reasons that look unrelated to this file.
# Auth is the only unauthenticated API surface: /api/login, /api/admin-signup
# (itself gated by ADMIN_SETUP_KEY) and /api/me, which authenticates itself.
app.include_router(auth_router)

# Mesh chat accepts anonymous app posts and assigns origins from credentials.
app.include_router(mesh_router)

# SOS ingest is intentionally unauthenticated - see app/api/sos.py. A handset in
# distress has no token, and the LoRa gateway relays frames it cannot
# authenticate. Reading and acknowledging SOS events stays protected.
app.include_router(sos_ingest_router)

# Vessel identity registration is unauthenticated for the same reason SOS
# ingest is - the handset has no account, and it is the same self-declared
# identity as the call itself. The read side (GET /api/sos/active) stays
# protected. See app/api/vessel_profile.py.
app.include_router(vessel_profile_router)
app.include_router(vessel_confirmation_router)

# Catch logging now sits behind a vessel-bound device credential rather than a
# dispatcher token. Keeping it off the blanket operator dependency here lets
# the mobile app use its own credential type while SOS ingest stays open.
app.include_router(catch_ingest_router)

# Gateway-only contact-event ingest (docs/04_INGEST_API.md "Contact events").
# Guarded per-route by its own require_gateway_key, not the blanket operator
# dependency below - a dashboard operator token must not be able to
# manufacture a contact event, and a gateway key must not read dispatcher
# data. See app/api/contacts.py.
app.include_router(contacts_router)

# Gateway-only pressure-event ingest (docs/04_INGEST_API.md "Pressure
# events"), the trusted-telemetry source squall nowcasting is gated on
# (docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md Phase 1). Same
# per-route require_gateway_key guard as contacts_router, for the same
# reason. See app/api/pressure_events.py.
app.include_router(pressure_events_router)

# Gateway-only SOS downlink (GET /api/sos/downlink). The return leg of the
# distress loop: the shore gateway reads the responder's acknowledgement and
# ETA here and puts them back on the radio. Same require_gateway_key guard as
# the ingest routers, and deliberately NOT mounted under _protected - the
# gateway has no operator account and cannot obtain one. It stays a separate
# router from sos_read_router precisely so the gateway key buys the downlink
# fields and nothing else; see sos_downlink() for the field-by-field reasoning.
app.include_router(sos_downlink_router)

# Gateway-only current-event ingest (Phase 2 Task 2.2). Guarded per-route by
# require_gateway_key, matching contacts_router and pressure_events_router.
app.include_router(current_events_router)

# Explicit vessel trips and welfare evidence collection (Phase 2 Task 2.4).
app.include_router(trips_router)

# Read-only safety feeds for the handset. Unauthenticated for the same reason
# ingest is: the fisherman app has no account by design, so anything it needs
# in an emergency cannot sit behind a token. See app/api/public.py.
app.include_router(public_router)
# The aggregated catch-activity surface. Public for the same reason
# public_router is - the handset has no account. Its privacy property is in
# the response shape, not in auth: app/api/hotspots.py emits binned cells
# with a minimum reporter count and never a vessel id or an exact point, so
# there is nothing here that authentication would be protecting.
app.include_router(hotspots_router)
# Vessel-device pairing + token lifecycle. Some routes are public
# (enrollment), others require an operator or vessel-device token per-route.
app.include_router(vessel_auth_router)

# Advisories handles its own auth per-route rather than a blanket dependency
# here, because public_advisories_router (below) is intentionally
# unauthenticated - see app/api/public.py's reasoning for the handset feeds.
# Every route on advisories_router itself now requires a token
# (app/api/advisories.py), including POST /alert, which previously had none.
app.include_router(advisories_router)
app.include_router(public_advisories_router)

# Case timelines and the admin-only global audit search/export - each route
# carries its own require_responder_roles/require_admin_role guard
# (app/api/ops_audit.py), same self-guarded pattern as advisories_router.
app.include_router(ops_audit_router)
app.include_router(ops_status_router)

# Everything else requires a valid bearer token. Declaring it here rather than
# on each route means a newly added endpoint is protected by default - the safe
# direction to fail.
_protected = [Depends(require_user)]
app.include_router(anomaly_router, dependencies=_protected)
app.include_router(anomaly_cases_router, dependencies=_protected)
app.include_router(drift_router, dependencies=_protected)
app.include_router(squall_router, dependencies=_protected)
app.include_router(sea_condition_router, dependencies=_protected)
app.include_router(metrics_router, dependencies=_protected)
app.include_router(sos_read_router, dependencies=_protected)
app.include_router(catch_read_router, dependencies=_protected)

if os.environ.get('DEMO_MODE', '').strip().lower() in {'1', 'true', 'yes', 'on'}:
    app.include_router(demo_router)


@app.get('/healthz')
async def healthz() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/health/ready')
async def ready() -> dict[str, str | None]:
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
    except Exception as exc:
        raise HTTPException(status_code=503, detail='database not ready') from exc

    return {'status': 'ok', 'commit': os.environ.get('RENDER_GIT_COMMIT')}


def _resolve_web_dir() -> Path | None:
    """Locate the dashboard directory in both the container and a local checkout.

    This file lives at <root>/backend/app/main.py, and the Dockerfile copies
    web/ to the matching place inside the image, so parents[2]/web covers both.
    The second candidate is a fallback for layouts that nest web/ under
    backend/. A missing directory silently skips the mount and produces 404s
    with no obvious cause, so the failure is logged loudly rather than passed
    over.
    """
    here = Path(__file__).resolve()
    candidates = [here.parents[2] / 'web', here.parents[1] / 'web']
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    logger.warning(
        'Dashboard not mounted: no web directory found. Tried: %s',
        ', '.join(str(c) for c in candidates),
    )
    return None


_web_dir = _resolve_web_dir()
if _web_dir is not None:
    # Mounted last, at the root, with html=True so "/" serves web/index.html
    # and the existing relative asset paths in the HTML keep resolving.
    app.mount('/', StaticFiles(directory=str(_web_dir), html=True), name='web')
