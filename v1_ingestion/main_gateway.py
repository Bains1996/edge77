"""EDGE77 Freight Auditor — Main API Gateway.

Central FastAPI application that ties together ingestion, AI parsing,
dispute automation, database, and monitoring. Serves the workspace UI
and exposes the v1 REST API.
"""

import os
import uuid
import time
import hmac
import hashlib
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import structlog
from fastapi import FastAPI, UploadFile, File, Header, Query, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from v1_monitoring.logger import setup_logging, get_logger, RequestLoggingMiddleware
from v1_ingestion.middleware import AuthMiddleware, RateLimiter
from v1_database.supabase_client import (
    save_audit_record,
    check_duplicate,
    get_client_audits,
    get_client_stats,
    get_client_contract,
    update_audit_status,
    MOCK_MODE,
)
from v1_database.dedup import compute_pdf_hash, is_duplicate
from v1_ingestion.pdf_extractor import validate_pdf, extract_text
from v1_ai_brain.schemas import FreightInvoiceSchema
from v1_automation.dispute_engine import evaluate_and_dispute

LOG_PREFIX = "[EDGE77 ENGINE]"
BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
if not PUBLIC_DIR.exists():
    PUBLIC_DIR = Path.cwd() / "public"
if not PUBLIC_DIR.exists():
    PUBLIC_DIR = Path(__file__).resolve().parent / "public"
if not PUBLIC_DIR.exists():
    PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "20"))
MAX_PDF_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

setup_logging(LOG_LEVEL)
log = get_logger("edge77.gateway")


# ---------------------------------------------------------------------------
# Background processing pipeline
# ---------------------------------------------------------------------------

async def process_invoice_background(
    pdf_bytes: bytes,
    client_id: str,
    tracking_id: str,
    pdf_hash: str,
) -> None:
    """Full audit pipeline executed off the request path.

    Steps:
      1. Extract text from PDF
      2. Parse with AI via OpenRouter
      3. Evaluate overcharge and optionally send dispute
    """
    import sys
    print(f"{LOG_PREFIX} Background pipeline STARTED for tracking_id={tracking_id}", file=sys.stderr, flush=True)
    try:
        log.info(
            f"{LOG_PREFIX} Background pipeline started",
            tracking_id=tracking_id,
            client_id=client_id,
        )

        # 1. Extract text from PDF
        print(f"{LOG_PREFIX} STEP1: Extracting text from {len(pdf_bytes)} bytes", file=sys.stderr, flush=True)
        extracted = extract_text(pdf_bytes)
        print(f"{LOG_PREFIX} STEP1 result: success={extracted.success}", file=sys.stderr, flush=True)
        if not extracted.success:
            log.error(
                f"{LOG_PREFIX} PDF extraction failed",
                tracking_id=tracking_id,
                error=extracted.error,
            )
            update_audit_status_by_tracking(client_id, tracking_id, "EXTRACTION_FAILED")
            return

        log.info(
            f"{LOG_PREFIX} PDF text extracted",
            tracking_id=tracking_id,
            pages=extracted.page_count,
            method=extracted.extraction_method,
        )

        # 2. Parse with AI
        print(f"{LOG_PREFIX} STEP2: Parsing with AI, text_len={len(extracted.raw_text)}", file=sys.stderr, flush=True)
        parsed: FreightInvoiceSchema = await parse_invoice(extracted.raw_text)
        print(f"{LOG_PREFIX} STEP2 result: parsed OK, total={parsed.total_charge}", file=sys.stderr, flush=True)

        log.info(
            f"{LOG_PREFIX} AI parse complete",
            tracking_id=tracking_id,
            parsed_tracking=parsed.tracking_id,
            total_charge=parsed.total_charge,
        )

        # 3. Evaluate and dispute
        print(f"{LOG_PREFIX} STEP3: Evaluating overcharge", file=sys.stderr, flush=True)
        result = evaluate_and_dispute(parsed.model_dump(), client_id)
        print(f"{LOG_PREFIX} STEP3 result: overcharge={result.overcharge}, fee={result.fee_earned}", file=sys.stderr, flush=True)

        log.info(
            f"{LOG_PREFIX} Pipeline complete",
            tracking_id=tracking_id,
            overcharge=result.overcharge,
            fee=result.fee_earned,
            status=result.status,
        )

    except Exception as exc:
        log.error(
            f"{LOG_PREFIX} Background pipeline failed",
            tracking_id=tracking_id,
            error=str(exc),
            exc_info=True,
        )
        print(f"{LOG_PREFIX} PIPELINE FAILED: {exc}", file=sys.stderr, flush=True)
        try:
            update_audit_status_by_tracking(client_id, tracking_id, "PIPELINE_FAILED")
        except Exception:
            pass


