"""EDGE77 Client API Key Management.

Handles creation, validation, and revocation of per-client API keys.
Keys are stored as SHA-512 hashes — plaintext is only shown once at creation.
"""

import os
import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("edge77")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

KEY_PREFIX = "e77_"
KEY_LENGTH = 32
HASH_ALGO = "sha512"


def _hash_key(raw_key: str) -> str:
    """Hash an API key using SHA-512."""
    return hashlib.sha512(raw_key.encode("utf-8")).hexdigest()


def generate_api_key(client_id: str, name: str = "default") -> dict:
    """Generate a new API key for a client.

    Returns dict with:
        - api_key: The plaintext key (ONLY shown once)
        - key_hash: The hashed key (stored in DB)
        - key_prefix: First 8 chars for identification
        - client_id: The client this key belongs to
    """
    raw_key = KEY_PREFIX + secrets.token_hex(KEY_LENGTH)
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:11] + "..."

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            resp = httpx.post(
                f"{SUPABASE_URL}/rest/v1/client_api_keys",
                json={
                    "client_id": client_id,
                    "key_hash": key_hash,
                    "key_prefix": key_prefix,
                    "name": name,
                    "active": True,
                },
                headers={
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info(f"[EDGE77] Generated API key for client {client_id}")
        except Exception as e:
            logger.error(f"[EDGE77] Failed to store API key: {e}")
            raise RuntimeError(f"Failed to store API key: {e}")

    return {
        "api_key": raw_key,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "client_id": client_id,
        "name": name,
    }


def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate an API key and return its metadata.

    Returns dict with client_id, key_prefix, etc. if valid, None otherwise.
    """
    if not api_key.startswith(KEY_PREFIX):
        return None

    key_hash = _hash_key(api_key)

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("[EDGE77] No Supabase configured, skipping API key validation")
        return None

    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/client_api_keys",
            params={
                "select": "client_id,key_prefix,name,active,rate_limit_per_minute",
                "key_hash": f"eq.{key_hash}",
                "active": "eq.true",
                "limit": 1,
            },
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        rows = resp.json()

        if not rows:
            return None

        key_data = rows[0]

        # Update last_used_at
        try:
            httpx.patch(
                f"{SUPABASE_URL}/rest/v1/client_api_keys",
                json={"last_used_at": datetime.now(timezone.utc).isoformat()},
                params={"key_hash": f"eq.{key_hash}"},
                headers={
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json",
                },
                timeout=5.0,
            )
        except Exception:
            pass  # Non-critical

        return key_data
    except Exception as e:
        logger.error(f"[EDGE77] API key validation failed: {e}")
        return None


def revoke_api_key(client_id: str, key_prefix: str) -> bool:
    """Revoke (deactivate) an API key."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    try:
        resp = httpx.patch(
            f"{SUPABASE_URL}/rest/v1/client_api_keys",
            json={"active": False},
            params={
                "client_id": f"eq.{client_id}",
                "key_prefix": f"like.{key_prefix}%",
            },
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY,
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"[EDGE77] Failed to revoke API key: {e}")
        return False
