# BarePage Browser Extension — Spec

## Goal
A Chrome/Firefox extension that adds a "Clean Page" button to the toolbar. Click it on any recipe blog or article page, and the extension strips ads and bloat inline — no need to copy-paste URLs.

## Architecture

### Option A: In-page cleaning (simpler)
- Extension injects a content script that runs the same logic as the web tool
- Uses local trafilatura (WASM or bundled JS version) OR calls the BarePage API
- Overlays a "Clean this page" button or uses browser action popup

### Option B: API-based (recommended for MVP)
- Extension calls the BarePage backend API (`POST /api/clean`)
- On click: sends current page URL to API, receives cleaned HTML, replaces page content
- Requires backend to be publicly deployed

## Features
1. **Browser action** — click the extension icon to clean the current page
2. **Context menu** — right-click link → "Open with BarePage"
3. **Auto-clean toggle** — option to auto-clean recipe domains (bbcgoodfood.com, allrecipes.com, etc.)
4. **Premium badge** — shows usage count, premium upgrade link

## Files needed
```
extension/
├── manifest.json
├── background.js
├── content.js
├── popup.html
├── popup.js
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
```

## MVP scope
- manifest.json (Chrome MV3 + Firefox compatible)
- Popup with URL cleaner (same as web tool but in extension popup)
- Content script that replaces page content with cleaned version
- API call to backend

## Future
- Auto-detect recipe pages and add "Clean" button inline
- Offline mode with WASM trafilatura
- Saved preferences per domain