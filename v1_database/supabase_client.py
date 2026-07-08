import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("edge77")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
MOCK_MODE = True

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        MOCK_MODE = False
        logger.info("[EDGE77 ENGINE] Supabase client initialized successfully")
    except Exception as e:
        logger.warning(f"[EDGE77 ENGINE] Failed to initialize Supabase: {e}. Operating in mock mode.")
else:
    logger.warning(
        "[EDGE77 ENGINE] SUPABASE_URL or SUPABASE_KEY not set. "
        "Operating in MOCK MODE — all data is in-memory and will be lost on restart. "
        "Set SUPABASE_URL and SUPABASE_KEY environment variables for production use."
    )


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

        existing = (
            supabase.table("freight_audits")
            .select("id")
            .eq("client_id", client_id)
            .eq("tracking_id", tracking_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            record_id = existing.data[0]["id"]
            update_data = {k: v for k, v in data.items() if k not in ("client_id", "tracking_id")}
            result = (
                supabase.table("freight_audits")
                .update(update_data)
                .eq("id", record_id)
                .execute()
            )
            record = result.data[0] if result.data else {"id": record_id, **data}
            logger.info(f"[EDGE77 ENGINE] Updated audit record id={record_id}")
            return record
        else:
            result = supabase.table("freight_audits").insert(data).execute()
            record = result.data[0] if result.data else {}
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

        result = (
            supabase.table("freight_audits")
            .select("id")
            .eq("client_id", client_id)
            .eq("tracking_id", tracking_id)
            .limit(1)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to check duplicate: {e}")
        return False


def get_client_contract(client_id: str) -> dict:
    try:
        if MOCK_MODE:
            return MOCK_CONTRACTS.get(client_id, MOCK_CONTRACTS["default"])

        result = (
            supabase.table("client_contracts")
            .select("*")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]

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

        query = (
            supabase.table("freight_audits")
            .select("*")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if status_filter:
            query = query.eq("status", status_filter)

        result = query.execute()
        return result.data or []
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

        result = (
            supabase.table("freight_audits")
            .update(update_data)
            .eq("id", audit_id)
            .execute()
        )
        record = result.data[0] if result.data else {}
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

        result = (
            supabase.table("freight_audits")
            .select("id, overcharge_detected, fee_earned")
            .eq("client_id", client_id)
            .execute()
        )
        rows = result.data or []
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
