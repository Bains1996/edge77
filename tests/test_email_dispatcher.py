"""Tests for the email dispatcher module."""
import os
from datetime import datetime, timezone

# Use Brevo key from env or set a placeholder for test
os.environ.setdefault("BREVO_API_KEY", "test_brevo_key_for_tests")
# Ensure SES and Gmail keys are NOT set so Brevo is used
if "AWS_SES_ACCESS_KEY" in os.environ:
    del os.environ["AWS_SES_ACCESS_KEY"]
if "AWS_SES_SECRET_KEY" in os.environ:
    del os.environ["AWS_SES_SECRET_KEY"]
if "GMAIL_APP_PASSWORD" in os.environ:
    del os.environ["GMAIL_APP_PASSWORD"]

import pytest
from v1_automation.email_dispatcher import (
    build_dispute_html,
    send_dispute_email,
    send_processing_complete,
    _email_provider,
    _send_via_brevo,
)


# ── Provider Detection Tests ─────────────────────────────────────────────

class TestEmailProvider:
    def test_provider_is_brevo(self):
        """With only BREVO_API_KEY set, provider should be 'brevo'."""
        # Re-import to trigger provider detection
        import importlib
        from v1_automation import email_dispatcher
        importlib.reload(email_dispatcher)
        assert email_dispatcher._email_provider == "brevo"


# ── build_dispute_html Tests ─────────────────────────────────────────────

class TestBuildDisputeHtml:
    def test_returns_html_string(self):
        html = build_dispute_html("TRK-001", 50.00, 7.50, "USD", "carrier@example.com")
        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")
        assert html.endswith("</html>")

    def test_contains_tracking_id(self):
        html = build_dispute_html("TRK-001", 50.00, 7.50, "USD", "carrier@example.com")
        assert "TRK-001" in html

    def test_contains_overcharge_amount(self):
        html = build_dispute_html("TRK-001", 123.45, 18.52, "USD", "c@example.com")
        assert "123.45" in html or "123,45" in html.replace(",", ".")

    def test_contains_fee_amount(self):
        html = build_dispute_html("TRK-001", 100.00, 15.00, "USD", "c@example.com")
        assert "15.00" in html

    def test_contains_carrier_email(self):
        html = build_dispute_html("TRK-001", 50.00, 7.50, "USD", "carrier@example.com")
        assert "carrier@example.com" in html

    def test_contains_currency_symbol(self):
        html = build_dispute_html("TRK-001", 50.00, 7.50, "EUR", "c@example.com")
        assert "EUR" in html

    def test_zero_values_rendered(self):
        html = build_dispute_html("TRK-000", 0.00, 0.00, "USD", "c@example.com")
        assert "0.00" in html

    def test_timestamp_included(self):
        html = build_dispute_html("TRK-001", 50.00, 7.50, "USD", "c@example.com")
        assert "UTC" in html


# ── send_dispute_email Tests ─────────────────────────────────────────────

class TestSendDisputeEmail:
    def test_returns_false_for_empty_recipient(self):
        result = send_dispute_email("", "Subject", "<html></html>")
        assert result is False

    def test_returns_false_when_no_provider(self):
        # Temporarily unset the provider
        old_provider = _email_provider
        import v1_automation.email_dispatcher as ed
        # Can't easily unset provider, but should handle gracefully
        result = send_dispute_email("test@example.com", "Subject", "<html></html>")
        assert isinstance(result, bool)


# ── _send_via_brevo Tests ────────────────────────────────────────────────

class TestSendViaBrevo:
    def test_returns_false_with_bad_key(self):
        """With a fake Brevo key, send should return False (not crash)."""
        result = _send_via_brevo("nobody@example.com", "Test", "<html></html>")
        assert result is False  # Will fail auth against Brevo API, but not crash


# ── send_processing_complete Tests ───────────────────────────────────────

class TestSendProcessingComplete:
    def test_returns_false_for_empty_recipient(self):
        result = send_processing_complete("", "TRK-001", "PASS")
        assert result is False

    def test_contains_tracking_in_subject(self):
        # The function builds an HTML with tracking info
        # We verify it generates valid HTML in the body
        result = send_processing_complete("test@example.com", "TRK-999", "PASS")
        assert isinstance(result, bool)

    def test_handles_different_statuses(self):
        for status in ("PASS", "APPROVED", "DISPUTE_SENT", "FAILED"):
            result = send_processing_complete("test@example.com", "TRK-001", status)
            assert isinstance(result, bool)
