import os
import re
import json
import asyncio
import logging
from openai import OpenAI
from .schemas import FreightInvoiceSchema
from .prompts import INVOICE_EXTRACTION_PROMPT

logger = logging.getLogger("edge77.engine")

PRIMARY_MODEL = "openrouter/free"
FALLBACK_MODEL = "openrouter/free"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

RETRY_DELAYS = [1, 3, 7]


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key if api_key else "sk-placeholder",
    )


async def _call_with_retry_async(messages: list, model: str, attempt: int = 0) -> str:
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
        await asyncio.sleep(delay)
        return await _call_with_retry_async(messages, model, attempt + 1)


def _fallback_parse(extracted_text: str) -> FreightInvoiceSchema:
    logger.info("[EDGE77 ENGINE] AI fallback failed, using enhanced mock parser")
    return _smart_parse(extracted_text)


def _clean_json(raw: str) -> dict:
    text = raw.strip()

    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("[EDGE77 ENGINE] No JSON object found in response")

    json_str = text[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json.loads(json_str)


def _smart_parse(extracted_text: str) -> FreightInvoiceSchema:
    logger.info("[EDGE77 ENGINE] Using smart regex parser on extracted text")
    text = extracted_text.upper()

    tracking = "UNKNOWN"
    tracking_match = re.search(r'(?:TRACKING|PRO)\s*(?:#|NUM|NUMBER|ID)?\s*[:\s]+([A-Z0-9\-]+)', text)
    if tracking_match:
        tracking = tracking_match.group(1)
    else:
        invoice_match = re.search(r'INVOICE\s*(?:#|NUM|NUMBER|ID)?\s*[:\s]+([A-Z0-9\-]+)', text)
        if invoice_match:
            tracking = invoice_match.group(1)

    total = 0.0
    fuel = 0.0
    base = 0.0

    total_match = re.search(r'(?:TOTAL\s*(?:CHARGE|AMOUNT|DUE)?)\s*[:\s]*\$?\s*([\d,]+\.?\d*)', text)
    if total_match:
        total = float(total_match.group(1).replace(',', ''))

    fuel_match = re.search(r'(?:FUEL\s*SURCHARGE)\s*[:\s]*\$?\s*([\d,]+\.?\d*)', text)
    if fuel_match:
        fuel = float(fuel_match.group(1).replace(',', ''))

    base_match = re.search(r'(?:LINEHAUL|BASE\s*(?:RATE|FREIGHT)?)\s*[:\s]*\$?\s*([\d,]+\.?\d*)', text)
    if base_match:
        base = float(base_match.group(1).replace(',', ''))

    if total == 0.0:
        all_numbers = re.findall(r'\$?\s*([\d,]+\.\d{2})\b', extracted_text)
        parsed = []
        for n in all_numbers:
            try:
                parsed.append(float(n.replace(',', '')))
            except ValueError:
                pass
        if parsed:
            total = max(parsed)

    if fuel == 0.0 and total > 0.0:
        fuel = round(total * 0.12, 2)
    if base == 0.0 and total > 0.0 and fuel > 0.0:
        base = round(total - fuel, 2)

    return FreightInvoiceSchema(
        tracking_id=tracking,
        total_charge=total if total > 0.0 else 0.0,
        currency="USD",
        fuel_surcharge=fuel,
        base_freight_rate=base,
    )


async def parse_invoice(extracted_text: str) -> FreightInvoiceSchema:
    logger.info("[EDGE77 ENGINE] Parsing invoice with %s", PRIMARY_MODEL)

    messages = [
        {"role": "system", "content": INVOICE_EXTRACTION_PROMPT},
        {"role": "user", "content": extracted_text},
    ]

    try:
        raw = await _call_with_retry_async(messages, PRIMARY_MODEL)
        data = _clean_json(raw)
        schema = FreightInvoiceSchema(**data)
        if schema.total_charge > 0:
            logger.info("[EDGE77 ENGINE] Parsed tracking_id=%s total=%.2f", schema.tracking_id, schema.total_charge)
            return schema
        logger.warning("[EDGE77 ENGINE] AI returned zero total, falling back to smart parser")
    except Exception as e:
        logger.warning("[EDGE77 ENGINE] Primary model failed: %s", e)

    return _smart_parse(extracted_text)
