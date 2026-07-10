"""Tests for the API endpoints."""
import os
from datetime import datetime, timezone
os.environ.setdefault("INTERNAL_API_TOKEN", "test_token_for_tests")
os.environ["HMAC_SECRET"] = ""

from fastapi.testclient import TestClient
from v1_ingestion.main_gateway import app

client = TestClient(app)
TEST_TOKEN = "test_token_for_tests"


def _auth_headers():
    return {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "X-Timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_health_endpoint():
    """Test that health endpoint returns 200 and has expected structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "mode" in data


def test_health_reports_mode():
    """Test that health endpoint reports mock or production mode."""
    response = client.get("/health")
    data = response.json()
    assert data["mode"] in ("mock", "production")


def test_landing_page():
    """Test that landing page is served."""
    response = client.get("/")
    assert response.status_code == 200


def test_dashboard_page():
    """Test that dashboard page is served."""
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_ingest_requires_auth():
    """Test that ingest endpoint requires authentication."""
    response = client.post("/v1/invoice/ingest")
    assert response.status_code == 401


def test_ingest_rejects_bad_token():
    """Test that ingest endpoint rejects invalid tokens."""
    response = client.post(
        "/v1/invoice/ingest",
        headers={"Authorization": "Bearer wrong_token"},
    )
    assert response.status_code == 403


def test_get_contract():
    """Test that contract endpoint returns a contract."""
    response = client.get(
        "/v1/client/default/contract",
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert "contract" in data
    assert "client_id" in data


def test_approve_audit_missing():
    """Test that approve endpoint returns 404 for nonexistent audit."""
    response = client.post(
        "/v1/client/default/audits/99999/approve",
        headers=_auth_headers(),
    )
    assert response.status_code == 404
