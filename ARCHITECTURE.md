# BarePage Architecture

## Overview
A web tool that strips ads, pop-ups, and fluff from any webpage, returning clean core content.

## Components

### 1. Backend (Python/FastAPI)
- **`/api/clean`** — POST endpoint accepting `{ url: string, mode: "bloat" | "ads" }`
  - Fetches the URL's HTML (with proper user-agent headers)
  - Mode "ads": Strips ad iframes, script tags, known ad selectors, popup overlays
  - Mode "bloat": Same as ads + extracts only the "main" content using readability algo, stripping sidebars, footers, navs, and long backstories
  - Returns `{ title, content, url, mode }`
- Uses: `trafilatura`, `beautifulsoup4`, `httpx`
- Runs on port 8000

### 2. Frontend (Static HTML/CSS/JS)
- Single-page app with:
  - URL input field
  - Two action buttons: "Remove Bloat" and "Remove Ads"
  - Cleaned content display area
  - Reader-friendly styling (clean typography, max-width)
- Served by the backend (or separately)

### 3. Flow
1. User pastes URL → clicks "Remove Bloat" or "Remove Ads"
2. Frontend sends POST to `/api/clean` with `{ url, mode }`
3. Backend fetches page → parses → extracts → returns clean content
4. Frontend renders cleaned content

## File Structure
```
/home/team/shared/barepage/
├── backend/
│   ├── main.py          (FastAPI app)
│   ├── cleaner.py       (content extraction logic)
│   ├── requirements.txt
│   └── __init__.py
├── frontend/
│   ├── index.html       (SPA)
│   ├── styles.css
│   └── app.js
└── ARCHITECTURE.md
```