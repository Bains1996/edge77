import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx

logger = logging.getLogger("edge77")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_rest_client: Optional[httpx.Client] = None
_async_rest_client: Optional[httpx.AsyncClient] = None
MOCK_MODE = True


def _get_rest_client() -> Optional[httpx.Client]:
    global _rest_client
    if _rest_client is not None:
        return _rest_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    _rest_client = httpx.Client(
        base_url=f"{SUPABASE_URL}/rest/v1",
        headers={
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        timeout=15.0,
    )
    return _rest_client


def _get_async_rest_client() -> Optional[httpx.AsyncClient]:
    global _async_rest_client
    if _async_rest_client is not None:
        return _async_rest_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    _async_rest_client = httpx.AsyncClient(
        base_url=f"{SUPABASE_URL}/rest/v1",
        headers={
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        timeout=15.0,
    )
    return _async_rest_client


def _rest_select(table: str, params: dict) -> list[dict]:
    client = _get_rest_client()
    if not client:
        return []
    resp = client.get(f"/{table}", params=params)
    resp.raise_for_status()
    return resp.json()


async def _async_rest_select(table: str, params: dict) -> list[dict]:
    client = _get_async_rest_client()
    if not client:
        return []
    resp = await client.get(f"/{table}", params=params)
    resp.raise_for_status()
    return resp.json()


def _rest_insert(table: str, data: dict) -> dict:
    client = _get_rest_client()
    if not client:
        return {}
    resp = client.post(f"/{table}", json=data)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else {}


def _rest_update(table: str, data: dict, filters: dict) -> list[dict]:
    client = _get_rest_client()
    if not client:
        return []
    resp = client.patch(f"/{table}", json=data, params=filters)
    resp.raise_for_status()
    return resp.json()


try:
    if SUPABASE_URL and SUPABASE_KEY:
        c = _get_rest_client()
        if c:
            resp = c.get("/freight_audits", params={"select": "id", "limit": 1})
            resp.raise_for_status()
            MOCK_MODE = False
            logger.info("[EDGE77 ENGINE] Supabase REST client initialized successfully")
    else:
        logger.warning(
            "[EDGE77 ENGINE] SUPABASE_URL or SUPABASE_KEY not set. "
            "Operating in MOCK MODE — all data is in-memory and will be lost on restart."
        )
except Exception as e:
    logger.warning(f"[EDGE77 ENGINE] Failed to initialize Supabase REST client: {e}. Operating in mock mode.")


MOCK_AUDITS: list[dict] = []
MOCK_CONTRACTS: dict[str, dict] = {
    "default": {
        "base_fee_per_shipment": 25.00,
        "dispute_fee_percentage": 0.25,
        "minimum_overcharge_to_dispute": 5.00,
        "dispute_mode": "MANUAL_GATE",
        "max_allowed_fuel": 0.0,
    }
}


def save_audit_record(data: dict) -> dict:
    try:
        if MOCK_MODE:
            existing = next(
                (a for a in MOCK_AUDITS if a.get("client_id") == data.get("client_id") and a.get("tracking_id") == data.get("tracking_id")),
                None,
            )
            if existing:
                existing.update(data)
                logger.info(f"[EDGE77 ENGINE] Mock updated audit record id={existing['id']}")
                return existing
            audit_id = len(MOCK_AUDITS) + 1
            record = {"id": audit_id, **data, "created_at": datetime.now(timezone.utc).isoformat()}
            MOCK_AUDITS.append(record)
            logger.info(f"[EDGE77 ENGINE] Mock saved audit record id={audit_id}")
            return record

        client_id = data.get("client_id")
        tracking_id = data.get("tracking_id")

        existing = _rest_select("freight_audits", {
            "select": "id",
            "client_id": f"eq.{client_id}",
            "tracking_id": f"eq.{tracking_id}",
            "limit": 1,
        })

        if existing:
            record_id = existing[0]["id"]
            update_data = {k: v for k, v in data.items() if k not in ("client_id", "tracking_id")}
            rows = _rest_update("freight_audits", update_data, {"id": f"eq.{record_id}"})
            record = rows[0] if rows else {"id": record_id, **data}
            logger.info(f"[EDGE77 ENGINE] Updated audit record id={record_id}")
            return record
        else:
            record = _rest_insert("freight_audits", data)
            logger.info(f"[EDGE77 ENGINE] Saved audit record id={record.get('id')}")
            return record
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to save audit record: {e}")
        return {}


def check_duplicate(client_id: str, tracking_id: str) -> bool:
    try:
        if MOCK_MODE:
            return any(
                a.get("client_id") == client_id and a.get("tracking_id") == tracking_id
                for a in MOCK_AUDITS
            )

        rows = _rest_select("freight_audits", {
            "select": "id",
            "client_id": f"eq.{client_id}",
            "tracking_id": f"eq.{tracking_id}",
            "limit": 1,
        })
        return len(rows) > 0
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to check duplicate: {e}")
        return False


def get_client_contract(client_id: str) -> dict:
    try:
        if MOCK_MODE:
            return MOCK_CONTRACTS.get(client_id, MOCK_CONTRACTS["default"])

        rows = _rest_select("client_contracts", {
            "select": "*",
            "client_id": f"eq.{client_id}",
            "limit": 1,
        })
        if rows:
            return rows[0]

        logger.info(f"[EDGE77 ENGINE] No contract found for client {client_id}, using defaults")
        return MOCK_CONTRACTS["default"]
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to fetch contract for {client_id}: {e}")
        return MOCK_CONTRACTS["default"]


def get_client_audits(
    client_id: str,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    try:
        if MOCK_MODE:
            filtered = [a for a in MOCK_AUDITS if a.get("client_id") == client_id]
            if status_filter:
                filtered = [a for a in filtered if a.get("status") == status_filter]
            return filtered[offset : offset + limit]

        params = {
            "select": "*",
            "client_id": f"eq.{client_id}",
            "order": "created_at.desc",
            "limit": limit,
            "offset": offset,
        }
        if status_filter:
            params["status"] = f"eq.{status_filter}"

        return _rest_select("freight_audits", params)
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to fetch audits for {client_id}: {e}")
        return []


def update_audit_status(
    audit_id: int, status: str, dispute_sent: bool = False
) -> dict:
    try:
        update_data = {
            "status": status,
            "dispute_sent": dispute_sent,
        }

        if MOCK_MODE:
            for audit in MOCK_AUDITS:
                if audit.get("id") == audit_id:
                    audit.update(update_data)
                    logger.info(f"[EDGE77 ENGINE] Mock updated audit {audit_id} to status={status}")
                    return audit
            return {}

        rows = _rest_update("freight_audits", update_data, {"id": f"eq.{audit_id}"})
        record = rows[0] if rows else {}
        logger.info(f"[EDGE77 ENGINE] Updated audit {audit_id} to status={status}")
        return record
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to update audit {audit_id}: {e}")
        return {}


def get_client_stats(client_id: str) -> dict:
    try:
        if MOCK_MODE:
            client_audits = [a for a in MOCK_AUDITS if a.get("client_id") == client_id]
            total = len(client_audits)
            overcharges = sum(1 for a in client_audits if a.get("overcharge_detected"))
            fees = sum(a.get("fee_earned", 0) for a in client_audits if a.get("fee_earned"))
            return {
                "total_audits": total,
                "overcharges_found": overcharges,
                "fees_earned": round(fees, 2),
            }

        rows = _rest_select("freight_audits", {
            "select": "id,overcharge_detected,fee_earned",
            "client_id": f"eq.{client_id}",
        })
        total = len(rows)
        overcharges = sum(1 for r in rows if r.get("overcharge_detected"))
        fees = sum(r.get("fee_earned", 0) or 0 for r in rows)

        return {
            "total_audits": total,
            "overcharges_found": overcharges,
            "fees_earned": round(fees, 2),
        }
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to compute stats for {client_id}: {e}")
        return {"total_audits": 0, "overcharges_found": 0, "fees_earned": 0.0}
