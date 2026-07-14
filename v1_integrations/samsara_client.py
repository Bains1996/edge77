"""Samsara API Integration — OAuth2 + Vehicle/Driver Data.

This module handles:
- OAuth2 authorization flow for Samsara partners
- Fetching vehicle and driver data from Samsara
- Matching invoices to trips/vehicles
- Marketplace-ready integration
"""

import os
import time
import secrets
import hashlib
import base64
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

from v1_monitoring.logger import get_logger

log = get_logger("edge77.samsara")

# Samsara API Configuration
SAMSARA_BASE_URL = "https://api.samsara.com"
SAMSARA_AUTH_URL = "https://api.samsara.com/connect/authorize"
SAMSARA_TOKEN_URL = "https://api.samsara.com/connect/token"

# Scopes needed for freight audit
SAMSARA_SCOPES = [
    "vehicles",
    "drivers",
    "trips",
    "fuel",
    "maintenance",
]


class SamsaraClient:
    """Client for Samsara OAuth2 and API integration."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._token_cache: Dict[str, Any] = {}

    def generate_auth_url(self, state: Optional[str] = None) -> Tuple[str, str, str]:
        """Generate OAuth2 authorization URL with PKCE.

        Returns:
            Tuple of (auth_url, state, code_verifier)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(SAMSARA_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{SAMSARA_AUTH_URL}?{urlencode(params)}"
        return auth_url, state, code_verifier

    async def exchange_code(self, code: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from redirect
            code_verifier: PKCE code verifier

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SAMSARA_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            token_data = response.json()

            # Cache token with expiry
            self._token_cache = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": time.time() + token_data.get("expires_in", 3600),
                "scope": token_data.get("scope"),
            }

            log.info("samsara_token_exchanged", scope=token_data.get("scope"))
            return token_data

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SAMSARA_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            token_data = response.json()

            self._token_cache = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", refresh_token),
                "expires_at": time.time() + token_data.get("expires_in", 3600),
                "scope": token_data.get("scope"),
            }

            return token_data

    async def _get_valid_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if not self._token_cache:
            raise ValueError("No token available. Complete OAuth2 flow first.")

        if time.time() >= self._token_cache.get("expires_at", 0) - 60:
            # Token expired or about to expire
            refresh_token = self._token_cache.get("refresh_token")
            if refresh_token:
                await self.refresh_token(refresh_token)
            else:
                raise ValueError("Token expired and no refresh token available.")

        return self._token_cache["access_token"]

    async def _api_get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make authenticated GET request to Samsara API."""
        token = await self._get_valid_token()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SAMSARA_BASE_URL}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_vehicles(self) -> List[Dict[str, Any]]:
        """Fetch all vehicles from Samsara."""
        data = await self._api_get("/v1/fleet/list")
        vehicles = data.get("vehicles", [])
        log.info("samsara_vehicles_fetched", count=len(vehicles))
        return vehicles

    async def get_drivers(self) -> List[Dict[str, Any]]:
        """Fetch all drivers from Samsara."""
        data = await self._api_get("/v1/fleet/drivers/list")
        drivers = data.get("drivers", [])
        log.info("samsara_drivers_fetched", count=len(drivers))
        return drivers

    async def get_trips(
        self,
        vehicle_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch trips, optionally filtered by vehicle and time range."""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()

        params: Dict[str, Any] = {
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
        }
        if vehicle_id:
            params["vehicle_id"] = vehicle_id

        data = await self._api_get("/v1/fleet/trips", params=params)
        trips = data.get("trips", [])
        log.info("samsara_trips_fetched", count=len(trips), vehicle_id=vehicle_id)
        return trips

    async def get_vehicle_fuel(self, vehicle_id: str) -> Dict[str, Any]:
        """Get fuel data for a specific vehicle."""
        return await self._api_get(f"/v1/fleet/vehicles/{vehicle_id}/fuel")

    async def get_vehicle_info(self, vehicle_id: str) -> Dict[str, Any]:
        """Get detailed vehicle information."""
        return await self._api_get(f"/v1/fleet/vehicles/{vehicle_id}")

    async def get_odometer(self, vehicle_id: str) -> Dict[str, Any]:
        """Get odometer reading for mileage verification."""
        return await self._api_get(f"/v1/fleet/vehicles/{vehicle_id}/odometer")


