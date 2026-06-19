# BarePage

One-click removal of ads, pop-ups, and fluff from any webpage. Get straight to the core content — recipe ingredients, article text, product specs — without the clutter.

## Features

- **Remove Ads** — Strips ad iframes, script tags, popup overlays, tracker pixels. Preserves page layout.
- **Remove Bloat** — Extracts only the core content (article body, recipe steps) using trafilatura + heuristics. Strip headers, footers, sidebars, navs, comments, and backstories.

## Quick Start

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 3000
```

Then open http://localhost:3000 in your browser.

## API

`POST /api/clean`
```json
{ "url": "https://example.com/recipe", "mode": "bloat" }
```

Returns `{ title, content, content_text, url, mode }`.

## Tech Stack

- **Backend**: Python/FastAPI with trafilatura, beautifulsoup4, httpx
- **Frontend**: Static HTML/CSS/JS (no build step)
- **Payments**: Stripe (freemium: 5 free/day, $3.99/month premium)