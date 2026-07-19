"""Samsara OAuth2 Routes — FastAPI endpoints for marketplace integration.

Handles:
- OAuth2 authorization flow
- Callback handling
- Credential storage
- Fleet data endpoints
"""

import hmac
import os
import time
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from v1_integrations.samsara_client import (
    SamsaraClient,
    SamsaraIntegration,
    store_samsara_credentials,
    get_samsara_credentials,
    create_client,
)
from v1_monitoring.logger import get_logger

log = get_logger("edge77.samsara_routes")

router = APIRouter(prefix="/v1/samsara", tags=["samsara"])

# In-memory OAuth state (short-lived, cleared on callback)
_oauth_states: dict = {}
_oauth_code_verifiers: dict = {}


def _verify_samsara_auth(authorization: Optional[str], client_id: str) -> None:
    """Verify the caller is authorized for this client_id.

    Accepts either:
    - Internal API token (admin access)
    - e77_ API key belonging to this client
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]

    # Internal token = admin access (constant-time comparison)
    internal_token = os.getenv("INTERNAL_API_TOKEN", "")
    if internal_token and hmac.compare_digest(token, internal_token):
        return

    # Per-client API key
    if token.startswith("e77_"):
        from v1_database.api_keys import validate_api_key
        key_data = validate_api_key(token)
        if key_data and key_data.get("client_id") == client_id:
            return

    raise HTTPException(status_code=403, detail="Not authorized for this client")


@router.get("/auth")
async def samsara_auth(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    """Initiate Samsara OAuth2 authorization."""
    _verify_samsara_auth(authorization, client_id)

    samsara_client_id = os.getenv("SAMSARA_CLIENT_ID")
    samsara_client_secret = os.getenv("SAMSARA_CLIENT_SECRET")
    samsara_redirect_uri = os.getenv("SAMSARA_REDIRECT_URI")

    if not all([samsara_client_id, samsara_client_secret, samsara_redirect_uri]):
        raise HTTPException(
            status_code=503,
            detail="Samsara integration not configured. Set SAMSARA_CLIENT_ID, SAMSARA_CLIENT_SECRET, and SAMSARA_REDIRECT_URI.",
        )

    client = SamsaraClient(
        client_id=samsara_client_id,
        client_secret=samsara_client_secret,
        redirect_uri=samsara_redirect_uri,
    )

    try:
        auth_url, state, code_verifier = client.generate_auth_url()
    except Exception as exc:
        log.error("samsara_auth_url_failed", client_id=client_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to generate Samsara auth URL")

    _oauth_states[state] = {
        "client_id": client_id,
        "created_at": time.time(),
    }
    _oauth_code_verifiers[state] = code_verifier

    # Clean old states (older than 10 minutes)
    now = time.time()
    stale = [s for s, d in _oauth_states.items() if now - d.get("created_at", 0) > 600]
    for s in stale:
        _oauth_states.pop(s, None)
        _oauth_code_verifiers.pop(s, None)

    log.info("samsara_auth_initiated", client_id=client_id, state=state[:8] + "...")

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def samsara_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handle OAuth2 callback from Samsara.

    This endpoint is called by Samsara servers — no auth required.
    Must be in AuthMiddleware.SKIP_PATHS.
    """
    if error:
        log.error("samsara_auth_error", error=error)
        raise HTTPException(status_code=400, detail=f"Samsara authorization failed: {error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state")

    state_data = _oauth_states.pop(state, None)
    code_verifier = _oauth_code_verifiers.pop(state, None)

    if not state_data or not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    client_id = state_data["client_id"]

    samsara_client_id = os.getenv("SAMSARA_CLIENT_ID", "")
    samsara_client_secret = os.getenv("SAMSARA_CLIENT_SECRET", "")
    samsara_redirect_uri = os.getenv("SAMSARA_REDIRECT_URI", "")

    if not all([samsara_client_id, samsara_client_secret, samsara_redirect_uri]):
        raise HTTPException(status_code=503, detail="Samsara credentials not configured")

    samsara_client = SamsaraClient(
        client_id=samsara_client_id,
        client_secret=samsara_client_secret,
        redirect_uri=samsara_redirect_uri,
    )

    try:
        token_data = await samsara_client.exchange_code(code, code_verifier)
    except Exception as e:
        log.error("samsara_token_exchange_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to exchange authorization code")

    store_samsara_credentials(
        client_id=client_id,
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", ""),
        expires_at=time.time() + token_data.get("expires_in", 3600),
        scope=token_data.get("scope", ""),
    )

    log.info("samsara_auth_completed", client_id=client_id, scope=token_data.get("scope"))

    return HTMLResponse("""
        <html>
        <head><title>Samsara Connected</title></head>
        <body>
            <h1>Samsara Connected Successfully!</h1>
            <p>Your fleet data is now connected to EDGE77.</p>
            <script>
                if (window.opener) {
                    window.opener.postMessage({type: 'samsara_connected'}, '*');
                    window.close();
                } else {
                    setTimeout(function() { window.location.href = '/dashboard'; }, 2000);
                }
            </script>
        </body>
        </html>
    """)


