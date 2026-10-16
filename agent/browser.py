"""Browser sessions: Anchor Browser (cloud, via CDP) or local Playwright fallback."""
from __future__ import annotations

import os
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from agent.schemas import BrowserRun
from tests.acceptance import run_acceptance

# Daytona shows an interstitial on browser visits to previews unless this header is set.
PREVIEW_HEADERS = {"X-Daytona-Skip-Preview-Warning": "true"}


@contextmanager
def _page(provider: str):
    with sync_playwright() as p:
        session_id = None
        client = None
        if provider == "anchor":
            from anchorbrowser import Anchorbrowser

            client = Anchorbrowser(api_key=os.environ["ANCHOR_API_KEY"])
            sess = client.sessions.create_session()
            session_id = sess.data.id
            browser = p.chromium.connect_over_cdp(sess.data.cdp_url)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        else:
            browser = p.chromium.launch()
            ctx = browser.new_context()
        ctx.set_extra_http_headers(PREVIEW_HEADERS)
        page = ctx.new_page()
        page.set_viewport_size({"width": 1100, "height": 760})
        try:
            yield page, session_id
        finally:
            try:
                browser.close()
            finally:
                if client and session_id:
                    try:
                        client.sessions.delete_session(session_id)
                    except Exception:
                        pass


def default_provider() -> str:
    return "anchor" if os.environ.get("ANCHOR_API_KEY") else "local-playwright"


def run_checks(url: str, screenshot_path: str, provider: str | None = None) -> BrowserRun:
    provider = provider or default_provider()
    try:
        with _page(provider) as (page, session_id):
            checks = run_acceptance(page, url, screenshot_path)
        return BrowserRun(url, provider, checks, screenshot_path, session_id)
    except Exception as e:
        return BrowserRun(url, provider, [], None, None, f"{type(e).__name__}: {e}")


