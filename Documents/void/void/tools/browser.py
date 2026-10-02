"""Browser + vision tools -- real rendering and image understanding.

browser_fetch: headless rendering via Playwright when installed, else static HTTP.
vision_describe: send a local image to the configured model (needs a vision-capable model).
"""

import base64
import json
from pathlib import Path

from void.tools.registry import register


def browser_fetch(url: str, wait_ms: int = 2000) -> dict:
    """Render a page in a real headless browser and return its text.

    Requires `pip install playwright && playwright install chromium`.
    Falls back to static fetch when Playwright is unavailable.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        from void.tools.web import web_extract_text
        out = web_extract_text(url)
        out["note"] = "playwright not installed -- static fetch. pip install playwright && playwright install chromium"
        return out

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(wait_ms)
            text = page.inner_text("body")
            html = page.content()
            browser.close()
        lines = [l for l in text.splitlines() if l.strip()]
        return {
            "url": url,
            "text_length": len(text),
            "line_count": len(lines),
            "text": "\n".join(lines[:500]),
            "html_length": len(html),
            "note": "playwright",
        }
    except Exception as e:
        return {"error": str(e), "url": url}


def browser_click(url: str, selector: str, wait_ms: int = 1000) -> dict:
    """Open a page, click an element, return the resulting text."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "playwright not installed. pip install playwright && playwright install chromium"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.click(selector, timeout=10000)
            page.wait_for_timeout(wait_ms)
            text = page.inner_text("body")
            browser.close()
        return {"url": url, "selector": selector, "text": text[:20000], "note": "playwright"}
    except Exception as e:
        return {"error": str(e)}


def vision_describe(image_path: str, question: str = "Describe this image.") -> dict:
    """Ask the configured model about a local image (needs a vision model)."""
    p = Path(image_path)
    if not p.exists():
        return {"error": f"file not found: {image_path}"}

    ext = p.suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext)
    if not mime:
        return {"error": f"unsupported image type: .{ext}"}

    try:
        b64 = base64.b64encode(p.read_bytes()).decode()
    except OSError as e:
        return {"error": str(e)}

    try:
        from void.cli import build_model
        import argparse
        model = build_model(argparse.Namespace(api_key=None, base_url=None, model=None))
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
            ],
        }]
        resp = model.chat(messages)
        return {"image": str(p), "question": question, "answer": resp.content or ""}
    except Exception as e:
        return {"error": f"vision call failed (model may not support images): {e}"}


register(
    "browser_fetch",
    {
        "name": "browser_fetch",
        "description": "Render a page in a real headless browser (JS-rendered SPAs) and return its text. Needs playwright.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to render"},
                "wait_ms": {"type": "integer", "description": "Extra wait after load", "default": 2000},
            },
            "required": ["url"],
        },
    },
    browser_fetch,
)
register(
    "browser_click",
    {
        "name": "browser_click",
        "description": "Open a page in a headless browser, click a CSS selector, return resulting text.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "selector": {"type": "string", "description": "CSS selector to click"},
                "wait_ms": {"type": "integer", "default": 1000},
            },
            "required": ["url", "selector"],
        },
    },
    browser_click,
)
register(
    "vision_describe",
    {
        "name": "vision_describe",
        "description": "Ask the model about a local image file (screenshot, chart, photo). Needs a vision-capable model.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to a local image"},
                "question": {"type": "string", "description": "What to ask about it", "default": "Describe this image."},
            },
            "required": ["image_path"],
        },
    },
    vision_describe,
)


if __name__ == "__main__":
    # Self-check: tools register and bad input is handled, not crashed on.
    from void.tools.registry import list_tools
    assert "browser_fetch" in list_tools()
    assert "vision_describe" in list_tools()
    assert "error" in vision_describe("/nonexistent/x.png")
    assert "error" in vision_describe(__file__)  # .py is not an image
    print("browser/vision tools OK")
