"""PDF extraction module for edge77 freight auditor.

Extracts text and tables from freight invoice PDFs using pdfplumber
with pypdf as fallback. Never crashes the pipeline.
"""

import io
import os
import logging
import tempfile
from dataclasses import dataclass, field

import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
PDF_MAGIC_BYTES = b"%PDF"
EDGE77_PREFIX = "[EDGE77 ENGINE]"


@dataclass
class ExtractedContent:
    raw_text: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)
    page_count: int = 0
    extraction_method: str = ""
    success: bool = False
    error: str | None = None


def validate_pdf(pdf_bytes: bytes) -> tuple[bool, str]:
    """Validate PDF magic bytes and file size."""
    if not pdf_bytes:
        return False, f"{EDGE77_PREFIX} PDF is empty (0 bytes)"

    if len(pdf_bytes) > MAX_FILE_SIZE:
        size_mb = len(pdf_bytes) / (1024 * 1024)
        return False, f"{EDGE77_PREFIX} PDF exceeds 20MB limit ({size_mb:.1f}MB)"

    header = pdf_bytes[:8]
    if not header.startswith(PDF_MAGIC_BYTES):
        return False, f"{EDGE77_PREFIX} Invalid PDF magic bytes: {header!r}"

    return True, ""


def _format_tables(tables: list) -> list[list[list[str]]]:
    """Clean up extracted tables — remove None/empty cells, strip whitespace."""
    formatted: list[list[list[str]]] = []
    for table in tables:
        if not table:
            continue
        clean_rows: list[list[str]] = []
        for row in table:
            if row is None:
                continue
            clean_row: list[str] = []
            for cell in row:
                if cell is None:
                    clean_row.append("")
                else:
                    clean_row.append(str(cell).strip())
            if any(cell for cell in clean_row):
                clean_rows.append(clean_row)
        if clean_rows:
            formatted.append(clean_rows)
    return formatted


def _extract_with_pdfplumber(pdf_bytes: bytes) -> ExtractedContent:
    """Primary extraction using pdfplumber."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        with pdfplumber.open(tmp_path) as pdf:
            pages = pdf.pages
            page_count = len(pages)
            text_parts: list[str] = []
            all_tables: list[list[list[str]]] = []

            for page in pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)

                try:
                    page_tables = page.extract_tables()
                    if page_tables:
                        all_tables.extend(_format_tables(page_tables))
                except Exception as table_err:
                    logger.warning(
                        f"{EDGE77_PREFIX} Table extraction failed on page: {table_err}"
                    )

            return ExtractedContent(
                raw_text="\n".join(text_parts).strip(),
                tables=all_tables,
                page_count=page_count,
                extraction_method="pdfplumber",
                success=True,
            )
    except Exception as e:
        raise RuntimeError(f"pdfplumber failed: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _extract_with_pypdf(pdf_bytes: bytes) -> ExtractedContent:
    """Fallback extraction using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ExtractedContent(
                    extraction_method="pypdf",
                    success=False,
                    error=f"{EDGE77_PREFIX} PDF is encrypted and could not be decrypted",
                )

        page_count = len(reader.pages)
        text_parts: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)

        return ExtractedContent(
            raw_text="\n".join(text_parts).strip(),
            tables=[],
            page_count=page_count,
            extraction_method="pypdf",
            success=True,
        )
    except Exception as e:
        raise RuntimeError(f"pypdf failed: {e}") from e


def _extract_with_ocr(pdf_bytes: bytes) -> ExtractedContent:
    """OCR extraction using Tesseract for scanned/image-based PDFs."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes, dpi=300)
        text_parts: list[str] = []

        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image, lang="eng")
            if page_text.strip():
                text_parts.append(page_text)

        return ExtractedContent(
            raw_text="\n".join(text_parts).strip(),
            tables=[],
            page_count=len(images),
            extraction_method="tesseract_ocr",
            success=True,
        )
    except ImportError:
        logger.warning(
            f"{EDGE77_PREFIX} pytesseract or pdf2image not installed — OCR unavailable"
        )
        return ExtractedContent(
            extraction_method="ocr",
            success=False,
            error=f"{EDGE77_PREFIX} OCR libraries not installed",
        )
    except Exception as e:
        raise RuntimeError(f"OCR extraction failed: {e}") from e


def extract_text(pdf_bytes: bytes) -> ExtractedContent:
    """Main entry point — extract text and tables from a PDF.

    Tries pdfplumber first, falls back to pypdf on failure.
    Never raises — always returns an ExtractedContent with error details.
    """
    valid, err_msg = validate_pdf(pdf_bytes)
    if not valid:
        logger.error(err_msg)
        return ExtractedContent(
            extraction_method="none",
            success=False,
            error=err_msg,
        )

    try:
        content = _extract_with_pdfplumber(pdf_bytes)
        logger.info(
            f"{EDGE77_PREFIX} pdfplumber extracted {content.page_count} pages, "
            f"{len(content.tables)} tables"
        )
        if content.raw_text.strip():
            return content
        logger.warning(f"{EDGE77_PREFIX} pdfplumber returned empty text — trying OCR")
    except Exception as plum_err:
        logger.warning(f"{EDGE77_PREFIX} pdfplumber failed, falling back to pypdf: {plum_err}")

    try:
        content = _extract_with_pypdf(pdf_bytes)
        logger.info(
            f"{EDGE77_PREFIX} pypdf extracted {content.page_count} pages (fallback)"
        )
        if content.raw_text.strip():
            return content
        logger.warning(f"{EDGE77_PREFIX} pypdf returned empty text — trying OCR")
    except Exception as pypdf_err:
        logger.warning(f"{EDGE77_PREFIX} pypdf failed: {pypdf_err}")

    try:
        content = _extract_with_ocr(pdf_bytes)
        if content.success and content.raw_text.strip():
            logger.info(
                f"{EDGE77_PREFIX} OCR extracted {content.page_count} pages"
            )
            return content
        logger.warning(f"{EDGE77_PREFIX} OCR returned no text")
    except Exception as ocr_err:
        logger.warning(f"{EDGE77_PREFIX} OCR failed: {ocr_err}")

    return ExtractedContent(
        extraction_method="none",
        success=False,
        error=f"{EDGE77_PREFIX} All extractors failed (pdfplumber, pypdf, OCR)",
    )
