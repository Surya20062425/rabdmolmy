"""Web scraping tools — fetch pages, extract content.

Ponytail: prefers requests + beautifulsoup4 (installed). Falls back to
stdlib urllib + regex. No JS rendering (use Playwright/Steampipe when needed).
"""

import json
import re
from urllib.parse import urlparse, urljoin, quote_plus

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from void.tools.registry import register


_HEADERS = {
    "User-Agent": "Void/1.0 (CLI agent; +https://github.com/NousResearch/hermes-agent)",
}


def _fetch(session, url: str, timeout: int = 30) -> str | None:
    """Return HTML text or None."""
    if HAS_REQUESTS:
        try:
            resp = session.get(url, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception:
            pass

    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def web_fetch(url: str, timeout: int = 30) -> dict:
    """Fetch a URL and return raw HTML content."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"error": f"invalid URL (need scheme + host): {url}"}

    session = requests.Session() if HAS_REQUESTS else None
    html = _fetch(session, url, timeout)
    if html is None:
        return {"error": f"failed to fetch: {url}", "url": url}

    cap = 50000
    return {
        "url": url,
        "status": "ok",
        "length": len(html),
        "content": html[:cap],
        "truncated": len(html) > cap,
    }


def web_extract_text(url: str, timeout: int = 30) -> dict:
    """Fetch a webpage and extract readable text content."""
    fetch_result = web_fetch(url, timeout)
    if "error" in fetch_result:
        return fetch_result

    html = fetch_result["content"]
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
    else:
        text = re.sub(r"<[^>]+>", "\n", html)
        text = re.sub(r"\n\s*\n+", "\n", text)
        text = text.strip()

    lines = [l for l in text.splitlines() if l.strip()]
    text = "\n".join(lines[:500])

    return {
        "url": url,
        "text_length": len(text),
        "line_count": len(lines),
        "text": text,
        "note": "bs4" if HAS_BS4 else "regex fallback",
    }


def web_search(query: str, timeout: int = 10) -> dict:
    """Search DuckDuckGo HTML (no API key needed)."""
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    session = requests.Session() if HAS_REQUESTS else None
    html = _fetch(session, search_url, timeout)

    if html is None:
        return {"error": "search failed", "query": query}

    results = []
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select(".result__a"):
            title = a.get_text(strip=True)
            raw = a.get("href", "")
            m = re.search(r"uddg=([^&]+)", raw)
            url = quote_plus(m.group(1).rstrip("=").strip()) if m else raw
            results.append({"title": title, "url": url})
    else:
        for m in re.finditer(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        ):
            url = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            results.append({"title": title, "url": url})

    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    return {
        "query": query,
        "result_count": len(unique),
        "results": unique[:10],
    }


register(
    name="web_fetch",
    schema={
        "name": "web_fetch",
        "description": "Fetch a URL and return raw HTML content",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch (must include scheme)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            },
            "required": ["url"],
        },
    },
    handler=web_fetch,
)

register(
    name="web_extract_text",
    schema={
        "name": "web_extract_text",
        "description": "Fetch a webpage and extract readable text content",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            },
            "required": ["url"],
        },
    },
    handler=web_extract_text,
)

register(
    name="web_search",
    schema={
        "name": "web_search",
        "description": "Search the web using DuckDuckGo (no API key needed)",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    handler=web_search,
)
