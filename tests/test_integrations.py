"""Tests for integration routes: Samsara and Stripe."""
import os
from datetime import datetime, timezone

os.environ.setdefault("INTERNAL_API_TOKEN", "test_token_for_tests")
os.environ["MOCK_MODE"] = "true"

import pytest
from fastapi.testclient import TestClient

from v1_ingestion.main_gateway import app

client = TestClient(app)
TEST_TOKEN = "test_token_for_tests"


def _auth_headers():
    return {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "X-Timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Samsara Routes Tests ─────────────────────────────────────────────────

class TestSamsaraAuthEndpoint:
    def test_samsara_auth_requires_auth(self):
        """GET /v1/samsara/auth should require authentication."""
        resp = client.get("/v1/samsara/auth?client_id=test-client")
        assert resp.status_code == 401

    def test_samsara_auth_rejects_bad_token(self):
        resp = client.get(
            "/v1/samsara/auth?client_id=test-client",
            headers={"Authorization": "Bearer wrong_token"},
        )
        assert resp.status_code == 403

    def test_samsara_auth_missing_config(self):
        """When Samsara credentials are not set in env, should return 503."""
        resp = client.get(
            "/v1/samsara/auth?client_id=test-client",
            headers=_auth_headers(),
        )
        # Should fail because SAMSARA_CLIENT_ID etc are not set
        assert resp.status_code in (503, 502)


class TestSamsaraStatusEndpoint:
    def test_samsara_status_requires_auth(self):
        resp = client.get("/v1/samsara/status/test-client")
        assert resp.status_code == 401

    def test_samsara_status_not_connected(self):
        """Without Samsara credentials, status should report not connected."""
        resp = client.get(
            "/v1/samsara/status/test-client",
            headers=_auth_headers(),
        )
        # Should return "not connected" gracefully
        assert resp.status_code == 200
        data = resp.json()
        assert "connected" in data
        assert data["connected"] is False


class TestSamsaraCallbackEndpoint:
    def test_callback_requires_code_and_state(self):
        """GET /v1/samsara/callback without params should return 400."""
        resp = client.get("/v1/samsara/callback")
        assert resp.status_code == 400

    def test_callback_with_invalid_state(self):
        resp = client.get("/v1/samsara/callback?code=abc&state=invalid")
        assert resp.status_code == 400

    def test_callback_with_error(self):
        resp = client.get("/v1/samsara/callback?error=access_denied")
        assert resp.status_code == 400
        assert "access_denied" in resp.text


class TestSamsaraFleetEndpoint:
    def test_fleet_requires_auth(self):
        resp = client.get("/v1/samsara/fleet/test-client")
        assert resp.status_code == 401

    def test_fleet_not_connected(self):
        resp = client.get(
            "/v1/samsara/fleet/test-client",
            headers=_auth_headers(),
        )
        # Should return 404 since Samsara not connected for this client
        assert resp.status_code == 404


class TestSamsaraVehiclesEndpoint:
    def test_vehicles_requires_auth(self):
        resp = client.get("/v1/samsara/vehicles/test-client")
        assert resp.status_code == 401

    def test_vehicles_not_connected(self):
        resp = client.get(
            "/v1/samsara/vehicles/test-client",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404


class TestSamsaraDriversEndpoint:
    def test_drivers_requires_auth(self):
        resp = client.get("/v1/samsara/drivers/test-client")
        assert resp.status_code == 401

    def test_drivers_not_connected(self):
        resp = client.get(
            "/v1/samsara/drivers/test-client",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404


class TestSamsaraTripsEndpoint:
    def test_trips_requires_auth(self):
        resp = client.get("/v1/samsara/trips/test-client")
        assert resp.status_code == 401

    def test_trips_not_connected(self):
        resp = client.get(
            "/v1/samsara/trips/test-client",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404


class TestSamsaraMatchEndpoint:
    def test_match_requires_auth(self):
        resp = client.get("/v1/samsara/match/test-client")
        assert resp.status_code == 401

    def test_match_not_connected(self):
        resp = client.get(
            "/v1/samsara/match/test-client",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404


# ── Stripe Billing Routes Tests ─────────────────────────────────────────

class TestStripeCheckoutEndpoint:
    def test_checkout_requires_auth(self):
        resp = client.post("/v1/billing/checkout")
        assert resp.status_code == 401

    def test_checkout_rejects_bad_token(self):
        resp = client.post(
            "/v1/billing/checkout",
            headers={"Authorization": "Bearer wrong_token"},
            json={"client_id": "test", "tier": "starter"},
        )
        assert resp.status_code == 403

    def test_checkout_validates_tier(self):
        resp = client.post(
            "/v1/billing/checkout",
            headers=_auth_headers(),
            json={"client_id": "test-client", "tier": "nonexistent"},
        )
        assert resp.status_code == 400

    def test_checkout_missing_fields(self):
        resp = client.post(
            "/v1/billing/checkout",
            headers=_auth_headers(),
            json={},
        )
        assert resp.status_code == 422  # Validation error


class TestStripePortalEndpoint:
    def test_portal_requires_auth(self):
        resp = client.post("/v1/billing/portal")
        assert resp.status_code == 401

    def test_portal_no_billing_account(self):
        resp = client.post(
            "/v1/billing/portal",
            headers=_auth_headers(),
            json={"client_id": "nonexistent-client"},
        )
        assert resp.status_code == 404


class TestStripeUsageEndpoint:
    def test_usage_requires_auth(self):
        resp = client.post("/v1/billing/usage")
        assert resp.status_code == 401

    def test_usage_no_billing_account(self):
        resp = client.post(
            "/v1/billing/usage",
            headers=_auth_headers(),
            json={"client_id": "test-client", "event_type": "invoice_audited", "quantity": 1},
        )
        # Without billing data, should return skipped
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "skipped"


class TestStripeSubscriptionEndpoint:
    def test_subscription_requires_auth(self):
        resp = client.get("/v1/billing/subscription?client_id=test")
        assert resp.status_code == 401

    def test_subscription_no_subscription(self):
        resp = client.get(
            "/v1/billing/subscription?client_id=nonexistent-client",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "none"


class TestStripeInvoicesEndpoint:
    def test_invoices_requires_auth(self):
        resp = client.get("/v1/billing/invoices?client_id=test")
        assert resp.status_code == 401

    def test_invoices_no_billing_account(self):
        resp = client.get(
            "/v1/billing/invoices?client_id=nonexistent-client",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoices"] == []


class TestStripeWebhookEndpoint:
    def test_webhook_no_secret(self):
        """Without STRIPE_WEBHOOK_SECRET, webhook should return 500."""
        resp = client.post(
            "/v1/billing/webhook",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json", "stripe-signature": "test"},
        )
        assert resp.status_code == 500

    def test_webhook_invalid_payload(self):
        """Invalid JSON payload should return 400."""
        # Temporarily set webhook secret
        os.environ["STRIPE_WEBHOOK_SECRET"] = "test_whsec"
        try:
            resp = client.post(
                "/v1/billing/webhook",
                content=b"not-json",
                headers={"Content-Type": "application/json", "stripe-signature": "test"},
            )
            # Without valid signature, it will fail with 400
            assert resp.status_code in (400, 500)
        finally:
            del os.environ["STRIPE_WEBHOOK_SECRET"]
