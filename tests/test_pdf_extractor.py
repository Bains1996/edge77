"""Tests for the PDF extraction module."""
import pytest
from v1_ingestion.pdf_extractor import validate_pdf, extract_text, ExtractedContent


def test_validate_pdf_rejects_empty():
    valid, error = validate_pdf(b"")
    assert valid is False
    assert "empty" in error.lower() or "size" in error.lower()


def test_validate_pdf_rejects_non_pdf():
    valid, error = validate_pdf(b"This is not a PDF file")
    assert valid is False
    assert "magic" in error.lower() or "pdf" in error.lower()


def test_validate_pdf_accepts_valid_header():
    # Minimal PDF header
    valid, error = validate_pdf(b"%PDF-1.4 fake content")
    assert valid is True


def test_extract_text_returns_content():
    # Test with minimal PDF bytes (will likely fail extraction but should return gracefully)
    result = extract_text(b"%PDF-1.4 minimal")
    assert isinstance(result, ExtractedContent)
    assert result.success is False  # Expected to fail with minimal bytes


def test_extracted_content_structure():
    result = ExtractedContent(
        raw_text="test",
        tables=[],
        page_count=0,
        extraction_method="test",
        success=True,
    )
    assert result.raw_text == "test"
    assert result.success is True
    assert result.error is None