@router.get("/status/{client_id}")
async def samsara_status(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    """Check Samsara connection status for a client."""
    _verify_samsara_auth(authorization, client_id)

    creds = get_samsara_credentials(client_id)

    if not creds:
        return JSONResponse({
            "connected": False,
            "message": "Samsara not connected",
        })

    expires_at = creds.get("expires_at", "")
    is_expired = False
    if expires_at:
        try:
            exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            is_expired = exp_time.timestamp() < time.time()
        except (ValueError, TypeError):
            is_expired = True

    return JSONResponse({
        "connected": True,
        "scope": creds.get("scope"),
        "connected_at": creds.get("connected_at"),
        "token_expired": is_expired,
    })


@router.get("/fleet/{client_id}")
async def get_fleet(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get fleet overview for a connected client."""
    _verify_samsara_auth(authorization, client_id)

    client = create_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Samsara not connected for this client")

    integration = SamsaraIntegration(client)
    try:
        summary = await integration.get_client_fleet_summary(client_id)
    except Exception as exc:
        log.error("samsara_fleet_failed", client_id=client_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch fleet data")

    return JSONResponse(summary)


@router.get("/vehicles/{client_id}")
async def get_vehicles(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get all vehicles for a connected client."""
    _verify_samsara_auth(authorization, client_id)

    client = create_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Samsara not connected for this client")

    try:
        vehicles = await client.get_vehicles()
    except Exception as exc:
        log.error("samsara_vehicles_failed", client_id=client_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch vehicles")
    return JSONResponse({"vehicles": vehicles})


@router.get("/drivers/{client_id}")
async def get_drivers(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get all drivers for a connected client."""
    _verify_samsara_auth(authorization, client_id)

    client = create_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Samsara not connected for this client")

    try:
        drivers = await client.get_drivers()
    except Exception as exc:
        log.error("samsara_drivers_failed", client_id=client_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch drivers")
    return JSONResponse({"drivers": drivers})


@router.get("/trips/{client_id}")
async def get_trips(
    client_id: str,
    vehicle_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """Get trips for a connected client, optionally filtered."""
    _verify_samsara_auth(authorization, client_id)

    client = create_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Samsara not connected for this client")

    start = datetime.fromisoformat(start_time) if start_time else None
    end = datetime.fromisoformat(end_time) if end_time else None

    try:
        trips = await client.get_trips(
            vehicle_id=vehicle_id,
            start_time=start,
            end_time=end,
        )
    except Exception as exc:
        log.error("samsara_trips_failed", client_id=client_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch trips")

    return JSONResponse({"trips": trips})


@router.get("/match/{client_id}")
async def match_invoice(
    client_id: str,
    vehicle_id: Optional[str] = None,
    driver_name: Optional[str] = None,
    trip_date: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """Match invoice data to Samsara fleet data."""
    _verify_samsara_auth(authorization, client_id)

    client = create_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Samsara not connected for this client")

    integration = SamsaraIntegration(client)

    mock_invoice = {
        "vehicle_id": vehicle_id,
        "driver_name": driver_name,
        "trip_date": trip_date,
    }

    match_result = await integration.match_invoice_to_trip(mock_invoice, client_id)

    return JSONResponse(match_result)
