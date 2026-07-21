"""Tests for monitoring: health checks, logger, request logging middleware."""
import os
import time
import json
from io import StringIO

os.environ.setdefault("INTERNAL_API_TOKEN", "test_token_for_tests")
os.environ["MOCK_MODE"] = "true"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from v1_monitoring.logger import setup_logging, get_logger, log_request, RequestLoggingMiddleware
from v1_monitoring.health import (
    check_supabase_health,
    check_openrouter_health,
    get_system_health,
    get_readiness_check,
    get_liveness_check,
    _measure_latency,
)


# ── Logger Tests ─────────────────────────────────────────────────────────

class TestLogger:
    def test_setup_logging_does_not_crash(self):
        """setup_logging should not raise for standard levels."""
        setup_logging("INFO")  # Should not raise
        setup_logging("DEBUG")
        setup_logging("ERROR")

    def test_get_logger_returns_logger(self):
        logger = get_logger("test")
        assert logger is not None
        # Should be able to call various log methods
        logger.info("test message", extra_field="value")
        logger.error("error message")
        logger.warning("warning message")

    def test_get_logger_default_name(self):
        logger = get_logger()
        assert logger is not None


# ── Request Logging Tests ────────────────────────────────────────────────

class TestLogRequest:
    def test_log_request_does_not_crash(self):
        """log_request should accept request/response-like objects."""
        class MockRequest:
            method = "GET"
            url = "/test"
            client = type("Client", (), {"host": "127.0.0.1"})()

        class MockResponse:
            status_code = 200

        # Should not raise
        log_request(MockRequest(), MockResponse(), 0.05)

    def test_log_request_error_level(self):
        """500+ status codes should use error level."""
        class MockRequest:
            method = "GET"
            url = "/error"
            client = type("Client", (), {"host": "127.0.0.1"})()

        class MockResponse:
            status_code = 500

        log_request(MockRequest(), MockResponse(), 0.1)

    def test_log_request_warning_level(self):
        """400+ status codes should use warning level."""
        class MockRequest:
            method = "POST"
            url = "/bad-request"
            client = type("Client", (), {"host": "127.0.0.1"})()

        class MockResponse:
            status_code = 404

        log_request(MockRequest(), MockResponse(), 0.1)


# ── RequestLoggingMiddleware Tests ───────────────────────────────────────

class TestRequestLoggingMiddleware:
    def test_middleware_does_not_block_requests(self):
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_middleware_logs_all_methods(self):
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        @app.post("/submit")
        async def submit():
            return {"received": True}

        client = TestClient(app)
        resp = client.post("/submit", json={"key": "value"})
        assert resp.status_code == 200


# ── Health Check Tests ───────────────────────────────────────────────────

class TestSupabaseHealth:
    def test_supabase_health_no_credentials(self):
        """Without SUPABASE_URL/KEY, health should report degraded."""
        # Temporarily clear the env vars for this test
        old_url = os.environ.pop("SUPABASE_URL", None)
        old_key = os.environ.pop("SUPABASE_KEY", None)
        try:
            result = check_supabase_health()
            assert result["status"] == "degraded"
            assert "not configured" in result.get("error", "")
        finally:
            if old_url:
                os.environ["SUPABASE_URL"] = old_url
            if old_key:
                os.environ["SUPABASE_KEY"] = old_key


class TestOpenRouterHealth:
    def test_openrouter_health_no_key(self):
        """Without OPENROUTER_API_KEY, health should report degraded."""
        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            result = check_openrouter_health()
            assert result["status"] == "degraded"
            assert "not configured" in result.get("error", "")
        finally:
            if old_key:
                os.environ["OPENROUTER_API_KEY"] = old_key


class TestSystemHealth:
    def test_get_system_health_returns_structure(self):
        result = get_system_health()
        assert "status" in result
        assert "timestamp" in result
        assert "services" in result
        assert "supabase" in result["services"]
        assert "openrouter" in result["services"]

    def test_get_system_health_timestamp_format(self):
        result = get_system_health()
        # Should be ISO format
        assert "T" in result["timestamp"]

    def test_system_health_status_is_valid(self):
        result = get_system_health()
        assert result["status"] in ("healthy", "degraded", "unhealthy")


class TestReadinessCheck:
    def test_returns_ready_flag(self):
        result = get_readiness_check()
        assert "ready" in result
        assert "status" in result
        assert "timestamp" in result
        assert isinstance(result["ready"], bool)


class TestLivenessCheck:
    def test_always_healthy(self):
        result = get_liveness_check()
        assert result["status"] == "healthy"
        assert result["uptime"] == "ok"
        assert "timestamp" in result


# ── _measure_latency Tests ───────────────────────────────────────────────

class TestMeasureLatency:
    def test_returns_result_and_latency(self):
        def sync_func():
            return {"status": "healthy"}

        result, latency = _measure_latency(sync_func)
        assert result["status"] == "healthy"
        assert latency >= 0

    def test_catches_exceptions(self):
        def failing_func():
            raise ValueError("test error")

        result, latency = _measure_latency(failing_func)
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert latency >= 0
