import time
import os
import httpx
from datetime import datetime, timezone
from typing import Any

LOG_PREFIX = "[EDGE77 ENGINE]"

HEALTH_TIMEOUT_SECONDS = 5.0


def _supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def _supabase_key() -> str:
    return os.getenv("SUPABASE_KEY", "")


def _openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "")


def _openrouter_base_url() -> str:
    return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


def _measure_latency(func: Any, *args: Any, **kwargs: Any) -> tuple[dict, float]:
    start = time.monotonic()
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "status": "unhealthy",
            "latency_ms": latency_ms,
            "error": str(exc),
        }, latency_ms
    latency_ms = round((time.monotonic() - start) * 1000, 2)
    result["latency_ms"] = latency_ms
    return result, latency_ms


def check_supabase_health() -> dict:
    url = _supabase_url()
    key = _supabase_key()
    if not url or not key:
        return {
            "status": "degraded",
            "latency_ms": 0.0,
            "error": "SUPABASE_URL or SUPABASE_KEY not configured",
        }

    try:
        start = time.monotonic()
        resp = httpx.get(
            f"{url}/rest/v1/freight_audits",
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
            },
            params={"select": "id", "limit": 1},
            timeout=HEALTH_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except httpx.TimeoutException:
        return {"status": "unhealthy", "latency_ms": 0.0, "error": "Request timed out"}
    except Exception as exc:
        return {"status": "unhealthy", "latency_ms": 0.0, "error": str(exc)}


def check_openrouter_health() -> dict:
    api_key = _openrouter_api_key()
    if not api_key:
        return {
            "status": "degraded",
            "latency_ms": 0.0,
            "error": "OPENROUTER_API_KEY not configured",
        }

    try:
        start = time.monotonic()
        response = httpx.get(
            f"{_openrouter_base_url()}/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=HEALTH_TIMEOUT_SECONDS,
        )
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        if response.status_code == 200:
            return {"status": "healthy", "latency_ms": latency_ms}
        elif response.status_code == 401:
            return {"status": "unhealthy", "latency_ms": latency_ms, "error": "Invalid API key"}
        else:
            return {"status": "degraded", "latency_ms": latency_ms, "error": f"HTTP {response.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unhealthy", "latency_ms": 0.0, "error": "Request timed out"}
    except Exception as exc:
        return {"status": "unhealthy", "latency_ms": 0.0, "error": str(exc)}


def get_system_health() -> dict:
    supabase_result, _ = _measure_latency(check_supabase_health)
    openrouter_result, _ = _measure_latency(check_openrouter_health)

    checks = {
        "supabase": supabase_result,
        "openrouter": openrouter_result,
    }

    statuses = [check["status"] for check in checks.values()]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": checks,
    }


def get_readiness_check() -> dict:
    health = get_system_health()
    is_ready = health["status"] != "unhealthy"
    return {
        "ready": is_ready,
        "status": health["status"],
        "timestamp": health["timestamp"],
    }


def get_liveness_check() -> dict:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "ok",
    }
