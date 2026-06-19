"""
BarePage - Content extraction and cleaning logic.

Supports two modes:
- "ads": strips ad iframes, script tags, known ad selectors, popup overlays, tracker pixels
- "bloat": extracts only the core content (article, recipe, docs) using trafilatura + heuristics
          while stripping sidebars, footers, navs, and pre-content narratives
"""

import re
import httpx
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

# Known ad class/id patterns to remove
# NOTE: Keep patterns narrow — "sticky" is too broad (matches Wikipedia vector-sticky-*)
AD_PATTERNS = re.compile(
    r'((^|[\s_-])(ad|ads|advert|advertisement|sponsor|sponsored|promo|promotion|'
    r'banner|popup|pop-up|overlay|modal|paid|promoted|marketing)'
    r'([\s_-]|$))',
    re.IGNORECASE,
)

# Elements that are typically not core content
BLOAT_SELECTORS = [
    'header', 'footer', 'nav', 'aside',
    '.sidebar', '#sidebar', '.nav', '.navbar', '.navigation',
    '.footer', '.header',
    '.comments', '#comments', '.comment-list',
    '.related-posts', '.recommended',
    '.social-share', '.social-sharing', '.share-buttons',
    '.author-bio', '.author-box',
    '.breadcrumbs', '.breadcrumb',
    '.widget', '.widget-area',
    '.cookie', '.cookie-consent', '.cookie-notice',
    '.newsletter', '.subscribe',
    '.table-of-contents', '.toc',
    '[role="navigation"]', '[role="complementary"]',
    '[role="contentinfo"]',
]

# Script-like tags that are always removed
REMOVABLE_TAGS = ['script', 'style', 'noscript', 'iframe', 'object', 'embed', 'canvas']

# Popup/overlay common IDs and classes
POPUP_PATTERNS = re.compile(
    r'((^|[\s_-])(popup|pop-up|overlay|modal|lightbox|cookie-notice|'
    r'newsletter-popup|exit-intent|slide-in)([\s_-]|$))',
    re.IGNORECASE,
)

# Tracker pixel patterns
TRACKER_PATTERNS = re.compile(
    r'((^|[\s_-])(pixel|tracker|analytics|beacon|web-vitals)([\s_-]|$))',
    re.IGNORECASE,
)

DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def _get_tag_attrs(tag: Tag) -> dict:
    """Safely get tag attributes, handling None attrs (beautifulsoup4 v4.15+)."""
    attrs = tag.attrs
    return attrs if isinstance(attrs, dict) else {}


def _has_ad_pattern(text: str, pattern: re.Pattern) -> bool:
    """Check if a string matches an ad/popup/tracker pattern."""
    if not text:
        return False
    return bool(pattern.search(text))


def _is_ad_element(tag: Tag) -> bool:
    """Check if a tag looks like an ad based on its id, class, or attributes."""
    attrs = _get_tag_attrs(tag)

    # Check id
    tag_id = attrs.get('id', '') or ''
    if _has_ad_pattern(tag_id, AD_PATTERNS):
        return True

    # Check class
    classes = attrs.get('class', [])
    if isinstance(classes, list):
        for cls in classes:
            if cls and _has_ad_pattern(str(cls), AD_PATTERNS):
                return True

    # Check data attributes (used by many ad frameworks)
    for attr in attrs:
        if any(kw in attr.lower() for kw in ['ad', 'sponsor', 'promo', 'tracking']):
            return True

    # Check for ad-related aria labels
    aria_label = attrs.get('aria-label', '') or ''
    if _has_ad_pattern(aria_label, AD_PATTERNS):
        return True

    return False


def _is_popup_overlay(tag: Tag) -> bool:
    """Check if a tag is likely a popup/overlay."""
    attrs = _get_tag_attrs(tag)
    tag_id = attrs.get('id', '') or ''
    if _has_ad_pattern(tag_id, POPUP_PATTERNS):
        return True

    classes = attrs.get('class', [])
    if isinstance(classes, list):
        for cls in classes:
            if cls and _has_ad_pattern(str(cls), POPUP_PATTERNS):
                return True

    return False


def _is_tracker(tag: Tag) -> bool:
    """Check if a tag is a tracking pixel."""
    attrs = _get_tag_attrs(tag)

    # Very small images (pixels)
    if tag.name == 'img':
        w = attrs.get('width')
        h = attrs.get('height')
        if w is not None and h is not None:
            try:
                if int(w) <= 1 and int(h) <= 1:
                    return True
            except (ValueError, TypeError):
                pass

    tag_id = attrs.get('id', '') or ''
    if _has_ad_pattern(tag_id, TRACKER_PATTERNS):
        return True

    classes = attrs.get('class', [])
    if isinstance(classes, list):
        for cls in classes:
            if cls and _has_ad_pattern(str(cls), TRACKER_PATTERNS):
                return True

    return False


def _remove_ads(soup: BeautifulSoup) -> int:
    """Remove ad elements, popups, trackers from the soup. Returns count removed."""
    count = 0

    # Remove known ad-related tags by type
    for tag_name in REMOVABLE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
            count += 1

    # Remove elements matching ad patterns in id/class
    for tag in soup.find_all(True):
        # Never remove structural/core tags
        if tag.name in ('html', 'head', 'body', 'title', 'meta'):
            continue
        if _is_ad_element(tag):
            tag.decompose()
            count += 1
            continue
        if _is_popup_overlay(tag):
            tag.decompose()
            count += 1
            continue
        if _is_tracker(tag):
            tag.decompose()
            count += 1
            continue

    return count


