import time
import os
import httpx
from datetime import datetime, timezone
from typing import Any

LOG_PREFIX = "[EDGE77 ENGINE]"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

HEALTH_TIMEOUT_SECONDS = 5.0


def _measure_latency(func: Any, *args: Any, **kwargs: Any) -> tuple[dict, float]:
    """Execute a health check function and measure its latency.

    Returns:
        Tuple of (result_dict, latency_ms).
    """
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
    """Check Supabase connectivity by running a lightweight query.

    Returns:
        Dict with status and latency_ms keys.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {
            "status": "degraded",
            "latency_ms": 0.0,
            "error": "SUPABASE_URL or SUPABASE_KEY not configured",
        }

    try:
        from supabase import create_client

        start = time.monotonic()
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table("freight_audits").select("id").limit(1).execute()
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "latency_ms": 0.0,
            "error": str(exc),
        }


def check_openrouter_health() -> dict:
    """Check OpenRouter API availability via a lightweight models endpoint call.

    Returns:
        Dict with status and latency_ms keys.
    """
    if not OPENROUTER_API_KEY:
        return {
            "status": "degraded",
            "latency_ms": 0.0,
            "error": "OPENROUTER_API_KEY not configured",
        }

    try:
        start = time.monotonic()
        response = httpx.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=HEALTH_TIMEOUT_SECONDS,
        )
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        if response.status_code == 200:
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
            }
        elif response.status_code == 401:
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "error": "Invalid API key",
            }
        else:
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "error": f"HTTP {response.status_code}",
            }
    except httpx.TimeoutException:
        return {
            "status": "unhealthy",
            "latency_ms": 0.0,
            "error": "Request timed out",
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "latency_ms": 0.0,
            "error": str(exc),
        }


def get_system_health() -> dict:
    """Aggregate health checks for all dependent services.

    Returns:
        Dict containing overall status and individual service checks.
    """
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
    """Readiness probe - returns 200 if the service can handle requests.

    Returns:
        Dict with readiness status.
    """
    health = get_system_health()
    is_ready = health["status"] != "unhealthy"

    return {
        "ready": is_ready,
        "status": health["status"],
        "timestamp": health["timestamp"],
    }


def get_liveness_check() -> dict:
    """Liveness probe - always returns healthy if the process is running.

    Returns:
        Dict with liveness status.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "ok",
    }
