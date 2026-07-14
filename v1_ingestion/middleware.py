import hmac
import hashlib
import time
import os
import uuid
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any, Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

LOG_PREFIX = "[EDGE77 ENGINE]"

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
HMAC_SECRET = os.getenv("HMAC_SECRET", "")


def verify_hmac_signature(
    payload: bytes,
    secret: str,
    signature: str,
    timestamp: str,
) -> bool:
    """Verify an HMAC-SHA256 signature against the payload and timestamp.

    The signed message format is: f"{timestamp}.{payload.decode('utf-8', errors='replace')}"

    Args:
        payload: The raw request body bytes.
        secret: The HMAC shared secret.
        signature: The expected hex-encoded HMAC signature.
        timestamp: The timestamp string used during signing.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not secret or not signature:
        return False

    message = f"{timestamp}.{payload.decode('utf-8', errors='replace')}"
    expected = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def validate_timestamp(timestamp: str, max_age: int = 300) -> bool:
    """Validate that a timestamp is within the allowed age window.

    Args:
        timestamp: ISO 8601 timestamp string to validate.
        max_age: Maximum allowed age in seconds (default 300 = 5 minutes).

    Returns:
        True if the timestamp is valid and within the age limit, False otherwise.
    """
    try:
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"
        request_time = datetime.fromisoformat(timestamp)
        now = datetime.now(timezone.utc)
        age_seconds = (now - request_time).total_seconds()
        return -30 <= age_seconds <= max_age
    except (ValueError, TypeError):
        return False


class RateLimiter:
    """Simple in-memory sliding window rate limiter.

    Tracks request counts per client ID using a fixed window approach.
    Expired entries are cleaned up on each check to prevent memory leaks.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, client_id: str, now: float) -> None:
        """Remove expired timestamps for a client."""
        cutoff = now - self.window_seconds
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > cutoff
        ]
        if not self._requests[client_id]:
            del self._requests[client_id]

    def check(self, client_id: str) -> bool:
        """Check if a client is within the rate limit.

        Args:
            client_id: Unique identifier for the client (e.g., IP or API key hash).

        Returns:
            True if the request is allowed, False if rate limited.
        """
        now = time.monotonic()
        self._cleanup(client_id, now)

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for a client in the current window."""
        now = time.monotonic()
        self._cleanup(client_id, now)
        return max(0, self.max_requests - len(self._requests[client_id]))

    def get_reset_seconds(self, client_id: str) -> float:
        """Get seconds until the oldest request in the window expires."""
        now = time.monotonic()
        self._cleanup(client_id, now)
        if not self._requests[client_id]:
            return 0.0
        oldest = self._requests[client_id][0]
        remaining = self.window_seconds - (now - oldest)
        return max(0.0, remaining)


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware for HMAC auth, timestamp validation, and rate limiting.

    Skips health check and docs endpoints. Applies:
    - HMAC-SHA256 signature verification
    - Timestamp freshness validation
    - Per-client rate limiting
    - Bearer token authentication
    """

    SKIP_PATHS: set[str] = {"/", "/dashboard", "/health", "/health/live", "/health/ready", "/v1/samsara/callback"}

    def __init__(
        self,
        app: Any,
        hmac_secret: Optional[str] = None,
        api_token: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        super().__init__(app)
        self.hmac_secret = hmac_secret or HMAC_SECRET
        self.api_token = api_token or INTERNAL_API_TOKEN
        self.rate_limiter = rate_limiter or RateLimiter()

    def _get_client_id(self, request: Request) -> str:
        """Extract a client identifier from the request for rate limiting."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process each incoming request through the auth pipeline."""
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:12]
        request.state.request_id = request_id

        if request.url.path in self.SKIP_PATHS:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        client_id = self._get_client_id(request)

        if not self.rate_limiter.check(client_id):
            remaining = self.rate_limiter.get_remaining(client_id)
            reset_seconds = self.rate_limiter.get_reset_seconds(client_id)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.rate_limiter.max_requests} requests per {self.rate_limiter.window_seconds}s",
                    "retry_after_seconds": round(reset_seconds, 1),
                },
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "Retry-After": str(int(reset_seconds)),
                },
            )

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header"},
                headers={"X-Request-ID": request_id},
            )

        token = auth_header[7:]

        # Check if it's a per-client API key (e77_ prefix)
        if token.startswith("e77_"):
            from v1_database.api_keys import validate_api_key
            key_data = validate_api_key(token)
            if not key_data:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Invalid or revoked API key"},
                )
            # Rate limit by API key hash, not just IP
            api_key_client_id = key_data["client_id"]
            if not self.rate_limiter.check(f"apikey:{api_key_client_id}"):
                remaining = self.rate_limiter.get_remaining(f"apikey:{api_key_client_id}")
                reset_seconds = self.rate_limiter.get_reset_seconds(f"apikey:{api_key_client_id}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "detail": f"Maximum {self.rate_limiter.max_requests} requests per {self.rate_limiter.window_seconds}s",
                        "retry_after_seconds": round(reset_seconds, 1),
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.rate_limiter.max_requests),
                        "X-RateLimit-Remaining": str(remaining),
                        "Retry-After": str(int(reset_seconds)),
                        "X-Request-ID": request_id,
                    },
                )
            request.state.client_id = api_key_client_id
            request.state.auth_type = "api_key"
            response = await call_next(request)
            remaining = self.rate_limiter.get_remaining(f"apikey:{api_key_client_id}")
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-Request-ID"] = request_id
            return response

        # Fall back to internal token auth
        if not self.api_token:
            return JSONResponse(
                status_code=500,
                content={"error": "INTERNAL_API_TOKEN not configured"},
                headers={"X-Request-ID": request_id},
            )

        if not hmac.compare_digest(token, self.api_token):
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API token"},
                headers={"X-Request-ID": request_id},
            )

        timestamp = request.headers.get("X-Timestamp", "")
        if not timestamp:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing X-Timestamp header"},
                headers={"X-Request-ID": request_id},
            )

        if not validate_timestamp(timestamp):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Request timestamp expired or invalid",
                    "detail": "Timestamp must be within the last 5 minutes",
                },
                headers={"X-Request-ID": request_id},
            )

        if self.hmac_secret:
            signature = request.headers.get("X-Signature", "")
            if not signature:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing X-Signature header"},
                    headers={"X-Request-ID": request_id},
                )

            body = await request.body()
            if not verify_hmac_signature(body, self.hmac_secret, signature, timestamp):
                return JSONResponse(
                    status_code=403,
                    content={"error": "Invalid HMAC signature"},
                    headers={"X-Request-ID": request_id},
                )

        request.state.auth_type = "internal_token"
        response = await call_next(request)
        remaining = self.rate_limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-Request-ID"] = request_id
        return response