def _remove_bloat(soup: BeautifulSoup) -> int:
    """Remove non-core content elements. Returns count removed."""
    count = 0
    for selector in BLOAT_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()
            count += 1
    return count


def _clean_html(soup: BeautifulSoup, url: str) -> BeautifulSoup:
    """Clean up the HTML after extraction - fix links, remove empty elements."""
    # Make relative links absolute
    for tag in soup.find_all(['a', 'img', 'link']):
        attrs = _get_tag_attrs(tag)
        href = attrs.get('href')
        if href and not href.startswith(('#', 'javascript:', 'mailto:')):
            tag['href'] = urljoin(url, href)

        src = attrs.get('src')
        if src:
            tag['src'] = urljoin(url, src)

    # Remove empty elements (that have no text and no meaningful children)
    for tag in soup.find_all(True):
        if tag.name in ['div', 'span', 'section', 'p']:
            if not tag.get_text(strip=True) and not tag.find_all(['img', 'video', 'audio']):
                tag.decompose()

    return soup


async def fetch_html(url: str) -> str:
    """Fetch HTML content from a URL with a proper user-agent."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15.0,
        headers={'User-Agent': DEFAULT_USER_AGENT},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def clean_ads(html: str, url: str) -> dict:
    """Remove ads, popups, trackers from HTML. Returns cleaned content."""
    soup = BeautifulSoup(html, 'html.parser')

    # Save original title
    title = soup.title.string if soup.title and soup.title.string else ''

    _remove_ads(soup)

    # Clean up
    soup = _clean_html(soup, url)

    return {
        'title': title.strip() if title else '',
        'content': str(soup.body) if soup.body else '',
        'content_text': soup.get_text(separator='\n', strip=True),
        'url': url,
        'mode': 'ads',
    }


def _extract_via_trafilatura(html: str) -> str | None:
    """Try to extract core content using trafilatura."""
    try:
        import trafilatura
        extracted = trafilatura.extract(html, output_format='html', include_links=True,
                                        include_tables=True, include_images=True)
        return extracted
    except Exception:
        return None


def _extract_via_selectors(soup: BeautifulSoup) -> Tag | None:
    """Try to extract main content using common content selectors."""
    content_selectors = [
        'article',
        '[role="main"]',
        'main',
        '#content',
        '.content',
        '.post-content',
        '.article-content',
        '.entry-content',
        '.post',
        '.article',
        '#main-content',
        '.main-content',
        '.recipe-content',
        '.recipe',
        '#recipe',
        '.mw-parser-output',  # Wikipedia
        '#readability-page-1',  # readability
        '.reading-content',
    ]

    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            # Return the first substantial match
            for el in elements:
                text_len = len(el.get_text(strip=True))
                if text_len > 100:
                    return el

    return None


def clean_bloat(html: str, url: str) -> dict:
    """
    Remove all clutter and extract only the main content.
    
    Strategy: Use trafilatura first (best extraction), fall back to 
    manual content selectors, then apply light cleaning.
    """
    # Save original title
    soup_for_title = BeautifulSoup(html, 'html.parser')
    title = soup_for_title.title.string if soup_for_title.title and soup_for_title.title.string else ''

    # --- Strategy 1: Try trafilatura on the raw HTML ---
    extracted = _extract_via_trafilatura(html)
    if extracted and len(extracted.strip()) > 100:
        # Parse the extracted content and do light cleanup (ads, empty elements)
        content_soup = BeautifulSoup(extracted, 'html.parser')
        _remove_ads(content_soup)
        content_soup = _clean_html(content_soup, url)

        content_html = str(content_soup)
        content_text = content_soup.get_text(separator='\n', strip=True)

        return {
            'title': title.strip() if title else '',
            'content': content_html,
            'content_text': content_text,
            'url': url,
            'mode': 'bloat',
        }

    # --- Strategy 2: Fall back to manual extraction ---
    soup = BeautifulSoup(html, 'html.parser')

    # Try to find main content area FIRST before stripping
    main_content = _extract_via_selectors(soup)

    if main_content:
        # Work only within the main content area
        content_soup = BeautifulSoup(str(main_content), 'html.parser')
        _remove_ads(content_soup)
        _remove_bloat(content_soup)
        content_soup = _clean_html(content_soup, url)

        # If we stripped too much, use the original main content with just ads removed
        cleaned_text = content_soup.get_text(separator='\n', strip=True)
        if len(cleaned_text) < 50:
            # Too aggressive — redo with just ad removal on the original main content
            content_soup = BeautifulSoup(str(main_content), 'html.parser')
            _remove_ads(content_soup)
            content_soup = _clean_html(content_soup, url)
    else:
        # No main content area found — remove ads/bloat from body and use that
        _remove_ads(soup)
        _remove_bloat(soup)
        content_soup = _clean_html(soup, url)

    content_html = str(content_soup)
    content_text = content_soup.get_text(separator='\n', strip=True)

    # If still empty, return the raw body text as a last resort
    if not content_text.strip():
        fallback_soup = BeautifulSoup(html, 'html.parser')
        _remove_ads(fallback_soup)
        body = fallback_soup.find('body')
        if body:
            content_text = body.get_text(separator='\n', strip=True)
            content_html = str(body)
        else:
            content_text = fallback_soup.get_text(separator='\n', strip=True)
            content_html = f'<p>{content_text}</p>'

    return {
        'title': title.strip() if title else '',
        'content': content_html,
        'content_text': content_text,
        'url': url,
        'mode': 'bloat',
    }
