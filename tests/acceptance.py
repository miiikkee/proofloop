"""Three fixed, developer-defined acceptance checks. The LLM never edits these.

Usage against any reachable URL (local Playwright):
    python -m tests.acceptance http://127.0.0.1:3000
"""
from __future__ import annotations

import sys
import time
from urllib.parse import urlparse

from agent.schemas import CheckResult

STEP_TIMEOUT_MS = 8000


def _timed(name, fn) -> CheckResult:
    t0 = time.monotonic()
    try:
        detail = fn() or "ok"
        passed = True
    except Exception as e:  # assertion or Playwright timeout
        detail = f"{type(e).__name__}: {str(e).splitlines()[0][:300]}"
        passed = False
    return CheckResult(name, passed, detail, int((time.monotonic() - t0) * 1000))


def run_acceptance(page, base_url: str, screenshot_path: str | None = None) -> list[CheckResult]:
    base = base_url.rstrip("/")
    page.set_default_timeout(STEP_TIMEOUT_MS)

    def homepage():
        resp = page.goto(base + "/", wait_until="domcontentloaded")
        assert resp is not None and resp.ok, f"HTTP {resp.status if resp else 'no response'}"
        h1 = page.locator("h1").first.inner_text()
        assert "Acme Studio" in h1, f"unexpected heading {h1!r}"
        return f"heading={h1!r}"

    def contact_page():
        page.goto(base + "/", wait_until="domcontentloaded")
        page.click("#contact-link")
        page.wait_for_selector("form#contact-form")
        assert page.locator("#send").count() == 1, "Send button missing"
        return f"path={urlparse(page.url).path}"

    def contact_submit():
        page.goto(base + "/contact", wait_until="domcontentloaded")
        page.fill("#name", "Ada QA")
        page.fill("#email", "ada@example.com")
        page.fill("#message", "Automated acceptance check from ProofLoop.")
        page.click("#send")
        try:
            page.wait_for_selector("text=Thank you", timeout=5000)
        finally:
            if screenshot_path:
                page.screenshot(path=screenshot_path, full_page=True)
        return "confirmation visible"

    results = [
        _timed("homepage_heading", homepage),
        _timed("contact_page_reachable", contact_page),
        _timed("contact_submit_thank_you", contact_submit),
    ]
    if screenshot_path and not results[2].passed:
        # Record what the user saw after clicking Send.
        # Path only: preview hostnames carry access tokens and must not be logged.
        path = urlparse(page.url).path or "/"
        results[2].detail += f" | page_path_after_click={path} | visible_h1={page.locator('h1').first.inner_text()!r}"
    return results


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000"
    with sync_playwright() as p:
        b = p.chromium.launch()
        res = run_acceptance(b.new_page(), url, "artifacts/local_check.png")
        b.close()
    for r in res:
        print(("PASS" if r.passed else "FAIL"), r.name, "-", r.detail)
    print(f"{sum(r.passed for r in res)}/{len(res)} passed")
