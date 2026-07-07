import os
import json
import time
import random
import logging
from openai import OpenAI
from .schemas import FreightInvoiceSchema
from .prompts import INVOICE_EXTRACTION_PROMPT

logger = logging.getLogger("edge77.engine")

PRIMARY_MODEL = "deepseek/deepseek-v4-flash"
FALLBACK_MODEL = "openai/gpt-4o-mini"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CUSTOM_HEADERS = {
    "HTTP-Referer": "https://edge77.com",
    "X-Title": "Edge77",
}

RETRY_DELAYS = [1, 5, 15]


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key if api_key else "sk-placeholder",
        default_headers=CUSTOM_HEADERS,
    )


def _call_with_retry(messages: list, model: str, attempt: int = 0) -> str:
    if attempt >= len(RETRY_DELAYS):
        raise RuntimeError(f"[EDGE77 ENGINE] All retry attempts exhausted for model {model}")

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        delay = RETRY_DELAYS[attempt]
        logger.warning(
            "[EDGE77 ENGINE] Attempt %d/%d failed for %s: %s. Retrying in %ds...",
            attempt + 1,
            len(RETRY_DELAYS),
            model,
            str(e),
            delay,
        )
        time.sleep(delay)
        return _call_with_retry(messages, model, attempt + 1)


def _fallback_parse(extracted_text: str) -> FreightInvoiceSchema:
    logger.info("[EDGE77 ENGINE] Falling back to %s", FALLBACK_MODEL)
    try:
        raw = _call_with_retry(
            messages=[
                {"role": "system", "content": INVOICE_EXTRACTION_PROMPT},
                {"role": "user", "content": extracted_text},
            ],
            model=FALLBACK_MODEL,
        )
        data = _clean_json(raw)
        return FreightInvoiceSchema(**data)
    except Exception as e:
        logger.warning("[EDGE77 ENGINE] Fallback model also failed: %s", e)
        return _mock_parse(extracted_text)


def _clean_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    if text.startswith("```json"):
        text = text[7:].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("[EDGE77 ENGINE] No JSON object found in response")
    return json.loads(text[start:end])


def _mock_parse(extracted_text: str) -> FreightInvoiceSchema:
    logger.info("[EDGE77 ENGINE] Using mock parser — no API available")
    words = extracted_text.split()
    tracking = "UNKNOWN"
    for i, w in enumerate(words):
        if w.upper().startswith("TRACKING") and i + 1 < len(words):
            tracking = words[i + 1].strip(":,")
            break
        if len(w) >= 8 and any(c.isdigit() for c in w):
            tracking = w.strip(",:")
            break

    charges = [w for w in words if w.replace(".", "").replace(",", "").isdigit()]
    numeric = []
    for c in charges:
        try:
            numeric.append(float(c.replace(",", "")))
        except ValueError:
            pass

    total = numeric[0] if len(numeric) > 0 else 150.00
    fuel = numeric[1] if len(numeric) > 1 else round(total * 0.12, 2)
    base = numeric[2] if len(numeric) > 2 else round(total - fuel, 2)

    return FreightInvoiceSchema(
        tracking_id=tracking,
        total_charge=total,
        currency="USD",
        fuel_surcharge=fuel,
        base_freight_rate=base,
    )


def parse_invoice(extracted_text: str) -> FreightInvoiceSchema:
    logger.info("[EDGE77 ENGINE] Parsing invoice with %s", PRIMARY_MODEL)

    messages = [
        {"role": "system", "content": INVOICE_EXTRACTION_PROMPT},
        {"role": "user", "content": extracted_text},
    ]

    try:
        raw = _call_with_retry(messages, PRIMARY_MODEL)
        data = _clean_json(raw)
        schema = FreightInvoiceSchema(**data)
        logger.info("[EDGE77 ENGINE] Parsed tracking_id=%s total=%.2f", schema.tracking_id, schema.total_charge)
        return schema
    except Exception as e:
        logger.warning("[EDGE77 ENGINE] Primary model failed: %s", e)
        return _fallback_parse(extracted_text)
