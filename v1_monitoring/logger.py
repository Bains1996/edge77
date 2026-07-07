import structlog
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

LOG_PREFIX = "[EDGE77 ENGINE]"


def setup_logging(level: str = "INFO"):
    """Configure structlog for JSON output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = "edge77") -> Any:
    """Return a configured structlog logger with the given name."""
    return structlog.get_logger(name)


def log_request(
    request: Any,
    response: Any,
    duration: float,
    logger: Optional[Any] = None,
) -> None:
    """Log an HTTP request/response pair with timing information.

    Args:
        request: The incoming request object (must have method, url attributes).
        response: The outgoing response object (must have status_code attribute).
        duration: Request duration in seconds.
        logger: Optional pre-configured logger instance.
    """
    log = logger or get_logger("edge77.request")

    request_method = getattr(request, "method", "UNKNOWN")
    request_url = str(getattr(request, "url", "UNKNOWN"))
    status_code = getattr(response, "status_code", 0)
    client_host = getattr(request, "client", None)
    client_ip = getattr(client_host, "host", "unknown") if client_host else "unknown"

    duration_ms = round(duration * 1000, 2)

    log_level = "info"
    if status_code >= 500:
        log_level = "error"
    elif status_code >= 400:
        log_level = "warning"

    log_event = {
        "event": f"{LOG_PREFIX} HTTP Request",
        "method": request_method,
        "url": request_url,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "client_ip": client_ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    log_fn = getattr(log, log_level, log.info)
    log_fn(**log_event)


class RequestLoggingMiddleware:
    """ASGI middleware for logging all HTTP requests with timing."""

    def __init__(self, app: Any, level: str = "INFO") -> None:
        self.app = app
        self.logger = get_logger("edge77.middleware")
        setup_logging(level)

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        start_time = time.monotonic()

        status_code = 0

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.monotonic() - start_time
            duration_ms = round(duration * 1000, 2)

            log_level = "info"
            if status_code >= 500:
                log_level = "error"
            elif status_code >= 400:
                log_level = "warning"

            log_fn = getattr(self.logger, log_level, self.logger.info)
            log_fn(
                event=f"{LOG_PREFIX} HTTP {method} {path}",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