class SamsaraIntegration:
    """High-level integration for freight audit + Samsara."""

    def __init__(self, client: SamsaraClient):
        self.client = client
        self._vehicles_cache: Optional[List[Dict]] = None
        self._drivers_cache: Optional[List[Dict]] = None
        self._cache_expires: float = 0

    async def _ensure_cache(self) -> None:
        """Refresh cache if expired (5 minute TTL)."""
        if time.time() > self._cache_expires:
            self._vehicles_cache = await self.client.get_vehicles()
            self._drivers_cache = await self.client.get_drivers()
            self._cache_expires = time.time() + 300

    async def match_invoice_to_trip(
        self,
        invoice: Dict[str, Any],
        client_id: str,
    ) -> Dict[str, Any]:
        """Match an invoice to Samsara trip data."""
        await self._ensure_cache()

        vehicle_id = invoice.get("vehicle_id")
        driver_name = invoice.get("driver_name")
        trip_date = invoice.get("trip_date")

        matched_data: Dict[str, Any] = {
            "samsara_match_found": False,
            "vehicle": None,
            "driver": None,
            "trip": None,
            "verification": {},
        }

        # Match by vehicle ID/VIN
        if vehicle_id and self._vehicles_cache:
            for vehicle in self._vehicles_cache:
                if vehicle.get("id") == vehicle_id or vehicle.get("vin") == vehicle_id:
                    matched_data["vehicle"] = vehicle
                    matched_data["samsara_match_found"] = True
                    break

        # Match by driver name
        if driver_name and self._drivers_cache:
            for driver in self._drivers_cache:
                if driver_name.lower() in driver.get("name", "").lower():
                    matched_data["driver"] = driver
                    matched_data["samsara_match_found"] = True
                    break

        # Get trip data if we have a vehicle and date
        if matched_data["vehicle"] and trip_date:
            try:
                start = datetime.fromisoformat(trip_date)
                end = start + timedelta(days=1)
                trips = await self.client.get_trips(
                    vehicle_id=matched_data["vehicle"]["id"],
                    start_time=start,
                    end_time=end,
                )
                if trips:
                    matched_data["trip"] = trips[0]
            except Exception as e:
                log.warning("samsara_trip_fetch_failed", error=str(e))

        # Verify fuel surcharge against actual fuel data
        if matched_data["vehicle"] and invoice.get("fuel_surcharge"):
            try:
                fuel_data = await self.client.get_vehicle_fuel(
                    matched_data["vehicle"]["id"]
                )
                matched_data["verification"]["fuel"] = {
                    "invoice_fuel": invoice.get("fuel_surcharge"),
                    "samsara_data": fuel_data,
                }
            except Exception as e:
                log.warning("samsara_fuel_fetch_failed", error=str(e))

        return matched_data

    async def get_client_fleet_summary(self, client_id: str) -> Dict[str, Any]:
        """Get fleet summary for a client's Samsara-connected account."""
        await self._ensure_cache()

        return {
            "total_vehicles": len(self._vehicles_cache or []),
            "total_drivers": len(self._drivers_cache or []),
            "vehicles": self._vehicles_cache[:10] if self._vehicles_cache else [],
            "drivers": self._drivers_cache[:10] if self._drivers_cache else [],
        }


def store_samsara_credentials(
    client_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: float,
    scope: str,
) -> None:
    """Store Samsara OAuth credentials for a client in Supabase."""
    from v1_database.supabase_client import MOCK_MODE, _rest_upsert

    if MOCK_MODE:
        log.info("samsara_credentials_stored_mock", client_id=client_id)
        return

    try:
        _rest_upsert("samsara_credentials", {
            "client_id": client_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
            "scope": scope,
            "connected_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        })
        log.info("samsara_credentials_stored", client_id=client_id)
    except Exception as e:
        log.error("samsara_credentials_store_failed", client_id=client_id, error=str(e))
        raise


def get_samsara_credentials(client_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve Samsara credentials for a client from Supabase."""
    from v1_database.supabase_client import MOCK_MODE, _rest_select

    if MOCK_MODE:
        return None

    try:
        rows = _rest_select("samsara_credentials", {
            "select": "*",
            "client_id": f"eq.{client_id}",
            "limit": 1,
        })
        if rows:
            creds = rows[0]
            # Check if token is expired
            expires_at = creds.get("expires_at", "")
            if expires_at:
                exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp_time.timestamp() < time.time():
                    log.warning("samsara_token_expired", client_id=client_id)
            return creds
        return None
    except Exception as e:
        log.error("samsara_credentials_fetch_failed", client_id=client_id, error=str(e))
        return None


def create_client(client_id: str) -> Optional[SamsaraClient]:
    """Create a SamsaraClient for a specific client using stored credentials."""
    creds = get_samsara_credentials(client_id)
    if not creds:
        return None

    samsara_client_id = os.getenv("SAMSARA_CLIENT_ID", "")
    samsara_client_secret = os.getenv("SAMSARA_CLIENT_SECRET", "")
    samsara_redirect_uri = os.getenv("SAMSARA_REDIRECT_URI", "")

    if not all([samsara_client_id, samsara_client_secret, samsara_redirect_uri]):
        log.error("samsara_env_missing", client_id=client_id)
        return None

    client = SamsaraClient(
        client_id=samsara_client_id,
        client_secret=samsara_client_secret,
        redirect_uri=samsara_redirect_uri,
    )
    client._token_cache = {
        "access_token": creds["access_token"],
        "refresh_token": creds.get("refresh_token", ""),
        "expires_at": datetime.fromisoformat(
            creds["expires_at"].replace("Z", "+00:00")
        ).timestamp(),
        "scope": creds.get("scope"),
    }

    return client
