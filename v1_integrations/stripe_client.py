"""Stripe Billing Integration — Subscriptions, Invoices, Metered Billing.

This module handles:
- Customer creation and management
- Subscription lifecycle (create, update, cancel)
- Metered billing for per-invoice fees
- Invoice generation and payment
- Webhook signature verification
"""

import os
import hmac
import hashlib
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

import httpx

from v1_monitoring.logger import get_logger

log = get_logger("edge77.stripe")

STRIPE_API_BASE = "https://api.stripe.com/v1"

# EDGE77 Pricing Tiers (15% contingency fee model)
PRICING_TIERS = {
    "starter": {
        "name": "Starter",
        "monthly_fee": 0,
        "contingency_fee_pct": 0.15,
        "included_audits": 50,
        "excess_audit_fee": 2.00,
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", ""),
    },
    "growth": {
        "name": "Growth",
        "monthly_fee": 499,
        "contingency_fee_pct": 0.12,
        "included_audits": 500,
        "excess_audit_fee": 1.50,
        "stripe_price_id": os.getenv("STRIPE_PRICE_GROWTH", ""),
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_fee": 2999,
        "contingency_fee_pct": 0.10,
        "included_audits": -1,  # unlimited
        "excess_audit_fee": 0,
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", ""),
    },
}


class StripeClient:
    """Client for Stripe API v1."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY", "")
        if not self.api_key:
            log.warning("stripe_api_key_missing")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def _post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated POST request to Stripe API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{STRIPE_API_BASE}{endpoint}",
                headers=self._headers(),
                data=data or {},
            )
            response.raise_for_status()
            return response.json()

    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated GET request to Stripe API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{STRIPE_API_BASE}{endpoint}",
                headers=self._headers(),
                params=params or {},
            )
            response.raise_for_status()
            return response.json()

    async def _del(self, endpoint: str) -> Dict[str, Any]:
        """Make authenticated DELETE request to Stripe API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{STRIPE_API_BASE}{endpoint}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    # ── Customer Management ──────────────────────────────────────────────

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe customer."""
        data: Dict[str, Any] = {"email": email}
        if name:
            data["name"] = name
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        customer = await self._post("/customers", data)
        log.info("stripe_customer_created", customer_id=customer["id"], email=email)
        return customer

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve a Stripe customer."""
        return await self._get(f"/customers/{customer_id}")

    async def update_customer(
        self, customer_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a Stripe customer."""
        return await self._post(f"/customers/{customer_id}", data)

    # ── Subscription Management ──────────────────────────────────────────

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a subscription for a customer."""
        data: Dict[str, Any] = {
            "customer": customer_id,
            "items[0][price]": price_id,
            "payment_behavior": "default_incomplete",
            "expand[]": "latest_invoice.payment_intent",
        }
        if trial_days:
            data["trial_period_days"] = trial_days
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        sub = await self._post("/subscriptions", data)
        log.info("stripe_subscription_created", subscription_id=sub["id"], customer_id=customer_id)
        return sub

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Retrieve a subscription."""
        return await self._get(f"/subscriptions/{subscription_id}")

    async def update_subscription(
        self, subscription_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a subscription (plan change, proration)."""
        return await self._post(f"/subscriptions/{subscription_id}", data)

    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription at period end."""
        return await self._del(f"/subscriptions/{subscription_id}")

    async def cancel_immediate(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription immediately."""
        return await self._post(
            f"/subscriptions/{subscription_id}",
            {"cancel_at_period_end": "false"},
        )

    async def list_subscriptions(self, customer_id: str) -> List[Dict[str, Any]]:
        """List all subscriptions for a customer."""
        result = await self._get(
            "/subscriptions", {"customer": customer_id, "status": "all"}
        )
        return result.get("data", [])

    # ── Metered Billing (Usage Records) ──────────────────────────────────

    async def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Report usage for metered billing."""
        data: Dict[str, Any] = {
            "quantity": quantity,
            "action": "increment",
        }
        if timestamp:
            data["timestamp"] = timestamp

        result = await self._post(
            f"/subscription_items/{subscription_item_id}/usage_records", data
        )
        log.info(
            "stripe_usage_reported",
            item_id=subscription_item_id,
            quantity=quantity,
        )
        return result

    # ── Invoice Management ───────────────────────────────────────────────

    async def create_invoice(
        self,
        customer_id: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a draft invoice."""
        data: Dict[str, Any] = {"customer": customer_id}
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        return await self._post("/invoices", data)

    async def add_invoice_item(
        self,
        invoice_id: str,
        amount_cents: int,
        currency: str = "usd",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Add a line item to a draft invoice."""
        data: Dict[str, Any] = {
            "invoice": invoice_id,
            "amount": amount_cents,
            "currency": currency,
        }
        if description:
            data["description"] = description
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        return await self._post("/invoiceitems", data)

    async def finalize_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Finalize a draft invoice for payment."""
        return await self._post(f"/invoices/{invoice_id}/finalize")

    async def send_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Send a finalized invoice to the customer."""
        return await self._post(f"/invoices/{invoice_id}/send")

    async def pay_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Attempt to pay an invoice."""
        return await self._post(f"/invoices/{invoice_id}/pay")

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve an invoice."""
        return await self._get(f"/invoices/{invoice_id}")

    async def list_invoices(
        self, customer_id: str, limit: int = 25
    ) -> List[Dict[str, Any]]:
        """List invoices for a customer."""
        result = await self._get(
            "/invoices", {"customer": customer_id, "limit": limit}
        )
        return result.get("data", [])

    # ── Checkout Sessions (Self-Serve Signup) ────────────────────────────

    async def create_checkout_session(
        self,
        customer_id: Optional[str],
        price_id: str,
        success_url: str,
        cancel_url: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for self-serve signup."""
        data: Dict[str, Any] = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": 1,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "subscription_data[trial_period_days]": trial_days or 14,
        }
        if customer_id:
            data["customer"] = customer_id
            data["customer_creation"] = "always"
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        return await self._post("/checkout/sessions", data)

    async def create_billing_portal(
        self, customer_id: str, return_url: str
    ) -> Dict[str, Any]:
        """Create a Stripe Customer Portal session for managing billing."""
        return await self._post(
            "/billing_portal/sessions",
            {"customer": customer_id, "return_url": return_url},
        )

    # ── Webhook Verification ─────────────────────────────────────────────

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        sig_header: str,
        webhook_secret: str,
        tolerance: int = 300,
    ) -> bool:
        """Verify Stripe webhook signature."""
        try:
            elements = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = int(elements["t"])
            signature = elements["v1"]

            # Check timestamp tolerance
            if abs(time.time() - timestamp) > tolerance:
                log.warning("stripe_webhook_timestamp_expired")
                return False

            # Compute expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected = hmac.new(
                webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(signature, expected)
        except Exception as e:
            log.error("stripe_webhook_verify_error", error=str(e))
            return False


