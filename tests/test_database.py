"""Tests for database layer (supabase_client with MOCK_MODE)."""
import os
from datetime import datetime, timezone

# Force mock mode for tests
os.environ["MOCK_MODE"] = "true"

import pytest
from v1_database.supabase_client import (
    MOCK_MODE,
    MOCK_AUDITS,
    save_audit_record,
    check_duplicate,
    get_client_contract,
    get_client_audits,
    update_audit_status,
    get_client_stats,
)


@pytest.fixture(autouse=True)
def clear_mock_data():
    """Clear MOCK_AUDITS before each test so tests are isolated."""
    MOCK_AUDITS.clear()
    yield
    MOCK_AUDITS.clear()


# ── MOCK_MODE Configuration ──────────────────────────────────────────────

class TestMockMode:
    def test_mock_mode_enabled(self):
        assert MOCK_MODE is True


# ── save_audit_record Tests ──────────────────────────────────────────────

class TestSaveAuditRecord:
    def test_saves_new_record(self):
        data = {
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        }
        record = save_audit_record(data)
        assert record["id"] == 1
        assert record["tracking_id"] == "TRK-001"
        assert record["client_id"] == "client-1"
        assert "created_at" in record
        assert len(MOCK_AUDITS) == 1

    def test_updates_existing_record(self):
        data1 = {
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        }
        record1 = save_audit_record(data1)
        assert record1["id"] == 1

        data2 = {
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "PROCESSED",
        }
        record2 = save_audit_record(data2)
        # Should update existing, not create new
        assert record2["id"] == 1
        assert record2["status"] == "PROCESSED"
        assert len(MOCK_AUDITS) == 1  # Still only 1 record

    def test_saves_multiple_records(self):
        for i in range(3):
            save_audit_record({
                "client_id": "client-1",
                "tracking_id": f"TRK-{i:03d}",
                "status": "RECEIVED",
            })
        assert len(MOCK_AUDITS) == 3
        assert MOCK_AUDITS[0]["id"] == 1
        assert MOCK_AUDITS[2]["id"] == 3


# ── check_duplicate Tests ────────────────────────────────────────────────

class TestCheckDuplicate:
    def test_returns_false_for_new_record(self):
        assert check_duplicate("client-1", "TRK-001") is False

    def test_returns_true_for_existing_record(self):
        save_audit_record({
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        })
        assert check_duplicate("client-1", "TRK-001") is True

    def test_different_client_not_duplicate(self):
        save_audit_record({
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        })
        assert check_duplicate("client-2", "TRK-001") is False

    def test_different_tracking_not_duplicate(self):
        save_audit_record({
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        })
        assert check_duplicate("client-1", "TRK-999") is False


# ── get_client_contract Tests ────────────────────────────────────────────

class TestGetClientContract:
    def test_returns_default_for_unknown_client(self):
        contract = get_client_contract("unknown-client")
        assert contract["base_fee_per_shipment"] == 25.00
        assert contract["dispute_mode"] == "MANUAL_GATE"

    def test_returns_known_client_contract(self):
        from v1_database.supabase_client import MOCK_CONTRACTS
        MOCK_CONTRACTS["custom-client"] = {
            "base_fee_per_shipment": 10.00,
            "dispute_fee_percentage": 0.10,
            "minimum_overcharge_to_dispute": 1.00,
            "dispute_mode": "AUTONOMOUS",
            "max_allowed_fuel": 15.0,
        }
        contract = get_client_contract("custom-client")
        assert contract["base_fee_per_shipment"] == 10.00
        assert contract["dispute_mode"] == "AUTONOMOUS"
        assert contract["max_allowed_fuel"] == 15.0


# ── get_client_audits Tests ──────────────────────────────────────────────

class TestGetClientAudits:
    def test_returns_empty_for_new_client(self):
        audits = get_client_audits("client-1")
        assert audits == []

    def test_returns_client_audits_only(self):
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-001", "status": "PASS"})
        save_audit_record({"client_id": "client-2", "tracking_id": "TRK-002", "status": "PASS"})
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-003", "status": "FAIL"})

        audits = get_client_audits("client-1")
        assert len(audits) == 2
        assert all(a["client_id"] == "client-1" for a in audits)

    def test_filters_by_status(self):
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-001", "status": "PASS"})
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-002", "status": "FAIL"})
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-003", "status": "PASS"})

        audits = get_client_audits("client-1", status_filter="PASS")
        assert len(audits) == 2
        assert all(a["status"] == "PASS" for a in audits)

    def test_respects_limit(self):
        for i in range(5):
            save_audit_record({
                "client_id": "client-1",
                "tracking_id": f"TRK-{i:03d}",
                "status": "PASS",
            })
        audits = get_client_audits("client-1", limit=3)
        assert len(audits) == 3

    def test_respects_offset(self):
        for i in range(5):
            save_audit_record({
                "client_id": "client-1",
                "tracking_id": f"TRK-{i:03d}",
                "status": "PASS",
            })
        audits = get_client_audits("client-1", limit=10, offset=3)
        assert len(audits) == 2  # 5 total - 3 offset


# ── update_audit_status Tests ────────────────────────────────────────────

class TestUpdateAuditStatus:
    def test_updates_existing_audit(self):
        record = save_audit_record({
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        })
        result = update_audit_status(record["id"], "APPROVED")
        assert result["status"] == "APPROVED"
        assert result["dispute_sent"] is False

    def test_updates_with_dispute_flag(self):
        record = save_audit_record({
            "client_id": "client-1",
            "tracking_id": "TRK-001",
            "status": "RECEIVED",
        })
        result = update_audit_status(record["id"], "DISPUTE_SENT", dispute_sent=True)
        assert result["status"] == "DISPUTE_SENT"
        assert result["dispute_sent"] is True

    def test_returns_empty_for_nonexistent_audit(self):
        result = update_audit_status(99999, "APPROVED")
        assert result == {}


# ── get_client_stats Tests ────────────────────────────────────────────────

class TestGetClientStats:
    def test_returns_zeros_for_empty_client(self):
        stats = get_client_stats("client-1")
        assert stats == {"total_audits": 0, "overcharges_found": 0, "fees_earned": 0.0}

    def test_counts_audits(self):
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-001"})
        save_audit_record({"client_id": "client-1", "tracking_id": "TRK-002"})
        save_audit_record({"client_id": "client-2", "tracking_id": "TRK-003"})
        stats = get_client_stats("client-1")
        assert stats["total_audits"] == 2

    def test_counts_overcharges(self):
        save_audit_record({
            "client_id": "client-1", "tracking_id": "TRK-001",
            "overcharge_detected": True, "fee_earned": 15.0,
        })
        save_audit_record({
            "client_id": "client-1", "tracking_id": "TRK-002",
            "overcharge_detected": False, "fee_earned": 0.0,
        })
        stats = get_client_stats("client-1")
        assert stats["overcharges_found"] == 1
        assert stats["fees_earned"] == 15.0

    def test_sums_fees(self):
        save_audit_record({
            "client_id": "client-1", "tracking_id": "TRK-001",
            "overcharge_detected": True, "fee_earned": 10.50,
        })
        save_audit_record({
            "client_id": "client-1", "tracking_id": "TRK-002",
            "overcharge_detected": True, "fee_earned": 20.25,
        })
        stats = get_client_stats("client-1")
        assert stats["fees_earned"] == 30.75