async def parse_invoice(extracted_text: str) -> FreightInvoiceSchema:
    """Import and invoke the OpenRouter parser."""
    from v1_ai_brain.openrouter_parser import parse_invoice as _parse
    return await _parse(extracted_text)


BACKGROUND_TASK_TIMEOUT = int(os.getenv("BACKGROUND_TASK_TIMEOUT", "120"))


async def _process_with_timeout(
    pdf_bytes: bytes,
    client_id: str,
    tracking_id: str,
    pdf_hash: str,
) -> None:
    """Wrapper that enforces a timeout on the background pipeline."""
    import asyncio
    try:
        await asyncio.wait_for(
            process_invoice_background(pdf_bytes, client_id, tracking_id, pdf_hash),
            timeout=BACKGROUND_TASK_TIMEOUT,
        )
    except asyncio.TimeoutError:
        log.error(f"{LOG_PREFIX} Background pipeline timed out after {BACKGROUND_TASK_TIMEOUT}s", tracking_id=tracking_id)
        update_audit_status_by_tracking(client_id, tracking_id, "PIPELINE_TIMEOUT")


def update_audit_status_by_tracking(client_id: str, tracking_id: str, status: str) -> None:
    """Find an audit record by tracking_id and update its status."""
    from v1_database.supabase_client import MOCK_AUDITS, MOCK_MODE, _rest_select

    if MOCK_MODE:
        for audit in MOCK_AUDITS:
            if audit.get("client_id") == client_id and audit.get("tracking_id") == tracking_id:
                audit["status"] = status
                return
        return

    try:
        rows = _rest_select("freight_audits", {
            "select": "id",
            "client_id": f"eq.{client_id}",
            "tracking_id": f"eq.{tracking_id}",
            "limit": 1,
        })
        if rows:
            update_audit_status(rows[0]["id"], status)
    except Exception as exc:
        log.error(f"{LOG_PREFIX} Failed to update audit status: {exc}")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _verify_token(authorization: Optional[str]) -> str:
    """Extract and validate the Bearer token. Returns client_id or raises."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]

    # Check if it's a per-client API key (e77_ prefix)
    if token.startswith("e77_"):
        from v1_database.api_keys import validate_api_key
        key_data = validate_api_key(token)
        if not key_data:
            raise HTTPException(status_code=403, detail="Invalid or revoked API key")
        return key_data["client_id"]

    # Fall back to internal token (admin access)
    if not INTERNAL_API_TOKEN:
        raise HTTPException(status_code=500, detail="INTERNAL_API_TOKEN not configured")
    if not hmac.compare_digest(token, INTERNAL_API_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid API token")
    return "__admin__"


# ---------------------------------------------------------------------------
# Lifespan / startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"{LOG_PREFIX} Gateway starting — mode={'MOCK' if MOCK_MODE else 'PRODUCTION'}")
    log.info(f"{LOG_PREFIX} Rate limit: {RATE_LIMIT_PER_MINUTE} req/min")
    log.info(f"{LOG_PREFIX} Max PDF size: {MAX_PDF_SIZE_MB}MB")
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    yield
    log.info(f"{LOG_PREFIX} Gateway shutting down")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

_is_production = os.getenv("ENVIRONMENT", "development") == "production"

app = FastAPI(
    title="EDGE77 Freight Auditor Gateway",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    openapi_url=None if _is_production else "/openapi.json",
)

# --- Middleware (order matters: last added = first executed) ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://edge77-yyqrijv53a-uc.a.run.app",
        "https://edge77.axalglobal.com",
        "https://edge77-364995933969.us-central1.run.app",
    ] if _is_production else [
        "https://edge77-yyqrijv53a-uc.a.run.app",
        "https://edge77.axalglobal.com",
        "https://edge77-364995933969.us-central1.run.app",
        "http://localhost:8000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)

rate_limiter = RateLimiter(max_requests=RATE_LIMIT_PER_MINUTE, window_seconds=60)

app.add_middleware(
    AuthMiddleware,
    rate_limiter=rate_limiter,
)

app.add_middleware(
    RequestLoggingMiddleware,
    level=LOG_LEVEL,
)

# --- Integration routes ---
from v1_integrations.samsara_routes import router as samsara_router
from v1_integrations.stripe_routes import router as stripe_router
app.include_router(samsara_router)
app.include_router(stripe_router)


# ---------------------------------------------------------------------------
# Static files & pages
# ---------------------------------------------------------------------------

if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_landing():
    index = PUBLIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Freight Auditor</h1><p>Landing page not found. Place <code>public/index.html</code> in the project root.</p>",
        status_code=200,
    )


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    dashboard = PUBLIC_DIR / "dashboard.html"
    if dashboard.exists():
        return FileResponse(str(dashboard), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Dashboard</h1><p>Dashboard not found. Place <code>public/dashboard.html</code> in the project root.</p>",
        status_code=200,
    )


@app.get("/pricing", response_class=HTMLResponse, include_in_schema=False)
async def serve_pricing():
    page = PUBLIC_DIR / "pricing.html"
    if page.exists():
        return FileResponse(str(page), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Pricing</h1><p>Pricing page not found. Place <code>public/pricing.html</code> in the project root.</p>",
        status_code=200,
    )


@app.get("/terms", response_class=HTMLResponse, include_in_schema=False)
async def serve_terms():
    page = PUBLIC_DIR / "terms.html"
    if page.exists():
        return FileResponse(str(page), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Terms of Service</h1><p>Terms page not found. Place <code>public/terms.html</code> in the project root.</p>",
        status_code=200,
    )


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def serve_privacy():
    page = PUBLIC_DIR / "privacy.html"
    if page.exists():
        return FileResponse(str(page), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Privacy Policy</h1><p>Privacy page not found. Place <code>public/privacy.html</code> in the project root.</p>",
        status_code=200,
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def serve_login():
    page = PUBLIC_DIR / "login.html"
    if page.exists():
        return FileResponse(str(page), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Login</h1><p>Login page not found. Place <code>public/login.html</code> in the project root.</p>",
        status_code=200,
    )


@app.get("/signup", response_class=HTMLResponse, include_in_schema=False)
async def serve_signup():
    page = PUBLIC_DIR / "signup.html"
    if page.exists():
        return FileResponse(str(page), media_type="text/html")
    return HTMLResponse(
        content="<h1>EDGE77 Sign Up</h1><p>Signup page not found. Place <code>public/signup.html</code> in the project root.</p>",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    checks = {
        "supabase": "skip",
        "openrouter": "skip",
    }

    if not MOCK_MODE:
        try:
            from v1_database.supabase_client import _async_rest_select
            await _async_rest_select("freight_audits", {"select": "id", "limit": 1})
            checks["supabase"] = "ok"
        except Exception as e:
            checks["supabase"] = f"error: {str(e)[:100]}"

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        checks["openrouter"] = "configured"
    else:
        checks["openrouter"] = "not_configured"

    unhealthy = [k for k, v in checks.items() if v.startswith("error")]

    return {
        "status": "healthy" if not unhealthy else "degraded",
        "service": "edge77-gateway",
        "mode": "mock" if MOCK_MODE else "production",
        "checks": checks,
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# POST /v1/invoice/ingest
# ---------------------------------------------------------------------------

@app.post("/v1/invoice/ingest")
async def ingest_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_client_id: Optional[str] = Header(None, alias="x-client-id"),
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)

    if not x_client_id:
        raise HTTPException(status_code=422, detail="x-client-id header is required")

    if not file.filename:
        raise HTTPException(status_code=422, detail="No file provided")

    lower_name = file.filename.lower()
    if not lower_name.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()

    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(pdf_bytes) > MAX_PDF_BYTES:
        size_mb = len(pdf_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_PDF_SIZE_MB}MB limit ({size_mb:.1f}MB)",
        )

    valid, err_msg = validate_pdf(pdf_bytes)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg.replace(f"{LOG_PREFIX} ", ""))

    tracking_id = str(uuid.uuid4())
    pdf_hash = compute_pdf_hash(pdf_bytes)

    if is_duplicate(x_client_id, pdf_hash):
        log.info(f"{LOG_PREFIX} Duplicate PDF rejected", client_id=x_client_id, pdf_hash=pdf_hash[:16])
        raise HTTPException(status_code=409, detail="Duplicate PDF — this file has already been processed")

    audit_record = save_audit_record({
        "client_id": x_client_id,
        "tracking_id": tracking_id,
        "pdf_hash": pdf_hash,
        "filename": file.filename,
        "file_size": len(pdf_bytes),
        "status": "RECEIVED",
    })

    background_tasks.add_task(
        _process_with_timeout,
        pdf_bytes=pdf_bytes,
        client_id=x_client_id,
        tracking_id=tracking_id,
        pdf_hash=pdf_hash,
    )

    log.info(
        f"{LOG_PREFIX} Invoice accepted",
        tracking_id=tracking_id,
        client_id=x_client_id,
        filename=file.filename,
        size_bytes=len(pdf_bytes),
    )

    return {
        "status": "success",
        "tracking_id": tracking_id,
        "message": "Invoice received and queued for processing",
    }


# ---------------------------------------------------------------------------
# GET /v1/invoice/{tracking_id}/status
# ---------------------------------------------------------------------------

@app.get("/v1/invoice/{tracking_id}/status")
async def get_invoice_status(
    tracking_id: str,
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)

    from v1_database.supabase_client import MOCK_AUDITS, _rest_select

    if MOCK_MODE:
        record = next(
            (a for a in MOCK_AUDITS if a.get("tracking_id") == tracking_id),
            None,
        )
    else:
        try:
            rows = _rest_select("freight_audits", {
                "select": "*",
                "tracking_id": f"eq.{tracking_id}",
                "limit": 1,
            })
            record = rows[0] if rows else None
        except Exception as exc:
            log.error(f"{LOG_PREFIX} Status lookup failed: {exc}")
            raise HTTPException(status_code=500, detail="Failed to query audit status")

    if not record:
        raise HTTPException(status_code=404, detail=f"No audit found for tracking_id={tracking_id}")

    return record


# ---------------------------------------------------------------------------
# GET /v1/client/{client_id}/audits
# ---------------------------------------------------------------------------

@app.get("/v1/client/{client_id}/audits")
async def list_client_audits(
    client_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)

    audits = get_client_audits(client_id, status_filter=status, limit=limit, offset=offset)

    log.info(
        f"{LOG_PREFIX} Fetched audits",
        client_id=client_id,
        count=len(audits),
        status_filter=status,
    )

    return {
        "client_id": client_id,
        "count": len(audits),
        "offset": offset,
        "limit": limit,
        "audits": audits,
    }


# ---------------------------------------------------------------------------
# GET /v1/client/{client_id}/stats
# ---------------------------------------------------------------------------

@app.get("/v1/client/{client_id}/stats")
async def client_stats(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)

    stats = get_client_stats(client_id)

    log.info(f"{LOG_PREFIX} Fetched stats", client_id=client_id, stats=stats)

    return {
        "client_id": client_id,
        **stats,
    }


# ---------------------------------------------------------------------------
# GET /v1/client/{client_id}/contract
# ---------------------------------------------------------------------------

@app.get("/v1/client/{client_id}/contract")
async def get_contract(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)
    contract = get_client_contract(client_id)
    log.info(f"{LOG_PREFIX} Fetched contract", client_id=client_id)
    return {
        "client_id": client_id,
        "contract": contract,
    }


# ---------------------------------------------------------------------------
# POST /v1/client/{client_id}/contract
# ---------------------------------------------------------------------------

@app.post("/v1/client/{client_id}/contract")
async def update_contract(
    client_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    max_allowed_fuel = body.get("max_allowed_fuel")
    carrier_billing_email = body.get("carrier_billing_email")
    dispute_mode = body.get("dispute_mode")

    if max_allowed_fuel is not None and not isinstance(max_allowed_fuel, (int, float)):
        raise HTTPException(status_code=422, detail="max_allowed_fuel must be a number")
    if dispute_mode is not None and dispute_mode not in ("AUTONOMOUS", "MANUAL_GATE"):
        raise HTTPException(status_code=422, detail="dispute_mode must be AUTONOMOUS or MANUAL_GATE")

    from v1_database.supabase_client import MOCK_CONTRACTS, _rest_select, _rest_insert, _rest_update

    if MOCK_MODE:
        existing = MOCK_CONTRACTS.get(client_id, MOCK_CONTRACTS["default"].copy())
        if max_allowed_fuel is not None:
            existing["max_allowed_fuel"] = max_allowed_fuel
        if carrier_billing_email is not None:
            existing["carrier_billing_email"] = carrier_billing_email
        if dispute_mode is not None:
            existing["dispute_mode"] = dispute_mode
        MOCK_CONTRACTS[client_id] = existing
        contract = existing
    else:
        try:
            update_data = {}
            if max_allowed_fuel is not None:
                update_data["max_allowed_fuel"] = max_allowed_fuel
            if carrier_billing_email is not None:
                update_data["carrier_billing_email"] = carrier_billing_email
            if dispute_mode is not None:
                update_data["dispute_mode"] = dispute_mode

            if not update_data:
                raise HTTPException(status_code=422, detail="No valid fields provided")

            update_data["client_id"] = client_id

            existing = _rest_select("client_contracts", {
                "select": "client_id",
                "client_id": f"eq.{client_id}",
                "limit": 1,
            })
            if existing:
                rows = _rest_update("client_contracts", update_data, {"client_id": f"eq.{client_id}"})
                contract = rows[0] if rows else update_data
            else:
                record = _rest_insert("client_contracts", update_data)
                contract = record if record else update_data
        except HTTPException:
            raise
        except Exception as exc:
            log.error(f"{LOG_PREFIX} Contract update failed: {exc}")
            raise HTTPException(status_code=500, detail="Failed to update contract")

    log.info(f"{LOG_PREFIX} Contract updated", client_id=client_id, fields=list(body.keys()))

    return {
        "status": "success",
        "client_id": client_id,
        "contract": contract,
    }


# ---------------------------------------------------------------------------
# POST /v1/client/{client_id}/audits/{audit_id}/approve
# ---------------------------------------------------------------------------

@app.post("/v1/client/{client_id}/audits/{audit_id}/approve")
async def approve_audit(
    client_id: str,
    audit_id: int,
    authorization: Optional[str] = Header(None),
):
    _verify_token(authorization)

    record = update_audit_status(audit_id, "APPROVED")
    if not record:
        raise HTTPException(status_code=404, detail=f"Audit {audit_id} not found")

    log.info(f"{LOG_PREFIX} Audit approved", client_id=client_id, audit_id=audit_id)

    return {
        "status": "success",
        "audit_id": audit_id,
        "new_status": "APPROVED",
    }


# ---------------------------------------------------------------------------
# Admin: API Key Management
# ---------------------------------------------------------------------------

@app.post("/v1/admin/api-keys")
async def create_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Generate a new per-client API key. Requires internal token auth."""
    _verify_token(authorization)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    client_id = body.get("client_id")
    name = body.get("name", "default")

    if not client_id:
        raise HTTPException(status_code=422, detail="client_id is required")

    from v1_database.api_keys import generate_api_key
    result = generate_api_key(client_id, name)

    log.info(f"{LOG_PREFIX} API key generated", client_id=client_id, key_prefix=result["key_prefix"])

    return {
        "status": "success",
        "client_id": client_id,
        "api_key": result["api_key"],
        "key_prefix": result["key_prefix"],
        "name": name,
        "message": "Store this key securely — it will not be shown again",
    }


