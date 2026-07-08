"""Tests for the dispute engine."""
import pytest
from v1_automation.dispute_engine import _calculate_overcharge, _calculate_fee


def test_calculate_overcharge_no_violation():
    assert _calculate_overcharge(100.0, 150.0) == 0.0


def test_calculate_overcharge_with_violation():
    assert _calculate_overcharge(200.0, 150.0) == 50.0


def test_calculate_overcharge_exact_limit():
    assert _calculate_overcharge(150.0, 150.0) == 0.0


def test_calculate_overcharge_zero():
    assert _calculate_overcharge(0.0, 150.0) == 0.0


def test_calculate_fee_default_15_percent():
    assert _calculate_fee(100.0) == 15.0


def test_calculate_fee_custom_percentage():
    assert _calculate_fee(100.0, 0.20) == 20.0


def test_calculate_fee_zero():
    assert _calculate_fee(0.0) == 0.0


def test_calculate_fee_rounding():
    result = _calculate_fee(33.33)
    assert result == 5.0  # 33.33 * 0.15 = 4.9995 -> rounded
