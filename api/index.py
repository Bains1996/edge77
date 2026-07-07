"""Vercel entry point."""
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse

app = FastAPI(title="EDGE77")

_inner = None
_err = None
_loaded = False
index_html = None
dashboard_html = None


def _load():
    global _inner, _err, _loaded, index_html, dashboard_html
    if _loaded:
        return
    _loaded = True
    try:
        from v1_ingestion.main_gateway import app as loaded
        _inner = loaded
    except Exception:
        import traceback
        _err = traceback.format_exc()
    for name in ["index.html", "dashboard.html"]:
        fpath = Path(__file__).resolve().parent / name
        if fpath.exists():
            globals()[name.replace(".", "_")] = fpath.read_text(encoding="utf-8")


@app.get("/health")
async def health():
    _load()
    if _inner:
        return {"status": "healthy", "service": "edge77-gateway"}
    return JSONResponse(status_code=500, content={"error": _err[:2000] if _err else "unknown"})


@app.get("/", response_class=HTMLResponse)
async def landing():
    _load()
    if index_html:
        return HTMLResponse(content=index_html)
    return HTMLResponse("<h1>EDGE77</h1>")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    _load()
    if dashboard_html:
        return HTMLResponse(content=dashboard_html)
    return HTMLResponse("<h1>Dashboard</h1>")


@app.get("/docs")
async def docs():
    return HTMLResponse("<h1>API Docs</h1><p>Available at /docs on local server</p>")


@app.get("/openapi.json")
async def openapi():
    return JSONResponse({"openapi": "3.0.0", "info": {"title": "EDGE77", "version": "1.0.0"}})