# ── Database Helpers ─────────────────────────────────────────────────────

def store_stripe_customer(
    client_id: str,
    stripe_customer_id: str,
    email: str,
    tier: str = "starter",
) -> None:
    """Store Stripe customer mapping in Supabase."""
    from v1_database.supabase_client import MOCK_MODE, _rest_upsert

    if MOCK_MODE:
        log.info("stripe_customer_stored_mock", client_id=client_id)
        return

    try:
        _rest_upsert("stripe_customers", {
            "client_id": client_id,
            "stripe_customer_id": stripe_customer_id,
            "email": email,
            "tier": tier,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        log.info("stripe_customer_stored", client_id=client_id, tier=tier)
    except Exception as e:
        log.error("stripe_customer_store_failed", client_id=client_id, error=str(e))
        raise


def get_stripe_customer(client_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve Stripe customer for a client."""
    from v1_database.supabase_client import MOCK_MODE, _rest_select

    if MOCK_MODE:
        return None

    try:
        rows = _rest_select("stripe_customers", {
            "select": "*",
            "client_id": f"eq.{client_id}",
            "limit": 1,
        })
        return rows[0] if rows else None
    except Exception as e:
        log.error("stripe_customer_fetch_failed", client_id=client_id, error=str(e))
        return None


def store_subscription(
    client_id: str,
    stripe_subscription_id: str,
    tier: str,
    status: str,
    current_period_end: Optional[str] = None,
) -> None:
    """Store subscription info in Supabase."""
    from v1_database.supabase_client import MOCK_MODE, _rest_upsert

    if MOCK_MODE:
        log.info("subscription_stored_mock", client_id=client_id)
        return

    try:
        data = {
            "client_id": client_id,
            "stripe_subscription_id": stripe_subscription_id,
            "tier": tier,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if current_period_end:
            data["current_period_end"] = current_period_end

        _rest_upsert("subscriptions", data)
        log.info("subscription_stored", client_id=client_id, tier=tier, status=status)
    except Exception as e:
        log.error("subscription_store_failed", client_id=client_id, error=str(e))
        raise


def get_subscription(client_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve subscription for a client."""
    from v1_database.supabase_client import MOCK_MODE, _rest_select

    if MOCK_MODE:
        return None

    try:
        rows = _rest_select("subscriptions", {
            "select": "*",
            "client_id": f"eq.{client_id}",
            "limit": 1,
        })
        return rows[0] if rows else None
    except Exception as e:
        log.error("subscription_fetch_failed", client_id=client_id, error=str(e))
        return None


def log_usage_event(
    client_id: str,
    event_type: str,
    quantity: int = 1,
    metadata: Optional[Dict] = None,
) -> None:
    """Log a usage event for billing metering."""
    from v1_database.supabase_client import MOCK_MODE, _rest_insert

    if MOCK_MODE:
        log.info("usage_event_logged_mock", client_id=client_id, event_type=event_type)
        return

    try:
        _rest_insert("usage_events", {
            "client_id": client_id,
            "event_type": event_type,
            "quantity": quantity,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        log.error("usage_event_log_failed", client_id=client_id, error=str(e))
