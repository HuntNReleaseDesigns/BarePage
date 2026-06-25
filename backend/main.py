"""
BarePage - FastAPI backend application.

Serves the static frontend and exposes the /api/clean endpoint.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from backend.cleaner import fetch_html, clean_ads, clean_bloat

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'

app = FastAPI(
    title='BarePage',
    description='Strip ads, pop-ups, and fluff from any webpage.',
    version='0.1.0',
)


class CleanRequest(BaseModel):
    url: str
    mode: str = 'bloat'  # "bloat" or "ads"


@app.get('/api/health')
async def health():
    return {'status': 'ok', 'service': 'barepage'}


@app.post('/api/clean')
async def clean_url(req: CleanRequest):
    """Fetch a URL and return cleaned content based on the requested mode."""
    if req.mode not in ('bloat', 'ads'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{req.mode}'. Must be 'bloat' or 'ads'.",
        )

    # Validate URL
    url = req.url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f'Failed to fetch URL: {str(e)}',
        )

    try:
        if req.mode == 'ads':
            result = clean_ads(html, url)
        else:
            result = clean_bloat(html, url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to clean content: {str(e)}',
        )

    return result


# --- Serve static frontend ---

@app.get('/', response_class=HTMLResponse)
async def serve_landing():
    """Serve the marketing landing page."""
    landing_path = FRONTEND_DIR / 'landing.html'
    if not landing_path.exists():
        # Fallback to index.html if landing doesn't exist yet
        index_path = FRONTEND_DIR / 'index.html'
        if index_path.exists():
            return HTMLResponse(index_path.read_text(encoding='utf-8'))
        return HTMLResponse('<h1>BarePage</h1><p>Frontend not found.</p>', status_code=404)
    return HTMLResponse(landing_path.read_text(encoding='utf-8'))


@app.get('/app', response_class=HTMLResponse)
async def serve_tool():
    """Serve the BarePage cleaning tool SPA."""
    tool_path = FRONTEND_DIR / 'tool.html'
    if not tool_path.exists():
        return HTMLResponse('<h1>BarePage</h1><p>Tool not found.</p>', status_code=404)
    return HTMLResponse(tool_path.read_text(encoding='utf-8'))


@app.get('/{path:path}')
async def serve_static(path: str):
    """Serve static frontend files (css, js, etc.) with SPA fallback."""
    file_path = FRONTEND_DIR / path

    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))

    # For unknown paths under /app, serve tool.html (SPA fallback)
    tool_path = FRONTEND_DIR / 'tool.html'
    if tool_path.exists():
        return HTMLResponse(tool_path.read_text(encoding='utf-8'))
    else:
        return HTMLResponse('<h1>BarePage</h1><p>Frontend not found.</p>', status_code=404)