@app.get("/v1/admin/api-keys")
async def list_api_keys(
    client_id: str,
    authorization: Optional[str] = Header(None),
):
    """List API keys for a client. Requires internal token auth."""
    _verify_token(authorization)

    if not MOCK_MODE:
        try:
            from v1_database.supabase_client import _rest_select
            rows = _rest_select("client_api_keys", {
                "select": "id,key_prefix,name,active,created_at,last_used_at",
                "client_id": f"eq.{client_id}",
                "order": "created_at.desc",
            })
            return {"client_id": client_id, "keys": rows}
        except Exception:
            return {"client_id": client_id, "keys": []}

    return {"client_id": client_id, "keys": []}


@app.delete("/v1/admin/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    authorization: Optional[str] = Header(None),
):
    """Revoke (deactivate) an API key. Requires internal token auth."""
    _verify_token(authorization)

    if not MOCK_MODE:
        from v1_database.supabase_client import _rest_update
        _rest_update("client_api_keys", {"active": False}, {"id": f"eq.{key_id}"})
        log.info(f"{LOG_PREFIX} API key revoked", key_id=key_id)
        return {"status": "success", "message": "Key revoked"}

    return {"status": "success", "message": "Key revoked (mock mode)"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "v1_ingestion.main_gateway:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level=LOG_LEVEL.lower(),
    )
