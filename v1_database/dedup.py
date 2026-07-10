import hashlib
import logging
from datetime import datetime, timezone

from .supabase_client import MOCK_MODE, MOCK_AUDITS, _rest_select

logger = logging.getLogger("edge77")


def compute_pdf_hash(pdf_bytes: bytes) -> str:
    try:
        return hashlib.sha256(pdf_bytes).hexdigest()
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to compute PDF hash: {e}")
        return ""


def check_and_mark_duplicate(
    client_id: str, tracking_id: str, pdf_hash: str
) -> bool:
    try:
        if MOCK_MODE:
            for audit in MOCK_AUDITS:
                if (
                    audit.get("client_id") == client_id
                    and audit.get("tracking_id") == tracking_id
                    and audit.get("pdf_hash") == pdf_hash
                ):
                    logger.info(
                        f"[EDGE77 ENGINE] Duplicate detected (mock): client={client_id} tracking={tracking_id}"
                    )
                    return True
            return False

        rows = _rest_select("freight_audits", {
            "select": "id",
            "client_id": f"eq.{client_id}",
            "tracking_id": f"eq.{tracking_id}",
            "pdf_hash": f"eq.{pdf_hash}",
            "limit": 1,
        })
        is_dup = len(rows) > 0
        if is_dup:
            logger.info(
                f"[EDGE77 ENGINE] Duplicate detected: client={client_id} tracking={tracking_id}"
            )
        return is_dup
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to check duplicate: {e}")
        return False


def is_duplicate(client_id: str, pdf_hash: str) -> bool:
    try:
        if MOCK_MODE:
            return any(
                a.get("client_id") == client_id and a.get("pdf_hash") == pdf_hash
                for a in MOCK_AUDITS
            )

        rows = _rest_select("freight_audits", {
            "select": "id",
            "client_id": f"eq.{client_id}",
            "pdf_hash": f"eq.{pdf_hash}",
            "limit": 1,
        })
        return len(rows) > 0
    except Exception as e:
        logger.error(f"[EDGE77 ENGINE] Failed to check hash duplicate: {e}")
        return False
