"""Stripe Billing Routes — Checkout, Portal, Webhooks.

Endpoints:
- POST /v1/billing/checkout   — Create Checkout session for self-serve signup
- POST /v1/billing/portal     — Create Customer Portal session
- POST /v1/billing/usage      — Report usage for metered billing
- POST /v1/billing/webhook    — Stripe webhook handler
- GET  /v1/billing/subscription — Get current subscription status
- GET  /v1/billing/invoices   — List invoices
"""

import os
import json
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from v1_integrations.stripe_client import (
    StripeClient,
    PRICING_TIERS,
    store_stripe_customer,
    get_stripe_customer,
    store_subscription,
    get_subscription,
    log_usage_event,
)
from v1_monitoring.logger import get_logger

log = get_logger("edge77.billing")

router = APIRouter(prefix="/v1/billing", tags=["billing"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://edge77.vercel.app")


# ── Request Models ───────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    client_id: str
    tier: str = "starter"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PortalRequest(BaseModel):
    client_id: str
    return_url: Optional[str] = None


class UsageRequest(BaseModel):
    client_id: str
    event_type: str = "invoice_audited"
    quantity: int = 1


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/checkout")
async def create_checkout(req: CheckoutRequest):
    """Create a Stripe Checkout session for self-serve subscription signup."""
    tier_config = PRICING_TIERS.get(req.tier)
    if not tier_config:
        raise HTTPException(400, f"Unknown tier: {req.tier}")

    price_id = tier_config.get("stripe_price_id", "")
    if not price_id:
        raise HTTPException(500, f"Stripe price ID not configured for tier: {req.tier}")

    stripe = StripeClient()

    # Get or create Stripe customer
    customer_data = get_stripe_customer(req.client_id)
    stripe_customer_id = None

    if customer_data:
        stripe_customer_id = customer_data.get("stripe_customer_id")
    else:
        # Create new customer — email will be set from client data
        customer = await stripe.create_customer(
            email=f"{req.client_id}@edge77.placeholder",
            metadata={"client_id": req.client_id, "source": "checkout"},
        )
        stripe_customer_id = customer["id"]
        store_stripe_customer(req.client_id, stripe_customer_id, "", req.tier)

    success_url = req.success_url or f"{FRONTEND_URL}/dashboard?upgraded=true"
    cancel_url = req.cancel_url or f"{FRONTEND_URL}/pricing"

    session = await stripe.create_checkout_session(
        customer_id=stripe_customer_id,
        price_id=price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        trial_days=14,
        metadata={"client_id": req.client_id, "tier": req.tier},
    )

    log.info(
        "checkout_session_created",
        client_id=req.client_id,
        tier=req.tier,
        session_id=session.get("id"),
    )

    return {
        "checkout_url": session.get("url"),
        "session_id": session.get("id"),
    }


@router.post("/portal")
async def create_portal(req: PortalRequest):
    """Create a Stripe Customer Portal session for managing billing."""
    customer_data = get_stripe_customer(req.client_id)
    if not customer_data:
        raise HTTPException(404, "No billing account found. Subscribe first.")

    stripe = StripeClient()
    return_url = req.return_url or f"{FRONTEND_URL}/dashboard"

    session = await stripe.create_billing_portal(
        customer_id=customer_data["stripe_customer_id"],
        return_url=return_url,
    )

    return {"portal_url": session.get("url")}


@router.post("/usage")
async def report_usage(req: UsageRequest):
    """Report usage for metered billing (called after each audit)."""
    customer_data = get_stripe_customer(req.client_id)
    if not customer_data:
        return {"status": "skipped", "reason": "no_billing_account"}

    sub_data = get_subscription(req.client_id)
    if not sub_data or sub_data.get("status") != "active":
        return {"status": "skipped", "reason": "no_active_subscription"}

    # Log usage event
    log_usage_event(req.client_id, req.event_type, req.quantity)

    log.info(
        "usage_reported",
        client_id=req.client_id,
        event_type=req.event_type,
        quantity=req.quantity,
    )

    return {
        "status": "recorded",
        "event_type": req.event_type,
        "quantity": req.quantity,
    }


@router.get("/subscription")
async def get_subscription_status(client_id: str):
    """Get current subscription status for a client."""
    customer_data = get_stripe_customer(req.client_id) if False else None
    sub_data = get_subscription(client_id)

    if not sub_data:
        return {
            "status": "none",
            "tier": None,
            "message": "No active subscription",
        }

    tier_config = PRICING_TIERS.get(sub_data.get("tier", "starter"), {})

    return {
        "status": sub_data.get("status", "unknown"),
        "tier": sub_data.get("tier"),
        "tier_name": tier_config.get("name", "Unknown"),
        "monthly_fee": tier_config.get("monthly_fee", 0),
        "contingency_fee_pct": tier_config.get("contingency_fee_pct", 0.15),
        "current_period_end": sub_data.get("current_period_end"),
    }


@router.get("/invoices")
async def list_invoices(client_id: str, limit: int = 25):
    """List invoices for a client."""
    customer_data = get_stripe_customer(client_id)
    if not customer_data:
        return {"invoices": []}

    stripe = StripeClient()
    invoices = await stripe.list_invoices(
        customer_data["stripe_customer_id"], limit=limit
    )

    return {
        "invoices": [
            {
                "id": inv.get("id"),
                "amount_paid": inv.get("amount_paid", 0) / 100,
                "currency": inv.get("currency", "usd"),
                "status": inv.get("status"),
                "created": inv.get("created"),
                "invoice_pdf": inv.get("invoice_pdf"),
            }
            for inv in invoices
        ]
    }


# ── Webhook Handler ──────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if STRIPE_WEBHOOK_SECRET:
        verified = StripeClient.verify_webhook_signature(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        if not verified:
            log.warning("stripe_webhook_signature_invalid")
            raise HTTPException(400, "Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid payload")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    log.info("stripe_webhook_received", event_type=event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "invoice.paid":
        await _handle_invoice_paid(data)
    elif event_type == "invoice.payment_failed":
        await _handle_invoice_failed(data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data)

    return {"received": True}


async def _handle_checkout_completed(data: dict) -> None:
    """Handle successful checkout — activate subscription."""
    client_id = data.get("metadata", {}).get("client_id")
    subscription_id = data.get("subscription")
    tier = data.get("metadata", {}).get("tier", "starter")

    if client_id and subscription_id:
        stripe = StripeClient()
        sub = await stripe.get_subscription(subscription_id)

        store_subscription(
            client_id=client_id,
            stripe_subscription_id=subscription_id,
            tier=tier,
            status=sub.get("status", "active"),
            current_period_end=_ts_to_iso(sub.get("current_period_end")),
        )
        log.info("checkout_activated", client_id=client_id, tier=tier)


async def _handle_invoice_paid(data: dict) -> None:
    """Handle successful payment."""
    customer_id = data.get("customer")
    amount = data.get("amount_paid", 0) / 100
    log.info("invoice_paid", customer_id=customer_id, amount=amount)


async def _handle_invoice_failed(data: dict) -> None:
    """Handle failed payment."""
    customer_id = data.get("customer")
    log.warning("invoice_payment_failed", customer_id=customer_id)


async def _handle_subscription_updated(data: dict) -> None:
    """Handle subscription update (plan change, renewal)."""
    sub_id = data.get("id")
    status = data.get("status")
    log.info("subscription_updated", subscription_id=sub_id, status=status)


async def _handle_subscription_deleted(data: dict) -> None:
    """Handle subscription cancellation."""
    sub_id = data.get("id")
    client_id = data.get("metadata", {}).get("client_id")
    log.info("subscription_cancelled", subscription_id=sub_id, client_id=client_id)


def _ts_to_iso(ts: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to ISO string."""
    if not ts:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
